Examples
========

This section provides practical examples of using Pure3270 in various scenarios.

.. note::
   **For comprehensive protocol examples and advanced patterns**, see the new dedicated sections:

   * :doc:`protocol_examples` - Complete TN3270/TN3270E protocol examples with detailed explanations
   * :doc:`advanced_patterns` - Advanced usage patterns and optimization techniques
   * :doc:`integration_scenarios` - Real-world enterprise integration examples

For basic examples demonstrating API usage patterns, see the example files in the ``examples/`` directory:

Core Usage Patterns
-------------------

**Standalone Sessions** - Basic synchronous and asynchronous session usage

**P3270 Compatibility** - Drop-in replacement for p3270 applications

**Screen Operations** - Basic screen buffer manipulation and field operations

**Error Handling** - Connection errors, timeouts, and recovery patterns

**Protocol Operations** - Low-level TN3270/TN3270E protocol operations

**File Transfers** - IND$FILE protocol for uploading/downloading files

Getting Started Examples
------------------------

Standalone Synchronous Session
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from pure3270 import Session

   with Session() as session:
       session.connect('your-host.example.com', port=23, ssl_context=None)
       session.key('Enter')
       print(session.ascii(session.read()))

Standalone Asynchronous Session
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   from pure3270 import AsyncSession

   async def main():
       async with AsyncSession() as session:
           await session.connect('your-host.example.com', port=23, ssl_context=None)
           await session.key('Enter')
           print(session.ascii(await session.read()))

   asyncio.run(main())


Using P3270Client API
~~~~~~~~~~~~~~~~~~~~~

Pure3270 implements a superset of the ``p3270`` library API through its native ``P3270Client``
class. This provides 100% drop-in compatibility without requiring any external dependencies:

.. code-block:: python

   from pure3270 import P3270Client

   # Use p3270-compatible API directly
   session = P3270Client(hostName='your-host.example.com', hostPort=23)
   session.connect()
   session.sendEnter()  # Using P3270Client methods
   screen_text = session.getScreen()
   print(screen_text)
   session.close()

Since ``pure3270.P3270Client`` implements the full ``p3270`` API natively, existing p3270 code
can simply replace the import statement:

.. code-block:: python

   # Before: import p3270
   # After:  from pure3270 import P3270Client as p3270
   from pure3270 import P3270Client as p3270

   session = p3270.P3270Client()  # Now using pure3270 implementation
   session.connect('your-host.example.com', port=23, ssl_context=None)
   session.key('Enter')
   screen_text = session.ascii(session.read())
   print(screen_text)
   session.close()

Selecting Terminal Models
~~~~~~~~~~~~~~~~~~~~~~~~~

You can pass ``terminal_type`` when creating sessions to emulate different IBM models:

.. code-block:: python

    from pure3270 import Session

    # Emulate a color 32x80 terminal (3279 Model 3)
    with Session(terminal_type="IBM-3279-3") as session:
       session.connect('your-host.example.com', port=23)
       print("Screen size:", session.screen_buffer.rows, "x", session.screen_buffer.cols)

    # Emulate a wide 27x132 terminal (3278 Model 5)
    with Session(terminal_type="IBM-3278-5") as session:
       session.connect('your-host.example.com', port=23)
       print("Screen size:", session.screen_buffer.rows, "x", session.screen_buffer.cols)

See :doc:`terminal_models` for the full list of supported terminal types and details.

Advanced Examples
-----------------

.. note::
   **For comprehensive protocol examples and advanced patterns**, see:

   * :doc:`protocol_examples` - Complete TN3270/TN3270E protocol examples
   * :doc:`advanced_patterns` - Advanced patterns and optimization

Basic Screen Operations
~~~~~~~~~~~~~~~~~~~~~~~~~

The ``examples/example_advanced_screen_operations.py`` file demonstrates:

- Direct screen buffer manipulation
- Field detection and navigation
- EBCDIC/ASCII conversion
- Cursor positioning and text input
- Screen reading and parsing

Run with: ``python examples/example_advanced_screen_operations.py``

Basic Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~

The ``examples/example_error_handling.py`` file demonstrates:

- Connection errors and recovery
- Timeout handling
- SSL/TLS certificate validation
- Network interruption recovery
- Terminal configuration errors
- Operation error handling

Run with: ``python examples/example_error_handling.py``

Basic Protocol Operations
~~~~~~~~~~~~~~~~~~~~~~~~~

The ``examples/example_protocol_operations.py`` file demonstrates:

- TN3270 protocol negotiation details
- Data stream manipulation
- EBCDIC encoding operations
- IND$FILE transfer protocol framework
- Protocol utility functions

Run with: ``python examples/example_protocol_operations.py``

.. note::
   **For comprehensive protocol implementation examples**, see :doc:`protocol_examples`

Real-World Usage Examples
------------------------

Several examples are available in the ``examples/`` directory:

- ``example_end_to_end.py`` - Complete session lifecycle with login
- ``example_pub400*.py`` - Real TN3270 host interactions
- ``example_terminal_models.py`` - Terminal model configurations
- ``example_standalone.py`` - Basic standalone usage patterns

File Transfer with IND$FILE
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pure3270 supports file transfer using the IND$FILE protocol:

.. code-block:: python

    import asyncio
    from pure3270 import AsyncSession

    async def file_transfer_example():
        async with AsyncSession() as session:
            await session.connect('your-host.example.com', port=23)

            # Upload a local file to the host
            await session.send_file('/local/path/source.txt', 'destination.txt')

            # Download a file from the host
            await session.receive_file('remote_file.txt', '/local/path/downloaded.txt')

            print("File transfer completed successfully")

    asyncio.run(file_transfer_example())

All example files are executable and include detailed comments explaining the functionality demonstrated.

.. note::
   **For comprehensive real-world integration scenarios**, see :doc:`integration_scenarios` which includes:

   * Enterprise banking system integration
   * Multi-session management patterns
   * Printer emulation scenarios
   * MCP server integration for AI systems
   * Network resilience patterns
   * Production deployment configurations
