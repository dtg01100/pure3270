Advanced Usage
==============

Macro Scripting DSL
-------------------

Pure3270 supports a powerful macro DSL for automation:

Commands:
- ``WAIT(AID=ENTER, timeout=5)`` - Wait for AID response
- ``WAIT(pattern="welcome", timeout=5)`` - Wait for screen pattern
- ``SENDKEYS("hello ${user}")`` - Send text with variable substitution
- ``IF aid==ENTER: SENDKEYS(hello) ELSE: FAIL(error)`` - Conditional execution
- ``CALL MACRONAME`` - Call nested macro
- ``SET var = value`` - Set variable
- ``SYSREQ(ATN)`` - Send system request

Example macro:
.. code-block:: text

    DEFINE LOGIN
    SENDKEYS("user123")
    key TAB
    SENDKEYS("${password}")
    key ENTER
    WAIT(pattern="Welcome", timeout=10)
    END

Loading and executing:
.. code-block:: python

    session.load_macro("login.macro")
    result = session.execute_macro("LOGIN", {"password": "secret"})

Printer Sessions
----------------

For printer LU support:
.. code-block:: python

    session = Session(host="printer-host", printer_mode=True)
    session.connect()
    # Handle SCS data streams
    printer_status = session.printer_buffer.get_status()

SNA Response Handling
---------------------

Advanced SNA state tracking:
.. code-block:: python

    if session.sna_session_state == "BIND_COMPLETE":
        # Session ready for 3270 data
        pass
    elif response.is_negative():
        # Handle error recovery
        session.reconnect()

Custom Negotiation
------------------

Extend negotiation:
.. code-block:: python

    class CustomNegotiator(Negotiator):
        async def _negotiate_tn3270(self):
            # Custom device type negotiation
            await super()._negotiate_tn3270()
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
- Async macro execution for parallel operations
- Memory limits via RLIMIT_AS for resource-constrained environments
