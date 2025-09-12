"""
Printer buffer and rendering logic for 3287 printer emulation.
"""
import logging

logger = logging.getLogger(__name__)


class PrinterBuffer:
    def __init__(self):
        self._buffer = []
        self.reset()

    def reset(self):
        """Resets the printer buffer."""
        self._buffer = []
        self._current_line = []
        self._column = 0
        self._row = 0

    def write_scs_data(self, data: bytes):
        """Processes incoming SCS data."""
        # This is a simplified implementation.
        # Full implementation would involve parsing SCS commands like text,
        # line feed, carriage return, form feed, etc.
        for byte in data:
            char = chr(byte)
            if char == '\n':  # Line Feed
                self._new_line()
            elif char == '\r':  # Carriage Return
                self._column = 0
            elif 0x20 <= byte <= 0x7E:  # Printable ASCII
                self._current_line.append(char)
                self._column += 1
            # Add more SCS command handling here (e.g., Form Feed, Horizontal Tab)
        self._flush_current_line()

    def _new_line(self):
        """Adds the current line to the buffer and starts a new one."""
        self._flush_current_line()
        self._row += 1
        self._column = 0

    def _flush_current_line(self):
        """Flushes the current line to the buffer."""
        if self._current_line:
            self._buffer.append("".join(self._current_line))
            self._current_line = []

    def get_rendered_output(self) -> str:
        """Returns the current rendered output as a string."""
        # For simplicity, join all lines with newlines.
        # A real renderer might handle page breaks, margins, etc.
        return "\n".join(self._buffer) + "".join(self._current_line)

    def get_buffer_content(self) -> list:
        """Returns the raw buffer content (list of lines)."""
        return self._buffer + ["".join(self._current_line)]

    def __str__(self):
        return self.get_rendered_output()

    def update_status(self, status_code: int):
        """
        Updates the printer's internal status.
        This method can be expanded to handle various printer status codes.
        """
        # For now, just log the status. In a real scenario, this would update
        # internal state variables, e.g., self._status = status_code
        # and potentially trigger events or state transitions.
        logger.debug(f"Printer status updated to: 0x{status_code:02x}")