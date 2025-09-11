import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.exceptions import NegotiationError, ProtocolError
from pure3270.protocol.utils import (
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IS,
    TN3270E_REQUEST,
    TN3270E_SEND,
    TN3270E_BIND_IMAGE,
    TN3270E_DATA_STREAM_CTL,
    TN3270E_RESPONSES,
    TN3270E_SCS_CTL_CODES,
    TN3270E_SYSREQ,
    TN3270E_IBM_DYNAMIC,
)


class TestNegotiatorMissingCoverage:
    """Tests for missing coverage in negotiator.py"""

    @pytest.fixture
    def negotiator(self):
        parser = DataStreamParser(ScreenBuffer())
        screen_buffer = ScreenBuffer()
        return Negotiator(None, parser, screen_buffer)

    def test_parse_tn3270e_subnegotiation_edge_cases(self, negotiator):
        """Test edge cases in TN3270E subnegotiation parsing."""
        # Test with malformed data that should be handled gracefully
        negotiator._parse_tn3270e_subnegotiation(b"")
        negotiator._parse_tn3270e_subnegotiation(b"\x00")
        negotiator._parse_tn3270e_subnegotiation(b"\xff\xff\xff")

        # Test with invalid TN3270E option
        negotiator._parse_tn3270e_subnegotiation(b"\x99\x01\x02")  # Invalid option 0x99

    def test_handle_device_type_subnegotiation_invalid_data(self, negotiator):
        """Test handling of invalid device type subnegotiation data."""
        # Test with data that doesn't match expected format
        negotiator._handle_device_type_subnegotiation(b"")
        negotiator._handle_device_type_subnegotiation(b"\x01")  # Missing sub-type
        negotiator._handle_device_type_subnegotiation(
            b"\x03\x01"
        )  # REJECT with no reason

    def test_handle_functions_subnegotiation_invalid_data(self, negotiator):
        """Test handling of invalid functions subnegotiation data."""
        # Test with malformed function data
        negotiator._handle_functions_subnegotiation(b"")
        negotiator._handle_functions_subnegotiation(b"\x01")  # Missing function bits
        negotiator._handle_functions_subnegotiation(b"\x99\x01\x02")  # Invalid sub-type

    def test_send_supported_device_types_no_writer(self, negotiator):
        """Test sending device types when writer is None."""
        # This should log an error but not crash
        negotiator._send_supported_device_types()

    def test_send_supported_functions_no_writer(self, negotiator):
        """Test sending functions when writer is None."""
        # This should log an error but not crash
        negotiator._send_supported_functions()

    def test_lu_name_property(self, negotiator):
        """Test LU name property getter and setter."""
        # Test getter when None
        assert negotiator.lu_name is None

        # Test setter and getter
        negotiator.lu_name = "TEST-LU"
        assert negotiator.lu_name == "TEST-LU"

        # Test setting to None
        negotiator.lu_name = None
        assert negotiator.lu_name is None

    def test_is_printer_session_active(self, negotiator):
        """Test printer session detection."""
        # Initially should be False
        assert negotiator.is_printer_session_active() is False

        # Set printer session flag
        negotiator.is_printer_session = True
        assert negotiator.is_printer_session_active() is True

    def test_receive_data_no_handler(self, negotiator):
        """Test receiving data when no handler is available."""
        with pytest.raises(NotImplementedError):
            asyncio.run(negotiator._receive_data())

    def test_read_iac_no_handler(self, negotiator):
        """Test reading IAC when no handler is available."""
        with pytest.raises(NotImplementedError):
            asyncio.run(negotiator._read_iac())

    def test_negotiate_no_writer(self, negotiator):
        """Test negotiate when writer is None."""
        negotiator.writer = None
        with pytest.raises(ProtocolError):
            asyncio.run(negotiator.negotiate())

    def test_handle_device_type_is_with_invalid_data(self, negotiator):
        """Test DEVICE-TYPE IS handling with invalid device type data."""
        # Test with malformed device type string
        negotiator._handle_device_type_subnegotiation(bytes([TN3270E_IS]) + b"")
        negotiator._handle_device_type_subnegotiation(
            bytes([TN3270E_IS]) + b"incomplete\x00"
        )

    def test_handle_device_type_request_with_no_supported_types(self, negotiator):
        """Test DEVICE-TYPE REQUEST handling when no supported types."""
        # Clear supported types
        negotiator.supported_device_types = []
        negotiator._handle_device_type_subnegotiation(bytes([TN3270E_REQUEST]))

    def test_handle_functions_is_with_empty_data(self, negotiator):
        """Test FUNCTIONS IS handling with empty function data."""
        negotiator._handle_functions_subnegotiation(bytes([TN3270E_IS]))

    def test_handle_functions_request_with_no_supported_functions(self, negotiator):
        """Test FUNCTIONS REQUEST handling when no supported functions."""
        # Clear supported functions
        negotiator.supported_functions = 0
        negotiator._handle_functions_subnegotiation(bytes([TN3270E_REQUEST]))

    def test_send_supported_device_types_with_empty_supported_list(self, negotiator):
        """Test sending device types when supported list is empty."""
        negotiator.writer = MagicMock()
        negotiator.supported_device_types = []
        negotiator._send_supported_device_types()

    def test_send_supported_functions_with_no_functions(self, negotiator):
        """Test sending functions when no functions are supported."""
        negotiator.writer = MagicMock()
        negotiator.supported_functions = 0
        negotiator._send_supported_functions()
