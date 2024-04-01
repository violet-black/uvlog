"""Standard log formatters."""

import io
import traceback
from datetime import datetime
from json import dumps
from typing import Any, Collection, cast, ClassVar

from uvlog.uvlog import LogRecord, Formatter

__all__ = [
    "JSONFormatter",
    "TextFormatter",
]

DEFAULT_TIMESPEC = "seconds"
DEFAULT_FORMAT = "{asctime} | {level:8} | {name} | {message} | {ctx}"


def _dumps_default(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def _dumps_bytes(obj) -> bytes:
    # patched standard json dumps method to dump bytestring
    # in reality you'd rather want to use a faster json library like `orjson` etc.
    return dumps(obj, default=_dumps_default).encode("utf-8")


class TextFormatter(Formatter):
    """Text log formatter.

    Creates human-readable log output.

    Formatter settings must be set directly or using the :py:func:`uvlog.config` method.

    .. code-block:: python

        _formatter = TextFormatter()
        _formatter.timespec = 'seconds'

    """

    timespec: str
    """Precision for ISO timestamps,
    see `datetime.isoformat() <https://docs.python.org/3/library/datetime.html#datetime.datetime.isoformat>`_"""

    timestamp_separator: str
    """Timestamp separator for ISO timestamps,
    see `datetime.isoformat() <https://docs.python.org/3/library/datetime.html#datetime.datetime.isoformat>`_"""

    format: str
    """Log record format, a python f-string,
    the available keys can be seen in :py:class:`~uvlog.LogRecord` type
    """

    def __init__(self):
        """Initialize."""
        self.timespec = DEFAULT_TIMESPEC
        self.timestamp_separator = "T"
        self.format = DEFAULT_FORMAT

    def format_record(self, record: LogRecord, /) -> bytes:
        message = self.format.format_map(
            {
                "asctime": record.asctime.isoformat(
                    timespec=self.timespec, sep=self.timestamp_separator
                ),
                "level": record.level,
                "name": record.name,
                "message": record.message,
                "filename": record.filename,
                "func": record.func,
                "lineno": record.lineno,
                "extra": record.extra,
                "ctx": record.ctx,
            }
        )
        if record.exc_info is not None:
            exc_info = record.exc_info
            message += "\n" + self._format_exc(
                type(exc_info), exc_info, exc_info.__traceback__
            )
        return message.encode("utf-8")

    @staticmethod
    def _format_exc(error_cls, exc, stack, /) -> str:
        sio = io.StringIO()
        traceback.print_exception(error_cls, exc, stack, None, sio)
        s = sio.getvalue()
        sio.close()
        if s[-1:] == "\n":
            s = s[:-1]
        return s


class JSONFormatter(Formatter):
    """JSON log formatter.

    To change the default `dumps` function assign it to the class attribute.

    .. code-block:: python

        import orjson

        JSONFormatter.serializer = orjson.dumps

    Formatter settings must be set directly or using the :py:func:`uvlog.config` method.

    .. code-block:: python

        _formatter = JSONFormatter()
        _formatter.exc_pass_locals = True

    """

    serializer: ClassVar = _dumps_bytes
    """Serializer function - a class attribute"""

    keys: Collection[str]
    """List of serialized log record keys.

    The available keys can be seen in :py:class:`~uvlog.LogRecord` type"""

    exc_pass_locals: bool
    """Pass locals dict in exception traceback (don't use it unless your logs are secure)"""

    exc_pass_filenames: bool
    """Pass globals dict in exception traceback (don't use it unless your logs are secure)"""

    def __init__(self):
        """Initialize."""
        self.exc_pass_locals = False
        self.exc_pass_filenames = False
        self.keys = (
            "name",
            "level",
            "levelno",
            "asctime",
            "message",
            "exc_info",
            "args",
            "extra",
            "ctx",
            "filename",
            "lineno",
            "func",
        )

    def format_record(self, record: LogRecord, /) -> bytes:
        data = {}
        for key in self.keys:
            value = getattr(record, key, None)
            if value is not None:
                data[key] = value
        exc_info = cast(Exception, data.pop("exc_info", None))
        if exc_info:
            error_cls, exc, _ = type(exc_info), exc_info, exc_info.__traceback__
            data["exc_info"] = {
                "message": str(exc),
                "type": error_cls.__name__,
                "data": exc.json_repr() if hasattr(exc, "json_repr") else {},
            }
            tb = exc.__traceback__
            if tb and tb.tb_next:
                frame = tb.tb_next
                data["exc_info"]["traceback"] = tb_dict = {
                    "lineno": frame.tb_lineno,
                    "func": frame.tb_frame.f_code.co_name,
                }
                if self.exc_pass_filenames:
                    tb_dict["filename"] = (frame.tb_frame.f_code.co_filename,)
                if self.exc_pass_locals:
                    tb_dict["locals"] = frame.tb_frame.f_locals

        return self.__class__.serializer(data)
