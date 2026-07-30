import os
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from tornado.log import access_log
from tornado.web import Application, RequestHandler, StaticFileHandler

from controller import (
    jobController,
    mediaScrapingController,
    notifyController,
    systemController,
    webhookController,
)


SENSITIVE_QUERY_KEYS = {
    'access_token',
    'api_key',
    'apikey',
    'key',
    'passwd',
    'password',
    'secret',
    'token',
}


def redact_request_uri(uri):
    parts = urlsplit(str(uri or ''))
    if not parts.query:
        return str(uri or '')
    query = [
        (key, '<redacted>' if key.lower() in SENSITIVE_QUERY_KEYS else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def log_request(handler):
    status = handler.get_status()
    if status < 400:
        log_method = access_log.info
    elif status < 500:
        log_method = access_log.warning
    else:
        log_method = access_log.error
    summary = '%s %s (%s)' % (
        handler.request.method,
        redact_request_uri(handler.request.uri),
        handler.request.remote_ip,
    )
    log_method('%d %s %.2fms', status, summary, 1000.0 * handler.request.request_time())


class MainIndex(RequestHandler):
    def initialize(self, front_dir):
        self.front_dir = front_dir

    def get(self):
        index_path = os.path.join(self.front_dir, 'index.html')
        if os.path.exists(index_path):
            self.render(index_path)
        else:
            self.write("Frontend not built. Run the Vue dev server from 'web/' for source-mode development.")


def resolve_front_dir(base_dir='.'):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'front')
    for candidate in ('front', os.path.join('web', 'dist')):
        path = os.path.join(base_dir, candidate)
        if os.path.exists(os.path.join(path, 'index.html')):
            return path
    return os.path.join(base_dir, 'front')


def make_app(server_cfg, front_dir=None):
    front_dir = front_dir or resolve_front_dir()
    return Application([
        (r'/svr/noAuth/login', systemController.Login),
        (r'/svr/user', systemController.User),
        (r'/svr/language', systemController.Language),
        (r'/svr/system/config', systemController.Config),
        (r'/svr/media/scraping', mediaScrapingController.MediaScraping),
        (r'/svr/openlist', jobController.OpenList),
        (r'/svr/job', jobController.Job),
        (r'/svr/notify', notifyController.Notify),
        (r'/webhook', webhookController.Webhook),
        (r'/', MainIndex, {'front_dir': front_dir}),
        (r'/(.*)', StaticFileHandler, {'path': front_dir}),
    ], cookie_secret=server_cfg['passwdStr'], log_function=log_request)
