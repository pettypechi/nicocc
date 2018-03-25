# condig: utf-8

__all__ = ['generate_result_csv']

import csv, re, json, shutil, os
from os import path
from datetime import datetime
from collections import OrderedDict
from logging import getLogger
from html.parser import HTMLParser
from urllib.parse import (
    parse_qs,
)
from time import sleep

from httpclient import *
from util import *

logger = getLogger(__name__)

_VIDEO_ID_REGEX = re.compile(r'^(sm)?[0-9]+$')


def load_videos(r):
    logger.debug('動画リストファイルから動画情報を読み込みます。')
    videos = OrderedDict()
    with open(r.path.videos_csv, 'r', encoding=r.config.counter.encoding, errors='xmlcharrefreplace') as f:
        reader = csv.reader(f)
        i = 0
        for row in reader:
            i += 1
            length = len(row)
            if length > 0:
                if _VIDEO_ID_REGEX.match(row[0]):
                    videos[row[0]] = row[1] if length > 1 else ''
                else:
                    logger.debug('"%s", %d行目: 不正な動画ID "%s"', r.path.videos_csv, i, row[0])
    logger.debug('動画リストファイルから %d 件の動画情報を読み込みました。' % len(videos))
    return videos


def login(r):
    r.client.remove_user_session()
    response = r.client.request(
        r.url.login_url,
        data={
            'mail': r.config.user.mail,
            'password': r.config.user.password,
        },
    )
    if not response or not r.client.get_user_session() or not r.client.get_user_session_secure():
        abort('ログインに失敗しました。', logger)
    logger.debug('ログインに成功しました。')


class VideoInfoParser(HTMLParser):
    def __init__(self, info):
        super().__init__()
        self._info = info

    def handle_starttag(self, tag, attrs):
        if not self._info.done and tag == 'div':
            for name, value in attrs:
                if name == 'id' and value == 'js-initial-watch-data':
                    for name, value in attrs:
                        if name == 'data-api-data':
                            self._info.init(value)
                            return


class VideoInfoError(Exception):
    pass


class VideoInfo:
    def __init__(self):
        self.done = False

    def init(self, d):
        if self.done:
            return
        try:
            data = json.loads(d)
        except:
            logger.debug('JSON: %s' % d)
            raise VideoInfoError('JSONの解析に失敗しました。')
        try:
            self.user_id = int(data['viewer']['id'])
            self.thread_id = data['thread']['ids']['default']
            self.duration = int(data['video']['duration'])
            self.title = data['video']['title']
            self.attr = 'NORMAL'
            self.done = True
        except:
            logger.debug('動画情報JSON - %s' % d)
            raise VideoInfoError('動画情報JSONの解析に失敗しました。')

    def init_flapi(self, qs, attr):
        try:
            data = parse_qs(qs)
        except:
            logger.debug('動画情報クエリ文字列 - %s' % qs)
            raise VideoInfoError('動画情報クエリ文字列の解析に失敗しました。')
        try:
            self.user_id = int(data['user_id'][0])
            self.thread_id = data['thread_id'][0]
            self.duration = int(data['l'][0])
            self.title = ''
            self.attr = attr
            self.done = True
        except:
            logger.debug('動画情報クエリ文字列 - %s' % qs)
            raise VideoInfoError('動画情報クエリ文字列の解析に失敗しました。')

    def __repr__(self):
        return 'user_id=%d, thread_id=%s, duration=%d, title=%s, attr=%s' % (
            self.user_id, self.thread_id, self.duration, self.title, self.attr,
        )


def get_video_info_flapi(r, video_id, attr):
    def represent(req, res):
        try:
            res = represent_default(req, res)
            qs = res.read().decode()
            video_info = VideoInfo()
            video_info.init_flapi(qs, attr)
            return video_info
        except RepresentError as err:
            login(r)
            raise err

    logger.debug('flapi から %s の動画情報を取得します。' % video_id)
    return r.client.request(
        r.url.get_flapi_url(video_id),
        represent_func=represent,
    )


def get_video_info(r, video_id):
    def represent(req, res):
        try:
            res = represent_default(req, res)
            video_info = VideoInfo()
            parser = VideoInfoParser(video_info)
            data = res.read().decode()
            try:
                parser.feed(data)
            except VideoInfoError as err:
                raise RepresentError(err)
            except:
                pass
            if not video_info.done:
                logger.debug('%s の動画情報が見つかりませんでした。' % video_id)
                return get_video_info_flapi(r, video_id, 'FLASH_ONLY')
            return video_info
        except RepresentError as err:
            login(r)
            raise err

    def handle_error(req, err):
        try:
            handle_error_default(req, err)
        except Exception as err:
            if hasattr(err, 'status'):
                if err.status == 403:
                    logger.debug('%s の動画は非公開になっています。' % video_id)
                    return get_video_info_flapi(r, video_id, 'PRIVATE')
                elif err.status == 404:
                    logger.debug('%s の動画は削除されています。' % video_id)
                    return get_video_info_flapi(r, video_id, 'DELETED')
            raise err

    logger.debug('%s の動画情報を取得します。' % video_id)
    video_info = r.client.request(
        r.url.get_video_url(video_id),
        represent_func=represent,
        handle_error_func=handle_error,
    )
    if not video_info:
        abort('動画情報の取得に失敗しました。(video_id=%s)' % video_id, logger)
    logger.debug('%s 動画情報を取得しました。 - %s' % (video_id, video_info))
    return video_info


def get_waybackkey(r, thread_id):
    def represent(req, res):
        try:
            res = represent_default(req, res)
            data = res.read().decode()
            data_dict = parse_qs(data)
            waybackkey = data_dict.get('waybackkey', [''])[0]
            if not waybackkey:
                logger.debug('waybackkey クエリ文字列 - %s' % data)
                raise RepresentError('waybackkey の解析に失敗しました。', is_server_error=True)
            return waybackkey
        except RepresentError as err:
            login(r)
            raise err

    logger.debug('thread_id=%s の waybackkey を取得します。' % thread_id)
    waybackkey = r.client.request(
        r.url.get_waybackkey_url(thread_id),
        represent_func=represent,
    )
    if not waybackkey:
        abort('waybackkey の取得に失敗しました。(thread_id=%s)' % thread_id, logger)
    logger.debug('thread_id=%s の waybackkey を取得しました。 - %s', thread_id, waybackkey)
    return waybackkey


def get_comments(r, video_info, waybackkey, when, last_no):
    def represent(req, res):
        try:
            res = represent_default(req, res)
            data = res.read().decode()
            rows = json.loads(data)
            start = r.config.counter.start.timestamp()
            end = r.config.counter.end.timestamp()
            result = []
            for row in rows:
                if 'chat' in row and start <= row['chat']['date'] <= end and (
                        last_no is None or last_no > row['chat']['no']):
                    result.append(row['chat'])
                elif 'thread' in row and row['thread']['resultcode'] != 0:
                    abort('コメントデータのパラメータが不正です。', logger)
            return result
        except RepresentError as err:
            login(r)
            raise err

    data = [
        {'ping': {'content': 'rs:1'}},
        {'ping': {'content': 'ps:11'}},
        {'thread': {
            'fork': 0,
            'nicoru': 0,
            'res_from': -1000,
            'scores': 1,
            'thread': video_info.thread_id,
            'user_id': str(video_info.user_id),
            'version': '20090904',
            'waybackkey': waybackkey,
            'when': when + 1,
            'with_global': 1,
        }},
        {'ping': {'content': 'pf:11'}},
        {'ping': {'content': 'rf:1'}},
    ]
    comments = r.client.request(
        r.url.api_json_url,
        method='POST',
        headers={
            'Content-Type': 'application/json',
        },
        data=json.dumps(data),
        represent_func=represent,
    )
    if comments is None:
        abort('コメントの取得に失敗しました。', logger)
    logger.debug('%d 件のコメントを取得しました。', len(comments))
    return comments


def generate_result_csv(r):
    videos = load_videos(r)
    login(r)
    i = 0
    for video_id, video_title in videos.items():
        i += 1
        comment_csv = r.path.get_comment_csv(video_id)
        comment_temp_csv = r.path.get_comment_temp_csv(video_id)
        if path.isfile(comment_csv):
            puts('%s のコメント取得をスキップ (%d / %d)' % (video_id, i, len(videos)), logger)
            continue
        else:
            puts('%s のコメント取得を開始 (%d / %d)' % (video_id, i, len(videos)), logger)
        video_info = get_video_info(r, video_id)
        waybackkey = get_waybackkey(r, video_info.thread_id)
        when = int(r.config.counter.end.timestamp())
        last_no = None
        with open(comment_temp_csv, mode='w', encoding=r.config.counter.encoding, errors='xmlcharrefreplace') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow((
                '動画ID',
                '動画タイトル',
                '動画属性',
                'コメント番号',
                'ユーザーID',
                'プレミアム会員フラグ',
                '匿名フラグ',
                '削除フラグ',
                'VPOS',
                'NGスコア',
                'コマンド',
                'コメント',
                '書き込み日時',
            ))
            while True:
                comments = get_comments(r, video_info, waybackkey, when, last_no)
                if len(comments) == 0:
                    break
                comments.reverse()
                for comment in comments:
                    if comment['date'] < when:
                        when = comment['date']
                    if last_no is None or comment['no'] < last_no:
                        last_no = comment['no']
                    try:
                        writer.writerow((
                            video_id,
                            video_title or video_info.title,
                            video_info.attr,
                            comment['no'],
                            comment.get('user_id', ''),
                            comment.get('premium', 0),
                            comment.get('anonymity', 0),
                            comment.get('deleted', 0),
                            comment['vpos'],
                            comment.get('score', 0),
                            comment.get('mail', ''),
                            comment.get('content', ''),
                            datetime.fromtimestamp(comment['date'], tz=TZ).strftime('%Y-%m-%d %H:%M:%S'),
                        ))
                    except Exception as err:
                        abort(err, logger)
                if last_no == 1:
                    break
        shutil.move(comment_temp_csv, comment_csv)

    result_csv = r.path.result_csv
    result_temp_csv = r.path.result_temp_csv
    with open(result_temp_csv, mode='w', encoding=r.config.counter.encoding, errors='xmlcharrefreplace') as wf:
        writer = csv.writer(wf, lineterminator='\n')
        writer.writerow((
            '動画ID',
            '動画タイトル',
            'プレミアム会員ユニークコメント',
            '匿名プレミアム会員ユニークコメント',
            '一般会員ユニークコメント',
            '匿名一般会員ユニークコメント',
        ))
        for video_id, video_title in videos.items():
            result = {
                'premium': set(),
                'premium_184': set(),
                'general': set(),
                'general_184': set(),
            }
            title = None
            attr = None
            comment_csv = r.path.get_comment_csv(video_id)
            if path.isfile(comment_csv):
                with open(comment_csv, 'r', encoding=r.config.counter.encoding, errors='xmlcharrefreplace') as rf:
                    reader = csv.reader(rf)
                    row = next(reader)
                    if row[0] != '動画ID':
                        abort('コメントファイル "%s" が不正です。' % comment_csv, logger)
                    for row in reader:
                        if title is None:
                            title = row[1] or video_title
                        if row[4] == '':
                            continue
                        if row[5] == '1':
                            if row[6] == '1':
                                result['premium_184'].add(row[4])
                            else:
                                result['premium'].add(row[4])
                        elif row:
                            if row[6] == '1':
                                result['general_184'].add(row[4])
                            else:
                                result['general'].add(row[4])
            try:
                writer.writerow((
                    video_id,
                    title or video_title,
                    len(result['premium']),
                    len(result['premium_184']),
                    len(result['general']),
                    len(result['general_184']),
                ))
            except Exception as err:
                abort(err, logger)
    if path.isfile(result_csv):
        os.remove(result_csv)
    shutil.move(result_temp_csv, result_csv)
    puts('集計結果を %s に出力しました。' % result_csv, logger)
