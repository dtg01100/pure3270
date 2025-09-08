import pytest
import logging
import pure3270.session
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from contextlib import asynccontextmanager

from pure3270.session import Session, AsyncSession, Pure3270Error, SessionError
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.tn3270_handler import TN3270Handler, NegotiationError
from pure3270.protocol.data_stream import DataStreamParser, DataStreamSender
from pure3270.protocol.ssl_wrapper import SSLWrapper

@pytest.mark.asyncio
class TestAsyncSession:
    @pytest.mark.asyncio
    async def test_init_force_3270(self):
        """Test initialization with force_3270=True."""
        session = AsyncSession(rows=25, cols=85, force_3270=True)
        assert session.force_3270 is True
        assert session.screen.rows == 25
        assert session.screen.cols == 85

    def test_init(self, async_session):
        assert isinstance(async_session.screen, ScreenBuffer)
        assert isinstance(async_session.parser, DataStreamParser)
        assert isinstance(async_session.sender, DataStreamSender)
        assert async_session.handler is None
        assert async_session._connected is False

    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.SSLWrapper')
    async def test_connect_non_ssl(self, mock_ssl, mock_handler, async_session):
        mock_handler_instance = AsyncMock()
        mock_handler.return_value = mock_handler_instance
        mock_handler_instance.connect = AsyncMock()
        await async_session.connect('host', 23, ssl=False)
        mock_handler.assert_called_with('host', 23, None)
        mock_handler_instance.connect.assert_called_once()
        assert async_session._connected is True

    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.SSLWrapper')
    async def test_connect_ssl(self, mock_ssl, mock_handler, async_session):
        mock_ssl_instance = MagicMock()
        mock_ssl.return_value = mock_ssl_instance
        mock_ssl_instance.get_context.return_value = 'ssl_context'
        mock_handler_instance = AsyncMock()
        mock_handler.return_value = mock_handler_instance
        mock_handler_instance.connect = AsyncMock()
        await async_session.connect('host', 992, ssl=True)
        mock_ssl.assert_called_with(verify=True)
        mock_handler.assert_called_with('host', 992, 'ssl_context')
        mock_handler_instance.connect.assert_called_once()
        assert async_session._connected is True

    @patch('pure3270.session.TN3270Handler')
    async def test_connect_error(self, mock_handler, async_session):
        mock_handler.side_effect = Exception('Connect failed')
        with pytest.raises(SessionError):
            await async_session.connect('host', 23)
        assert async_session._connected is False

    @patch('pure3270.session.TN3270Handler')
    async def test_send_key(self, mock_handler, async_session):
        async_session.handler = mock_handler.return_value = AsyncMock()
        mock_handler.return_value.send_data = AsyncMock()
        async_session._connected = True
        await async_session.send('key Enter')
        mock_handler.return_value.send_data.assert_called_once()

    @patch('pure3270.session.TN3270Handler')
    async def test_send_string(self, mock_handler, async_session):
        async_session.handler = mock_handler.return_value = AsyncMock()
        mock_handler.return_value.send_data = AsyncMock()
        async_session._connected = True
        await async_session.send('String(hello)')
        mock_handler.return_value.send_data.assert_called_once()

    @patch('pure3270.session.TN3270Handler')
    async def test_send_not_connected(self, mock_handler, async_session):
        async_session._connected = False
        with pytest.raises(SessionError):
            await async_session.send('key Enter')

    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.DataStreamParser')
    async def test_read(self, mock_parser, mock_handler, async_session):
        async_session.handler = mock_handler.return_value = AsyncMock()
        mock_handler.return_value.receive_data.return_value = b'\x05\xC1'
        mock_parser.return_value.parse = MagicMock()
        async_session._connected = True
        async_session.tn3270_mode = True  # Enable TN3270 mode to call parse
        text = await async_session.read()
        mock_handler.return_value.receive_data.assert_called_once()
        mock_parser.return_value.parse.assert_called_once()
        assert text == ''  # Default to_text empty

    @patch('pure3270.session.TN3270Handler')
    async def test_read_not_connected(self, mock_handler, async_session):
        async_session._connected = False
        with pytest.raises(SessionError):
            await async_session.read()

    @patch('pure3270.session.TN3270Handler')
    async def test_macro(self, mock_handler, async_session):
        async_session.handler = mock_handler.return_value = AsyncMock()
        async_session.send = AsyncMock()
        async_session._connected = True
        await async_session.macro(['key Enter', 'key PF3'])
        assert async_session.send.call_count == 2

    @patch('pure3270.session.TN3270Handler')
    async def test_close(self, mock_handler, async_session):
        async_session.handler = mock_handler.return_value = AsyncMock()
        mock_handler.return_value.close = AsyncMock()
        await async_session.close()
        mock_handler.return_value.close.assert_called_once()
        assert async_session._connected is False

    def test_connected_property(self, async_session):
        assert async_session.connected is False
        async_session._connected = True
        assert async_session.connected is True

    async def test_managed_context(self, async_session):
        async_session._connected = True
        async_session.close = AsyncMock()
        async with async_session.managed():
            assert async_session._connected is True
        async_session.close.assert_called_once()

    async def test_managed_not_connected(self, async_session):
        with pytest.raises(SessionError):
            async with async_session.managed():
                pass

    async def test_pf_key_processing_with_aid(self, async_session):
        """
        Ported from s3270 test case 5: PF key processing with AID.
        Input PF key (e.g., PF3 AID 0x6D); output updates screen, sets AID;
        assert correct AID, field advance.
        """
        # Mock handler and sender
        mock_handler = AsyncMock()
        mock_handler.send_data = AsyncMock()
        async_session.handler = mock_handler
        async_session._connected = True
        async_session.tn3270_mode = True  # Enable TN3270 mode for correct AID mapping

        # Mock parser to set AID after send (simulate response)
        mock_parser = MagicMock()
        mock_parser.aid = 0x6D
        async_session.parser = mock_parser

        # Send PF3 key
        await async_session.send('key PF3')

        # Assert send_data called with correct AID (0x6D for PF3 as per case)
        mock_handler.send_data.assert_called_once()
        data = mock_handler.send_data.call_args[0][0]
        assert data == b'\x6D'  # AID 0x6D

        # Assert AID set correctly in parser
        assert async_session.parser.aid == 0x6D


    @patch('pure3270.session.asyncio.open_connection')
    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.SSLWrapper')
    async def test_connect_force_3270_non_ssl(self, mock_ssl, mock_handler, mock_open, async_session):
        """Test connect with force_3270, non-SSL: skips negotiation, sets modes."""
        async_session.force_3270 = True
        mock_writer = AsyncMock()
        mock_reader = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)
        mock_handler_instance = AsyncMock()
        mock_handler.return_value = mock_handler_instance
        mock_handler_instance.host = 'host'
        mock_handler_instance.port = 23
        mock_handler_instance.ssl_context = None

        await async_session.connect('host', 23, ssl=False)

        mock_open.assert_called_once_with(ANY, ANY)
        assert async_session.tn3270_mode is True
        assert async_session.tn3270e_mode is True
        assert async_session.lu_name == "DEFAULT"
        assert async_session._connected is True

    @patch('pure3270.session.asyncio.open_connection')
    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.SSLWrapper')
    async def test_connect_force_3270_ssl(self, mock_ssl, mock_handler, mock_open, async_session):
        """Test connect with force_3270, SSL."""
        async_session.force_3270 = True
        mock_writer = AsyncMock()
        mock_reader = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)
        mock_ssl_instance = MagicMock()
        mock_ssl.return_value = mock_ssl_instance
        mock_ssl_instance.get_context.return_value = 'ssl_context'
        mock_handler_instance = AsyncMock()
        mock_handler.return_value = mock_handler_instance
        mock_handler_instance.host = 'host'
        mock_handler_instance.port = 992
        mock_handler_instance.ssl_context = 'ssl_context'

        await async_session.connect('host', 992, ssl=True)

        mock_open.assert_called_once_with(ANY, ANY, ssl='ssl_context')
        assert async_session.tn3270_mode is True
        assert async_session.tn3270e_mode is True
        assert async_session.lu_name == "DEFAULT"
        assert async_session._connected is True

    @patch('pure3270.session.TN3270Handler')
    async def test_connect_negotiation_error_fallback(self, mock_handler, async_session):
        """Test connect with NegotiationError: fallback to ASCII, connected=True."""
        mock_handler_instance = AsyncMock()
        mock_handler.return_value = mock_handler_instance
        mock_handler_instance.connect.side_effect = NegotiationError('Negotiation failed')

        await async_session.connect('host', 23, ssl=False)

        mock_handler_instance.connect.assert_called_once()
        assert async_session.tn3270_mode is False
        assert async_session._connected is True

    @patch('pure3270.session.TN3270Handler')
    async def test_connect_lu_name_resize(self, mock_handler, async_session):
        """Test connect with LU name and screen resize."""
        mock_handler_instance = AsyncMock()
        mock_handler.return_value = mock_handler_instance
        mock_handler_instance.connect = AsyncMock()
        mock_handler_instance.supports_tn3270 = True
        mock_handler_instance.negotiated_tn3270e = True
        mock_handler_instance.lu_name = "TESTLU"
        mock_handler_instance.screen_rows = 32
        mock_handler_instance.screen_cols = 160

        await async_session.connect('host', 23, ssl=False)

        assert async_session.tn3270_mode is True
        assert async_session.tn3270e_mode is True
        assert async_session.lu_name == "TESTLU"
        assert async_session.screen.rows == 32
        assert async_session.screen.cols == 160

    @patch('pure3270.session.TN3270Handler')
    async def test_send_ascii_key(self, mock_handler, async_session):
        """Test send in non-TN3270 mode: ASCII key mapping."""
        mock_handler_instance = AsyncMock()
        async_session.handler = mock_handler_instance
        mock_handler_instance.send_data = AsyncMock()
        async_session._connected = True
        async_session.tn3270_mode = False

        await async_session.send('key enter')

        mock_handler_instance.send_data.assert_called_once_with(b'\r')

    @patch('pure3270.session.TN3270Handler')
    async def test_send_ascii_string(self, mock_handler, async_session):
        """Test send string in ASCII mode."""
        mock_handler_instance = AsyncMock()
        async_session.handler = mock_handler_instance
        mock_handler_instance.send_data = AsyncMock()
        async_session._connected = True
        async_session.tn3270_mode = False

        await async_session.send('String(hello)')

        mock_handler_instance.send_data.assert_called_once_with(b'hello')

    @patch('pure3270.session.TN3270Handler')
    async def test_send_unknown_command(self, mock_handler, async_session):
        """Test send unknown command in ASCII mode."""
        mock_handler_instance = AsyncMock()
        async_session.handler = mock_handler_instance
        mock_handler_instance.send_data = AsyncMock()
        async_session._connected = True
        async_session.tn3270_mode = False

        await async_session.send('unknown')

        mock_handler_instance.send_data.assert_called_once_with(b'unknown')

    @patch('pure3270.session.TN3270Handler')
    async def test_read_ascii_mode(self, mock_handler, async_session):
        """Test read in non-TN3270 mode: strip IAC, format to screen."""
        mock_handler_instance = AsyncMock()
        async_session.handler = mock_handler_instance
        mock_handler_instance.receive_data.return_value = b'IAC\xFF EOR\x19 text\x0c'
        async_session._connected = True
        async_session.tn3270_mode = False

        text = await async_session.read()

        # Assert stripped and formatted (partial example)
        assert 'text' in text
        mock_handler_instance.receive_data.assert_called_once_with(timeout=10.0)

    @patch('pure3270.session.TN3270Handler')
    @patch('pure3270.session.DataStreamParser')
    async def test_read_parse_exception_fallback(self, mock_parser, mock_handler, async_session):
        """Test read with DataStreamParser exception: fallback to raw decode."""
        mock_handler_instance = AsyncMock()
        async_session.handler = mock_handler_instance
        mock_handler_instance.receive_data.return_value = b'data'
        async_session._connected = True
        async_session.tn3270_mode = True
        async_session.tn3270e_mode = True
        mock_parser.side_effect = Exception('Parse failed')

        text = await async_session.read()

        # Fallback should return decoded 'data'
        assert text == 'data'
        mock_handler_instance.receive_data.assert_called_once_with(timeout=10.0)

    @patch('pure3270.session.TN3270Handler')
    async def test_strip_telnet_iac_sb_se(self, mock_handler, async_session):
        """Test _strip_telnet_iac with SB/SE subnegotiation."""
        async_session._connected = True
        async_session.tn3270_mode = False
        data = b'\xFF\xFA sub\xF0text'
        stripped = async_session._strip_telnet_iac(data)
        assert stripped == b'text'

    @patch('pure3270.session.TN3270Handler')
    async def test_strip_telnet_iac_will_wont_do_dont(self, mock_handler, async_session):
        """Test _strip_telnet_iac with WILL/WONT/DO/DONT."""
        async_session._connected = True
        async_session.tn3270_mode = False
        data = b'\xFF\xFB\x01\xFF\xFC\x02\xFF\xFD\x03\xFF\xFE\x04text'
        stripped = async_session._strip_telnet_iac(data)
        assert stripped == b'text'

    @patch('pure3270.session.TN3270Handler')
    async def test_strip_telnet_iac_eor_ga(self, mock_handler, async_session):
        """Test _strip_telnet_iac with EOR/GA."""
        async_session._connected = True
        async_session.tn3270_mode = False
        data = b'\xFF\x19\xFF\xF9text'
        stripped = async_session._strip_telnet_iac(data)
        assert stripped == b'text'

    @patch('pure3270.session.TN3270Handler')
    async def test_strip_telnet_iac_other(self, mock_handler, async_session):
        """Test _strip_telnet_iac with other IAC."""
        async_session._connected = True
        async_session.tn3270_mode = False
        data = b'\xFF other text'
        stripped = async_session._strip_telnet_iac(data)
        assert stripped == b'other text'

    @patch('pure3270.session.TN3270Handler')
    async def test_macro_empty_sequence(self, mock_handler, async_session):
        """Test macro with empty sequence."""
        async_session.handler = mock_handler.return_value = AsyncMock()
        async_session.send = AsyncMock()
        async_session._connected = True
        await async_session.macro([])
        assert async_session.send.call_count == 0

    async def test_close_no_handler(self):
        """Test close without handler."""
        session = AsyncSession()
        await session.close()
        assert session._connected is False

class TestSession:
    def test_init(self, sync_session):
        assert isinstance(sync_session._async_session, AsyncSession)

    @patch('pure3270.session.asyncio.run')
    @patch('pure3270.session.TN3270Handler')
    def test_connect_non_ssl(self, mock_handler, mock_run, sync_session):
        mock_handler_instance = MagicMock()
        mock_handler_instance.connect = AsyncMock()
        mock_handler_instance.supports_tn3270 = True
        mock_handler_instance.negotiated_tn3270e = True
        mock_handler_instance.lu_name = "TEST"
        mock_handler_instance.screen_rows = 24
        mock_handler_instance.screen_cols = 80
        mock_handler.return_value = mock_handler_instance
        sync_session.connect('host', 23, ssl=False)
        # Verify connection was made
        assert sync_session.connected

    @patch('pure3270.session.asyncio.run')
    @patch('pure3270.session.TN3270Handler')
    def test_connect_ssl(self, mock_handler, mock_run, sync_session):
        mock_handler_instance = MagicMock()
        mock_handler_instance.connect = AsyncMock()
        mock_handler_instance.supports_tn3270 = True
        mock_handler_instance.negotiated_tn3270e = True
        mock_handler_instance.lu_name = "TEST"
        mock_handler_instance.screen_rows = 24
        mock_handler_instance.screen_cols = 80
        mock_handler.return_value = mock_handler_instance
        sync_session.connect('host', 992, ssl=True)
        # Verify connection was made
        assert sync_session.connected

    @patch('pure3270.session.asyncio.run')
    def test_connect_error(self, mock_run, sync_session):
        mock_run.side_effect = Exception('Connect failed')
        with pytest.raises(SessionError):
            sync_session.connect('host', 23)

    @patch('pure3270.session.asyncio.run')
    def test_send(self, mock_run, sync_session):
        # Set up connected state
        sync_session.loop = MagicMock()
        sync_session._async_session.send = AsyncMock()
        sync_session.send('key Enter')
        sync_session.loop.run_until_complete.assert_called_once()

    @patch('pure3270.session.asyncio.run')
    def test_read(self, mock_run, sync_session):
        # Set up connected state
        sync_session.loop = MagicMock()
        sync_session.loop.run_until_complete.return_value = 'screen text'
        text = sync_session.read()
        assert text == 'screen text'
        sync_session.loop.run_until_complete.assert_called_once()

    @patch('pure3270.session.asyncio.run')
    def test_macro(self, mock_run, sync_session):
        # Set up connected state
        sync_session.loop = MagicMock()
        sync_session._async_session.macro = AsyncMock()
        sync_session.macro(['key Enter'])
        sync_session.loop.run_until_complete.assert_called_once()

    @patch('pure3270.session.asyncio.run')
    def test_close(self, mock_run, sync_session):
        # Set up connected state
        mock_loop = MagicMock()
        sync_session.loop = mock_loop
        sync_session._async_session.close = AsyncMock()
        sync_session.close()
        mock_loop.run_until_complete.assert_called_once()

    def test_connected_property(self, sync_session):
        assert sync_session.connected is False
        sync_session._async_session._connected = True
        assert sync_session.connected is True

    def test_context_manager(self, sync_session):
        sync_session.close = MagicMock()
        with sync_session:
            assert sync_session.connected is False  # Assume not connected
        sync_session.close.assert_called_once()

    def test_tn3270_mode_property(self, sync_session):
        """Test tn3270_mode property."""
        sync_session._async_session.tn3270_mode = True
        assert sync_session.tn3270_mode is True
        sync_session._async_session.tn3270_mode = False
        assert sync_session.tn3270_mode is False

    def test_tn3270e_mode_property(self, sync_session):
        """Test tn3270e_mode property."""
        sync_session._async_session.tn3270e_mode = True
        assert sync_session.tn3270e_mode is True
        sync_session._async_session.tn3270e_mode = False
        assert sync_session.tn3270e_mode is False

    def test_lu_name_property(self, sync_session):
        """Test lu_name property."""
        sync_session._async_session.lu_name = "TESTLU"
        assert sync_session.lu_name == "TESTLU"
        sync_session._async_session.lu_name = None
        assert sync_session.lu_name is None

    def test_context_manager_connected(self):
        """Test context manager with connected session."""
        session = Session()
        session.loop = MagicMock()
        session._async_session._connected = True
        session.close = MagicMock()
        with session:
            assert session.connected is True
        session.close.assert_called_once()

# General tests for exceptions, logging, performance
def test_session_error(caplog):
    session = Session()
    with caplog.at_level('ERROR'):
        with pytest.raises(SessionError):
            session.send('key Enter')
    assert 'Must connect first' in caplog.text

def test_pure3270_error(caplog):
    with caplog.at_level('ERROR'):
        with pytest.raises(Pure3270Error):
            raise Pure3270Error('Test')
    assert 'Test' in caplog.text

# Performance: time macro execution
def test_performance_macro(benchmark, sync_session):
    sync_session._connected = True
    sync_session.loop = MagicMock()
    @patch('pure3270.session.asyncio.run')
    def run_macro(mock_run):
        sync_session.macro(['key Enter'] * 10)
    benchmark(run_macro)
    # Benchmark for efficient async wrapping

# Logging setup test
def test_setup_logging(caplog):
    from pure3270.session import setup_logging
    caplog.set_level('DEBUG')
    setup_logging('DEBUG')
    assert logging.getLogger("pure3270").level == logging.DEBUG

def test_setup_logging_warn():
    """Test setup_logging with WARN level."""
    from pure3270.session import setup_logging
    original_level = logging.getLogger("pure3270").level
    setup_logging('WARN')
    assert logging.getLogger("pure3270").level == logging.WARN
    # Restore
    logging.getLogger("pure3270").setLevel(original_level)

# Integration test with mocks
@patch('pure3270.session.TN3270Handler')
@patch('pure3270.session.asyncio.run')
def test_integration_flow(mock_run, mock_handler, sync_session):
    mock_handler_instance = MagicMock()
    mock_handler_instance.connect = AsyncMock()
    mock_handler_instance.send_data = AsyncMock()
    mock_handler_instance.receive_data = AsyncMock()
    mock_handler_instance.close = AsyncMock()
    mock_handler_instance.receive_data.return_value = b'\x05\xC1'
    mock_handler_instance.supports_tn3270 = True
    mock_handler_instance.negotiated_tn3270e = True
    mock_handler_instance.lu_name = "TEST"
    mock_handler_instance.screen_rows = 24
    mock_handler_instance.screen_cols = 80
    mock_handler.return_value = mock_handler_instance
    mock_run.return_value = 'screen text'
    sync_session.connect('host')
    sync_session.send('key Enter')
    text = sync_session.read()
    # Verify connection before closing
    assert sync_session.connected
    sync_session.close()
    # After closing, connection should be False
    assert not sync_session.connected
