import pytest
from unittest.mock import MagicMock
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.utils import (
    STRUCTURED_FIELD,
    QUERY_REPLY_SF,
    QUERY_REPLY_DEVICE_TYPE,
    QUERY_REPLY_CHARACTERISTICS,
)
from pure3270.emulation.screen_buffer import ScreenBuffer


class TestStructuredFieldSupport:
    def test_handle_structured_field(self):
        """Test handling structured field command."""
        screen_buffer = ScreenBuffer()
        parser = DataStreamParser(screen_buffer)

        # Mock the skip method to verify it's called
        parser._skip_structured_field = MagicMock()

        # Test with structured field command
        parser._data = bytes([STRUCTURED_FIELD, 0x01, 0x02])
        parser._pos = 0

        parser._handle_structured_field()

        # Verify skip method was called
        parser._skip_structured_field.assert_called_once()

    def test_skip_structured_field(self):
        """Test skipping structured field data."""
        screen_buffer = ScreenBuffer()
        parser = DataStreamParser(screen_buffer)

        # Test with some structured field data followed by a command
        parser._data = bytes([STRUCTURED_FIELD, 0x01, 0x02, 0x03, 0x10])  # 0x10 = SBA
        parser._pos = 1  # Start after SF command

        parser._skip_structured_field()

        # Should have moved to the SBA command
        assert parser._pos == 4

    def test_build_query_reply_sf(self):
        """Test building query reply structured field."""
        screen_buffer = ScreenBuffer()
        parser = DataStreamParser(screen_buffer)

        # Test building a simple query reply
        data = b"test data"
        sf = parser.build_query_reply_sf(QUERY_REPLY_DEVICE_TYPE, data)

        # Should start with STRUCTURED_FIELD
        assert sf[0] == STRUCTURED_FIELD
        # Should contain the query reply SF type
        assert QUERY_REPLY_SF in sf
        # Should contain the query type
        assert QUERY_REPLY_DEVICE_TYPE in sf
        # Should contain our data
        assert data in sf

    def test_build_device_type_query_reply(self):
        """Test building device type query reply."""
        screen_buffer = ScreenBuffer()
        parser = DataStreamParser(screen_buffer)

        sf = parser.build_device_type_query_reply()

        # Should start with STRUCTURED_FIELD
        assert sf[0] == STRUCTURED_FIELD
        # Should contain the query reply SF type
        assert QUERY_REPLY_SF in sf
        # Should contain device type query type
        assert QUERY_REPLY_DEVICE_TYPE in sf
        # Should contain device type string
        assert b"IBM-3278" in sf or b"IBM-DYNAMIC" in sf

    def test_build_characteristics_query_reply(self):
        """Test building characteristics query reply."""
        screen_buffer = ScreenBuffer()
        parser = DataStreamParser(screen_buffer)

        sf = parser.build_characteristics_query_reply()

        # Should start with STRUCTURED_FIELD
        assert sf[0] == STRUCTURED_FIELD
        # Should contain the query reply SF type
        assert QUERY_REPLY_SF in sf
        # Should contain characteristics query type
        assert QUERY_REPLY_CHARACTERISTICS in sf
