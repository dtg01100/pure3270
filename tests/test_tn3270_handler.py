import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pure3270.protocol.tn3270_handler import (
    TN3270Handler,
    ProtocolError,
    NegotiationError,
)
from pure3270.protocol.ssl_wrapper import SSLWrapper


class TestTN3270Handler:
    @pytest.mark.asyncio
    @patch("asyncio.open_connection")
    async def test_connect_non_ssl(self, mock_open, tn3270_handler):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_reader.read.return_value = b""  # Initial data
        mock_open.return_value = (mock_reader, mock_writer)
        # Mock the negotiator's _read_iac method to return valid IAC data
        with patch.object(
            tn3270_handler.negotiator, "_read_iac", return_value=b"\xff\xfd\x18"
        ):
            with patch.object(tn3270_handler, "_negotiate_tn3270"):
                await tn3270_handler.connect()
        mock_open.assert_called_with(tn3270_handler.host, tn3270_handler.port, ssl=None)
        assert tn3270_handler.reader == mock_reader
        assert tn3270_handler.writer == mock_writer

    @pytest.mark.asyncio
    @patch("asyncio.open_connection")
    async def test_connect_ssl(self, mock_open, tn3270_handler):
        ssl_wrapper = SSLWrapper()
        ssl_context = ssl_wrapper.get_context()
        tn3270_handler.ssl_context = ssl_context
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_reader.read.return_value = b""  # Initial data
        mock_open.return_value = (mock_reader, mock_writer)
        # Mock the negotiator's _read_iac method to return valid IAC data
        with patch.object(
            tn3270_handler.negotiator, "_read_iac", return_value=b"\xff\xfd\x18"
        ):
            with patch.object(tn3270_handler, "_negotiate_tn3270"):
                await tn3270_handler.connect()
        mock_open.assert_called_with(
            tn3270_handler.host, tn3270_handler.port, ssl=ssl_context
        )

    @pytest.mark.asyncio
    @patch("asyncio.open_connection")
    async def test_connect_error(self, mock_open, tn3270_handler):
        mock_open.side_effect = Exception("Connection failed")
        with pytest.raises(ConnectionError):
            await tn3270_handler.connect()

    @pytest.mark.asyncio
    async def test_negotiate_tn3270_success(self, tn3270_handler):
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        # Update negotiator's writer as well
        tn3270_handler.negotiator.writer = tn3270_handler.writer

        # Mock the negotiation sequence
        tn3270_handler.reader.read.side_effect = [
            b"\xff\xfb\x24",  # WILL TN3270E
            b"\xff\xfa\x18\x00\x02IBM-3279-4-E\xff\xf0",  # DEVICE_TYPE IS
            b"\xff\xfa\x18\x01\x02\x15\xff\xf0",  # FUNCTIONS IS
            b"\xff\xfb\x19",  # WILL EOR
        ]

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
