import pytest
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.emulation.screen_buffer import ScreenBuffer
from unittest.mock import AsyncMock, MagicMock


class TestNegotiatorEnhancements:
    def test_init_with_device_type_support(self):
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

    def test_parse_tn3270e_subnegotiation_invalid_data(self):
        """Test parsing invalid TN3270E subnegotiation data."""
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        negotiator = Negotiator(None, parser, screen_buffer)

        # Test with too short data
        negotiator._parse_tn3270e_subnegotiation(b"\x01\x02")
        # Should not raise exception, just log warning

        # Test with invalid TN3270E option
        negotiator._parse_tn3270e_subnegotiation(b"\x01\x02\x03")
        # Should not raise exception, just log warning

    def test_handle_device_type_subnegotiation(self):
        """Test handling device type subnegotiation."""
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        negotiator = Negotiator(None, parser, screen_buffer)

        # Test with invalid data
        negotiator._handle_device_type_subnegotiation(b"\x01")
        # Should not raise exception, just log warning

        # Test with valid IS message but no device type
        negotiator._handle_device_type_subnegotiation(b"\x02")
        # Should not raise exception

        # Test with IBM-DYNAMIC device type
        negotiator._handle_device_type_subnegotiation(b"\x02IBM-DYNAMIC\x00")
        # Should set negotiated_device_type to IBM-DYNAMIC
        assert negotiator.negotiated_device_type == "IBM-DYNAMIC"

    def test_handle_functions_subnegotiation(self):
        """Test handling functions subnegotiation."""
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        negotiator = Negotiator(None, parser, screen_buffer)

        # Test with invalid data
        negotiator._handle_functions_subnegotiation(b"\x01")
        # Should not raise exception, just log warning

        # Test with valid IS message but no functions
        negotiator._handle_functions_subnegotiation(b"\x02")
        # Should not raise exception

    def test_send_supported_device_types_no_writer(self):
        """Test sending device types with no writer."""
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        negotiator = Negotiator(None, parser, screen_buffer)

        # Should log error but not raise exception
        negotiator._send_supported_device_types()

    def test_send_supported_functions_no_writer(self):
        """Test sending functions with no writer."""
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        negotiator = Negotiator(None, parser, screen_buffer)

        # Should log error but not raise exception
        negotiator._send_supported_functions()
