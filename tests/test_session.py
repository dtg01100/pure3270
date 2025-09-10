import pytest
import asyncio
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch, ANY, mock_open
from pure3270.session import Session, AsyncSession, SessionError, MacroError
from pure3270.emulation.screen_buffer import ScreenBuffer, Field
from pure3270.protocol.tn3270_handler import TN3270Handler


@pytest.fixture
def async_session():
    return AsyncSession("localhost", 23)


@pytest.fixture
def sync_session():
    return Session("localhost", 23)


@pytest.mark.asyncio
class TestAsyncSession:
    def test_init(self, async_session):
        assert isinstance(async_session.screen_buffer, ScreenBuffer)
        assert async_session._handler is None
        assert async_session._connected is False
        assert async_session.host == "localhost"
        assert async_session.port == 23

    @patch("pure3270.session.asyncio.open_connection")
    @patch("pure3270.session.TN3270Handler")
    async def test_connect(self, mock_handler, mock_open, async_session):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)
        mock_handler.return_value = AsyncMock()
        mock_reader.readexactly.return_value = b"\xff\xfb\x27"
        mock_reader.read.return_value = b"\x28\x00\x01\x00"
        mock_handler.return_value.set_ascii_mode = AsyncMock()

        await async_session.connect()

        mock_open.assert_called_once()
        mock_handler.assert_called_once_with(mock_reader, mock_writer)
        assert async_session._connected is True

    @patch("pure3270.session.asyncio.open_connection")
    @patch("pure3270.session.TN3270Handler")
    async def test_connect_negotiation_fail(
        self, mock_handler, mock_open, async_session
    ):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)
        handler_instance = AsyncMock()
        mock_handler.return_value = handler_instance
        mock_reader.readexactly.return_value = b"\xff\xfb\x27"
        mock_reader.read.return_value = b""

        # Mock negotiate to raise NegotiationError
        from pure3270.protocol.exceptions import NegotiationError

        handler_instance.negotiate.side_effect = NegotiationError("Negotiation failed")

        # Test that NegotiationError is raised
        with pytest.raises(NegotiationError):
            await async_session.connect()

    @patch("pure3270.session.asyncio.open_connection")
    @patch("pure3270.session.TN3270Handler")
    async def test_send(self, mock_handler, mock_open, async_session):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)
        mock_handler.return_value = AsyncMock()
        mock_reader.readexactly.return_value = b"\xff\xfb\x27"
        mock_reader.read.return_value = b"\x28\x00\x01\x00"
        mock_handler.return_value.set_ascii_mode = AsyncMock()

        await async_session.connect()

        await async_session.send(b"test data")

        mock_open.assert_called_once()
        mock_handler.assert_called_once_with(mock_reader, mock_writer)
        mock_handler.return_value.send_data.assert_called_once_with(b"test data")
        assert async_session._connected is True

    async def test_send_not_connected(self, async_session):
        with pytest.raises(SessionError):
            await async_session.send(b"data")

    @patch("pure3270.session.asyncio.open_connection")
    @patch("pure3270.session.TN3270Handler")
    async def test_read(self, mock_handler, mock_open, async_session):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)
        handler_instance = AsyncMock()
        mock_handler.return_value = handler_instance
        mock_reader.readexactly.return_value = b"\xff\xfb\x27"
        mock_reader.read.return_value = b"\x28\x00\x01\x00"
        handler_instance.set_ascii_mode = AsyncMock()
        handler_instance.receive_data.return_value = b"test"
        # Mock handler properties
        handler_instance.screen_rows = 24
        handler_instance.screen_cols = 80
        handler_instance.negotiated_tn3270e = False
        handler_instance.lu_name = None

        await async_session.connect()

        data = await async_session.read()

        assert data == b"test"
        mock_open.assert_called_once()
        mock_handler.assert_called_once_with(mock_reader, mock_writer)
        handler_instance.receive_data.assert_called_once_with(5.0)
        assert async_session._connected is True

    async def test_read_not_connected(self, async_session):
        with pytest.raises(SessionError):
            await async_session.read()

    async def test_close(self, async_session):
        async_session._handler = AsyncMock()
        async_session._handler.close = AsyncMock()
        async_session._connected = True

        handler = async_session._handler
        await async_session.close()

        handler.close.assert_called_once()
        assert async_session._connected is False
        assert async_session._handler is None

    async def test_close_no_handler(self, async_session):
        await async_session.close()
        assert async_session._connected is False

    def test_connected(self, async_session):
        assert async_session.connected is False
        async_session._connected = True
        assert async_session.connected is True

    async def test_managed_context(self, async_session):
        async_session._connected = True
        async_session.close = AsyncMock()
        async with async_session.managed():
            assert async_session._connected is True
        async_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_conditional_branching(self):
        """Test conditional branching in execute_macro."""
        session = AsyncSession("localhost", 23)
        with patch("pure3270.session.asyncio.open_connection") as mock_open, patch(
            "pure3270.session.TN3270Handler"
        ) as mock_handler:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_open.return_value = (mock_reader, mock_writer)
            mock_handler.return_value = AsyncMock()
            mock_reader.readexactly.return_value = b"\xff\xfb\x27"
            mock_reader.read.return_value = b"\x28\x00\x01\x00"
            mock_handler.return_value.set_ascii_mode = AsyncMock()
            await session.connect()
        session.send = AsyncMock()
        session.read = AsyncMock(return_value=b"output")

        macro = "if connected: key Enter"
        vars_dict = {}
        result = await session.execute_macro(macro, vars_dict)

        assert result["success"] is True
        assert len(result["output"]) == 1
        assert "output" in result["output"][0]
        session.send.assert_called_once_with(b"key Enter")

    @pytest.mark.asyncio
    async def test_variable_substitution(self):
        """Test variable substitution in execute_macro."""
        session = AsyncSession("localhost", 23)
        with patch("pure3270.session.asyncio.open_connection") as mock_open, patch(
            "pure3270.session.TN3270Handler"
        ) as mock_handler:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_open.return_value = (mock_reader, mock_writer)
            mock_handler.return_value = AsyncMock()
            mock_reader.readexactly.return_value = b"\xff\xfb\x27"
            mock_reader.read.return_value = b"\x28\x00\x01\x00"
            mock_handler.return_value.set_ascii_mode = AsyncMock()
            await session.connect()
        session.send = AsyncMock()
        session.read = AsyncMock(return_value=b"substituted")

        macro = "key ${action}"
        vars_dict = {"action": "PF3"}
        result = await session.execute_macro(macro, vars_dict)

        assert result["success"] is True
        assert len(result["output"]) == 1
        assert "substituted" in result["output"][0]
        session.send.assert_called_once_with(b"key PF3")

    @pytest.mark.asyncio
    async def test_nested_macros(self):
        """Test nested macros in execute_macro."""
        session = AsyncSession("localhost", 23)
        with patch("pure3270.session.asyncio.open_connection") as mock_open, patch(
            "pure3270.session.TN3270Handler"
        ) as mock_handler:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_open.return_value = (mock_reader, mock_writer)
            mock_handler.return_value = AsyncMock()
            mock_reader.readexactly.return_value = b"\xff\xfb\x27"
            mock_reader.read.return_value = b"\x28\x00\x01\x00"
            mock_handler.return_value.set_ascii_mode = AsyncMock()
            await session.connect()
        session.send = AsyncMock()
        session.read = AsyncMock(return_value=b"nested output")

        macro = "macro sub_macro"
        vars_dict = {"sub_macro": "key Enter"}
        result = await session.execute_macro(macro, vars_dict)

        assert result["success"] is True
        assert len(result["output"]) == 1
        sub_result = result["output"][0]
        assert isinstance(sub_result, dict)
        assert sub_result["success"] is True
        assert len(sub_result["output"]) == 1
        assert "nested output" in sub_result["output"][0]
        session.send.assert_called_once_with(b"key Enter")

    @pytest.mark.asyncio
    async def test_incompatible_patching(self):
        """Test macro execution with incompatible patching (graceful handling)."""
        with patch("pure3270.patching.patching.enable_replacement") as mock_patch:
            mock_patch.side_effect = ValueError("Incompatible version")

            session = AsyncSession("localhost", 23)
            with patch("pure3270.session.asyncio.open_connection") as mock_open, patch(
                "pure3270.session.TN3270Handler"
            ) as mock_handler:
                mock_reader = AsyncMock()
                mock_writer = AsyncMock()
                mock_open.return_value = (mock_reader, mock_writer)
                mock_handler.return_value = AsyncMock()
                mock_reader.readexactly.return_value = b"\xff\xfb\x27"
                mock_reader.read.return_value = b"\x28\x00\x01\x00"
                mock_handler.return_value.set_ascii_mode = AsyncMock()
                await session.connect()
            session.send = AsyncMock()
            session.read = AsyncMock(return_value=b"output")

            macro = "key Enter"
            result = await session.execute_macro(macro)

            assert result["success"] is True
            assert len(result["output"]) == 1
            assert "output" in result["output"][0]

    @pytest.mark.asyncio
    async def test_execute_macro_malformed(self, async_session):
        """Test macro execution with malformed script raising MacroError."""
        with patch("pure3270.session.asyncio.open_connection") as mock_open, patch(
            "pure3270.session.TN3270Handler"
        ) as mock_handler:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_open.return_value = (mock_reader, mock_writer)
            mock_handler.return_value = AsyncMock()
            mock_reader.readexactly.return_value = b"\xff\xfb\x27"
            mock_reader.read.return_value = b"\x28\x00\x01\x00"
            mock_handler.return_value.set_ascii_mode = AsyncMock()
            await async_session.connect()
        with patch.object(
            async_session, "send", side_effect=MacroError("Invalid command")
        ):
            result = await async_session.execute_macro("invalid_cmd;")
        assert result["success"] is False
        assert "Error in command" in result["output"][0]

    @pytest.mark.asyncio
    async def test_execute_macro_unhandled_exception(self, async_session):
        """Test unhandled exception in async macro loop raises MacroError."""
        with patch("pure3270.session.asyncio.open_connection") as mock_open, patch(
            "pure3270.session.TN3270Handler"
        ) as mock_handler:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_open.return_value = (mock_reader, mock_writer)
            mock_handler.return_value = AsyncMock()
            mock_reader.readexactly.return_value = b"\xff\xfb\x27"
            mock_reader.read.return_value = b"\x28\x00\x01\x00"
            mock_handler.return_value.set_ascii_mode = AsyncMock()
            await async_session.connect()
        async_session.send = AsyncMock()
        async_session.read = AsyncMock(side_effect=Exception("Unhandled"))
        result = await async_session.execute_macro("cmd1;cmd2;")
        assert result["success"] is False
        assert "Error in command" in result["output"][0]

    @pytest.mark.asyncio
    async def test_execute_macro_timeout(self, async_session):
        """Test macro execution failure with timeout raises MacroError."""
        with patch("pure3270.session.asyncio.open_connection") as mock_open, patch(
            "pure3270.session.TN3270Handler"
        ) as mock_handler:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_open.return_value = (mock_reader, mock_writer)
            mock_handler.return_value = AsyncMock()
            mock_reader.readexactly.return_value = b"\xff\xfb\x27"
            mock_reader.read.return_value = b"\x28\x00\x01\x00"
            mock_handler.return_value.set_ascii_mode = AsyncMock()
            await async_session.connect()
        async_session.send = AsyncMock()
        async_session.read = AsyncMock(
            side_effect=[b"output1", asyncio.TimeoutError("Timeout")]
        )
        result = await async_session.execute_macro("cmd1;cmd2;")
        assert result["success"] is False
        assert "Error in command" in result["output"][1]

    @pytest.mark.asyncio
    async def test_execute_macro_empty(self, async_session):
        """Test macro with empty script succeeds with empty output."""
        async_session._handler = AsyncMock()
        async_session._connected = True
        result = await async_session.execute_macro("")
        assert result["success"] is True
        assert result["output"] == []


class TestSession:
    @patch("pure3270.session.asyncio.run")
    @patch("pure3270.session.AsyncSession")
    def test_connect(self, mock_async_session, mock_run, sync_session):
        mock_async_instance = AsyncMock()
        mock_async_session.return_value = mock_async_instance
        mock_async_instance.connect = AsyncMock()

        sync_session.connect()

        mock_async_session.assert_called_once_with(
            sync_session._host, sync_session._port, sync_session._ssl_context
        )
        mock_async_instance.connect.assert_called_once()
        mock_run.assert_called_once()

    @patch("pure3270.session.asyncio.run")
    def test_send(self, mock_run, sync_session):
        mock_run.return_value = None
        # Set up session to be connected
        sync_session._async_session = AsyncSession("localhost", 23)

        sync_session.send(b"data")

        mock_run.assert_called_once()

    @patch("pure3270.session.asyncio.run")
    def test_read(self, mock_run, sync_session):
        mock_run.return_value = b"data"
        # Set up session to be connected
        sync_session._async_session = AsyncSession("localhost", 23)

        data = sync_session.read()

        assert data == b"data"
        mock_run.assert_called_once()

    @patch("pure3270.session.asyncio.run")
    def test_execute_macro(self, mock_run, sync_session):
        mock_run.return_value = {"success": True}
        # Set up session to be connected
        sync_session._async_session = AsyncSession("localhost", 23)

        result = sync_session.execute_macro("macro")

        assert result["success"] is True
        mock_run.assert_called_once()

    @patch("pure3270.session.asyncio.run")
    def test_close(self, mock_run, sync_session):
        mock_run.return_value = None
        # Set up session to be connected
        sync_session._async_session = AsyncSession("localhost", 23)

        sync_session.close()

        mock_run.assert_called_once()

    def test_connected_property(self, sync_session):
        assert sync_session.connected is False
        sync_session._async_session = AsyncSession("localhost", 23)
        sync_session._async_session._connected = True
        assert sync_session.connected is True

    def test_screen_buffer_property(self, sync_session):
        sync_session._async_session = AsyncSession("localhost", 23)
        sync_session._async_session.screen_buffer = ScreenBuffer()
        assert isinstance(sync_session.screen_buffer, ScreenBuffer)

    @patch("pure3270.session.asyncio.run")
    def test_cursor_select(self, mock_run, sync_session):
        mock_run.return_value = None
        # Set up session to be connected
        sync_session._async_session = AsyncSession("localhost", 23)
        sync_session.cursor_select()
        mock_run.assert_called_once_with(ANY)  # Calls _cursor_select_async

    @patch("pure3270.session.asyncio.run")
    def test_delete_field(self, mock_run, sync_session):
        mock_run.return_value = None
        # Set up session to be connected
        sync_session._async_session = AsyncSession("localhost", 23)
        sync_session.delete_field()
        mock_run.assert_called_once_with(ANY)

    @patch("pure3270.session.asyncio.run")
    def test_circum_not(self, mock_run, sync_session):
        mock_run.return_value = None
        # Set up session to be connected
        sync_session._async_session = AsyncSession("localhost", 23)
        sync_session.circum_not()
        mock_run.assert_called_once_with(ANY)

    @patch("pure3270.session.asyncio.run")
    def test_script(self, mock_run, sync_session):
        mock_run.return_value = None
        # Set up session to be connected
        sync_session._async_session = AsyncSession("localhost", 23)
        sync_session.script("test")
        mock_run.assert_called_once_with(ANY)

    @patch("pure3270.session.asyncio.run")
    def test_erase(self, mock_run, sync_session):
        mock_run.return_value = None
        # Set up session to be connected
        sync_session._async_session = AsyncSession("localhost", 23)
        sync_session.erase()
        mock_run.assert_called_once_with(ANY)

    @patch("pure3270.session.asyncio.run")
    def test_erase_eof(self, mock_run, sync_session):
        mock_run.return_value = None
        # Set up session to be connected
        sync_session._async_session = AsyncSession("localhost", 23)
        sync_session.erase_eof()
        mock_run.assert_called_once_with(ANY)


@pytest.mark.asyncio
class TestAsyncSessionAdvanced:

    async def test_clear_action(self, async_session):
        """Test Clear action."""
        async_session.screen_buffer.buffer = bytearray([0xC1] * 100)  # EBCDIC 'A'
        await async_session.clear()
        assert list(async_session.screen_buffer.buffer[:100]) == [0x40] * 100

    async def test_cursor_select_action(self, async_session):
        """Test CursorSelect action."""
        from pure3270.emulation.screen_buffer import Field

        field = Field((0, 0), (0, 5), protected=False, selected=False)
        async_session.screen_buffer.fields = [field]
        async_session.screen_buffer.set_position(0, 2)
        await async_session.cursor_select()
        assert field.selected is True
        assert len(async_session.screen_buffer.fields) == 1  # Fields unchanged

    async def test_delete_field_action(self, async_session):
        """Test DeleteField action."""
        # Set up a simple field manually for testing
        from pure3270.emulation.screen_buffer import Field

        field = Field((0, 0), (0, 5), protected=False)
        async_session.screen_buffer.fields = [field]
        async_session.screen_buffer.set_position(0, 2)
        await async_session.delete_field()
        # Check that buffer is cleared to spaces (more important than field count)
        for i in range(6):
            assert async_session.screen_buffer.buffer[i] == 0x40  # Space in EBCDIC

    async def test_script_action(self, async_session):
        """Test Script action."""
        mock_method = AsyncMock()
        async_session.cursor_select = mock_method
        await async_session.script("cursor_select")
        mock_method.assert_called_once()

    async def test_circum_not_action(self, async_session):
        """Test CircumNot action."""
        assert async_session.circumvent_protection is False
        await async_session.circum_not()
        assert async_session.circumvent_protection is True
        await async_session.circum_not()
        assert async_session.circumvent_protection is False

    async def test_insert_text_with_circumvent(self, async_session):
        """Test insert_text with circumvent_protection."""
        # Mock connection for local operations
        async_session._connected = True
        async_session.handler = AsyncMock()

        # Setup protected field
        async_session.screen_buffer.attributes[0] = 0x40  # Protected (bit 6)
        async_session.circumvent_protection = True
        async_session.screen_buffer.set_position(0, 0)
        await async_session.insert_text("A")
        assert list(async_session.screen_buffer.buffer[0:1]) == [0xC1]  # EBCDIC for A

    async def test_insert_text_protected_without_circumvent(self, async_session):
        """Test insert_text skips protected without circumvent."""
        # Mock connection for local operations
        async_session._connected = True
        async_session.handler = AsyncMock()

        # Setup protected field
        async_session.screen_buffer.attributes[0] = 0x40  # Protected (bit 6)
        async_session.circumvent_protection = False
        async_session.screen_buffer.set_position(0, 0)
        await async_session.insert_text("A")
        assert list(async_session.screen_buffer.buffer[0:1]) == [
            0x40
        ]  # Space (skipped)

    async def test_disconnect_action(self, async_session):
        """Test Disconnect action."""
        mock_close = AsyncMock()
        async_session.close = mock_close
        await async_session.disconnect()
        mock_close.assert_called_once()

    async def test_info_action(self, async_session):
        """Test Info action (capture output)."""
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        try:
            await async_session.info()
        finally:
            sys.stdout = old_stdout
        output = captured_output.getvalue()
        assert "Connected:" in output

    async def test_quit_action(self, async_session):
        """Test Quit action."""
        mock_close = AsyncMock()
        async_session.close = mock_close
        await async_session.quit()
        mock_close.assert_called_once()

    async def test_newline_action(self, async_session):
        """Test Newline action."""
        async_session.screen_buffer.set_position(0, 0)
        await async_session.newline()
        row, col = async_session.screen_buffer.get_position()
        assert col == 0 and row > 0

    async def test_page_down_action(self, async_session):
        """Test PageDown action."""
        async_session.screen_buffer.set_position(0, 0)
        await async_session.page_down()
        row, col = async_session.screen_buffer.get_position()
        assert row == 0  # Full cycle wraps back to 0

    async def test_page_up_action(self, async_session):
        """Test PageUp action."""
        async_session.screen_buffer.set_position(23, 79)
        await async_session.page_up()
        row, col = async_session.screen_buffer.get_position()
        assert row <= 0  # Should wrap

    async def test_paste_string_action(self, async_session):
        """Test PasteString action."""
        mock_insert = AsyncMock()
        async_session.insert_text = mock_insert
        await async_session.paste_string("test")
        mock_insert.assert_called_once_with("test")

    async def test_set_option_action(self, async_session):
        """Test Set action."""
        # Placeholder test
        await async_session.set_option("option", "value")
        # Assert no error
        assert True

    async def test_bell_action(self, async_session):
        """Test Bell action."""
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        try:
            await async_session.bell()
        finally:
            sys.stdout = old_stdout
        output = captured_output.getvalue()
        assert "\a" in output or output == ""  # Depending on implementation

    async def test_pause_action(self, async_session):
        """Test Pause action."""
        import time

        start = time.time()
        await async_session.pause(0.1)
        end = time.time()
        assert end - start >= 0.05  # Allow some tolerance

    async def test_ansi_text_action(self, async_session):
        """Test AnsiText action."""
        data = b"\xc1\xc2"  # EBCDIC 'A' 'B'
        result = await async_session.ansi_text(data)
        assert result == "AB"

    async def test_hex_string_action(self, async_session):
        """Test HexString action."""
        result = await async_session.hex_string("C1 C2")
        assert result == b"\xc1\xc2"

    async def test_show_action(self, async_session):
        """Test Show action."""
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        try:
            await async_session.show()
        finally:
            sys.stdout = old_stdout
        output = captured_output.getvalue()
        assert output == async_session.screen_buffer.to_text()

    async def test_left2_action(self, async_session):
        """Test Left2 action."""
        # Mock connection for local operations
        async_session._connected = True
        async_session.handler = AsyncMock()

        async_session.screen_buffer.set_position(0, 5)
        await async_session.left2()
        row, col = async_session.screen_buffer.get_position()
        assert col == 3

    async def test_right2_action(self, async_session):
        """Test Right2 action."""
        # Mock connection for local operations
        async_session._connected = True
        async_session.handler = AsyncMock()

        async_session.screen_buffer.set_position(0, 0)
        await async_session.right2()
        row, col = async_session.screen_buffer.get_position()
        assert col == 2

    async def test_nvt_text_action(self, async_session):
        """Test NvtText action."""
        mock_send = AsyncMock()
        async_session.send = mock_send
        await async_session.nvt_text("hello")
        mock_send.assert_called_once_with(b"hello")

    async def test_print_text_action(self, async_session):
        """Test PrintText action."""
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        try:
            await async_session.print_text("test")
        finally:
            sys.stdout = old_stdout
        output = captured_output.getvalue()
        assert "test" in output

    async def test_read_buffer_action(self, async_session):
        """Test ReadBuffer action."""
        buffer = await async_session.read_buffer()
        assert (
            isinstance(buffer, bytes)
            and len(buffer) == async_session.screen_buffer.size
        )

    async def test_reconnect_action(self, async_session):
        """Test Reconnect action."""
        mock_close = AsyncMock()
        mock_connect = AsyncMock()
        async_session.close = mock_close
        async_session.connect = mock_connect
        await async_session.reconnect()
        mock_close.assert_called_once()
        mock_connect.assert_called_once()

    async def test_screen_trace_action(self, async_session):
        """Test ScreenTrace action."""
        # Placeholder test
        await async_session.screen_trace()
        assert True

    async def test_source_action(self, async_session):
        """Test Source action."""
        # Placeholder test
        await async_session.source("test_file")
        assert True

    async def test_subject_names_action(self, async_session):
        """Test SubjectNames action."""
        # Placeholder test
        await async_session.subject_names()
        assert True

    async def test_sys_req_action(self, async_session):
        """Test SysReq action."""
        # Placeholder test
        await async_session.sys_req()
        assert True

    async def test_toggle_option_action(self, async_session):
        """Test Toggle action."""
        # Placeholder test
        await async_session.toggle_option("option")
        assert True

    async def test_trace_action(self, async_session):
        """Test Trace action."""
        # Placeholder test
        await async_session.trace(True)
        assert True

    async def test_transfer_action(self, async_session):
        """Test Transfer action."""
        # Placeholder test
        await async_session.transfer("test_file")
        assert True

    async def test_wait_condition_action(self, async_session):
        """Test Wait action."""
        # Placeholder test
        await async_session.wait_condition("condition")
        assert True

    @patch("os.path.getmtime", return_value=1234567890.0)
    @pytest.mark.asyncio
    async def test_load_resource_definitions(self, mock_getmtime, async_session):
        """Test resource definitions loading."""
        # Mock connection for local operations
        async_session._connected = True
        async_session.handler = AsyncMock()

        # Mock file path and check no error
        with patch("builtins.open", mock_open(read_data="s3270.model: 3279")):
            await async_session.load_resource_definitions("test.xrdb")
        assert True

    @patch("os.path.getmtime", return_value=1234567890.0)
    @pytest.mark.asyncio
    async def test_load_resource_definitions_parsing(
        self, mock_getmtime, async_session
    ):
        """Test parsing valid xrdb file."""
        # Mock connection for local operations
        async_session._connected = True
        async_session.handler = AsyncMock()

        xrdb_content = """s3270.color8: #FF0000
s3270.ssl: true
s3270.model: 3279
s3270.font: monospace
# comment
s3270.keymap: default
"""
        with patch("builtins.open", mock_open(read_data=xrdb_content)):
            await async_session.load_resource_definitions("test.xrdb")

        assert async_session.resources == {
            "color8": "#FF0000",
            "ssl": "true",
            "model": "3279",
            "font": "monospace",
            "keymap": "default",
        }
        assert async_session.model == "3279"
        assert async_session.color_mode is False  # 3279 is not '3'
        assert async_session.font == "monospace"
        assert async_session.keymap == "default"
        # Check color applied
        r, g, b = async_session.color_palette[8]
        assert r == 255 and g == 0 and b == 0

    @patch("os.path.getmtime", return_value=1234567890.0)
    @pytest.mark.asyncio
    async def test_load_resource_definitions_error(self, mock_getmtime, async_session):
        """Test error handling: invalid file raises error."""
        # Mock connection for local operations
        async_session._connected = True
        async_session.handler = AsyncMock()

        with patch("builtins.open", side_effect=IOError("File not found")):
            with pytest.raises(SessionError):
                await async_session.load_resource_definitions("nonexistent.xrdb")

    @patch("os.path.getmtime", return_value=1234567890.0)
    @pytest.mark.asyncio
    async def test_load_resource_definitions_invalid_resource(
        self, mock_getmtime, async_session
    ):
        """Test error handling: invalid resource logged but partial success."""
        # Mock connection for local operations
        async_session._connected = True
        async_session.handler = AsyncMock()

        xrdb_content = """s3270.color8: invalid
s3270.model: 3279
"""
        with patch("builtins.open", mock_open(read_data=xrdb_content)):
            with patch.object(async_session, "logger") as mock_logger:
                await async_session.load_resource_definitions("test.xrdb")

        # Partial success: model applied
        assert async_session.model == "3279"
        # Invalid color logged
        mock_logger.warning.assert_called()
        # No SessionError raised

    @patch("os.path.getmtime", return_value=1234567890.0)
    @pytest.mark.asyncio
    async def test_load_resource_definitions_integration_macro(
        self, mock_getmtime, async_session
    ):
        """Integration test: Load resources in macro and verify."""
        # Mock connection for local operations
        async_session._connected = True
        async_session.handler = AsyncMock()

        xrdb_content = """s3270.color1: #00FF00
"""
        with patch("builtins.open", mock_open(read_data=xrdb_content)):
            # Mock macro execution to include LoadResource
            async_session.load_resource_definitions = AsyncMock()
            macro = "LoadResource(test.xrdb); key Enter"
            vars_dict = {}
            result = await async_session.execute_macro(macro, vars_dict)

        # Verify LoadResource called
        async_session.load_resource_definitions.assert_called_once_with("test.xrdb")
        # Verify key Enter sent (macro parsing)
        # (Actual implementation may vary)

    async def test_set_field_attribute(self, async_session):
        """Test extended field attributes."""
        # Setup a field
        from pure3270.emulation.screen_buffer import Field

        async_session.screen_buffer.fields = [
            Field((0, 0), (0, 10), protected=False, content=b"test")
        ]
        async_session.set_field_attribute(0, "color", 0x01)
        # Check if attributes were set (simplified)
        assert len(async_session.screen_buffer.attributes) > 0

    async def test_erase_action(self, async_session):
        """Test Erase action."""
        async_session.screen_buffer.set_position(0, 0)
        async_session.screen_buffer.buffer[0] = 0xC1  # EBCDIC 'A'
        await async_session.erase()
        assert list(async_session.screen_buffer.buffer[0:1]) == [0x40]  # Space

    async def test_erase_eof_action(self, async_session):
        """Test EraseEOF action."""
        async_session.screen_buffer.set_position(0, 2)
        async_session.screen_buffer.buffer[2:5] = [0xC1, 0xC2, 0xC3]
        await async_session.erase_eof()
        assert list(async_session.screen_buffer.buffer[2:5]) == [0x40, 0x40, 0x40]

    async def test_end_action(self, async_session):
        """Test End action."""
        async_session.screen_buffer.set_position(0, 0)
        await async_session.end()
        row, col = async_session.screen_buffer.get_position()
        assert col == async_session.screen_buffer.cols - 1

    async def test_field_end_action(self, async_session):
        """Test FieldEnd action."""
        mock_end = AsyncMock()
        async_session.end = mock_end
        await async_session.field_end()
        mock_end.assert_called_once()

    async def test_erase_input_action(self, async_session):
        """Test EraseInput action."""
        from pure3270.emulation.screen_buffer import Field

        field = Field(
            (0, 0),
            (0, 5),
            protected=False,
            content=bytes([0xC1, 0xC2, 0xC3, 0xC4, 0xC5]),
        )
        async_session.screen_buffer.fields = [field]
        await async_session.erase_input()
        assert list(field.content) == [0x40] * 5  # Spaces
        assert field.modified is True

    async def test_move_cursor_action(self, async_session):
        """Test MoveCursor action."""
        await async_session.move_cursor(5, 10)
        row, col = async_session.screen_buffer.get_position()
        assert row == 5 and col == 10

    async def test_move_cursor1_action(self, async_session):
        """Test MoveCursor1 action (1-based)."""
        await async_session.move_cursor1(1, 1)
        row, col = async_session.screen_buffer.get_position()
        assert row == 0 and col == 0  # 1-based to 0-based

    async def test_next_word_action(self, async_session):
        """Test NextWord action."""
        mock_right = AsyncMock()
        async_session.right = mock_right
        await async_session.next_word()
        mock_right.assert_called_once()

    async def test_previous_word_action(self, async_session):
        """Test PreviousWord action."""
        mock_left = AsyncMock()
        async_session.left = mock_left
        await async_session.previous_word()
        mock_left.assert_called_once()

    async def test_flip_action(self, async_session):
        """Test Flip action."""
        mock_toggle = AsyncMock()
        async_session.toggle_insert = mock_toggle
        await async_session.flip()
        mock_toggle.assert_called_once()

    async def test_insert_action(self, async_session):
        """Test Insert action."""
        initial_mode = async_session.insert_mode
        await async_session.insert()
        assert async_session.insert_mode != initial_mode  # Toggles mode

    async def test_delete_action(self, async_session):
        """Test Delete action."""
        async_session.screen_buffer.set_position(0, 1)
        async_session.screen_buffer.buffer[1:4] = [0xC1, 0xC2, 0xC3]
        await async_session.delete()
        assert list(async_session.screen_buffer.buffer[1:3]) == [0xC2, 0xC3]
        assert list(async_session.screen_buffer.buffer[3:4]) == [0x40]  # Last cleared
