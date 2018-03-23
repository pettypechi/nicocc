# coding: utf-8

__all__ = [
    'Resource',
]

import os
from os import path
from logging import (
    basicConfig,
    FileHandler,
)
from datetime import datetime

from filelock import FileLock

from util import TZ
from config import parse_config
from httpclient import HttpClient


class PathInfo:
    def __init__(self, dir):
        self.work_dir = dir
        self.config_file = path.join(dir, 'nicocc.toml')
        self.temp_dir = path.join(dir, 'tmp')
        self.log_dir = path.join(dir, 'log')
        self.videos_csv = path.join(dir, 'videos.csv')
        self.videos_temp_csv = path.join(self.temp_dir, '_videos.csv')
        self.result_csv = path.join(dir, 'result.csv')
        self.result_temp_csv = path.join(self.temp_dir, '_result.csv')
        self.comment_dir = None

    def _get_comment_file(self, filename):
        return path.join(self.comment_dir, filename)

    def get_comment_temp_csv(self, video_id):
        return self._get_comment_file('_%s.csv' % video_id)

    def get_comment_csv(self, video_id):
        return self._get_comment_file('%s.csv' % video_id)


class UrlInfo:
    def __init__(self):
        self.login_url = 'https://secure.nicovideo.jp/secure/login?site=niconico'
        self.api_json_url = 'http://nmsg.nicovideo.jp/api.json/'

    def get_video_url(self, video_id):
        return 'http://www.nicovideo.jp/watch/%s' % video_id

    def get_waybackkey_url(self, thread_id):
        return 'http://www.nicovideo.jp/api/getwaybackkey?thread=%s' % thread_id

    def get_mylist_url(self, mylist_id):
        return 'http://www.nicovideo.jp/mylist/%d' % mylist_id

    def get_flapi_url(self, video_id):
        return 'http://flapi.nicovideo.jp/api/getflv/%s' % video_id


class StringInfo:
    def __init__(self):
        from nicocc import __version__
        self.version = __version__
        self.user_agent = 'python-nicocc/%s' % __version__


class Resource:
    def __init__(self, dir):
        dir = dir if path.isabs(dir) else path.join(os.getcwd(), dir)
        self.path = PathInfo(dir)
        self.url = UrlInfo()
        self.str = StringInfo()
        self.config = parse_config(self.path.config_file)
        self.client = HttpClient(self)

        comment_dirname = '%s_%s_%s' % (
            self.config.counter.start.strftime('%y%m%d-%H%M%S'),
            self.config.counter.end.strftime('%y%m%d-%H%M%S'),
            self.config.counter.encoding,
        )
        self.path.comment_dir = path.join(self.path.temp_dir, self.str.version, comment_dirname)

        if not path.isdir(self.path.comment_dir):
            os.makedirs(self.path.comment_dir)
        if not path.isdir(self.path.log_dir):
            os.makedirs(self.path.log_dir)
        basicConfig(
            level=self.config.logging.level,
            format=self.config.logging.format,
            handlers=[
                FileHandler(
                    path.join(
                        self.path.log_dir,
                        datetime.now(tz=TZ).strftime('nicocc-%y%m%d-%H%M%S.log'),
                    ),
                    encoding='utf-8',
                )
            ],
        )

    def __enter__(self):
        self._filelock = FileLock(path.join(self.path.temp_dir, 'nicocc.lock'))
        self._filelock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._filelock.release()
