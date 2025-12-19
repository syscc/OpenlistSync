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


def _find_max_dir(client, parent_dir, prefix):
    """
    通用函数：查找指定目录下以 prefix 为前缀的子目录中，数字后缀最大的那个。
    """
    try:
        # 确保父目录以 / 开头
        if not parent_dir.startswith('/'):
            parent_dir = '/' + parent_dir
        
        dirs = client.filePathList(parent_dir)
        best = None
        best_n = -1
        
        for it in dirs:
            name = it.get('path') or ''
            # name 是纯文件名，不带路径
            if name.startswith(prefix):
                # 提取数字后缀
                m = re.search(r"(\d+)$", name)
                n = int(m.group(1)) if m else 0
                if n > best_n:
                    best_n = n
                    best = name
        return best or f"{prefix}1"
    except Exception:
        return f"{prefix}1"


def _expand_targets(env_s, client):
    arr = []
    if not env_s:
        return arr
    raw = [p.strip() for p in re.split(r"[,;:]", env_s) if p and p.strip() != '']
    
    for base in raw:
        # 1. 处理通用 {max} 语法
        def max_replacer(match):
            parent = match.group(1) # e.g. "/a/b/" or ""
            prefix = match.group(2) # e.g. "disk"
            
            # 如果没有父路径，默认使用根目录 /
            search_dir = parent if parent else '/'
            
            best_name = _find_max_dir(client, search_dir, prefix)
            
            if not parent:
                 return f"/{best_name}"
            return f"{parent}{best_name}"

        base = re.sub(r"(^|.*?/)([^/]*)\{max\}", max_replacer, base)
        
        if not base.startswith('/'):
            base = '/' + base
        base = re.sub(r"/{2,}", "/", base).rstrip('/')
        arr.append(base)
    return arr


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
    base_paths = []
    name = remark
    dedup = []
    seen = set()
    tv_src = os.getenv('TVsource') or ''
    mov_src = os.getenv('MOVsource') or ''

    dst_target_env = os.getenv('DST_TV_TARGETS') if is_tv else os.getenv('DST_MOV_TARGETS')
    sync_target_env = os.getenv('SYNC_TV_TARGETS') if is_tv else os.getenv('SYNC_MOV_TARGETS')
    dst_bases = _expand_targets(dst_target_env, client)
    sync_bases = _expand_targets(sync_target_env, client)
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
        if is_tv:
            env_refresh = os.getenv('SYNC_REFRESH_TV')
        else:
            env_refresh = os.getenv('SYNC_REFRESH_MOV')
    
    logger.info(f"Refresh env config: dst_used={dst_used}, env_refresh={env_refresh}")
    
    if env_refresh:
        # 使用通用展开逻辑处理刷新路径中的 {max}
        raw_refresh_paths = _expand_targets(env_refresh, client)
        for base in raw_refresh_paths:
            path = f"{base}/{name}"
            if path not in seen:
                dedup.append(path)
                seen.add(path)
        
        # 即使配置了刷新变量，也自动追加任务的目标路径（SYNC模式下）
        # 这样可以保证：不管变量怎么配，至少任务同步过去的地方会被刷新
        # 如果用户只想刷新变量指定的目录，不想刷新任务目标目录，这种场景比较少见，暂不考虑
        if not dst_used:
             for d in dsts:
                d = d.rstrip('/')
                if d not in seen:
                    dedup.append(d)
                    seen.add(d)
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
        # 如果通过变量解析出的刷新路径为空，尝试回退到默认策略（刷新任务目标路径）
        # 这种情况通常发生在配置了变量但变量解析结果为空，或者变量配置有误
        logger.info("Refresh base_paths empty from env, fallback to task dsts")
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
            for d in dsts:
                d = d.rstrip('/')
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
            fail_list.append({'path': p, 'msg': msg})
    
    # 智能过滤：如果至少有一个路径刷新成功，则忽略那些因为“对象不存在”而失败的路径
    # 场景：配置了 {max} 变量指向了新盘，但老剧集实际存在于旧盘。
    # 旧盘路径通常包含在 dsts 中并会刷新成功，此时新盘路径的“不存在”报错是可以忽略的。
    if ok_list:
        final_fail_list = []
        for item in fail_list:
            msg = item['msg'] or ''
            if 'object not found' in msg.lower():
                logger.info(f"Refresh failed but ignored (covered by other success): {item['path']}")
                continue
            final_fail_list.append(f"{item['path']} ❌ {msg}")
        fail_list_str = final_fail_list
    else:
        # 如果全部失败，则保留所有报错
        fail_list_str = [f"{x['path']} ❌ {x['msg']}" for x in fail_list]

    logger.info(f"Refresh result: ok={len(ok_list)}, fail={len(fail_list_str)}")

    notify_list = notifyService.getNotifyList(True)
    if not notify_list:
        logger.info("Refresh notify skipped: no notify config")
        return
    title = ('目录刷新完成 ✔️' if not fail_list_str else '目录刷新失败 ❌')
    content = ("全部目录刷新成功：\n" + "\n".join(ok_list)) if not fail_list_str else ("以下目录刷新失败：\n" + "\n".join(fail_list_str))
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