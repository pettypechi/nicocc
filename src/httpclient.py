# coding: utf-8

__all__ = [
    'represent_default',
    'handle_error_default',
    'RepresentError',
    'HttpClient',
]

from http.cookiejar import CookieJar
from urllib.request import (
    build_opener,
    Request,
    HTTPCookieProcessor,
)
from urllib.parse import (
    urlencode,
)
from time import sleep
from datetime import datetime
from logging import getLogger

from resource import TZ


class RepresentError(Exception):
    pass


def represent_default(req, res):
    if res.status != 200:
        logger.warning('%s (%d) - %s', res.method, res.status, res.url)
        raise RepresentError('%s (%d) - %s' % res.method, res.status, req.full_url)
    return res


def handle_error_default(req, err):
    if hasattr(err, 'status') and (err.status // 100) == 5:
        sleep(30)
    raise err


logger = getLogger(__name__)


class HttpClient:
    def __init__(self, r):
        self._r = r
        self._lastaccess = None
        self._cookiejar = CookieJar()

    def remove_user_session(self):
        try:
            self._cookiejar.clear('.nicovideo.jp', '/', 'user_session')
        except KeyError:
            pass
        try:
            self._cookiejar.clear('.nicovideo.jp', '/', 'user_session_secure')
        except KeyError:
            pass

    def get_user_session(self)        :
        for cookie in self._cookiejar:
            if cookie.name == 'user_session' and cookie.path == '/' and cookie.domain == '.nicovideo.jp':
                return cookie.value

    def get_user_session_secure(self)        :
        for cookie in self._cookiejar:
            if cookie.name == 'user_session_secure' and cookie.path == '/' and cookie.domain == '.nicovideo.jp':
                return cookie.value

    def request(self, url, data=None, method=None, headers=None, cookie=True, represent_func=None,
                handle_error_func=None):
        headers = headers or {}
        headers['User-Agent'] = self._r.str.user_agent
        data = urlencode(data) if isinstance(data, dict) and 'Content-Type' not in headers else data
        if isinstance(data, str):
            data = data.encode()
        request = Request(url, data=data, headers=headers, method=method)
        opener = build_opener(HTTPCookieProcessor(cookiejar=self._cookiejar)) if cookie else build_opener()
        for i in range(self._r.config.http.retry + 1):
            if self._lastaccess:
                delta = self._lastaccess + self._r.config.http.interval - datetime.now(TZ).timestamp()
                if delta > 0:
                    sleep(delta)
            logger.debug('HTTPリクエスト %s - %s', request.get_method(), url)
            try:
                response = opener.open(request)
            except Exception as err:
                try:
                    response = (handle_error_func if handle_error_func else handle_error_default)(request, err)
                except Exception as err:
                    logger.warning(err)
                    continue
                return response
            finally:
                self._lastaccess = datetime.now(TZ).timestamp()
            try:
                response = (represent_func if represent_func else represent_default)(request, response)
            except Exception as err:
                logger.warning(err)
                continue
            return response
        return None
