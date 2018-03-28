# coding: utf-8

__version__ = '0.2.6-SNAPSHOT'

import sys

if sys.version_info.major < 3:
    print >> sys.stderr, u'nicocc は Python 2.x.x には対応していません。'
    sys.exit(1)

from os import path
from logging import getLogger

from util import *
from resource import *
from proc import *

if __name__ == '__main__':
    logger = getLogger(__name__)

    if len(sys.argv) < 2 or sys.argv[1] in ('--help','-h',):
        print(HELP, file=sys.stderr)
        sys.exit(1)
    if sys.argv[1] in ('--version','-v',):
        print('nicocc v%s' % __version__, file=sys.stderr)
        sys.exit(1)
    if sys.argv[1] in ('--show-config','-c',):
        for arg in sys.argv[2:]:
            print('%s の設定値' % arg)
            print(Resource(arg).config)
        sys.exit(1)
    for arg in sys.argv[1:]:
        with Resource(arg) as r:
            puts('%s の処理を開始します。' % arg, logger)
            print(r.config, end='')
            if r.config.counter.overwrite_videos or not path.isfile(r.path.videos_csv):
                generate_videos_csv(r)
            generate_result_csv(r)
            puts('%s の処理を正常に終了しました。' % arg, logger)
