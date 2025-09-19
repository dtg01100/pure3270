import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pure3270.protocol.negotiator import SnaSessionState
from pure3270.protocol.ssl_wrapper import SSLWrapper
from pure3270.protocol.tn3270_handler import (
    NegotiationError,
    ProtocolError,
    TN3270Handler,
)
from pure3270.protocol.tn3270e_header import TN3270EHeader
from pure3270.protocol.utils import TELOPT_EOR, TELOPT_TN3270E, WILL


class TestTN3270Handler:
    @pytest.mark.asyncio
    @patch("asyncio.open_connection")
    async def test_connect_non_ssl(self, mock_open, tn3270_handler):
        # Clear existing reader/writer to test connection logic
        tn3270_handler.reader = None
        tn3270_handler.writer = None
        tn3270_handler._connected = False

        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_reader.read.return_value = b""  # Initial data
        mock_reader.at_eof.return_value = False  # Not at EOF
        mock_open.return_value = (mock_reader, mock_writer)

        # Mock the SessionManager methods to avoid real network calls
        with patch(
            "pure3270.protocol.tn3270_handler.SessionManager"
        ) as mock_session_manager:
            mock_manager = AsyncMock()
            mock_manager.setup_connection = AsyncMock()
            mock_manager.perform_telnet_negotiation = AsyncMock()
            mock_manager.perform_tn3270_negotiation = AsyncMock()
            mock_manager.reader = mock_reader
            mock_manager.writer = mock_writer
            mock_session_manager.return_value = mock_manager

            await tn3270_handler.connect()

        assert tn3270_handler.reader == mock_reader
        assert tn3270_handler.writer == mock_writer

    @pytest.mark.asyncio
    @patch("asyncio.open_connection")
    async def test_connect_ssl(self, mock_open, tn3270_handler):
        # Clear existing reader/writer to test connection logic
        tn3270_handler.reader = None
        tn3270_handler.writer = None
        tn3270_handler._connected = False

        ssl_wrapper = SSLWrapper()
        ssl_context = ssl_wrapper.get_context()
        tn3270_handler.ssl_context = ssl_context
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_reader.read.return_value = b""  # Initial data
        mock_reader.at_eof.return_value = False  # Not at EOF
        mock_open.return_value = (mock_reader, mock_writer)

        # Mock the SessionManager methods to avoid real network calls
        with patch(
            "pure3270.protocol.tn3270_handler.SessionManager"
        ) as mock_session_manager:
            mock_manager = AsyncMock()
            mock_manager.setup_connection = AsyncMock()
            mock_manager.perform_telnet_negotiation = AsyncMock()
            mock_manager.perform_tn3270_negotiation = AsyncMock()
            mock_manager.reader = mock_reader
            mock_manager.writer = mock_writer
            mock_session_manager.return_value = mock_manager

            await tn3270_handler.connect()

        assert tn3270_handler.reader == mock_reader
        assert tn3270_handler.writer == mock_writer

    @pytest.mark.asyncio
    @patch("asyncio.open_connection")
    async def test_connect_error(self, mock_open, tn3270_handler):
        # Clear existing reader/writer to test connection logic
        tn3270_handler.reader = None
        tn3270_handler.writer = None
        tn3270_handler._connected = False

        mock_open.side_effect = Exception("Connection failed")
        with pytest.raises(ConnectionError):
            await tn3270_handler.connect()

    def test_sna_session_state_property(self, tn3270_handler):
        # Initial state should be NORMAL
        assert tn3270_handler.sna_session_state == SnaSessionState.NORMAL.value
        # Mock negotiator's state change
        tn3270_handler.negotiator._sna_session_state = SnaSessionState.ERROR
        assert tn3270_handler.sna_session_state == SnaSessionState.ERROR.value

    @pytest.mark.asyncio
    async def test_negotiate_tn3270_success(self, tn3270_handler):
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        # Update negotiator's writer as well
        tn3270_handler.negotiator.writer = tn3270_handler.writer

        # Manually trigger negotiation steps to set events
        # DEVICE-TYPE SEND
        await tn3270_handler.negotiator.handle_subnegotiation(TELOPT_TN3270E, b'\x00\x04')
        # DEVICE-TYPE IS
        await tn3270_handler.negotiator.handle_subnegotiation(TELOPT_TN3270E, b'\x00\x02IBM-3279-4-E\x00')
        # FUNCTIONS IS
        await tn3270_handler.negotiator.handle_subnegotiation(TELOPT_TN3270E, b'\x01\x02\x01\x02\x04\x08')
        # WILL EOR
        def mock_send_iac(*args, **kwargs):
            return asyncio.sleep(0)
        with patch('pure3270.protocol.utils.send_iac', side_effect=mock_send_iac):
            await tn3270_handler.negotiator.handle_iac_command(WILL, TELOPT_EOR)

        # Mock the infer_tn3270e_from_trace method to return True
        tn3270_handler.negotiator.infer_tn3270e_from_trace = MagicMock(
            return_value=True
        )

        with patch.object(tn3270_handler, '_reader_loop', return_value=None):
            with patch('asyncio.wait_for', return_value=None):
                await tn3270_handler._negotiate_tn3270()
            assert tn3270_handler.negotiated_tn3270e is True

    @pytest.mark.asyncio
    async def test_negotiate_tn3270_fail(self, tn3270_handler):
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        # Update negotiator's writer as well
        tn3270_handler.negotiator.writer = tn3270_handler.writer

        # Mock failure response - WONT TN3270E
        tn3270_handler.reader.read.return_value = b"\xff\xfc\x24"  # WONT TN3270E

        await tn3270_handler._negotiate_tn3270()
        assert tn3270_handler.negotiated_tn3270e is False

    @pytest.mark.asyncio
    async def test_send_data(self, tn3270_handler):
        data = b"\x7d"
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        await tn3270_handler.send_data(data)
        tn3270_handler.writer.write.assert_called_with(data)

    @pytest.mark.asyncio
    async def test_send_data_not_connected(self, tn3270_handler):
        tn3270_handler.writer = None
        with pytest.raises(ProtocolError):
            await tn3270_handler.send_data(b"")

    @pytest.mark.asyncio
    async def test_receive_data(self, tn3270_handler):
        data = b"\xc1\xc2"
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.reader.read.return_value = data + b"\xff\x19"  # Add EOR marker
        received = await tn3270_handler.receive_data()
        assert received == data

    @pytest.mark.asyncio
    async def test_receive_data_not_connected(self, tn3270_handler):
        tn3270_handler.reader = None
        with pytest.raises(ProtocolError):
            await tn3270_handler.receive_data()

    @pytest.mark.asyncio
    async def test_close(self, tn3270_handler):
        mock_writer = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        tn3270_handler.writer = mock_writer
        await tn3270_handler.close()
        mock_writer.close.assert_called_once()
        assert tn3270_handler.writer is None

    def test_is_connected(self, tn3270_handler):
        assert tn3270_handler.is_connected() is False
        tn3270_handler.writer = MagicMock()
        tn3270_handler.reader = MagicMock()
        tn3270_handler.writer.is_closing = MagicMock(return_value=False)
        tn3270_handler.reader.at_eof = MagicMock(return_value=False)
        tn3270_handler._connected = True
        assert tn3270_handler.is_connected() is True

    def test_is_connected_writer_closing(self, tn3270_handler):
        tn3270_handler.writer = MagicMock()
        tn3270_handler.reader = MagicMock()
        tn3270_handler.writer.is_closing = MagicMock(return_value=True)
        tn3270_handler.reader.at_eof = MagicMock(return_value=False)
        tn3270_handler._connected = True
        assert tn3270_handler.is_connected() is False

    def test_is_connected_reader_at_eof(self, tn3270_handler):
        tn3270_handler.writer = MagicMock()
        tn3270_handler.reader = MagicMock()
        tn3270_handler.writer.is_closing = MagicMock(return_value=False)
        tn3270_handler.reader.at_eof = MagicMock(return_value=True)
        tn3270_handler._connected = True
        assert tn3270_handler.is_connected() is False

    @pytest.mark.asyncio
    async def test_tn3270e_negotiation_with_fallback(self, tn3270_handler):
        """
        Ported from s3270 test case 2: TN3270E negotiation with fallback.
        Input subnegotiation for TN3270E (e.g., BIND-IMAGE); output fallback to basic TN3270,
        DO/DONT responses; assert no errors, correct options.
        """
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        # Update negotiator's writer as well
        tn3270_handler.negotiator.writer = tn3270_handler.writer

        # Mock responses: WONT TN3270E
        tn3270_handler.reader.read.side_effect = [
            b"\xff\xfc\x24",  # WONT TN3270E
            b"\xff\xfb\x19",  # WILL EOR
        ]

        # Call negotiate
        await tn3270_handler._negotiate_tn3270()

        # Assert fallback to basic TN3270, no error
        assert tn3270_handler.negotiated_tn3270e is False
        # No NegotiationError raised

    @pytest.mark.asyncio
    async def test_send_scs_data_printer_session(self, tn3270_handler):
        tn3270_handler._connected = True
        tn3270_handler.negotiator.is_printer_session = True
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()

        await tn3270_handler.send_scs_data(b"printer data")
        tn3270_handler.writer.write.assert_called_with(b"printer data")
        tn3270_handler.writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_scs_data_not_printer_session(self, tn3270_handler):
        tn3270_handler._connected = True
        tn3270_handler.is_printer_session = False

        with pytest.raises(ProtocolError):
            await tn3270_handler.send_scs_data(b"printer data")

    @pytest.mark.asyncio
    async def test_send_print_eoj_printer_session(self, tn3270_handler):
        tn3270_handler._connected = True
        tn3270_handler.negotiator.is_printer_session = True
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()

        await tn3270_handler.send_print_eoj()
        # Should send SCS-CTL-CODES with PRINT-EOJ (0x01)
        tn3270_handler.writer.write.assert_called()
        tn3270_handler.writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_print_eoj_not_printer_session(self, tn3270_handler):
        tn3270_handler._connected = True
        tn3270_handler.is_printer_session = False

        with pytest.raises(ProtocolError):
            await tn3270_handler.send_print_eoj()

    def test_is_printer_session_active(self, tn3270_handler):
        tn3270_handler.is_printer_session = False
        assert tn3270_handler.is_printer_session_active() is False

        tn3270_handler.is_printer_session = True
        assert tn3270_handler.is_printer_session_active() is True

    @pytest.mark.asyncio
    async def test_process_telnet_stream_iac_do_dont_will_wont(self, tn3270_handler):
        from pure3270.protocol.utils import DO, DONT, EOR, IAC
        from pure3270.protocol.utils import (
            TELOPT_BINARY as BINARY,  # Use alias for clarity
        )
        from pure3270.protocol.utils import WILL, WONT

        tn3270_handler.writer = AsyncMock()
        tn3270_handler.negotiator.writer = (
            tn3270_handler.writer
        )  # Ensure negotiator has the mock writer

        # Test DO
        data = bytes([IAC, DO, BINARY])
        with patch.object(
            tn3270_handler.negotiator, "handle_iac_command"
        ) as mock_handle_iac:
            result = await tn3270_handler._process_telnet_stream(data)
            cleaned_data, ascii_mode = result
            mock_handle_iac.assert_called_once_with(DO, BINARY)
            assert cleaned_data == b""
            assert not ascii_mode

        # Test DONT
        data = bytes([IAC, DONT, BINARY])
        with patch.object(
            tn3270_handler.negotiator, "handle_iac_command"
        ) as mock_handle_iac:
            result = await tn3270_handler._process_telnet_stream(data)
            cleaned_data, ascii_mode = result
            mock_handle_iac.assert_called_once_with(DONT, BINARY)
            assert cleaned_data == b""
            assert not ascii_mode

        # Test WILL
        data = bytes([IAC, WILL, BINARY])
        with patch.object(
            tn3270_handler.negotiator, "handle_iac_command"
        ) as mock_handle_iac:
            result = await tn3270_handler._process_telnet_stream(data)
            cleaned_data, ascii_mode = result
            mock_handle_iac.assert_called_once_with(WILL, BINARY)
            assert cleaned_data == b""
            assert not ascii_mode

        # Test WONT
        data = bytes([IAC, WONT, BINARY])
        with patch.object(
            tn3270_handler.negotiator, "handle_iac_command"
        ) as mock_handle_iac:
            result = await tn3270_handler._process_telnet_stream(data)
            cleaned_data, ascii_mode = result
            mock_handle_iac.assert_called_once_with(WONT, BINARY)
            assert cleaned_data == b""
            assert not ascii_mode

    @pytest.mark.asyncio
    async def test_process_telnet_stream_incomplete_iac(self, tn3270_handler):
        from pure3270.protocol.utils import DO, IAC

        # Incomplete IAC sequence
        data = bytes([IAC, DO])
        result = await tn3270_handler._process_telnet_stream(data)
        cleaned_data, ascii_mode = result
        assert cleaned_data == b""
        assert not ascii_mode
        assert tn3270_handler._telnet_buffer == data

        # Complete the sequence
        data_completion = bytes([0x01])  # Some option
        result = await tn3270_handler._process_telnet_stream(data_completion)
        cleaned_data, ascii_mode = result
        assert tn3270_handler._telnet_buffer == b""  # Buffer should be cleared
        # The command would have been handled by negotiator, so cleaned_data is still empty
        assert cleaned_data == b""
        assert not ascii_mode

    @pytest.mark.asyncio
    async def test_process_telnet_stream_incomplete_subnegotiation(
        self, tn3270_handler
    ):
        from pure3270.protocol.utils import IAC, SB, TN3270E

        # Incomplete subnegotiation sequence
        data = bytes([IAC, SB, TN3270E])
        result = await tn3270_handler._process_telnet_stream(data)
        cleaned_data, ascii_mode = result
        assert cleaned_data == b""
        assert not ascii_mode
        assert tn3270_handler._telnet_buffer == data

        # Complete the sequence
        data_completion = bytes([0x01, 0x02, IAC, 0xF0])  # Some sub-data and IAC SE
        with patch.object(
            tn3270_handler.negotiator, "_parse_tn3270e_subnegotiation"
        ) as mock_parse_sub:
            result = await tn3270_handler._process_telnet_stream(data_completion)
            cleaned_data, ascii_mode = result
            mock_parse_sub.assert_called_once_with(bytes([TN3270E, 0x01, 0x02]))
            assert cleaned_data == b""
            assert not ascii_mode
            assert tn3270_handler._telnet_buffer == b""

    @pytest.mark.asyncio
    async def test_receive_data_tn3270e_header_extraction(self, tn3270_handler):
        from pure3270.protocol.data_stream import SCS_DATA, TN3270_DATA
        from pure3270.protocol.tn3270e_header import TN3270EHeader

        # Mock a TN3270E header with SCS_DATA type
        mock_header = MagicMock(spec=TN3270EHeader)
        mock_header.data_type = SCS_DATA
        mock_header.seq_number = 123
        mock_header.request_flag = 0
        mock_header.response_flag = 0x00  # NO_RESPONSE
        mock_header_bytes = b"\x00\x00\x00\x00\x00"  # Dummy bytes, actual value doesn't matter for this test

        with (
            patch(
                "pure3270.protocol.tn3270e_header.TN3270EHeader.from_bytes",
                return_value=mock_header,
            ),
            patch.object(tn3270_handler.parser, "parse") as mock_parse_data_stream,
        ):

            tn3270_handler.reader = AsyncMock()
            # Simulate receiving TN3270E header + actual data + IAC EOR
            test_data = mock_header_bytes + b"actual data"
            tn3270_handler.reader.read.return_value = test_data + b"\xff\x19"

            received_data = await tn3270_handler.receive_data()

            # Verify that from_bytes was called with the correct header length
            TN3270EHeader.from_bytes.assert_called_once_with(test_data[:5])
            # Verify that parser.parse was called with the data type from the header and correct data
            mock_parse_data_stream.assert_called_once_with(
                b"actual data", data_type=SCS_DATA
            )
            # Verify that the returned data is the processed data (without IAC EOR)
            assert received_data == test_data

    @pytest.mark.asyncio
    async def test_receive_data_no_tn3270e_header(self, tn3270_handler):
        from pure3270.protocol.data_stream import TN3270_DATA

        with (
            patch(
                "pure3270.protocol.tn3270e_header.TN3270EHeader.from_bytes",
                return_value=None,
            ),
            patch.object(tn3270_handler.parser, "parse") as mock_parse_data_stream,
        ):

            tn3270_handler.reader = AsyncMock()
            # Simulate receiving data without TN3270E header + IAC EOR
            test_data = b"plain 3270 data"
            tn3270_handler.reader.read.return_value = test_data + b"\xff\x19"

            received_data = await tn3270_handler.receive_data()

            # Verify that from_bytes was called (and returned None)
            TN3270EHeader.from_bytes.assert_called_once()
            # Verify that parser.parse was called with default TN3270_DATA type and full data
            mock_parse_data_stream.assert_called_once_with(
                test_data, data_type=TN3270_DATA
            )
            # Verify that the returned data is the processed data (without IAC EOR)
            assert received_data == test_data

    @pytest.mark.asyncio
    async def test_receive_data_ascii_mode_detection(self, tn3270_handler):
        # Simulate VT100 sequence to trigger ASCII mode detection
        vt100_data = (
            b"\x1b[H\x1b[2JVT100 test"  # ESC H, ESC 2J (clear screen), then text
        )

        tn3270_handler.reader = AsyncMock()
        tn3270_handler.reader.read.return_value = vt100_data + b"\xff\x19"  # Add EOR

        # Patch the local import in receive_data
        with (
            patch("pure3270.protocol.tn3270_handler.VT100Parser") as MockVT100Parser,
            patch.object(
                tn3270_handler.negotiator, "set_ascii_mode"
            ) as mock_set_ascii_mode,
        ):

            await tn3270_handler.receive_data()

            mock_set_ascii_mode.assert_called_once()
            MockVT100Parser.return_value.parse.assert_called_once_with(vt100_data)
            assert (
                tn3270_handler.negotiator._ascii_mode is True
            )  # Should be set by set_ascii_mode

    @pytest.mark.asyncio
    async def test_receive_data_incomplete_telnet_sequence_buffering(
        self, tn3270_handler
    ):
        from pure3270.protocol.utils import DO, IAC, TELOPT_BINARY

        # First read: incomplete IAC sequence
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.reader.read.side_effect = [
            bytes([IAC, DO]),  # Incomplete DO command
            bytes(
                [TELOPT_BINARY, IAC, 0x19]
            ),  # Complete the DO command, and add a WILL EOR
        ]

        # First receive call
        with patch.object(
            tn3270_handler.negotiator, "handle_iac_command"
        ) as mock_handle_iac:
            received_data_1 = await tn3270_handler.receive_data()
            assert tn3270_handler._telnet_buffer == bytes(
                [IAC, DO]
            )  # Buffer should hold incomplete sequence
            assert received_data_1 == b""  # No 3270 data yet
            mock_handle_iac.assert_not_called()

            # Second receive call
            received_data_2 = await tn3270_handler.receive_data()
            mock_handle_iac.assert_called_once_with(DO, TELOPT_BINARY)
            assert tn3270_handler._telnet_buffer == b""  # Buffer should be cleared
            assert received_data_2 == b""  # Still no 3270 data, only IAC handling

    @pytest.mark.asyncio
    async def test_send_printer_status_sf(self, tn3270_handler):
        from pure3270.protocol.data_stream import (
            PRINTER_STATUS_SF_TYPE,
            STRUCTURED_FIELD,
        )

        tn3270_handler._connected = True
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        status_code = 0x01  # Example: Device End

        await tn3270_handler.send_printer_status_sf(status_code)

        expected_sf_payload = bytes([PRINTER_STATUS_SF_TYPE, status_code])
        expected_sf = (
            bytes([STRUCTURED_FIELD])
            + (len(expected_sf_payload) + 2).to_bytes(2, "big")
            + expected_sf_payload
        )
        tn3270_handler.writer.write.assert_called_once_with(expected_sf)
        tn3270_handler.writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_soh_message(self, tn3270_handler):
        from pure3270.protocol.data_stream import SOH, SOH_DEVICE_END

        tn3270_handler._connected = True
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        status_code = SOH_DEVICE_END  # Example: Device End

        await tn3270_handler.send_soh_message(status_code)

        expected_soh_message = bytes([SOH, status_code])
        tn3270_handler.writer.write.assert_called_once_with(expected_soh_message)
        tn3270_handler.writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_break(self, tn3270_handler):
        tn3270_handler._connected = True
        mock_writer = AsyncMock()
        mock_writer.drain = AsyncMock()
        tn3270_handler.writer = mock_writer

        await tn3270_handler.send_break()

        # Should send IAC BRK
        from pure3270.protocol.utils import BRK, IAC

        mock_writer.write.assert_called_once_with(bytes([IAC, BRK]))
        mock_writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_break_not_connected(self, tn3270_handler):
        tn3270_handler._connected = False

        with pytest.raises(ProtocolError, match="Not connected"):
            await tn3270_handler.send_break()

    @pytest.mark.asyncio
    async def test_process_telnet_stream_iac_brk(self, tn3270_handler):
        from pure3270.protocol.utils import BRK, IAC

        tn3270_handler.writer = AsyncMock()
        tn3270_handler.negotiator.writer = tn3270_handler.writer

        # Test BRK command
        data = bytes([IAC, BRK])
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
            mock_logger.debug.assert_called_with("Received IAC BRK")
            assert cleaned_data == b""
            assert not ascii_mode
