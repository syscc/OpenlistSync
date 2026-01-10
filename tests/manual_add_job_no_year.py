import os
import sys
import time

if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
    from service.syncJob import jobService
    from service.system import onStart
    from common.config import getConfig
    onStart.init()
    cfg = getConfig()
    job = {
        'enable': 1,
        'remark': 'test-no-year-binding',
        'srcPath': '/sync/test-src/',
        'dstPath': '/sync/test-dst/',
        'openlistId': 1,
        'useCacheT': 1,
        'scanIntervalT': 1,
        'useCacheS': 0,
        'scanIntervalS': 0,
        'method': 0,
        'interval': None,
        'isCron': 1,
        'cronExpr': '0 3 * * *',
        'exclude': None
    }
    try:
        jobService.addJobClient(job, isInit=False)
        print("OK: addJobClient without explicit 'year' succeeded")
        time.sleep(1.0)
    except Exception as e:
        print(f"ERR: {e}")
