import logging

from tornado.web import RequestHandler

from common.commonService import get_post_data, result_map
from service.webhook import webhookService


class Webhook(RequestHandler):
    def post(self):
        try:
            req = get_post_data(self)
            logger = logging.getLogger()
            try:
                logger.info(f"Webhook raw: {req}")
            except Exception:
                pass
            data = webhookService.handleWebhook(req)
            try:
                logger.info(f"Webhook resp: {data}")
            except Exception:
                pass
            msg = result_map(data)
        except Exception as e:
            logger = logging.getLogger()
            logger.exception(e)
            msg = result_map(str(e), 500)
        self.write(msg)
