# coding: utf-8

__all__ = ['parse_config']

import toml, re, sys
from datetime import datetime
from logging import (
    FATAL,
    CRITICAL,
    ERROR,
    WARNING,
    INFO,
    DEBUG,
    NOTSET
)

from util import TZ


class ParserError(Exception):
    def __init__(self, *values):
        super().__init__(values[0].format(*values[1:]))


class Config:
    pass


class Parser:
    def __init__(self, key, **kwargs):
        self._key = key
        self._default_value = kwargs.get('default_value')
        self._validate_func = kwargs.get('validate_func')
        self._represent_func = kwargs.get('represent_func')

    @property
    def key(self):
        return self._key

    def validate(self, value, file):
        pass

    def represent(self, value, file):
        return value

    def get_default(self):
        return self._default_value

    def parse(self, value, file):
        try:
            self.validate(value, file)
            if self._validate_func:
                self._validate_func(value, file)
            result = self.represent(value, file)
            if self._represent_func:
                return self._represent_func(result)
            return result
        except ParserError as err:
            default_value = self.get_default()
            if default_value is not None:
                return default_value
            print(err, file=sys.stderr)
            sys.exit(1)


class TypeParser(Parser):
    def __init__(self, type, key, **kwargs):
        super().__init__(key, **kwargs)
        self._type = type

    def validate(self, value, file):
        if not isinstance(value, self._type):
            raise ParserError('設定ファイル "{}" のパラメータ "{}" が不正です。{}型を記述してください。', file, self.key, self._type)


class StringParser(TypeParser):
    def __init__(self, key, **kwargs):
        super().__init__(str, key, **kwargs)


class IntParser(TypeParser):
    def __init__(self, key, **kwargs):
        super().__init__(int, key, **kwargs)


class UIntParser(IntParser):
    def validate(self, value, file):
        super().validate(value, file)
        if value < 0:
            raise ParserError('設定ファイル "{}" のパラメータ "{}" は符号なし整数を記述してください。', file, self.key)


class BoolParser(TypeParser):
    def __init__(self, key, **kwargs):
        super().__init__(bool, key, **kwargs)


class UIntListParser(TypeParser):
    def __init__(self, key, **kwargs):
        super().__init__(list, key, **kwargs)

    def validate(self, value, file):
        super().validate(value, file)
        for item in value:
            if not isinstance(item, int):
                raise ParserError('設定ファイル "{}" のパラメータ "{}" は符号なし整数のリストを記述してください。', file, self.key)
            if item < 0:
                raise ParserError('設定ファイル "{}" のパラメータ "{}" は符号なし整数のリストを記述してください。', file, self.key)


_DATETIME_REGEX = re.compile(r'^([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})$')


class DateParser(StringParser):
    def represent(self, value, file):
        m = _DATETIME_REGEX.match(value)
        if m:
            return TZ.localize(datetime(
                int(m.group(1)),
                int(m.group(2)),
                int(m.group(3)),
                int(m.group(4)),
                int(m.group(5)),
                int(m.group(6)),
            ))
        raise ParserError(
            '設定ファイル "{}" のパラメータ "{}" が不正です。"[西暦(4桁)]-[月(2桁)]-[日(2桁)] [時(2桁)]:[分(2桁)]:[秒(2桁)]" の形式で記述してください。', file,
            self.key)


_LEVEL_DICT = {
    'CRITICAL': CRITICAL,
    'FATAL': FATAL,
    'ERROR': ERROR,
    'WARN': WARNING,
    'WARNING': WARNING,
    'INFO': INFO,
    'DEBUG': DEBUG,
    'NOTSET': NOTSET,
}

_PARSER_DICT = {
    'user': {
        'mail': StringParser('user.mail'),
        'password': StringParser('user.password'),
    },
    'counter': {
        'start': DateParser('counter.start'),
        'end': DateParser('counter.end'),
        'mylist': UIntListParser(
            'counter.mylist',
            default_value=[],
        ),
        'overwrite_videos': BoolParser(
            'counter.overwrite_videos',
            default_value=True,
        ),
        'encoding': StringParser(
            'counter.encoding',
            default_value='cp932',
        )
    },
    'http': {
        'interval': UIntParser(
            'counter.interval',
            default_value=1,
            represent_func=lambda _: _ / 1000,
        ),
        'server_error_interval': UIntParser(
            'counter.server_error_interval',
            default_value=30,
            represent_func=lambda _: _ / 1000,
        ),
        'retry': UIntParser(
            'counter.interval',
            default_value=2,
        ),
    },
    'logging': {
        'level': StringParser(
            'logging.level',
            represent_func=lambda _: _LEVEL_DICT.get(_, INFO),
        ),
        'format': StringParser(
            'logging.format',
            default_value='[%(levelname)s] %(asctime)s - %(name)s: %(message)s',
        )
    },
}


def parse_config(config_file):
    try:
        config_dict = toml.load(config_file)
    except Exception:
        print('設定ファイル "%s" の読み込みに失敗しました。' % config_file, file=sys.stderr)
        sys.exit(1)

    config = Config()

    for name, parser_dict in _PARSER_DICT.items():
        setattr(config, name, Config())
        section_dict = config_dict.get(name)
        if not isinstance(section_dict, dict):
            section_dict = {}
        for k, v in parser_dict.items():
            setattr(getattr(config, name), k, v.parse(section_dict.get(k), config_file))

    return config
