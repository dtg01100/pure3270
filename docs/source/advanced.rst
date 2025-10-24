Advanced Usage
==============

Macro scripting/DSL has been removed and is not supported. It will not be reintroduced.

Printer Sessions
----------------

Pure3270 provides high-level printer session support for TN3270E printer LU operations:

**Synchronous Printer Sessions:**

.. code-block:: python

    from pure3270 import PrinterSession

    with PrinterSession(host="printer-host.example.com", port=23) as session:
        # Wait for print jobs
        import time
        time.sleep(5)

        # Get printed output
        output = session.get_printer_output()
        print("Printer output:", output)

        # Check printer status
        status = session.get_printer_status()
        print(f"Status: 0x{status:02x}")

**Asynchronous Printer Sessions:**

.. code-block:: python

    import asyncio
    from pure3270 import AsyncPrinterSession

    async def monitor_printer():
        async with AsyncPrinterSession(host="printer-host.example.com") as session:
            while True:
                await asyncio.sleep(5)
                output = await session.get_printer_output()
                if output:
                    print("New print job received:", output)
                    break

    asyncio.run(monitor_printer())

**Low-level Printer Support:**

For advanced use cases, you can still access the underlying printer buffer:

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

P3270 API Compatibility
------------------------

Pure3270 implements a superset of the ``p3270`` library API natively:

.. code-block:: python

    from pure3270 import P3270Client

    # Drop-in replacement for p3270.P3270Client
    session = P3270Client(hostName='host', hostPort=23)
    session.connect()
    session.sendEnter()
    print(session.getScreen())
    session.close()

    # For existing code, simply change the import:
    # from pure3270 import P3270Client as p3270

Performance Optimization
------------------------

- Use buffer pools for large data streams
- Batch AID submissions
- Memory limits via RLIMIT_AS for resource-constrained environments
