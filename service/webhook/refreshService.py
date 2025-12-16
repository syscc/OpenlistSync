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
    
    # 获取 /ODC 下的默认 tv/mov 前缀，仅用于兼容 {odc_tv}/{odc_mov} 占位符
    # 如果用户不使用这俩旧占位符，这里的查询其实是多余的，但为了保持对旧配置的兼容，还是保留比较稳妥
    # 既然用户明确要求"不用兼容旧的"（可能是指不需要默认去搜根目录下的 tv/mov），
    # 那么我们可以把这里写死的 '/' 改成 '/ODC' 或者干脆去掉这两个变量？
    # 但下方代码还用到了 tv_prefix_default 和 mov_prefix_default 来替换 {odc_tv}/{odc_mov}
    # 如果完全移除，旧占位符将失效。
    # 用户意图应该是：不要写死搜索根目录 '/'。
    # 之前的逻辑是搜索 '/ODC'，后来为了去硬编码改成了 '/'。
    # 如果用户彻底不用 {odc_tv}，那这两行确实没用。
    # 但为了代码健壮性（防止配置文件里还有旧占位符导致崩溃），建议保留变量定义，但可以设为空字符串或者不进行搜索？
    # 或者，我们遵循用户的"写死的路径都删掉"，既然 {odc_tv} 本身就隐含了 ODC，
    # 那么这里应该恢复成搜索 /ODC 吗？不，用户之前说要删掉 /ODC。
    # 最彻底的做法：如果用户不再使用 {odc_tv}，那这两行和下面的 replace 都可以删掉。
    # 但如果用户只是说"这里代码还有写死的"，是指 `_find_max_dir(client, '/', 'tv')` 里的 `'/'` 吗？
    
    # 让我们假设用户希望彻底移除对 {odc_tv} 的隐式支持逻辑，完全依赖 {max}。
    # 那么我们可以移除这两个默认搜索。
    
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
        
        # 2. 移除旧占位符支持（根据用户要求）
        # base = base.replace('{odc_tv}', tv_prefix_default).replace('{odc_mov}', mov_prefix_default)
        
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
    odc_prefix = None
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
        # 尝试获取 SYNC_REFRESH_TV/MOV，如果为空则尝试获取 REFRESH_TV/MOV_TARGETS（兼容旧配置或用户习惯）
        if is_tv:
            env_refresh = os.getenv('SYNC_REFRESH_TV') or os.getenv('REFRESH_TV_TARGETS')
        else:
            env_refresh = os.getenv('SYNC_REFRESH_MOV') or os.getenv('REFRESH_MOV_TARGETS')
    
    logger.info(f"Refresh env config: dst_used={dst_used}, env_refresh={env_refresh}")
    
    if env_refresh:
        # 使用通用展开逻辑处理刷新路径中的 {max}
        raw_refresh_paths = _expand_targets(env_refresh, client)
        for base in raw_refresh_paths:
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