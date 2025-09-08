"""Screen buffer management for 3270 emulation."""

from typing import List, Tuple, Optional
from .ebcdic import EBCDICCodec

class Field:
    """Represents a 3270 field with content, attributes, and boundaries."""

    def __init__(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        protected: bool = False,
        numeric: bool = False,
        modified: bool = False,
        content: Optional[bytes] = None,
    ):
        """
        Initialize a Field.

        :param start: Tuple of (row, col) for field start position.
        :param end: Tuple of (row, col) for field end position.
        :param protected: Whether the field is protected (non-input).
        :param numeric: Whether the field accepts only numeric input.
        :param modified: Whether the field has been modified.
        :param content: Initial EBCDIC content bytes.
        """
        self.start = start
        self.end = end
        self.protected = protected
        self.numeric = numeric
        self.modified = modified
        self.content = content or b""

    def get_content(self) -> str:
        """Get field content as Unicode string."""
        if not self.content:
            return ""
        codec = EBCDICCodec()
        return codec.decode(self.content)

    def set_content(self, text: str):
        """Set field content from Unicode string."""
        codec = EBCDICCodec()
        self.content = codec.encode(text)
        self.modified = True

    def __repr__(self) -> str:
        return f"Field(start={self.start}, end={self.end}, protected={self.protected})"

class ScreenBuffer:
    """Manages the 3270 screen buffer, including characters, attributes, and fields."""

    def __init__(self, rows: int = 24, cols: int = 80):
        """
        Initialize the ScreenBuffer.

        :param rows: Number of rows (default 24).
        :param cols: Number of columns (default 80).
        """
        self.rows = rows
        self.cols = cols
        self.size = rows * cols
        # EBCDIC character buffer
        self.buffer = bytearray(self.size)
        # Attributes buffer: 3 bytes per position (protection, foreground, background/highlight)
        self.attributes = bytearray(self.size * 3)
        # List of fields
        self.fields: List[Field] = []
        # Cursor position
        self.cursor_row = 0
        self.cursor_col = 0
        # Default field attributes
        self._default_protected = True
        self._default_numeric = False

    def clear(self):
        """Clear the screen buffer and reset fields."""
        self.buffer = bytearray(self.size)
        self.attributes = bytearray(self.size * 3)
        self.fields = []
        self.cursor_row = 0
        self.cursor_col = 0

    def set_position(self, row: int, col: int):
        """Set cursor position."""
        self.cursor_row = row
        self.cursor_col = col

    def get_position(self) -> Tuple[int, int]:
        """Get current cursor position."""
        return (self.cursor_row, self.cursor_col)

    def write_char(self, ebcdic_byte: int, row: int, col: int, protected: bool = False):
        """
        Write an EBCDIC character to the buffer at position.

        :param ebcdic_byte: EBCDIC byte value.
        :param row: Row position.
        :param col: Column position.
        :param protected: Protection attribute.
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            pos = row * self.cols + col
            self.buffer[pos] = ebcdic_byte
            attr_offset = pos * 3
            # Set protection bit (simplified: byte 0 bit 1)
            self.attributes[attr_offset] = 0x02 if protected else 0x00

    def update_from_stream(self, data: bytes):
        """
        Update buffer from a 3270 data stream (basic implementation).

        :param data: Raw 3270 data stream bytes.
        """
        i = 0
        while i < len(data):
            order = data[i]
            i += 1
            if order == 0xF5:  # Write
                if i < len(data):
                    i += 1  # skip WCC
                continue
            elif order == 0x10:  # SBA
                if i + 1 < len(data):
                    i += 2  # skip address bytes
                self.set_position(0, 0)  # Address 0x0000 -> row 0, col 0
                continue
            elif order in (0x05, 0x0D):  # Unknown/EOA
                continue
            else:
                # Treat as data byte
                pos = self.cursor_row * self.cols + self.cursor_col
                if pos < self.size:
                    self.buffer[pos] = order
                    self.cursor_col += 1
                    if self.cursor_col >= self.cols:
                        self.cursor_col = 0
                        self.cursor_row += 1
                        if self.cursor_row >= self.rows:
                            self.cursor_row = 0  # wrap around
        # Update fields (basic detection)
        self._detect_fields()

    def _detect_fields(self):
        """Detect field boundaries based on attribute changes (simplified)."""
        self.fields = []
        in_field = False
        start = (0, 0)
        for row in range(self.rows):
            for col in range(self.cols):
                pos = row * self.cols + col
                attr_offset = pos * 3
                protected = bool(self.attributes[attr_offset] & 0x02)
                if not in_field and not protected:
                    in_field = True
                    start = (row, col)
                elif in_field and protected:
                    in_field = False
                    end = (row, col - 1) if col > 0 else (row, self.cols - 1)
                    content = bytes(self.buffer[pos - (col - start[1]):pos])
                    self.fields.append(Field(start, end, protected=True, content=content))
        if in_field:
            end = (self.rows - 1, self.cols - 1)
            content = bytes(self.buffer[start[0] * self.cols + start[1]:])
            self.fields.append(Field(start, end, protected=False, content=content))

    def to_text(self) -> str:
        """
        Convert screen buffer to Unicode text string.

        :return: Multi-line string representation.
        """
        codec = EBCDICCodec()
        lines = []
        for row in range(self.rows):
            line_bytes = bytes(self.buffer[row * self.cols : (row + 1) * self.cols])
            line_text = codec.decode(line_bytes)
            lines.append(line_text)
        return "\n".join(lines)

    def get_field_content(self, field_index: int) -> str:
        """
        Get content of a specific field.

        :param field_index: Index in fields list.
        :return: Unicode string content.
        """
        if 0 <= field_index < len(self.fields):
            return self.fields[field_index].get_content()
        return ""

    def read_modified_fields(self) -> List[Tuple[Tuple[int, int], str]]:
        """
        Read modified fields (RMF support, basic).

        :return: List of (position, content) for modified fields.
        """
        modified = []
        for field in self.fields:
            if field.modified:
                content = field.get_content()
                modified.append((field.start, content))
        return modified

    def __repr__(self) -> str:
        return f"ScreenBuffer({self.rows}x{self.cols}, fields={len(self.fields)})"
