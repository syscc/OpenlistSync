import time
import re
import threading
import os
from service.notify import notifyService


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
        delay = req.get('delay', None)
        def _read_env_file(key):
            try:
                with open(os.path.join('data', 'env'), 'r', encoding='utf-8') as f:
                    for line in f:
                        s = line.strip()
                        if not s or s.startswith('#') or '=' not in s:
                            continue
                        k, v = s.split('=', 1)
                        if k.strip() == key:
                            return v.strip()
            except Exception:
                return None
        if delay is None:
            raw = os.getenv('WEBHOOK_DELAY') or _read_env_file('WEBHOOK_DELAY') or '30'
            try:
                delay = int(raw)
            except Exception:
                delay = 30
        else:
            try:
                delay = int(delay)
            except Exception:
                delay = 30
        def _trigger():
            try:
                import logging
                lg = logging.getLogger()
                try:
                    lg.info(f"Webhook trigger start: remark={remark}")
                except Exception:
                    pass
                from mapper import jobMapper
                jobs = jobMapper.getJobList()
                target = next((j for j in jobs if j.get('remark') == remark), None)
                if target and int(target.get('enable', 0)) == 1:
                    from service.syncJob import jobService
                    jobService.doJobManual(int(target['id']))
                    try:
                        lg.info(f"Webhook manual run existing job id={int(target['id'])}")
                    except Exception:
                        pass
                else:
                    from mapper import alistMapper
                    alists = alistMapper.getAlistList()
                    if not alists:
                        return
                    if not alists:
                        try:
                            notify_list = notifyService.getNotifyList(True)
                            if notify_list:
                                for n in notify_list:
                                    try:
                                        notifyService.sendNotify(n, 'Webhook已收到，但未配置引擎', '请在引擎管理中添加OpenList地址与Token', False)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        return
                    alistId = int(alists[0]['id'])
                    from service.openlist import openlistService
                    client = None
                    try:
                        client = openlistService.getClientById(alistId)
                    except Exception:
                        client = None
                    def _is_tv(s):
                        if not s:
                            return False
                        return bool(re.search(r"\bS\d{1,2}\b", s, re.I) or re.search(r"\bE\d{1,3}\b", s, re.I) or re.search(r"E\d{1,3}-E?\d{1,3}", s, re.I))
                    tv_flag = _is_tv(title) or _is_tv(text)
                    tv_src = os.getenv('TVsource') or ''
                    mov_src = os.getenv('MOVsource') or ''
                    media_root = tv_src if tv_flag else mov_src
                    has_src = False
                    if client is not None:
                        try:
                            dirs = client.filePathList(media_root)
                            names = [d['path'] for d in dirs]
                            has_src = remark in names
                        except Exception:
                            has_src = False
                    force_create = False
                    try:
                        force_create = bool(req.get('force', False)) or (os.getenv('WEBHOOK_FORCE_CREATE', 'false').lower() in ['1','true','yes'])
                    except Exception:
                        force_create = False
                    if not has_src and not force_create:
                        try:
                            notify_list = notifyService.getNotifyList(True)
                            if notify_list:
                                title2 = 'Webhook已收到，源不存在，已跳过'
                                content2 = f"源路径- {media_root.rstrip('/')}/{remark}"
                                for n in notify_list:
                                    try:
                                        notifyService.sendNotify(n, title2, content2, False)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        return
                    def _pick(prefix):
                        if client is None:
                            return f"{prefix}1"
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
                    dst_env = os.getenv('DST_TV_TARGETS') if tv_flag else os.getenv('DST_MOV_TARGETS')
                    dsts = []
                    if dst_env and client is not None:
                        try:
                            raw_dst = [p.strip() for p in re.split(r"[,;:]", dst_env) if p and p.strip() != '']
                            tv_prefix = _pick('tv')
                            mov_prefix = _pick('mov')
                            for base in raw_dst:
                                base = base.replace('{odc_tv}', tv_prefix).replace('{odc_mov}', mov_prefix)
                                if not base.startswith('/'):
                                    base = '/' + base
                                base = re.sub(r"/{2,}", "/", base).rstrip('/')
                                exists_dirs = client.filePathList(base)
                                names = [d['path'] for d in exists_dirs]
                                if remark in names:
                                    dsts = [f"{base}/{remark}/"]
                                    break
                        except Exception:
                            pass
                    if not dsts:
                        sync_env = os.getenv('SYNC_TV_TARGETS') if tv_flag else os.getenv('SYNC_MOV_TARGETS')
                        if sync_env:
                            raw = [p.strip() for p in re.split(r"[,;:]", sync_env) if p and p.strip() != '']
                            tv_prefix = _pick('tv')
                            mov_prefix = _pick('mov')
                            for base in raw:
                                base = base.replace('{odc_tv}', tv_prefix).replace('{odc_mov}', mov_prefix)
                                if not base.startswith('/'):
                                    base = '/' + base
                                base = re.sub(r"/{2,}", "/", base).rstrip('/')
                                dsts.append(f"{base}/{remark}/")
                        else:
                            try:
                                notify_list = notifyService.getNotifyList(True)
                                if notify_list:
                                    for n in notify_list:
                                        try:
                                            notifyService.sendNotify(n, 'Webhook已收到，但未配置同步集合', '请设置 DST_* 或 SYNC_* 环境变量', False)
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                            return
                    from service.syncJob import jobService
                    payload = {
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
                        'exclude': None,
                        'year': None,
                        'month': None,
                        'day': None,
                        'week': None,
                        'day_of_week': None,
                        'hour': None,
                        'minute': None,
                        'second': None,
                        'start_date': None,
                        'end_date': None
                    }
                    try:
                        lg.info(f"Webhook create payload: dstPath={payload['dstPath']}")
                    except Exception:
                        pass
                    jobService.addJobClient(payload)
                    jobs2 = jobMapper.getJobList()
                    created = next((j for j in jobs2 if j.get('remark') == remark and int(j.get('alistId', 0)) == alistId), None)
                    if created:
                        jobService.doJobManual(int(created['id']))
                        try:
                            lg.info(f"Webhook created and manual run job id={int(created['id'])}")
                        except Exception:
                            pass
            except Exception:
                try:
                    import logging
                    logging.getLogger().exception("Webhook trigger error")
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
