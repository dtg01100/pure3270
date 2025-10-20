"""
Component initialization tests.

This file consolidates initialization tests for core components
to eliminate redundancy and ensure consistent initialization behavior.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.negotiator import Negotiator


class TestComponentInitialization:
    """Tests for proper initialization of core components."""

    def test_screen_buffer_initialization(self):
        """Test that ScreenBuffer initializes with correct default values."""
        rows, cols = 24, 80
        screen = ScreenBuffer(rows, cols)

        # Verify basic properties
        assert screen.rows == rows
        assert screen.cols == cols
        assert len(screen.buffer) == rows * cols
        assert screen.buffer == bytearray(
            b"\x40" * (rows * cols)
        )  # Filled with EBCDIC space (0x40)

        # Verify initial cursor position
        assert screen.get_position() == (0, 0)

        # Verify field detection
        assert hasattr(screen, "fields")
        assert screen.fields == []

        # Verify dimensions
        assert (screen.rows, screen.cols) == (rows, cols)

    def test_data_stream_parser_initialization(self):
        """Test that DataStreamParser initializes correctly."""
        screen_buffer = ScreenBuffer(24, 80)
        parser = DataStreamParser(screen_buffer)

        assert parser._screen_buffer is not None
        assert hasattr(parser, "parse")
        assert hasattr(parser, "_parse_order")
        assert hasattr(parser, "_parse_char")
        assert parser._pos == 0
        # Accept either None or empty bytes for initial _data state depending on implementation
        assert parser._data in (None, b"")

    def test_negotiator_initialization(self):
        """Test that Negotiator initializes with correct default values."""
        screen_buffer = ScreenBuffer(24, 80)
        reader = AsyncMock()
        writer = AsyncMock()
        negotiator = Negotiator(reader, writer, screen_buffer=screen_buffer)

        assert negotiator._reader is not None
        assert negotiator._writer is not None
        assert negotiator._screen_buffer is not None
        assert negotiator.tn3270_mode is False
        assert negotiator.tn3270e_mode is False
        assert negotiator._negotiated_options == {}
        assert negotiator._pending_negotiations == {}

    def test_screen_buffer_initialization_edge_cases(self):
        """Test ScreenBuffer initialization with edge case dimensions."""
        # Test normal dimensions
        normal_screen = ScreenBuffer(24, 80)
        assert normal_screen.rows == 24
        assert normal_screen.cols == 80

        # Test small dimensions
        small_screen = ScreenBuffer(2, 2)
        assert small_screen.rows == 2
        assert small_screen.cols == 2

        # Test buffer size is correct for different dimensions
        assert len(small_screen.buffer) == 4  # 2 * 2

        # Test larger dimensions
        large_screen = ScreenBuffer(32, 132)  # Common 3270 size
        assert large_screen.rows == 32
        assert large_screen.cols == 132
        assert len(large_screen.buffer) == 32 * 132

    def test_data_stream_parser_initialization_with_different_screen_buffers(self):
        """Test DataStreamParser initialization with different screen buffer configurations."""
        # Test with standard 24x80 screen
        screen_24x80 = ScreenBuffer(24, 80)
        parser_24x80 = DataStreamParser(screen_24x80)
        assert parser_24x80._screen_buffer.rows == 24
        assert parser_24x80._screen_buffer.cols == 80

        # Test with different dimensions
        screen_32x132 = ScreenBuffer(32, 132)
        parser_32x132 = DataStreamParser(screen_32x132)
        assert parser_32x132._screen_buffer.rows == 32
        assert parser_32x132._screen_buffer.cols == 132

    def test_negotiator_initialization_with_different_configs(self):
        """Test Negotiator initialization with different configurations."""
        screen_buffer = ScreenBuffer(24, 80)

        # Test with mock reader/writer
        reader = AsyncMock()
        writer = AsyncMock()
        negotiator = Negotiator(reader, writer, screen_buffer=screen_buffer)

        # Verify negotiator has access to its dependencies
        assert negotiator._reader is reader
        assert negotiator._writer is writer
        assert negotiator._screen_buffer is screen_buffer

        # Test that negotiator starts in correct initial state
        assert not negotiator.negotiated_tn3270e
        assert negotiator.negotiated_functions == 0
        assert negotiator.negotiated_device_type is None

    def test_component_initialization_consistency(self):
        """Test that all components initialize consistently across different instances."""
        # Create multiple instances and verify they all start the same way
        screens = [ScreenBuffer(24, 80) for _ in range(3)]
        parsers = [DataStreamParser(screen) for screen in screens]

        # All screens should be identical
        for screen in screens:
            assert screen.rows == 24
            assert screen.cols == 80
            assert screen.get_position() == (0, 0)
            assert len(screen.buffer) == 24 * 80

        # All parsers should be identical
        for parser in parsers:
            assert parser._pos == 0
            assert parser._data in (None, b"")

    def test_invalid_screen_buffer_dimensions(self):
        """Test error handling for invalid screen buffer dimensions."""
        # Test with invalid dimensions
        with pytest.raises(ValueError):
            ScreenBuffer(0, 80)  # Zero rows

        with pytest.raises(ValueError):
            ScreenBuffer(24, 0)  # Zero columns

        with pytest.raises(ValueError):
            ScreenBuffer(-1, 80)  # Negative rows

        with pytest.raises(ValueError):
            ScreenBuffer(24, -1)  # Negative columns
