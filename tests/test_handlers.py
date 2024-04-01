import pytest

import uvlog


@pytest.mark.parametrize('cls', ['StreamHandler', 'QueueStreamHandler'])
def test_std_handler(cls):
    logger = uvlog.configure({
        'loggers': {'': {'handlers': ['stderr', 'stdout']}},
        'handlers': {'stderr': {'class': cls}, 'stdout': {'class': cls}},
        'formatters': {'text': {'format': '{message}'}},
    })
    print(str(logger.handlers[0]))
    logger.info('message')


@pytest.mark.parametrize('cls', ['StreamHandler', 'QueueStreamHandler'])
def test_io_error(tmpdir, cls):

    def _raise_io_error(*args, **kws):
        raise IOError('error')

    log_file = tmpdir / f'test_{cls}_io_error.log'
    route = f'file://{str(log_file)}'
    logger = uvlog.configure({
        'loggers': {'': {'handlers': [route]}},
        'handlers': {route: {'cls': cls}},
        'formatters': {'text': {'format': '{message}'}},
    })
    logger.info('')  # init stream
    _stream = logger.handlers[0]._stream
    _write = _stream.write
    _stream.write = _raise_io_error
    logger.info('message')
    _stream.write = _write
    _stream.flush()
    # assert capsys.readouterr().err.startswith('--- Logging error ---')  # capsys is currently unstable in pytest


@pytest.mark.parametrize('cls', ['StreamHandler', 'QueueStreamHandler'])
def test_file_handler(tmp_path, cls):
    log_file = tmp_path / f'test_{cls}.log'
    route = f'file://{str(log_file)}'
    logger = uvlog.configure({
        'loggers': {'': {'handlers': [route]}},
        'handlers': {route: {'cls': cls}},
        'formatters': {'text': {'format': '{message}'}},
    })
    logger.info('message')
    logger.handlers[0]._stream.flush()
    assert log_file.read_text() == 'message\n'


@pytest.mark.parametrize('cls', ['StreamHandler', 'QueueStreamHandler'])
def test_unsupported_handler_route(cls):
    route = f'unsupported://123'
    with pytest.raises(ValueError):
        uvlog.configure({
            'loggers': {'': {'handlers': [route]}},
            'handlers': {route: {'cls': cls}},
            'formatters': {'text': {'format': '{message}'}},
        })
