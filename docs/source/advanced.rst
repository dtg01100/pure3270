Advanced Usage
==============

Macro scripting/DSL has been removed and is not supported. It will not be reintroduced.

Printer Sessions
----------------

For printer LU support:
.. code-block:: python

    session = Session()
    session.connect("printer-host")
    # Handle SCS data streams
    printer_status = session.printer_buffer.get_status()

SNA Response Handling
---------------------

Advanced SNA state tracking:
.. code-block:: python

    if session.sna_session_state == "NORMAL":
        # Session ready for 3270 data
        pass
    # Note: response.is_negative() not implemented; use exception handling for error recovery
    # session.reconnect() not implemented; use close() and connect() for recovery

Custom Negotiation
------------------

Extend negotiation:
.. code-block:: python

    class CustomNegotiator(Negotiator):
        async def negotiate_tn3270(self):
            # Custom device type negotiation
            await super().negotiate_tn3270()
            await self._send_custom_query()

Patching Integration
--------------------

For p3270 compatibility:
.. code-block:: python

    from pure3270.patching import enable_replacement

    enable_replacement()  # Enable monkey patching
    # Now s3270 APIs work with pure3270 backend

Performance Optimization
------------------------

- Use buffer pools for large data streams
- Batch AID submissions
- Memory limits via RLIMIT_AS for resource-constrained environments
