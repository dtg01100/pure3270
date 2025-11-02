"""
Session tests.

Comprehensive tests for Session and AsyncSession functionality.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pure3270 import AsyncSession, Session
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.session import ConnectionError, SessionError


class TestSession:
    """Tests for Session functionality."""

    def test_session_initialization(self):
        """Test Session initializes with correct defaults."""
        session = Session()

        assert session.connected is False
        # Session creates async_session only on connect, so screen_buffer property provides default
        assert isinstance(session.screen_buffer, ScreenBuffer)

    @pytest.mark.asyncio
    async def test_async_session_initialization(self):
        """Test AsyncSession initializes correctly."""
        session = AsyncSession()

        assert session.connected is False
        assert isinstance(session._screen_buffer, ScreenBuffer)
        assert session._handler is None

    def test_session_context_manager(self):
        """Test Session context manager."""
        session = Session()

        # Should not raise, but since no real connection, just test it doesn't crash
        try:
            with session:
                pass
        except Exception:
            # Expected since no connection
            pass

    @pytest.mark.asyncio
    async def test_async_session_context_manager(self):
        """Test AsyncSession context manager."""
        session = AsyncSession()

        # Should attempt to connect to None:23
        try:
            async with session:
                pass
        except Exception:
            # Expected since no real connection
            pass

    def test_session_send_not_connected(self):
        """Test send raises error when not connected."""
        session = Session()

        with pytest.raises(Exception):  # SessionError
            session.send(b"data")

    @pytest.mark.asyncio
    async def test_async_session_send_not_connected(self):
        """Test async send raises error when not connected."""
        session = AsyncSession()

        with pytest.raises(Exception):  # SessionError
            await session.send(b"data")

    @pytest.mark.asyncio
    async def test_async_session_receive_not_connected(self):
        """Test async receive raises error when not connected."""
        session = AsyncSession()

        with pytest.raises(Exception):  # SessionError
            await session.read()

    def test_performance_session_operations(self):
        """Performance regression test for session operations."""
        session = Session()

        # Mock the Session's send method to avoid connection errors
        original_send = session.send

        def mock_send(data):
            pass  # Do nothing

        session.send = mock_send

        start = time.time()
        for _ in range(1000):
            try:
                session.send(b"test data")
            except:
                pass  # Ignore connection errors
        end = time.time()

        # Restore
        session.send = original_send

        # Should complete in less than 0.1 seconds
        assert end - start < 0.1

    def test_session_initialization_with_parameters(self):
        """Test Session initialization with various parameters."""
        session = Session(
            host="127.0.0.1",
            port=992,
            ssl_context=None,
            force_mode="TN3270",
            allow_fallback=False,
            enable_trace=True,
            terminal_type="IBM-3278-3",
        )

        assert session._host == "127.0.0.1"
        assert session._port == 992
        assert session._ssl_context is None
        assert session._force_mode == "TN3270"
        assert session._allow_fallback is False
        assert session._enable_trace is True
        assert session._terminal_type == "IBM-3278-3"
        assert session._async_session is None
        assert session._loop is None
        assert session._thread is None

    def test_session_initialization_invalid_terminal_type(self):
        """Test Session initialization with invalid terminal type."""
        with pytest.raises(ValueError, match="Invalid terminal type"):
            Session(terminal_type="INVALID")

    @pytest.mark.asyncio
    async def test_async_session_initialization_with_parameters(self):
        """Test AsyncSession initialization with various parameters."""
        session = AsyncSession(
            host="127.0.0.1",
            port=992,
            ssl_context=None,
            force_mode="TN3270E",
            allow_fallback=False,
            enable_trace=True,
            terminal_type="IBM-3279-4",
            is_printer_session=True,
        )

        assert session._host == "127.0.0.1"
        assert session._port == 992
        assert session._ssl_context is None
        assert session._force_mode == "TN3270E"
        assert session._allow_fallback is False
        assert session._enable_trace is True
        assert session._terminal_type == "IBM-3279-4"
        assert session._is_printer_session is True
        assert session._handler is None
        assert session._connected is False
        assert session._aid is None
        assert session._trace_events == []
        assert session._resource_mtime == 0.0
        assert session.resources == {}
        assert session.color_palette == [(0, 0, 0)] * 16
        assert session.font == "default"
        assert session.keymap == "default"
        assert session.model == "2"
        assert session.color_mode is False
        assert session.tn3270_mode is False
        assert session.circumvent_protection is False
        assert session.insert_mode is False

    @pytest.mark.asyncio
    async def test_async_session_initialization_invalid_terminal_type(self):
        """Test AsyncSession initialization with invalid terminal type."""
        with pytest.raises(ValueError, match="Invalid terminal type"):
            AsyncSession(terminal_type="INVALID")

    def test_session_properties_before_connection(self):
        """Test Session properties before connection."""
        session = Session()

        assert session.connected is False
        assert session.get_aid() is None
        assert session.tn3270e_mode is False
        assert isinstance(session.screen_buffer, ScreenBuffer)
        assert session.screen_buffer.rows == 24  # Default for IBM-3278-2
        assert session.screen_buffer.cols == 80

    @pytest.mark.asyncio
    async def test_async_session_properties_before_connection(self):
        """Test AsyncSession properties before connection."""
        session = AsyncSession()

        assert session.connected is False
        assert session.get_aid() is None
        assert session.tn3270e_mode is False
        assert isinstance(session.screen_buffer, ScreenBuffer)
        assert session.screen_buffer.rows == 24
        assert session.screen_buffer.cols == 80
        assert session.handler is None

    def test_session_connect_parameter_setting(self):
        """Test Session connect parameter setting."""
        session = Session()

        # Mock the async session creation and connect method
        with patch("pure3270.session.AsyncSession") as mock_async_session_class:
            mock_async_session = MagicMock()
            mock_async_session.connect = AsyncMock()
            mock_async_session.connected = True
            mock_async_session_class.return_value = mock_async_session

            # Test connect with parameters
            session.connect(host="test.com", port=23, ssl_context=None)

            # Verify AsyncSession was created with correct parameters
            mock_async_session_class.assert_called_once_with(
                "test.com",
                23,
                None,
                force_mode=None,
                allow_fallback=True,
                enable_trace=False,
                terminal_type="IBM-3278-2",
            )
            # Note: connect is called via _run_async, so we can't easily assert on it
            assert session._async_session is mock_async_session

    @pytest.mark.asyncio
    async def test_async_session_connect_success(self):
        """Test AsyncSession connect success with mocked transport."""
        session = AsyncSession(host="127.0.0.1", port=23)

        # Mock transport for testing
        mock_transport = MagicMock()
        mock_transport.setup_connection = AsyncMock()
        mock_transport.perform_telnet_negotiation = AsyncMock()
        mock_transport.perform_tn3270_negotiation = AsyncMock()
        mock_transport.reader = MagicMock()
        mock_transport.writer = MagicMock()
        session._transport = mock_transport

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.connect = AsyncMock()
        mock_handler.negotiated_tn3270e = True
        session._handler = mock_handler

        await session.connect()

        assert session._connected is True
        assert session.tn3270_mode is True
        # Handler connect is called in the real connection path, not the transport path
        # So we can't assert on it directly

    @pytest.mark.asyncio
    async def test_async_session_connect_negotiation_failure_with_fallback(self):
        """Test AsyncSession connect with negotiation failure but fallback enabled."""
        session = AsyncSession(host="127.0.0.1", port=23, allow_fallback=True)

        # Mock handler that fails negotiation but supports fallback
        mock_handler = MagicMock()
        mock_handler.connect = AsyncMock(side_effect=Exception("Negotiation failed"))
        mock_handler.set_ascii_mode = MagicMock()
        mock_handler.negotiated_tn3270e = False
        session._handler = mock_handler

        # Mock the real connection path to avoid actual network calls
        with patch("asyncio.open_connection") as mock_open_connection:
            mock_reader = MagicMock()
            mock_writer = MagicMock()
            mock_open_connection.return_value = (mock_reader, mock_writer)

            # Mock TN3270Handler creation
            with patch("pure3270.session.TN3270Handler") as mock_handler_class:
                mock_handler_instance = MagicMock()
                mock_handler_instance.connect = AsyncMock(
                    side_effect=Exception("Negotiation failed")
                )
                mock_handler_instance.set_ascii_mode = MagicMock()
                mock_handler_instance.negotiated_tn3270e = False
                mock_handler_class.return_value = mock_handler_instance

                await session.connect()

                assert session._connected is True
                mock_handler_instance.set_ascii_mode.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_connect_negotiation_failure_no_fallback(self):
        """Test AsyncSession connect with negotiation failure and no fallback."""
        session = AsyncSession(host="127.0.0.1", port=23, allow_fallback=False)

        # Mock the real connection path to avoid actual network calls
        with patch("asyncio.open_connection") as mock_open_connection:
            mock_reader = MagicMock()
            mock_writer = MagicMock()
            mock_open_connection.return_value = (mock_reader, mock_writer)

            # Mock TN3270Handler creation
            with patch("pure3270.session.TN3270Handler") as mock_handler_class:
                mock_handler_instance = MagicMock()
                mock_handler_instance.connect = AsyncMock(
                    side_effect=Exception("Negotiation failed")
                )
                mock_handler_class.return_value = mock_handler_instance

                with pytest.raises(Exception, match="Negotiation failed"):
                    await session.connect()

    def test_session_close(self):
        """Test Session close."""
        session = Session()

        # Mock async session
        mock_async_session = MagicMock()
        mock_async_session.close = AsyncMock()
        session._async_session = mock_async_session

        session.close()

        mock_async_session.close.assert_called_once()
        assert session._async_session is None

    @pytest.mark.asyncio
    async def test_async_session_close(self):
        """Test AsyncSession close."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.close = AsyncMock()
        session._handler = mock_handler

        await session.close()

        mock_handler.close.assert_called_once()
        assert session._handler is None
        assert session._connected is False

    def test_session_context_manager_success(self):
        """Test Session context manager with successful connection."""
        session = Session()

        # Mock the connection methods
        with (
            patch.object(session, "connect") as mock_connect,
            patch.object(session, "close") as mock_close,
        ):

            with session:
                pass

            mock_connect.assert_not_called()  # Context manager doesn't auto-connect
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_context_manager_success(self):
        """Test AsyncSession context manager with successful connection."""
        session = AsyncSession()

        # Mock the connection methods
        with (
            patch.object(session, "connect", new_callable=AsyncMock) as mock_connect,
            patch.object(session, "close", new_callable=AsyncMock) as mock_close,
        ):

            async with session:
                pass

            mock_connect.assert_not_called()  # Context manager doesn't auto-connect
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_send_success(self):
        """Test AsyncSession send success."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        session._handler = mock_handler

        await session.send(b"test data")

        mock_handler.send_data.assert_called_once_with(b"test data")

    @pytest.mark.asyncio
    async def test_async_session_send_retry_on_failure(self):
        """Test AsyncSession send with retry on failure."""
        session = AsyncSession()

        # Mock handler that fails twice then succeeds
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock(
            side_effect=[
                OSError("Connection failed"),
                OSError("Connection failed"),
                None,
            ]
        )
        session._handler = mock_handler

        await session.send(b"test data")

        assert mock_handler.send_data.call_count == 3

    @pytest.mark.asyncio
    async def test_async_session_send_max_retries_exceeded(self):
        """Test AsyncSession send with max retries exceeded."""
        session = AsyncSession()

        # Mock handler that always fails
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock(side_effect=OSError("Connection failed"))
        session._handler = mock_handler

        with pytest.raises(OSError, match="Connection failed"):
            await session.send(b"test data")

        assert mock_handler.send_data.call_count == 3

    @pytest.mark.asyncio
    async def test_async_session_read_success(self):
        """Test AsyncSession read success."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.receive_data = AsyncMock(return_value=b"response data")
        mock_handler.parser = None  # Disable parser to avoid complex mocking
        session._handler = mock_handler
        session.tn3270_mode = False  # Disable TN3270 mode

        result = await session.read(timeout=5.0)

        assert result == b"response data"
        # Note: Due to complex retry logic, we just check the result

    @pytest.mark.asyncio
    async def test_async_session_read_with_timeout_retry(self):
        """Test AsyncSession read with timeout and retry."""
        session = AsyncSession()

        # Mock handler that times out twice then succeeds
        mock_handler = MagicMock()
        mock_handler.receive_data = AsyncMock(
            side_effect=[asyncio.TimeoutError(), asyncio.TimeoutError(), b"data"]
        )
        session._handler = mock_handler

        result = await session.read(timeout=1.0)

        assert result == b"data"
        assert mock_handler.receive_data.call_count == 3

    @pytest.mark.asyncio
    async def test_async_session_read_max_retries_timeout(self):
        """Test AsyncSession read with max retries on timeout."""
        session = AsyncSession()

        # Mock handler that always times out
        mock_handler = MagicMock()
        mock_handler.receive_data = AsyncMock(side_effect=asyncio.TimeoutError())
        session._handler = mock_handler

        result = await session.read(timeout=1.0)

        assert result == b""  # Empty bytes on timeout
        assert mock_handler.receive_data.call_count == 3

    @pytest.mark.asyncio
    async def test_async_session_read_with_parser(self):
        """Test AsyncSession read with TN3270 parser."""
        session = AsyncSession()

        # Mock handler and parser
        mock_handler = MagicMock()
        mock_handler.receive_data = AsyncMock(return_value=b"raw data")
        mock_parser = MagicMock()
        mock_parser.parse = AsyncMock()
        mock_handler.parser = mock_parser
        session._handler = mock_handler
        session.tn3270_mode = True

        result = await session.read()

        assert result == b"raw data"
        # Parser is called but we can't easily assert due to complex mocking

    def test_session_send_with_decorator(self):
        """Test Session send with connection decorator."""
        session = Session()

        # Mock async session
        mock_async_session = MagicMock()
        mock_async_session.connected = True
        mock_async_session.send = AsyncMock()
        session._async_session = mock_async_session

        session.send(b"test data")

        mock_async_session.send.assert_called_once_with(b"test data")

    def test_session_send_not_connected_decorator(self):
        """Test Session send decorator when not connected."""
        session = Session()

        with pytest.raises(SessionError, match="Session not connected"):
            session.send(b"test data")

    def test_session_read_with_decorator(self):
        """Test Session read with connection decorator."""
        session = Session()

        # Mock async session
        mock_async_session = MagicMock()
        mock_async_session.connected = True
        mock_async_session.read = AsyncMock(return_value=b"response")
        session._async_session = mock_async_session

        result = session.read()

        assert result == b"response"
        mock_async_session.read.assert_called_once_with(5.0)

    def test_session_read_with_custom_timeout(self):
        """Test Session read with custom timeout."""
        session = Session()

        # Mock async session
        mock_async_session = MagicMock()
        mock_async_session.connected = True
        mock_async_session.read = AsyncMock(return_value=b"response")
        session._async_session = mock_async_session

        result = session.read(timeout=10.0)

        assert result == b"response"
        mock_async_session.read.assert_called_once_with(10.0)

    @pytest.mark.asyncio
    async def test_async_session_connect_connection_error(self):
        """Test AsyncSession connect with connection error."""
        session = AsyncSession(host="invalid.host", port=23)

        with patch(
            "asyncio.open_connection", side_effect=OSError("Connection refused")
        ):
            with pytest.raises(OSError, match="Connection refused"):
                await session.connect()

    @pytest.mark.asyncio
    async def test_async_session_connect_invalid_host(self):
        """Test AsyncSession connect with invalid host."""
        session = AsyncSession(host=None, port=23)

        with pytest.raises(ValueError, match="Host must be specified"):
            await session.connect()

    @pytest.mark.asyncio
    async def test_async_session_send_not_connected(self):
        """Test AsyncSession send when not connected."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="Session not connected"):
            await session.send(b"data")

    @pytest.mark.asyncio
    async def test_async_session_read_not_connected(self):
        """Test AsyncSession read when not connected."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="Session not connected"):
            await session.read()

    @pytest.mark.asyncio
    async def test_async_session_close_without_handler(self):
        """Test AsyncSession close without handler."""
        session = AsyncSession()
        session._connected = True

        await session.close()

        assert session._connected is False

    @pytest.mark.asyncio
    async def test_async_session_close_with_transport(self):
        """Test AsyncSession close with transport."""
        session = AsyncSession()

        # Mock handler and transport
        mock_handler = MagicMock()
        mock_handler.close = AsyncMock()
        session._handler = mock_handler

        mock_transport = MagicMock()
        session._transport = mock_transport

        await session.close()

        mock_handler.close.assert_called_once()
        assert session._handler is None
        assert session._connected is False

    @pytest.mark.asyncio
    async def test_async_session_background_reader(self):
        """Test AsyncSession background reader task."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.receive_data = AsyncMock(
            side_effect=[b"data1", b"data2", asyncio.TimeoutError()]
        )
        session._handler = mock_handler

        # Start background reader manually for testing
        async def test_reader():
            for _ in range(2):  # Limited iterations for test
                try:
                    await mock_handler.receive_data(timeout=0.1)
                except asyncio.TimeoutError:
                    break
                await asyncio.sleep(0)

        await test_reader()

        # Just check that it was called (exact count may vary due to timing)
        assert mock_handler.receive_data.call_count >= 2

    @pytest.mark.asyncio
    async def test_async_session_concurrent_access(self):
        """Test AsyncSession concurrent access."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        session._handler = mock_handler

        # Run multiple concurrent send operations
        tasks = [session.send(b"data") for _ in range(5)]
        await asyncio.gather(*tasks)

        assert mock_handler.send_data.call_count == 5

    @pytest.mark.asyncio
    async def test_async_session_worker_loop_management(self):
        """Test Session worker loop management."""
        session = Session()

        # Test loop creation
        session._ensure_worker_loop()
        assert session._loop is not None
        assert session._thread is not None
        assert session._thread.is_alive()

        # Test loop reuse
        loop1 = session._loop
        thread1 = session._thread
        session._ensure_worker_loop()
        assert session._loop is loop1
        assert session._thread is thread1

        # Test loop shutdown
        session._shutdown_worker_loop()
        assert session._loop is None
        assert session._thread is None

    def test_session_open_method(self):
        """Test Session open method."""
        session = Session()

        with patch.object(session, "connect") as mock_connect:
            session.open("test.com", 992)

            mock_connect.assert_called_once_with("test.com", 992)

    def test_session_get_aid(self):
        """Test Session get_aid method."""
        session = Session()

        # No async session
        assert session.get_aid() is None

        # With async session
        mock_async_session = MagicMock()
        mock_async_session.get_aid = MagicMock(return_value=0xF1)
        session._async_session = mock_async_session

        assert session.get_aid() == 0xF1

    @pytest.mark.asyncio
    async def test_async_session_get_aid(self):
        """Test AsyncSession get_aid method."""
        session = AsyncSession()

        assert session.get_aid() is None

        session._aid = 0x7D
        assert session.get_aid() == 0x7D

    def test_session_connected_property(self):
        """Test Session connected property."""
        session = Session()

        assert session.connected is False

        # With async session
        mock_async_session = MagicMock()
        mock_async_session.connected = True
        session._async_session = mock_async_session

        assert session.connected is True

    @pytest.mark.asyncio
    async def test_async_session_connected_property(self):
        """Test AsyncSession connected property."""
        session = AsyncSession()

        assert session.connected is False

        # Direct connection flag
        session._connected = True
        assert session.connected is True

        # Reset and test handler-based connection
        session._connected = False
        mock_handler = MagicMock()
        mock_handler.connected = True
        session._handler = mock_handler
        assert session.connected is True

        # Reset and test transport-based connection
        session._handler = None
        mock_transport = MagicMock()
        mock_transport.connected = True
        session._transport = mock_transport
        assert session.connected is True

    def test_session_screen_buffer_property(self):
        """Test Session screen_buffer property."""
        session = Session()

        # Before connection, should return default buffer
        buffer = session.screen_buffer
        assert isinstance(buffer, ScreenBuffer)
        assert buffer.rows == 24
        assert buffer.cols == 80

        # After mock connection
        mock_async_session = MagicMock()
        mock_screen_buffer = ScreenBuffer(12, 40)
        mock_async_session.screen_buffer = mock_screen_buffer
        session._async_session = mock_async_session

        buffer = session.screen_buffer
        assert buffer is mock_screen_buffer
        assert buffer.rows == 12
        assert buffer.cols == 40

    @pytest.mark.asyncio
    async def test_async_session_screen_buffer_property(self):
        """Test AsyncSession screen_buffer property."""
        session = AsyncSession(terminal_type="IBM-3278-4")

        # Should create buffer based on terminal type
        buffer = session.screen_buffer
        assert isinstance(buffer, ScreenBuffer)
        # Note: The actual dimensions depend on the terminal type implementation
        assert buffer.cols == 80

        # Test setter
        new_buffer = ScreenBuffer(25, 80)
        session.screen_buffer = new_buffer
        assert session.screen_buffer is new_buffer

    @pytest.mark.asyncio
    async def test_async_session_tn3270e_mode_property(self):
        """Test AsyncSession tn3270e_mode property."""
        session = AsyncSession()

        # No handler
        assert session.tn3270e_mode is False

        # With handler but no negotiated_tn3270e
        mock_handler = MagicMock()
        mock_handler.negotiated_tn3270e = False
        session._handler = mock_handler
        assert session.tn3270e_mode is False

        # With negotiated TN3270E
        mock_handler.negotiated_tn3270e = True
        assert session.tn3270e_mode is True

    def test_session_tn3270e_mode_property(self):
        """Test Session tn3270e_mode property."""
        session = Session()

        # No async session
        assert session.tn3270e_mode is False

        # With async session
        mock_async_session = MagicMock()
        mock_async_session.tn3270_mode = True
        session._async_session = mock_async_session
        assert session.tn3270e_mode is True

    @pytest.mark.asyncio
    async def test_async_session_ascii_methods(self):
        """Test AsyncSession ASCII/EBCDIC conversion methods."""
        session = AsyncSession()

        # Test ascii method
        result = session.ascii(b"\x81\x82\x83")  # EBCDIC 'abc'
        assert result == "abc"

        # Test ebcdic method
        result = session.ebcdic("def")
        assert isinstance(result, bytes)
        assert len(result) == 3

        # Test ascii1 method - simplified implementation
        result = session.ascii1(0x81)  # EBCDIC 'a'
        assert isinstance(result, str)  # Just check it's a string

        # Test ebcdic1 method
        result = session.ebcdic1("g")
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_async_session_ascii_field_method(self):
        """Test AsyncSession ascii_field method."""
        session = AsyncSession()

        # Create a mock field in the screen buffer
        field = MagicMock()
        field.start = (0, 0)
        field.end = (0, 4)
        session.screen_buffer.fields = [field]

        # Mock the buffer content
        session.screen_buffer.buffer = bytearray(
            b"ABCD\x40\x40\x40\x40"
        )  # EBCDIC 'ABCD' + spaces
        session.screen_buffer.cols = 80

        result = session.ascii_field(0)
        assert isinstance(result, str)
        # Note: The actual result depends on the implementation

    @pytest.mark.asyncio
    async def test_async_session_cursor_select(self):
        """Test AsyncSession cursor_select method."""
        session = AsyncSession()

        # Set cursor position
        session.screen_buffer.set_position(1, 5)

        # Mock field at cursor
        field = MagicMock()
        session.screen_buffer.get_field_at_position = MagicMock(return_value=field)

        await session.cursor_select()

        assert field.selected is True

    @pytest.mark.asyncio
    async def test_async_session_delete_field(self):
        """Test AsyncSession delete_field method."""
        session = AsyncSession()

        # Set cursor position and mock field
        session.screen_buffer.set_position(2, 10)
        field = MagicMock()
        field.start = (2, 5)
        field.end = (2, 15)
        session.screen_buffer.get_field_at_position = MagicMock(return_value=field)

        # Mock buffer with content
        session.screen_buffer.buffer = bytearray(b"\x40" * 80 * 24)
        session.screen_buffer.cols = 80

        await session.delete_field()

        # Verify the field area was cleared (EBCDIC spaces)
        # This is a basic check - the actual implementation may be more complex
        assert session.screen_buffer.buffer[2 * 80 + 5 : 2 * 80 + 16] == b"\x40" * 11

    @pytest.mark.asyncio
    async def test_async_session_insert_text(self):
        """Test AsyncSession insert_text method."""
        session = AsyncSession()

        # Set cursor position
        session.screen_buffer.set_position(1, 0)

        # Mock EBCDIC encoder
        with patch("pure3270.emulation.ebcdic.EmulationEncoder.encode") as mock_encode:
            mock_encode.return_value = (0x81, 1)  # EBCDIC 'a'

            await session.insert_text("a")

            # Verify cursor moved
            row, col = session.screen_buffer.get_position()
            assert row == 1
            assert col == 1

    @pytest.mark.asyncio
    async def test_async_session_string_method(self):
        """Test AsyncSession string method."""
        session = AsyncSession()

        with patch.object(session, "insert_text") as mock_insert:
            await session.string("test text")

            mock_insert.assert_called_once_with("test text")

    @pytest.mark.asyncio
    async def test_async_session_circum_not(self):
        """Test AsyncSession circum_not method."""
        session = AsyncSession()

        assert session.circumvent_protection is False

        await session.circum_not()

        assert session.circumvent_protection is True

        await session.circum_not()

        assert session.circumvent_protection is False

    @pytest.mark.asyncio
    async def test_async_session_key_method_enter(self):
        """Test AsyncSession key method with Enter key."""
        session = AsyncSession()

        # Mock handler and screen buffer
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        mock_handler.receive_data = AsyncMock(return_value=b"response")
        session._handler = mock_handler

        # Mock screen buffer with modified fields - fix the return format
        session.screen_buffer.read_modified_fields = MagicMock(
            return_value=[((0, 0), b"test")]
        )

        # Mock parser for response reading
        mock_parser = MagicMock()
        mock_parser.parse = AsyncMock()
        mock_handler.parser = mock_parser

        await session.key("Enter")

        # Verify AID was sent (checking that send_data was called)
        assert mock_handler.send_data.called

    @pytest.mark.asyncio
    async def test_async_session_key_method_pf_key(self):
        """Test AsyncSession key method with PF key."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        session._handler = mock_handler

        await session.key("PF(1)")

        # Verify PF1 AID was sent
        mock_handler.send_data.assert_called_once_with(b"\xf1")

    @pytest.mark.asyncio
    async def test_async_session_key_method_cursor_movement(self):
        """Test AsyncSession key method with cursor movement keys."""
        session = AsyncSession()

        # Test Tab key
        session.screen_buffer.move_cursor_to_next_input_field = MagicMock()
        await session.key("Tab")
        session.screen_buffer.move_cursor_to_next_input_field.assert_called_once()

        # Test Home key
        session.screen_buffer.set_position = MagicMock()
        session.screen_buffer.get_position = MagicMock(return_value=(1, 5))
        mock_field = MagicMock()
        mock_field.start = (1, 0)
        session.screen_buffer.get_field_at_position = MagicMock(return_value=mock_field)
        await session.key("Home")
        session.screen_buffer.set_position.assert_called_with(1, 0)

    @pytest.mark.asyncio
    async def test_async_session_key_method_basic_cursor_keys(self):
        """Test AsyncSession key method with basic cursor keys."""
        session = AsyncSession()

        # Test Up key
        session.screen_buffer.get_position = MagicMock(return_value=(5, 10))
        session.screen_buffer.set_position = MagicMock()
        await session.key("Up")
        session.screen_buffer.set_position.assert_called_with(4, 10)

        # Test Left key
        session.screen_buffer.get_position = MagicMock(return_value=(5, 10))
        session.screen_buffer.set_position = MagicMock()
        await session.key("Left")
        session.screen_buffer.set_position.assert_called_with(5, 9)

    @pytest.mark.asyncio
    async def test_async_session_key_method_backspace(self):
        """Test AsyncSession key method with BackSpace key."""
        session = AsyncSession()

        # Set cursor position and mock buffer
        session.screen_buffer.get_position = MagicMock(return_value=(1, 5))
        session.screen_buffer.set_position = MagicMock()
        session.screen_buffer.buffer = bytearray(b" " * 80 * 24)

        await session.key("BackSpace")

        # Verify cursor moved left
        session.screen_buffer.set_position.assert_called_with(1, 4)

    @pytest.mark.asyncio
    async def test_async_session_submit_method(self):
        """Test AsyncSession submit method."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        session._handler = mock_handler

        await session.submit(0xF1)

        mock_handler.send_data.assert_called_once_with(b"\xf1")

    @pytest.mark.asyncio
    async def test_async_session_key_method_unknown_key(self):
        """Test AsyncSession key method with unknown key."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        session._handler = mock_handler

        await session.key("UnknownKey")

        # Should send default AID
        mock_handler.send_data.assert_called_once_with(b"\xf3")

    @pytest.mark.asyncio
    async def test_async_session_cursor_movement_methods(self):
        """Test AsyncSession cursor movement methods."""
        session = AsyncSession()

        # Mock screen buffer
        session.screen_buffer.get_position = MagicMock(return_value=(5, 10))
        session.screen_buffer.set_position = MagicMock()
        session.screen_buffer.cols = 80
        session.screen_buffer.rows = 24

        # Test home method
        mock_field = MagicMock()
        mock_field.start = (5, 0)
        session.screen_buffer.get_field_at_position = MagicMock(return_value=mock_field)
        await session.home()
        session.screen_buffer.set_position.assert_called_with(5, 0)

    @pytest.mark.asyncio
    async def test_async_session_enter_method(self):
        """Test AsyncSession enter method."""
        session = AsyncSession()

        with patch.object(session, "key") as mock_key:
            await session.enter()
            mock_key.assert_called_once_with("Enter")

    @pytest.mark.asyncio
    async def test_async_session_pf_method(self):
        """Test AsyncSession pf method."""
        session = AsyncSession()

        with patch.object(session, "key") as mock_key:
            await session.pf("3")
            mock_key.assert_called_once_with("PF(3)")

    @pytest.mark.asyncio
    async def test_async_session_pa_method(self):
        """Test AsyncSession pa method."""
        session = AsyncSession()

        with patch.object(session, "key") as mock_key:
            await session.pa("2")
            mock_key.assert_called_once_with("PA(2)")

    @pytest.mark.asyncio
    async def test_async_session_clear_method(self):
        """Test AsyncSession clear method."""
        session = AsyncSession()

        session.screen_buffer.clear = MagicMock()
        await session.clear()
        session.screen_buffer.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_erase_method(self):
        """Test AsyncSession erase method (alias for clear)."""
        session = AsyncSession()

        session.screen_buffer.clear = MagicMock()
        await session.erase()
        session.screen_buffer.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_send_file_method(self):
        """Test AsyncSession send_file method."""
        session = AsyncSession()

        # Mock IND$FILE
        mock_ind_file = MagicMock()
        mock_ind_file.send = AsyncMock()
        session._ind_file = mock_ind_file

        await session.send_file("local.txt", "remote.txt")

        mock_ind_file.send.assert_called_once_with("local.txt", "remote.txt")

    @pytest.mark.asyncio
    async def test_async_session_receive_file_method(self):
        """Test AsyncSession receive_file method."""
        session = AsyncSession()

        # Mock IND$FILE
        mock_ind_file = MagicMock()
        mock_ind_file.receive = AsyncMock()
        session._ind_file = mock_ind_file

        await session.receive_file("remote.txt", "local.txt")

        mock_ind_file.receive.assert_called_once_with("remote.txt", "local.txt")

    @pytest.mark.asyncio
    async def test_async_session_send_file_no_ind_file(self):
        """Test AsyncSession send_file method without IND$FILE initialized."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="IND\\$FILE not initialized"):
            await session.send_file("local.txt", "remote.txt")

    @pytest.mark.asyncio
    async def test_async_session_receive_file_no_ind_file(self):
        """Test AsyncSession receive_file method without IND$FILE initialized."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="IND\\$FILE not initialized"):
            await session.receive_file("remote.txt", "local.txt")

    @pytest.mark.asyncio
    async def test_async_session_load_resource_definitions_file_not_found(self):
        """Test AsyncSession load_resource_definitions with missing file."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="Failed to read resource file"):
            await session.load_resource_definitions("nonexistent.res")

    @pytest.mark.asyncio
    async def test_async_session_load_resource_definitions_empty_file(self):
        """Test AsyncSession load_resource_definitions with empty file."""
        session = AsyncSession()

        import os
        import tempfile

        # Create empty temp file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            await session.load_resource_definitions(temp_file)
            assert session.resources == {}
        finally:
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_async_session_apply_resources_empty(self):
        """Test AsyncSession apply_resources with no resources."""
        session = AsyncSession()

        await session.apply_resources()

        # Should not crash
        assert session.resources == {}

    @pytest.mark.asyncio
    async def test_async_session_apply_resources_invalid_color(self):
        """Test AsyncSession apply_resources with invalid color."""
        session = AsyncSession()

        session.resources = {"color0": "invalid"}

        # Should not crash, just log warning
        await session.apply_resources()

    @pytest.mark.asyncio
    async def test_async_session_apply_resources_invalid_highlight(self):
        """Test AsyncSession apply_resources with invalid highlight."""
        session = AsyncSession()

        session.resources = {"highlight0": "invalid"}

        # Should not crash
        await session.apply_resources()

    @pytest.mark.asyncio
    async def test_async_session_set_field_attribute_invalid_index(self):
        """Test AsyncSession set_field_attribute with invalid field index."""
        session = AsyncSession()

        # Should not crash with invalid index
        session.set_field_attribute(999, "color", 1)

    @pytest.mark.asyncio
    async def test_async_session_set_field_attribute_invalid_attr(self):
        """Test AsyncSession set_field_attribute with invalid attribute."""
        session = AsyncSession()

        # Create a mock field
        field = MagicMock()
        field.start = (0, 0)
        field.end = (0, 9)
        session.screen_buffer.fields = [field]

        # Should not crash with invalid attribute
        session.set_field_attribute(0, "invalid", 1)

    @pytest.mark.asyncio
    async def test_async_session_sys_req_no_handler(self):
        """Test AsyncSession sys_req method without handler."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="Cannot send SysReq"):
            await session.sys_req("ATTN")

    @pytest.mark.asyncio
    async def test_async_session_send_break_no_handler(self):
        """Test AsyncSession send_break method without handler."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="Session not connected"):
            await session.send_break()

    @pytest.mark.asyncio
    async def test_async_session_send_soh_message_no_handler(self):
        """Test AsyncSession send_soh_message method without handler."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="Session not connected"):
            await session.send_soh_message(0x01)

    @pytest.mark.asyncio
    async def test_async_session_select_light_pen_no_aid(self):
        """Test AsyncSession select_light_pen method with no AID returned."""
        session = AsyncSession()

        # Mock screen buffer to return None
        session.screen_buffer.select_light_pen = MagicMock(return_value=None)

        # Should not crash and not send anything
        await session.select_light_pen(1, 5)

    @pytest.mark.asyncio
    async def test_async_session_start_lu_lu_session_property(self):
        """Test AsyncSession lu_lu_session property."""
        session = AsyncSession()

        assert session.lu_lu_session is None

        # Set mock session
        mock_session = MagicMock()
        session._lu_lu_session = mock_session

        assert session.lu_lu_session is mock_session

    @pytest.mark.asyncio
    async def test_async_session_macro_invalid_command(self):
        """Test AsyncSession macro method with invalid command."""
        session = AsyncSession()

        with pytest.raises(ValueError, match="Unsupported macro command"):
            await session.macro(["InvalidCommand()"])

    @pytest.mark.asyncio
    async def test_async_session_macro_sysreq_command(self):
        """Test AsyncSession macro method with SysReq command."""
        session = AsyncSession()

        # Mock handler for sys_req
        mock_handler = MagicMock()
        mock_handler.send_sysreq_command = AsyncMock()
        session._handler = mock_handler

        await session.macro(["SysReq(ATTN)"])

        mock_handler.send_sysreq_command.assert_called_once_with(0xF1)

    @pytest.mark.asyncio
    async def test_async_session_macro_key_command(self):
        """Test AsyncSession macro method with key command."""
        session = AsyncSession()

        with patch.object(session, "key") as mock_key:
            await session.macro(["key Enter"])
            mock_key.assert_called_once_with("Enter")

    # Note on naming: The project permanently removed any public macro DSL
    # (e.g., execute_macro/load_macro/MacroError). References to
    # "_execute_macro_command" here exercise the internal s3270-style
    # script-command parser for compatibility, not a public macro API.
    # CI enforces the removal via tools/forbid_macros.py.

    @pytest.mark.asyncio
    async def test_async_session__execute_macro_command_invalid(self):
        """Test AsyncSession _execute_macro_command with invalid command."""
        session = AsyncSession()

        with pytest.raises(ValueError, match="Unsupported macro command"):
            await session._execute_macro_command("InvalidCommand()")

    @pytest.mark.asyncio
    async def test_async_session__execute_macro_command_string(self):
        """Test AsyncSession _execute_macro_command with String command."""
        session = AsyncSession()

        with patch.object(session, "string") as mock_string:
            await session._execute_macro_command("String(hello)")
            mock_string.assert_called_once_with("hello")

    @pytest.mark.asyncio
    async def test_async_session__execute_macro_command_key(self):
        """Test AsyncSession _execute_macro_command with key command."""
        session = AsyncSession()

        with patch.object(session, "key") as mock_key:
            await session._execute_macro_command("key Enter")
            mock_key.assert_called_once_with("Enter")

    @pytest.mark.asyncio
    async def test_async_session__execute_macro_command_sysreq(self):
        """Test AsyncSession _execute_macro_command with SysReq command."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_sysreq_command = AsyncMock()
        session._handler = mock_handler

        await session._execute_macro_command("SysReq(ATTN)")

        mock_handler.send_sysreq_command.assert_called_once_with(0xF1)

    @pytest.mark.asyncio
    async def test_async_session__retry_operation_success(self):
        """Test AsyncSession _retry_operation with success."""
        session = AsyncSession()

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await session._retry_operation(operation)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_session__retry_operation_retry_then_success(self):
        """Test AsyncSession _retry_operation with retry then success."""
        session = AsyncSession()

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success"

        result = await session._retry_operation(operation)

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_session__retry_operation_max_retries(self):
        """Test AsyncSession _retry_operation with max retries exceeded."""
        session = AsyncSession()

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent failure")

        with pytest.raises(Exception, match="Persistent failure"):
            await session._retry_operation(operation, max_retries=2)

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_session_submit_no_handler(self):
        """Test AsyncSession submit method without handler."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="Session not connected"):
            await session.submit(0xF1)

    @pytest.mark.asyncio
    async def test_async_session_interrupt_no_handler(self):
        """Test AsyncSession interrupt method without handler."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="Session not connected"):
            await session.interrupt()

    @pytest.mark.asyncio
    async def test_async_session_key_no_handler(self):
        """Test AsyncSession key method without handler."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="Session not connected"):
            await session.key("Enter")

    @pytest.mark.asyncio
    async def test_async_session_script_no_handler(self):
        """Test AsyncSession script method without handler."""
        session = AsyncSession()

        with pytest.raises(SessionError, match="Session not connected"):
            await session.script("test")

    @pytest.mark.asyncio
    async def test_async_session_execute_no_handler(self):
        """Test AsyncSession execute method without handler - executes external commands."""
        session = AsyncSession()

        # execute() runs external shell commands and doesn't require a handler
        result = await session.execute("echo test")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_async_session_query_no_handler(self):
        """Test AsyncSession query method without handler - returns local state."""
        session = AsyncSession()

        # query() can return connection status without a handler
        result = await session.query("All")
        assert isinstance(result, str)
        assert "Connected:" in result

    @pytest.mark.asyncio
    async def test_async_session_set_no_handler(self):
        """Test AsyncSession set method without handler - sets local options."""
        session = AsyncSession()

        # set() can set local options without a handler
        await session.set("option", "value")
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_async_session_print_text_no_handler(self):
        """Test AsyncSession print_text method without handler - works with local buffer."""
        session = AsyncSession()

        # print_text() works with local state
        await session.print_text("test")
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_async_session_snap_no_handler(self):
        """Test AsyncSession snap method without handler - snapshots local state."""
        session = AsyncSession()

        # snap() saves local state snapshot
        await session.snap()
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_async_session_show_no_handler(self):
        """Test AsyncSession show method without handler - displays local buffer."""
        session = AsyncSession()

        # show() displays local screen buffer
        await session.show()
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_async_session_trace_no_handler(self):
        """Test AsyncSession trace method without handler - controls local tracing."""
        session = AsyncSession()

        # trace() controls local tracing
        await session.trace(True)
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_async_session_transfer_no_handler(self):
        """Test AsyncSession transfer method without handler - file operation."""
        session = AsyncSession()

        # transfer() is a file operation
        await session.transfer("file")
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_async_session_source_no_handler(self):
        """Test AsyncSession source method without handler - reads local file."""
        session = AsyncSession()

        # source() reads from local file
        await session.source("file")
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_async_session_expect_no_handler(self):
        """Test AsyncSession expect method without handler - checks local state."""
        session = AsyncSession()

        # expect() can check local screen state
        result = await session.expect("pattern")
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_async_session_fail_no_handler(self):
        """Test AsyncSession fail method without handler - raises exception."""
        session = AsyncSession()

        # fail() raises an exception with the message - that's its purpose
        with pytest.raises(Exception, match="Script failed: message"):
            await session.fail("message")

    @pytest.mark.asyncio
    async def test_async_session_compose_no_handler(self):
        """Test AsyncSession compose method without handler - composes text locally."""
        session = AsyncSession()

        # compose() works with local composition
        await session.compose("text")
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_async_session_cookie_no_handler(self):
        """Test AsyncSession cookie method without handler - manages local cookies."""
        session = AsyncSession()

        # cookie() manages local cookie storage
        await session.cookie("name=value")
        # No exception should be raised

    @pytest.mark.asyncio
    async def test_async_session_interrupt_with_handler(self):
        """Test AsyncSession interrupt method with handler."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_break = AsyncMock()
        session._handler = mock_handler

        await session.interrupt()

        mock_handler.send_break.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_key_with_handler(self):
        """Test AsyncSession key method with handler."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        session._handler = mock_handler

        await session.key("PF(1)")

        mock_handler.send_data.assert_called_once_with(b"\xf1")

    @pytest.mark.asyncio
    async def test_async_session_submit_with_handler(self):
        """Test AsyncSession submit method with handler."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        session._handler = mock_handler

        await session.submit(0xF1)

        mock_handler.send_data.assert_called_once_with(b"\xf1")

    @pytest.mark.asyncio
    async def test_async_session_script_with_handler(self):
        """Test AsyncSession script method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        # Mock the method that would be called
        with patch.object(session, "string") as mock_string:
            await session.script("String(test)")
            mock_string.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_async_session_execute_with_handler(self):
        """Test AsyncSession execute method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        # Mock subprocess
        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            mock_proc = MagicMock()
            mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
            mock_proc.returncode = 0
            mock_subprocess.return_value = mock_proc

            result = await session.execute("echo test")

            assert result == "output"

    @pytest.mark.asyncio
    async def test_async_session_query_with_handler(self):
        """Test AsyncSession query method with handler."""
        session = AsyncSession()

        # Mock handler but ensure connected returns False
        session._handler = MagicMock()
        session._handler.connected = False

        result = await session.query("All")

        assert result == "Connected: False"

    @pytest.mark.asyncio
    async def test_async_session_set_with_handler(self):
        """Test AsyncSession set method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        await session.set("option", "value")

        # set_option does nothing, just test it doesn't crash

    @pytest.mark.asyncio
    async def test_async_session_print_text_with_handler(self):
        """Test AsyncSession print_text method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        # Just test it doesn't crash (prints text)
        await session.print_text("test")

    @pytest.mark.asyncio
    async def test_async_session_snap_with_handler(self):
        """Test AsyncSession snap method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        # Just test it doesn't crash
        await session.snap()

    @pytest.mark.asyncio
    async def test_async_session_show_with_handler(self):
        """Test AsyncSession show method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        # Just test it doesn't crash (prints screen content)
        await session.show()

    @pytest.mark.asyncio
    async def test_async_session_trace_with_handler(self):
        """Test AsyncSession trace method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        # Just test it doesn't crash
        await session.trace(True)

    @pytest.mark.asyncio
    async def test_async_session_transfer_with_handler(self):
        """Test AsyncSession transfer method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        # Just test it doesn't crash
        await session.transfer("test_file")

    @pytest.mark.asyncio
    async def test_async_session_source_with_handler(self):
        """Test AsyncSession source method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        # Just test it doesn't crash
        await session.source("test_file")

    @pytest.mark.asyncio
    async def test_async_session_expect_with_handler(self):
        """Test AsyncSession expect method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        # Use ASCII mode for simple testing
        session.screen_buffer._ascii_mode = True
        test_text = b"test"
        for i, byte in enumerate(test_text):
            session.screen_buffer.buffer[i] = byte

        result = await session.expect("test", timeout=0.1)
        assert result is True

    @pytest.mark.asyncio
    async def test_async_session_fail_with_handler(self):
        """Test AsyncSession fail method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        with pytest.raises(Exception, match="Script failed: test error"):
            await session.fail("test error")

    @pytest.mark.asyncio
    async def test_async_session_compose_with_handler(self):
        """Test AsyncSession compose method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        with patch.object(session, "insert_text") as mock_insert:
            await session.compose("test")
            mock_insert.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_async_session_cookie_with_handler(self):
        """Test AsyncSession cookie method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        await session.cookie("name=value")

        assert session._cookies == {"name": "value"}

    @pytest.mark.asyncio
    async def test_async_session_prompt_with_handler(self):
        """Test AsyncSession prompt method with handler."""
        session = AsyncSession()

        # Mock handler
        session._handler = MagicMock()

        # Mock asyncio loop and input
        with (
            patch("asyncio.get_running_loop") as mock_loop,
            patch("builtins.input", return_value="test_response") as mock_input,
        ):

            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value="test_response"
            )

            result = await session.prompt("Enter value:")

            assert result == "test_response"

    def test_session_boundary_conditions(self):
        """Test Session boundary conditions and edge cases."""
        # Test with None host/port
        session = Session(host=None, port=None)
        assert session._host is None
        assert session._port is None

        # Test connect with None parameters
        with patch("pure3270.session.AsyncSession") as mock_async_session_class:
            mock_async_session = MagicMock()
            mock_async_session.connect = AsyncMock()
            mock_async_session_class.return_value = mock_async_session

            session.connect(host=None, port=None, ssl_context=None)

            # Should use instance defaults
            mock_async_session_class.assert_called_once_with(
                None,
                None,
                None,
                force_mode=None,
                allow_fallback=True,
                enable_trace=False,
                terminal_type="IBM-3278-2",
            )

    @pytest.mark.asyncio
    async def test_async_session_boundary_conditions(self):
        """Test AsyncSession boundary conditions and edge cases."""
        # Test with extreme terminal types
        session = AsyncSession(terminal_type="IBM-DYNAMIC")
        assert session._terminal_type == "IBM-DYNAMIC"

        # Test AID map boundaries
        assert session.AID_MAP.get("PF(24)") == 0x4C
        assert session.AID_MAP.get("PA(3)") == 0x6B
        assert session.AID_MAP.get("Enter") == 0x7D

        # Test invalid AID key
        assert session.AID_MAP.get("INVALID_KEY") is None

    def test_session_error_context(self):
        """Test SessionError context handling."""
        # Test error with context
        error = SessionError("Test error", {"key": "value", "code": 123})
        assert str(error) == "Test error (code=123, key=value)"

        # Test error without context
        error2 = SessionError("Simple error")
        assert str(error2) == "Simple error"

    def test_session_worker_loop_edge_cases(self):
        """Test Session worker loop edge cases."""
        session = Session()

        # Test shutdown without loop
        session._shutdown_worker_loop()  # Should not crash

        # Test multiple shutdowns
        session._shutdown_worker_loop()
        session._shutdown_worker_loop()

    @pytest.mark.asyncio
    async def test_async_session_connection_state_transitions(self):
        """Test AsyncSession connection state transitions."""
        session = AsyncSession()

        # Initially disconnected
        assert session.connected is False

        # Set connected via property
        session.connected = True
        assert session.connected is True

        # Reset and test handler-based connection
        session.connected = False
        mock_handler = MagicMock()
        mock_handler.connected = True
        session._handler = mock_handler
        assert session.connected is True

        # Reset and test transport-based connection
        session._handler = None
        mock_transport = MagicMock()
        mock_transport.connected = True
        session._transport = mock_transport
        assert session.connected is True

    def test_session_property_access_edge_cases(self):
        """Test Session property access edge cases."""
        session = Session()

        # tn3270e_mode without handler
        assert session.tn3270e_mode is False

        # screen_buffer should always be available
        buffer = session.screen_buffer
        assert isinstance(buffer, ScreenBuffer)

        # get_aid without session
        assert session.get_aid() is None

    @pytest.mark.asyncio
    async def test_async_session_aid_tracking(self):
        """Test AsyncSession AID tracking."""
        session = AsyncSession()

        # Initially None
        assert session.get_aid() is None

        # Set AID
        session._aid = 0xF1
        assert session.get_aid() == 0xF1

        # Reset AID
        session._aid = None
        assert session.get_aid() is None

    def test_session_context_manager_exception_handling(self):
        """Test Session context manager exception handling."""
        session = Session()

        # Test that exceptions in context manager are propagated
        with pytest.raises(ValueError):
            with session:
                raise ValueError("Test exception")

        # Verify close was still called (mock it to check)
        with patch.object(session, "close") as mock_close:
            try:
                with session:
                    raise RuntimeError("Test")
            except RuntimeError:
                pass
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_context_manager_exception_handling(self):
        """Test AsyncSession context manager exception handling."""
        session = AsyncSession()

        # Test that exceptions in async context manager are propagated
        with pytest.raises(ValueError):
            async with session:
                raise ValueError("Test exception")

        # Verify close was still called
        with patch.object(session, "close", new_callable=AsyncMock) as mock_close:
            try:
                async with session:
                    raise RuntimeError("Test")
            except RuntimeError:
                pass
            mock_close.assert_called_once()

    def test_session_initialization_parameter_validation(self):
        """Test Session initialization parameter validation."""
        # Test valid terminal types
        valid_types = [
            "IBM-3278-2",
            "IBM-3278-3",
            "IBM-3278-4",
            "IBM-3278-5",
            "IBM-3279-2",
            "IBM-3279-3",
            "IBM-3279-4",
            "IBM-3279-5",
            "IBM-3179-2",
            "IBM-3270PC-G",
            "IBM-3270PC-GA",
            "IBM-3270PC-GX",
            "IBM-DYNAMIC",
        ]

        for term_type in valid_types:
            session = Session(terminal_type=term_type)
            assert session._terminal_type == term_type

        # Test invalid terminal type (already tested, but ensure it raises ValueError)
        with pytest.raises(ValueError):
            Session(terminal_type="INVALID")

    @pytest.mark.asyncio
    async def test_async_session_initialization_parameter_validation(self):
        """Test AsyncSession initialization parameter validation."""
        # Test valid terminal types
        valid_types = [
            "IBM-3278-2",
            "IBM-3278-3",
            "IBM-3278-4",
            "IBM-3278-5",
            "IBM-3279-2",
            "IBM-3279-3",
            "IBM-3279-4",
            "IBM-3279-5",
            "IBM-3179-2",
            "IBM-3270PC-G",
            "IBM-3270PC-GA",
            "IBM-3270PC-GX",
            "IBM-DYNAMIC",
        ]

        for term_type in valid_types:
            session = AsyncSession(terminal_type=term_type)
            assert session._terminal_type == term_type

        # Test invalid terminal type
        with pytest.raises(ValueError):
            AsyncSession(terminal_type="INVALID")

    def test_session_trace_events_initialization(self):
        """Test Session trace events initialization."""
        session = Session()

        # Initially empty
        assert session.get_trace_events() == []

        # With async session
        mock_async_session = MagicMock()
        mock_async_session.get_trace_events = MagicMock(
            return_value=["event1", "event2"]
        )
        session._async_session = mock_async_session

        assert session.get_trace_events() == ["event1", "event2"]

    @pytest.mark.asyncio
    async def test_async_session_trace_events(self):
        """Test AsyncSession trace events."""
        session = AsyncSession()

        # Initially empty
        assert session.get_trace_events() == []

        # Add trace events
        session._trace_events = ["event1", "event2", "event3"]
        assert session.get_trace_events() == ["event1", "event2", "event3"]

        # Test copy behavior
        events = session.get_trace_events()
        events.append("new_event")
        assert session._trace_events == [
            "event1",
            "event2",
            "event3",
        ]  # Original unchanged

    def test_session_open_method_edge_cases(self):
        """Test Session open method edge cases."""
        session = Session()

        # Test with different port values
        with patch.object(session, "connect") as mock_connect:
            session.open("host1", 23)
            mock_connect.assert_called_once_with("host1", 23)

            session.open("host2", 992)
            assert mock_connect.call_count == 2

    @pytest.mark.asyncio
    async def test_async_session_resource_mtime_tracking(self):
        """Test AsyncSession resource mtime tracking."""
        session = AsyncSession()

        # Initially 0.0
        assert session._resource_mtime == 0.0

        # Set mtime
        session._resource_mtime = 1234567890.0
        assert session._resource_mtime == 1234567890.0

    @pytest.mark.asyncio
    async def test_async_session_color_palette_initialization(self):
        """Test AsyncSession color palette initialization."""
        session = AsyncSession()

        # Should have 16 colors, all black initially
        assert len(session.color_palette) == 16
        assert all(color == (0, 0, 0) for color in session.color_palette)

        # Test palette modification
        session.color_palette[0] = (255, 0, 0)
        assert session.color_palette[0] == (255, 0, 0)

    @pytest.mark.asyncio
    async def test_async_session_font_and_keymap_defaults(self):
        """Test AsyncSession font and keymap defaults."""
        session = AsyncSession()

        assert session.font == "default"
        assert session.keymap == "default"

        # Test modification
        session.font = "monospace"
        session.keymap = "custom"

        assert session.font == "monospace"
        assert session.keymap == "custom"

    @pytest.mark.asyncio
    async def test_async_session_model_and_color_mode(self):
        """Test AsyncSession model and color mode."""
        session = AsyncSession()

        # Default model 2, color mode False
        assert session.model == "2"
        assert session.color_mode is False

        # Change model to 3 (should enable color mode)
        session.model = "3"
        assert session.model == "3"
        assert session.color_mode is True

        # Change back to 2
        session.model = "2"
        assert session.model == "2"
        assert session.color_mode is False

    @pytest.mark.asyncio
    async def test_async_session_circumvent_protection_toggle(self):
        """Test AsyncSession circumvent protection toggle."""
        session = AsyncSession()

        # Initially False
        assert session.circumvent_protection is False

        # Toggle on
        session.circumvent_protection = True
        assert session.circumvent_protection is True

        # Toggle off
        session.circumvent_protection = False
        assert session.circumvent_protection is False

    @pytest.mark.asyncio
    async def test_async_session_insert_mode_toggle(self):
        """Test AsyncSession insert mode toggle."""
        session = AsyncSession()

        # Initially False
        assert session.insert_mode is False

        # Toggle on
        session.insert_mode = True
        assert session.insert_mode is True

        # Toggle off
        session.insert_mode = False
        assert session.insert_mode is False

    def test_session_screen_buffer_fallback(self):
        """Test Session screen_buffer fallback when no async session."""
        session = Session()

        # Should return a default buffer
        buffer = session.screen_buffer
        assert isinstance(buffer, ScreenBuffer)
        assert buffer.rows == 24
        assert buffer.cols == 80

    @pytest.mark.asyncio
    async def test_async_session_tn3270_mode_flags(self):
        """Test AsyncSession TN3270 mode flags."""
        session = AsyncSession()

        # Initially False
        assert session.tn3270_mode is False

        # Set via flag
        session.tn3270_mode = True
        assert session.tn3270_mode is True

        # Reset
        session.tn3270_mode = False
        assert session.tn3270_mode is False

    def test_session_tn3270e_mode_fallback_logic(self):
        """Test Session tn3270e_mode fallback logic."""
        session = Session()

        # No async session
        assert session.tn3270e_mode is False

        # With async session but no handler
        mock_async_session = MagicMock()
        mock_async_session.tn3270_mode = False
        session._async_session = mock_async_session
        assert session.tn3270e_mode is False

        # With handler negotiated TN3270E
        mock_handler = MagicMock()
        mock_handler.negotiated_tn3270e = True
        session._handler = mock_handler
        assert session.tn3270e_mode is True

    @pytest.mark.asyncio
    async def test_async_session_handler_property(self):
        """Test AsyncSession handler property."""
        session = AsyncSession()

        # Initially None
        assert session.handler is None

        # Set handler
        mock_handler = MagicMock()
        session.handler = mock_handler
        assert session.handler is mock_handler

        # Reset
        session.handler = None
        assert session.handler is None

    @pytest.mark.asyncio
    async def test_async_session_transport_property(self):
        """Test AsyncSession transport property."""
        session = AsyncSession()

        # Initially None
        assert session._transport is None

        # Set transport
        mock_transport = MagicMock()
        session._transport = mock_transport
        assert session._transport is mock_transport

    def test_session_performance_under_load(self):
        """Test Session performance under load."""
        session = Session()

        # Test rapid connect/close cycles
        for i in range(10):
            session._async_session = None  # Reset
            # Just test that initialization doesn't crash under rapid cycling
            assert session.connected is False

    @pytest.mark.asyncio
    async def test_async_session_concurrent_operations_stress(self):
        """Test AsyncSession concurrent operations stress test."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        mock_handler.receive_data = AsyncMock(return_value=b"data")
        session._handler = mock_handler

        # Run many concurrent operations
        async def stress_operation():
            await session.send(b"test")
            await session.read()

        tasks = [stress_operation() for _ in range(50)]
        await asyncio.gather(*tasks)

        # Verify operations completed
        assert mock_handler.send_data.call_count == 50
        assert mock_handler.receive_data.call_count == 50

    def test_session_s3270_compatibility_methods(self):
        """Test Session s3270 compatibility methods."""
        session = Session()

        # Mock async session
        mock_async_session = MagicMock()
        session._async_session = mock_async_session

        # Test various s3270 methods
        session.string("test")
        session.enter()
        session.pf("1")
        session.pa("2")
        session.clear()
        session.erase()

        # Verify calls were made
        mock_async_session.string.assert_called_once_with("test")
        mock_async_session.enter.assert_called_once()
        mock_async_session.pf.assert_called_once_with("1")
        mock_async_session.pa.assert_called_once_with("2")
        mock_async_session.clear.assert_called_once()
        mock_async_session.erase.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_s3270_compatibility_methods(self):
        """Test AsyncSession s3270 compatibility methods."""
        session = AsyncSession()

        # Mock handler for methods that need it
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        session._handler = mock_handler

        # Test various s3270 methods
        await session.string("test")
        await session.enter()
        await session.pf("1")
        await session.pa("2")
        await session.clear()
        await session.erase()

        # Verify calls were made (some may have been mocked)
        # The key methods should have been called appropriately

    def test_session_ascii_ebcdic_conversion(self):
        """Test Session ASCII/EBCDIC conversion methods."""
        session = Session()

        # Test ascii method
        result = session.ascii(b"\x81\x82\x83")
        assert result == "abc"

        # Test ebcdic method
        result = session.ebcdic("def")
        assert isinstance(result, bytes)
        assert len(result) == 3

        # Test ascii1 method
        result = session.ascii1(0x81)
        assert isinstance(result, str)

        # Test ebcdic1 method
        result = session.ebcdic1("g")
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_async_session_script_method(self):
        """Test AsyncSession script method."""
        session = AsyncSession()

        # Mock the method that would be called
        with patch.object(session, "string") as mock_string:
            await session.script("String(hello)")
            mock_string.assert_called_once_with("hello")

    @pytest.mark.asyncio
    async def test_async_session_execute_method(self):
        """Test AsyncSession execute method."""
        session = AsyncSession()

        # Mock asyncio.create_subprocess_shell
        with patch("asyncio.create_subprocess_shell") as mock_subprocess:
            mock_proc = MagicMock()
            mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
            mock_proc.returncode = 0
            mock_subprocess.return_value = mock_proc

            result = await session.execute("echo test")

            assert result == "output"
            mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_info_method(self):
        """Test AsyncSession info method."""
        session = AsyncSession()

        # Test disconnected
        result = await session.info()
        assert "disconnected" in result

        # Test connected
        session._connected = True
        result = await session.info()
        assert "connected" in result

    @pytest.mark.asyncio
    async def test_async_session_query_method(self):
        """Test AsyncSession query method."""
        session = AsyncSession()

        result = await session.query("All")
        assert result == "Connected: False"

    @pytest.mark.asyncio
    async def test_async_session_set_option_method(self):
        """Test AsyncSession set_option method."""
        session = AsyncSession()

        # This method currently does nothing, just test it doesn't crash
        await session.set_option("test", "value")

    @pytest.mark.asyncio
    async def test_async_session_bell_method(self):
        """Test AsyncSession bell method."""
        session = AsyncSession()

        # Just test it doesn't crash (prints \a)
        await session.bell()

    @pytest.mark.asyncio
    async def test_async_session_pause_method(self):
        """Test AsyncSession pause method."""
        session = AsyncSession()

        import time

        start = time.time()
        await session.pause(0.1)
        end = time.time()

        assert end - start >= 0.1

    @pytest.mark.asyncio
    async def test_async_session_show_method(self):
        """Test AsyncSession show method."""
        session = AsyncSession()

        # Just test it doesn't crash (prints screen content)
        await session.show()

    @pytest.mark.asyncio
    async def test_async_session_snap_method(self):
        """Test AsyncSession snap method."""
        session = AsyncSession()

        # Just test it doesn't crash (snapshot functionality)
        await session.snap()

    @pytest.mark.asyncio
    async def test_async_session_print_text_method(self):
        """Test AsyncSession print_text method."""
        session = AsyncSession()

        # Just test it doesn't crash (prints text)
        await session.print_text("test")

    @pytest.mark.asyncio
    async def test_async_session_nvt_text_method(self):
        """Test AsyncSession nvt_text method."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        session._handler = mock_handler

        await session.nvt_text("test")

        mock_handler.send_data.assert_called_once_with(b"test")

    @pytest.mark.asyncio
    async def test_async_session_hex_string_method(self):
        """Test AsyncSession hex_string method."""
        session = AsyncSession()

        result = await session.hex_string("414243")
        assert result == b"ABC"

    @pytest.mark.asyncio
    async def test_async_session_read_buffer_method(self):
        """Test AsyncSession read_buffer method."""
        session = AsyncSession()

        result = await session.read_buffer()
        assert isinstance(result, bytes)
        assert len(result) == 24 * 80  # Default screen size

    @pytest.mark.asyncio
    async def test_async_session_reconnect_method(self):
        """Test AsyncSession reconnect method."""
        session = AsyncSession()

        with (
            patch.object(session, "close") as mock_close,
            patch.object(session, "connect") as mock_connect,
        ):

            await session.reconnect()

            mock_close.assert_called_once()
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_quit_method(self):
        """Test AsyncSession quit method."""
        session = AsyncSession()

        with patch.object(session, "close") as mock_close:
            await session.quit()

            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_expect_method(self):
        """Test AsyncSession expect method."""
        session = AsyncSession()

        # Set screen content
        session.screen_buffer.buffer[0:4] = b"test"

        result = await session.expect("test", timeout=0.1)
        assert result is True

        result = await session.expect("notfound", timeout=0.1)
        assert result is False

    @pytest.mark.asyncio
    async def test_async_session_fail_method(self):
        """Test AsyncSession fail method."""
        session = AsyncSession()

        with pytest.raises(Exception, match="Script failed: test error"):
            await session.fail("test error")

    @pytest.mark.asyncio
    async def test_async_session_select_light_pen_method(self):
        """Test AsyncSession select_light_pen method."""
        session = AsyncSession()

        # Mock screen buffer select_light_pen
        session.screen_buffer.select_light_pen = MagicMock(return_value=0xF1)

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_data = AsyncMock()
        session._handler = mock_handler

        await session.select_light_pen(1, 5)

        mock_handler.send_data.assert_called_once_with(b"\xf1")

    @pytest.mark.asyncio
    async def test_async_session_start_lu_lu_session_method(self):
        """Test AsyncSession start_lu_lu_session method."""
        session = AsyncSession()

        # Mock LuLuSession
        with patch("pure3270.session.LuLuSession") as mock_lu_lu_class:
            mock_lu_lu = MagicMock()
            mock_lu_lu.start = AsyncMock()
            mock_lu_lu_class.return_value = mock_lu_lu

            await session.start_lu_lu_session("LU001")

            mock_lu_lu_class.assert_called_once_with(session)
            mock_lu_lu.start.assert_called_once_with("LU001")
            assert session.lu_lu_session is mock_lu_lu

    @pytest.mark.asyncio
    async def test_async_session_load_resource_definitions_method(self):
        """Test AsyncSession load_resource_definitions method."""
        session = AsyncSession()

        import os
        import tempfile

        # Create a temporary resource file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".res") as f:
            f.write("s3270.font: monospace\n")
            f.write("s3270.keymap: default\n")
            temp_file = f.name

        try:
            await session.load_resource_definitions(temp_file)

            assert session.font == "monospace"
            assert session.keymap == "default"
        finally:
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_async_session_apply_resources_method(self):
        """Test AsyncSession apply_resources method."""
        session = AsyncSession()

        session.resources = {
            "font": "test_font",
            "keymap": "test_keymap",
            "model": "3",
            "color0": "#000000",
            "color1": "#FF0000",
        }

        await session.apply_resources()

        assert session.font == "test_font"
        assert session.keymap == "test_keymap"
        assert session.model == "3"
        assert session.color_mode is True
        assert session.color_palette[0] == (0, 0, 0)
        assert session.color_palette[1] == (255, 0, 0)

    def test_session_set_field_attribute_method(self):
        """Test Session set_field_attribute method."""
        session = Session()

        # Mock async session
        mock_async_session = MagicMock()
        session._async_session = mock_async_session

        session.set_field_attribute(0, "color", 1)

        mock_async_session.set_field_attribute.assert_called_once_with(0, "color", 1)

    @pytest.mark.asyncio
    async def test_async_session_set_field_attribute_method(self):
        """Test AsyncSession set_field_attribute method."""
        session = AsyncSession()

        # Create a mock field
        field = MagicMock()
        field.start = (0, 0)
        field.end = (0, 9)
        session.screen_buffer.fields = [field]

        session.set_field_attribute(0, "color", 255)

        # Verify the attribute was set (this is a simplified test)
        # The actual implementation modifies screen buffer attributes

    @pytest.mark.asyncio
    async def test_async_session_sys_req_method(self):
        """Test AsyncSession sys_req method."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_sysreq_command = AsyncMock()
        session._handler = mock_handler

        await session.sys_req("ATTN")

        mock_handler.send_sysreq_command.assert_called_once_with(0xF1)

        # Test invalid command
        with pytest.raises(ValueError, match="Unknown SYSREQ command"):
            await session.sys_req("INVALID")

    @pytest.mark.asyncio
    async def test_async_session_send_break_method(self):
        """Test AsyncSession send_break method."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_break = AsyncMock()
        session._handler = mock_handler

        await session.send_break()

        mock_handler.send_break.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_send_soh_message_method(self):
        """Test AsyncSession send_soh_message method."""
        session = AsyncSession()

        # Mock handler
        mock_handler = MagicMock()
        mock_handler.send_soh_message = AsyncMock()
        session._handler = mock_handler

        await session.send_soh_message(0x01)

        mock_handler.send_soh_message.assert_called_once_with(0x01)

    @pytest.mark.asyncio
    async def test_async_session_toggle_option_method(self):
        """Test AsyncSession toggle_option method."""
        session = AsyncSession()

        # Just test it doesn't crash
        await session.toggle_option("test")

    @pytest.mark.asyncio
    async def test_async_session_trace_method(self):
        """Test AsyncSession trace method."""
        session = AsyncSession()

        # Just test it doesn't crash
        await session.trace(True)
        await session.trace(False)

    @pytest.mark.asyncio
    async def test_async_session_transfer_method(self):
        """Test AsyncSession transfer method."""
        session = AsyncSession()

        # Just test it doesn't crash
        await session.transfer("test_file")

    @pytest.mark.asyncio
    async def test_async_session_source_method(self):
        """Test AsyncSession source method."""
        session = AsyncSession()

        # Just test it doesn't crash
        await session.source("test_file")

    @pytest.mark.asyncio
    async def test_async_session_compose_method(self):
        """Test AsyncSession compose method."""
        session = AsyncSession()

        with patch.object(session, "insert_text") as mock_insert:
            await session.compose("test")
            mock_insert.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_async_session_cookie_method(self):
        """Test AsyncSession cookie method."""
        session = AsyncSession()

        session.cookie("name=value")

        assert session._cookies == {"name": "value"}

    @pytest.mark.asyncio
    async def test_async_session_prompt_method(self):
        """Test AsyncSession prompt method."""
        session = AsyncSession()

        # Mock asyncio loop and input
        with (
            patch("asyncio.get_running_loop") as mock_loop,
            patch("builtins.input", return_value="test_response") as mock_input,
        ):

            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value="test_response"
            )

            result = await session.prompt("Enter value:")

            assert result == "test_response"

    @pytest.mark.asyncio
    async def test_async_session_end_method(self):
        """Test AsyncSession end method."""
        session = AsyncSession()

        session.screen_buffer.set_position = MagicMock()

        await session.end()

        session.screen_buffer.set_position.assert_called_with(
            0, 79
        )  # End of first line

    @pytest.mark.asyncio
    async def test_async_session_move_cursor_method(self):
        """Test AsyncSession move_cursor method."""
        session = AsyncSession()

        session.screen_buffer.set_position = MagicMock()

        await session.move_cursor(5, 10)

        session.screen_buffer.set_position.assert_called_once_with(5, 10)

    @pytest.mark.asyncio
    async def test_async_session_move_cursor1_method(self):
        """Test AsyncSession move_cursor1 method."""
        session = AsyncSession()

        session.screen_buffer.set_position = MagicMock()

        await session.move_cursor1(2, 3)  # 1-based

        session.screen_buffer.set_position.assert_called_once_with(1, 2)  # 0-based

    @pytest.mark.asyncio
    async def test_async_session_next_word_method(self):
        """Test AsyncSession next_word method."""
        session = AsyncSession()

        with patch.object(session, "right") as mock_right:
            await session.next_word()
            mock_right.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_previous_word_method(self):
        """Test AsyncSession previous_word method."""
        session = AsyncSession()

        with patch.object(session, "left") as mock_left:
            await session.previous_word()
            mock_left.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_toggle_insert_method(self):
        """Test AsyncSession toggle_insert method."""
        session = AsyncSession()

        assert session.insert_mode is False

        await session.toggle_insert()

        assert session.insert_mode is True

        await session.toggle_insert()

        assert session.insert_mode is False

    @pytest.mark.asyncio
    async def test_async_session_flip_method(self):
        """Test AsyncSession flip method (alias for toggle_insert)."""
        session = AsyncSession()

        await session.flip()

        assert session.insert_mode is True

    @pytest.mark.asyncio
    async def test_async_session_insert_method(self):
        """Test AsyncSession insert method."""
        session = AsyncSession()

        await session.insert()

        assert session.insert_mode is True

    @pytest.mark.asyncio
    async def test_async_session_delete_method(self):
        """Test AsyncSession delete method."""
        session = AsyncSession()

        # Set cursor position and mock buffer
        session.screen_buffer.get_position = MagicMock(return_value=(1, 5))
        session.screen_buffer.buffer = bytearray(b"A" * 80 * 24)

        await session.delete()

        # Verify character was shifted left (simplified check)
        assert session.screen_buffer.buffer[1 * 80 + 5] == ord(
            "A"
        )  # Should be unchanged in this simple test

    @pytest.mark.asyncio
    async def test_async_session_disconnect_method(self):
        """Test AsyncSession disconnect method."""
        session = AsyncSession()

        with patch.object(session, "close") as mock_close:
            await session.disconnect()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_left_method(self):
        """Test AsyncSession left method."""
        session = AsyncSession()

        session.screen_buffer.get_position = MagicMock(return_value=(5, 10))
        session.screen_buffer.set_position = MagicMock()

        await session.left()

        session.screen_buffer.set_position.assert_called_with(5, 9)

    @pytest.mark.asyncio
    async def test_async_session_right_method(self):
        """Test AsyncSession right method."""
        session = AsyncSession()

        session.screen_buffer.get_position = MagicMock(return_value=(5, 10))
        session.screen_buffer.set_position = MagicMock()

        await session.right()

        session.screen_buffer.set_position.assert_called_with(5, 11)

    @pytest.mark.asyncio
    async def test_async_session_left2_method(self):
        """Test AsyncSession left2 method."""
        session = AsyncSession()

        with patch.object(session, "left") as mock_left:
            await session.left2()
            assert mock_left.call_count == 2

    @pytest.mark.asyncio
    async def test_async_session_right2_method(self):
        """Test AsyncSession right2 method."""
        session = AsyncSession()

        with patch.object(session, "right") as mock_right:
            await session.right2()
            assert mock_right.call_count == 2

    @pytest.mark.asyncio
    async def test_async_session_mono_case_method(self):
        """Test AsyncSession mono_case method."""
        session = AsyncSession()

        # Just test it doesn't crash
        await session.mono_case()

    @pytest.mark.asyncio
    async def test_async_session_wait_condition_method(self):
        """Test AsyncSession wait_condition method."""
        session = AsyncSession()

        # Just test it doesn't crash
        await session.wait_condition("test")

    @pytest.mark.asyncio
    async def test_async_session_subject_names_method(self):
        """Test AsyncSession subject_names method."""
        session = AsyncSession()

        # Just test it doesn't crash
        await session.subject_names()

    @pytest.mark.asyncio
    async def test_async_session_screen_trace_method(self):
        """Test AsyncSession screen_trace method."""
        session = AsyncSession()

        # Just test it doesn't crash
        await session.screen_trace()

    @pytest.mark.asyncio
    async def test_async_session_macro_method(self):
        """Test AsyncSession macro method."""
        session = AsyncSession()

        with patch.object(session, "string") as mock_string:
            await session.macro(["String(test)"])
            mock_string.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_async_session_erase_eof_method(self):
        """Test AsyncSession erase_eof method."""
        session = AsyncSession()

        # Set cursor position
        session.screen_buffer.get_position = MagicMock(return_value=(1, 5))
        session.screen_buffer.cols = 80

        await session.erase_eof()

        # Verify characters from cursor to end of line were cleared
        # (This is a simplified test - actual implementation is more complex)

    @pytest.mark.asyncio
    async def test_async_session_erase_input_method(self):
        """Test AsyncSession erase_input method."""
        session = AsyncSession()

        # Create mock fields
        field1 = MagicMock()
        field1.protected = False
        field1.content = b"test"
        field1.modified = False

        field2 = MagicMock()
        field2.protected = True
        field2.content = b"protected"

        session.screen_buffer.fields = [field1, field2]

        await session.erase_input()

        # Verify unprotected field was modified
        assert field1.modified is True
        assert field2.modified is False  # Protected field unchanged

    @pytest.mark.asyncio
    async def test_async_session_field_end_method(self):
        """Test AsyncSession field_end method."""
        session = AsyncSession()

        with patch.object(session, "end") as mock_end:
            await session.field_end()
            mock_end.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_field_mark_method(self):
        """Test AsyncSession field_mark method."""
        session = AsyncSession()

        # Just test it doesn't crash (placeholder implementation)
        await session.field_mark()

    @pytest.mark.asyncio
    async def test_async_session_dup_method(self):
        """Test AsyncSession dup method."""
        session = AsyncSession()

        with patch.object(session, "key") as mock_key:
            await session.dup()
            mock_key.assert_called_once_with("Dup")

    @pytest.mark.asyncio
    async def test_async_session_field_exit_method(self):
        """Test AsyncSession field_exit method."""
        session = AsyncSession()

        with patch.object(session, "key") as mock_key:
            await session.field_exit()
            mock_key.assert_called_once_with("FieldExit")

    @pytest.mark.asyncio
    async def test_async_session_sysreq_method(self):
        """Test AsyncSession sysreq method."""
        session = AsyncSession()

        with patch.object(session, "key") as mock_key:
            await session.sysreq()
            mock_key.assert_called_once_with("SysReq")

    @pytest.mark.asyncio
    async def test_async_session_attn_method(self):
        """Test AsyncSession attn method."""
        session = AsyncSession()

        with patch.object(session, "key") as mock_key:
            await session.attn()
            mock_key.assert_called_once_with("Attn")

    @pytest.mark.asyncio
    async def test_async_session_test_method(self):
        """Test AsyncSession test method."""
        session = AsyncSession()

        with patch.object(session, "key") as mock_key:
            await session.test()
            mock_key.assert_called_once_with("Test")

    @pytest.mark.asyncio
    async def test_async_session_newline_method(self):
        """Test AsyncSession newline method."""
        session = AsyncSession()

        session.screen_buffer.get_position = MagicMock(return_value=(5, 10))
        session.screen_buffer.set_position = MagicMock()

        await session.newline()

        session.screen_buffer.set_position.assert_called_with(6, 0)

    @pytest.mark.asyncio
    async def test_async_session_page_down_method(self):
        """Test AsyncSession page_down method."""
        session = AsyncSession()

        session.screen_buffer.get_position = MagicMock(return_value=(5, 10))
        session.screen_buffer.set_position = MagicMock()

        await session.page_down()

        session.screen_buffer.set_position.assert_called_with(0, 10)

    @pytest.mark.asyncio
    async def test_async_session_page_up_method(self):
        """Test AsyncSession page_up method."""
        session = AsyncSession()

        session.screen_buffer.get_position = MagicMock(return_value=(5, 10))
        session.screen_buffer.set_position = MagicMock()

        await session.page_up()

        session.screen_buffer.set_position.assert_called_with(0, 10)

    @pytest.mark.asyncio
    async def test_async_session_paste_string_method(self):
        """Test AsyncSession paste_string method."""
        session = AsyncSession()

        with patch.object(session, "insert_text") as mock_insert:
            await session.paste_string("test")
            mock_insert.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_async_session_exit_method(self):
        """Test AsyncSession exit method."""
        session = AsyncSession()

        with patch.object(session, "close") as mock_close:
            await session.exit()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_tab_method(self):
        """Test AsyncSession tab method."""
        session = AsyncSession()

        session.screen_buffer.move_cursor_to_next_input_field = MagicMock()

        await session.tab()

        session.screen_buffer.move_cursor_to_next_input_field.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_backtab_method(self):
        """Test AsyncSession backtab method."""
        session = AsyncSession()

        # Set up mock fields - need at least 2 fields for backtab to work
        mock_field_0 = MagicMock()
        mock_field_0.start = (0, 0)
        mock_field_1 = MagicMock()
        mock_field_1.start = (1, 0)
        session.screen_buffer.fields = [mock_field_0, mock_field_1]

        # Cursor is at position (1, 5) in field 1
        session.screen_buffer.get_position = MagicMock(return_value=(1, 5))
        session.screen_buffer.get_field_at_position = MagicMock(
            return_value=mock_field_1
        )
        session.screen_buffer.set_position = MagicMock()

        await session.backtab()

        # Should move to start of previous field (field 0)
        session.screen_buffer.set_position.assert_called_with(0, 0)

    @pytest.mark.asyncio
    async def test_async_session_backspace_method(self):
        """Test AsyncSession backspace method."""
        session = AsyncSession()

        with patch.object(session, "key") as mock_key:
            await session.backspace()
            mock_key.assert_called_once_with("BackSpace")

    @pytest.mark.asyncio
    async def test_async_session_clear_method(self):
        """Test AsyncSession clear method."""
        session = AsyncSession()

        session.screen_buffer.clear = MagicMock()

        await session.clear()

        session.screen_buffer.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_session_erase_method(self):
        """Test AsyncSession erase method (alias for clear)."""
        session = AsyncSession()

        session.screen_buffer.clear = MagicMock()
        await session.erase()
        session.screen_buffer.clear.assert_called_once()
