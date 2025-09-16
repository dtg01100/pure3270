"""
VT100 terminal emulator for pure3270 ASCII mode support.

This module provides VT100 escape sequence parsing to support ASCII terminal emulation
as a fallback when TN3270 negotiation fails, matching s3270 behavior.
"""

import logging
import re
from typing import List, Tuple

from .utils import BaseStringParser, ParseError

logger = logging.getLogger(__name__)


class VT100Parser:
    """VT100 escape sequence parser for ASCII terminal emulation."""

    def __init__(self, screen_buffer):
        """
        Initialize VT100 parser.

        Args:
            screen_buffer: ScreenBuffer instance to update with parsed content
        """
        self.screen_buffer = screen_buffer
        self.current_row = 0
        self.current_col = 0
        self.saved_row = 0
        self.saved_col = 0
        self.charset = "B"  # Default charset
        self.graphics_charset = "0"  # Graphics charset
        self.is_alt_charset = False  # Alternative character set mode
        self.parser = None

    def parse(self, data: bytes) -> None:
        """
        Parse VT100 escape sequences and update screen buffer.

        Args:
            data: Raw ASCII data with VT100 escape sequences
        """
        try:
            text = data.decode("ascii", errors="ignore")
            self._parse_text(text)
        except Exception as e:
            logger.warning(f"Error parsing VT100 data: {e}")

    def _parse_text(self, text: str) -> None:
        """
        Parse text with VT100 escape sequences.

        Args:
            text: ASCII text with escape sequences
        """
        self.parser = BaseStringParser(text)
        # Process text character by character
        while self.parser.has_more():
            char = self.parser.peek_char()
            if char == "\x1b":  # ESC character
                # Parse escape sequence
                self._parse_escape_sequence()
            elif char == "\x0e":  # SO (Shift Out) - Activate alternate charset
                self.is_alt_charset = True
                self.parser.advance(1)
            elif char == "\x0f":  # SI (Shift In) - Activate standard charset
                self.is_alt_charset = False
                self.parser.advance(1)
            else:
                # Regular character
                self._write_char(self.parser.read_char())

    def _parse_escape_sequence(self) -> None:
        """
        Parse a VT100 escape sequence, advancing the parser.

        Advances the parser past the ESC and sequence.
        """
        # Already peeked ESC, advance past it
        self.parser.advance(1)
        if not self.parser.has_more():
            return

        next_char = self.parser.peek_char()

        # Check for CSI (Control Sequence Introducer) - ESC [
        if next_char == "[":
            self.parser.advance(1)
            self._parse_csi_sequence()
            return
        # Check for other escape sequences
        elif next_char == "(":
            # ESC ( - Designate G0 Character Set
            self.parser.advance(1)
            if self.parser.has_more():
                self.charset = self.parser.read_char()
        elif next_char == ")":
            # ESC ) - Designate G1 Character Set
            self.parser.advance(1)
            if self.parser.has_more():
                self.graphics_charset = self.parser.read_char()
        elif next_char == "#":
            # ESC # - DEC Double-Height/Width Line
            self.parser.advance(2)
        elif next_char == "7":
            # ESC 7 - Save Cursor
            self._save_cursor()
            self.parser.advance(1)
        elif next_char == "8":
            # ESC 8 - Restore Cursor
            self._restore_cursor()
            self.parser.advance(1)
        elif next_char == "=":
            # ESC = - Application Keypad Mode
            self.parser.advance(1)
        elif next_char == ">":
            # ESC > - Normal Keypad Mode
            self.parser.advance(1)
        elif next_char == "D":
            # ESC D - Index (IND)
            self._index()
            self.parser.advance(1)
        elif next_char == "M":
            # ESC M - Reverse Index (RI)
            self._reverse_index()
            self.parser.advance(1)
        elif next_char == "c":
            # ESC c - Reset
            self._reset()
            self.parser.advance(1)
        else:
            # Simple escape sequence - ESC followed by one character
            self.parser.advance(1)

    def _parse_csi_sequence(self) -> None:
        """
        Parse CSI (Control Sequence Introducer) sequence, advancing the parser.

        Advances the parser past the CSI sequence.
        """
        # Find the end of the sequence (alphabetic final character)
        start_pos = self.parser._pos
        while self.parser.has_more() and not self.parser.peek_char().isalpha():
            self.parser.advance(1)

        if not self.parser.has_more():
            self.parser._pos = len(self.parser._text)
            return

        # Extract parameters
        params_str = self.parser._text[start_pos : self.parser._pos]
        command = self.parser.read_char()

        # Parse parameters
        params = []
        if params_str:
            for param in params_str.split(";"):
                if param.isdigit():
                    params.append(int(param))
                elif param == "":
                    params.append(0)  # Empty parameter defaults to 0
                else:
                    params.append(0)  # Default value for non-numeric
        else:
            params = [0]  # Default parameter

        # Handle commands
        self._handle_csi_command(command, params)

    def _handle_csi_command(self, command: str, params: list) -> None:
        """
        Handle CSI command.

        Args:
            command: Command character
            params: List of parameters
        """
        try:
            if command == "H" or command == "f":  # Cursor Position
                # ESC [ r ; c H or ESC [ r ; c f
                row = params[0] if len(params) > 0 and params[0] > 0 else 1
                col = params[1] if len(params) > 1 and params[1] > 0 else 1
                self._move_cursor(row - 1, col - 1)  # Convert to 0-based
            elif command == "A":  # Cursor Up
                rows = params[0] if len(params) > 0 and params[0] > 0 else 1
                self._move_cursor(max(0, self.current_row - rows), self.current_col)
            elif command == "B":  # Cursor Down
                rows = params[0] if len(params) > 0 and params[0] > 0 else 1
                self._move_cursor(
                    min(self.screen_buffer.rows - 1, self.current_row + rows),
                    self.current_col,
                )
            elif command == "C":  # Cursor Forward
                cols = params[0] if len(params) > 0 and params[0] > 0 else 1
                self._move_cursor(
                    self.current_row,
                    min(self.screen_buffer.cols - 1, self.current_col + cols),
                )
            elif command == "D":  # Cursor Backward
                cols = params[0] if len(params) > 0 and params[0] > 0 else 1
                self._move_cursor(self.current_row, max(0, self.current_col - cols))
            elif command == "J":  # Erase in Display
                param = params[0] if len(params) > 0 else 0
                self._erase_display(param)
            elif command == "K":  # Erase in Line
                param = params[0] if len(params) > 0 else 0
                self._erase_line(param)
            elif command == "s":  # Save Cursor Position
                self._save_cursor()
            elif command == "u":  # Restore Cursor Position
                self._restore_cursor()
            elif command == "m":  # Select Graphic Rendition (SGR)
                self._handle_sgr(params)
            elif command == "n":  # Device Status Report
                # Ignore for now
                pass
            elif command == "h":  # Set Mode
                # Ignore for now
                pass
            elif command == "l":  # Reset Mode
                # Ignore for now
                pass
            else:
                logger.debug(f"Unhandled CSI command: {command} with params {params}")
        except Exception as e:
            logger.warning(f"Error handling CSI command {command}: {e}")

    def _handle_sgr(self, params: List[int]) -> None:
        """
        Handle Select Graphic Rendition (SGR) commands.

        Args:
            params: SGR parameters
        """
        # For now, just consume the parameters
        # In a full implementation, this would handle colors, bold, etc.
        pass

    def _write_char(self, char: str) -> None:
        """
        Write a character to the current cursor position.

        Args:
            char: Character to write
        """
        if char == "\n":
            self.current_row = min(self.screen_buffer.rows - 1, self.current_row + 1)
            self.current_col = 0
        elif char == "\r":
            self.current_col = 0
        elif char == "\t":
            # Tab to next 8-character boundary
            self.current_col = min(
                self.screen_buffer.cols - 1, ((self.current_col // 8) + 1) * 8
            )
        elif char == "\b":
            # Backspace
            if self.current_col > 0:
                self.current_col -= 1
        elif char == "\x07":  # Bell
            # Ignore bell character
            pass
        else:
            # Regular character
            if (
                self.current_row < self.screen_buffer.rows
                and self.current_col < self.screen_buffer.cols
            ):
                # Convert ASCII to EBCDIC for storage in screen buffer
                try:
                    # Try to use the existing EBCDIC translation utilities
                    from ..emulation.ebcdic import translate_ascii_to_ebcdic

                    ebcdic_bytes = translate_ascii_to_ebcdic(char)
                    if ebcdic_bytes:
                        ebcdic_byte = ebcdic_bytes[0]
                        pos = (
                            self.current_row * self.screen_buffer.cols
                            + self.current_col
                        )
                        if pos < len(self.screen_buffer.buffer):
                            self.screen_buffer.buffer[pos] = ebcdic_byte
                    else:
                        # Fallback to space if conversion fails
                        pos = (
                            self.current_row * self.screen_buffer.cols
                            + self.current_col
                        )
                        if pos < len(self.screen_buffer.buffer):
                            self.screen_buffer.buffer[pos] = 0x40  # Space in EBCDIC
                except Exception as e:
                    logger.debug(f"Error converting character '{char}' to EBCDIC: {e}")
                    # Store as space if conversion fails
                    pos = self.current_row * self.screen_buffer.cols + self.current_col
                    if pos < len(self.screen_buffer.buffer):
                        self.screen_buffer.buffer[pos] = 0x40  # Space in EBCDIC

            # Move cursor
            self.current_col += 1
            if self.current_col >= self.screen_buffer.cols:
                self.current_col = 0
                self.current_row = min(
                    self.screen_buffer.rows - 1, self.current_row + 1
                )

    def _move_cursor(self, row: int, col: int) -> None:
        """
        Move cursor to specified position.

        Args:
            row: Row position (0-based)
            col: Column position (0-based)
        """
        self.current_row = max(0, min(self.screen_buffer.rows - 1, row))
        self.current_col = max(0, min(self.screen_buffer.cols - 1, col))

    def _save_cursor(self) -> None:
        """Save current cursor position."""
        self.saved_row = self.current_row
        self.saved_col = self.current_col

    def _restore_cursor(self) -> None:
        """Restore saved cursor position."""
        self.current_row = self.saved_row
        self.current_col = self.saved_col

    def _erase_display(self, param: int) -> None:
        """
        Erase display.

        Args:
            param: Erase parameter
                0: Clear from cursor to end of screen
                1: Clear from beginning of screen to cursor
                2: Clear entire screen
        """
        if param == 0:
            # Clear from cursor to end of screen
            start_pos = self.current_row * self.screen_buffer.cols + self.current_col
            for i in range(start_pos, len(self.screen_buffer.buffer)):
                self.screen_buffer.buffer[i] = 0x40  # Space
        elif param == 1:
            # Clear from beginning of screen to cursor
            end_pos = self.current_row * self.screen_buffer.cols + self.current_col
            for i in range(0, end_pos + 1):
                self.screen_buffer.buffer[i] = 0x40  # Space
        elif param == 2:
            # Clear entire screen
            self.screen_buffer.clear()

    def _erase_line(self, param: int) -> None:
        """
        Erase line.

        Args:
            param: Erase parameter
                0: Clear from cursor to end of line
                1: Clear from beginning of line to cursor
                2: Clear entire line
        """
        if param == 0:
            # Clear from cursor to end of line
            start_pos = self.current_row * self.screen_buffer.cols + self.current_col
            end_pos = (
                self.current_row * self.screen_buffer.cols + self.screen_buffer.cols
            )
            for i in range(start_pos, min(end_pos, len(self.screen_buffer.buffer))):
                self.screen_buffer.buffer[i] = 0x40  # Space
        elif param == 1:
            # Clear from beginning of line to cursor
            start_pos = self.current_row * self.screen_buffer.cols
            end_pos = self.current_row * self.screen_buffer.cols + self.current_col
            for i in range(start_pos, min(end_pos + 1, len(self.screen_buffer.buffer))):
                self.screen_buffer.buffer[i] = 0x40  # Space
        elif param == 2:
            # Clear entire line
            start_pos = self.current_row * self.screen_buffer.cols
            end_pos = (
                self.current_row * self.screen_buffer.cols + self.screen_buffer.cols
            )
            for i in range(start_pos, min(end_pos, len(self.screen_buffer.buffer))):
                self.screen_buffer.buffer[i] = 0x40  # Space

    def _index(self) -> None:
        """Index (IND) - Move cursor down one line, scrolling if needed."""
        if self.current_row < self.screen_buffer.rows - 1:
            self.current_row += 1
        # In a full implementation, this would scroll the screen

    def _reverse_index(self) -> None:
        """Reverse Index (RI) - Move cursor up one line, scrolling if needed."""
        if self.current_row > 0:
            self.current_row -= 1
        # In a full implementation, this would reverse scroll the screen

    def _reset(self) -> None:
        """Reset terminal to initial state."""
        self.current_row = 0
        self.current_col = 0
        self.saved_row = 0
        self.saved_col = 0
        self.charset = "B"
        self.graphics_charset = "0"
        self.is_alt_charset = False
        self.screen_buffer.clear()
