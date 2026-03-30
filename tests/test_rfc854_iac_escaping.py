"""
Test RFC 854 IAC escaping compliance.

Per RFC 854 Section 3.2.1:
"Within the data stream, a 0xFF byte (IAC) must be doubled to distinguish it
from the IAC command prefix. Thus, IAC IAC (0xFF 0xFF) in the data stream
represents a single 0xFF data byte."

This test suite verifies that pure3270 correctly handles IAC escaping in
both inbound (host→terminal) and outbound (terminal→host) data streams.
"""

import pytest
from unittest.mock import AsyncMock, patch

from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.utils import IAC


@pytest.fixture
def tn3270_handler(memory_limit_500mb):
    """Create a TN3270Handler for testing."""
    screen_buffer = ScreenBuffer()
    handler = TN3270Handler(
        reader=None,
        writer=None,
        screen_buffer=screen_buffer,
        host="localhost",
        port=23,
        terminal_type="IBM-3278-2",
        is_printer_session=False,
    )
    handler._connected = True
    handler.writer = AsyncMock()
    handler.writer.drain = AsyncMock()
    handler.reader = AsyncMock()
    return handler


class TestIACEscaping:
    """Tests for RFC 854 IAC escaping compliance."""

    @pytest.mark.asyncio
    async def test_iac_iac_represents_single_0xff_data_byte(self, tn3270_handler):
        """RFC 854: IAC IAC (0xFF 0xFF) in data stream = single 0xFF data byte.
        
        This is the core IAC escaping requirement from RFC 854 Section 3.2.1.
        """
        # Data stream with IAC IAC (escaped 0xFF) followed by normal data
        data = bytes([0x41, 0x42, IAC, IAC, 0x43, 0x44])  # AB (0xFF) CD
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        
        # Should have 5 bytes: A B 0xFF C D
        assert len(cleaned_data) == 5
        assert cleaned_data == bytes([0x41, 0x42, 0xFF, 0x43, 0x44])
        assert ascii_mode is False

    @pytest.mark.asyncio
    async def test_multiple_iac_escapes_in_stream(self, tn3270_handler):
        """Multiple IAC IAC sequences should each produce single 0xFF bytes."""
        # Multiple escaped IAC bytes
        data = bytes([IAC, IAC, 0x41, IAC, IAC, 0x42, IAC, IAC])
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        
        # Should be: 0xFF A 0xFF B 0xFF
        assert len(cleaned_data) == 5
        assert cleaned_data == bytes([0xFF, 0x41, 0xFF, 0x42, 0xFF])

    @pytest.mark.asyncio
    async def test_iac_followed_by_command_not_escaped(self, tn3270_handler):
        """IAC followed by command byte (DO, WILL, etc.) is NOT escaped data."""
        # IAC DO ECHO - this is a command, not escaped data
        data = bytes([IAC, 0xFD, 0x01])  # IAC DO ECHO
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        
        # Commands should be stripped, no cleaned data
        assert cleaned_data == b""

    @pytest.mark.asyncio
    async def test_mixed_iac_commands_and_escaped_data(self, tn3270_handler):
        """Test stream with both IAC commands and escaped IAC data bytes."""
        # IAC NOP (command) + A + IAC IAC (escaped 0xFF) + B + IAC GA (command)
        data = bytes([IAC, 0xF1, 0x41, IAC, IAC, 0x42, IAC, 0xF9])
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        
        # Should be: A 0xFF B (commands stripped)
        assert len(cleaned_data) == 3
        assert cleaned_data == bytes([0x41, 0xFF, 0x42])

    @pytest.mark.asyncio
    async def test_lone_iac_at_end_buffered(self, tn3270_handler):
        """Lone IAC at end of chunk should be buffered for next chunk."""
        # Data ending with lone IAC
        data = bytes([0x41, 0x42, IAC])
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        
        # Should buffer the IAC and return only AB
        assert cleaned_data == bytes([0x41, 0x42])
        assert tn3270_handler._telnet_buffer == bytes([IAC])
        
        # Next chunk should combine buffered IAC with new data
        next_data = bytes([IAC, 0x43])  # IAC IAC + C = escaped 0xFF + C
        cleaned_data2, ascii_mode2 = await tn3270_handler._process_telnet_stream(next_data)
        
        # Should produce: 0xFF C
        assert cleaned_data2 == bytes([0xFF, 0x43])
        assert tn3270_handler._telnet_buffer == b""

    @pytest.mark.asyncio
    async def test_iac_iac_split_across_chunks(self, tn3270_handler):
        """IAC IAC split across two chunks should be handled correctly."""
        # First chunk ends with IAC
        data1 = bytes([0x41, IAC])
        cleaned1, _ = await tn3270_handler._process_telnet_stream(data1)
        
        assert cleaned1 == bytes([0x41])
        assert tn3270_handler._telnet_buffer == bytes([IAC])
        
        # Second chunk starts with IAC (completing IAC IAC)
        data2 = bytes([IAC, 0x42])
        cleaned2, _ = await tn3270_handler._process_telnet_stream(data2)
        
        # Should produce: 0xFF B
        assert cleaned2 == bytes([0xFF, 0x42])
        assert tn3270_handler._telnet_buffer == b""

    @pytest.mark.asyncio
    async def test_consecutive_iac_iac_pairs(self, tn3270_handler):
        """Multiple consecutive IAC IAC pairs should all be escaped."""
        # Four IAC bytes = two escaped 0xFF bytes
        data = bytes([IAC, IAC, IAC, IAC])
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        
        # Should produce: 0xFF 0xFF
        assert cleaned_data == bytes([0xFF, 0xFF])

    @pytest.mark.asyncio
    async def test_iac_iac_in_3270_data_stream(self, tn3270_handler):
        """IAC IAC in actual 3270 data stream context."""
        # Simulate a 3270 Write command with 0xFF in the data
        # Write (0xF5) + WCC (0xC1) + data with 0xFF
        data = bytes([0xF5, 0xC1, 0x40, IAC, IAC, 0x50, 0x60])
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        
        # Should preserve all bytes with IAC IAC converted to single 0xFF
        assert cleaned_data == bytes([0xF5, 0xC1, 0x40, 0xFF, 0x50, 0x60])

    @pytest.mark.asyncio
    async def test_no_false_positive_iac_detection(self, tn3270_handler):
        """Normal data bytes should not be mistaken for IAC."""
        # Data with bytes that look like commands but aren't IAC-prefixed
        data = bytes([0xFD, 0xFB, 0xFC, 0xFE])  # DO, WILL, WONT, DONT without IAC
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        
        # All bytes should pass through unchanged
        assert cleaned_data == data
        assert len(cleaned_data) == 4


class TestIACEscapingEdgeCases:
    """Edge cases for IAC escaping."""

    @pytest.mark.asyncio
    async def test_empty_data_stream(self, tn3270_handler):
        """Empty data stream should return empty cleaned data."""
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(b"")
        assert cleaned_data == b""
        assert ascii_mode is False

    @pytest.mark.asyncio
    async def test_only_iac_iac(self, tn3270_handler):
        """Data stream with only IAC IAC should produce single 0xFF."""
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(
            bytes([IAC, IAC])
        )
        assert cleaned_data == bytes([0xFF])

    @pytest.mark.asyncio
    async def test_iac_in_subnegotiation_payload(self, tn3270_handler):
        """IAC bytes in subnegotiation payload should be handled by negotiator."""
        # This tests that subnegotiation extraction works correctly
        # IAC SB TN3270E ... IAC SE
        # The negotiator handles IAC escaping within subnegotiations
        with patch.object(tn3270_handler.negotiator, 'handle_subnegotiation', 
                         return_value=None) as mock_handle:
            data = bytes([IAC, 0xFA, 0x18, 0x41, 0x42, IAC, 0xF0])  # SB TTYPE AB SE
            cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
            
            # Subnegotiation should be stripped
            assert cleaned_data == b""
            mock_handle.assert_called_once()


class TestIACEscapingWithRealScenarios:
    """Real-world scenarios for IAC escaping."""

    @pytest.mark.asyncio
    async def test_binary_data_with_0xff_bytes(self, tn3270_handler):
        """Binary 3270 data streams may contain 0xFF bytes that must be escaped."""
        # Simulate binary data with multiple 0xFF bytes
        binary_data = bytes([0x00, 0xFF, 0x80, 0xFF, 0xFF, 0xFF])
        
        # In telnet stream, 0xFF must be escaped as IAC IAC
        telnet_stream = bytearray()
        for byte in binary_data:
            if byte == 0xFF:
                telnet_stream.extend([IAC, IAC])
            else:
                telnet_stream.append(byte)
        
        cleaned_data, _ = await tn3270_handler._process_telnet_stream(bytes(telnet_stream))
        
        # Should recover original binary data
        assert cleaned_data == binary_data

    @pytest.mark.asyncio
    async def test_host_sends_escaped_iac_in_screen_data(self, tn3270_handler):
        """Host may send screen data containing escaped IAC bytes."""
        # Host sends: Write + WCC + SBA(0,0) + data with 0xFF
        # In telnet: 0xF5 0xC1 0x11 0x00 0x00 0x41 IAC IAC 0x42
        data = bytes([0xF5, 0xC1, 0x11, 0x00, 0x00, 0x41, IAC, IAC, 0x42])
        cleaned_data, _ = await tn3270_handler._process_telnet_stream(data)
        
        assert cleaned_data == bytes([0xF5, 0xC1, 0x11, 0x00, 0x00, 0x41, 0xFF, 0x42])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
