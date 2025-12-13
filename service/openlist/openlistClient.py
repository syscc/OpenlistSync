import time

import requests

from common.LNG import G


def checkExs(path, rts, spec):
    rtsNew = rts.copy()
    for rtsItem in rts.keys():
        if spec.match_file(path + '/' + rtsItem):
            del rtsNew[rtsItem]
    return rtsNew


class OpenListClient:
    def __init__(self, url, token, openlistId=None):
        self.url = url
        self.user = None
        self.openlistId = openlistId
        self.token = token
        self.waits = {}
        self.getUser()

    def req(self, method, url, data=None, params=None):
        res = {
            'code': 500,
            'message': None,
            'data': None
        }
        headers = None
        if self.token is not None:
            headers = {
                'Authorization': self.token
            }
        try:
            r = requests.request(method, self.url + url, json=data, params=params, headers=headers, timeout=(60, 300))
            if r.status_code == 200:
                res = r.json()
            else:
                res['code'] = r.status_code
                res['message'] = G('code_not_200')
        except Exception as e:
            if 'Invalid URL' in str(e):
                raise Exception(G('address_incorrect'))
            elif 'Max retries' in str(e):
                raise Exception(G('openlist_connect_fail'))
            raise Exception(e)
        if res['code'] != 200:
            if res['code'] == 401:
                raise Exception(G('openlist_un_auth'))
            raise Exception(G('openlist_fail_code_reason').format(res['code'], res['message']))
        return res['data']

    def post(self, url, data=None, params=None):
        return self.req('post', url, data, params)

    def get(self, url, params=None):
        return self.req('get', url, params=params)

    def getUser(self):
        self.user = self.get('/api/me')['username']

    def updateOpenListId(self, openlistId):
        self.openlistId = openlistId

    def checkWait(self, path, scanInterval=0):
        if scanInterval != 0:
            pathFirst = path.split('/', maxsplit=2)[1]
            if pathFirst in self.waits:
                timeC = time.time() - self.waits[pathFirst]
                if timeC < scanInterval:
                    self.waits[pathFirst] = time.time() + timeC
                    time.sleep(scanInterval - timeC)
                    return
            self.waits[pathFirst] = time.time()

    def fileListApi(self, path, useCache=0, scanInterval=0, spec=None, rootPath=None):
        self.checkWait(path, scanInterval)
        res = self.post('/api/fs/list', data={
            'path': path,
            'refresh': useCache != 1
        })['content']
        if res is not None:
            rts = {
                f"{item['name']}/" if item['is_dir'] else item['name']: {} if item['is_dir']
                else item['size'] for item in res
            }
        else:
            rts = {}
        if spec and rts:
            if rootPath is None:
                rootPath = path
            rts = checkExs(path[len(rootPath):], rts, spec)
        return rts

    def filePathList(self, path):
        res = self.post('/api/fs/list', data={
            'path': path,
            'refresh': True
        })['content']
        if res is not None:
            return [{'path': item['name']} for item in res if item['is_dir']]
        else:
            return []

    def mkdir(self, path, scanInterval=0):
        self.checkWait(path, scanInterval)
        return self.post('/api/fs/mkdir', data={
            'path': path
        })

    def deleteFile(self, path, names, scanInterval=0):
        self.checkWait(path, scanInterval)
        self.post('/api/fs/remove', data={
            'names': names,
            'dir': path
        })

    def copyFile(self, srcDir, dstDir, name):
        tasks = self.post('/api/fs/copy', data={
            'src_dir': srcDir,
            'dst_dir': dstDir,
            'overwrite': True,
            'names': [name]
        })['tasks']
        if tasks:
            return tasks[0]['id']
        else:
            return None

    def moveFile(self, srcDir, dstDir, name):
        tasks = self.post('/api/fs/move', data={
            'src_dir': srcDir,
            'dst_dir': dstDir,
            'overwrite': True,
            'names': [name]
        })['tasks']
        if tasks:
            return tasks[0]['id']
        else:
            return None

    def taskInfo(self, taskId):
        return self.post('/api/admin/task/copy/info', params={'tid': taskId})

    def copyTaskDone(self):
        return self.get('/api/admin/task/copy/done')

    def copyTaskUnDone(self):
        return self.get('/api/admin/task/copy/undone')

    def copyTaskRetry(self, taskId):
        self.post('/api/admin/task/copy/retry', params={'tid': taskId})

    def copyTaskClearSucceeded(self):
        self.post('/api/admin/task/copy/clear_succeeded')

    def copyTaskDelete(self, taskId):
        self.post('/api/admin/task/copy/delete', params={'tid': taskId})

    def copyTaskCancel(self, taskId):
        self.post('/api/admin/task/copy/cancel', params={'tid': taskId})