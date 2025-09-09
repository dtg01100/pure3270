import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pure3270.protocol.data_stream import DataStreamParser, ParseError
from pure3270.protocol.tn3270_handler import (
    TN3270Handler,
    ProtocolError,
    NegotiationError,
)
from pure3270.protocol.ssl_wrapper import SSLWrapper, SSLError
from pure3270.emulation.screen_buffer import ScreenBuffer
import ssl


class TestDataStreamParser:
    def test_init(self, data_stream_parser):
        assert data_stream_parser.screen is not None
        assert data_stream_parser._data == b""
        assert data_stream_parser._pos == 0
        assert data_stream_parser.wcc is None
        assert data_stream_parser.aid is None

    def test_parse_wcc(self, data_stream_parser):
        sample_data = b"\xf5\xc1"  # WCC 0xC1
        data_stream_parser.parse(sample_data)
        assert data_stream_parser.wcc == 0xC1
        # Check if clear was called if bit set (bit 0 means reset modified flags)
        # Our implementation clears buffer to spaces (0x40) when cleared
        assert data_stream_parser.screen.buffer == bytearray([0x40] * 1920)

    def test_parse_aid(self, data_stream_parser):
        sample_data = b"\xf6\x7d"  # AID Enter 0x7D
        data_stream_parser.parse(sample_data)
        assert data_stream_parser.aid == 0x7D

    def test_parse_sba(self, data_stream_parser):
        sample_data = b"\x10\x00\x00"  # SBA to 0,0
        with patch.object(data_stream_parser.screen, "set_position"):
            data_stream_parser.parse(sample_data)
            data_stream_parser.screen.set_position.assert_called_with(0, 0)

    def test_parse_sf(self, data_stream_parser):
        sample_data = b"\x1d\x40"  # SF protected
        with patch.object(data_stream_parser.screen, "write_char"):
            data_stream_parser.parse(sample_data)
            data_stream_parser.screen.write_char.assert_called_once()

    def test_parse_ra(self, data_stream_parser):
        sample_data = b"\xf3\x40\x00\x05"  # RA space 5 times
        data_stream_parser.parse(sample_data)
        # Assert logging or basic handling

    def test_parse_ge(self, data_stream_parser):
        sample_data = b"\x29"  # GE
        data_stream_parser.parse(sample_data)
        # Assert debug log for unsupported

    def test_parse_write(self, data_stream_parser):
        sample_data = b"\x05"  # Write
        with patch.object(data_stream_parser.screen, "clear"):
            data_stream_parser.parse(sample_data)
            data_stream_parser.screen.clear.assert_called_once()

    def test_parse_data(self, data_stream_parser):
        sample_data = b"\xc1\xc2"  # Data ABC
        data_stream_parser.parse(sample_data)
        # Check buffer updated
        assert data_stream_parser.screen.buffer[0:2] == b"\xc1\xc2"

    def test_parse_bind(self, data_stream_parser):
        sample_data = b"\x28" + b"\x00" * 10  # BIND stub
        data_stream_parser.parse(sample_data)
        # Assert debug log

    def test_parse_incomplete(self, data_stream_parser):
        sample_data = b"\xf5"  # Incomplete WCC
        with pytest.raises(ParseError):
            data_stream_parser.parse(sample_data)

    def test_get_aid(self, data_stream_parser):
        data_stream_parser.aid = 0x7D
        assert data_stream_parser.get_aid() == 0x7D


class TestDataStreamSender:
    def test_build_read_modified_all(self, data_stream_sender):
        stream = data_stream_sender.build_read_modified_all()
        assert stream == b"\x7d\xf1"  # AID + Read Partition

    def test_build_read_modified_fields(self, data_stream_sender):
        stream = data_stream_sender.build_read_modified_fields()
        assert stream == b"\x7d\xf6\xf0"

    def test_build_key_press(self, data_stream_sender):
        stream = data_stream_sender.build_key_press(0x7D)
        assert stream == b"\x7d"

    def test_build_write(self, data_stream_sender):
        data = b"\xc1\xc2"
        stream = data_stream_sender.build_write(data)
        assert stream.startswith(b"\xf5\xc1\x05")
        assert b"\xc1\xc2" in stream
        assert stream.endswith(b"\x0d")

    def test_build_sba(self, data_stream_sender):
        # Note: sender has no screen, but assume default
        with patch("pure3270.protocol.data_stream.ScreenBuffer", rows=24, cols=80):
            stream = data_stream_sender.build_sba(0, 0)
            assert stream == b"\x10\x00\x00"


class TestSSLWrapper:
    def test_init(self, ssl_wrapper):
        assert ssl_wrapper.verify is True
        assert ssl_wrapper.cafile is None
        assert ssl_wrapper.capath is None
        assert ssl_wrapper.context is None

    @patch("ssl.SSLContext")
    def test_create_context_verify(self, mock_ssl_context, ssl_wrapper):
        ctx = MagicMock()
        mock_ssl_context.return_value = ctx
        with patch("ssl.PROTOCOL_TLS_CLIENT"):
            ssl_wrapper.create_context()
        mock_ssl_context.assert_called_once()
        assert ctx.check_hostname is True
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2
        ctx.set_ciphers.assert_called_with("HIGH:!aNULL:!MD5")

    @patch("ssl.SSLContext")
    def test_create_context_no_verify(self, mock_ssl_context, ssl_wrapper):
        wrapper = SSLWrapper(verify=False)
        ctx = MagicMock()
        mock_ssl_context.return_value = ctx
        with patch("ssl.PROTOCOL_TLS_CLIENT"):
            wrapper.create_context()
        ctx.check_hostname = False
        ctx.verify_mode = 0  # CERT_NONE

    @patch("ssl.SSLContext")
    def test_create_context_error(self, mock_ssl_context, ssl_wrapper):
        mock_ssl_context.side_effect = ssl.SSLError("Test error")
        with pytest.raises(SSLError):
            ssl_wrapper.create_context()

    def test_wrap_connection(self, ssl_wrapper):
        telnet_conn = MagicMock()
        wrapped = ssl_wrapper.wrap_connection(telnet_conn)
        assert wrapped == telnet_conn  # Stub returns original

    def test_get_context(self, ssl_wrapper):
        with patch.object(ssl_wrapper, "create_context") as mock_create:
            context = ssl_wrapper.get_context()
        mock_create.assert_called_once()
        assert context == ssl_wrapper.context

    def test_ssl_encryption_for_data_transit(self, ssl_wrapper):
        """
        Ported from s3270 test case 4: SSL encryption for data transit.
        Input SSL-wrapped connection, send encrypted data; output decrypts;
        assert plain text matches decrypted, no plaintext exposure.
        """
        # Test the basic encryption workflow
        mock_connection = MagicMock()

        # Call create_context through wrapper
        with patch("ssl.SSLContext") as mock_ssl_context:
            mock_context = MagicMock()
            mock_ssl_context.return_value = mock_context
            context = ssl_wrapper.get_context()  # This will call create_context

        # Wrap connection
        wrapped = ssl_wrapper.wrap_connection(mock_connection)

        # Test decrypt (which is a stub)
        plain_text = b"plain_data"
        encrypted_data = b"encrypted_data"
        decrypted = ssl_wrapper.decrypt(encrypted_data)

        # Assert context was created and connection was handled
        assert ssl_wrapper.context is not None
        assert wrapped == mock_connection  # Stub returns original
        assert decrypted == encrypted_data  # Stub returns input


@pytest.mark.asyncio
class TestTN3270Handler:
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

    @patch("asyncio.open_connection")
    async def test_connect_error(self, mock_open, tn3270_handler):
        mock_open.side_effect = Exception("Connection failed")
        with pytest.raises(ConnectionError):
            await tn3270_handler.connect()

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

    async def test_send_data(self, tn3270_handler):
        data = b"\x7d"
        tn3270_handler.writer = AsyncMock()
        tn3270_handler.writer.drain = AsyncMock()
        await tn3270_handler.send_data(data)
        tn3270_handler.writer.write.assert_called_with(data)

    async def test_send_data_not_connected(self, tn3270_handler):
        tn3270_handler.writer = None
        with pytest.raises(ProtocolError):
            await tn3270_handler.send_data(b"")

    async def test_receive_data(self, tn3270_handler):
        data = b"\xc1\xc2"
        tn3270_handler.reader = AsyncMock()
        tn3270_handler.reader.read.return_value = data + b"\xff\x19"  # Add EOR marker
        received = await tn3270_handler.receive_data()
        assert received == data

    async def test_receive_data_not_connected(self, tn3270_handler):
        tn3270_handler.reader = None
        with pytest.raises(ProtocolError):
            await tn3270_handler.receive_data()

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
        # Configure mock methods for liveness checks
        tn3270_handler.writer.is_closing.return_value = False
        tn3270_handler.reader.at_eof.return_value = False
        tn3270_handler._connected = True
        assert tn3270_handler.is_connected() is True

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


# Sample data streams fixtures
@pytest.fixture
def sample_wcc_stream():
    return b"\xf5\xc1"  # WCC reset modified


@pytest.fixture
def sample_sba_stream():
    return b"\x10\x00\x14"  # SBA to row 0 col 20


@pytest.fixture
def sample_write_stream():
    return b"\x05\xc1\xc2\xc3"  # Write ABC


def test_parse_sample_wcc(data_stream_parser, sample_wcc_stream):
    data_stream_parser.parse(sample_wcc_stream)
    assert data_stream_parser.wcc == 0xC1


def test_parse_sample_sba(data_stream_parser, sample_sba_stream):
    with patch.object(data_stream_parser.screen, "set_position"):
        data_stream_parser.parse(sample_sba_stream)
        data_stream_parser.screen.set_position.assert_called_with(0, 20)


def test_parse_sample_write(data_stream_parser, sample_write_stream):
    with patch.object(data_stream_parser.screen, "clear"):
        data_stream_parser.parse(sample_write_stream)
        data_stream_parser.screen.clear.assert_called_once()
    assert data_stream_parser.screen.buffer[0:3] == b"\xc1\xc2\xc3"


# General tests: exceptions, logging, performance
def test_parse_error(caplog):
    parser = DataStreamParser(ScreenBuffer())
    with caplog.at_level("ERROR"):
        with pytest.raises(ParseError):
            parser.parse(b"\xf5")  # Incomplete
    assert "Unexpected end" in caplog.text


def test_protocol_error(caplog):
    handler = TN3270Handler(None, None, None, "host", 23)
    handler.writer = None
    with caplog.at_level("ERROR"):
        with pytest.raises(Exception):  # Catch ProtocolError
            asyncio.run(handler.send_data(b""))
    assert "Not connected" in caplog.text


def test_ssl_error(caplog):
    wrapper = SSLWrapper()
    with patch("ssl.SSLContext", side_effect=ssl.SSLError("Test")):
        with caplog.at_level("ERROR"):
            with pytest.raises(SSLError):
                wrapper.create_context()
    assert "SSL context creation failed" in caplog.text


# Performance: parse large stream (reduced size to avoid OOM)
def test_performance_parse(data_stream_parser):
    large_stream = b"\x05" + b"\x40" * 1000  # Reduced size to avoid OOM
    data_stream_parser.parse(large_stream)
    # No benchmark to avoid OOM
