Developer Guide
==================

This comprehensive guide helps developers quickly find and understand the right resources for working with Pure3270 and TN3270 protocols.

Quick Start Navigation
----------------------

**New to Pure3270?** → Start with :doc:`installation` and :doc:`usage`

**Need Protocol Details?** → See :doc:`protocol_examples`

**Looking for Advanced Patterns?** → Check :doc:`advanced_patterns`

**Enterprise Integration?** → Review :doc:`integration_scenarios`

**API Reference?** → Go to :doc:`api`

Documentation Structure
-----------------------

Getting Started
~~~~~~~~~~~~~~~

* :doc:`installation` - Setting up Pure3270 environment
* :doc:`usage` - Basic usage patterns and concepts
* :doc:`examples` - Common usage examples and code samples
* :doc:`terminal_models` - Available terminal models and specifications

Protocol & Deep Technical Content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* :doc:`protocol_examples` - **NEW**: Comprehensive TN3270/TN3270E protocol examples
  * Basic connection flows with step-by-step examples
  * TN3270E negotiation with detailed explanations
  * Data stream parsing examples
  * Screen buffer manipulation examples
  * Field attribute handling examples
  * Protocol error handling examples
  * Connection recovery examples

* :doc:`advanced_patterns` - **NEW**: Advanced usage patterns and optimization
  * Complex session management patterns
  * Error handling and recovery strategies
  * Performance optimization techniques
  * Custom protocol extensions
  * Testing strategies for protocol implementations

* :doc:`protocol` - Low-level protocol implementation details
  * IND$FILE file transfer protocol
  * Protocol utility functions
  * Data stream handling

Reference Documentation
~~~~~~~~~~~~~~~~~~~~~~~

* :doc:`api` - Complete API reference with all modules and classes
* :doc:`session` - Session management and lifecycle
* :doc:`emulation` - Screen buffer and terminal emulation
* :doc:`patching` - Patching and compatibility features
* :doc:`terminal_models` - Terminal model specifications
* :doc:`advanced` - Advanced features (printer sessions, etc.)
* :doc:`warnings` - Warning system and categorization

Learning Path by Use Case
-------------------------

For Application Developers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Basic Integration** → :doc:`installation` → :doc:`usage` → :doc:`examples`
2. **API Compatibility** → :doc:`usage` (P3270Client section) → :doc:`examples`
3. **Terminal Configuration** → :doc:`terminal_models` → :doc:`usage`
4. **Basic Error Handling** → :doc:`examples` → :doc:`advanced` (Error Handling section)

For Protocol Engineers
~~~~~~~~~~~~~~~~~~~~~~

1. **Protocol Fundamentals** → :doc:`protocol_examples` (Basic Connection Flow)
2. **TN3270E Features** → :doc:`protocol_examples` (TN3270E Negotiation)
3. **Data Stream Processing** → :doc:`protocol_examples` (Data Stream Parsing)
4. **Error Recovery** → :doc:`protocol_examples` (Error Handling)
5. **Protocol Implementation** → :doc:`protocol` → :doc:`advanced_patterns`

For Enterprise Architects
~~~~~~~~~~~~~~~~~~~~~~~~~

1. **System Integration** → :doc:`integration_scenarios` (Enterprise Integration)
2. **High Availability** → :doc:`integration_scenarios` (Multi-Session Management)
3. **Printer Management** → :doc:`integration_scenarios` (Printer Emulation)
4. **Network Resilience** → :doc:`integration_scenarios` (Network Resilience)
5. **Production Deployment** → :doc:`integration_scenarios` (Production Deployment)
6. **MCP Integration** → :doc:`integration_scenarios` (MCP Server Integration)

For Performance Engineers
~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Session Management** → :doc:`advanced_patterns` (Session Management)
2. **Performance Optimization** → :doc:`advanced_patterns` (Performance Optimization)
3. **Resource Management** → :doc:`advanced_patterns` (Memory Optimization)
4. **Monitoring Integration** → :doc:`integration_scenarios` (Production Monitoring)

For Security Engineers
~~~~~~~~~~~~~~~~~~~~~~

1. **Connection Security** → :doc:`usage` (SSL/TLS Configuration)
2. **Authentication** → :doc:`integration_scenarios` (Enterprise Authentication)
3. **Network Security** → :doc:`integration_scenarios` (Network Resilience)
4. **Compliance** → :doc:`integration_scenarios` (Production Security)

Example Code Organization
-------------------------

The examples directory contains organized code samples:

Core Examples (``examples/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``example_standalone.py`` - Basic standalone usage
* ``example_advanced_screen_operations.py`` - Advanced screen manipulation
* ``example_error_handling.py`` - Error handling patterns
* ``example_protocol_operations.py`` - Protocol-level operations
* ``example_end_to_end.py`` - Complete workflow examples

Real-World Examples (``examples/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``example_pub400*.py`` - Real mainframe interactions
* ``example_printer_session.py`` - Printer session management
* ``example_terminal_models.py`` - Terminal model configurations

Development and Testing Examples (``examples/``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``trace_*.py`` - Protocol tracing and debugging
* ``integration_test.py`` - Integration testing patterns
* ``batch_*.py`` - Performance and batch testing

Protocol Implementation Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Connection Flows**: :doc:`protocol_examples` - Basic TN3270 Connection Flow
* **Negotiation**: :doc:`protocol_examples` - TN3270E Negotiation Details
* **Data Processing**: :doc:`protocol_examples` - Data Stream Parsing Examples
* **Error Recovery**: :doc:`protocol_examples` - Protocol Error Handling
* **Session Management**: :doc:`advanced_patterns` - Complex Session Management

Enterprise Integration Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Banking Systems**: :doc:`integration_scenarios` - Bank Processing System
* **Multi-Session**: :doc:`integration_scenarios` - Enterprise Session Management
* **Printer Management**: :doc:`integration_scenarios` - Enterprise Printer Management
* **MCP Integration**: :doc:`integration_scenarios` - AI-Integrated Terminals
* **Network Resilience**: :doc:`integration_scenarios` - Mission-Critical Environments
* **Production**: :doc:`integration_scenarios` - Enterprise Production Deployment

Common Development Tasks
-----------------------

Creating a New Session
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from pure3270 import AsyncSession

    async def create_session():
        async with AsyncSession() as session:
            await session.connect('mainframe.example.com')
            # Session ready for use

See: :doc:`usage`, :doc:`examples`

Handling Protocol Errors
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    from pure3270.exceptions import ConnectionError

    async def robust_connection():
        for attempt in range(3):
            try:
                session = AsyncSession()
                await session.connect('mainframe.example.com')
                return session
            except ConnectionError:
                await asyncio.sleep(1)
        raise ConnectionError("Failed to connect")

See: :doc:`protocol_examples` (Protocol Error Handling Examples), :doc:`advanced_patterns`

Implementing File Transfer
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async def transfer_file():
        async with AsyncSession() as session:
            await session.connect('mainframe.example.com')
            await session.send_file('local.txt', 'remote.txt')
            await session.receive_file('remote.txt', 'local_copy.txt')

See: :doc:`protocol` (IND$FILE Protocol), :doc:`examples`

Managing Multiple Sessions
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async def multi_session_example():
        sessions = []
        for i in range(5):
            session = AsyncSession()
            await session.connect(f'mainframe{i}.example.com')
            sessions.append(session)

        # Use sessions...
        for session in sessions:
            await session.close()

See: :doc:`integration_scenarios` (Multi-Session Management), :doc:`advanced_patterns`

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    from pure3270 import AsyncSession

    async def batch_operations():
        async with AsyncSession() as session:
            await session.connect('mainframe.example.com')

            # Batch operations for performance
            await session.string("DATA1")
            await session.key("ENTER")
            await session.key("TAB")
            await session.string("DATA2")
            await session.key("ENTER")

See: :doc:`advanced_patterns` (Performance Optimization)

Troubleshooting Guide
--------------------

Common Issues and Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Connection Timeout**

* **Problem**: Connections timing out
* **Solution**: Increase timeout values, check network connectivity
* **See**: :doc:`protocol_examples` (Connection Recovery Examples)

**Screen Parsing Errors**

* **Problem**: Cannot parse screen data correctly
* **Solution**: Use proper EBCDIC/ASCII conversion, check field attributes
* **See**: :doc:`protocol_examples` (Data Stream Parsing Examples)

**Performance Issues**

* **Problem**: Slow operation response times
* **Solution**: Implement connection pooling, optimize data handling
* **See**: :doc:`advanced_patterns` (Performance Optimization)

**Memory Usage**

* **Problem**: High memory consumption
* **Solution**: Implement proper session cleanup, buffer management
* **See**: :doc:`advanced_patterns` (Memory Optimization)

Debugging Tools
~~~~~~~~~~~~~~

Protocol Tracing
"""""""""""""""

Enable detailed protocol logging:

.. code-block:: python

    from pure3270 import setup_logging

    setup_logging(level="DEBUG", component="tn3270")

Screen State Analysis
"""""""""""""""""""""

Analyze current screen state:

.. code-block:: python

    screen_text = session.ascii(session.read())
    print("Screen content:", screen_text)

    # Analyze fields
    fields = session.screen_buffer.get_fields()
    for field in fields:
        print(f"Field at {field.position}: {field.attribute}")

See: :doc:`examples` (example_trace.py), :doc:`examples` (example_advanced_screen_operations.py)

Integration Checkpoints
~~~~~~~~~~~~~~~~~~~~~~~

Before Production Deployment
"""""""""""""""""""""""""""

✓ **Security Review**
  - SSL/TLS configuration validated
  - Authentication mechanisms tested
  - Network security measures implemented

✓ **Performance Testing**
  - Load testing completed
  - Response time benchmarks met
  - Resource usage optimized

✓ **Reliability Testing**
  - Connection recovery tested
  - Failover mechanisms verified
  - Error handling validated

✓ **Monitoring Setup**
  - Metrics collection configured
  - Alerting rules defined
  - Performance baselines established

See: :doc:`integration_scenarios` (Production Deployment)

Code Quality Guidelines
-----------------------

For Pure3270 Development
~~~~~~~~~~~~~~~~~~~~~~~~

* Follow :doc:`CONTRIBUTING` guidelines
* Ensure all code passes linting: ``python -m flake8 pure3270/``
* Run type checking: ``python -m mypy pure3270/``
* Format code: ``python -m black pure3270/``
* Run tests: ``python -m pytest tests/``

For Documentation Contributions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Update relevant documentation sections
* Add examples for new features
* Ensure code examples are tested
* Update this guide if adding new sections

Best Practices Summary
~~~~~~~~~~~~~~~~~~~~~~

1. **Always use context managers** for session lifecycle
2. **Implement proper error handling** with recovery strategies
3. **Use connection pooling** for production environments
4. **Enable detailed logging** for troubleshooting
5. **Test with real mainframe systems** when possible
6. **Follow RFC specifications** for protocol implementation
7. **Use proper EBCDIC/ASCII conversion** functions
8. **Implement resource cleanup** in finally blocks

Additional Resources
-------------------

External References
~~~~~~~~~~~~~~~~~~~

* RFC 854 - Telnet Protocol Specification
* RFC 1576 - TN3270 Current Practices
* RFC 1646 - TN3270 Extensions for LUname and-printer Session
* IBM 3270 Information Display System: Data Stream Programmer's Reference

Community and Support
~~~~~~~~~~~~~~~~~~~~

* GitHub Issues - Bug reports and feature requests
* GitHub Discussions - Community support and questions
* Code Examples - Additional examples in the repository

Version History
~~~~~~~~~~~~~~

* **v3.0** - Major protocol examples and advanced patterns added
* **v2.0** - Enhanced enterprise integration features
* **v1.0** - Initial release with basic TN3270 support

This developer guide provides a comprehensive navigation framework for the enhanced Pure3270 documentation. Use the cross-references to find specific information quickly and efficiently.
