import io

import pytest

import uvlog


def patch_stream_handlers(logger):
    for handler in logger.handlers:
        handler._stream = io.BytesIO()


def read(logger):
    logger.handlers[0]._stream.seek(0)
    return logger.handlers[0]._stream.read()


def test_unsupported_logger_name():
    logger = uvlog.configure({
        'loggers': {'': {'level': 'DEBUG', 'sample_rate': 0.25, 'sample_propagate': False, 'handlers': ['stderr']}},
        'formatters': {'text': {'format': '{message}'}}
    })
    with pytest.raises(ValueError):
        logger.get_child('child.with.a.dot')


@pytest.mark.parametrize('msg_type', [
    'debug', 'info', 'warning', 'error', 'critical', 'never'
])
def test_message_types(msg_type):
    logger = uvlog.configure({
        'loggers': {'': {'level': 'DEBUG', 'capture_trace': True, 'handlers': ['stderr']}},
        'formatters': {'text': {'format': '{level} : {message} : {ctx}'}}
    })
    print(str(logger))
    uvlog.LOG_CONTEXT.set({'value': 1})
    patch_stream_handlers(logger)
    getattr(logger, msg_type)('test message')
    assert read(logger) == (msg_type.upper() + " : test message : {'value': 1}\n").encode()



@pytest.mark.parametrize('msg_type', [
    'debug', 'info', 'warning', 'error', 'critical'
])
def test_non_logging(msg_type):
    logger = uvlog.configure({
        'loggers': {'': {'level': 'NEVER', 'handlers': ['stderr']}},
        'formatters': {'text': {'format': '{level} : {message} : {ctx}'}}
    })
    uvlog.LOG_CONTEXT.set({'value': 1})
    patch_stream_handlers(logger)
    getattr(logger, msg_type)('test message')
    assert read(logger) == b''


@pytest.mark.parametrize('msg_type', [
    'debug', 'info'
])
def test_sampling(msg_type):
    logger = uvlog.configure({
        'loggers': {'': {'level': 'DEBUG', 'sample_rate': 0.25, 'sample_propagate': False, 'handlers': ['stderr']}},
        'formatters': {'text': {'format': '{message}'}}
    })
    uvlog.LOG_CONTEXT.set({'value': 1})
    patch_stream_handlers(logger)
    for _ in range(25):
        getattr(logger, msg_type)('t')
    assert len(read(logger)) < len('t\n') * 25


@pytest.mark.parametrize('msg_type', [
    'warning', 'error', 'critical'
])
def test_sampling_enforce_for_high_levels(msg_type):
    logger = uvlog.configure({
        'loggers': {'': {'level': 'DEBUG', 'sample_rate': 0.25, 'sample_propagate': False, 'handlers': ['stderr']}},
        'formatters': {'text': {'format': '{message}'}}
    })
    uvlog.LOG_CONTEXT.set({'value': 1})
    patch_stream_handlers(logger)
    for _ in range(25):
        getattr(logger, msg_type)('t')
    assert len(read(logger)) == len('t\n') * 25


@pytest.mark.parametrize('msg_type', [
    'debug', 'info'
])
def test_sample_propagation(msg_type):
    logger = uvlog.configure({
        'loggers': {'': {'level': 'DEBUG', 'sample_rate': 0.25, 'handlers': ['stderr']}},
        'formatters': {'text': {'format': '{message}'}}
    })
    uvlog.LOG_CONTEXT.set({'value': 1})
    patch_stream_handlers(logger)
    logger.error('error')  # enforces propagation for the following logs
    for _ in range(25):
        getattr(logger, msg_type)('t')
    assert len(read(logger)) == len('error\n') + len('t\n') * 25
