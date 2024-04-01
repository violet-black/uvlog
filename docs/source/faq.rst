.. _faq:

FAQ
===

**Q: How can I enable filenames and line numbers for all my log records?**

By default trace is enabled only for exceptions. To enable it for all records set a logger's `capture_trace`
attribute to `True`.

**Q: How can I enable JSON logs for my logger?**

The best way is to use the :py:func:`uvlog.configure` function and change a formatter for provided handlers. By
default all loggers use the 'stderr' handler, so you can simply override its config like this.

.. code-block:: python

    uvlog.configure({
        'handlers': {
            'stderr': {
                'format': 'json'
            }
        }
    })

**Q: How can I enable the logging queue?**

Use config to change the handler to the :py:class:`~uvlog.QueueStreamHandler`.

.. code-block:: python

    uvlog.configure({
        'handlers': {
            'stderr': {
                'class': 'QueueStreamHandler'
            }
        }
    })

**Q: How can I enable log sampling?**

Define the :py:attr:`~uvlog.Logger.sample_rate` < 1 in a logger configuration.

.. code-block:: python

    root_logger = uvlog.configure({
        'loggers': {
            '': {
                'sample_rate': 0.25
            }
        }
    })
