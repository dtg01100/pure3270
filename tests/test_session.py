import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pure3270.session import Session, AsyncSession, SessionError, MacroError
from pure3270.emulation.screen_buffer import ScreenBuffer
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

    @patch('pure3270.session.asyncio.open_connection')
    @patch('pure3270.session.TN3270Handler')
    async def test_connect(self, mock_handler, mock_open, async_session):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)
        mock_handler_instance = AsyncMock()
        mock_handler.return_value = mock_handler_instance
        mock_handler_instance.negotiate = AsyncMock()
        mock_handler_instance._negotiate_tn3270 = AsyncMock()
        mock_handler_instance.set_ascii_mode = AsyncMock()

        await async_session.connect()

        mock_open.assert_called_once()
        mock_handler.assert_called_once_with(mock_reader, mock_writer)
        mock_handler_instance.negotiate.assert_called_once()
        mock_handler_instance._negotiate_tn3270.assert_called_once()
        assert async_session._connected is True

    @patch('pure3270.session.asyncio.open_connection')
    @patch('pure3270.session.TN3270Handler')
    async def test_connect_negotiation_fail(self, mock_handler, mock_open, async_session):
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open.return_value = (mock_reader, mock_writer)
        mock_handler_instance = AsyncMock()
        mock_handler.return_value = mock_handler_instance
        mock_handler_instance.negotiate = AsyncMock()
        from pure3270.protocol.exceptions import NegotiationError
        mock_handler_instance._negotiate_tn3270.side_effect = NegotiationError("Negotiation failed")
        mock_handler_instance.set_ascii_mode = AsyncMock()

        await async_session.connect()

        mock_handler_instance.set_ascii_mode.assert_called_once()
        assert async_session._connected is True

    @patch('pure3270.session.TN3270Handler')
    async def test_send(self, mock_handler, async_session):
        async_session._handler = mock_handler.return_value = AsyncMock()
        async_session._connected = True
        mock_handler.return_value.send_data = AsyncMock()

        await async_session.send(b"test data")

        mock_handler.return_value.send_data.assert_called_once_with(b"test data")

    async def test_send_not_connected(self, async_session):
        with pytest.raises(SessionError):
            await async_session.send(b"data")

    @patch('pure3270.session.TN3270Handler')
    async def test_read(self, mock_handler, async_session):
        async_session._handler = mock_handler.return_value = AsyncMock()
        async_session._connected = True
        mock_handler.return_value.receive_data.return_value = b"test"

        data = await async_session.read()

        assert data == b"test"
        mock_handler.return_value.receive_data.assert_called_once_with(5.0)

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
        session._connected = True
        session._handler = AsyncMock()
        session.send = AsyncMock()
        session.read = AsyncMock(return_value=b'output')
        
        macro = 'if connected: key Enter'
        vars_dict = {}
        result = await session.execute_macro(macro, vars_dict)
        
        assert result['success'] is True
        assert len(result['output']) == 1
        assert 'output' in result['output'][0]
        session.send.assert_called_once_with(b'key Enter')

    @pytest.mark.asyncio
    async def test_variable_substitution(self):
        """Test variable substitution in execute_macro."""
        session = AsyncSession("localhost", 23)
        session._connected = True
        session._handler = AsyncMock()
        session.send = AsyncMock()
        session.read = AsyncMock(return_value=b'substituted')
        
        macro = 'key ${action}'
        vars_dict = {'action': 'PF3'}
        result = await session.execute_macro(macro, vars_dict)
        
        assert result['success'] is True
        assert len(result['output']) == 1
        assert 'substituted' in result['output'][0]
        session.send.assert_called_once_with(b'key PF3')

    @pytest.mark.asyncio
    async def test_nested_macros(self):
        """Test nested macros in execute_macro."""
        session = AsyncSession("localhost", 23)
        session._connected = True
        session._handler = AsyncMock()
        session.send = AsyncMock()
        session.read = AsyncMock(return_value=b'nested output')
        
        macro = 'macro sub_macro'
        vars_dict = {'sub_macro': 'key Enter'}
        result = await session.execute_macro(macro, vars_dict)
        
        assert result['success'] is True
        assert len(result['output']) == 1
        sub_result = result['output'][0]
        assert isinstance(sub_result, dict)
        assert sub_result['success'] is True
        assert len(sub_result['output']) == 1
        assert 'nested output' in sub_result['output'][0]
        session.send.assert_called_once_with(b'key Enter')

    @pytest.mark.asyncio
    async def test_incompatible_patching(self):
        """Test macro execution with incompatible patching (graceful handling)."""
        with patch('pure3270.patching.patching.enable_replacement') as mock_patch:
            mock_patch.side_effect = ValueError("Incompatible version")
            
            session = AsyncSession("localhost", 23)
            session._connected = True
            session._handler = AsyncMock()
            session.send = AsyncMock()
            session.read = AsyncMock(return_value=b'output')
            
            macro = 'key Enter'
            result = await session.execute_macro(macro)
            
            assert result['success'] is True
            assert len(result['output']) == 1
            assert 'output' in result['output'][0]

    @pytest.mark.asyncio
    async def test_execute_macro_malformed(self, async_session):
        """Test macro execution with malformed script raising MacroError."""
        async_session._handler = AsyncMock()
        async_session._connected = True
        with patch.object(async_session, 'send', side_effect=MacroError('Invalid command')):
            result = await async_session.execute_macro('invalid_cmd;')
        assert result['success'] is False
        assert 'Error in command' in result['output'][0]

    @pytest.mark.asyncio
    async def test_execute_macro_unhandled_exception(self, async_session):
        """Test unhandled exception in async macro loop raises MacroError."""
        async_session._handler = AsyncMock()
        async_session._connected = True
        async_session.send = AsyncMock()
        async_session.read = AsyncMock(side_effect=Exception('Unhandled'))
        result = await async_session.execute_macro('cmd1;cmd2;')
        assert result['success'] is False
        assert 'Error in command' in result['output'][0]

    @pytest.mark.asyncio
    async def test_execute_macro_timeout(self, async_session):
        """Test macro execution failure with timeout raises MacroError."""
        async_session._handler = AsyncMock()
        async_session._connected = True
        async_session.send = AsyncMock()
        async_session.read = AsyncMock(side_effect=[b'output1', asyncio.TimeoutError('Timeout')])
        result = await async_session.execute_macro('cmd1;cmd2;')
        assert result['success'] is False
        assert 'Error in command' in result['output'][1]

    @pytest.mark.asyncio
    async def test_execute_macro_empty(self, async_session):
        """Test macro with empty script succeeds with empty output."""
        async_session._handler = AsyncMock()
        async_session._connected = True
        result = await async_session.execute_macro('')
        assert result['success'] is True
        assert result['output'] == []

class TestSession:
    @patch('pure3270.session.AsyncSession')
    def test_connect(self, mock_async_session, sync_session):
        mock_async_instance = AsyncMock()
        mock_async_session.return_value = mock_async_instance
        mock_async_instance.connect = AsyncMock()

        # Use asyncio.run to actually execute the coroutine
        import asyncio
        asyncio.run(sync_session._connect_async())

        mock_async_session.assert_called_once_with(sync_session._host, sync_session._port, sync_session._ssl_context)
        mock_async_instance.connect.assert_called_once()

    @patch('pure3270.session.asyncio.run')
    def test_send(self, mock_run, sync_session):
        mock_run.return_value = None

        sync_session.send(b"data")

        mock_run.assert_called_once()

    @patch('pure3270.session.asyncio.run')
    def test_read(self, mock_run, sync_session):
        mock_run.return_value = b"data"

        data = sync_session.read()

        assert data == b"data"
        mock_run.assert_called_once()

    @patch('pure3270.session.asyncio.run')
    def test_execute_macro(self, mock_run, sync_session):
        mock_run.return_value = {'success': True}

        result = sync_session.execute_macro("macro")

        assert result['success'] is True
        mock_run.assert_called_once()

    @patch('pure3270.session.asyncio.run')
    def test_close(self, mock_run, sync_session):
        mock_run.return_value = None

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
