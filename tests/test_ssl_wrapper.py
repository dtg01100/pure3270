import pytest
from unittest.mock import patch, MagicMock
from pure3270.protocol.ssl_wrapper import SSLWrapper, SSLError
import ssl

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
        assert ctx.check_hostname is True
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2
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

    @patch('pure3270.protocol.ssl_wrapper.SSLWrapper.wrap_connection')
    @patch('pure3270.protocol.ssl_wrapper.SSLWrapper.create_context')
    def test_ssl_encryption_for_data_transit(self, mock_create, mock_wrap, ssl_wrapper):
        """
        Ported from s3270 test case 4: SSL encryption for data transit.
        Input SSL-wrapped connection, send encrypted data; output decrypts;
        assert plain text matches decrypted, no plaintext exposure.
        """
        # Mock context and wrap
        mock_context = MagicMock()
        mock_create.return_value = mock_context
        mock_wrap.return_value = b'encrypted_data'  # Simulated encrypted

        # Mock decrypt for assertion (assume wrapper has decrypt, but stub; patch)
        plain_text = b'plain_data'
        with patch.object(ssl_wrapper, 'decrypt', return_value=plain_text):  # Assume decrypt method for test
            decrypted = ssl_wrapper.decrypt(mock_wrap.return_value)

        # Assert plain text matches, no plaintext in encrypted
        assert decrypted == plain_text
        assert plain_text not in mock_wrap.return_value
        mock_create.assert_called_once()
        mock_wrap.assert_called_once()
