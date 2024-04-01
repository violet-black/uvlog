[![pypi](https://img.shields.io/pypi/v/uvlog.svg)](https://pypi.python.org/pypi/uvlog/)
[![docs](https://readthedocs.org/projects/uvlog/badge/?version=latest&style=flat)](https://uvlog.readthedocs.io)
[![codecov](https://codecov.io/gh/violet-black/uvlog/graph/badge.svg?token=FEUUMQELFX)](https://codecov.io/gh/violet-black/uvlog)
[![tests](https://github.com/violet-black/uvlog/actions/workflows/tests.yaml/badge.svg)](https://github.com/violet-black/uvlog/actions/workflows/tests.yaml)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**uvlog** is yet another Python logging library built with an idea of a simple logger what 'just works' without
need for extension and customization.

- Single package, no dependencies
- JSON and [contextvars](https://docs.python.org/3/library/contextvars.html) out of the box
- Less abstraction, better [performance](#Performance)
- Pythonic method names and classes

# Installation

With pip and python 3.8+:

```bash
pip3 install uvlog
```

# Use

Our main scenario is logging our containerized server applications, i.e. writing all the logs to the stderr
of the container, where they are gathered and sent to the log storage by another service. However, you
can use this library for any application as long as it doesn't require complicated things like filters, adapters etc.

```python
from uvlog import get_logger

logger = get_logger('app')

logger.info('Hello, {name} {surname}!', name='John', surname='Dowe')
```

Note that you can use extras directly as variable keys in log calls (variable positional args are stored in a log
record but not supported by the formatter).

To write an exception use `exc_info` as in the standard logger.

```python
try:
    ...
except ValueError as exc:
    logger.error('Something bad happened', exc_info=exc)
```

Log configuration is similar to *dictConfig*. It updates the default configuration.

```python
from uvlog import configure

logger = configure({
    'loggers': {
        '': {'level': 'DEBUG', 'handlers': ['./log.txt']}
    },
    'handlers': {
        './log.txt': {'formatter': 'json'}
    }
})
```

You can use context variables to maintain log context between log records. This can be useful for log aggregation.
See the [documentation on contextvars](https://uvlog.readthedocs.io/guide.html#context-variables) for more info.

```python
from uvlog import LOG_CONTEXT, get_logger

app_logger = get_logger('app')

async def handler_request(request):
    LOG_CONTEXT.set({'request_id': request.headers['Request-Id']})
    await call_system_api()

async def call_system_api():
    # this record will have 'request_id' in its context
    app_logger.info('Making a system call')
```

When using the `JSONFormatter` you should consider providing a better json serializer for
better performance (such as [orjson](https://github.com/ijl/orjson)).

```python
import orjson
from uvlog import JSONFormatter

JSONFormatter.serializer = orjson.dumps
```

# Never say never

The library adds support for additional log level - `NEVER`. The idea behind this is to use such logs in places of code
which should never be executed in production and monitor such cases. 'NEVER' logs have the maximum priority.
They cannot be suppressed by any logger and are always handled.

The use of `NEVER` is straightforward.

```python
def handle_authorization(username, password) -> bool:
    if DEBUG and username == debug_login:
        logger.never('skip authorization for {username}', username=username)
        return True
    return check_password_is_valid(username, password)
```

Why not just use a `DEBUG` or `WARNING` level here? The reason is low priority of such records, which allows them
to be mixed with less significant logs or even be skipped by loggers.

# Loggers are weak

Unlike the standard logging module, loggers are weak referenced unless they are described explicitly
in the configuration dict or created with `persistent=True` argument.

It means that a logger is eventually garbage collected once it has no active references.
This allows creation of a logger per task, not being concerned about running out of memory eventually.
However, this also means that all logger settings for a weak logger will be forgotten once it's collected.

In general this is not a problem since you shouldn't fiddle with logger settings outside the initialization
phase.

# Sampling

The library implements internal log sampling. In shorts, it allows you to specify the `sample_rate`,
a probability at which a logger will pass a record to the handlers. It allows to release some load due
to extensive logging.

```python
from uvlog import get_logger

logger = get_logger()
logger.sample_rate = 0.25
```

... or via a config dict

```python
from uvlog import configure

configure({
    'loggers': {
        '': {'sample_rate': 0.25}
    }
})
```

See the [documentation on sampling](https://uvlog.readthedocs.io/guide.html#sampling) for more info.

# Customization

You can create custom formatters and handlers with ease. Note that inheritance is not required.
Just be sure to implement `Handler` / `Formatter` protocol.

See the extension guide for more info. There's an example of
[HTTP queue logger](https://uvlog.readthedocs.io/extension.html#example-http-logger) using
[requests](https://docs.python-requests.org/en/latest/index.html) library there.

# Performance

Benchmark results are provided for the M1 Pro Mac (16GB). The results are for the `StreamHandler`
writing same log records into a file. The `QueueStreamHandler` provides similar performance, but has been excluded
from the test since Python threading model prevents results from being consistent between runs. However,
I'd still recommend using the `QueueStreamHandler` for server applications.

| name          | total (s) | logs/s | %   |
|---------------|-----------|--------|-----|
| python logger | 0.085     | 117357 | 100 |
| uvlog text    | 0.022     | 455333 | 388 |
| uvlog json    | 0.015     | 665942 | 567 |

# Compatibility

There's a certain compatibility between this logger and the standard logger. However, it's impossible to preserve
full compatibility because of certain design decisions.

See the [compatibility guide](https://uvlog.readthedocs.io/compatibility.html) if you want to migrate from the standard
python logger to this one.
