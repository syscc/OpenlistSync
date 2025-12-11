import logging

from tornado.web import RequestHandler

from common.commonService import get_post_data, result_map
from service.webhook import webhookService


class Webhook(RequestHandler):
    def post(self):
        try:
            req = get_post_data(self)
            data = webhookService.handleWebhook(req)
            msg = result_map(data)
        except Exception as e:
            logger = logging.getLogger()
            logger.exception(e)
            msg = result_map(str(e), 500)
        self.write(msg)