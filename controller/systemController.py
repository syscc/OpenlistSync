import json
from concurrent.futures import ThreadPoolExecutor

from common.LNG import language
from common.config import getConfig
from controller.baseController import BaseHandler, handle_request, cookieName
from tornado.concurrent import run_on_executor
from service.system import configService, userService


class Login(BaseHandler):
    @handle_request
    def post(self, req):
        cfg = getConfig()
        user = userService.checkPwd(None, req['passwd'], req['userName'])
        self.set_signed_cookie(cookieName, json.dumps(user),
                               expires_days=cfg['server']['expires'])
        userReturn = user.copy()
        del userReturn['passwd']
        del userReturn['sqlVersion']
        return userReturn

    @handle_request
    def put(self, req):
        return userService.resetPasswd(req['userName'], req['key'], req.get('passwd', None))

    @handle_request
    def delete(self, req):
        self.clear_cookie(cookieName)


class User(BaseHandler):
    @handle_request
    def get(self, req):
        user = req['__user']
        return user

    @handle_request
    def put(self, req):
        user = json.loads(self.get_signed_cookie(cookieName))
        userService.editPasswd(user['id'], req['passwd'], req['oldPasswd'])


class Language(BaseHandler):
    @handle_request
    def get(self, req):
        return language()

    @handle_request
    def post(self, req):
        language(req['language'])
        return language()


class Config(BaseHandler):
    @handle_request
    def get(self, req):
        return configService.getConfig()

    @handle_request
    def post(self, req):
        return configService.updateConfig(req)


class ProxyReveal(BaseHandler):
    @handle_request
    def get(self, req):
        self.set_header('Cache-Control', 'no-store')
        return configService.revealProxyServer()


class ProxyTest(BaseHandler):
    executor = ThreadPoolExecutor(2)

    @run_on_executor
    @handle_request
    def post(self, req):
        return configService.testProxyServer(req)
