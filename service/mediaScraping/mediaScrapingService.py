import contextlib
import io
import json
import logging
import posixpath
import re
import threading
import time

from common import commonUtils
from common.LNG import G, set_context_lang
from mapper import mediaScrapingMapper, openlistMapper, systemConfigMapper
from media_tools.openlist_media_renamer import (
    DEFAULT_MEDIA_EXTENSIONS,
    DEFAULT_MOVIE_TEMPLATE,
    DEFAULT_RENAME_THREADS,
    DEFAULT_TV_TEMPLATE,
    MediaInfo,
    RenamePlan,
    TMDbError,
    apply_file_plans,
    apply_root_renames,
    build_client,
    build_tmdb_client,
    collect_root_rename_pairs,
    collect_files,
    join_openlist_path,
    normalize_openlist_path,
    plan_for_file,
    run as run_media_renamer,
)
from service.notify import notifyService
from service.openlist import openlistService


MEDIA_SCRAPING_CONFIG_KEY = 'media_scraping'
ROOT_RENAME_RE = re.compile(r'^\[root-renamed\]\s+(.+?)\s+->\s+(.+)$', re.MULTILINE)
MEDIA_LOG_LINE_RE = re.compile(r'^\[(?:timing|root-renamed|dry-run|error)\].*', re.MULTILINE)
MEDIA_OUTPUT_RE = re.compile(r'^\[(?P<status>[^\]]+)\]\s+(?P<src>.+?)\s+->\s+(?P<target>.+)$', re.MULTILINE)
MEDIA_ERROR_RE = re.compile(r'^\[error\]\s+(?P<src>.+?)\s+->\s+(?P<target>.+?):\s+(?P<error>.+)$', re.MULTILINE)
MEDIA_NAME_SEGMENT_RE = re.compile(r'.+\s\(\d{4}\)$')
MEDIA_ABORT_EVENTS = {}
MEDIA_ABORT_LOCK = threading.Lock()


def _default_config():
    return {
        'defaultOpenlistId': None,
        'openlistIds': [],
        'tmdbApiKey': '',
        'tmdbBearerToken': '',
        'tmdbLanguage': 'zh-CN',
        'tmdbIncludeAdult': False,
        'tmdbRequired': True,
        'tmdbTimeout': 30,
        'openlistTimeout': 30,
        'dryRun': True,
        'overwrite': False,
        'refresh': False,
        'limit': 0,
        'renameThreads': DEFAULT_RENAME_THREADS,
        'movieTemplate': DEFAULT_MOVIE_TEMPLATE,
        'tvTemplate': DEFAULT_TV_TEMPLATE,
        'mediaExtensions': sorted(DEFAULT_MEDIA_EXTENSIONS),
        'customWords': '',
        'customReleaseGroups': '',
        'customization': '',
        'renameLogLimit': 10,
        'rules': []
    }


def _to_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _to_int(value, default=0, min_value=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if min_value is not None and result < min_value:
        return min_value
    return result


def _optional_int(data, *keys):
    for key in keys:
        if isinstance(data, dict) and key in data:
            value = data.get(key)
            if value is None or value == '':
                return None
            return _to_int(value, 0, 0)
    return None


def _line_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [line.strip() for line in str(value or '').splitlines() if line.strip()]


def _extract_root_renames(stdout):
    result = []
    seen = set()
    for match in ROOT_RENAME_RE.finditer(stdout or ''):
        item = {
            'from': normalize_openlist_path(match.group(1)),
            'to': normalize_openlist_path(match.group(2))
        }
        key = (item['from'], item['to'])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _log_run_result(action, path, elapsed, result):
    logger = logging.getLogger()
    logger.info(
        "Media scraping action=%s path=%s elapsed=%.2fs success=%s usedPreviewPlans=%s",
        action,
        path,
        elapsed,
        result.get('success') if isinstance(result, dict) else None,
        result.get('usedPreviewPlans') if isinstance(result, dict) else None,
    )
    if not isinstance(result, dict):
        return
    for item in result.get('results') or []:
        if not isinstance(item, dict):
            continue
        logger.info(
            "Media scraping result openlist=%s success=%s code=%s error=%s",
            item.get('openlistName') or item.get('openlistId'),
            item.get('success'),
            item.get('code'),
            item.get('error') or '',
        )
        stdout = item.get('stdout') or ''
        for line in MEDIA_LOG_LINE_RE.findall(stdout):
            logger.info("Media scraping %s", line)
        stderr = (item.get('stderr') or '').strip()
        if stderr:
            logger.warning("Media scraping stderr: %s", stderr[:2000])


def _plans_from_preview(items):
    plans = []
    if not isinstance(items, list):
        return plans
    for item in items:
        if not isinstance(item, dict):
            continue
        src_path = normalize_openlist_path(str(item.get('srcPath') or ''))
        target_path = normalize_openlist_path(str(item.get('targetPath') or ''))
        if src_path == '/' or target_path == '/':
            continue
        info = MediaInfo(
            title=str(item.get('title') or ''),
            year=str(item.get('year') or ''),
            season=str(item.get('season') or ''),
            season_episode=str(item.get('episode') or ''),
            file_ext=''
        )
        plans.append(RenamePlan(
            info=info,
            src_path=src_path,
            target_path=target_path,
            effective_src_path=normalize_openlist_path(str(item.get('effectiveSrcPath') or src_path)),
            root_rename_from=normalize_openlist_path(str(item.get('rootRenameFrom') or '')) if item.get('rootRenameFrom') else '',
            root_rename_to=normalize_openlist_path(str(item.get('rootRenameTo') or '')) if item.get('rootRenameTo') else ''
        ))
    return plans


def _normalize_extensions(value):
    if isinstance(value, list):
        items = value
    else:
        items = str(value or '').replace('\n', ',').split(',')
    result = []
    for item in items:
        ext = str(item).strip().lower()
        if not ext:
            continue
        if not ext.startswith('.'):
            ext = '.' + ext
        if ext not in result:
            result.append(ext)
    return result or sorted(DEFAULT_MEDIA_EXTENSIONS)


def _normalize_rules(rules):
    result = []
    if not isinstance(rules, list):
        return result
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        path = str(rule.get('path') or '').strip()
        if not path:
            continue
        media_type = str(rule.get('type') or 'auto').strip().lower()
        if media_type not in {'auto', 'movie', 'tv'}:
            media_type = 'auto'
        result.append({
            'path': path,
            'type': media_type,
            'recursive': _to_bool(rule.get('recursive'), True),
            'extensions': _normalize_extensions(rule.get('extensions')) if rule.get('extensions') else None,
            'tmdbId': _optional_int(rule, 'tmdbId', 'tmdb_id') or 0,
            'seasonNumber': _optional_int(rule, 'seasonNumber', 'season')
        })
    return result


def _normalize_config(config):
    default_config = _default_config()
    config = config if isinstance(config, dict) else {}

    openlist_ids = config.get('openlistIds')
    if openlist_ids is None and config.get('openlistId') is not None:
        openlist_ids = [config.get('openlistId')]
    if not isinstance(openlist_ids, list):
        openlist_ids = []
    normalized_openlist_ids = []
    for item in openlist_ids:
        openlist_id = _to_int(item, 0, 0)
        if openlist_id and openlist_id not in normalized_openlist_ids:
            normalized_openlist_ids.append(openlist_id)
    default_openlist_id = _to_int(config.get('defaultOpenlistId'), 0, 0)
    if not default_openlist_id and normalized_openlist_ids:
        default_openlist_id = normalized_openlist_ids[0]
    if default_openlist_id and default_openlist_id not in normalized_openlist_ids:
        normalized_openlist_ids.insert(0, default_openlist_id)

    normalized = {
        **default_config,
        'defaultOpenlistId': default_openlist_id or None,
        'openlistIds': normalized_openlist_ids,
        'tmdbApiKey': str(config.get('tmdbApiKey') or '').strip(),
        'tmdbBearerToken': str(config.get('tmdbBearerToken') or '').strip(),
        'tmdbLanguage': str(config.get('tmdbLanguage') or default_config['tmdbLanguage']).strip() or default_config['tmdbLanguage'],
        'tmdbIncludeAdult': _to_bool(config.get('tmdbIncludeAdult'), default_config['tmdbIncludeAdult']),
        'tmdbRequired': _to_bool(config.get('tmdbRequired'), default_config['tmdbRequired']),
        'tmdbTimeout': _to_int(config.get('tmdbTimeout'), default_config['tmdbTimeout'], 1),
        'openlistTimeout': _to_int(config.get('openlistTimeout'), default_config['openlistTimeout'], 1),
        'dryRun': _to_bool(config.get('dryRun'), default_config['dryRun']),
        'overwrite': _to_bool(config.get('overwrite'), default_config['overwrite']),
        'refresh': _to_bool(config.get('refresh'), default_config['refresh']),
        'limit': _to_int(config.get('limit'), default_config['limit'], 0),
        'renameThreads': min(_to_int(config.get('renameThreads'), default_config['renameThreads'], 1), 16),
        'movieTemplate': str(config.get('movieTemplate') or default_config['movieTemplate']),
        'tvTemplate': str(config.get('tvTemplate') or default_config['tvTemplate']),
        'mediaExtensions': _normalize_extensions(config.get('mediaExtensions', default_config['mediaExtensions'])),
        'customWords': str(config.get('customWords') or ''),
        'customReleaseGroups': str(config.get('customReleaseGroups') or ''),
        'customization': str(config.get('customization') or ''),
        'renameLogLimit': _to_int(config.get('renameLogLimit'), default_config['renameLogLimit'], 0),
        'rules': _normalize_rules(config.get('rules'))
    }
    return normalized


def _task_item_status(status):
    status = str(status or '').lower()
    if status.startswith('error'):
        return 7
    if status.startswith('skip') or status.startswith('dry-run'):
        return 3
    return 2


def _progress_status(status, error=None):
    if str(status or '').lower() == 'running':
        return 1, ''
    if error:
        return 7, str(error)
    status_code = _task_item_status(status)
    err_msg = ''
    if status_code == 3:
        err_msg = status or ''
    return status_code, err_msg


def _is_root_follow_skip(item, src, target, result):
    if not isinstance(item, dict) or not isinstance(result, dict):
        return False
    if result.get('rawStatus') != 'skip: already named':
        return False
    root_from = normalize_openlist_path(str(item.get('rootRenameFrom') or ''))
    root_to = normalize_openlist_path(str(item.get('rootRenameTo') or ''))
    if not root_from or not root_to or root_from == root_to:
        return False
    return normalize_openlist_path(src) != normalize_openlist_path(target)


def _output_maps(stdout, stderr):
    outputs = {}
    for match in MEDIA_OUTPUT_RE.finditer(stdout or ''):
        status = match.group('status')
        src = normalize_openlist_path(match.group('src'))
        target = normalize_openlist_path(match.group('target'))
        if status.startswith('timing') or status == 'root-renamed':
            continue
        outputs[(src, target)] = {
            'status': _task_item_status(status),
            'errMsg': '',
            'rawStatus': status,
        }
    for match in MEDIA_ERROR_RE.finditer(stderr or ''):
        src = normalize_openlist_path(match.group('src'))
        target = normalize_openlist_path(match.group('target'))
        outputs[(src, target)] = {
            'status': 7,
            'errMsg': match.group('error'),
            'rawStatus': 'error',
        }
    return outputs


def _preview_items_from_req(req):
    items = req.get('plans')
    return items if isinstance(items, list) else []


def _mark_duplicate_targets(items):
    target_counts = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        target = normalize_openlist_path(str(item.get('targetPath') or ''))
        if not target:
            continue
        target_counts[target] = target_counts.get(target, 0) + 1
    duplicate_count = 0
    for item in items or []:
        if not isinstance(item, dict):
            continue
        target = normalize_openlist_path(str(item.get('targetPath') or ''))
        count = target_counts.get(target, 0)
        item['duplicateTarget'] = count > 1
        item['targetConflictCount'] = count if count > 1 else 0
        if count > 1:
            duplicate_count += 1
    return duplicate_count


def _target_before_root_rename(item, target):
    root_from = normalize_openlist_path(str(item.get('rootRenameFrom') or '')) if isinstance(item, dict) else ''
    root_to = normalize_openlist_path(str(item.get('rootRenameTo') or '')) if isinstance(item, dict) else ''
    target = normalize_openlist_path(str(target or ''))
    if not root_from or not root_to:
        return target
    if target == root_to:
        return root_from
    if target.startswith(root_to + '/'):
        return root_from + target[len(root_to):]
    return target


def _root_rename_rows(task_id, preview_items, status=0, err_msg=''):
    rows = []
    for item in _root_renames_from_preview_items(preview_items):
        src = item['from']
        target = item['to']
        preview_item = next((
            row for row in preview_items or []
            if isinstance(row, dict)
            and normalize_openlist_path(str(row.get('rootRenameFrom') or '')) == src
            and normalize_openlist_path(str(row.get('rootRenameTo') or '')) == target
        ), {})
        rows.append({
            'taskId': task_id,
            'srcPath': src,
            'targetPath': target,
            'status': status,
            'title': str(preview_item.get('title') or ''),
            'year': str(preview_item.get('year') or ''),
            'season': '',
            'episode': '',
            'errMsg': err_msg,
        })
    return rows


def _drop_nested_root_renames(items):
    return [
        item for item in items
        if not any(
            item['from'] != other['from'] and item['from'].startswith(other['from'] + '/')
            for other in items
        )
    ]


def _root_renames_from_preview_items(preview_items):
    items = []
    seen = set()
    for item in preview_items or []:
        if not isinstance(item, dict):
            continue
        src = normalize_openlist_path(str(item.get('rootRenameFrom') or ''))
        target = normalize_openlist_path(str(item.get('rootRenameTo') or ''))
        if not src or not target or src == target or (src, target) in seen:
            continue
        seen.add((src, target))
        items.append({'from': src, 'to': target})
    return _drop_nested_root_renames(items)


def _planned_item_count(preview_items):
    return len([item for item in preview_items if isinstance(item, dict)]) + len(_root_rename_rows(0, preview_items))


def _build_task_items(task_id, preview_items, stdout, stderr):
    output_map = _output_maps(stdout, stderr)
    root_output = {
        (item['from'], item['to'])
        for item in _extract_root_renames(stdout)
    }
    rows = []
    used_keys = set()
    for item in preview_items:
        if not isinstance(item, dict):
            continue
        src = normalize_openlist_path(str(item.get('srcPath') or ''))
        target = normalize_openlist_path(str(item.get('targetPath') or ''))
        key = (src, target)
        output_key = (src, _target_before_root_rename(item, target))
        result = output_map.get(key) or output_map.get(output_key)
        if result:
            used_keys.add(key)
            used_keys.add(output_key)
            if _is_root_follow_skip(item, src, target, result):
                root_pair = (
                    normalize_openlist_path(str(item.get('rootRenameFrom') or '')),
                    normalize_openlist_path(str(item.get('rootRenameTo') or '')),
                )
                if root_pair in root_output:
                    result = {'status': 2, 'errMsg': '', 'rawStatus': 'renamed by root rename'}
                else:
                    result = {'status': 0, 'errMsg': G('media_root_rename_pending'), 'rawStatus': ''}
        elif src == target:
            result = {'status': 3, 'errMsg': '', 'rawStatus': 'skip: already named'}
        else:
            result = {'status': 0, 'errMsg': '', 'rawStatus': ''}
        rows.append({
            'taskId': task_id,
            'srcPath': src,
            'targetPath': target,
            'status': result['status'],
            'title': str(item.get('title') or ''),
            'year': str(item.get('year') or ''),
            'season': str(item.get('season') or ''),
            'episode': str(item.get('episode') or ''),
            'errMsg': result.get('errMsg') or result.get('rawStatus') or '',
        })
    for (src, target), result in output_map.items():
        if (src, target) in used_keys:
            continue
        rows.append({
            'taskId': task_id,
            'srcPath': src,
            'targetPath': target,
            'status': result['status'],
            'title': '',
            'year': '',
            'season': '',
            'episode': '',
            'errMsg': result.get('errMsg') or result.get('rawStatus') or '',
        })
    for row in _root_rename_rows(task_id, preview_items):
        if (row['srcPath'], row['targetPath']) in root_output:
            row['status'] = 2
        rows.append(row)
    return rows


def _task_name_from_items(items, path):
    for item in items or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get('title') or '').strip()
        year = str(item.get('year') or '').strip()
        if title and year:
            return f"{title} ({year})"
        if title:
            return title
    for item in items or []:
        if not isinstance(item, dict):
            continue
        target_path = normalize_openlist_path(str(item.get('targetPath') or ''))
        for part in target_path.split('/'):
            if MEDIA_NAME_SEGMENT_RE.match(part):
                return part
    parts = normalize_openlist_path(str(path or '')).split('/')
    return parts[-1] if parts and parts[-1] else normalize_openlist_path(str(path or '/'))


def _parent_path(path):
    parts = normalize_openlist_path(str(path or '/')).split('/')
    parts = [part for part in parts if part]
    if not parts:
        return '/'
    parts.pop()
    return '/' + '/'.join(parts) if parts else '/'


def _task_group_path(path, task_name):
    task_name = str(task_name or '').strip()
    if not task_name:
        return normalize_openlist_path(str(path or '/'))
    return join_openlist_path(_parent_path(path), task_name)


def _task_group_key(openlist_id, path, task_name):
    return f"{openlist_id or 0}:{_task_group_path(path, task_name)}"


def _task_request(req, config):
    request = {
        key: value for key, value in (req or {}).items()
        if key not in ('__user', '__lang')
    }
    request['config'] = config
    request['apply'] = _to_bool(request.get('apply'), True)
    return request


def _root_rename_display_path(root_renames, fallback_path):
    if isinstance(root_renames, str):
        try:
            root_renames = json.loads(root_renames or '[]')
        except json.JSONDecodeError:
            root_renames = []
    if isinstance(root_renames, list):
        for item in reversed(root_renames):
            if not isinstance(item, dict):
                continue
            src = normalize_openlist_path(str(item.get('from') or ''))
            target = normalize_openlist_path(str(item.get('to') or ''))
            if src and target and src != target:
                return f"{src}=>{target}"
    return normalize_openlist_path(str(fallback_path or '/'))


def _root_rename_display_name(root_renames, fallback_name=''):
    if isinstance(root_renames, str):
        try:
            root_renames = json.loads(root_renames or '[]')
        except json.JSONDecodeError:
            root_renames = []
    if isinstance(root_renames, list):
        for item in reversed(root_renames):
            if not isinstance(item, dict):
                continue
            target = normalize_openlist_path(str(item.get('to') or ''))
            if target and target != '/':
                return target.rstrip('/').split('/')[-1]
    return str(fallback_name or '').strip()


def _root_renames_from_task_request(request):
    if isinstance(request, str):
        try:
            request = json.loads(request or '{}')
        except json.JSONDecodeError:
            request = {}
    if not isinstance(request, dict):
        return []
    return _root_renames_from_preview_items(request.get('plans'))


def _root_renames_from_task(task):
    if not task:
        return []
    try:
        root_renames = json.loads(task.get('rootRenames') or '[]')
    except json.JSONDecodeError:
        root_renames = []
    if isinstance(root_renames, list) and root_renames:
        return root_renames
    return _root_renames_from_task_request(task.get('request'))


def _latest_task_with_root_rename_hints(job_id):
    return mediaScrapingMapper.getLatestTaskWithRootRenameHintsByJobId(job_id)


def _attach_task_display_path(task):
    if not task:
        return task
    item = dict(task)
    root_renames = _root_renames_from_task(item)
    item['displayPath'] = _root_rename_display_path(root_renames, item.get('path'))
    item['displayTaskName'] = _root_rename_display_name(root_renames, item.get('taskName'))
    return item


def _attach_job_display_path(job):
    if not job:
        return job
    item = dict(job)
    root_task = _latest_task_with_root_rename_hints(item.get('id'))
    root_renames = _root_renames_from_task(root_task) if root_task else _root_renames_from_task_request(item.get('request'))
    item['displayPath'] = _root_rename_display_path(
        root_renames,
        item.get('path'),
    )
    item['displayTaskName'] = _root_rename_display_name(
        root_renames,
        item.get('taskName'),
    )
    return item


def _root_rename_target(task, path):
    path = normalize_openlist_path(str(path or ''))
    if not task or not path:
        return ''
    root_renames = _root_renames_from_task(task)
    if not isinstance(root_renames, list):
        return ''
    for item in reversed(root_renames):
        if not isinstance(item, dict):
            continue
        src = normalize_openlist_path(str(item.get('from') or ''))
        target = normalize_openlist_path(str(item.get('to') or ''))
        if not src or not target:
            continue
        if path == src:
            return target
        if path.startswith(src + '/'):
            return target + path[len(src):]
    return ''


def _root_rename_path_pair(task, path):
    path = normalize_openlist_path(str(path or ''))
    if not task or not path:
        return '', ''
    root_renames = _root_renames_from_task(task)
    if not isinstance(root_renames, list):
        return '', ''
    for item in reversed(root_renames):
        if not isinstance(item, dict):
            continue
        src = normalize_openlist_path(str(item.get('from') or ''))
        target = normalize_openlist_path(str(item.get('to') or ''))
        if not src or not target:
            continue
        if path == src:
            return src, target
        if path.startswith(src + '/'):
            suffix = path[len(src):]
            return path, target + suffix
        if path == target:
            return src, target
        if path.startswith(target + '/'):
            suffix = path[len(target):]
            return src + suffix, path
    return '', ''


def _is_openlist_missing_error(exc):
    message = str(exc).lower()
    return (
        'not found' in message
        or 'object not found' in message
        or 'no such' in message
        or '不存在' in message
        or '已删除' in message
        or '20018' in message
        or '430004' in message
    )


def _openlist_path_exists(openlist_id, path, refresh=False):
    path = normalize_openlist_path(str(path or ''))
    if not path or path == '/':
        return True
    try:
        client = openlistService.getClientById(openlist_id)
        if refresh:
            parent = _parent_openlist_path(path)
            client.post('/api/fs/list', data={'path': parent, 'refresh': True})
        client.post('/api/fs/get', data={'path': path})
        return True
    except Exception as exc:
        if _is_openlist_missing_error(exc):
            return False
        raise


def _parent_openlist_path(path):
    path = normalize_openlist_path(str(path or ''))
    if not path or path == '/':
        return '/'
    parent = normalize_openlist_path(posixpath.dirname(path))
    return parent or '/'


def _refresh_openlist_paths(openlist_id, paths):
    seen = set()
    for path in paths or []:
        path = normalize_openlist_path(str(path or ''))
        if not path or path in seen:
            continue
        seen.add(path)
        _openlist_path_exists(openlist_id, path, refresh=True)


def _prepare_rerun_request(task_req, fallback_path='', latest_task=None, openlist_id=None):
    task_req = dict(task_req or {})
    old_path = normalize_openlist_path(str(task_req.get('path') or fallback_path or ''))
    source_path, target_path = _root_rename_path_pair(latest_task, old_path)
    path = target_path or _root_rename_target(latest_task, old_path) or normalize_openlist_path(str(fallback_path or old_path or ''))
    if openlist_id and source_path and target_path:
        _refresh_openlist_paths(openlist_id, [
            _parent_openlist_path(source_path),
            _parent_openlist_path(target_path),
        ])
        source_exists = _openlist_path_exists(openlist_id, source_path, refresh=True)
        target_exists = _openlist_path_exists(openlist_id, target_path, refresh=True)
        if source_exists:
            path = source_path
        elif target_exists:
            path = target_path
    task_req.pop('action', None)
    task_req.pop('plans', None)
    task_req['path'] = path
    task_req['apply'] = True

    config = task_req.get('config')
    if isinstance(config, dict):
        config = dict(config)
        rules = config.get('rules')
        if isinstance(rules, list) and rules:
            updated_rules = []
            matched = False
            replace_paths = {old_path}
            if source_path:
                replace_paths.add(source_path)
            if target_path:
                replace_paths.add(target_path)
            for rule in rules:
                if not isinstance(rule, dict):
                    updated_rules.append(rule)
                    continue
                updated_rule = dict(rule)
                rule_path = normalize_openlist_path(str(updated_rule.get('path') or ''))
                if not rule_path or rule_path in replace_paths:
                    updated_rule['path'] = path
                    matched = True
                updated_rules.append(updated_rule)
            if not matched and isinstance(updated_rules[0], dict):
                updated_rules[0]['path'] = path
            config['rules'] = updated_rules
        task_req['config'] = config
    return task_req


def _new_task_row(req, config, openlist, preview_items, status=1):
    path = normalize_openlist_path(str(req.get('path') or ''))
    root_renames = _root_renames_from_preview_items(preview_items)
    task_name = _task_name_from_items(preview_items, path)
    task_name = _root_rename_display_name(root_renames, task_name)
    success_num = 0
    fail_num = 0
    skip_num = len([item for item in preview_items if isinstance(item, dict) and item.get('srcPath') == item.get('targetPath')])
    total = _planned_item_count(preview_items)
    return {
        'jobId': req.get('jobId'),
        'taskName': task_name,
        'path': path,
        'openlistId': openlist.get('id') if openlist else None,
        'openlistName': (openlist.get('remark') or openlist.get('url')) if openlist else '',
        'status': status,
        'apply': 1 if _to_bool(req.get('apply'), True) else 0,
        'usedPreviewPlans': 1 if preview_items else 0,
        'total': total or _to_int(req.get('limit'), config.get('limit', 0), 0),
        'changed': len([item for item in preview_items if isinstance(item, dict) and item.get('srcPath') != item.get('targetPath')]) + len(_root_rename_rows(0, preview_items)),
        'successNum': success_num,
        'failNum': fail_num,
        'skipNum': skip_num,
        'elapsed': 0,
        'rootRenames': json.dumps(root_renames, ensure_ascii=False),
        'stdout': '',
        'stderr': '',
        'errMsg': '',
        'request': json.dumps(_task_request(req, config), ensure_ascii=False),
        'updateTime': int(time.time()),
    }


def _job_row_from_task(task, config=None):
    task_name = _root_rename_display_name(_root_renames_from_task(task), task.get('taskName'))
    task_name = str(task_name or _task_name_from_items([], task.get('path')) or '').strip()
    path = normalize_openlist_path(str(task.get('path') or ''))
    openlist_id = _to_int(task.get('openlistId'), 0, 0)
    return {
        'id': task.get('jobId'),
        'groupKey': _task_group_key(openlist_id, path, task_name),
        'taskName': task_name,
        'path': _task_group_path(path, task_name),
        'openlistId': openlist_id or None,
        'openlistName': task.get('openlistName') or '',
        'request': task.get('request') or json.dumps(_task_request({'path': path}, config or getConfig()), ensure_ascii=False),
        'latestTaskId': task.get('id'),
        'status': task.get('status') or 0,
        'total': task.get('total') or 0,
        'changed': task.get('changed') or 0,
        'successNum': task.get('successNum') or 0,
        'failNum': task.get('failNum') or 0,
        'skipNum': task.get('skipNum') or 0,
        'elapsed': task.get('elapsed') or 0,
        'updateTime': int(time.time()),
    }


def _ensure_job_for_task(task, config=None):
    job_row = _job_row_from_task(task, config)
    if task.get('jobId'):
        job = mediaScrapingMapper.getJobById(task['jobId'])
        if job:
            if job.get('groupKey') == job_row['groupKey']:
                return job['id']
            existing = mediaScrapingMapper.getJobByGroupKey(job_row['groupKey'])
            if existing:
                mediaScrapingMapper.updateTaskJobId(task['id'], existing['id'])
                if mediaScrapingMapper.countTasksByJobId(job['id']) == 0:
                    mediaScrapingMapper.deleteJobOnly(job['id'])
                return existing['id']
            job.update(job_row)
            job['id'] = task['jobId']
            mediaScrapingMapper.updateJob(job)
            return job['id']
    job = mediaScrapingMapper.getJobByGroupKey(job_row['groupKey'])
    if job:
        job_id = job['id']
        job.update(job_row)
        job['id'] = job_id
        mediaScrapingMapper.updateJob(job)
        mediaScrapingMapper.updateTaskJobId(task['id'], job_id)
        return job_id
    job_id = mediaScrapingMapper.addJob(job_row)
    mediaScrapingMapper.updateTaskJobId(task['id'], job_id)
    return job_id


def _ensure_legacy_jobs():
    for task in mediaScrapingMapper.getTasksWithoutJob():
        _ensure_job_for_task(task)


def _touch_job_from_task(task_id):
    task = mediaScrapingMapper.getTaskById(task_id)
    if not task:
        return
    job_id = _ensure_job_for_task(task)
    task['jobId'] = job_id
    job = mediaScrapingMapper.getJobById(job_id)
    if not job:
        return
    job.update(_job_row_from_task(task))
    job['id'] = job_id
    mediaScrapingMapper.updateJob(job)


def _initial_task_items(task_id, preview_items):
    rows = []
    for item in preview_items:
        if not isinstance(item, dict):
            continue
        rows.append({
            'taskId': task_id,
            'srcPath': normalize_openlist_path(str(item.get('srcPath') or '')),
            'targetPath': normalize_openlist_path(str(item.get('targetPath') or '')),
            'status': 0,
            'title': str(item.get('title') or ''),
            'year': str(item.get('year') or ''),
            'season': str(item.get('season') or ''),
            'episode': str(item.get('episode') or ''),
            'errMsg': G('media_duplicate_target') if item.get('duplicateTarget') else '',
        })
    rows.extend(_root_rename_rows(task_id, preview_items))
    return rows


def _prepare_task_preview_items(task_id, req, config):
    if _preview_items_from_req(req):
        return req
    preview_config = {
        **config,
        'refresh': True,
    }
    preview = previewNaming({
        **req,
        'config': preview_config,
    })
    preview_items = preview.get('items') if isinstance(preview, dict) else []
    if not preview_items:
        return req
    req = {
        **req,
        'plans': preview_items,
        'openlistId': preview.get('openlistId') or req.get('openlistId'),
    }
    root_renames = _root_renames_from_preview_items(preview_items)
    task = mediaScrapingMapper.getTaskById(task_id)
    if task:
        task.update({
            'taskName': _root_rename_display_name(
                root_renames,
                _task_name_from_items(preview_items, req.get('path')),
            ),
            'usedPreviewPlans': 1,
            'total': _planned_item_count(preview_items),
            'changed': len([
                item for item in preview_items
                if isinstance(item, dict) and item.get('srcPath') != item.get('targetPath')
            ]) + len(_root_rename_rows(0, preview_items)),
            'skipNum': len([
                item for item in preview_items
                if isinstance(item, dict) and item.get('srcPath') == item.get('targetPath')
            ]),
            'rootRenames': json.dumps(root_renames, ensure_ascii=False),
            'request': json.dumps(_task_request(req, preview_config), ensure_ascii=False),
            'updateTime': int(time.time()),
        })
        mediaScrapingMapper.updateTask(task)
        mediaScrapingMapper.deleteTaskItems(task_id)
        mediaScrapingMapper.addTaskItems(_initial_task_items(task_id, preview_items))
        _touch_job_from_task(task_id)
    return req


def _status_from_counts(success, success_num, fail_num, skip_num):
    if fail_num > 0 and (success_num > 0 or skip_num > 0):
        return 3
    return 2 if success else 6


def _record_run_tasks(req, config, result, elapsed):
    if not isinstance(result, dict):
        return
    preview_items = _preview_items_from_req(req)
    path = normalize_openlist_path(str(req.get('path') or ''))
    apply = _to_bool(result.get('apply'), _to_bool(req.get('apply'), False))
    used_preview_plans = _to_bool(result.get('usedPreviewPlans'), False)
    for item in result.get('results') or []:
        if not isinstance(item, dict):
            continue
        stdout = item.get('stdout') or ''
        stderr = item.get('stderr') or ''
        task_items_for_count = _build_task_items(0, preview_items, stdout, stderr)
        success_num = len([row for row in task_items_for_count if row['status'] == 2])
        fail_num = len([row for row in task_items_for_count if row['status'] == 7])
        skip_num = len([row for row in task_items_for_count if row['status'] == 3])
        status = _status_from_counts(item.get('success'), success_num, fail_num, skip_num)
        task_payload = {
            'jobId': None,
            'taskName': _root_rename_display_name(
                item.get('rootRenames') or [],
                _task_name_from_items(task_items_for_count or preview_items, path),
            ),
            'path': path,
            'openlistId': item.get('openlistId'),
            'openlistName': item.get('openlistName') or '',
            'status': status,
            'apply': 1 if apply else 0,
            'usedPreviewPlans': 1 if used_preview_plans else 0,
            'total': len(task_items_for_count) or _to_int(result.get('limit'), 0, 0),
            'changed': success_num,
            'successNum': success_num,
            'failNum': fail_num,
            'skipNum': skip_num,
            'elapsed': elapsed,
            'rootRenames': json.dumps(item.get('rootRenames') or [], ensure_ascii=False),
            'stdout': stdout[-20000:],
            'stderr': stderr[-20000:],
            'errMsg': item.get('error') or '',
            'request': json.dumps(_task_request(req, config), ensure_ascii=False),
            'updateTime': int(time.time()),
        }
        job_row = _job_row_from_task(task_payload, config)
        job = mediaScrapingMapper.getJobByGroupKey(job_row['groupKey'])
        task_payload['jobId'] = job['id'] if job else mediaScrapingMapper.addJob(job_row)
        task_id = mediaScrapingMapper.addTask(task_payload)
        _touch_job_from_task(task_id)
        rows = _build_task_items(task_id, preview_items, stdout, stderr)
        mediaScrapingMapper.addTaskItems(rows)
    mediaScrapingMapper.pruneTasks(config.get('renameLogLimit') or 0)


def _update_run_task(task_id, req, config, result, elapsed, aborted=False):
    task = mediaScrapingMapper.getTaskById(task_id)
    if not task:
        return
    preview_items = _preview_items_from_req(req)
    item = (result.get('results') or [{}])[0] if isinstance(result, dict) else {}
    stdout = item.get('stdout') or ''
    stderr = item.get('stderr') or ''
    rows = _build_task_items(task_id, preview_items, stdout, stderr)
    if item.get('error'):
        for row in rows:
            if row['status'] in (0, 1):
                row['status'] = 7
                row['errMsg'] = item.get('error')
    if aborted:
        for row in rows:
            if row['status'] in (0, 1):
                row['status'] = 7
                row['errMsg'] = G('media_task_aborted')
    success_num = len([row for row in rows if row['status'] == 2])
    fail_num = len([row for row in rows if row['status'] == 7])
    skip_num = len([row for row in rows if row['status'] == 3])
    success = bool(result.get('success')) if isinstance(result, dict) else False
    status = 4 if aborted else _status_from_counts(success, success_num, fail_num, skip_num)
    task.update({
        'taskName': _root_rename_display_name(
            result.get('rootRenames') if isinstance(result, dict) else [],
            _task_name_from_items(rows or preview_items, req.get('path')),
        ),
        'path': normalize_openlist_path(str(req.get('path') or task.get('path') or '')),
        'openlistId': item.get('openlistId') or task.get('openlistId'),
        'openlistName': item.get('openlistName') or task.get('openlistName') or '',
        'status': status,
        'apply': 1 if _to_bool(result.get('apply') if isinstance(result, dict) else None, _to_bool(req.get('apply'), True)) else 0,
        'usedPreviewPlans': 1 if _to_bool(result.get('usedPreviewPlans') if isinstance(result, dict) else None, bool(preview_items)) else 0,
        'total': len(rows) or _planned_item_count(preview_items) or task.get('total') or _to_int(result.get('limit') if isinstance(result, dict) else 0, 0, 0),
        'changed': success_num,
        'successNum': success_num,
        'failNum': fail_num,
        'skipNum': skip_num,
        'elapsed': elapsed,
        'rootRenames': json.dumps(result.get('rootRenames') if isinstance(result, dict) else [], ensure_ascii=False),
        'stdout': stdout[-20000:],
        'stderr': stderr[-20000:],
        'errMsg': G('media_task_aborted') if aborted else item.get('error') or '',
        'request': task.get('request') or json.dumps(_task_request(req, config), ensure_ascii=False),
        'updateTime': int(time.time()),
    })
    mediaScrapingMapper.updateTask(task)
    mediaScrapingMapper.deleteTaskItems(task_id)
    mediaScrapingMapper.addTaskItems(rows)
    _touch_job_from_task(task_id)
    mediaScrapingMapper.pruneTasks(config.get('renameLogLimit') or 0)
    return task


def _run_task_background(task_id, req, abort_event=None, request_lang=None):
    if request_lang:
        set_context_lang(request_lang)
    started = time.perf_counter()
    config = _normalize_config(req.get('config') or getConfig())
    progress_lock = threading.Lock()

    def progress_callback(index, plan, status, target_path, error=None):
        with progress_lock:
            status_code, err_msg = _progress_status(status, error)
            if (
                status == 'skip: already named'
                and getattr(plan, 'root_rename_from', '')
                and getattr(plan, 'root_rename_to', '')
                and normalize_openlist_path(plan.src_path) != normalize_openlist_path(plan.target_path)
            ):
                status_code = 0
                err_msg = G('media_root_rename_pending')
            mediaScrapingMapper.updateTaskItemStatus(
                task_id,
                normalize_openlist_path(plan.src_path),
                status_code,
                err_msg,
            )

    def root_progress_callback(src_path, target_path, status, error=None):
        with progress_lock:
            status_code, err_msg = _progress_status(status, error)
            mediaScrapingMapper.updateTaskItemStatus(
                task_id,
                normalize_openlist_path(src_path),
                status_code,
                err_msg,
                normalize_openlist_path(target_path),
            )

    try:
        req = _prepare_task_preview_items(task_id, req, config)
        if abort_event and abort_event.is_set():
            raise InterruptedError('aborted')
        result = runScraping(req, abort_event, progress_callback, root_progress_callback)
        elapsed = time.perf_counter() - started
        task = _update_run_task(task_id, req, config, result, elapsed, bool(abort_event and abort_event.is_set()))
        _send_task_notify(task)
        _log_run_result('run', str(req.get('path') or ''), elapsed, result)
    except Exception as e:
        elapsed = time.perf_counter() - started
        aborted = bool(abort_event and abort_event.is_set())
        task = mediaScrapingMapper.getTaskById(task_id)
        if task:
            mediaScrapingMapper.updateTaskItemsStatus(task_id, 7)
            stats = mediaScrapingMapper.getTaskItemStats(task_id)
            success_num = stats.get(2, task.get('successNum') or 0)
            fail_num = stats.get(7, task.get('failNum') or 0)
            skip_num = stats.get(3, task.get('skipNum') or 0)
            task.update({
                'status': 4 if aborted else 6,
                'successNum': success_num,
                'failNum': fail_num,
                'skipNum': skip_num,
                'total': max(_to_int(task.get('total'), 0, 0), success_num + fail_num + skip_num),
                'elapsed': elapsed,
                'errMsg': G('media_task_aborted') if aborted else str(e),
                'updateTime': int(time.time()),
            })
            mediaScrapingMapper.updateTask(task)
            _touch_job_from_task(task_id)
            _send_task_notify(task, task['status'], task['errMsg'])
        logging.getLogger().exception(e)
    finally:
        with MEDIA_ABORT_LOCK:
            MEDIA_ABORT_EVENTS.pop(task_id, None)


def startRunTask(req):
    request_lang = req.get('__lang')
    config = _normalize_config(req.get('config') or getConfig())
    openlist_id = _selected_openlist_id(req, config)
    openlist = openlistMapper.getOpenlistById(openlist_id)
    preview_items = _preview_items_from_req(req)
    task_req = _task_request(req, config)
    task_req['openlistId'] = openlist_id
    task_row = _new_task_row(task_req, config, openlist, preview_items)
    if not preview_items and task_req.get('jobId'):
        root_task = _latest_task_with_root_rename_hints(task_req['jobId'])
        _, target_path = _root_rename_path_pair(root_task, task_row.get('path'))
        if target_path:
            task_row['taskName'] = target_path.rstrip('/').split('/')[-1]
            task_row['rootRenames'] = json.dumps(_root_renames_from_task(root_task), ensure_ascii=False)
    job_row = _job_row_from_task(task_row, config)
    job = mediaScrapingMapper.getJobByGroupKey(job_row['groupKey'])
    if job:
        job_id = job['id']
    else:
        job_id = mediaScrapingMapper.addJob(job_row)
    task_req['jobId'] = job_id
    task_row['jobId'] = job_id
    task_id = mediaScrapingMapper.addTask(task_row)
    mediaScrapingMapper.addTaskItems(_initial_task_items(task_id, preview_items))
    _touch_job_from_task(task_id)
    abort_event = threading.Event()
    with MEDIA_ABORT_LOCK:
        MEDIA_ABORT_EVENTS[task_id] = abort_event
    threading.Thread(
        target=_run_task_background,
        args=(task_id, task_req, abort_event, request_lang),
        daemon=True,
    ).start()
    mediaScrapingMapper.pruneTasks(config.get('renameLogLimit') or 0)
    return {
        'jobId': job_id,
        'taskId': task_id,
        'status': 1,
        'taskName': _task_name_from_items(preview_items, task_req.get('path')),
    }


def getTaskList(req):
    _ensure_legacy_jobs()
    data = mediaScrapingMapper.getJobs(req)
    rows = data.get('list', data) if isinstance(data, dict) else data
    rows = [_attach_job_display_path(item) for item in rows]
    return {
        'taskList': rows,
        'count': data.get('count', len(data)) if isinstance(data, dict) else len(data)
    }


def getJobTasks(req):
    _ensure_legacy_jobs()
    job_id = _to_int(req.get('jobId') or req.get('id'), 0, 0)
    data = mediaScrapingMapper.getTaskList({
        **req,
        'jobId': job_id,
    })
    rows = data.get('list', data) if isinstance(data, dict) else data
    rows = [_attach_task_display_path(item) for item in rows]
    return {
        'taskList': rows,
        'count': data.get('count', len(data)) if isinstance(data, dict) else len(data)
    }


def getJobCurrent(req):
    _ensure_legacy_jobs()
    job_id = _to_int(req.get('jobId') or req.get('id'), 0, 0)
    task = mediaScrapingMapper.getRunningTaskByJobId(job_id)
    if not task:
        return None
    task = _attach_task_display_path(task)
    params = {
        'taskId': task['id'],
        'pageSize': _to_int(req.get('pageSize'), 10, 1),
        'pageNum': _to_int(req.get('pageNum'), 1, 1),
    }
    if req.get('status') is not None:
        params['status'] = req.get('status')
    data = mediaScrapingMapper.getTaskItems(params)
    return {
        'task': task,
        'summary': _task_summary(task),
        'taskItemList': data.get('list', data) if isinstance(data, dict) else data,
        'count': data.get('count', len(data)) if isinstance(data, dict) else len(data)
    }


def _task_summary(task):
    if not task:
        return {}
    stats = mediaScrapingMapper.getTaskItemStats(task['id'])
    success_num = stats.get(2, task.get('successNum') or 0)
    skip_num = stats.get(3, task.get('skipNum') or 0)
    fail_num = stats.get(7, task.get('failNum') or 0)
    running_num = stats.get(1, 0)
    wait_num = stats.get(0, 0)
    total = max(
        _to_int(task.get('total'), 0, 0),
        sum(stats.values()) if stats else 0,
    )
    finished = success_num + skip_num + fail_num
    status = _to_int(task.get('status'), 0, 0)
    if status == 1 and task.get('createTime'):
        elapsed = max(0, int(time.time()) - _to_int(task.get('createTime'), 0, 0))
    else:
        elapsed = int(float(task.get('elapsed') or 0))
    progress = 100 if status in (2, 3, 6) and total else 0
    if total:
        progress = min(100, round(finished * 100 / total, 2))
        if status in (2, 3, 6) and finished >= total:
            progress = 100
    remaining = None
    if status == 1 and finished > 0 and total > finished:
        remaining = int((elapsed / finished) * (total - finished))
    elif status != 1:
        remaining = 0
    return {
        'waitNum': wait_num,
        'runningNum': running_num,
        'successNum': success_num,
        'skipNum': skip_num,
        'failNum': fail_num,
        'allNum': total,
        'finishedNum': finished,
        'progress': progress,
        'elapsed': elapsed,
        'remaining': remaining,
    }


def _send_task_notify(task, status=None, err_msg=''):
    if not task:
        return
    notify_list = notifyService.getNotifyList(True)
    if not notify_list:
        return
    status = _to_int(status if status is not None else task.get('status'), 0, 0)
    status_names = G('task_status')
    status_name = status_names[status] if 0 <= status < len(status_names) else str(status)
    task_name = task.get('taskName') or _task_name_from_items([], task.get('path'))
    title = G('media_notify_title').format(status_name)
    hours, minutes, seconds = commonUtils.convertSeconds(int(float(task.get('elapsed') or 0)))
    duration_text = G('hms').format(hours, minutes, seconds)
    content = "\n".join([
        G('media_notify_task_name').format(task_name),
        G('media_notify_engine').format(task.get('openlistName') or task.get('openlistId') or '-'),
        G('media_notify_path').format(task.get('path') or '-'),
        G('media_notify_status').format(status_name),
        '',
        G('media_notify_counts').format(
            task.get('total') or 0,
            task.get('successNum') or 0,
            task.get('skipNum') or 0,
            task.get('failNum') or 0,
        ),
        '',
        G('media_notify_duration').format(duration_text),
    ])
    err_msg = err_msg or task.get('errMsg') or ''
    if err_msg:
        content += "\n" + G('media_notify_error').format(err_msg)
    logger = logging.getLogger()
    for notify in notify_list:
        try:
            notifyService.sendNotify(notify, title, content, False)
        except Exception as exc:
            logger.error(G('notify_error').format(str(exc)))


def getTaskItems(req):
    task = mediaScrapingMapper.getTaskById(_to_int(req.get('taskId'), 0, 0))
    task = _attach_task_display_path(task)
    params = {**req}
    if _to_bool(params.get('all'), False):
        params.pop('pageSize', None)
        params.pop('pageNum', None)
    data = mediaScrapingMapper.getTaskItems(params)
    return {
        'task': task,
        'summary': _task_summary(task),
        'taskItemList': data.get('list', data) if isinstance(data, dict) else data,
        'count': data.get('count', len(data)) if isinstance(data, dict) else len(data)
    }


def deleteTask(req):
    task_id = _to_int(req.get('taskId') or req.get('id'), 0, 0)
    task = mediaScrapingMapper.getTaskById(task_id)
    mediaScrapingMapper.deleteTask(task_id)
    if not task or not task.get('jobId'):
        return
    latest = mediaScrapingMapper.getLatestTaskByJobId(task['jobId'])
    if latest:
        _touch_job_from_task(latest['id'])
    else:
        mediaScrapingMapper.deleteJob(task['jobId'])


def deleteJob(req):
    mediaScrapingMapper.deleteJob(_to_int(req.get('jobId') or req.get('id'), 0, 0))


def rerunTask(req):
    request_lang = req.get('__lang')
    task_id = _to_int(req.get('taskId') or req.get('id'), 0, 0)
    task = mediaScrapingMapper.getTaskById(task_id)
    if not task:
        raise Exception(G('task_not_found'))
    task_req = None
    if task.get('request'):
        try:
            task_req = json.loads(task['request'])
        except json.JSONDecodeError:
            task_req = None
    if not isinstance(task_req, dict):
        task_req = {
            'apply': True,
            'path': task.get('path') or '',
            'config': getConfig()
        }
    if task.get('jobId'):
        task_req['jobId'] = task['jobId']
    openlist_id = _to_int(task_req.get('openlistId') or task.get('openlistId'), 0, 0)
    root_task = task
    if task.get('jobId') and not task.get('rootRenames'):
        root_task = _latest_task_with_root_rename_hints(task['jobId']) or task
    task_req = _prepare_rerun_request(task_req, task.get('path') or '', root_task, openlist_id)
    if request_lang:
        task_req['__lang'] = request_lang
    return startRunTask(task_req)


def rerunJob(req):
    request_lang = req.get('__lang')
    _ensure_legacy_jobs()
    job_id = _to_int(req.get('jobId') or req.get('id'), 0, 0)
    job = mediaScrapingMapper.getJobById(job_id)
    if not job:
        raise Exception(G('task_not_found'))
    task_req = None
    if job.get('request'):
        try:
            task_req = json.loads(job['request'])
        except json.JSONDecodeError:
            task_req = None
    if not isinstance(task_req, dict):
        task_req = {
            'apply': True,
            'path': job.get('path') or '',
            'openlistId': job.get('openlistId'),
            'config': getConfig()
        }
    latest_task = (
        _latest_task_with_root_rename_hints(job_id)
        or mediaScrapingMapper.getLatestTaskByJobId(job_id)
    )
    openlist_id = _to_int(task_req.get('openlistId') or job.get('openlistId'), 0, 0)
    task_req = _prepare_rerun_request(task_req, job.get('path') or '', latest_task, openlist_id)
    task_req['jobId'] = job_id
    if request_lang:
        task_req['__lang'] = request_lang
    return startRunTask(task_req)


def abortTask(req):
    task_id = _to_int(req.get('taskId') or req.get('id'), 0, 0)
    task = mediaScrapingMapper.getTaskById(task_id)
    if not task or _to_int(task.get('status'), 0, 0) != 1:
        raise Exception(G('media_no_running_task'))
    with MEDIA_ABORT_LOCK:
        event = MEDIA_ABORT_EVENTS.get(task_id)
        if event:
            event.set()
    task['status'] = 4
    task['errMsg'] = G('media_task_aborted')
    task['updateTime'] = int(time.time())
    mediaScrapingMapper.updateTask(task)
    mediaScrapingMapper.updateTaskItemsStatus(task_id, 7)
    _touch_job_from_task(task_id)
    return {}


def abortJob(req):
    _ensure_legacy_jobs()
    job_id = _to_int(req.get('jobId') or req.get('id'), 0, 0)
    task = mediaScrapingMapper.getRunningTaskByJobId(job_id)
    if not task:
        raise Exception(G('media_no_running_task'))
    return abortTask({'taskId': task['id']})


def getConfig():
    raw = systemConfigMapper.getConfigValue(MEDIA_SCRAPING_CONFIG_KEY)
    if not raw:
        return _default_config()
    try:
        config = json.loads(raw)
    except json.JSONDecodeError:
        return _default_config()
    return _normalize_config(config)


def updateConfig(req):
    config = _normalize_config(req)
    systemConfigMapper.setConfigValue(MEDIA_SCRAPING_CONFIG_KEY, json.dumps(config, ensure_ascii=False))
    return config


def _build_runner_config(config, openlist):
    rules = []
    for rule in config['rules']:
        item = {
            'path': rule['path'],
            'type': rule['type'],
            'recursive': rule['recursive'],
            'extensions': rule['extensions'] or config['mediaExtensions'],
            'tmdbId': rule.get('tmdbId') or 0,
            'seasonNumber': rule.get('seasonNumber')
        }
        rules.append(item)

    return {
        'openlist': {
            'base_url': openlist['url'],
            'token': openlist['token'],
            'username': '',
            'password': '',
            'otp_code': '',
            'timeout': config['openlistTimeout'],
        },
        'tmdb': {
            'api_key': config['tmdbApiKey'],
            'bearer_token': config['tmdbBearerToken'],
            'language': config['tmdbLanguage'],
            'include_adult': config['tmdbIncludeAdult'],
            'required': config['tmdbRequired'],
            'timeout': config['tmdbTimeout'],
        },
        'dry_run': config['dryRun'],
        'overwrite': config['overwrite'],
        'refresh': config['refresh'],
        'rename_threads': config['renameThreads'],
        'templates': {
            'movie': config['movieTemplate'],
            'tv': config['tvTemplate'],
        },
        'moviepilot': {
            'custom_words': _line_list(config['customWords']),
            'custom_release_groups': _line_list(config['customReleaseGroups']),
            'customization': _line_list(config['customization']),
        },
        'rules': rules,
    }


def _selected_openlist_id(req, config):
    openlist_id = _to_int(req.get('openlistId'), 0, 0)
    if not openlist_id:
        openlist_id = _to_int(config.get('defaultOpenlistId'), 0, 0)
    if not openlist_id:
        raise Exception(G('media_default_engine_required'))
    return openlist_id


def browsePath(req):
    config = _normalize_config(req.get('config') or getConfig())
    openlist_id = _selected_openlist_id(req, config)
    path = normalize_openlist_path(str(req.get('path') or '/'))
    refresh = _to_bool(req.get('refresh'), False)
    client = openlistService.getClientById(openlist_id)
    data = client.post('/api/fs/list', data={
        'path': path,
        'refresh': refresh
    })
    content = data.get('content') or []
    items = []
    for item in content:
        name = item.get('name')
        if not name:
            continue
        is_dir = bool(item.get('is_dir'))
        items.append({
            'name': name,
            'path': join_openlist_path(path, name),
            'isDir': is_dir,
            'size': item.get('size'),
            'modified': item.get('modified'),
            'sign': item.get('sign')
        })
    items.sort(key=lambda row: (not row['isDir'], row['name'].lower()))
    return {
        'openlistId': openlist_id,
        'path': path,
        'items': items
    }


def previewNaming(req):
    config = _normalize_config(req.get('config') or getConfig())
    openlist_id = _selected_openlist_id(req, config)
    path = normalize_openlist_path(str(req.get('path') or ''))
    if path == '/':
        raise Exception(G('media_preview_path_required'))
    media_type = str(req.get('type') or 'auto').lower()
    if media_type not in {'auto', 'movie', 'tv'}:
        media_type = 'auto'
    recursive = _to_bool(req.get('recursive'), True)
    limit = _to_int(req.get('limit'), config['limit'], 0)
    preview_limit = _to_int(req.get('previewLimit'), limit, 0)
    tmdb_id = _optional_int(req, 'tmdbId', 'tmdb_id') or 0
    season_number = _optional_int(req, 'seasonNumber', 'season')
    if tmdb_id and media_type == 'auto' and season_number is not None:
        media_type = 'tv'

    openlist = openlistMapper.getOpenlistById(openlist_id)
    runner_config = _build_runner_config({
        **config,
        'rules': [{
            'path': path,
            'type': media_type,
            'recursive': recursive,
            'extensions': config['mediaExtensions'],
            'tmdbId': tmdb_id,
            'seasonNumber': season_number
        }]
    }, openlist)
    client = build_client(runner_config)
    client.login()
    tmdb_client = build_tmdb_client(runner_config)
    if (runner_config.get('tmdb') or {}).get('required', True) and not tmdb_client.enabled():
        raise TMDbError(G('media_tmdb_config_required'))

    extensions = {ext.lower() for ext in config['mediaExtensions']}
    scan_limit = preview_limit + 1 if preview_limit else 0
    files = collect_files(client, path, recursive, config['refresh'], extensions, scan_limit)
    limited = bool(preview_limit and len(files) > preview_limit)
    if limited:
        files = files[:preview_limit]

    plans = []
    root_renames = []
    seen_root = set()
    for file_path in files:
        plan = plan_for_file(
            file_path,
            path,
            media_type,
            tmdb_client,
            {
                'movie': config['movieTemplate'],
                'tv': config['tvTemplate']
            },
            {
                'custom_words': _line_list(config['customWords']),
                'custom_release_groups': _line_list(config['customReleaseGroups']),
                'customization': _line_list(config['customization']),
            },
            tmdb_id,
            season_number
        )
        if plan.root_rename_from and plan.root_rename_to:
            pair = (plan.root_rename_from, plan.root_rename_to)
            if pair not in seen_root:
                seen_root.add(pair)
                root_renames.append({
                    'from': plan.root_rename_from,
                    'to': plan.root_rename_to
                })
        plans.append({
            'srcPath': plan.src_path,
            'effectiveSrcPath': plan.effective_src_path,
            'targetPath': plan.target_path,
            'changed': plan.effective_src_path != plan.target_path,
            'title': plan.info.title,
            'year': plan.info.year,
            'season': plan.info.season,
            'episode': plan.info.season_episode,
            'rootRenameFrom': plan.root_rename_from,
            'rootRenameTo': plan.root_rename_to
        })

    duplicate_targets = _mark_duplicate_targets(plans)
    return {
        'openlistId': openlist_id,
        'path': path,
        'type': media_type,
        'recursive': recursive,
        'tmdbId': tmdb_id,
        'seasonNumber': season_number,
        'total': len(plans),
        'changed': len([item for item in plans if item['changed']]),
        'previewLimit': preview_limit,
        'limited': limited,
        'duplicateTargets': duplicate_targets,
        'rootRenames': root_renames,
        'items': plans
    }


def searchTmdb(req):
    config = _normalize_config(req.get('config') or getConfig())
    query = str(req.get('query') or '').strip()
    if not query:
        raise Exception(G('media_search_required'))
    media_type = str(req.get('type') or 'auto').lower()
    if media_type not in {'auto', 'movie', 'tv'}:
        media_type = 'auto'
    page = _to_int(req.get('page'), 1, 1)

    runner_config = _build_runner_config({
        **config,
        'rules': []
    }, {'url': '', 'token': ''})
    tmdb_client = build_tmdb_client(runner_config)
    if not tmdb_client.enabled():
        raise TMDbError(G('media_tmdb_config_required'))

    if media_type == 'movie':
        endpoint = 'search/movie'
    elif media_type == 'tv':
        endpoint = 'search/tv'
    else:
        endpoint = 'search/multi'
    data = tmdb_client.request(endpoint, {
        'query': query,
        'include_adult': str(config['tmdbIncludeAdult']).lower(),
        'page': page
    })
    results = []
    for item in data.get('results') or []:
        if not isinstance(item, dict):
            continue
        result_type = item.get('media_type') or media_type
        if result_type not in {'movie', 'tv'}:
            continue
        title = item.get('title') if result_type == 'movie' else item.get('name')
        original_title = item.get('original_title') if result_type == 'movie' else item.get('original_name')
        date_value = item.get('release_date') if result_type == 'movie' else item.get('first_air_date')
        poster_path = item.get('poster_path') or ''
        results.append({
            'id': item.get('id'),
            'type': result_type,
            'typeText': '电影' if result_type == 'movie' else '电视剧',
            'title': title or original_title or '',
            'originalTitle': original_title or '',
            'year': str(date_value or '')[:4] if date_value else '',
            'date': date_value or '',
            'overview': item.get('overview') or '',
            'posterPath': poster_path,
            'posterUrl': f'https://image.tmdb.org/t/p/w185{poster_path}' if poster_path else '',
            'voteAverage': item.get('vote_average') or 0
        })
    return {
        'query': query,
        'type': media_type,
        'page': data.get('page') or page,
        'totalPages': data.get('total_pages') or 0,
        'totalResults': data.get('total_results') or len(results),
        'items': results
    }


def runScraping(req, abort_event=None, progress_callback=None, root_progress_callback=None):
    config = _normalize_config(req.get('config') or getConfig())
    preview_plans = _plans_from_preview(req.get('plans'))
    if preview_plans:
        return runScrapingWithPreviewPlans(req, config, preview_plans, abort_event, progress_callback, root_progress_callback)
    if not config['openlistIds']:
        raise Exception(G('media_engine_required'))
    if not config['rules']:
        path = str(req.get('path') or '').strip()
        if not path:
            raise Exception(G('media_path_required'))
        media_type = str(req.get('type') or 'auto').lower()
        if media_type not in {'auto', 'movie', 'tv'}:
            media_type = 'auto'
        season_number = _optional_int(req, 'seasonNumber', 'season')
        if media_type == 'auto' and season_number is not None:
            media_type = 'tv'
        config['rules'] = [{
            'path': normalize_openlist_path(path),
            'type': media_type,
            'recursive': _to_bool(req.get('recursive'), True),
            'extensions': config['mediaExtensions'],
            'tmdbId': _optional_int(req, 'tmdbId', 'tmdb_id') or 0,
            'seasonNumber': season_number
        }]

    apply = _to_bool(req.get('apply'), False)
    limit = _to_int(req.get('limit'), config['limit'], 0)
    results = []
    root_renames = []

    for openlist_id in config['openlistIds']:
        openlist = openlistMapper.getOpenlistById(openlist_id)
        stdout = io.StringIO()
        stderr = io.StringIO()
        item = {
            'openlistId': openlist_id,
            'openlistName': openlist.get('remark') or openlist.get('url'),
            'success': True,
            'code': 0,
            'stdout': '',
            'stderr': '',
            'error': ''
        }
        try:
            runner_config = _build_runner_config(config, openlist)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                if abort_event and abort_event.is_set():
                    raise Exception('aborted')
                item['code'] = run_media_renamer(runner_config, apply_override=apply, limit=limit)
            item['success'] = item['code'] == 0
        except Exception as e:
            item['success'] = False
            item['code'] = 1
            item['error'] = str(e)
        item['stdout'] = stdout.getvalue()
        item['stderr'] = stderr.getvalue()
        item['rootRenames'] = _extract_root_renames(item['stdout'])
        for root_rename in item['rootRenames']:
            if root_rename not in root_renames:
                root_renames.append(root_rename)
        results.append(item)

    return {
        'apply': apply,
        'limit': limit,
        'rootRenames': root_renames,
        'results': results,
        'success': all(item['success'] for item in results)
    }


def runScrapingWithPreviewPlans(req, config, plans, abort_event=None, progress_callback=None, root_progress_callback=None):
    if not config['openlistIds']:
        raise Exception(G('media_engine_required'))
    apply = _to_bool(req.get('apply'), False)
    overwrite = config['overwrite']
    dry_run = config['dryRun']
    if apply:
        dry_run = False
    rename_threads = config['renameThreads']
    results = []
    root_renames = []

    for openlist_id in config['openlistIds']:
        openlist = openlistMapper.getOpenlistById(openlist_id)
        stdout = io.StringIO()
        stderr = io.StringIO()
        item = {
            'openlistId': openlist_id,
            'openlistName': openlist.get('remark') or openlist.get('url'),
            'success': True,
            'code': 0,
            'stdout': '',
            'stderr': '',
            'error': ''
        }
        try:
            runner_config = _build_runner_config(config, openlist)
            client = build_client(runner_config)
            client.login()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                started = time.perf_counter()
                print(f"[timing] use_preview_plans=true plans={len(plans)}")
                collect_root_rename_pairs(plans)
                apply_started = time.perf_counter()
                should_abort = abort_event.is_set if abort_event else None
                apply_file_plans(
                    client,
                    plans,
                    overwrite,
                    dry_run,
                    rename_threads,
                    should_abort=should_abort,
                    progress_callback=progress_callback,
                )
                print(f"[timing] file_apply={time.perf_counter() - apply_started:.2f}s threads={rename_threads}")
                root_started = time.perf_counter()
                apply_root_renames(
                    client,
                    plans,
                    overwrite,
                    dry_run,
                    should_abort=should_abort,
                    progress_callback=root_progress_callback,
                )
                print(f"[timing] root_rename={time.perf_counter() - root_started:.2f}s")
                print(f"[timing] total={time.perf_counter() - started:.2f}s")
            item['success'] = True
        except Exception as e:
            item['success'] = False
            item['code'] = 1
            item['error'] = str(e)
        item['stdout'] = stdout.getvalue()
        item['stderr'] = stderr.getvalue()
        item['rootRenames'] = _extract_root_renames(item['stdout'])
        for root_rename in item['rootRenames']:
            if root_rename not in root_renames:
                root_renames.append(root_rename)
        results.append(item)

    return {
        'apply': apply,
        'limit': len(plans),
        'usedPreviewPlans': True,
        'rootRenames': root_renames,
        'results': results,
        'success': all(item['success'] for item in results)
    }


def handleAction(req):
    action = req.get('action')
    path = str(req.get('path') or '')
    started = time.perf_counter()
    if action == 'browse':
        result = browsePath(req)
    elif action == 'preview':
        result = previewNaming(req)
    elif action == 'tmdbSearch':
        result = searchTmdb(req)
    elif action == 'taskList':
        return getTaskList(req)
    elif action == 'jobTasks':
        return getJobTasks(req)
    elif action == 'jobCurrent':
        return getJobCurrent(req)
    elif action == 'taskItems':
        return getTaskItems(req)
    elif action == 'deleteJob':
        deleteJob(req)
        return {}
    elif action == 'deleteTask':
        deleteTask(req)
        return {}
    elif action == 'rerunJob':
        return rerunJob(req)
    elif action == 'rerunTask':
        return rerunTask(req)
    elif action == 'abortJob':
        return abortJob(req)
    elif action == 'abortTask':
        return abortTask(req)
    else:
        return startRunTask(req)
    logging.getLogger().info(
        "Media scraping action=%s path=%s elapsed=%.2fs",
        action,
        path,
        time.perf_counter() - started,
    )
    return result
