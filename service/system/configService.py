import ipaddress
import json
import time
import urllib.parse

from mapper import systemConfigMapper
from media_tools import openlist_media_renamer as mediaRenamer


GLOBAL_EXCLUDE_KEY = 'global_exclude'
PROXY_SERVER_KEY = 'proxy_server'
TMDB_PROXY_KEY = 'tmdb_proxy'
PROXY_TEST_URL = 'http://www.google.com/generate_204'
PROXY_TEST_TIMEOUT = 10


def _default_proxy_server():
    return {'enabled': False, 'url': ''}


def _to_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _normalize_proxy_url(value):
    raw = str(value or '').strip()
    if not raw:
        return ''
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in raw):
        raise Exception('Proxy server URL is invalid')

    try:
        parts = urllib.parse.urlsplit(raw)
        hostname = parts.hostname
        port = parts.port
    except ValueError:
        raise Exception('Proxy server URL is invalid') from None

    scheme = parts.scheme.lower()
    if (
            scheme not in {'http', 'socks'}
            or not parts.netloc
            or not hostname
            or port is None
            or port < 1
            or port > 65535
            or parts.path not in {'', '/'}
            or parts.query
            or parts.fragment):
        raise Exception('Proxy server URL is invalid')

    host_port = parts.netloc.rsplit('@', 1)[-1]
    if host_port.startswith('[') or ':' in hostname:
        try:
            if ipaddress.ip_address(hostname).version != 6:
                raise ValueError
        except ValueError:
            raise Exception('Proxy server URL is invalid') from None

    auth = ''
    if parts.username is not None or parts.password is not None:
        auth = urllib.parse.quote(urllib.parse.unquote(parts.username or ''), safe='')
        if parts.password is not None:
            auth += ':' + urllib.parse.quote(urllib.parse.unquote(parts.password), safe='')
        auth += '@'
    return urllib.parse.urlunsplit((scheme, auth + host_port, '', '', ''))


def _legacy_proxy_to_url(proxy):
    proxy = proxy if isinstance(proxy, dict) else {}
    proxy_type = str(proxy.get('type') or 'http').strip().lower()
    if proxy_type not in {'http', 'socks5', 'socks5h', 'socks'}:
        raise Exception('Proxy server URL is invalid')
    scheme = 'socks' if proxy_type.startswith('socks') else 'http'
    host = str(proxy.get('host') or '').strip()
    port = proxy.get('port')
    if not host or port in (None, ''):
        if _to_bool(proxy.get('enabled'), False):
            raise Exception('Proxy server URL is invalid')
        return ''
    if host.startswith('[') and host.endswith(']'):
        host = host[1:-1]
    if ':' in host:
        host = f'[{host}]'

    username = str(proxy.get('username') or '')
    password = str(proxy.get('password') or '')
    auth = urllib.parse.quote(username, safe='')
    if password:
        auth += ':' + urllib.parse.quote(password, safe='')
    if username or password:
        auth += '@'
    return _normalize_proxy_url(f'{scheme}://{auth}{host}:{port}')


def _legacy_proxy_from_url(url, enabled=False):
    if not url:
        return {
            'enabled': bool(enabled),
            'type': 'http',
            'host': '',
            'port': None,
            'username': '',
            'password': '',
        }
    parts = urllib.parse.urlsplit(url)
    return {
        'enabled': bool(enabled),
        'type': 'socks5' if parts.scheme.startswith('socks') else 'http',
        'host': parts.hostname or '',
        'port': parts.port,
        'username': urllib.parse.unquote(parts.username or ''),
        'password': urllib.parse.unquote(parts.password or ''),
    }


def _decode_proxy_record(raw):
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        value = raw
    if isinstance(value, dict):
        url = _normalize_proxy_url(value.get('url'))
        enabled = _to_bool(value.get('enabled'), bool(url))
    else:
        url = _normalize_proxy_url(value)
        enabled = bool(url)
    if enabled and not url:
        raise Exception('Proxy server URL is invalid')
    return {'enabled': enabled, 'url': url}


def getProxyServer():
    raw = systemConfigMapper.getConfigValue(PROXY_SERVER_KEY)
    if raw is not None:
        try:
            return _decode_proxy_record(raw)
        except Exception:
            return _default_proxy_server()

    legacy_raw = systemConfigMapper.getConfigValue(TMDB_PROXY_KEY)
    if not legacy_raw:
        return _default_proxy_server()
    try:
        legacy_proxy = json.loads(legacy_raw)
        return {
            'enabled': _to_bool(legacy_proxy.get('enabled'), False),
            'url': _legacy_proxy_to_url(legacy_proxy),
        }
    except Exception:
        return _default_proxy_server()


def getTmdbProxy():
    proxy = getProxyServer()
    return _legacy_proxy_from_url(proxy['url'], proxy['enabled'])


def _safe_proxy_url(url):
    if not url:
        return ''
    parts = urllib.parse.urlsplit(url)
    if parts.password is None:
        return url
    host_port = parts.netloc.rsplit('@', 1)[-1]
    netloc = f'{parts.username}@{host_port}' if parts.username else host_port
    return urllib.parse.urlunsplit((
        parts.scheme,
        netloc,
        '',
        '',
        '',
    ))


def _public_proxy_server(proxy):
    url = proxy.get('url') or ''
    parts = urllib.parse.urlsplit(url)
    return {
        'enabled': bool(proxy.get('enabled')),
        'url': _safe_proxy_url(url),
        'passwordSet': bool(parts.password),
    }


def _public_tmdb_proxy(proxy):
    public = _legacy_proxy_from_url(proxy.get('url') or '', proxy.get('enabled'))
    public['passwordSet'] = bool(public['password'])
    public['password'] = ''
    return public


def _proxy_url_for_test(req):
    current_url = getProxyServer().get('url') or ''
    submitted_url = None
    if 'url' in req:
        submitted_url = _normalize_proxy_url(req.get('url'))

    if submitted_url is None:
        proxy_url = current_url
    elif submitted_url == _safe_proxy_url(current_url):
        proxy_url = current_url
    else:
        proxy_url = submitted_url

    return proxy_url


def testProxyServer(req):
    proxy_url = _proxy_url_for_test(req)
    client = mediaRenamer.TMDbClient(proxy={'url': proxy_url})
    started = time.monotonic()
    try:
        response = client.session.get(
            PROXY_TEST_URL,
            timeout=PROXY_TEST_TIMEOUT,
            proxies=client.proxies,
            allow_redirects=False,
        )
        try:
            status_code = response.status_code
        finally:
            response.close()
        if status_code != 204:
            raise Exception(f'Proxy test expected HTTP 204, got HTTP {status_code}')
        return {
            'url': PROXY_TEST_URL,
            'latencyMs': max(0, round((time.monotonic() - started) * 1000)),
            'statusCode': status_code,
        }
    except mediaRenamer.requests.RequestException as exc:
        error = client._redact_error(exc)
        raise Exception(f'Proxy test failed: {error}') from None
    finally:
        client.session.close()


def normalize_exclude(exclude):
    if exclude is None:
        return None
    if isinstance(exclude, list):
        items = exclude
    else:
        items = str(exclude).split(':')
    items = [str(item).strip() for item in items if str(item).strip()]
    return ':'.join(items) if items else None


def getGlobalExclude():
    return systemConfigMapper.getConfigValue(GLOBAL_EXCLUDE_KEY)


def getConfig():
    proxy = getProxyServer()
    return {
        'globalExclude': getGlobalExclude(),
        'proxyServer': _public_proxy_server(proxy),
        'tmdbProxy': _public_tmdb_proxy(proxy),
    }


def revealProxyServer():
    proxy = getProxyServer()
    return {'url': proxy.get('url') or ''}


def updateConfig(req):
    update_global_exclude = 'globalExclude' in req
    global_exclude = normalize_exclude(req.get('globalExclude')) if update_global_exclude else None
    proxy_url_to_save = None
    update_proxy = False

    if 'proxyServer' in req:
        update = req.get('proxyServer')
        if isinstance(update, dict):
            current = getProxyServer()
            proxy_enabled = _to_bool(update.get('enabled'), current['enabled'])
            proxy_url_to_save = current['url']
            if 'url' in update:
                submitted_url = _normalize_proxy_url(update.get('url'))
                proxy_url_to_save = (
                    current['url']
                    if submitted_url == _safe_proxy_url(current['url'])
                    else submitted_url
                )
                update_proxy = True
            if 'enabled' in update:
                update_proxy = True
            if proxy_enabled and not proxy_url_to_save:
                raise Exception('Proxy server URL is required when enabled')
        elif isinstance(update, str):
            proxy_url_to_save = _normalize_proxy_url(update)
            proxy_enabled = bool(proxy_url_to_save)
            update_proxy = True
        else:
            raise Exception('Proxy server configuration must be an object or URL')
    elif 'tmdbProxy' in req:
        update = req.get('tmdbProxy')
        if not isinstance(update, dict):
            raise Exception('Proxy server configuration must be an object')
        proxy = getTmdbProxy()
        current_identity = _safe_proxy_url(_legacy_proxy_to_url(proxy))
        for key in ('enabled', 'type', 'host', 'port', 'username'):
            if key in update:
                proxy[key] = update[key]
        if _to_bool(update.get('clearPassword'), False):
            proxy['password'] = ''
        elif update.get('password') not in (None, ''):
            proxy['password'] = str(update['password'])
        elif _safe_proxy_url(_legacy_proxy_to_url(proxy)) != current_identity:
            proxy['password'] = ''
        proxy_url_to_save = _legacy_proxy_to_url(proxy)
        proxy_enabled = _to_bool(proxy.get('enabled'), False)
        update_proxy = True

    if update_global_exclude:
        systemConfigMapper.setConfigValue(GLOBAL_EXCLUDE_KEY, global_exclude)
    if update_proxy:
        systemConfigMapper.setConfigValue(
            PROXY_SERVER_KEY,
            json.dumps({
                'enabled': proxy_enabled,
                'url': proxy_url_to_save,
            }, ensure_ascii=False),
        )
    return getConfig()
