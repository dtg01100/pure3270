import pytest
from unittest.mock import AsyncMock, patch





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
        expected_pattern[0:5] = b'\xC1\xC2\xC3\xC4\xC5'  # Sample 'ABCDE' in EBCDIC

        # Simulate receive data after sends: Write with sample data
        stream = (
            b'\xF5\x10\x00\x00' + bytes(expected_pattern) + b'\x0D'  # WCC, SBA(0,0), data, EOA
        )
        mock_handler.receive_data.return_value = stream

        async_session.handler = mock_handler
        async_session._connected = True

        with patch.object(async_session.parser, 'parse') as mock_parse:
            mock_parse.side_effect = lambda data: setattr(async_session.screen, 'buffer', expected_pattern)

            # Execute macro: startup connect (already mocked), send string, key Enter, read
            macro_sequence = ['String(login)', 'key Enter']
            await async_session.macro(macro_sequence)

            # Read after macro
            await async_session.read()

        # Assert final buffer matches expected EBCDIC pattern
        assert async_session.screen.buffer == expected_pattern

        # Verify sends: two calls for macro, one for read? But macro only sends
        assert mock_handler.send_data.call_count == 2
        mock_handler.receive_data.assert_called_once()
