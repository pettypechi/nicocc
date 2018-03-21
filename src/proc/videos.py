# coding: utf-8

__all__ = ['generate_videos_csv']

import csv, re, json, shutil
from logging import getLogger

from util import *
from httpclient import (
    represent_default,
    RepresentError,
)

logger = getLogger(__name__)

_MYLIST_REGEX = re.compile(r'^\s*Mylist\.preload\([0-9]+, (\[.*\])\);$', re.M)


def get_videos(r, mylist_id):
    def represent(req, res):
        res = represent_default(req, res)
        data = res.read().decode()
        m = _MYLIST_REGEX.search(data)
        if m is None:
            raise RepresentError('マイリストデータの解析に失敗しました。')
        try:
            mylists = json.loads(m.group(1))
        except:
            raise RepresentError('マイリストデータの解析に失敗しました。%s' % data)
        return [(mylist['item_data']['video_id'], mylist['item_data']['title'],) for mylist in mylists if
                mylist['item_type'] == 0]

    videos = r.client.request(
        r.url.get_mylist_url(mylist_id),
        cookie=False,
        represent_func=represent,
    )
    if videos is None:
        abort('マイリスト %d の取得に失敗しました。' % mylist_id, logger)
    logger.debug('マイリスト %d から %d 件の動画情報を取得しました。', mylist_id, len(videos))
    return videos


def generate_videos_csv(r):
    videos_csv = r.path.videos_csv
    videos_temp_csv = r.path.videos_temp_csv
    with open(videos_temp_csv, 'w', encoding=r.config.counter.encoding) as f:
        writer = csv.writer(f, lineterminator='\n')
        for mylist_id in r.config.counter.mylist:
            videos = get_videos(r, mylist_id)
            try:
                writer.writerows(videos)
            except Exception as err:
                abort(err, logger)
    shutil.move(videos_temp_csv, videos_csv)
    puts('動画リストを %s に出力しました。' % videos_csv, logger)
