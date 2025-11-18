Protocol Examples
==================

This section provides comprehensive examples of TN3270/TN3270E protocol operations, from basic connections to advanced scenarios.

For basic protocol operations and EBCDIC handling examples, see the :doc:`examples` section. For detailed protocol specifications, see the :doc:`protocol` module documentation.

Basic TN3270 Connection Flow
-----------------------------

Complete step-by-step TN3270 connection with detailed protocol operations:

.. code-block:: python

    import asyncio
    from pure3270 import AsyncSession, setup_logging

    async def basic_tn3270_connection():
        """Demonstrate complete TN3270 connection flow."""

        # Setup detailed logging to see protocol exchange
        setup_logging(level="DEBUG", component="tn3270")

        async with AsyncSession() as session:
            # Step 1: Create session with specific terminal model
            session = AsyncSession(terminal_type="IBM-3278-2")

            # Step 2: Connect to host
            # This initiates TN3270 negotiation
            await session.connect('mainframe.example.com', port=23)

            # Step 3: Read initial screen
            screen_data = await session.read()
            print(f"Initial screen size: {session.screen_buffer.rows}x{session.screen_buffer.cols}")

            # Step 4: Send attention identifier (AID) to get initial screen
            await session.key('Enter')
            screen = session.ascii(session.read())

            # Step 5: Navigate through application
            await session.string("LOGON")  # Enter application name
            await session.key('Enter')     # Submit

            return session

TN3270E Negotiation Details
----------------------------

Detailed TN3270E protocol negotiation with structured fields:

.. code-block:: python

    import asyncio
    from pure3270.protocol.negotiator import Negotiator
    from pure3270.protocol.tn3270e_header import TN3270EHeader, TN3270EDataStream

    async def tn3270e_negotiation_example():
        """Demonstrate TN3270E protocol negotiation."""

        async with AsyncSession() as session:
            # Connect triggers automatic TN3270E negotiation
            await session.connect('host.example.com', port=23, use_tn3270e=True)

            # TN3270E negotiation involves:
            # 1. Device type negotiation (TN3270E command)
            # 2. Bind session (TN3270E command)
            # 3. LU assignment (TN3270E command)

            # Check if TN3270E is active
            if hasattr(session, '_tn3270e_active') and session._tn3270e_active:
                print("TN3270E negotiation successful")

                # TN3270E provides additional features:
                # - Structured fields (SF)
                # - SCS printer data streams
                # - Extended error handling

                # Send structured field query
                # In real implementation, this would create proper SF
                print("Structured field capabilities available")
            else:
                print("Standard TN3270 connection established")

Data Stream Parsing Examples
-----------------------------

Comprehensive data stream parsing and manipulation:

.. code-block:: python

    import asyncio
    from pure3270 import AsyncSession
    from pure3270.protocol.data_stream import DataStreamParser
    from pure3270.emulation.screen_buffer import ScreenBuffer
    from pure3270.emulation.ebcdic import translate_ebcdic_to_ascii

    async def data_stream_parsing_example():
        """Demonstrate comprehensive data stream parsing."""

        async with AsyncSession() as session:
            await session.connect('mainframe.example.com')

            # Get the raw data stream from host
            raw_data = await session.read()

            # Parse TN3270 data stream components
            parser = DataStreamParser()

            # TN3270 data stream consists of:
            # - Order sequences (e.g., Start Field, Set Buffer Address)
            # - Text data (EBCDIC encoded)
            # - Field attributes
            # - Presentation commands

            # Example parsing logic
            print(f"Received {len(raw_data)} bytes of data stream")

            # Convert to screen buffer
            screen = ScreenBuffer(24, 80)

            # Parse orders and text data
            buffer_index = 0
            while buffer_index < len(raw_data):
                byte = raw_data[buffer_index]

                if byte == 0x11:  # Start Field (SF)
                    field_attr = raw_data[buffer_index + 1]
                    screen.add_field_attribute(
                        position=buffer_index,
                        attribute=field_attr
                    )
                    buffer_index += 2
                elif byte == 0x13:  # Set Buffer Address (SBA)
                    # Next 2 bytes contain address
                    addr_high = raw_data[buffer_index + 1]
                    addr_low = raw_data[buffer_index + 2]
                    buffer_index += 3
                elif byte == 0x3C:  # Field attribute byte
                    # Unprotected/protected, highlight, etc.
                    attr_info = {
                        'unprotected': bool(byte & 0x20),
                        'highlights': byte & 0x0F
                    }
                    buffer_index += 1
                else:
                    # Regular text data
                    text_char = translate_ebcdic_to_ascii(bytes([byte]))
                    screen.write_char(byte, position=buffer_index)
                    buffer_index += 1

            print(f"Parsed screen: {screen.to_text()}")

    async def advanced_screen_buffer_manipulation():
        """Advanced screen buffer operations with protocol awareness."""

        async with AsyncSession(terminal_type="IBM-3279-3") as session:
            await session.connect('mainframe.example.com')

            sb = session.screen_buffer

            # Find all unprotected fields (input fields)
            input_fields = []
            current_field = None

            for position, attr_byte in sb.field_attributes.items():
                if attr_byte & 0x20:  # Unprotected field
                    if current_field is None:
                        current_field = {'start': position, 'attributes': []}
                    current_field['attributes'].append(attr_byte)
                else:
                    if current_field:
                        current_field['end'] = position
                        input_fields.append(current_field)
                        current_field = None

            if current_field:
                current_field['end'] = len(sb.buffer)
                input_fields.append(current_field)

            print(f"Found {len(input_fields)} input fields")

            # Navigate to each field and fill it
            for i, field in enumerate(input_fields):
                field_pos = field['start'] + 1  # Skip attribute byte
                row, col = sb.position_to_coords(field_pos)

                # Set cursor to field position
                sb.set_position(row, col)

                # Generate test data for field
                test_data = f"INPUT{i+1:03d}"

                # Clear field first
                field_length = field['end'] - field['start'] - 1
                for j in range(field_length):
                    sb.write_char(0x40, position=field_pos + j)  # Space in EBCDIC

                # Enter data
                for j, char in enumerate(test_data):
                    if j < field_length:
                        ebcdic_char = session.ebcdic(char)
                        sb.write_char(ebcdic_char[0], position=field_pos + j)

            # Submit form
            await session.key('Enter')

            # Read response
            response = session.ascii(session.read())
            print(f"Form submission result: {response}")

Field Attribute Handling Examples
----------------------------------

Advanced field attribute handling and manipulation:

.. code-block:: python

    import asyncio
    from pure3270 import AsyncSession
    from pure3270.emulation.field_attributes import FieldAttribute

    async def field_attribute_examples():
        """Comprehensive field attribute handling."""

        async with AsyncSession() as session:
            await session.connect('mainframe.example.com')
            sb = session.screen_buffer

            # Define field attribute constants
            FA_UNPROTECTED = 0x20  # Field can be modified
            FA_PROTECTED = 0x00    # Field is read-only
            FA_NUMERIC = 0x10      # Numeric-only input
            FA_INTENSITY_NORMAL = 0x00
            FA_INTENSITY_HIGH = 0x01
            FA_INTENSITY_NONDISPLAY = 0x02

            # Create and modify field attributes programmatically
            screen_size = sb.rows * sb.cols

            # Create a login form with various field types
            fields = [
                {'pos': 100, 'type': FA_UNPROTECTED, 'label': 'Username'},
                {'pos': 150, 'type': FA_UNPROTECTED | FA_NUMERIC, 'label': 'Account'},
                {'pos': 200, 'type': FA_UNPROTECTED, 'label': 'Password'},
                {'pos': 250, 'type': FA_PROTECTED | FA_INTENSITY_HIGH, 'label': 'Message'},
            ]

            for field in fields:
                # Set field attribute byte
                sb.field_attributes[field['pos']] = field['type']

                # Add field label if specified
                if 'label' in field:
                    label_bytes = session.ebcdic(field['label'])
                    for i, byte in enumerate(label_bytes):
                        if field['pos'] - 15 + i < screen_size:  # Leave space for FA byte
                            sb.write_char(byte, position=field['pos'] - 15 + i)

            # Demonstrate field validation
            def validate_field_data(field_pos, expected_length, data):
                """Validate data for a specific field."""
                field_attr = sb.field_attributes.get(field_pos, 0)

                # Check if field is protected
                if not (field_attr & FA_UNPROTECTED):
                    raise ValueError("Field is read-only")

                # Check for numeric-only fields
                if field_attr & FA_NUMERIC:
                    for char in data:
                        if not char.isdigit():
                            raise ValueError("Numeric field contains non-digit")

                # Check length
                if len(data) > expected_length:
                    raise ValueError(f"Data too long for field (max {expected_length})")

                return True

            # Test field validation
            try:
                validate_field_data(150, 10, "1234567890")  # Should succeed
                validate_field_data(150, 10, "ABC123")       # Should fail - contains letters
                print("Field validation working correctly")
            except ValueError as e:
                print(f"Validation error: {e}")

            # Process form submission
            await session.key('Enter')

Screen Buffer Reconstruction Examples
-------------------------------------

Advanced screen buffer reconstruction from protocol data:

.. code-block:: python

    import asyncio
    from pure3270 import AsyncSession
    from pure3270.emulation.screen_buffer import ScreenBuffer
    from pure3270.emulation.addressing import parse_address

    async def screen_reconstruction_example():
        """Reconstruct screen from raw TN3270 data stream."""

        async with AsyncSession(terminal_type="IBM-3278-4") as session:
            await session.connect('mainframe.example.com')

            # Capture raw network data
            raw_stream = await session.read()

            # Create screen buffer for reconstruction
            screen = ScreenBuffer(session.screen_buffer.rows,
                                session.screen_buffer.cols)

            # Parse TN3270 orders and reconstruct screen
            i = 0
            current_address = 0  # Start at screen position 0

            while i < len(raw_stream):
                byte = raw_stream[i]

                if byte == 0x11:  # Start Field (SF)
                    field_attr = raw_stream[i + 1]
                    screen.field_attributes[current_address] = field_attr

                    # Next position after field attribute
                    current_address += 1
                    i += 2

                elif byte == 0x13:  # Set Buffer Address (SBA)
                    # Next 2 bytes are the address (12-bit format)
                    addr_high = raw_stream[i + 1]
                    addr_low = raw_stream[i + 2]
                    current_address = parse_address(addr_high, addr_low)
                    i += 3

                elif byte == 0x12:  # Repeat to Address (RA)
                    repeat_char = raw_stream[i + 1]
                    addr_high = raw_stream[i + 2]
                    addr_low = raw_stream[i + 3]
                    target_address = parse_address(addr_high, addr_low)

                    # Fill positions with repeat character
                    distance = target_address - current_address
                    for pos in range(distance):
                        if current_address + pos < len(screen.buffer):
                            screen.buffer[current_address + pos] = repeat_char

                    current_address = target_address
                    i += 4

                elif byte == 0x3D:  # Erase to End of Field (EOF)
                    # Fill current field with spaces
                    field_start = current_address
                    while field_start > 0 and 0x3C not in screen.field_attributes.get(field_start, [0]):
                        field_start -= 1

                    if field_start > 0:
                        field_start += 1

                        # Find field end
                        field_end = current_address
                        pos = current_address
                        while pos < len(screen.buffer):
                            if 0x3E in screen.field_attributes.get(pos, []):
                                field_end = pos
                                break
                            pos += 1

                        # Clear field
                        for pos in range(field_start, min(field_end + 1, len(screen.buffer))):
                            screen.buffer[pos] = 0x40  # EBCDIC space

                    i += 1

                else:
                    # Regular character data
                    if current_address < len(screen.buffer):
                        screen.buffer[current_address] = byte
                    current_address += 1
                    i += 1

            # Convert to readable format
            display_text = translate_ebcdic_to_ascii(screen.to_bytes())

            print(f"Reconstructed screen ({screen.rows}x{screen.cols}):")
            print("=" * 50)
            for row in range(screen.rows):
                line_start = row * screen.cols
                line_end = line_start + screen.cols
                line_data = screen.to_bytes()[line_start:line_end]
                print(f"{row+1:2d}: {translate_ebcdic_to_ascii(line_data)}")

            return screen

    async def interactive_screen_update():
        """Demonstrate real-time screen updates from protocol data."""

        async with AsyncSession() as session:
            await session.connect('mainframe.example.com')

            # Initial screen
            initial_screen = session.ascii(session.read())
            print("Initial screen received")

            # Wait for screen changes
            while True:
                try:
                    # Read with timeout to avoid blocking indefinitely
                    new_data = await asyncio.wait_for(session.read(), timeout=30.0)

                    if new_data:
                        # Compare with previous screen
                        new_screen = ScreenBuffer(session.screen_buffer.rows,
                                                session.screen_buffer.cols)

                        # Parse new data
                        # ... (similar to reconstruction example)

                        print("Screen update received")
                        break  # Exit for demo purposes

                except asyncio.TimeoutError:
                    print("No screen updates received in 30 seconds")
                    break

Protocol Error Handling Examples
---------------------------------

Comprehensive protocol error handling and recovery:

.. code-block:: python

    import asyncio
    import logging
    from pure3270 import AsyncSession, setup_logging
    from pure3270.exceptions import TN3270Error, ConnectionError, ProtocolError

    async def protocol_error_handling_example():
        """Demonstrate comprehensive protocol error handling."""

        # Setup detailed protocol logging
        logger = logging.getLogger('tn3270.protocol')
        logger.setLevel(logging.DEBUG)

        async def robust_connection():
            """Connection with comprehensive error handling."""

            # Retry configuration
            max_retries = 3
            retry_delay = 5.0
            timeout = 30.0

            session = None
            for attempt in range(max_retries + 1):
                try:
                    session = AsyncSession(terminal_type="IBM-3278-2")

                    # Connection timeout
                    await asyncio.wait_for(
                        session.connect('mainframe.example.com', port=23),
                        timeout=timeout
                    )

                    # Verify connection with test read
                    await asyncio.wait_for(
                        session.read(),
                        timeout=10.0
                    )

                    print(f"Connection successful on attempt {attempt + 1}")
                    return session

                except asyncio.TimeoutError:
                    print(f"Connection timeout on attempt {attempt + 1}")

                except ConnectionError as e:
                    print(f"Connection error: {e}")

                except ProtocolError as e:
                    print(f"Protocol error: {e}")

                except Exception as e:
                    print(f"Unexpected error: {type(e).__name__}: {e}")

                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)

            raise ConnectionError("All connection attempts failed")

        # Handle different error scenarios
        try:
            session = await robust_connection()

            # Screen read with error handling
            try:
                screen_data = await asyncio.wait_for(session.read(), timeout=15.0)
                print(f"Screen data received: {len(screen_data)} bytes")

            except asyncio.TimeoutError:
                print("Screen read timeout - host may be unavailable")
                # Attempt reconnection
                await session.connect()

            except Exception as e:
                logger.error(f"Screen read error: {e}")

                # Attempt recovery
                try:
                    await session.send(session.ebcdic('RESET'))
                    screen_data = await session.read()
                    logger.info("Recovery successful")
                except Exception as recovery_error:
                    logger.error(f"Recovery failed: {recovery_error}")
                    raise

            # Keyboard input with validation
            async def safe_input(prompt_text):
                """Safe keyboard input with error handling."""

                try:
                    # Clear any pending input
                    await session.key('CLEAR')

                    # Enter prompt text
                    await session.string(prompt_text)

                    # Submit
                    await session.key('ENTER')

                    # Validate response
                    screen = session.ascii(session.read())

                    # Check for error messages
                    if "ERROR" in screen.upper():
                        raise ValueError("Input resulted in error")

                    return screen

                except Exception as e:
                    logger.error(f"Input error: {e}")

                    # Try recovery sequence
                    try:
                        await session.key('PA1')  # Attention
                        await asyncio.sleep(1)
                        await session.key('CLEAR')  # Clear screen
                        await asyncio.sleep(1)
                        return session.ascii(session.read())
                    except Exception as recovery_error:
                        logger.error(f"Recovery failed: {recovery_error}")
                        raise

            # Use safe input function
            response = await safe_input("TEST INPUT")
            print(f"Response: {response}")

        except Exception as e:
            logger.error(f"Session failed: {e}")

        finally:
            if session:
                await session.close()

Connection Recovery Examples
----------------------------

Network resilience and connection recovery patterns:

.. code-block:: python

    import asyncio
    import time
    from contextlib import asynccontextmanager
    from pure3270 import AsyncSession
    from pure3270.exceptions import ConnectionError

    @asynccontextmanager
    async def resilient_session(host, port=23, max_retries=5, retry_delay=2.0):
        """Context manager for resilient TN3270 sessions."""

        session = None
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                session = AsyncSession()
                await session.connect(host, port, ssl_context=None)

                # Test connection with health check
                await asyncio.wait_for(session.read(), timeout=10.0)

                print(f"Session established after {attempt + 1} attempts")
                yield session
                break

            except Exception as e:
                last_error = e
                print(f"Connection attempt {attempt + 1} failed: {e}")

                if session:
                    try:
                        await session.close()
                    except:
                        pass

                if attempt < max_retries:
                    print(f"Waiting {retry_delay} seconds before retry...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff

        else:
            raise ConnectionError(f"Failed to establish session after {max_retries + 1} attempts: {last_error}")

        try:
            yield session
        finally:
            if session:
                await session.close()

    class SessionManager:
        """Advanced session management with pooling and health monitoring."""

        def __init__(self, host, port=23, pool_size=3, health_check_interval=60):
            self.host = host
            self.port = port
            self.pool_size = pool_size
            self.health_check_interval = health_check_interval
            self.sessions = []
            self._health_task = None
            self._lock = asyncio.Lock()

        async def start(self):
            """Initialize session pool."""
            async with self._lock:
                for _ in range(self.pool_size):
                    try:
                        session = AsyncSession()
                        await session.connect(self.host, self.port)
                        self.sessions.append(session)
                        print(f"Pool session created ({len(self.sessions)}/{self.pool_size})")
                    except Exception as e:
                        print(f"Failed to create pool session: {e}")

                # Start health monitoring
                self._health_task = asyncio.create_task(self._health_monitor())

        async def get_session(self):
            """Get an available session from pool."""
            async with self._lock:
                # Remove any dead sessions
                healthy_sessions = []
                for session in self.sessions:
                    try:
                        # Quick health check
                        await asyncio.wait_for(session.read(), timeout=2.0)
                        healthy_sessions.append(session)
                    except:
                        try:
                            await session.close()
                        except:
                            pass

                self.sessions = healthy_sessions

                # Create new session if pool is depleted
                if not self.sessions:
                    print("Pool depleted, creating new session...")
                    session = AsyncSession()
                    await session.connect(self.host, self.port)
                    self.sessions.append(session)

                # Return session and remove from pool temporarily
                session = self.sessions.pop(0)
                return session

        async def return_session(self, session):
            """Return session to pool."""
            async with self._lock:
                try:
                    # Quick validation
                    await asyncio.wait_for(session.read(), timeout=1.0)
                    self.sessions.append(session)
                    print(f"Session returned to pool ({len(self.sessions)} active)")
                except Exception as e:
                    print(f"Returned session failed validation: {e}")
                    try:
                        await session.close()
                    except:
                        pass

        async def _health_monitor(self):
            """Background health monitoring task."""
            while True:
                await asyncio.sleep(self.health_check_interval)

                async with self._lock:
                    for session in self.sessions.copy():
                        try:
                            await asyncio.wait_for(session.read(), timeout=5.0)
                        except:
                            print("Health check failed, removing session from pool")
                            try:
                                await session.close()
                            except:
                                pass
                            self.sessions.remove(session)

        async def stop(self):
            """Shutdown session pool."""
            if self._health_task:
                self._health_task.cancel()

            async with self._lock:
                for session in self.sessions:
                    try:
                        await session.close()
                    except:
                        pass
                self.sessions.clear()

    async def session_manager_example():
        """Demonstrate session management patterns."""

        # Create resilient connection
        async with resilient_session('mainframe.example.com') as session:
            # Use session normally
            await session.key('Enter')
            screen = session.ascii(session.read())
            print("Resilient session working")

        # Use session manager
        manager = SessionManager('mainframe.example.com')
        await manager.start()

        try:
            # Get session from pool
            session = await manager.get_session()

            # Use session
            await session.string("TEST")
            await session.key('Enter')
            response = session.ascii(session.read())
            print(f"Pool session response: {response}")

            # Return session to pool
            await manager.return_session(session)

        finally:
            await manager.stop()

    async def network_interruption_recovery():
        """Handle network interruptions gracefully."""

        session = AsyncSession()
        await session.connect('mainframe.example.com')

        # Monitor network state
        last_activity = time.time()
        timeout_threshold = 300  # 5 minutes

        try:
            while True:
                try:
                    # Read with short timeout
                    data = await asyncio.wait_for(session.read(), timeout=10.0)
                    if data:
                        last_activity = time.time()
                        print(f"Received {len(data)} bytes")

                except asyncio.TimeoutError:
                    # Check if session is stale
                    if time.time() - last_activity > timeout_threshold:
                        print("Session timeout - reconnecting")
                        await session.close()
                        session = AsyncSession()
                        await session.connect('mainframe.example.com')
                        last_activity = time.time()

                except ConnectionError as e:
                    print(f"Connection lost: {e}")
                    print("Attempting reconnection...")

                    # Exponential backoff reconnection
                    delay = 1.0
                    for _ in range(5):
                        try:
                            await asyncio.sleep(delay)
                            session = AsyncSession()
                            await session.connect('mainframe.example.com')
                            print("Reconnection successful")
                            last_activity = time.time()
                            break
                        except:
                            delay *= 2
                    else:
                        raise

                # Small delay between iterations
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("Monitoring stopped by user")
        finally:
            await session.close()
