import re
import os
import time

from service.openlist import openlistService
from service.notify import notifyService


def _refresh_path(client, path):
    try:
        if not path.endswith('/'):
            path = path + '/'
        client.fileListApi(path, 0, 0, None, path)
        return True, None
    except Exception as e:
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
    if status not in [2, 3]:
        return
    alistId = int(job['alistId'])
    client = openlistService.getClientById(alistId)
    remark = job.get('remark') or ''
    src = job.get('srcPath') or ''
    dsts = (job.get('dstPath') or '').split(':') if job.get('dstPath') else []
    is_tv = '/电视剧/' in src
    category = '电视剧' if is_tv else '电影'
    odc_prefix = None
    # 组装需刷新基本路径
    base_paths = []
    name = remark
    only_shanct = (is_tv and dsts and all(p.startswith('/shanct/电视剧') for p in dsts))
    if is_tv and only_shanct:
        # 仅同步到 /shanct 时，只刷新 /shanct 与 /videos
        base_paths = [
            f"/shanct/电视剧/{name}",
            f"/videos/电视剧/{name}"
        ]
    else:
        env_refresh = os.getenv('REFRESH_TV_TARGETS') if is_tv else os.getenv('REFRESH_MOV_TARGETS')
        dedup = []
        seen = set()
        if env_refresh:
            raw = [p.strip() for p in re.split(r"[,;:]", env_refresh) if p and p.strip() != '']
            tv_prefix = _select_latest_odc_prefix(client, 'tv')
            mov_prefix = _select_latest_odc_prefix(client, 'mov')
            for base in raw:
                base = base.replace('{odc_tv}', tv_prefix).replace('{odc_mov}', mov_prefix)
                if not base.startswith('/'):
                    base = '/' + base
                base = re.sub(r"/{2,}", "/", base).rstrip('/')
                path = f"{base}/{category}/{name}"
                if path not in seen:
                    dedup.append(path)
                    seen.add(path)
        else:
            # 默认回退逻辑
            if is_tv:
                for p in dsts:
                    m = re.search(r"/ODC/(tv\d+)/电视剧/", p)
                    if m:
                        odc_prefix = m.group(1)
                        break
                if odc_prefix is None:
                    odc_prefix = _select_latest_odc_prefix(client, 'tv')
                for base in [f"/115/videos/{category}", f"/ODC/{odc_prefix}/{category}"]:
                    path = f"{base}/{name}"
                    if path not in seen:
                        dedup.append(path)
                        seen.add(path)
            else:
                for p in dsts:
                    m = re.search(r"/ODC/(mov\d+)/电影/", p)
                    if m:
                        odc_prefix = m.group(1)
                        break
                if odc_prefix is None:
                    odc_prefix = _select_latest_odc_prefix(client, 'mov')
                for base in [f"/115/videos/{category}", f"/ODC/{odc_prefix}/{category}"]:
                    path = f"{base}/{name}"
                    if path not in seen:
                        dedup.append(path)
                        seen.add(path)
        # 始终追加 /videos 路径
        videos_path = f"/videos/{category}/{name}"
        if videos_path not in seen:
            dedup.append(videos_path)
            seen.add(videos_path)
        base_paths = dedup
    if not base_paths:
        return
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
    notify_list = notifyService.getNotifyList(True)
    if not notify_list:
        return
    title = ('目录刷新完成 ✔️' if not fail_list else '目录刷新失败 ❌')
    content = ("全部目录刷新成功：\n" + "\n".join(ok_list)) if not fail_list else ("以下目录刷新失败：\n" + "\n".join(fail_list))
    for notify in notify_list:
        try:
            notifyService.sendNotify(notify, title, content, False)
        except Exception:
            pass
    key = f"{remark}:{status}"
    now = time.time()
    last = _recent_refresh.get(key)
    if last and now - last < 60:
        return
    _recent_refresh[key] = now
