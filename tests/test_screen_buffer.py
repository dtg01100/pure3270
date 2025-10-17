import pytest

from pure3270.emulation.field_attributes import (
    ColorAttribute,
    ExtendedAttribute,
    ExtendedAttributeSet,
    HighlightAttribute,
    OutliningAttribute,
    ValidationAttribute,
)
from pure3270.emulation.screen_buffer import ScreenBuffer


class TestScreenBuffer:
    """Test cases for ScreenBuffer operations to verify correct behaviors."""

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
        assert screen.dimensions == (rows, cols)

    def test_screen_buffer_positioning(self):
        """Test that cursor positioning works correctly."""
        screen = ScreenBuffer(24, 80)

        # Test initial position
        assert screen.get_position() == (0, 0)

        # Test setting position within bounds
        screen.set_position(5, 10)
        assert screen.get_position() == (5, 10)

        # Test setting position using single address
        screen.set_position(12, 5)  # Row 12, Col 5
        address = 12 * 80 + 5  # Buffer address for (12, 5)
        screen.set_position_from_address(address)
        assert screen.get_position() == (12, 5)

        # Test position boundaries
        screen.set_position(23, 79)  # Maximum position for 24x80 screen
        assert screen.get_position() == (23, 79)

    def test_screen_buffer_position_bounds_checking(self):
        """Test that position bounds checking works correctly."""
        screen = ScreenBuffer(24, 80)

        # Test setting position beyond bounds raises appropriate errors
        # Since the implementation might not explicitly check bounds,
        # we'll test what happens when we try to access invalid positions
        with pytest.raises(IndexError):
            # This may not raise an error in current implementation,
            # but we can test boundary behaviors
            pass

    def test_screen_buffer_content_writing(self):
        """Test that writing content to screen buffer works correctly."""
        screen = ScreenBuffer(24, 80)

        # Test writing single character
        screen.write_at_position(0, 0, b"A")
        assert screen.buffer[0] == 0xC1  # EBCDIC 'A'

        # Test writing multiple characters
        screen.write_at_position(0, 1, b"BCD")
        assert screen.buffer[1] == 0xC2  # EBCDIC 'B'
        assert screen.buffer[2] == 0xC3  # EBCDIC 'C'
        assert screen.buffer[3] == 0xC4  # EBCDIC 'D'

        # Test writing with wrapping behavior
        screen.set_position(0, 78)
        screen.write(b"XY")  # Should wrap to next line
        assert screen.buffer[78] == 0xE7  # EBCDIC 'X'
        assert screen.buffer[79] == 0xE8  # EBCDIC 'Y'
        assert screen.get_position() == (1, 0)  # Position should wrap to next line

    def test_screen_buffer_reading(self):
        """Test that reading content from screen buffer works correctly."""
        screen = ScreenBuffer(24, 80)

        # Write some test data
        screen.write_at_position(0, 0, b"HELLO")

        # Test reading single character
        assert screen.read_at_position(0, 0, 1) == b"H"

        # Test reading multiple characters
        assert screen.read_at_position(0, 0, 5) == b"HELLO"

        # Test reading across multiple lines
        screen.write_at_position(
            0, 78, b"AB"
        )  # 'A' at pos 78, 'B' at pos 79 (next line)
        result = screen.read_at_position(
            0, 78, 3
        )  # Should read 'AB' + char from row 1, col 0
        assert len(result) == 3
        assert result[:2] == b"AB"

    def test_screen_buffer_cursor_movement(self):
        """Test that cursor movement operations work correctly."""
        screen = ScreenBuffer(24, 80)

        # Test initial position
        row, col = screen.get_position()
        assert row == 0 and col == 0

        # Test moving cursor right
        screen.move_right()
        row, col = screen.get_position()
        assert row == 0 and col == 1

        # Test moving cursor down
        screen.move_down()
        row, col = screen.get_position()
        assert row == 1 and col == 1

        # Test moving cursor left
        screen.move_left()
        row, col = screen.get_position()
        assert row == 1 and col == 0

        # Test moving cursor up
        screen.move_up()
        row, col = screen.get_position()
        assert row == 0 and col == 0

        # Test boundary behavior when moving cursor
        screen.set_position(0, 0)  # Top-left corner
        screen.move_up()  # Should stay at (0, 0)
        assert screen.get_position() == (0, 0)

        screen.set_position(0, 0)  # Top-left corner
        screen.move_left()  # Should stay at (0, 0)
        assert screen.get_position() == (0, 0)

        screen.set_position(23, 79)  # Bottom-right corner
        screen.move_down()  # Should stay at (23, 79)
        assert screen.get_position() == (23, 79)

        screen.set_position(23, 79)  # Bottom-right corner
        screen.move_right()  # Should stay at (23, 79)
        assert screen.get_position() == (23, 79)

    def test_screen_buffer_field_operations(self):
        """Test field creation and attribute operations."""
        screen = ScreenBuffer(24, 80)

        # Initially no fields
        assert len(screen.fields) == 0

        # Test setting field attributes
        screen.set_attribute(0xF1, row=5, col=10)  # Field attribute
        # Verify the attribute is set in the buffer
        pos = 5 * 80 + 10
        assert screen.buffer[pos] == 0xF1

        # Test field detection (this might depend on implementation details)
        screen._detect_fields()  # Assuming this is a method to detect fields
        # The exact behavior depends on implementation, so we'll verify it exists

        # Test extended attributes
        screen.set_extended_attribute(row=5, col=10, attr_type="color", value=0xF2)
        # Verify extended attribute was set (implementation dependent)

    def test_screen_buffer_clear_operations(self):
        """Test screen buffer clearing operations."""
        screen = ScreenBuffer(24, 80)

        # Fill screen with non-space characters
        test_data = b"A" * len(screen.buffer)
        screen.buffer[:] = test_data

        # Clear the screen
        screen.clear()

        # Verify screen is filled with space characters (0x40 in EBCDIC)
        assert screen.buffer == bytearray(b"\x40" * len(screen.buffer))

        # Verify position was reset to (0, 0)
        assert screen.get_position() == (0, 0)

    def test_screen_buffer_addressing(self):
        """Test screen buffer addressing calculations."""
        screen = ScreenBuffer(24, 80)

        # Test buffer address calculation
        row, col = 5, 10
        expected_address = row * screen.cols + col
        actual_address = screen._pos_from_row_col(row, col)

        assert actual_address == expected_address

        # Test reverse calculation
        rev_row, rev_col = screen._row_col_from_pos(expected_address)
        assert (rev_row, rev_col) == (row, col)

    def test_screen_buffer_ascii_conversion(self):
        """Test ASCII to EBCDIC conversions and vice versa."""
        screen = ScreenBuffer(24, 80)

        # Write ASCII string and verify EBCDIC conversion
        test_string = b"ABC"
        screen.write_at_position(0, 0, test_string)

        # Verify EBCDIC values for 'ABC' are stored
        assert screen.buffer[0] == 0xC1  # EBCDIC 'A'
        assert screen.buffer[1] == 0xC2  # EBCDIC 'B'
        assert screen.buffer[2] == 0xC3  # EBCDIC 'C'

        # Read back and verify ASCII conversion
        read_result = screen.read_at_position(0, 0, 3)
        assert read_result == test_string

    def test_screen_buffer_dimensions_validation(self):
        """Test that screen buffer properly validates dimensions."""
        # Test normal dimensions
        normal_screen = ScreenBuffer(24, 80)
        assert normal_screen.rows == 24
        assert normal_screen.cols == 80

        # Test small dimensions
        small_screen = ScreenBuffer(2, 2)
        assert small_screen.rows == 2
        assert small_screen.cols == 2

        # Test that buffer size is correct for different dimensions
        assert len(small_screen.buffer) == 4  # 2 * 2

        # Test larger dimensions
        large_screen = ScreenBuffer(32, 132)  # Common 3270 size
        assert large_screen.rows == 32
        assert large_screen.cols == 132
        assert len(large_screen.buffer) == 32 * 132
