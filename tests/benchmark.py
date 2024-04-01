"""
Testing stream loggers direct file writes: python logger, uv logger with text output, uv logger with
json output using orjson library.

Actual logging speed may depend on many factors, but in general the current logger is several times faster than the
default one, especially when dumping directly into JSON.

The threaded queue logger performance greatly depends on python interpreter behaviour (I guess), so its test results
may vary significantly from run to run.
"""

import logging
import os
from pathlib import Path
from time import time

from uvlog import JSONFormatter, clear, configure

NUMBER = 10_000
FILENAME = './log.txt'


def test_py_logger():
    logging.basicConfig(filename=FILENAME,
                        filemode='a',
                        format='%(asctime)s:%(name)s:%(levelname)s:%(message)s',
                        datefmt='%Y-%m-%dT%H:%M:%S',
                        level=logging.INFO)
    logger = logging.getLogger('python_logger')
    t0 = time()
    for _ in range(NUMBER):
        logger.info('Hello python')
    t = time() - t0
    lps = round(NUMBER / t)
    return t, lps


def test_uv_logger_text():
    clear()
    logger = configure({
        'loggers': {
            '': {
                'level': 'INFO',
                'handlers': ['log.txt']
            }
        },
        'handlers': {
            'log.txt': {
                'class': 'StreamHandler',
                'level': 'DEBUG',
                'formatter': 'text'
            }
        },
        'formatters': {
            'text': {
                'class': 'TextFormatter',
                'format': '{asctime}:{name}:{level}:{message}'
            }
        }
    })
    t0 = time()
    for _ in range(NUMBER):
        logger.info('Hello text!!')
    t = time() - t0
    lps = round(NUMBER / t)
    return t, lps


def test_uv_logger_json():
    from orjson import dumps
    clear()
    logger = configure({
        'loggers': {
            '': {
                'level': 'INFO',
                'handlers': ['log.txt']
            }
        },
        'handlers': {
            'log.txt': {
                'class': 'StreamHandler',
                'level': 'DEBUG',
                'formatter': 'json'
            }
        },
        'formatters': {
            'json': {
                'class': 'JSONFormatter',
                'keys': ['asctime', 'name', 'level', 'message']
            }
        }
    })
    JSONFormatter.serializer = dumps
    t0 = time()
    for _ in range(NUMBER):
        logger.info('Hello json!!')
    t = time() - t0
    lps = round(NUMBER / t)
    return t, lps


def test_uv_logger_queued_json():
    from orjson import dumps
    clear()
    logger = configure({
        'loggers': {
            '': {
                'level': 'INFO',
                'handlers': ['log.txt']
            }
        },
        'handlers': {
            'log.txt': {
                'class': 'QueueStreamHandler',
                'level': 'DEBUG',
                'formatter': 'json'
            }
        },
        'formatters': {
            'json': {
                'class': 'JSONFormatter',
                'keys': ['asctime', 'name', 'level', 'message']
            }
        }
    })
    JSONFormatter.serializer = dumps
    t0 = time()
    for _ in range(NUMBER):
        logger.info('Hello queue!')
    t = time() - t0
    lps = round(NUMBER / t)
    return t, lps


def main():
    t_py, lps_py = 1, 1
    t_py, lps_py = test_py_logger()
    t_uv, lps_uv = test_uv_logger_text()
    t_uv_j, lps_uv_j = test_uv_logger_json()
    t_uv_q_j, lps_uv_q_j = test_uv_logger_queued_json()
    print('\n\n')
    print(f'Number: {NUMBER}\n')
    print(f'{"name":<12} {"total (s)":>10} {"log/s":>10} {"%":>10}')
    print(f'{"py_log":<12} {t_py:>10.2} {lps_py:>10} {100:>10}')
    print(f'{"uv_log":<12} {t_uv:>10.2} {lps_uv:>10} {round(100 * lps_uv / lps_py):>10}')
    print(f'{"uv_log_j":<12} {t_uv_j:>10.2} {lps_uv_j:>10} {round(100 * lps_uv_j / lps_py):>10}')
    print(f'{"uv_log_q_j":<12} {t_uv_q_j:>10.2} {lps_uv_q_j:>10} {round(100 * lps_uv_q_j / lps_py):>10}')
    if Path(FILENAME).exists():
        os.remove(FILENAME)


if __name__ == '__main__':
    main()
