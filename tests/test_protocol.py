import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, MagicMock
from pure3270.protocol.data_stream import DataStreamParser, DataStreamSender, ParseError
from pure3270.protocol.ssl_wrapper import SSLWrapper, SSLError
from pure3270.protocol.tn3270_handler import TN3270Handler, ProtocolError, NegotiationError
from pure3270.emulation.screen_buffer import ScreenBuffer


@pytest.fixture
def screen_buffer():
    return ScreenBuffer()


@pytest.fixture
def data_stream_parser(screen_buffer):
    return DataStreamParser(screen_buffer)


@pytest.fixture
def data_stream_sender():
    return DataStreamSender()


@pytest.fixture
def ssl_wrapper():
    return SSLWrapper(verify=True)


@pytest.mark.asyncio
class TestDataStreamParser:
    def test_init(self, data_stream_parser):
        assert data_stream_parser.screen is not None
        assert data_stream_parser._data == b""
        assert data_stream_parser._pos == 0
        assert data_stream_parser.wcc is None
        assert data_stream_parser.aid is None

    def test_parse_wcc(self, data_stream_parser):
        sample_data = b'\xF5\xC1'  # WCC 0xC1
        data_stream_parser.parse(sample_data)
        assert data_stream_parser.wcc == 0xC1
        # Check if clear was called if bit set
        assert data_stream_parser.screen.buffer == bytearray(1920)  # cleared if bit 0

    def test_parse_aid(self, data_stream_parser):
        sample_data = b'\xF6\x7D'  # AID Enter 0x7D
        data_stream_parser.parse(sample_data)
        assert data_stream_parser.aid == 0x7D

    def test_parse_sba(self, data_stream_parser):
        sample_data = b'\x10\x00\x00'  # SBA to 0,0
        with patch.object(data_stream_parser.screen, 'set_position'):
            data_stream_parser.parse(sample_data)
        data_stream_parser.screen.set_position.assert_called_with(0, 0)

    def test_parse_sf(self, data_stream_parser):
        sample_data = b'\x1D\x40'  # SF protected
        with patch.object(data_stream_parser.screen, 'write_char'):
            data_stream_parser.parse(sample_data)
        data_stream_parser.screen.write_char.assert_called_once()

    def test_parse_ra(self, data_stream_parser):
        sample_data = b'\xF3\x40\x00\x05'  # RA space 5 times
        data_stream_parser.parse(sample_data)
        # Assert logging or basic handling

    def test_parse_ge(self, data_stream_parser):
        sample_data = b'\x29'  # GE
        data_stream_parser.parse(sample_data)
        # Assert debug log for unsupported

    def test_parse_write(self, data_stream_parser):
        sample_data = b'\x05'  # Write
        with patch.object(data_stream_parser.screen, 'clear'):
            data_stream_parser.parse(sample_data)
        data_stream_parser.screen.clear.assert_called_once()

    def test_parse_data(self, data_stream_parser):
        sample_data = b'\xC1\xC2'  # Data ABC
        data_stream_parser.parse(sample_data)
        # Check buffer updated
        assert data_stream_parser.screen.buffer[0:2] == b'\xC1\xC2'

    def test_parse_bind(self, data_stream_parser):
        sample_data = b'\x28' + b'\x00' * 10  # BIND stub
        data_stream_parser.parse(sample_data)
        # Assert debug log

    def test_parse_incomplete(self, data_stream_parser):
        sample_data = b'\xF5'  # Incomplete WCC
        with pytest.raises(ParseError):
            data_stream_parser.parse(sample_data)

    def test_get_aid(self, data_stream_parser):
        data_stream_parser.aid = 0x7D
        assert data_stream_parser.get_aid() == 0x7D


class TestDataStreamSender:
    def test_build_read_modified_all(self, data_stream_sender):
        stream = data_stream_sender.build_read_modified_all()
        assert stream == b'\x7D\xF1'  # AID + Read Partition

    def test_build_read_modified_fields(self, data_stream_sender):
        stream = data_stream_sender.build_read_modified_fields()
        assert stream == b'\x7D\xF6\xF0'

    def test_build_key_press(self, data_stream_sender):
        stream = data_stream_sender.build_key_press(0x7D)
        assert stream == b'\x7D'

    def test_build_write(self, data_stream_sender):
        data = b'\xC1\xC2'
        stream = data_stream_sender.build_write(data)
        assert stream.startswith(b'\xF5\xC1\x05')
        assert b'\xC1\xC2' in stream
        assert stream.endswith(b'\x0D')

    def test_build_sba(self, data_stream_sender):
        # Note: sender has no screen, but assume default
        with patch('pure3270.protocol.data_stream.ScreenBuffer', rows=24, cols=80):
            stream = data_stream_sender.build_sba(0, 0)
            assert stream == b'\x10\x00\x00'


@pytest.mark.asyncio
class TestSSLWrapper:
    def test_init(self, ssl_wrapper):
        assert ssl_wrapper.verify is True
        assert ssl_wrapper.cafile is None
        assert ssl_wrapper.capath is None
        assert ssl_wrapper.context is None

    @patch('ssl.SSLContext')
    def test_create_context_verify(self, mock_ssl_context, ssl_wrapper):
        ctx = MagicMock()
        mock_ssl_context.return_value = ctx
        with patch('ssl.PROTOCOL_TLS_CLIENT'):
            ssl_wrapper.create_context()
        mock_ssl_context.assert_called_once()
        ctx.check_hostname = True
        ctx.verify_mode = 2  # CERT_REQUIRED
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.set_ciphers.assert_called_with("HIGH:!aNULL:!MD5")

    @patch('ssl.SSLContext')
    def test_create_context_no_verify(self, mock_ssl_context, ssl_wrapper):
        wrapper = SSLWrapper(verify=False)
        ctx = MagicMock()
        mock_ssl_context.return_value = ctx
        with patch('ssl.PROTOCOL_TLS_CLIENT'):
            wrapper.create_context()
        ctx.check_hostname = False
        ctx.verify_mode = 0  # CERT_NONE

    @patch('ssl.SSLContext')
    def test_create_context_error(self, mock_ssl_context, ssl_wrapper):
        mock_ssl_context.side_effect = ssl.SSLError("Test error")
        with pytest.raises(SSLError):
            ssl_wrapper.create_context()

    def test_wrap_connection(self, ssl_wrapper):
        telnet_conn = MagicMock()
        wrapped = ssl_wrapper.wrap_connection(telnet_conn)
        assert wrapped == telnet_conn  # Stub returns original

    def test_get_context(self, ssl_wrapper):
        with patch.object(ssl_wrapper, 'create_context') as mock_create:
            context = ssl_wrapper.get_context()
        mock_create.assert_called_once()
        assert context == ssl_wrapper.context


@pytest.mark.asyncio
class TestTN3270Handler:
    @patch('telnetlib3.open_connection')
    async def test_connect_non_ssl(self, mock_open, tn3270_handler):
        mock_telnet = AsyncMock()
        mock_open.return_value = mock_telnet
        with patch.object(tn3270_handler, '_negotiate_tn3270'):
            await tn3270_handler.connect()
        mock_open.assert_called_with(tn3270_handler.host, tn3270_handler.port)
        assert tn3270_handler.telnet == mock_telnet

    @patch('telnetlib3.open_connection')
    async def test_connect_ssl(self, mock_open, tn3270_handler):
        ssl_wrapper = SSLWrapper()
        with patch.object(ssl_wrapper, 'get_context', return_value=MagicMock()):
            tn3270_handler.ssl_context = ssl_wrapper.get_context()
            mock_telnet = AsyncMock()
            mock_open.return_value = mock_telnet
            with patch.object(tn3270_handler, '_negotiate_tn3270'):
                await tn3270_handler.connect()
        mock_open.assert_called_with(tn3270_handler.host, tn3270_handler.port, ssl=ssl_wrapper.get_context())

    @patch('telnetlib3.open_connection')
    async def test_connect_error(self, mock_open, tn3270_handler):
        mock_open.side_effect = Exception("Connection failed")
        with pytest.raises(ConnectionError):
            await tn3270_handler.connect()

    @patch.object(TN3270Handler, 'telnet')
    async def test_negotiate_tn3270_success(self, mock_telnet, tn3270_handler):
        mock_telnet.request_negotiate = AsyncMock()
        mock_telnet.read_until.return_value = b'\xff\xfb\x27'  # WILL TN3270
        mock_telnet.read_until.return_value = b'\xff\xfb\x24'  # WILL TN3270E
        await tn3270_handler._negotiate_tn3270()
        assert tn3270_handler.negotiated_tn3270e is True

    @patch.object(TN3270Handler, 'telnet')
    async def test_negotiate_tn3270_fail(self, mock_telnet, tn3270_handler):
        mock_telnet.read_until.return_value = b''  # No WILL
        with pytest.raises(NegotiationError):
            await tn3270_handler._negotiate_tn3270()

    @patch.object(TN3270Handler, 'telnet')
    async def test_send_data(self, mock_telnet, tn3270_handler):
        data = b'\x7D'
        mock_telnet.write = AsyncMock()
        await tn3270_handler.send_data(data)
        mock_telnet.write.assert_called_with(data)

    @patch.object(TN3270Handler, 'telnet')
    async def test_send_data_not_connected(self, mock_telnet, tn3270_handler):
        tn3270_handler.telnet = None
        with pytest.raises(ProtocolError):
            await tn3270_handler.send_data(b'')

    @patch.object(TN3270Handler, 'telnet')
    async def test_receive_data(self, mock_telnet, tn3270_handler):
        data = b'\xC1\xC2'
        mock_telnet.read_until.return_value = data
        received = await tn3270_handler.receive_data()
        assert received == data

    @patch.object(TN3270Handler, 'telnet')
    async def test_receive_data_not_connected(self, mock_telnet, tn3270_handler):
        tn3270_handler.telnet = None
        with pytest.raises(ProtocolError):
            await tn3270_handler.receive_data()

    @patch.object(TN3270Handler, 'telnet')
    async def test_close(self, mock_telnet, tn3270_handler):
        mock_telnet.close = AsyncMock()
        await tn3270_handler.close()
        mock_telnet.close.assert_called_once()
        assert tn3270_handler.telnet is None

    def test_is_connected(self, tn3270_handler):
        assert tn3270_handler.is_connected() is False
        tn3270_handler.telnet = MagicMock()
        assert tn3270_handler.is_connected() is True


# Sample data streams fixtures
@pytest.fixture
def sample_wcc_stream():
    return b'\xF5\xC1'  # WCC reset modified


@pytest.fixture
def sample_sba_stream():
    return b'\x10\x00\x14'  # SBA to row 0 col 20


@pytest.fixture
def sample_write_stream():
    return b'\x05\xC1\xC2\xC3'  # Write ABC


def test_parse_sample_wcc(data_stream_parser, sample_wcc_stream):
    data_stream_parser.parse(sample_wcc_stream)
    assert data_stream_parser.wcc == 0xC1


def test_parse_sample_sba(data_stream_parser, sample_sba_stream):
    with patch.object(data_stream_parser.screen, 'set_position'):
        data_stream_parser.parse(sample_sba_stream)
    data_stream_parser.screen.set_position.assert_called_with(0, 20)


def test_parse_sample_write(data_stream_parser, sample_write_stream):
    with patch.object(data_stream_parser.screen, 'clear'):
        data_stream_parser.parse(sample_write_stream)
    data_stream_parser.screen.clear.assert_called_once()
    assert data_stream_parser.screen.buffer[0:3] == b'\xC1\xC2\xC3'


# General tests: exceptions, logging, performance
def test_parse_error(caplog):
    parser = DataStreamParser(ScreenBuffer())
    with caplog.at_level('ERROR'):
        with pytest.raises(ParseError):
            parser.parse(b'\xF5')  # Incomplete
    assert 'Unexpected end' in caplog.text


def test_protocol_error(caplog):
    handler = TN3270Handler('host', 23)
    handler.telnet = None
    with caplog.at_level('ERROR'):
        asyncio.run(handler.send_data(b''))
    assert 'Not connected' in caplog.text


def test_ssl_error(caplog):
    wrapper = SSLWrapper()
    with patch('ssl.SSLContext', side_effect=ssl.SSLError('Test')):
        with caplog.at_level('ERROR'):
            with pytest.raises(SSLError):
                wrapper.create_context()
    assert 'SSL context creation failed' in caplog.text


# Performance: parse large stream
def test_performance_parse(benchmark, data_stream_parser):
    large_stream = b'\x05' + b'\x40' * 10000  # Large write
    def parse_large():
        data_stream_parser.parse(large_stream)
    benchmark(parse_large)
    # Benchmark ensures efficient handling