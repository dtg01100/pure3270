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

    @pytest.mark.asyncio
    async def test_sna_session_state_property(self, tn3270_handler):
        # Initial state should be NORMAL
        assert tn3270_handler.sna_session_state == SnaSessionState.NORMAL.value
        # Mock negotiator's state change
        tn3270_handler.negotiator._sna_session_state = SnaSessionState.ERROR
        assert tn3270_handler.sna_session_state == SnaSessionState.ERROR.value

    @pytest.mark.asyncio
    async def test_negotiate_tn3270_success(self, tn3270_handler):
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        # Update negotiator's writer as well
        tn3270_handler.negotiator.writer = tn3270_handler.writer

        # For this test, use force_mode to skip actual negotiation
        # and just verify the method completes successfully
        tn3270_handler.negotiator.force_mode = "tn3270e"

        # Mock the infer_tn3270e_from_trace method to return True
        tn3270_handler.negotiator.infer_tn3270e_from_trace = MagicMock(
            return_value=True
        )

        await tn3270_handler._negotiate_tn3270()
        assert tn3270_handler.negotiated_tn3270e is True

    @pytest.mark.asyncio
    async def test_negotiate_tn3270_fail(self, tn3270_handler):
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        # Update negotiator's writer as well
        tn3270_handler.negotiator.writer = tn3270_handler.writer

        # Mock responses: WONT TN3270E
        # Return WONT once, then empty bytes to signal end of negotiation data
        tn3270_handler.reader.read.side_effect = [
            b"\xff\xfc\x24",  # WONT TN3270E (0x24)
            b"",  # End of stream
        ]

        # Since we're mocking reader.read, the telnet parser won't process the WONT
        # So we need to directly set the flag that would have been set by _handle_wont()
        tn3270_handler.negotiator._server_supports_tn3270e = False
        # Also set allow_fallback=True to allow the negotiation to proceed without raising
        tn3270_handler.negotiator.allow_fallback = True

        # Mock asyncio.wait_for to cause timeout (simulating that events never complete)
        import asyncio
        from unittest.mock import patch

        async def mock_wait_for(coro, timeout=None):
            # Simulate timeout for all negotiation events
            raise asyncio.TimeoutError()

        with patch("asyncio.wait_for", side_effect=mock_wait_for):
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

    @pytest.mark.asyncio
    async def test_is_connected(self, tn3270_handler):
        assert tn3270_handler.is_connected() is False
        tn3270_handler.writer = MagicMock()
        tn3270_handler.reader = MagicMock()
        tn3270_handler.writer.is_closing = MagicMock(return_value=False)
        tn3270_handler.reader.at_eof = MagicMock(return_value=False)
        tn3270_handler._connected = True
        assert tn3270_handler.is_connected() is True

    @pytest.mark.asyncio
    async def test_is_connected_writer_closing(self, tn3270_handler):
        tn3270_handler.writer = MagicMock()
        tn3270_handler.reader = MagicMock()
        tn3270_handler.writer.is_closing = MagicMock(return_value=True)
        tn3270_handler.reader.at_eof = MagicMock(return_value=False)
        tn3270_handler._connected = True
        assert tn3270_handler.is_connected() is False

    @pytest.mark.asyncio
    async def test_is_connected_reader_at_eof(self, tn3270_handler):
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

    @pytest.mark.asyncio
    async def test_is_printer_session_active(self, tn3270_handler):
        tn3270_handler.is_printer_session = False
        assert tn3270_handler.is_printer_session is False

        tn3270_handler.is_printer_session = True
        assert tn3270_handler.is_printer_session is True

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
            # Set expected sequence number to match the mock header
            tn3270_handler._last_received_seq_number = 123

            received_data = await tn3270_handler.receive_data()

            # Verify that from_bytes was called with the correct header length
            TN3270EHeader.from_bytes.assert_called_once_with(test_data[:5])
            # Verify that parser.parse was called with the data type from the header and correct data
            mock_parse_data_stream.assert_called_once_with(
                b"actual data", data_type=SCS_DATA
            )
            # Verify that the returned data is the payload only (header and IAC EOR stripped)
            assert received_data == b"actual data"

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

    # --- Additional tests for improved coverage ---

    @pytest.mark.asyncio
    async def test_send_sysreq_command_tn3270e_negotiated(self, tn3270_handler):
        """Test SYSREQ command when TN3270E is negotiated."""
        from pure3270.protocol.utils import TN3270E_SYSREQ_ATTN

        tn3270_handler._connected = True
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        tn3270_handler.negotiator.negotiated_functions = TN3270E_SYSREQ_ATTN

        await tn3270_handler.send_sysreq_command(TN3270E_SYSREQ_ATTN)

        # Should send TN3270E subnegotiation
        tn3270_handler.writer.write.assert_called()
        tn3270_handler.writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_sysreq_command_fallback(self, tn3270_handler):
        """Test SYSREQ command fallback when TN3270E not negotiated."""
        from pure3270.protocol.utils import TN3270E_SYSREQ_ATTN

        tn3270_handler._connected = True
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        tn3270_handler.negotiator.negotiated_functions = 0  # No TN3270E functions

        await tn3270_handler.send_sysreq_command(TN3270E_SYSREQ_ATTN)

        # Should send IAC IP fallback
        from pure3270.protocol.utils import IAC, IP

        tn3270_handler.writer.write.assert_called_with(bytes([IAC, IP]))
        tn3270_handler.writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_sysreq_command_not_connected(self, tn3270_handler):
        """Test SYSREQ command when not connected."""
        from pure3270.protocol.utils import TN3270E_SYSREQ_ATTN

        tn3270_handler._connected = False

        with pytest.raises(ProtocolError, match="Not connected"):
            await tn3270_handler.send_sysreq_command(TN3270E_SYSREQ_ATTN)

    @pytest.mark.asyncio
    async def test_send_sysreq_command_no_fallback(self, tn3270_handler):
        """Test SYSREQ command with no fallback available."""
        from pure3270.protocol.utils import TN3270E_SYSREQ_BREAK

        tn3270_handler._connected = True
        tn3270_handler.negotiator.negotiated_functions = 0  # No TN3270E functions

        with pytest.raises(ProtocolError, match="SYSREQ function not negotiated"):
            await tn3270_handler.send_sysreq_command(TN3270E_SYSREQ_BREAK)

    @pytest.mark.asyncio
    async def test_negotiate_addressing_mode(self, tn3270_handler):
        """Test addressing mode negotiation."""
        with (
            patch.object(
                tn3270_handler._addressing_negotiator, "get_client_capabilities_string"
            ) as mock_caps,
            patch.object(
                tn3270_handler._addressing_negotiator, "parse_server_capabilities"
            ) as mock_parse,
            patch.object(
                tn3270_handler._addressing_negotiator, "negotiate_mode"
            ) as mock_negotiate,
        ):

            mock_caps.return_value = "test capabilities"
            mock_negotiate.return_value = MagicMock(value="14-bit")

            await tn3270_handler.negotiate_addressing_mode()

            mock_caps.assert_called_once()
            mock_parse.assert_called_once_with("test capabilities")
            mock_negotiate.assert_called_once()

    @pytest.mark.asyncio
    async def test_negotiate_addressing_mode_exception(self, tn3270_handler):
        """Test addressing mode negotiation with exception."""
        with patch.object(
            tn3270_handler._addressing_negotiator, "get_client_capabilities_string"
        ) as mock_caps:
            mock_caps.side_effect = Exception("Test exception")

            await tn3270_handler.negotiate_addressing_mode()

            # Should fall back to 12-bit mode
            assert (
                tn3270_handler._addressing_negotiator._negotiated_mode.value == "12-bit"
            )

    @pytest.mark.asyncio
    async def test_handle_bind_image(self, tn3270_handler):
        """Test BIND-IMAGE handling."""
        bind_data = b"\x00\x00\x00\x00\x01\x02\x03"

        with (
            patch(
                "pure3270.protocol.tn3270_handler.BindImageParser.parse_addressing_mode"
            ) as mock_parse,
            patch.object(
                tn3270_handler._addressing_negotiator, "update_from_bind_image"
            ) as mock_update,
        ):

            mock_parse.return_value = MagicMock(value="14-bit")

            await tn3270_handler.handle_bind_image(bind_data)

            mock_parse.assert_called_once_with(bind_data)
            mock_update.assert_called_once_with(bind_data)

    @pytest.mark.asyncio
    async def test_handle_bind_image_no_mode(self, tn3270_handler):
        """Test BIND-IMAGE handling when no addressing mode detected."""
        bind_data = b"\x00\x00\x00\x00\x01\x02\x03"

        with patch(
            "pure3270.protocol.tn3270_handler.BindImageParser.parse_addressing_mode"
        ) as mock_parse:
            mock_parse.return_value = None

            await tn3270_handler.handle_bind_image(bind_data)

            mock_parse.assert_called_once_with(bind_data)

    @pytest.mark.asyncio
    async def test_validate_addressing_mode_transition(self, tn3270_handler):
        """Test addressing mode transition validation."""
        from pure3270.emulation.addressing import AddressingMode

        # Test with None from_mode (initial state)
        result = await tn3270_handler.validate_addressing_mode_transition(
            None, AddressingMode.MODE_14_BIT
        )
        assert result is True

        # Test with valid transition
        result = await tn3270_handler.validate_addressing_mode_transition(
            AddressingMode.MODE_12_BIT, AddressingMode.MODE_14_BIT
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_transition_addressing_mode(self, tn3270_handler):
        """Test addressing mode transition."""
        from pure3270.emulation.addressing import AddressingMode

        # Test successful transition
        await tn3270_handler.transition_addressing_mode(AddressingMode.MODE_14_BIT)

        assert (
            tn3270_handler._addressing_negotiator._negotiated_mode
            == AddressingMode.MODE_14_BIT
        )

    @pytest.mark.asyncio
    async def test_transition_addressing_mode_invalid(self, tn3270_handler):
        """Test invalid addressing mode transition."""
        from pure3270.emulation.addressing import AddressingMode

        # First set a current mode
        await tn3270_handler.transition_addressing_mode(AddressingMode.MODE_12_BIT)

        # Mock invalid transition from 12-bit to 14-bit
        with patch.object(
            tn3270_handler._addressing_negotiator, "validate_mode_transition"
        ) as mock_validate:
            mock_validate.return_value = False

            with pytest.raises(ValueError, match="Invalid addressing mode transition"):
                await tn3270_handler.transition_addressing_mode(
                    AddressingMode.MODE_14_BIT
                )

    @pytest.mark.asyncio
    async def test_get_addressing_negotiation_summary(self, tn3270_handler):
        """Test getting addressing negotiation summary."""
        with patch.object(
            tn3270_handler._addressing_negotiator, "get_negotiation_summary"
        ) as mock_summary:
            mock_summary.return_value = {"test": "summary"}

            result = tn3270_handler.get_addressing_negotiation_summary()

            assert result == {"test": "summary"}

    @pytest.mark.asyncio
    async def test_sequence_number_management(self, tn3270_handler):
        """Test sequence number management methods."""
        # Test recording sequence number
        tn3270_handler._record_sequence_number(123, "sent")
        assert len(tn3270_handler._sequence_number_history) == 1

        # Test wraparound detection
        result = tn3270_handler._detect_sequence_wraparound(100, 65530)
        assert result is True

        # Test sequence validation
        result = tn3270_handler._validate_sequence_number(124, 123)
        assert result is True

        # Test next sequence number
        seq = tn3270_handler._get_next_sent_sequence_number()
        assert seq == 1

        # Test update received sequence
        tn3270_handler._update_received_sequence_number(125)

        # Test synchronization
        tn3270_handler._synchronize_sequence_numbers(200)

        # Test info retrieval
        info = tn3270_handler.get_sequence_number_info()
        assert "last_sent" in info

        # Test window setting
        tn3270_handler.set_sequence_window(1024)
        assert tn3270_handler._sequence_number_window == 1024

        # Test reset
        tn3270_handler.reset_sequence_numbers()
        assert tn3270_handler._last_sent_seq_number == 0

    @pytest.mark.asyncio
    async def test_negotiation_timeout_methods(self, tn3270_handler):
        """Test negotiation timeout handling."""
        # Test marking timeout
        tn3270_handler._mark_negotiation_timeout()
        assert tn3270_handler._is_negotiation_timeout() is True

        # Test cleanup performed
        tn3270_handler._mark_cleanup_performed()
        assert tn3270_handler._is_cleanup_performed() is True

        # Test deadline setting
        tn3270_handler._set_negotiation_deadline(10.0)
        assert tn3270_handler._negotiation_deadline > 0

        # Test timeout check
        result = tn3270_handler._has_negotiation_timed_out()
        assert isinstance(result, bool)

        # Test cleanup
        await tn3270_handler._perform_timeout_cleanup()

        # Test state reset
        tn3270_handler._reset_negotiation_state()
        assert tn3270_handler._negotiation_timeout_occurred is False

        # Test status
        status = tn3270_handler.get_negotiation_status()
        assert "timeout_occurred" in status

    @pytest.mark.asyncio
    async def test_state_management(self, tn3270_handler):
        """Test enhanced state management."""
        from pure3270.protocol.tn3270_handler import HandlerState

        # Test state transition recording
        await tn3270_handler._record_state_transition(HandlerState.CONNECTED, "test")

        # Test validation
        result = tn3270_handler._validate_state_transition(
            HandlerState.DISCONNECTED, HandlerState.CONNECTING
        )
        assert result is True

        # Test invalid transition
        result = tn3270_handler._validate_state_transition(
            HandlerState.CONNECTED, HandlerState.DISCONNECTED
        )
        assert result is False

        # Test state change
        await tn3270_handler._change_state(HandlerState.CONNECTING, "test transition")
        assert tn3270_handler._current_state == HandlerState.CONNECTING

        # Test state consistency validation
        await tn3270_handler._validate_state_consistency(
            HandlerState.DISCONNECTED, HandlerState.CONNECTING
        )

        # Test state change handling
        await tn3270_handler._handle_state_change(
            HandlerState.DISCONNECTED, HandlerState.CONNECTING
        )

        # Test transition timeout
        timeout = tn3270_handler._get_transition_timeout(
            HandlerState.DISCONNECTED, HandlerState.CONNECTING
        )
        assert timeout > 0

        # Test safe operation
        async def test_func():
            return "success"

        result = await tn3270_handler._safe_state_operation("test", test_func)
        assert result == "success"

        # Test state snapshot
        snapshot = tn3270_handler._create_state_snapshot()
        assert "state" in snapshot

        # Test atomic update
        await tn3270_handler._update_state_atomically(
            {"_current_state": HandlerState.CONNECTED}, "test"
        )

        # Test recovery
        await tn3270_handler._attempt_state_recovery()

        # Test recovery strategies
        result = await tn3270_handler._recovery_reconnect()
        assert isinstance(result, bool)

        result = await tn3270_handler._recovery_renegotiate()
        assert isinstance(result, bool)

        result = await tn3270_handler._recovery_reset_mode()
        assert isinstance(result, bool)

        result = await tn3270_handler._recovery_full_reset()
        assert isinstance(result, bool)

        # Test recovery conditions
        result = tn3270_handler._can_attempt_recovery()
        assert isinstance(result, bool)

        # Test failure cleanup
        await tn3270_handler._cleanup_on_failure(Exception("test"))

        # Test state info
        info = await tn3270_handler._get_state_info_async()
        assert "current_state" in info

        # Test validation enable/disable
        tn3270_handler.enable_state_validation(False)
        assert tn3270_handler._state_validation_enabled is False

        # Test history size setting
        tn3270_handler.set_max_state_history(200)
        assert tn3270_handler._max_state_history == 200

    @pytest.mark.asyncio
    async def test_event_signaling(self, tn3270_handler):
        """Test event signaling methods."""
        from pure3270.protocol.tn3270_handler import HandlerState

        # Test callback addition
        callback = MagicMock()
        tn3270_handler.add_state_change_callback(HandlerState.CONNECTED, callback)

        # Test callback removal
        tn3270_handler.remove_state_change_callback(HandlerState.CONNECTED, callback)

        # Test entry callback
        entry_callback = MagicMock()
        tn3270_handler.add_state_entry_callback(HandlerState.CONNECTED, entry_callback)

        # Test exit callback
        exit_callback = MagicMock()
        tn3270_handler.add_state_exit_callback(HandlerState.CONNECTED, exit_callback)

        # Test callback triggering
        await tn3270_handler._trigger_state_change_callbacks(
            HandlerState.DISCONNECTED, HandlerState.CONNECTED, "test"
        )

        # Test event waiting
        event = tn3270_handler.wait_for_state(HandlerState.CONNECTED)
        assert isinstance(event, asyncio.Event)

        # Test event signaling enable/disable
        tn3270_handler.enable_event_signaling(False)
        assert tn3270_handler._event_signaling_enabled is False

        # Test event retrieval
        event = tn3270_handler.get_state_change_event(HandlerState.CONNECTED)
        assert isinstance(event, asyncio.Event)

        # Test state change signaling
        await tn3270_handler._signal_state_change(
            HandlerState.DISCONNECTED, HandlerState.CONNECTED, "test"
        )

    @pytest.mark.asyncio
    async def test_timing_configuration(self, tn3270_handler):
        """Test timing configuration methods."""
        # Test timing profile configuration
        tn3270_handler.configure_timing_profile("fast")

        # Test timing metrics
        metrics = tn3270_handler.get_timing_metrics()
        assert isinstance(metrics, dict)

        # Test current profile
        profile = tn3270_handler.get_current_timing_profile()
        assert isinstance(profile, str)

        # Test monitoring enable/disable
        tn3270_handler.enable_timing_monitoring(True)

        # Test step delays
        tn3270_handler.enable_step_delays(True)

    @pytest.mark.asyncio
    async def test_data_processing_edge_cases(self, tn3270_handler):
        """Test data processing edge cases."""
        # Test VT100 sequence detection
        result = tn3270_handler._detect_vt100_sequences(b"\x1b[H")
        assert result is True

        result = tn3270_handler._detect_vt100_sequences(b"plain text")
        assert result is False

        # Test ANSI stripping
        result = tn3270_handler._strip_ansi_sequences(b"\x1b[31mred\x1b[0m")
        assert result == b"red"

        # Test fixture header length
        result = tn3270_handler._get_fixture_header_len(b"\x00\x00\x00\x00\xf5", 5)
        assert result == 4

        # Test resilient parsing
        tn3270_handler._parse_resilient(b"test data")

    @pytest.mark.asyncio
    async def test_properties_and_setters(self, tn3270_handler):
        """Test property getters and setters."""
        # Test negotiated_tn3270e property
        tn3270_handler.negotiated_tn3270e = True
        assert tn3270_handler.negotiated_tn3270e is True

        # Test lu_name property
        tn3270_handler.lu_name = "TESTLU"
        assert tn3270_handler.lu_name == "TESTLU"

        # Test screen dimensions
        assert tn3270_handler.screen_rows > 0
        assert tn3270_handler.screen_cols > 0

        # Test printer session
        tn3270_handler.is_printer_session = True
        assert tn3270_handler.is_printer_session is True

        # Test printer status
        status = tn3270_handler.printer_status
        assert status is None or isinstance(status, int)

        # Test sna session state
        state = tn3270_handler.sna_session_state
        assert isinstance(state, str)

        # Test connected property
        tn3270_handler.connected = True
        assert tn3270_handler.connected is True

    @pytest.mark.asyncio
    async def test_error_scenarios(self, tn3270_handler):
        """Test various error scenarios."""
        # Test connection with invalid parameters
        with pytest.raises(Exception):
            await tn3270_handler.connect(host="", port=0)

        # Test send_data with invalid data
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        await tn3270_handler.send_data(b"")  # Should not raise

        # Test receive_data timeout
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.reader.read.side_effect = asyncio.TimeoutError()

        with pytest.raises(asyncio.TimeoutError):
            await tn3270_handler.receive_data(timeout=0.1)

        # Test close with cleanup
        await tn3270_handler.close()  # Should not raise even if not connected

    @pytest.mark.asyncio
    async def test_concurrent_access(self, tn3270_handler):
        """Test concurrent access scenarios."""
        import asyncio

        # Test concurrent state changes - set up proper state first
        tn3270_handler._connected = True
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.writer = AsyncMock()

        async def change_state(state, reason):
            try:
                await tn3270_handler._change_state(state, reason)
            except Exception:
                pass  # Expected for invalid transitions

        from pure3270.protocol.tn3270_handler import HandlerState

        tasks = [
            change_state(HandlerState.CONNECTING, "test1"),
            change_state(HandlerState.NEGOTIATING, "test2"),
            change_state(HandlerState.CONNECTED, "test3"),
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

        # Test concurrent data operations
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.reader.read.return_value = b"test\xff\x19"

        async def send_receive():
            await tn3270_handler.send_data(b"test")
            try:
                await tn3270_handler.receive_data(timeout=0.1)
            except Exception:
                pass

        tasks = [send_receive() for _ in range(5)]
        await asyncio.gather(*tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_timeout_handling(self, tn3270_handler):
        """Test timeout handling in various operations."""
        # Test negotiation timeout
        tn3270_handler._set_negotiation_deadline(0.1)
        await asyncio.sleep(0.2)  # Wait for timeout

        assert tn3270_handler._has_negotiation_timed_out() is True

        # Test reader timeout
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.reader.read.side_effect = asyncio.TimeoutError()

        with pytest.raises(asyncio.TimeoutError):
            await tn3270_handler.receive_data(timeout=0.1)

        # Test connection timeout
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            with pytest.raises(asyncio.TimeoutError):
                await tn3270_handler.connect()

    @pytest.mark.asyncio
    async def test_mode_transitions(self, tn3270_handler):
        """Test ASCII/TN3270 mode transitions."""
        # Test set_ascii_mode
        tn3270_handler.set_ascii_mode()
        assert tn3270_handler._ascii_mode is True

        # Test mode detection in processing
        vt100_data = b"\x1b[Htest"
        result = tn3270_handler._detect_vt100_sequences(vt100_data)
