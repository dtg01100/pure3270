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
        selected: bool = False,
        intensity: int = 0,  # 0=normal, 1=highlighted, 2=non-display, 3=blink
        color: int = 0,  # 0=neutral/default, 1=blue, 2=red, 3=pink, etc.
        background: int = 0,  # 0=neutral/default, 1=blue, 2=red, 3=pink, etc.
        validation: int = 0,  # 0=no validation, 1=mandatory fill, 2=trigger
        outlining: int = 0,  # 0=no outline, 1=underscore, 2=rightline, 3=overline
        content: Optional[bytes] = None,
    ):
        """
        Initialize a Field.

        :param start: Tuple of (row, col) for field start position.
        :param end: Tuple of (row, col) for field end position.
        :param protected: Whether the field is protected (non-input).
        :param numeric: Whether the field accepts only numeric input.
        :param modified: Whether the field has been modified.
        :param selected: Whether the field is selected.
        :param intensity: Field intensity (0=normal, 1=highlighted, 2=non-display, 3=blink).
        :param color: Foreground color (0=default, 1=blue, 2=red, etc.).
        :param background: Background color/highlight (0=default, 1=blue, 2=red, etc.).
        :param validation: Validation attribute (0=none, 1=mandatory, 2=trigger).
        :param outlining: Outlining attribute (0=none, 1=underscore, 2=rightline, 3=overline).
        :param content: Initial EBCDIC content bytes.
        """
        self.start = start
        self.end = end
        self.protected = protected
        self.numeric = numeric
        self.modified = modified
        self.selected = selected
        self.intensity = intensity
        self.color = color
        self.background = background
        self.validation = validation
        self.outlining = outlining
        self.content = content or b""

    def get_content(self) -> str:
        """Get field content as Unicode string."""
        if not self.content:
            return ""
        codec = EBCDICCodec()
        decoded, _ = codec.decode(self.content)
        return decoded

    def set_content(self, text: str):
        """Set field content from Unicode string."""
        codec = EBCDICCodec()
        encoded, _ = codec.encode(text)
        self.content = encoded
        self.modified = True

    def __repr__(self) -> str:
        return f"Field(start={self.start}, end={self.end}, protected={self.protected}, intensity={self.intensity})"


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
        # EBCDIC character buffer - initialize to spaces
        self.buffer = bytearray(b"\x40" * self.size)
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
        self.buffer = bytearray(b"\x40" * self.size)
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

    def write_char(
        self,
        ebcdic_byte: int,
        row: int,
        col: int,
        protected: bool = False,
        circumvent_protection: bool = False,
    ):
        """
        Write an EBCDIC character to the buffer at position.

        :param ebcdic_byte: EBCDIC byte value.
        :param row: Row position.
        :param col: Column position.
        :param protected: Protection attribute to set.
        :param circumvent_protection: If True, write even to protected fields.
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            pos = row * self.cols + col
            attr_offset = pos * 3
            is_protected = bool(self.attributes[attr_offset] & 0x40)  # Bit 6: protected
            if is_protected and not circumvent_protection:
                return  # Skip writing to protected field
            self.buffer[pos] = ebcdic_byte
            # Set protection bit (bit 6)
            self.attributes[attr_offset] = (self.attributes[attr_offset] & 0xBF) | (
                0x40 if protected else 0x00
            )

            # Update field content and mark as modified if this position belongs to a field
            self._update_field_content(row, col, ebcdic_byte)

    def _update_field_content(self, row: int, col: int, ebcdic_byte: int):
        """
        Update the field content when a character is written to a position.

        :param row: Row position.
        :param col: Column position.
        :param ebcdic_byte: EBCDIC byte value written.
        """
        # Find the field that contains this position
        for field in self.fields:
            start_row, start_col = field.start
            end_row, end_col = field.end

            # Check if the position is within this field
            if start_row <= row <= end_row and (
                start_row != end_row or (start_col <= col <= end_col)
            ):
                # Position is within this field, mark as modified
                field.modified = True

                # For now, we'll just mark the field as modified
                # A more complete implementation would update the field's content buffer
                break

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
                protected = bool(
                    self.attributes[attr_offset] & 0x40
                )  # Bit 6: protected
                if not in_field and not protected:
                    in_field = True
                    start = (row, col)
                elif in_field and protected:
                    in_field = False
                    end = (row, col - 1) if col > 0 else (row, self.cols - 1)
                    # Calculate content from start to end
                    start_pos = start[0] * self.cols + start[1]
                    end_pos = row * self.cols + (col - 1)
                    content = bytes(self.buffer[start_pos : end_pos + 1])

                    # Extract extended attributes
                    intensity = (
                        self.attributes[attr_offset + 1]
                        if attr_offset + 1 < len(self.attributes)
                        else 0
                    )
                    validation = (
                        self.attributes[attr_offset + 2]
                        if attr_offset + 2 < len(self.attributes)
                        else 0
                    )

                    # Input fields are not protected (protected=False)
                    self.fields.append(
                        Field(
                            start,
                            end,
                            protected=False,
                            content=content,
                            intensity=intensity,
                            validation=validation,
                        )
                    )
        if in_field:
            end = (self.rows - 1, self.cols - 1)
            # Calculate content from start to end
            start_pos = start[0] * self.cols + start[1]
            end_pos = end[0] * self.cols + end[1]
            content = bytes(self.buffer[start_pos : end_pos + 1])
            # Determine protection status of the final field
            end_pos_attr = end_pos * 3
            is_protected = bool(
                self.attributes[end_pos_attr] & 0x40
            )  # Bit 6: protected

            # Extract extended attributes
            intensity = (
                self.attributes[end_pos_attr + 1]
                if end_pos_attr + 1 < len(self.attributes)
                else 0
            )
            validation = (
                self.attributes[end_pos_attr + 2]
                if end_pos_attr + 2 < len(self.attributes)
                else 0
            )

            self.fields.append(
                Field(
                    start,
                    end,
                    protected=is_protected,
                    content=content,
                    intensity=intensity,
                    validation=validation,
                )
            )

    def to_text(self) -> str:
        """
        Convert screen buffer to Unicode text string.

        :return: Multi-line string representation.
        """
        codec = EBCDICCodec()
        lines = []
        for row in range(self.rows):
            line_bytes = bytes(self.buffer[row * self.cols : (row + 1) * self.cols])
            line_text, _ = codec.decode(line_bytes)
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

    def set_modified(self, row: int, col: int, modified: bool = True):
        """Set modified flag for position."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            pos = row * self.cols + col
            attr_offset = pos * 3 + 2  # Assume byte 2 for modified
            self.attributes[attr_offset] = 0x01 if modified else 0x00

    def is_position_modified(self, row: int, col: int) -> bool:
        """Check if position is modified."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            pos = row * self.cols + col
            attr_offset = pos * 3 + 2
            return bool(self.attributes[attr_offset])
        return False

    def __repr__(self) -> str:
        return f"ScreenBuffer({self.rows}x{self.cols}, fields={len(self.fields)})"

    def get_field_at_position(self, row: int, col: int) -> Optional[Field]:
        """Get the field containing the given position, if any."""
        for field in self.fields:
            start_row, start_col = field.start
            end_row, end_col = field.end
            if start_row <= row <= end_row and start_col <= col <= end_col:
                return field
        return None

    def remove_field(self, field: Field) -> None:
        """Remove a field from the fields list and clear its content in the buffer."""
        if field in self.fields:
            self.fields.remove(field)
            # Clear the buffer content for this field
            start_row, start_col = field.start
            end_row, end_col = field.end
            for r in range(start_row, end_row + 1):
                for c in range(start_col, end_col + 1):
                    if r < self.rows and c < self.cols:
                        pos = r * self.cols + c
                        self.buffer[pos] = 0x40  # Space in EBCDIC
                        # Clear attributes
                        attr_offset = pos * 3
                        self.attributes[attr_offset : attr_offset + 3] = b"\x00\x00\x00"
        # Re-detect fields to update boundaries
        self._detect_fields()

    def update_fields(self) -> None:
        """Update field detection and attributes."""
        self._detect_fields()
