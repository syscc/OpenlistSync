from concurrent.futures import ThreadPoolExecutor

from tornado.concurrent import run_on_executor

from controller.baseController import BaseHandler, handle_request
from service.mediaScraping import mediaScrapingService


class MediaScraping(BaseHandler):
    executor = ThreadPoolExecutor(2)

    @handle_request
    def get(self, req):
        return mediaScrapingService.getConfig()

    @handle_request
    def post(self, req):
        return mediaScrapingService.updateConfig(req)

    @run_on_executor
    @handle_request
    def put(self, req):
        return mediaScrapingService.handleAction(req)
