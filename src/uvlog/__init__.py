"""Python logging utilities."""

import atexit
import logging
from typing import Union, cast

from uvlog.formatters import *
from uvlog.handlers import *
from uvlog.uvlog import *

__python_version__ = "3.8"
__author__ = "violetblackdev@gmail.com"
__license__ = "MIT"
__version__ = "0.1.6"

add_formatter_type(TextFormatter)
add_formatter_type(JSONFormatter)
add_handler_type(StreamHandler)
add_handler_type(QueueStreamHandler)

configure(BASIC_CONFIG)
atexit.register(clear)

# compatibility with the standard library

_root_logger = get_logger()
debug = _root_logger.debug
info = _root_logger.info
warning = _root_logger.warning
error = _root_logger.error
critical = _root_logger.critical
never = _root_logger.never
getLogger = get_logger

_level_to_name = {
    logging.CRITICAL: "CRITICAL",
    logging.ERROR: "ERROR",
    logging.WARNING: "WARNING",
    logging.INFO: "INFO",
    logging.DEBUG: "DEBUG",
}


def basicConfig(level: Union[int, LevelName, None] = None):
    if level is not None and isinstance(level, int):
        level = cast(LevelName, _level_to_name[level])
        _root_logger.set_level(level)
