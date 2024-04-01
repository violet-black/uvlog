.. _api:

:tocdepth: 2

Functions
---------

.. autofunction:: uvlog.add_formatter_type

.. autofunction:: uvlog.add_handler_type

.. autofunction:: uvlog.clear

.. autofunction:: uvlog.configure

.. autofunction:: uvlog.get_logger

.. autofunction:: uvlog.set_logger_type

Loggers
-------

.. autoclass:: uvlog.Logger
   :members:
   :inherited-members:
   :undoc-members:
   :exclude-members: __init__

.. autoclass:: uvlog.LogRecord
   :members:
   :undoc-members:
   :exclude-members: __init__, __new__

Handlers
--------

.. autoclass:: uvlog.Handler
   :members:
   :undoc-members:
   :exclude-members: __init__

.. autoclass:: uvlog.QueueHandler
   :members:
   :inherited-members:
   :undoc-members:
   :exclude-members: __init__

.. autoclass:: uvlog.QueueStreamHandler
   :members:
   :inherited-members:
   :undoc-members:
   :exclude-members: __init__

.. autoclass:: uvlog.StreamHandler
   :members:
   :inherited-members:
   :undoc-members:
   :exclude-members: __init__

Formatters
----------

.. autoclass:: uvlog.Formatter
   :members:
   :undoc-members:
   :exclude-members: __init__

.. autoclass:: uvlog.TextFormatter
   :members:
   :undoc-members:
   :exclude-members: __init__

.. autoclass:: uvlog.JSONFormatter
   :members:
   :undoc-members:
   :exclude-members: __init__

Variables
---------

.. data:: uvlog.LOG_CONTEXT
   :annotation: : ContextVar[dict[str, Any]] - Default log context variable

.. data:: uvlog.BASIC_CONFIG
   :annotation: : dict - Default log configuration with stdout and stderr text handlers
