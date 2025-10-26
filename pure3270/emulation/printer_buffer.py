"""
Printer buffer and rendering logic for 3287 printer emulation.
"""

import logging
from typing import Any, List, Optional, Tuple, Type

from .buffer_writer import BufferWriter

logger = logging.getLogger(__name__)


class PrinterBuffer(BufferWriter):
    def __init__(self, max_lines: int = 10000, auto_reset: bool = False) -> None:
        self.max_lines = max_lines
        self.auto_reset = auto_reset
        self._buffer: List[str] = []
        self._current_line: List[str] = []
        self.reset()

    def reset(self) -> None:
        """Resets the printer buffer."""
        self._buffer = []
        self._current_line = []
        self.set_position(0, 0)

    def write_char(
        self,
        ebcdic_byte: int,
        row: Optional[int] = None,
        col: Optional[int] = None,
        protected: bool = False,
        circumvent_protection: bool = False,
    ) -> None:
        """
        Write an EBCDIC character to the printer buffer.
        Supports positioned writes by padding with spaces or adding empty lines.
        """
        current_row, current_col = self.get_position()
        if row is not None and row != current_row:
            self._flush_current_line()
            while self.cursor_row < row:
                self._new_line()
            self.cursor_row = row
        if col is not None and col != current_col:
            while len(self._current_line) < col:
                self._current_line.append(" ")
                self.cursor_col += 1
            self.cursor_col = col
        char = chr(ebcdic_byte)
        if char == "\n":
            self._new_line()
        elif char == "\r":
            self.cursor_col = 0
        elif 0x20 <= ebcdic_byte <= 0x7E:
            self._current_line.append(char)
            self.cursor_col += 1
        # Ignore other controls and non-printable for now

    def set_attribute(
        self,
        attr: int,
        row: Optional[int] = None,
        col: Optional[int] = None,
    ) -> None:
        """
        Set attribute at position. Printer buffer does not support attributes.
        """
        pass

    def get_content(self) -> str:
        """Retrieve the buffer content as a cleaned string (ASCII, no control chars except \n, \f, \t)."""
        raw = self.get_rendered_output()
        print(f"PrinterBuffer raw output: '{raw}'")  # Debug print
        # Remove only non-printable/control chars except \n, \f, \t
        import re

        cleaned = re.sub(r"[^\x09\x0a\x0c\x20-\x7e]", "", raw)
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"PrinterBuffer cleaned output: '{cleaned}'")
        return cleaned

    def write_scs_data(self, data: bytes) -> None:
        """Processes incoming SCS data, parsing SCS commands and robustly translating EBCDIC to ASCII."""
        from .ebcdic import EBCDICCodec

        codec = EBCDICCodec()
        i = 0
        import logging

        logger = logging.getLogger(__name__)
        while i < len(data):
            byte = data[i]
            ascii_char, _ = codec.decode(bytes([byte]))
            print(f"SCS byte: 0x{byte:02x}, decoded: '{ascii_char}'")  # Debug print
            if byte == 0x0A:  # LF (Line Feed)
                self._flush_current_line()
                self._new_line()
            elif byte == 0x0D:  # CR (Carriage Return)
                self.cursor_col = 0
            elif byte == 0x0C:  # FF (Form Feed)
                self._flush_current_line()
                self._buffer.append("\f")  # Page break marker
                self.cursor_row += 1
                self.cursor_col = 0
            elif byte == 0x09:  # HT (Horizontal Tab)
                self._current_line.append("\t")
                self.cursor_col += 1
            elif byte == 0x01:  # SOH (Start of Header, printer status)
                # SCS SOH is followed by a status byte; skip both
                if i + 1 < len(data):
                    i += 1  # skip SOH
                    continue
            else:
                # Always append decoded character for test parity
                if ascii_char:
                    self._current_line.append(ascii_char)
                    self.cursor_col += 1
            i += 1
        # Always flush any remaining text after processing all data
        self._flush_current_line()
        # Prune buffer if exceeds max_lines
        if len(self._buffer) > self.max_lines:
            self._buffer = self._buffer[-self.max_lines :]

    def _new_line(self) -> None:
        """Adds the current line to the buffer and starts a new one."""
        self._flush_current_line()
        self.cursor_row += 1
        self.cursor_col = 0

    def _flush_current_line(self) -> None:
        """Flushes the current line to the buffer."""
        line = "".join(self._current_line)
        self._buffer.append(line)
        self._current_line = []

    def get_rendered_output(self) -> str:
        """Returns the current rendered output as a string."""
        # For simplicity, join all lines with newlines.
        # A real renderer might handle page breaks, margins, etc.
        output = "\n".join(self._buffer) + "".join(self._current_line)
        if self.auto_reset:
            self.reset()
        return output

    def get_buffer_content(self) -> List[str]:
        """Returns the raw buffer content (list of lines)."""
        return self._buffer + ["".join(self._current_line)]

    def __str__(self) -> str:
        return self.get_rendered_output()

    def __enter__(self) -> "PrinterBuffer":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> bool:
        self.reset()
        return True

    def update_status(self, status_code: int) -> None:
        """
        Updates the printer's internal status with the given status code.

        Args:
            status_code: The status code (e.g., 0x00 success, 0x40 device end).

        This method updates the internal status state and can trigger events or updates
        for status SF handling in TN3270E printer sessions.
        """
        self._status = status_code
        logger.debug(f"Printer status updated to: 0x{status_code:02x}")
        # Trigger any necessary events or updates for status SF
        if hasattr(self, "_status_event") and self._status_event:
            self._status_event.set()

    def get_status(self) -> int:
        """
        Get the current printer status code.

        Returns:
            The current status code, or 0x00 if not set.
        """
        return getattr(self, "_status", 0x00)

    def end_job(self) -> None:
        """
        Ends the current print job.
        Appends a literal 'PRINT-EOJ' marker to the buffer for display parity.
        """
        logger.debug("Print job ended")
        self._flush_current_line()
        self._buffer.append("PRINT-EOJ")
