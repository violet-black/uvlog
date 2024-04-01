.. compatibility:

Compatibility
=============

This logger is made with certain design decisions in mind which makes it impossible to maintain the full compatibility
with the standard Python logging module. However, certain compatibility is preserved.

All the logging methods are the same, but the use of positional arguments is discouraged.

For example this code is valid and will be executed by the root logger.

.. code-block:: python

    import uvlog

    uvlog.info('test message is %s', 'test')

However, the output will look like this.

.. code-block:: console

    2024-04-03T14:36:36 | INFO |  | test message is %s

To make it work as intended you have to use a keyword argument.

.. code-block:: python

    uvlog.info('test message is {value}', value='test')

This is a deliberate choice to make the log more explicit and allow to use extra parameters more easily without
need to pass an extra dict each time you need to log something.

Even the better way would be to not use any format strings at all and just pass the parameter in extras.

.. code-block:: python

    uvlog.info('test message', value='test')

Why is it better? Because if you have a log aggregation service like Kibana and JSON logs, it's much easier to
search and aggregate not dynamic messages, so you would be able to write something like this in your
log aggregation console:

.. code-block:: console

    message: "test message" AND extra.value: "test"

Even in plain text logs you would still be able to see extras or args if you change log format for something like this.

.. code-block:: python

    uvlog.configure({
        'formatters': {
            'text': {
                'format': '{asctime} | {level:8} | {name} | {message} | {extra} | {args}'
            }
        }
    })

The library also provides at least partial compatibility for `getLogger` and `basicConfig` methods.

.. code-block:: python

    # better use uvlog.configure or uvlog.get_logger().set_level('ERROR")
    uvlog.basicConfig(level=logging.ERROR)

    # better use uvlog.get_logger('app')
    app_logger = uvlog.getLogger('app')

    # better use app_logger.get_logger('child') here
    child_logger = app_logger.getChild('child')
