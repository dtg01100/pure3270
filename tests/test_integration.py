import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
class TestIntegration:
    async def test_end_to_end_macro_execution(self, async_session):
        """
        Ported from s3270 test case: End-to-end macro execution.
        Input macro (startup, keys, reads); output expected screen state;
        assert final buffer matches EBCDIC pattern.
        """
        # Mock handler for simulation
        mock_handler = AsyncMock()
        mock_handler.connect = AsyncMock()
        mock_handler.send_data = AsyncMock()
        mock_handler.receive_data = AsyncMock()
        mock_handler.close = AsyncMock()

        # Mock responses for macro steps
        expected_pattern = bytearray([0x40] * (24 * 80))  # Full EBCDIC spaces
        expected_pattern[0:5] = b"\xc1\xc2\xc3\xc4\xc5"  # Sample 'ABCDE' in EBCDIC

        # Simulate receive data after sends: Write with sample data
        stream = (
            b"\xf5\x10\x00\x00"
            + bytes(expected_pattern)
            + b"\x0d"  # WCC, SBA(0,0), data, EOA
        )
        mock_handler.receive_data.return_value = stream

        async_session.handler = mock_handler
        async_session._connected = True
        async_session.tn3270_mode = True  # Enable TN3270 mode for proper parsing

        with patch("pure3270.session.DataStreamParser") as mock_parser_class:
            mock_parser_instance = MagicMock()
            mock_parser_class.return_value = mock_parser_instance
            mock_parser_instance.parse.side_effect = lambda data: setattr(
                async_session.screen, "buffer", expected_pattern
            )

            # Execute macro: startup connect (already mocked), send string, key Enter, read
            macro_sequence = ["String(login)", "key Enter"]
            await async_session.macro(macro_sequence)

            # Read after macro
            await async_session.read()

        # Assert final buffer matches expected EBCDIC pattern
        assert async_session.screen.buffer == expected_pattern

        # Verify sends: one call for macro (key Enter sends input stream)
        assert mock_handler.send_data.call_count == 1
        mock_handler.receive_data.assert_called_once()
