.. _extension:

Extension guide
===============

Formatters
^^^^^^^^^^

Use :py:class:`~uvlog.Formatter` protocol to implement your formatter type. Note that you don't need to inherit from it.
You need to call :py:func:`~uvlog.add_formatter_type` afterward to register your custom formatter type.

.. code-block:: python

    from uvlog import add_formatter_type, LogRecord

    class IdioticFormatter:

        def format_record(self, record: LogRecord, /) -> bytes:
            return b'Bang!'

    add_formatter_type(IdioticFormatter)

Handlers
^^^^^^^^

Use :py:class:`~uvlog.Handler` protocol to implement your handler type. Note that you don't need to inherit from it.
You need to call :py:func:`~uvlog.add_handler_type` afterward to register your custom handler type.

You can create your own queue handler by inheriting from :py:class:`~uvlog.handlers.QueueHandler`. You
must implement :py:meth:`~uvlog.handlers.QueueHandler.open_stream` and :py:meth:`~uvlog.handlers.QueueHandler.close_stream`
methods and also py:meth:`~uvlog.handlers.QueueHandler.write_records` method which should write a batch of formatted
log records (byte strings) to your destination. You also would need to create your own
:py:meth:`~uvlog.handlers.StreamHandler.set_destination` method.

See :py:class:`~uvlog.handlers.QueueStreamHandler` as an example.

Example: HTTP logger
^^^^^^^^^^^^^^^^^^^^

Here's an example of a simple HTTP queue handler
using `requests <https://docs.python-requests.org/en/latest/index.html>`_ library.

In this example a batch of logs is sent to some url in NDJSON format (newline delimited JSON). You may of course
customize the `write_records` method to suit your own needs.

.. code-block:: python

    import requests
    from typing import List
    from uvlog import QueueHandler, JSONFormatter, add_handler_type

    class QueueHTTPHandler(uvlog.QueueHandler):

        terminator = b'\n'

        headers: dict

        def __init__(self):
            QueueHandler.__init__(self)
            self.headers = {}
            self._formatter = JSONFormatter()
            self._url = None
            self._stream = None

        def set_destination(self, url: str, /):
            self._url = urlparse(url).geturl()

        def open_stream(self):
            self._stream = _session = requests.Session()
            _session.headers.update(self.headers)

        def close_stream(self):
            if self._stream is not None:
                self._stream.close()
                self._stream = None

        def write_records(self, records: List[bytes], /):
            self._stream.post(self._url, data=self.terminator.join(records) + b'\n', timeout=1)

    add_handler_type(QueueHTTPHandler)

Configuration example.

.. code-block:: python

    import os

    uvlog.configure({
        'loggers': {
            '': {
                'handlers': ['https://mylogs.com:8888']
            }
        },
        'handlers': {
            'https://mylogs.com:8888': {
                'class': 'QueueHTTPHandler',
                'headers': {
                    'Authorization': f'Basic {os.getenv("LOGS_CLIENT_KEY")}'
                }
            }
        }
    })
