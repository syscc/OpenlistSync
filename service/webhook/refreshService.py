import re
import os
import time
import logging

from service.openlist import openlistService
from service.notify import notifyService


def _refresh_path(client, path):
    logger = logging.getLogger()
    try:
        if not path.endswith('/'):
            path = path + '/'
        client.fileListApi(path, 0, 0, None, path)
        logger.info(f"Refresh success: {path}")
        return True, None
    except Exception as e:
        logger.error(f"Refresh failed: {path}, error: {str(e)}")
        return False, str(e)


def _list_seasons(client, base_path):
    try:
        if not base_path.endswith('/'):
            base_path = base_path + '/'
        content = client.fileListApi(base_path, 0, 0, None, base_path)
        seasons = []
        for name in content.keys():
            if name.endswith('/'):
                m = re.fullmatch(r"Season\s+(\d+)/", name)
                if m:
                    seasons.append(int(m.group(1)))
        return seasons
    except Exception:
        return []


def _resolve_season_path(client, base_path):
    base_path = base_path.rstrip('/')
    if re.search(r"/Season\s+\d+$", base_path):
        return base_path + '/'
    ss = _list_seasons(client, base_path)
    if ss:
        return f"{base_path}/Season {max(ss)}/"
    return base_path + '/'


def _select_latest_odc_prefix(client, prefix):
    try:
        dirs = client.filePathList('/ODC')
        best = None
        best_n = -1
        for it in dirs:
            name = it.get('path') or ''
            if name.startswith(prefix):
                m = re.search(r"(\d+)$", name)
                n = int(m.group(1)) if m else 0
                if n > best_n:
                    best_n = n
                    best = name
        return best or f"{prefix}1"
    except Exception:
        return f"{prefix}1"


_recent_refresh = {}


def refresh_after_task(job, status):
    logger = logging.getLogger()
    if status not in [2, 3]:
        logger.info(f"Refresh skipped: status {status} not in [2, 3]")
        return
    logger.info(f"Refresh start: job={job.get('remark')}, status={status}")
    
    openlistId = int(job['openlistId'])
    client = openlistService.getClientById(openlistId)
    remark = job.get('remark') or ''
    src = job.get('srcPath') or ''
    dsts = (job.get('dstPath') or '').split(':') if job.get('dstPath') else []
    src_norm = re.sub(r"/{2,}", "/", src).rstrip('/') + '/'
    tv_src_env = (os.getenv('TVsource') or '').strip()
    mov_src_env = (os.getenv('MOVsource') or '').strip()
    tv_src_norm = re.sub(r"/{2,}", "/", tv_src_env).rstrip('/') + '/' if tv_src_env else ''
    mov_src_norm = re.sub(r"/{2,}", "/", mov_src_env).rstrip('/') + '/' if mov_src_env else ''
    is_tv = bool(tv_src_norm and src_norm.startswith(tv_src_norm))
    logger.info(f"Refresh context: is_tv={is_tv}, src={src}, dsts={dsts}")
    odc_prefix = None
    base_paths = []
    name = remark
    dedup = []
    seen = set()
    tv_src = os.getenv('TVsource') or ''
    mov_src = os.getenv('MOVsource') or ''
    def _expand_targets(env_s):
        arr = []
        if not env_s:
            return arr
        raw = [p.strip() for p in re.split(r"[,;:]", env_s) if p and p.strip() != '']
        tv_prefix = _select_latest_odc_prefix(client, 'tv')
        mov_prefix = _select_latest_odc_prefix(client, 'mov')
        for base in raw:
            base = base.replace('{odc_tv}', tv_prefix).replace('{odc_mov}', mov_prefix)
            if not base.startswith('/'):
                base = '/' + base
            base = re.sub(r"/{2,}", "/", base).rstrip('/')
            arr.append(base)
        return arr
    dst_target_env = os.getenv('DST_TV_TARGETS') if is_tv else os.getenv('DST_MOV_TARGETS')
    sync_target_env = os.getenv('SYNC_TV_TARGETS') if is_tv else os.getenv('SYNC_MOV_TARGETS')
    dst_bases = _expand_targets(dst_target_env)
    sync_bases = _expand_targets(sync_target_env)
    dst_used = False
    for d in dsts:
        for b in dst_bases:
            if d.startswith(b.rstrip('/') + '/'):
                dst_used = True
                break
        if dst_used:
            break
    env_refresh = None
    if dst_used:
        env_refresh = os.getenv('DST_REFRESH_TV') if is_tv else os.getenv('DST_REFRESH_MOV')
    else:
        env_refresh = os.getenv('SYNC_REFRESH_TV') if is_tv else os.getenv('SYNC_REFRESH_MOV')
    
    logger.info(f"Refresh env config: dst_used={dst_used}, env_refresh={env_refresh}")

    if env_refresh:
        raw = [p.strip() for p in re.split(r"[,;:]", env_refresh) if p and p.strip() != '']
        tv_prefix = _select_latest_odc_prefix(client, 'tv')
        mov_prefix = _select_latest_odc_prefix(client, 'mov')
        for base in raw:
            base = base.replace('{odc_tv}', tv_prefix).replace('{odc_mov}', mov_prefix)
            if not base.startswith('/'):
                base = '/' + base
            base = re.sub(r"/{2,}", "/", base).rstrip('/')
            path = f"{base}/{name}"
            if path not in seen:
                dedup.append(path)
                seen.add(path)
    else:
        # 如果未配置刷新变量，则使用默认策略
        if dst_used:
            # DST模式：默认刷新源目录
            base = (tv_src if is_tv else mov_src).strip()
            if base:
                base = re.sub(r"/{2,}", "/", base).rstrip('/')
                path = f"{base}/{name}"
                if path not in seen:
                    dedup.append(path)
                    seen.add(path)
        else:
            # SYNC模式：默认刷新所有同步目标目录
            # 注意：这里的dsts是任务实际执行的目标路径列表（已包含变量替换后的结果）
            for d in dsts:
                d = d.rstrip('/')
                # 任务目标路径通常已经是 .../剧名/ 的形式，所以直接使用
                if d not in seen:
                    dedup.append(d)
                    seen.add(d)
    base_paths = dedup
    if not base_paths:
        logger.info("Refresh skipped: no base_paths found")
        return
    
    logger.info(f"Refresh targets: {base_paths}")

    # 解析 Season 并刷新
    resolved = []
    for base in base_paths:
        resolved.append(_resolve_season_path(client, base) if is_tv else (base.rstrip('/') + '/'))
    ok_list = []
    fail_list = []
    for p in resolved:
        ok, msg = _refresh_path(client, p)
        if ok:
            ok_list.append(p)
        else:
            fail_list.append(f"{p} ❌ {msg}")
    
    logger.info(f"Refresh result: ok={len(ok_list)}, fail={len(fail_list)}")

    notify_list = notifyService.getNotifyList(True)
    if not notify_list:
        logger.info("Refresh notify skipped: no notify config")
        return
    title = ('目录刷新完成 ✔️' if not fail_list else '目录刷新失败 ❌')
    content = ("全部目录刷新成功：\n" + "\n".join(ok_list)) if not fail_list else ("以下目录刷新失败：\n" + "\n".join(fail_list))
    for notify in notify_list:
        try:
            notifyService.sendNotify(notify, title, content, False)
        except Exception as e:
            logger.error(f"Refresh notify failed: {str(e)}")
            pass
    key = f"{remark}:{status}"
    now = time.time()
    last = _recent_refresh.get(key)
    if last and now - last < 60:
        return
    _recent_refresh[key] = now
