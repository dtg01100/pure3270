import platform
import resource


def set_memory_limit(max_memory_mb: int):
    """
    Set maximum memory limit for the current process.

    Args:
        max_memory_mb: Maximum memory in megabytes
    """
    # Only works on Unix systems
    if platform.system() != "Linux":
        return None

    try:
        max_memory_bytes = max_memory_mb * 1024 * 1024
        # RLIMIT_AS limits total virtual memory
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
        return max_memory_bytes
    except Exception:
        return None


#!/usr/bin/env python3
"""
Protocol-level integration tests for pure3270.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import pure3270
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser, DataStreamSender
from pure3270.protocol.tn3270_handler import TN3270Handler


class TestProtocolIntegration:
    """Test TN3270 protocol integration."""

    @pytest.mark.asyncio
    async def test_negotiation_sequence(self):
        """Test TN3270 negotiation sequence."""
        reader = AsyncMock()
        writer = AsyncMock()

        handler = TN3270Handler(reader, writer, host="localhost", port=23)
        writer.drain = AsyncMock()

        # Test that negotiator has the expected methods and properties
        assert hasattr(handler.negotiator, "_parse_tn3270e_subnegotiation")
        assert hasattr(handler.negotiator, "handle_subnegotiation")
        assert hasattr(handler.negotiator, "_device_type_is_event")
        assert hasattr(handler.negotiator, "_functions_is_event")

        # Test subnegotiation parsing directly
        # Format: tn3270e_type + tn3270e_subtype + payload
        device_type_data = b"\x00\x02IBM-3279-4-E\x00"  # 0x00=DEVICE_TYPE, 0x02=IS, "IBM-3279-4-E" + null terminator
        result = handler.negotiator._parse_tn3270e_subnegotiation(device_type_data)
        # The method returns a Task if called from async context, or runs synchronously
        if hasattr(result, "__await__"):
            await result
        assert handler.negotiator.negotiated_device_type == "IBM-3279-4-E"

        functions_data = b"\x01\x02\x15"  # 0x01=FUNCTIONS, 0x02=IS, 0x15=functions byte
        result = handler.negotiator._parse_tn3270e_subnegotiation(functions_data)
        if hasattr(result, "__await__"):
            await result
        assert handler.negotiator.negotiated_functions == 0x15

        # Verify the handler can be created and has expected properties
        assert handler.negotiator is not None
        assert handler.screen_buffer is not None

    @pytest.mark.asyncio
    async def test_data_stream_parsing(self):
        """Test data stream parsing."""
        screen = ScreenBuffer()
        parser = DataStreamParser(screen)

        # Sample 3270 data stream
        sample_data = b"\x05\xf5\xc1\x10\x00\x00\xc1\xc2\xc3\x0d"  # Write, WCC, SBA(0,0), ABC, EOA

        # Parse the data
        parser.parse(sample_data)

        # Verify results
        assert screen.buffer[0:3] == b"\xc1\xc2\xc3"  # ABC in EBCDIC

    def test_data_stream_building(self):
        """Test data stream building."""
        sender = DataStreamSender()

        # Build a key press command
        key_data = sender.build_key_press(0x7D)  # Enter key
        assert key_data == b"\x7d"

        # Build a write command
        write_data = sender.build_write(b"\xc1\xc2\xc3")  # ABC in EBCDIC
        assert b"\xc1\xc2\xc3" in write_data


@pytest.mark.asyncio
async def test_full_session_flow():
    """Test a full session flow with mocked connections."""
    # Enable patching
    pure3270.enable_replacement()

    with patch("asyncio.open_connection") as mock_open:
        # Mock connection
        reader = AsyncMock()
        writer = AsyncMock()
        mock_open.return_value = (reader, writer)

        # Mock data responses
        reader.readexactly.return_value = b"\xff\xfb\x27"  # WILL EOR
        reader.read.return_value = b"\x28\x00\x01\x00"  # BIND response

        writer.drain = AsyncMock()

        # Test session
        session = pure3270.AsyncSession("localhost", 2323)
        await session.connect()

        assert session.connected
        assert session._handler is not None


if __name__ == "__main__":
    # Run a simple test
    test = TestProtocolIntegration()
    test.test_data_stream_building()
    print("Protocol integration test passed!")
