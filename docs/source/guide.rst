.. _guide:

User guide
==========

Configuration
^^^^^^^^^^^^^

A basic way to start is to just use it as you would use the default Python logger.

.. code-block:: python

    import uvlog

    logger = uvlog.get_logger()
    logger.set_level('DEBUG')

    logger.debug('debug message')

By default the library provides a pre-configured root logger with a standard
`stderr` handler and a text formatter, so it can provide reasonable log output
out of the box.

For more sophisticated configuration you can use :py:func:`uvlog.configure` function
which is similar to the Python `dictConfig` (however the format is slightly different).

.. code-block:: python

    root_logger = uvlog.configure({
        'loggers': {
            '': {
                'levelname': 'ERROR',
                'handlers': ['log.txt']
            }
        },
        'handlers': {
            './log.txt': {
                'class': 'QueueStreamHandler',
                'formatter': 'json'
            }
        }
    })

The configuration extends the standard :py:obj:`~uvlog.BASIC_CONFIG` configuration by default, which has
default 'stdout', 'stderr' handlers and 'text', 'json' formatters preconfigured as well as the root logger.
If you want to do the entire configuration from scratch, use :py:func:`uvlog.clear` first and then
:py:func:`uvlog.configure`.

.. code-block:: python

    {
        "loggers": {
            "": {  # logger name, "" for the root logger
                "level": "INFO",            # log level
                "handlers": ["stderr"]      # list of handler names (destinations) for 'handlers' dict
            }
        },
        "handlers": {
            'stderr': {  # stderr and stdout are reserved for these special types of outputs
                "class": "StreamHandler",   # handler class
                "level": "DEBUG",           # log level for this particular handler
                "formatter": "text",        # assigned formatter key from 'formatters' dict
            }
        },
        "formatters": {
            "text": {   # you can use any names here, however the two default formatters are 'text' and 'json'
                "type": "TextFormatter",
                "timespec": _default_timespec,
                "format": _default_format,
            },
            "json": {"type": "JSONFormatter"},
        },
    }

Logging
^^^^^^^

You can pass extra parameters directly to the log record.

.. code-block:: python

    logger.info('my name is {name}', name='John')

Errors can be passed as in the standard logging module.

.. code-block:: python

    logger.error('something happened', exc_info=ValueError())

Child loggers can be created using :py:meth:`~uvlog.Logger.get_child` method.

.. code-block:: python

    app_logger = uvlog.get_logger('app')
    service_logger = logger.get_child('service')

    service_logger = uvlog.get_logger('app.service')  # alternative way

Note that a logger is *weak* by default. It means that it eventually will be garbage collected if there are no live
references to it. To create a persistent logger you need to pass `persistent=True` flag there.

Why do you want a persistent logger? Mostly because you want to have some logger-specific settings without need to
pass a reference along your code. However in this case you should probably consider adding it to the configuration
dict. *All loggers created by the :py:func:`uvlog.configure` function are persistent.*

.. code-block:: python

    app_logger = uvlog.get_logger('app', persistent=True)

Context variables
^^^^^^^^^^^^^^^^^

You can either provide your own context variable or use the default :py:obj:`uvlog.LOG_CONTEXT` to provide
useful context for your log records.

.. code-block:: python

    logger = uvlog.get_logger()

    async def handle_request(request):
        uvlog.LOG_CONTEXT.set({'request_id': request.headers['Request-Id']})
        logger.info('new request received')
        await call_system_method()
        return Response('OK')

    async def call_system_method():
        logger.info('calling a system method')

In the example both 'new request received' and 'calling a system method' messages will have
the same `request_id` value assigned to their context.

.. code-block:: console

    2024-04-01T17:04:37 | INFO |  | new request received | None | {'request_id': '123'}
    2024-04-01T17:04:37 | INFO |  | calling a system method | None | {'request_id': '123'}

Now you can *cat logs.txt | grep 123* to output the whole request log chain,
or use the :py:class:`~uvlog.JSONFormatter` for the output,
aggregate your logs and send them to your ELK for example.

Sampling
^^^^^^^^

Sampling allows to decrease amount of logs in a system by randomly picking and handling only some of them. There are
many sampling mechanisms and you are encouraged to use them in your log aggregation services.

However, this library provides a simple sampling for loggers. :py:attr:`~uvlog.Logger.sample_rate`
defines a rate at which logs will be sampled by this logger
(i.e. probability for a log record to reach the log handlers).
Values above 1 are ignored and sampling mechanism is considered to be disabled for them.

To enable sampling globally just pass :py:attr:`~uvlog.Logger.sample_rate` in your log config as follows.

.. code-block:: python

    root_logger = uvlog.configure({
        'loggers': {
            '': {
                'sample_rate': 0.25
            }
        }
    })

**Sampling rules**

Sampling mechanism is disabled for log messages of 'WARNING' and above.

If `Context variables`_ are used and the log context is not empty, then the first logger in the chain will
determine whether the entire chain will be sampled. The reason behind this is to sample the whole chain for each
incoming request (API call, task execution, etc.).

To illustrate this, imagine you have an incoming request in your server request handler, where you also set
a context variable. Now, if sampling is enabled, the first log call 'new request received'
will determine by a dice roll whether to sample the whole request chain.
So you will either see *all* log messages for the whole request chain or nothing at all.

.. code-block:: python

    root_logger = uvlog.configure({
        'loggers': {
            '': {
                'sample_rate': 0.25
            }
        }
    })

    system_logger = root_logger.get_child('system')

    async def handle_request(request):
        uvlog.LOG_CONTEXT.set({'request_id': request.headers['Request-Id']})
        logger.info('new request received')  # may be sampled here
        await call_system_method()
        logger.info('request finished')  # 'new request received' determines whether it will be sampled
        return Response('OK')

    async def call_system_method():
        system_logger.info('calling a system method')  # 'new request received' determines whether it will be sampled

If `Context variables`_ are used, and 'WARNING' or 'ERROR' log record is encountered, the whole request chain after this
record will be sampled to provide useful information for error handling. On the example below the error message
forces subsequent logs in the chain to be sampled.

.. code-block:: python

    async def handle_request(request):
        uvlog.LOG_CONTEXT.set({'request_id': request.headers['Request-Id']})
        logger.info('new request received')  # may be sampled here
        await call_system_method()
        logger.info('request finished')  # 'something happened!' will force this record to be sampled
        return Response('OK')

    async def call_system_method():
        system_logger.error('something happened!')  # will be sampled

If you want to *disable* these rules, you can set :py:attr:`~uvlog.Logger.sample_propagate` to `False`
for the root logger. This will disable all the log chaining mechanisms, and each logger becomes independent.

.. code-block:: python

    root_logger = uvlog.configure({
        'loggers': {
            '': {
                'sample_rate': 0.25
                'sample_propagate': False
            }
        }
    })

Optimization
^^^^^^^^^^^^

In a concurrent environment use the :py:class:`~uvlog.QueueStreamHandler`

If you have a log aggregation stack such as ELK consider using the :py:class:`~uvlog.JSONFormatter`
instead of the text formatter

Consider providing a more efficient JSON serializer for the :py:class:`~uvlog.JSONFormatter`
such as `orjson <https://github.com/ijl/orjson>`_.

.. code-block:: python

    uvlog.JSONFormatter.serializer = orjson.dumps

Finally, use logging levels wisely and do not log too much in the production
environment, or at least use `Sampling`_.
