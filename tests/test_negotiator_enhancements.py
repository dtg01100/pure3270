import platform
from unittest.mock import AsyncMock, MagicMock

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.negotiator import Negotiator


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
class TestNegotiatorEnhancements:
    def test_init_with_device_type_support(self, memory_limit_500mb):
        """Test that negotiator initializes with device type support."""
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        negotiator = Negotiator(None, parser, screen_buffer)

        # Check that device type support is initialized
        assert hasattr(negotiator, "supported_device_types")
        assert hasattr(negotiator, "requested_device_type")
        assert hasattr(negotiator, "negotiated_device_type")
        assert hasattr(negotiator, "supported_functions")
        assert hasattr(negotiator, "negotiated_functions")

        # Check default values
        assert negotiator.negotiated_device_type is None
        assert negotiator.supported_device_types is not None
        assert "IBM-DYNAMIC" in negotiator.supported_device_types

    @pytest.mark.asyncio
    async def test_parse_tn3270e_subnegotiation_invalid_data(self, memory_limit_500mb):
        """Test parsing invalid TN3270E subnegotiation data."""
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        negotiator = Negotiator(None, parser, screen_buffer)

        # Test with too short data
        await negotiator._parse_tn3270e_subnegotiation(b"\x01\x02")
        # Should not raise exception, just log warning

        # Test with invalid TN3270E option
        await negotiator._parse_tn3270e_subnegotiation(b"\x01\x02\x03")
        # Should not raise exception, just log warning

    @pytest.mark.asyncio
    async def test_handle_device_type_subnegotiation(self, memory_limit_500mb):
        """Test handling device type subnegotiation."""
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        negotiator = Negotiator(None, parser, screen_buffer)

        # Test with invalid data - should call _parse_tn3270e_subnegotiation
        from pure3270.protocol.utils import TELOPT_TN3270E

        await negotiator._parse_tn3270e_subnegotiation(bytes([TELOPT_TN3270E, 0x01]))
        # Should not raise exception, just log warning

        # Test with valid IS message but no device type
        await negotiator._parse_tn3270e_subnegotiation(bytes([TELOPT_TN3270E, 0x02]))
        # Should not raise exception

        # Test with IBM-DYNAMIC device type
        await negotiator._parse_tn3270e_subnegotiation(
            bytes([TELOPT_TN3270E, 0x02]) + b"IBM-DYNAMIC\x00"
        )
        # Should set negotiated_device_type to IBM-DYNAMIC
        assert negotiator.negotiated_device_type == "IBM-DYNAMIC"

    @pytest.mark.asyncio
    async def test_handle_functions_subnegotiation(self, memory_limit_500mb):
        """Test handling functions subnegotiation."""
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        negotiator = Negotiator(None, parser, screen_buffer)

        # Test with invalid data - should call _parse_tn3270e_subnegotiation
        from pure3270.protocol.utils import TELOPT_TN3270E

        await negotiator._parse_tn3270e_subnegotiation(bytes([TELOPT_TN3270E, 0x01]))
        # Should not raise exception, just log warning

        # Test with valid IS message but no functions
        await negotiator._parse_tn3270e_subnegotiation(bytes([TELOPT_TN3270E, 0x02]))
        # Should not raise exception

    @pytest.mark.asyncio
    async def test_send_supported_device_types_no_writer(self, memory_limit_500mb):
        """Test sending device types with no writer."""
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        negotiator = Negotiator(None, parser, screen_buffer)

        # Should log error but not raise exception
        await negotiator._send_supported_device_types()

    @pytest.mark.asyncio
    async def test_send_supported_functions_no_writer(self, memory_limit_500mb):
        """Test sending functions with no writer."""
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        negotiator = Negotiator(None, parser, screen_buffer)

        # Should log error but not raise exception
        await negotiator._send_functions_is()
