import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pure3270.protocol.tn3270_handler import TN3270Handler, ProtocolError, NegotiationError
from pure3270.protocol.ssl_wrapper import SSLWrapper


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

    async def test_negotiate_tn3270_success(self, tn3270_handler):
        with patch.object(tn3270_handler, 'telnet') as mock_telnet:
            mock_telnet.request_negotiate = AsyncMock()
            mock_telnet.read_until.side_effect = [b'\xff\xfb\x27', b'\xff\xfb\x24']
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


    @patch.object(TN3270Handler, 'reader')
    @patch.object(TN3270Handler, 'writer')
    async def test_tn3270e_negotiation_with_fallback(self, mock_writer, mock_reader, tn3270_handler):
        """
        Ported from s3270 test case 2: TN3270E negotiation with fallback.
        Input subnegotiation for TN3270E (e.g., BIND-IMAGE); output fallback to basic TN3270,
        DO/DONT responses; assert no errors, correct options.
        """
        # Mock responses: WILL TN3270 but WONT TN3270E
        mock_reader.read.return_value = b'\xff\xfb\x27'  # WILL TN3270
        mock_reader.read.return_value = b'\xff\xfc\x24'  # WONT TN3270E
        mock_writer.write = AsyncMock()
        mock_writer.drain = AsyncMock()

        # Call negotiate
        await tn3270_handler._negotiate_tn3270()

        # Assert fallback to basic TN3270, no error
        assert tn3270_handler.negotiated_tn3270e is False
        mock_writer.write.assert_any_call(b'\xff\xfd\x27')  # DO TN3270
        mock_writer.write.assert_any_call(b'\xff\xfd\x24')  # DO TN3270E
        # No NegotiationError raised
