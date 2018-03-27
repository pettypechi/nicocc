# coding: utf-8

__all__ = [
    'abort',
    'puts',
    'TZ',
    'HELP',
]

import sys, pytz

TZ = pytz.timezone('Asia/Tokyo')

def puts(msg, logger):
    logger.info(msg)
    print(msg)

def abort(msg, logger):
    logger.fatal(msg)
    print(msg, file=sys.stderr)
    sys.exit(1)

HELP = '''\
Usage:
    nicocc <対象となる nicocc.toml を含むフォルダのパス> ...
    nicocc --show-config <対象となる nicocc.toml を含むフォルダのパス> ...
    nicocc --version
    nicocc --help
'''
