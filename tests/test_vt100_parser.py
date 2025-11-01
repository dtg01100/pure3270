"""
Tests for VT100 parser functionality.

This module provides comprehensive unit tests for the VT100Parser class,
covering escape sequence parsing, cursor movement, screen manipulation,
character set handling, and error scenarios.
"""

from unittest.mock import MagicMock, Mock

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.vt100_parser import VT100Parser, VT100ParserState


class TestVT100ParserState:
    """Test VT100ParserState class functionality."""

    def test_initialization(self):
        """Test VT100ParserState initialization."""
        state = VT100ParserState()
        assert state.current_row == 0
        assert state.current_col == 0
        assert state.saved_row == 0
        assert state.saved_col == 0
        assert state.charset == "B"
        assert state.graphics_charset == "0"
        assert state.is_alt_charset is False
        assert state.parser_pos == 0

    def test_save_from_parser(self):
        """Test saving state from parser."""
        parser = Mock()
        parser.current_row = 5
        parser.current_col = 10
        parser.saved_row = 2
        parser.saved_col = 3
        parser.charset = "A"
        parser.graphics_charset = "1"
        parser.is_alt_charset = True
        parser._parser = Mock()
        parser._parser._pos = 42

        state = VT100ParserState()
        state.save_from_parser(parser)

        assert state.current_row == 5
        assert state.current_col == 10
        assert state.saved_row == 2
        assert state.saved_col == 3
        assert state.charset == "A"
        assert state.graphics_charset == "1"
        assert state.is_alt_charset is True
        assert state.parser_pos == 42

    def test_restore_to_parser(self):
        """Test restoring state to parser."""
        parser = Mock()
        parser._parser = Mock()
        parser._parser._text = "some text"

        state = VT100ParserState()
        state.current_row = 7
        state.current_col = 15
        state.saved_row = 1
        state.saved_col = 4
        state.charset = "C"
        state.graphics_charset = "2"
        state.is_alt_charset = False
        state.parser_pos = 55

        state.restore_to_parser(parser)

        assert parser.current_row == 7
        assert parser.current_col == 15
        assert parser.saved_row == 1
        assert parser.saved_col == 4
        assert parser.charset == "C"
        assert parser.graphics_charset == "2"
        assert parser.is_alt_charset is False
        assert parser._parser._pos == min(55, len(parser._parser._text))


class TestVT100ParserInitialization:
    """Test VT100Parser initialization and configuration."""

    def test_initialization(self):
        """Test VT100Parser initialization."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        assert parser.screen_buffer == screen_buffer
        assert parser.current_row == 0
        assert parser.current_col == 0
        assert parser.saved_row == 0
        assert parser.saved_col == 0
        assert parser.charset == "B"
        assert parser.graphics_charset == "0"
        assert parser.is_alt_charset is False
        assert parser._parser is None
        assert parser._last_good_state is None
        assert parser._error_recovery_enabled is True

    def test_error_recovery_methods(self):
        """Test error recovery enable/disable methods."""
        screen_buffer = Mock(spec=ScreenBuffer)
        parser = VT100Parser(screen_buffer)

        # Test initial state
        assert parser.is_error_recovery_enabled() is True

        # Test disable
        parser.disable_error_recovery()
        assert parser.is_error_recovery_enabled() is False

        # Test enable
        parser.enable_error_recovery()
        assert parser.is_error_recovery_enabled() is True


class TestVT100ParserBoundsChecking:
    """Test bounds checking and safe buffer access."""

    def test_validate_screen_buffer_bounds_valid(self):
        """Test bounds validation with valid coordinates."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)

        parser = VT100Parser(screen_buffer)

        assert parser._validate_screen_buffer_bounds(0, 0) is True
        assert parser._validate_screen_buffer_bounds(23, 79) is True
        assert parser._validate_screen_buffer_bounds(12, 40) is True

    def test_validate_screen_buffer_bounds_invalid(self):
        """Test bounds validation with invalid coordinates."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)

        parser = VT100Parser(screen_buffer)

        assert parser._validate_screen_buffer_bounds(-1, 0) is False
        assert parser._validate_screen_buffer_bounds(0, -1) is False
        assert parser._validate_screen_buffer_bounds(24, 0) is False
        assert parser._validate_screen_buffer_bounds(0, 80) is False
        assert parser._validate_screen_buffer_bounds(25, 81) is False

    def test_validate_screen_buffer_bounds_no_buffer(self):
        """Test bounds validation with no buffer."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = None

        parser = VT100Parser(screen_buffer)

        assert parser._validate_screen_buffer_bounds(0, 0) is False

    def test_safe_buffer_access_valid(self):
        """Test safe buffer access with valid coordinates."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)

        parser = VT100Parser(screen_buffer)

        # Position (0, 0) should be 0
        assert parser._safe_buffer_access(0, 0) == 0
        # Position (1, 1) should be 81
        assert parser._safe_buffer_access(1, 1) == 81
        # Position (23, 79) should be 1919
        assert parser._safe_buffer_access(23, 79) == 1919

    def test_safe_buffer_access_invalid(self):
        """Test safe buffer access with invalid coordinates."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)

        parser = VT100Parser(screen_buffer)

        assert parser._safe_buffer_access(-1, 0) == -1
        assert parser._safe_buffer_access(0, -1) == -1
        assert parser._safe_buffer_access(24, 0) == -1
        assert parser._safe_buffer_access(0, 80) == -1

    def test_safe_buffer_access_out_of_buffer(self):
        """Test safe buffer access when position exceeds buffer length."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * 100  # Smaller than expected

        parser = VT100Parser(screen_buffer)

        # Position that would be valid but exceeds actual buffer
        # Row 1, col 0 = position 80, but buffer only has 100 elements (0-99)
        # But the bounds check passes first, so it returns 80
        assert (
            parser._safe_buffer_access(1, 0) == 80
        )  # Position 80, even though buffer is short


class TestVT100ParserBasicParsing:
    """Test basic parsing functionality."""

    def test_parse_empty_data(self):
        """Test parsing empty data."""
        screen_buffer = Mock(spec=ScreenBuffer)
        parser = VT100Parser(screen_buffer)

        parser.parse(b"")

        # Should not crash
        assert parser.current_row == 0
        assert parser.current_col == 0

    def test_parse_regular_text(self):
        """Test parsing regular ASCII text."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)
        screen_buffer._ascii_mode = True

        parser = VT100Parser(screen_buffer)

        parser.parse(b"Hello World")

        # Check that characters were written
        assert screen_buffer.buffer[0] == ord("H")
        assert screen_buffer.buffer[1] == ord("e")
        assert screen_buffer.buffer[2] == ord("l")
        assert screen_buffer.buffer[3] == ord("l")
        assert screen_buffer.buffer[4] == ord("o")
        assert screen_buffer.buffer[5] == ord(" ")
        assert screen_buffer.buffer[6] == ord("W")
        assert screen_buffer.buffer[7] == ord("o")
        assert screen_buffer.buffer[8] == ord("r")
        assert screen_buffer.buffer[9] == ord("l")
        assert screen_buffer.buffer[10] == ord("d")

        # Cursor should have moved
        assert parser.current_col == 11

    def test_parse_newline(self):
        """Test parsing newline character."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)

        parser = VT100Parser(screen_buffer)

        parser.parse(b"Line1\nLine2")

        assert parser.current_row == 1
        assert parser.current_col == 5  # "Line2" is 5 characters

    def test_parse_carriage_return(self):
        """Test parsing carriage return."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)

        parser = VT100Parser(screen_buffer)

        parser.parse(b"ABC\rDEF")

        assert parser.current_row == 0
        assert (
            parser.current_col == 3
        )  # CR resets to column 0, then "DEF" advances to column 3

    def test_parse_tab(self):
        """Test parsing tab character."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)

        parser = VT100Parser(screen_buffer)

        parser.parse(b"AB\tC")

        # "A" at 0, "B" at 1, tab from 2 moves to next 8-char boundary (8), "C" at 8
        assert parser.current_col == 9

    def test_parse_backspace(self):
        """Test parsing backspace character."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)

        parser = VT100Parser(screen_buffer)

        parser.parse(b"ABC\bD")

        assert parser.current_col == 3  # Backspace moves cursor back

    def test_parse_bell(self):
        """Test parsing bell character (should be ignored)."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)

        parser = VT100Parser(screen_buffer)

        parser.parse(b"AB\x07C")

        assert parser.current_col == 3  # Bell should be ignored


class TestVT100ParserEscapeSequences:
    """Test escape sequence parsing."""

    def test_escape_sequence_cursor_position(self):
        """Test ESC [ H cursor position sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        parser.parse(b"\x1b[10;20H")

        assert parser.current_row == 9  # 0-based
        assert parser.current_col == 19  # 0-based

    def test_escape_sequence_cursor_position_f(self):
        """Test ESC [ f cursor position sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        parser.parse(b"\x1b[5;15f")

        assert parser.current_row == 4  # 0-based
        assert parser.current_col == 14  # 0-based

    def test_escape_sequence_cursor_up(self):
        """Test ESC [ A cursor up sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.current_row = 10

        parser.parse(b"\x1b[3A")

        assert parser.current_row == 7  # 10 - 3
        assert parser.current_col == 0

    def test_escape_sequence_cursor_down(self):
        """Test ESC [ B cursor down sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.current_row = 5

        parser.parse(b"\x1b[2B")

        assert parser.current_row == 7  # 5 + 2
        assert parser.current_col == 0

    def test_escape_sequence_cursor_forward(self):
        """Test ESC [ C cursor forward sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.current_col = 10

        parser.parse(b"\x1b[5C")

        assert parser.current_row == 0
        assert parser.current_col == 15  # 10 + 5

    def test_escape_sequence_cursor_backward(self):
        """Test ESC [ D cursor backward sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.current_col = 10

        parser.parse(b"\x1b[3D")

        assert parser.current_row == 0
        assert parser.current_col == 7  # 10 - 3

    def test_escape_sequence_save_cursor(self):
        """Test ESC 7 save cursor sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.current_row = 5
        parser.current_col = 10

        parser.parse(b"\x1b7")

        assert parser.saved_row == 5
        assert parser.saved_col == 10

    def test_escape_sequence_restore_cursor(self):
        """Test ESC 8 restore cursor sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.saved_row = 3
        parser.saved_col = 7

        parser.parse(b"\x1b8")

        assert parser.current_row == 3
        assert parser.current_col == 7

    def test_escape_sequence_csi_save_cursor(self):
        """Test ESC [ s CSI save cursor sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.current_row = 8
        parser.current_col = 12

        parser.parse(b"\x1b[s")

        assert parser.saved_row == 8
        assert parser.saved_col == 12

    def test_escape_sequence_csi_restore_cursor(self):
        """Test ESC [ u CSI restore cursor sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.saved_row = 4
        parser.saved_col = 9

        parser.parse(b"\x1b[u")

        assert parser.current_row == 4
        assert parser.current_col == 9

    def test_escape_sequence_index(self):
        """Test ESC D index sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.current_row = 5

        parser.parse(b"\x1bD")

        assert parser.current_row == 6

    def test_escape_sequence_reverse_index(self):
        """Test ESC M reverse index sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.current_row = 5

        parser.parse(b"\x1bM")

        assert parser.current_row == 4

    def test_escape_sequence_reset(self):
        """Test ESC c reset sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.clear = Mock()

        parser = VT100Parser(screen_buffer)
        parser.current_row = 10
        parser.current_col = 20
        parser.charset = "A"
        parser.is_alt_charset = True

        parser.parse(b"\x1bc")

        assert parser.current_row == 0
        assert parser.current_col == 0
        assert parser.saved_row == 0
        assert parser.saved_col == 0
        assert parser.charset == "B"
        assert parser.graphics_charset == "0"
        assert parser.is_alt_charset is False
        screen_buffer.clear.assert_called_once()

    def test_escape_sequence_designate_g0_charset(self):
        """Test ESC ( designate G0 charset sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        parser.parse(b"\x1b(A")

        assert parser.charset == "A"

    def test_escape_sequence_designate_g1_charset(self):
        """Test ESC ) designate G1 charset sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        parser.parse(b"\x1b)B")

        assert parser.graphics_charset == "B"

    def test_escape_sequence_shift_out(self):
        """Test SO (Shift Out) sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        parser.parse(b"\x0e")

        assert parser.is_alt_charset is True

    def test_escape_sequence_shift_in(self):
        """Test SI (Shift In) sequence."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.is_alt_charset = True

        parser.parse(b"\x0f")

        assert parser.is_alt_charset is False


class TestVT100ParserScreenManipulation:
    """Test screen manipulation commands."""

    def test_erase_display_from_cursor(self):
        """Test ESC [ J erase display from cursor."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [ord("X")] * (24 * 80)
        screen_buffer._ascii_mode = True

        parser = VT100Parser(screen_buffer)
        parser.current_row = 1
        parser.current_col = 2

        parser.parse(b"\x1b[J")

        # Check that everything from position (1,2) onwards is cleared
        start_pos = 1 * 80 + 2
        for i in range(start_pos, 24 * 80):
            assert screen_buffer.buffer[i] == 0x20  # Space in ASCII mode

    def test_erase_display_to_cursor(self):
        """Test ESC [ 1 J erase display to cursor."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [ord("X")] * (24 * 80)
        screen_buffer._ascii_mode = True

        parser = VT100Parser(screen_buffer)
        parser.current_row = 1
        parser.current_col = 2

        parser.parse(b"\x1b[1J")

        # Check that everything from start to position (1,2) is cleared
        end_pos = 1 * 80 + 2
        for i in range(end_pos + 1):
            assert screen_buffer.buffer[i] == 0x20  # Space in ASCII mode

    def test_erase_display_entire(self):
        """Test ESC [ 2 J erase entire display."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [ord("X")] * (24 * 80)
        screen_buffer.clear = Mock()

        parser = VT100Parser(screen_buffer)

        parser.parse(b"\x1b[2J")

        screen_buffer.clear.assert_called_once()

    def test_erase_line_from_cursor(self):
        """Test ESC [ K erase line from cursor."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [ord("X")] * (24 * 80)
        screen_buffer._ascii_mode = True

        parser = VT100Parser(screen_buffer)
        parser.current_row = 1
        parser.current_col = 2

        parser.parse(b"\x1b[K")

        # Check that current line from column 2 onwards is cleared
        line_start = 1 * 80
        for i in range(2, 80):
            assert screen_buffer.buffer[line_start + i] == 0x20

    def test_erase_line_to_cursor(self):
        """Test ESC [ 1 K erase line to cursor."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [ord("X")] * (24 * 80)
        screen_buffer._ascii_mode = True

        parser = VT100Parser(screen_buffer)
        parser.current_row = 1
        parser.current_col = 2

        parser.parse(b"\x1b[1K")

        # Check that current line from start to column 2 is cleared
        line_start = 1 * 80
        for i in range(3):  # 0, 1, 2
            assert screen_buffer.buffer[line_start + i] == 0x20

    def test_erase_line_entire(self):
        """Test ESC [ 2 K erase entire line."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [ord("X")] * (24 * 80)
        screen_buffer._ascii_mode = True

        parser = VT100Parser(screen_buffer)
        parser.current_row = 1

        parser.parse(b"\x1b[2K")

        # Check that entire line is cleared
        line_start = 1 * 80
        for i in range(80):
            assert screen_buffer.buffer[line_start + i] == 0x20


class TestVT100ParserErrorHandling:
    """Test error handling and recovery."""

    def test_unicode_decode_error_recovery(self):
        """Test recovery from Unicode decode errors."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        # Invalid UTF-8 sequence
        invalid_data = b"\xff\xfe"

        # Should not crash and should recover
        parser.parse(invalid_data)

        # Parser should still be in valid state
        assert parser.current_row == 0
        assert parser.current_col == 0

    def test_parser_error_recovery(self):
        """Test parser error recovery mechanism."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)
        screen_buffer._ascii_mode = True

        parser = VT100Parser(screen_buffer)

        # First, set up a good state
        parser.parse(b"Valid text")
        assert parser.current_col == 10

        # Then send a cursor position command with out-of-bounds coordinates
        # Parser should clamp to valid screen bounds (this is correct VT100 behavior)
        parser.parse(b"\x1b[999;999H")  # Out-of-bounds position

        # Should clamp to maximum valid position (row 23, col 79 for 24x80 screen)
        assert parser.current_row == 23  # Clamped to screen bottom
        assert parser.current_col == 79  # Clamped to rightmost column

    def test_error_recovery_disabled(self):
        """Test behavior when error recovery is disabled."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)
        screen_buffer._ascii_mode = True

        parser = VT100Parser(screen_buffer)
        parser.disable_error_recovery()

        # This should not crash even with recovery disabled
        parser.parse(b"Valid text")
        assert parser.current_col == 10

    def test_incomplete_escape_sequence(self):
        """Test handling of incomplete escape sequences."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        # Incomplete CSI sequence
        parser.parse(b"\x1b[")

        # Should not crash
        assert parser.current_row == 0
        assert parser.current_col == 0

    def test_invalid_csi_parameters(self):
        """Test handling of invalid CSI parameters."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)  # Add missing buffer attribute
        screen_buffer._ascii_mode = True

        parser = VT100Parser(screen_buffer)

        # Invalid parameters (non-numeric) - "a" will be treated as CSI command,
        # "bcH" will be printed as regular text
        parser.parse(b"\x1b[abcH")

        # Cursor should be at column 3 (printed "bcH")
        # Parser handles this gracefully without crashing
        assert parser.current_row == 0
        assert parser.current_col == 3  # Printed 3 characters: b, c, H


class TestVT100ParserEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_cursor_bounds_clamping(self):
        """Test cursor position clamping to screen bounds."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        # Try to move cursor beyond bounds
        parser.parse(b"\x1b[100;200H")

        assert parser.current_row == 23  # Clamped to max
        assert parser.current_col == 79  # Clamped to max

    def test_cursor_negative_position(self):
        """Test cursor position with negative values."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        # Negative positions should be clamped to 0
        parser.parse(b"\x1b[-5;-10H")

        assert parser.current_row == 0
        assert parser.current_col == 0

    def test_zero_parameters_default_to_one(self):
        """Test that zero parameters default to 1."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)
        parser.current_row = 5

        # ESC [ 0 A should move up 1 (default)
        parser.parse(b"\x1b[0A")

        assert parser.current_row == 4  # 5 - 1

    def test_empty_csi_parameters(self):
        """Test CSI sequences with empty parameters."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        # ESC [ ; H should default to 1;1
        parser.parse(b"\x1b[;H")

        assert parser.current_row == 0  # 1 - 1
        assert parser.current_col == 0  # 1 - 1

    def test_multiple_semicolons(self):
        """Test CSI sequences with multiple semicolons."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        # ESC [ ; ; H should handle gracefully
        parser.parse(b"\x1b[;;H")

        assert parser.current_row == 0
        assert parser.current_col == 0

    def test_cursor_movement_bounds(self):
        """Test cursor movement respects bounds."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80

        parser = VT100Parser(screen_buffer)

        # Move cursor to edge
        parser.current_col = 79

        # Try to move further right
        parser.parse(b"\x1b[10C")

        assert parser.current_col == 79  # Should not move beyond edge

        # Move cursor to top
        parser.current_row = 0

        # Try to move further up
        parser.parse(b"\x1b[5A")

        assert parser.current_row == 0  # Should not move beyond edge

    def test_line_wrapping(self):
        """Test automatic line wrapping."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)

        parser = VT100Parser(screen_buffer)

        # Write characters to fill a line
        long_text = "A" * 80
        parser.parse(long_text.encode())

        assert parser.current_row == 1  # Should wrap to next line
        assert parser.current_col == 0  # Should be at start of line

    def test_buffer_write_errors(self):
        """Test graceful handling of buffer write errors."""
        screen_buffer = Mock(spec=ScreenBuffer)
        screen_buffer.rows = 24
        screen_buffer.cols = 80
        screen_buffer.buffer = [0] * (24 * 80)
        screen_buffer._ascii_mode = True

        # Make buffer access fail
        def failing_access(row, col):
            raise IndexError("Simulated buffer error")

        parser = VT100Parser(screen_buffer)
        parser._safe_buffer_access = failing_access

        # Should not crash - the error is caught in _write_char
        parser.parse(b"Test")

        # Cursor should still advance even with buffer write errors
        assert parser.current_col == 4  # Should still advance cursor
