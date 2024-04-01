"""Python logging utilities."""

import logging
import os
import sys
from abc import abstractmethod, ABC
from collections import ChainMap
from contextvars import ContextVar  # noqa: pycharm bug?
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from random import random
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Protocol,
    Type,
    TypedDict,
    cast,
    ClassVar,
)
from weakref import WeakValueDictionary

__all__ = [
    "LOG_CONTEXT",
    "BASIC_CONFIG",
    "LogRecord",
    "Logger",
    "Handler",
    "Formatter",
    "add_formatter_type",
    "add_handler_type",
    "set_logger_type",
    "get_logger",
    "configure",
    "clear",
    "LevelName",
    "name_to_level",
]

LOG_CONTEXT: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "LOG_CONTEXT", default=None
)  #: default log context


_root_logger_name = ""
_formatter_types: Dict[str, Type["Formatter"]] = {}


class _DictConfig(TypedDict, total=False):
    loggers: Dict[str, dict]
    handlers: Dict[str, dict]
    formatters: Dict[str, dict]


BASIC_CONFIG: _DictConfig = {
    "loggers": {_root_logger_name: {}},
    "handlers": {
        "stderr": {},
        "stdout": {},
    },
    "formatters": {
        "text": {"class": "TextFormatter"},
        "json": {"class": "JSONFormatter"},
    },
}  #: default log configuration

LevelName = Literal["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NEVER"]
_handler_types: Dict[str, Type["Handler"]] = {}
_handlers: Dict[str, "Handler"] = {}
_formatters: Dict[str, "Formatter"] = {}
_loggers_persistent: Dict[str, "Logger"] = {}
_loggers_temp: WeakValueDictionary = WeakValueDictionary()
_loggers: ChainMap = ChainMap(_loggers_persistent, _loggers_temp)
name_to_level: Dict[LevelName, int] = {
    "NOTSET": logging.NOTSET,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
    "NEVER": logging.CRITICAL + 100,
}


@dataclass
class LogRecord:
    """Log record object.

    A log record object is created when a log method of a logger is called.
    """

    __slots__ = (
        "name",
        "level",
        "levelno",
        "asctime",
        "filename",
        "lineno",
        "func",
        "message",
        "exc_info",
        "args",
        "extra",
        "ctx",
    )

    name: str
    """Logger name"""

    level: LevelName
    """Log record level name"""

    levelno: int
    """Log record level number"""

    asctime: datetime
    """Timestamp of record creation"""

    message: str
    """Log message"""

    exc_info: Optional[Exception]
    """Exception (if any)"""

    args: Optional[tuple]
    """Log call positional arguments.

    This attribute is left only for compatibility reasons. It's not used in formatting log messages.
    """

    extra: Optional[Mapping[str, Any]]
    """Log extra information provided in kwargs"""

    ctx: Optional[Mapping[str, Any]]
    """Log contextual information"""

    filename: Optional[str]
    """Filename of the caller"""

    func: Optional[str]
    """Function name of the caller"""

    lineno: Optional[int]
    """Source code line number of the caller"""


class Formatter(Protocol):
    """Log formatter interface.

    It's a protocol class, i.e. one doesn't need to inherit from it to create a valid formatter.
    """

    @abstractmethod
    def format_record(self, record: LogRecord, /) -> bytes: ...

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}>"


class Handler(ABC):
    """Log handler interface.

    It's a protocol class, i.e. one doesn't need to inherit from it to create a valid handler.
    """

    route_prefix: ClassVar[str]

    def __init__(self, route: str, formatter: Formatter, level: LevelName) -> None:
        """Initialize."""
        self.route = route
        self.formatter = formatter
        self.level = level
        self.levelno = name_to_level[level]

    @classmethod
    def accepts_destination(cls, route: str, /) -> bool:
        return route.startswith(cls.route_prefix + ":")

    @classmethod
    @abstractmethod
    def resolve_destination(cls, route: str, /) -> str:
        """Resolve destination route and normalize it."""

    @abstractmethod
    def handle(self, record: LogRecord, /) -> None: ...

    def set_level(self, level: LevelName, /) -> None:
        self.level = level
        self.levelno = name_to_level[level]

    @abstractmethod
    def close(self) -> None:
        """Close the handler including all connections to its destination.

        This method is called automatically at exit for each added handler by the :py:func:`~uvlog.clear` function.
        """

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}: {self.route} / {self.formatter}>"


def add_formatter_type(typ: Type[Formatter], /) -> None:
    _formatter_types[typ.__name__] = typ


def add_handler_type(typ: Type[Handler], /) -> None:
    _handler_types[typ.__name__] = typ


@dataclass
class Logger:
    """Logger object.

    It can be used almost like a standard Python logger, except that it allows passing keyword arguments
    directly to `extra`:

    .. code-block:: python

        main_logger = uvlog.get_logger('app')
        logger = main_logger.get_child('my_service')

        logger.debug('debug message', debug_value=42)
        logger.error('error happened', exc_info=Exception())

    """

    name: str
    """Logger name"""

    level: LevelName = "INFO"
    """Logging level"""

    handlers: List[Handler] = field(default_factory=list)
    """List of attached log handlers"""

    sample_rate: float = 1.0
    """Log records sample rate which determines a probability at which a record should be sampled.

    Sample rate is not considered for levels above 'INFO'. Values >= 1 disable the sampling mechanism.
    """

    sample_propagate: bool = True
    """By default the sampling mechanism is contextual meaning that if there's a non-empty log context,
    the log chain is marked 'sampled' as it sampled by the first logger in a chain. Once a record is 'sampled' the
    log chain cannot be *unsampled*, i.e. all subsequent loggers will be forced to sample it as well.
    It allows to preserve an entire request log chain in the logs and not just some random not connected logs.
    """

    context: ContextVar[Optional[Dict[str, Any]]] = LOG_CONTEXT
    """Log context variable - useful for contextual data,
    see `contextvars <https://docs.python.org/3/library/contextvars.html>`_
    """

    capture_trace: bool = False
    """Capture traceback for each call such as line numbers, file names etc. — may affect performance"""

    _levelno: int = field(init=False, default=0)
    _parent: Optional["Logger"] = field(init=False, default=None)

    def __post_init__(self) -> None:
        self._levelno = name_to_level[self.level]

    def set_level(self, level: LevelName, /) -> None:
        self._levelno = name_to_level[level]
        self.level = level

    def getChild(self, name: str, /) -> "Logger":
        """Get or create a child logger.

        This is a compatibility wrapper around :py:meth:`~uvlog.uvlog.Logger.get_child`. Use that method instead.
        """
        return self.get_child(name)

    def get_child(self, name: str, /, *, persistent: bool = False) -> "Logger":
        """Get or create a child logger inheriting all the logger settings.

        .. attention::

            Note that by default a new logger is not *persistent*, i.e. it will be eventually garbage collected if
            there are no live references to it.
        """
        if "." in name:
            raise ValueError(
                '"." symbol is not allowed in logger names when calling `get_child` directly\n\n'
                "Fix: if you want to create a chain of loggers "
                "use `uvlog.get_logger()` function instead"
            )
        if name in _loggers:
            return _loggers[name]
        child_name = name if self.name == _root_logger_name else f"{self.name}.{name}"
        child_logger = _logger_type(
            name=child_name,
            level=self.level,
            context=self.context,
            handlers=[*self.handlers],
            capture_trace=self.capture_trace,
        )  # noqa
        child_logger._parent = self
        if persistent:
            _loggers_persistent[name] = child_logger
        else:
            _loggers_temp[name] = child_logger
        return child_logger

    def never(
        self,
        msg: str,
        /,
        *args,
        exc_info: Optional[Exception] = None,
        stack_info=None,
        stacklevel=1,
        **kws,
    ) -> None:
        ctx = self.context.get()
        if ctx and self.sample_rate < 1.0:
            ctx["_sample"] = True
        self._log(
            "NEVER",
            name_to_level["NEVER"],
            msg,
            exc_info,
            stack_info,
            stacklevel,
            ctx,
            args,
            kws,
        )

    def critical(
        self,
        msg: str,
        /,
        *args,
        exc_info: Optional[Exception] = None,
        stack_info=None,
        stacklevel=1,
        **kws,
    ) -> None:
        levelno = name_to_level["CRITICAL"]
        if self._levelno > levelno:
            return
        ctx = self.context.get()
        if ctx and self.sample_rate < 1.0:
            ctx["_sample"] = True
        self._log(
            "CRITICAL", levelno, msg, exc_info, stack_info, stacklevel, ctx, args, kws
        )

    def error(
        self,
        msg: str,
        /,
        *args,
        exc_info: Optional[Exception] = None,
        stack_info=None,
        stacklevel=1,
        **kws,
    ) -> None:
        levelno = name_to_level["ERROR"]
        if self._levelno > levelno:
            return
        ctx = self.context.get()
        if ctx and self.sample_rate < 1.0:
            ctx["_sample"] = True
        self._log(
            "ERROR", levelno, msg, exc_info, stack_info, stacklevel, ctx, args, kws
        )

    def warning(
        self,
        msg: str,
        /,
        *args,
        exc_info: Optional[Exception] = None,
        stack_info=None,
        stacklevel=1,
        **kws,
    ) -> None:
        levelno = name_to_level["WARNING"]
        if self._levelno > levelno:
            return
        ctx = self.context.get()
        if ctx and self.sample_rate < 1.0:
            ctx["_sample"] = True
        self._log(
            "WARNING", levelno, msg, exc_info, stack_info, stacklevel, ctx, args, kws
        )

    def info(
        self,
        msg: str,
        /,
        *args,
        exc_info: Optional[Exception] = None,
        stack_info=None,
        stacklevel=1,
        **kws,
    ) -> None:
        levelno = name_to_level["INFO"]
        if self._levelno > levelno:
            return
        ctx = self.context.get()
        if ctx and self.sample_rate < 1.0:
            if not self._sample(ctx):
                return
        self._log(
            "INFO", levelno, msg, exc_info, stack_info, stacklevel, ctx, args, kws
        )

    def debug(
        self,
        msg: str,
        /,
        *args,
        exc_info: Optional[Exception] = None,
        stack_info=None,
        stacklevel=1,
        **kws,
    ) -> None:
        levelno = name_to_level["DEBUG"]
        if self._levelno > levelno:
            return
        ctx = self.context.get()
        if ctx and self.sample_rate < 1.0:
            if not self._sample(ctx):
                return
        self._log(
            "DEBUG", levelno, msg, exc_info, stack_info, stacklevel, ctx, args, kws
        )

    def _sample(self, ctx: dict, /) -> bool:
        if not self.sample_propagate:
            return random() < self.sample_rate
        _sample = cast(bool, ctx.get("_sample"))
        if _sample is None:
            _sample = random() < self.sample_rate
            ctx["_sample"] = _sample
        return _sample

    def _log(
        self, level, levelno, msg, exc_info, stack_info, stacklevel, ctx, args, kws, /
    ) -> None:
        fn, lno, func, _ = (
            _find_caller(stack_info, stacklevel)
            if self.capture_trace
            else (None, None, None, None)
        )
        record = LogRecord(
            self.name,
            level,
            levelno,
            datetime.now(),
            msg.format_map(kws) if kws else msg,
            exc_info,
            args if args else None,
            kws if kws else None,
            ctx,
            fn,
            func,
            lno,
        )
        for handler in self.handlers:
            handler.handle(record)

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"


_logger_type = Logger


def set_logger_type(typ: Type["Logger"], /) -> None:
    global _logger_type
    _logger_type = typ


def get_logger(name: str = _root_logger_name, /, *, persistent: bool = False) -> Logger:
    """Get an existing logger or create a new one.

    :param name: logger full name, for example 'app.services.my_service', by default returns the root logger
    :param persistent: make this logger persistent and store it forever

    .. attention::

        Contrary to Python default logging module, this function by default produces a non-persistent logger unless it
        has been created using `uvlog.configure()`. This means that once no existing references exist for this logger,
        it will be garbage-collected.
    """
    if name in _loggers:
        return _loggers[name]
    if name == _root_logger_name:
        _loggers[_root_logger_name] = logger = _logger_type(_root_logger_name)
        return logger
    split_name = name.split(".")
    parent = _loggers[_root_logger_name]
    for parent_name in split_name[:-1]:
        parent = parent.get_child(parent_name, persistent=persistent)
    logger = parent.get_child(split_name[-1], persistent=persistent)
    return logger


# python traceback extraction methods - a ripoff of the standard logging library method

_srcfile = os.path.normcase(get_logger.__code__.co_filename)


def _find_caller(stack_info=None, stacklevel: int = 1):
    """Find the stack frame of the caller so that we can note the source file name, line number, function name."""
    f = sys._getframe(1)  # noqa
    if f is None:
        return "(unknown file)", 0, "(unknown function)", None
    while stacklevel > 0:
        next_f = f.f_back
        if next_f is None:
            break
        f = next_f
        filename = os.path.normcase(f.f_code.co_filename)
        is_internal_frame = filename == _srcfile or (
            "importlib" in filename and "_bootstrap" in filename
        )
        if not is_internal_frame:
            stacklevel -= 1
    co = f.f_code
    return co.co_filename, f.f_lineno, co.co_name, None


def _merge_dicts(from_dict: dict, to_dict: dict) -> dict:
    _new_dict = {**from_dict}
    for key, value in to_dict.items():
        if key in _new_dict and isinstance(value, dict):
            _new_dict[key] = _merge_dicts(_new_dict[key], value)
        else:
            _new_dict[key] = value
    return _new_dict


def _create_formatter(params: dict, /) -> Formatter:
    cls = _formatter_types[params.pop("class", "TextFormatter")]
    formatter = cls()
    for key, value in params.items():
        if not key.startswith("_"):
            setattr(formatter, key, value)
    return formatter


def _create_handler(route: str, params: dict, /) -> Handler:
    cls_name = params.pop("class", "StreamHandler")
    _handler_type = _handler_types[cls_name]
    if not _handler_type.accepts_destination(route):
        raise ValueError(
            f'Handler of type "{cls_name}" doesn\'t accept destination "{route}"'
        )

    route = _handler_type.resolve_destination(route)
    if route in _handlers:
        raise ValueError(f'Handler already exists for route "{route}"')

    formatter_name = params.pop("formatter", "text")
    level: LevelName = cast(LevelName, params.pop("level", "DEBUG"))
    handler = _handler_type(route, _formatters[formatter_name], level)
    for key, value in params.items():
        if not key.startswith("_"):
            setattr(handler, key, value)
    return handler


def _create_logger(name: str, params: dict, /) -> Logger:
    logger = get_logger(name, persistent=True)
    handler_names = params.pop("handlers", ["stderr"])
    logger.handlers = [_handlers[handler_name] for handler_name in handler_names]
    level: LevelName = cast(LevelName, params.pop("level", "INFO"))
    logger.set_level(level)
    for key, value in params.items():
        if not key.startswith("_"):
            setattr(logger, key, value)
    return logger


def configure(
    config_dict: _DictConfig, /, context_var: ContextVar = LOG_CONTEXT
) -> Logger:
    """Configure loggers for a configuration dict.

    :param config_dict: logging configuration (JSON compatible), at module init this function is called with
        `uvlog.BASIC_CONFIG` to provide default loggers and handlers
    :param context_var: log context variable, see `contextvars <https://docs.python.org/3/library/contextvars.html>`_

    This function is similar to dictConfig in the standard logging module, although the config format is slightly
    different.

    .. code-block:: python

        {
            "loggers": {
                "app": {
                    "level": "ERROR",
                    "handlers": ["my_file.txt"],
                    "capture_trace": True
                }
            },
            "handlers": {
                "my_file.txt": {
                    "class": "StreamHandler",
                    "level": "DEBUG",
                    "formatter": "my_format"
                }
            },
            "formatters": {
                "my_format": {
                    "class": "TextFormatter",
                    "format": "{name}: {message}"
                }
            }
        }

    The main differences are:

    - 'class' names for handlers and formatters must be registered beforehand using 'add_formatter_type()' and
        'add_handler_type()' respectively to allow classes not inherited from `Handler` / 'Formatter`
    - handler names are their destinations, since by design you're not allowed to bind multiple handlers to a single
        destination
    - 'format' for the text formatter should be in Python f-string format

    .. attention::

        The function is designed in such way you can extend or modify existing loggers, handlers or formatters
        by passing a config. If you want to configure logging from zero you should call `clear()` method beforehand.
        Please note that you need to provide all the handlers, formatters, loggers in the config after doing that,
        including the root logger (empty string).

    """
    clear()
    config_dict = cast(
        _DictConfig,
        _merge_dicts(cast(dict, deepcopy(BASIC_CONFIG)), cast(dict, config_dict)),
    )
    for name, params in config_dict["formatters"].items():
        _formatter = _create_formatter(params)
        _formatters[name] = _formatter
    for route, params in config_dict["handlers"].items():
        _handler = _create_handler(route, params)
        _handlers[route] = _handler
    # sorting loggers to init parents before children
    loggers_params = list(config_dict["loggers"].items())
    loggers_params.sort(key=lambda x: x[0])
    for name, params in loggers_params:
        _logger = _create_logger(name, params)
        _logger.context = context_var
        _loggers[name] = _logger
    return _loggers[_root_logger_name]


def clear() -> None:
    """Clear all existing loggers, handlers and formatters.

    This function also closes all existing handlers.
    """
    _loggers_temp.clear()
    _loggers_persistent.clear()
    for handler in _handlers.values():
        handler.close()
    _handlers.clear()
    _formatters.clear()
