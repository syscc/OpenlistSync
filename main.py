import asyncio
import logging
import os
import sys

from tornado.web import Application, RequestHandler, StaticFileHandler

from common.config import getConfig
from controller import systemController, jobController, notifyController, webhookController
from service.system import onStart


class MainIndex(RequestHandler):
    def get(self):
        indexPath = os.path.join(frontDir, "index.html")
        if os.path.exists(indexPath):
            self.render(indexPath)
        else:
            self.write("Frontend not built. Build via 'cd frontend && npm install && npm run build'.")


def make_app():
    # 以/svr/noAuth开头的请求无需鉴权，例如登录等
    return Application([
        (r"/svr/noAuth/login", systemController.Login),
        (r"/svr/user", systemController.User),
        (r"/svr/language", systemController.Language),
        (r"/svr/openlist", jobController.OpenList),
        (r"/svr/job", jobController.Job),
        (r"/svr/notify", notifyController.Notify),
        (r"/webhook", webhookController.Webhook),
        (r"/", MainIndex),
        (r"/(.*)", StaticFileHandler,
         {"path": frontDir})
    ], cookie_secret=server['passwdStr'])


async def main():
    app = make_app()
    logger = logging.getLogger()
    app.listen(server['port'])
    successMsg = f"启动成功_/_Running at http://127.0.0.1:{server['port']}/"
    logger.critical(successMsg)
    await asyncio.Event().wait()


if __name__ == "__main__":
    onStart.init()
    cfg = getConfig()
    if getattr(sys, 'frozen', False):
        frontendBase = sys._MEIPASS
        frontDir = os.path.join(frontendBase, 'front')
    else:
        if os.path.exists(os.path.join('front', 'index.html')):
            frontDir = os.path.join('front')
        elif os.path.exists(os.path.join('frontend', 'dist', 'index.html')):
            frontDir = os.path.join('frontend', 'dist')
        else:
            frontDir = os.path.join('front')
    # 后端配置
    server = cfg['server']
    asyncio.run(main())
