import time
import re
import threading
import os


def handleWebhook(req):
    result = {
        'job': None,
        'refresh': []
    }
    title = None
    text = None
    if isinstance(req, dict):
        title = req.get('title')
        text = req.get('text')
        if title is None and text is None:
            for k in ['message', 'msg', 'body']:
                v = req.get(k)
                if v:
                    text = str(v)
                    break
    def parse_tv_title_to_remark(s):
        if not s:
            return None
        if '已入库' not in s:
            return None
        m = re.search(r"\s*(.+?\(\d{4}\))\s*(S\d{1,2}|E\d{1,3}|E\d{1,3}-E?\d{1,3})?\s*已入库", s)
        if m:
            return m.group(1).strip()
        m2 = re.search(r"^\s*(.+?\(\d{4}\))", s)
        if m2:
            return m2.group(1).strip()
        return None
    remark = parse_tv_title_to_remark(title) or parse_tv_title_to_remark(text)
    if remark:
        delay = req.get('delay', 60)
        def _trigger():
            try:
                from mapper import jobMapper
                jobs = jobMapper.getJobList()
                target = next((j for j in jobs if j.get('remark') == remark), None)
                if target and int(target.get('enable', 0)) == 1:
                    from service.syncJob import jobService
                    jobService.doJobManual(int(target['id']))
                else:
                    from mapper import alistMapper
                    alists = alistMapper.getAlistList()
                    if not alists:
                        return
                    alistId = int(alists[0]['id'])
                    from service.openlist import openlistService
                    client = openlistService.getClientById(alistId)
                    def _is_tv(s):
                        if not s:
                            return False
                        return bool(re.search(r"\bS\d{1,2}\b", s, re.I) or re.search(r"\bE\d{1,3}\b", s, re.I) or re.search(r"E\d{1,3}-E?\d{1,3}", s, re.I))
                    tv_flag = _is_tv(title) or _is_tv(text)
                    category = '电视剧' if tv_flag else '电影'
                    tv_src = os.getenv('TVsource') or '/media/电视剧'
                    mov_src = os.getenv('MOVsource') or '/media/电影'
                    media_root = tv_src if tv_flag else mov_src
                    has_src = False
                    try:
                        dirs = client.filePathList(media_root)
                        names = [d['path'] for d in dirs]
                        has_src = remark in names
                    except Exception:
                        has_src = False
                    if not has_src:
                        return
                    def _pick(prefix):
                        try:
                            odc = client.filePathList('/ODC')
                            best = None
                            best_n = -1
                            for it in odc:
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
                    odc_prefix = _pick('tv' if tv_flag else 'mov')
                    srcPath = f"{media_root.rstrip('/')}/{remark}/"
                    dst_env = os.getenv('dst')
                    dsts = []
                    if dst_env:
                        try:
                            dst_root = f"{dst_env.rstrip('/')}/{category}"
                            exists_dirs = client.filePathList(dst_root)
                            names = [d['path'] for d in exists_dirs]
                            if remark in names:
                                dsts = [f"{dst_root}/{remark}/"]
                        except Exception:
                            pass
                    if not dsts:
                        sync_env = os.getenv('SYNC_TV_TARGETS') if tv_flag else os.getenv('SYNC_MOV_TARGETS')
                        if sync_env:
                            raw = [p.strip() for p in re.split(r"[,;:]", sync_env) if p and p.strip() != '']
                            for base in raw:
                                base = base.replace('{odc_tv}', f"/ODC/{odc_prefix}").replace('{odc_mov}', f"/ODC/{odc_prefix}")
                                dsts.append(f"{base.rstrip('/')}/{category}/{remark}/")
                        else:
                            dsts = [
                                f"/115/videos/{category}/{remark}/",
                                f"/ODC/{odc_prefix}/{category}/{remark}/"
                            ]
                    from service.syncJob import jobService
                    jobService.addJobClient({
                        'enable': 1,
                        'remark': remark,
                        'srcPath': srcPath,
                        'dstPath': ':'.join(dsts),
                        'alistId': alistId,
                        'useCacheT': 1,
                        'scanIntervalT': 1,
                        'useCacheS': 0,
                        'scanIntervalS': 0,
                        'method': 0,
                        'isCron': 2,
                        'interval': None,
                        'exclude': None
                    })
                    jobs2 = jobMapper.getJobList()
                    created = next((j for j in jobs2 if j.get('remark') == remark and j.get('srcPath') == srcPath and int(j.get('alistId', 0)) == alistId), None)
                    if created:
                        jobService.doJobManual(int(created['id']))
            except Exception:
                pass
        try:
            threading.Timer(int(delay), _trigger).start()
            result['job'] = {'remark': remark, 'scheduled_after_sec': int(delay)}
        except Exception as e:
            result['job'] = str(e)
    if 'jobId' in req and req['jobId'] is not None and str(req['jobId']).strip() != '':
        try:
            from service.syncJob import jobService
            jobService.doJobManual(int(req['jobId']))
            result['job'] = 'triggered'
        except Exception as e:
            result['job'] = str(e)
    if 'alistId' in req and 'paths' in req and req['alistId'] is not None and req['paths']:
        from service.openlist import openlistService
        client = openlistService.getClientById(int(req['alistId']))
        for p in req['paths']:
            if p is None:
                continue
            path = str(p).strip()
            if path == '':
                continue
            if not path.startswith('/'):
                path = '/' + path
            if not path.endswith('/'):
                path = path + '/'
            status = 'ok'
            msg = None
            try:
                client.fileListApi(path, 0, 0, None, path)
            except Exception as e:
                status = 'error'
                msg = str(e)
            result['refresh'].append({'path': path, 'status': status, 'msg': msg})
            time.sleep(0.01)
    return result