import logging

from tornado.web import RequestHandler

from common.LNG import set_context_lang
from common.commonService import get_post_data, result_map
from service.webhook import webhookService


class Webhook(RequestHandler):
    def post(self):
        try:
            req = get_post_data(self)
            request_lang = self.request.headers.get('Accept-Language')
            if request_lang:
                req['__lang'] = set_context_lang(request_lang)
            logger = logging.getLogger()
            try:
                log_req = dict(req)
                if 'apikey' in log_req:
                    log_req['apikey'] = '***'
                logger.info(f"Webhook raw: {log_req}")
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
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(msg)
