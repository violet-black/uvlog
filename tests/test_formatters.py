import io
from datetime import datetime

import pytest

import uvlog


class ErrorRepr(Exception):

    def json_repr(self):
        return {
            'value': 42
        }


def _raise_error():
    local_var = 11
    raise ValueError('error')


EXC_TB = None


try:
    _raise_error()
except ValueError as exc:
    EXC_TB = exc


@pytest.fixture
def log_record() -> uvlog.LogRecord:
    return uvlog.LogRecord(
        name='test',
        level='INFO',
        levelno=20,
        asctime=datetime.now(),
        message='test message',
        exc_info=None,
        args=None,
        extra={'extra_attr': 'extra'},
        ctx={'ctx_attr': 'ctx'},
        filename=None,
        lineno=None,
        func=None,
    )


def patch_stream_handlers(logger):
    for handler in logger.handlers:
        handler._stream = io.BytesIO()


def read(logger):
    logger.handlers[0]._stream.seek(0)
    return logger.handlers[0]._stream.read()


@pytest.mark.parametrize(['config', 'msg', 'kws', 'result'], [
    ({'format': '{message}'}, 'test message', {}, b'test message\n'),
    ({'format': '{message}'}, 'test message {name}', {'name': 'test'}, b'test message test\n'),
    ({'format': '{level} : {message}'}, 'test message', {'name': 'test'}, b'INFO : test message\n'),
    ({'format': '{message}'}, 'test message', {'exc_info': ValueError('error')}, b'test message\nValueError: error\n')
], ids=[
    'simple message',
    'formatted kwargs',
    'log format',
    'exception handling'
])
def test_text_formatter(config, msg, kws, result):
    logger = uvlog.configure({
        'handlers': {'stderr': {'formatter': 'text'}},
        'formatters': {'text': config}
    })
    print(str(logger.handlers[0].formatter))
    patch_stream_handlers(logger)
    logger.info(msg, **kws)
    assert read(logger) == result


@pytest.mark.parametrize(['config', 'msg', 'kws', 'result'], [
    ({'keys': ['message']}, 'test message', {}, b'{"message": "test message"}\n'),
    ({'keys': ['message']}, 'test message {name}', {'name': 'test'},  b'{"message": "test message test"}\n'),
    (
        {'keys': ['message', 'exc_info']},
        'test message',
        {'exc_info': ValueError('error')},
        b'{"message": "test message", "exc_info": {"message": "error", "type": "ValueError", "data": {}}}\n'
    ),
    (
        {'keys': ['message', 'exc_info']},
        'test message',
        {'exc_info': ErrorRepr('error')},
        b'{"message": "test message", "exc_info": {"message": "error", "type": "ErrorRepr", "data": {"value": 42}}}\n'
    ),
    (
        {'keys': ['message', 'exc_info'], 'exc_pass_locals': True, 'exc_pass_filenames': False},
        'test message',
        {'exc_info': EXC_TB},
        b'{"message": "test message", "exc_info": {"message": "error", "type": "ValueError", "data": {}, "traceback": {"lineno": 19, "func": "_raise_error", "locals": {"local_var": 11}}}}\n'
    ),
], ids=[
    'simple message',
    'formatted kwargs',
    'exception handling',
    'exception with json_repr',
    'exception with traceback'
])
def test_json_formatter(config, msg, kws, result):
    logger = uvlog.configure({
        'handlers': {'stderr': {'formatter': 'json'}},
        'formatters': {'json': config}
    })
    print(str(logger.handlers[0].formatter))
    patch_stream_handlers(logger)
    logger.info(msg, **kws)
    assert read(logger) == result


def test_timestamps():
    logger = uvlog.configure({
        'handlers': {'stderr': {'formatter': 'json'}},
        'formatters': {'json': {'keys': ['asctime']}}
    })
    print(str(logger.handlers[0].formatter))
    patch_stream_handlers(logger)
    logger.info('test message')
    assert b'asctime' in read(logger)
