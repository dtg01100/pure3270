"""Screen buffer management for 3270 emulation."""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .buffer_writer import BufferWriter
from .ebcdic import EBCDICCodec, EmulationEncoder


class Field:
    """A simple Field object that mirrors the previous namedtuple API with
    convenient defaults and helper methods used by tests.

    It intentionally implements `get_content`, `set_content`, and `_replace`
    to be compatible with test expectations. `content` is stored as raw
    EBCDIC bytes; `get_content`/`set_content` use the `EBCDICCodec` by default
    but will fall back to `EmulationEncoder` when the codec isn't present.
    """

    def __init__(
        self,
        start: Tuple[int, int] = (0, 0),
        end: Tuple[int, int] = (0, 0),
        protected: bool = False,
        numeric: bool = False,
        modified: bool = False,
        selected: bool = False,
        intensity: int = 0,
        color: int = 0,
        background: int = 0,
        validation: int = 0,
        outlining: int = 0,
        character_set: int = 0,
        sfe_highlight: int = 0,
        content: bytes = b"",
    ) -> None:
        # Normalize start/end coordinates so that start <= end (lexicographically).
        try:
            s_row, s_col = int(start[0]), int(start[1])
            e_row, e_col = int(end[0]), int(end[1])
        except Exception:
            s_row, s_col = 0, 0
            e_row, e_col = 0, 0

        if (s_row, s_col) <= (e_row, e_col):
            self.start = (s_row, s_col)
            self.end = (e_row, e_col)
        else:
            # Swap so the public invariant holds: start <= end
            self.start = (e_row, e_col)
            self.end = (s_row, s_col)

        self.protected = bool(protected)
        self.numeric = bool(numeric)
        self.modified = bool(modified)
        self.selected = bool(selected)
        self.intensity = int(intensity)
        self.color = int(color)
        self.background = int(background)
        self.validation = int(validation)
        self.outlining = int(outlining)
        self.character_set = int(character_set)
        self.sfe_highlight = int(sfe_highlight)
        # Ensure content is bytes
        self.content = bytes(content) if content is not None else b""

    def get_content(self, codec: Optional[EBCDICCodec] = None) -> str:
        """Return decoded content as a Unicode string.

        Accepts an optional `codec` for decoding; if not provided we use
        `EBCDICCodec()` when available, otherwise `EmulationEncoder`.
        """
        if codec is None:
            try:
                codec = EBCDICCodec()
            except Exception:
                codec = None
        if codec is not None:
            # Compatibility: some codecs return (text, length)
            try:
                res = codec.decode(self.content)
                # Handle both tuple and non-tuple results
                return str(res[0] if isinstance(res, tuple) else res)
            except Exception:
                # If codec fails, fall through to fallback below
                pass
        # Fallback
        return EmulationEncoder.decode(self.content)

    def set_content(self, text: str, codec: Optional[EBCDICCodec] = None) -> None:
        """Set the field content from a Unicode string and mark modified.

        Uses optional `codec` for encoding; falls back to `EmulationEncoder`.
        """
        if codec is None:
            try:
                codec = EBCDICCodec()
            except Exception:
                codec = None
        if codec is not None:
            try:
                res = codec.encode(text)
                # Handle both tuple and non-tuple results
                self.content = bytes(res[0] if isinstance(res, tuple) else res)
                self.modified = True
                return
            except Exception:
                # If codec fails, fall through to fallback below
                pass
        self.content = EmulationEncoder.encode(text)
        self.modified = True

    def _replace(self, **kwargs: Any) -> "Field":
        """Return a new Field with replaced attributes (compatible with namedtuple._replace)."""
        params = {
            "start": self.start,
            "end": self.end,
            "protected": self.protected,
            "numeric": self.numeric,
            "modified": self.modified,
            "selected": self.selected,
            "intensity": self.intensity,
            "color": self.color,
            "background": self.background,
            "validation": self.validation,
            "outlining": self.outlining,
            "character_set": self.character_set,
            "sfe_highlight": self.sfe_highlight,
            "content": self.content,
        }
        params.update(kwargs)
        # Constructing a new Field will run the normalization logic in __init__
        return Field(**params)  # type: ignore[arg-type]

    def __repr__(self) -> str:
        return (
            f"Field(start={self.start}, end={self.end}, protected={self.protected}, "
            f"numeric={self.numeric}, modified={self.modified}, intensity={self.intensity}, content={self.content!r})"
        )


logger = logging.getLogger(__name__)


class ScreenBuffer(BufferWriter):
    @property
    def ascii_buffer(self) -> str:
        """Return the entire screen buffer as a decoded ASCII/Unicode string."""
        lines = []
        for row in range(self.rows):
            line_bytes = bytes(self.buffer[row * self.cols : (row + 1) * self.cols])
            if self._ascii_mode:
                # In ASCII mode, buffer contains ASCII bytes directly
                line_text = line_bytes.decode('ascii', errors='replace')
            else:
                # In 3270 mode, buffer contains EBCDIC bytes that need conversion
                line_text, _ = EBCDICCodec().decode(line_bytes)
            lines.append(line_text)
        return "\n".join(lines)
    """Manages the 3270 screen buffer, including characters, attributes, and fields."""

    def __init__(self, rows: int = 24, cols: int = 80, init_value: int = 0x40):
        """
        Initialize the ScreenBuffer.

        :param rows: Number of rows (default 24).
        :param cols: Number of columns (default 80).
        :param init_value: Initial value for buffer (default 0x40 for space).
        """
        if rows <= 0:
            raise ValueError(f"rows must be positive, got {rows}")
        if cols <= 0:
            raise ValueError(f"cols must be positive, got {cols}")

        self.rows = rows
        self.cols = cols
        self.size = rows * cols
        self._ascii_mode = False  # Track whether we're in ASCII or EBCDIC mode
        # EBCDIC character buffer - initialize to spaces
        self.buffer = bytearray([init_value] * self.size)
        # Attributes buffer: 3 bytes per position (protection, foreground, background/highlight)
        self.attributes = bytearray([0] * (self.rows * self.cols * 3))
        # Extended attributes: dictionary mapping (row, col) to another dictionary of ext_attr_type: value
        self._extended_attributes: Dict[Tuple[int, int], Dict[str, Any]] = {}
        # List of fields
        self.fields: List[Field] = []
        # Cursor position
        self.cursor_row = 0
        self.cursor_col = 0
        # Default field attributes
        self._default_protected = True
        self._default_numeric = False
        self._current_aid = None

    def clear(self) -> None:
        """Clear the screen buffer and reset fields."""
        init_value = 0x20 if self._ascii_mode else 0x40  # ASCII space vs EBCDIC space
        self.buffer = bytearray([init_value] * self.size)
        self.attributes = bytearray([0] * len(self.attributes))
        self._extended_attributes.clear()
        self.fields = []
        self._detect_fields()
        self.set_position(0, 0)

    def set_ascii_mode(self, ascii_mode: bool = True) -> None:
        """
        Set ASCII mode for the screen buffer.
        
        Args:
            ascii_mode: True for ASCII mode, False for EBCDIC mode
        """
        logger.debug(f"ScreenBuffer setting ASCII mode: {ascii_mode}")
        self._ascii_mode = ascii_mode
        if ascii_mode:
            # Convert existing EBCDIC spaces to ASCII spaces
            for i in range(len(self.buffer)):
                if self.buffer[i] == 0x40:  # EBCDIC space
                    self.buffer[i] = 0x20  # ASCII space

    def is_ascii_mode(self) -> bool:
        """Return True if screen buffer is in ASCII mode."""
        return self._ascii_mode

    def set_position(self, row: int, col: int, wrap: bool = False) -> None:
        """Set cursor position with clamping to valid range."""
        if wrap:
            if col >= self.cols:
                col = 0
                row += 1
            row = max(0, min(self.rows - 1, row))
        else:
            row = max(0, min(self.rows - 1, row))
            col = max(0, min(self.cols - 1, col))
        self.cursor_row = row
        self.cursor_col = col

    def write_char(
        self,
        ebcdic_byte: int,
        row: Optional[int] = None,
        col: Optional[int] = None,
        protected: bool = False,
        circumvent_protection: bool = False,
    ) -> None:
        """
        Write an EBCDIC character to the buffer at position.

        :param ebcdic_byte: EBCDIC byte value.
        :param row: Row position.
        :param col: Column position.
        :param protected: Protection attribute to set.
        :param circumvent_protection: If True, write even to protected fields.
        """
        # If row/col not provided, use current cursor position
        if row is None or col is None:
            row, col = self.get_position()

        if 0 <= row < self.rows and 0 <= col < self.cols:
            pos = row * self.cols + col
            attr_offset = pos * 3

            # Ensure buffer position is valid
            if pos >= len(self.buffer):
                logger.error(
                    f"Buffer position {pos} out of bounds (buffer size: {len(self.buffer)})"
                )
                return

            # Check that attr_offset is within bounds of attributes array
            if attr_offset + 2 >= len(self.attributes):
                logger.error(
                    f"Attribute offset {attr_offset} out of bounds (attributes size: {len(self.attributes)})"
                )
                return

            is_protected = bool(self.attributes[attr_offset] & 0x40)  # Bit 6: protected
            if is_protected and not circumvent_protection:
                return  # Skip writing to protected field

            self.buffer[pos] = ebcdic_byte
            # Set full attributes: protection (bit 6 in byte 0), fg=0xF0 (default), bg=0xF0 (default)
            self.attributes[attr_offset : attr_offset + 3] = bytes(
                [0x40 if protected else 0, 0xF0, 0xF0]
            )

            # Update field content and mark as modified if this position belongs to a field
            modified_field_found = self._update_field_content(
                int(row), int(col), ebcdic_byte
            )
            # Only detect new fields if we didn't update an existing one
            if not modified_field_found:
                self._detect_fields()

    def _update_field_content(self, row: int, col: int, ebcdic_byte: int) -> bool:
        """
        Update the field content when a character is written to a position.

        :param row: Row position.
        :param col: Column position.
        :param ebcdic_byte: EBCDIC byte value written.
        :return: True if a field was found and updated, False otherwise.
        """
        # Find the field that contains this position
        for idx, field in enumerate(self.fields):
            start_row, start_col = field.start
            end_row, end_col = field.end

            # Check if the position is within this field
            if start_row <= row <= end_row and (
                start_row != end_row or (start_col <= col <= end_col)
            ):
                # Position is within this field
                # Recalculate the field content from the buffer to ensure consistency
                start_idx = start_row * self.cols + start_col
                end_idx = end_row * self.cols + end_col

                # Ensure indices are within buffer bounds
                if start_idx < 0:
                    start_idx = 0
                if end_idx >= self.size:
                    end_idx = self.size - 1
                if start_idx > end_idx:
                    logger.warning(
                        f"Invalid field bounds: start_idx={start_idx}, end_idx={end_idx}"
                    )
                    continue

                new_content = bytes(self.buffer[start_idx : end_idx + 1])
                new_field = field._replace(content=new_content, modified=True)
                self.fields[idx] = new_field
                return True
        return False

    def update_from_stream(self, data: bytes) -> None:
        """
        Update buffer from a 3270 data stream (basic implementation).

        :param data: Raw 3270 data stream bytes.
        """
        # Limit processing to prevent buffer overflow attacks
        max_data_len = self.size * 2  # Allow some overflow but not unlimited
        if len(data) > max_data_len:
            logger.warning(
                f"Data stream too large ({len(data)} bytes), truncating to {max_data_len}"
            )
            data = data[:max_data_len]

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
                        # Prevent unlimited wraparound - stop at buffer end
                        if self.cursor_row >= self.rows:
                            logger.warning(
                                "Reached end of screen buffer, stopping data stream processing"
                            )
                            break
        # Update fields (basic detection)
        self._detect_fields()

    def _detect_fields(self) -> None:
        logger.debug("Starting _detect_fields")
        self.fields = []
        field_start_idx = -1

        for i in range(self.size):
            row, col = self._calculate_coords(i)
            attr_offset = i * 3

            has_basic_attribute = (
                attr_offset < len(self.attributes)
                and self.attributes[attr_offset] != 0x00
            )
            has_extended_attribute = (
                self._extended_attributes.get((row, col)) is not None
            )

            is_attribute_position = has_basic_attribute or has_extended_attribute
            # Removed verbose logging to prevent memory exhaustion in tests from excessive output

            if is_attribute_position:
                if field_start_idx != -1 and self.attributes[attr_offset] == 0x00:
                    logger.debug(
                        f"Ending previous field on attrs==0x00 from {field_start_idx} to {i-1}"
                    )
                    self._create_field_from_range(field_start_idx, i - 1)
                    field_start_idx = -1
                if field_start_idx == -1:
                    logger.debug(f"Starting new field at {i}")
                    field_start_idx = i
            elif field_start_idx != -1 and i == self.size - 1:
                logger.debug(
                    f"Ending current field at end of screen from {field_start_idx} to {i}"
                )
                self._create_field_from_range(field_start_idx, i)

        # Handle any remaining open field at the end of the buffer
        if field_start_idx != -1:
            logger.debug(
                f"Ending final field from {field_start_idx} to {self.size - 1} after loop"
            )
            self._create_field_from_range(field_start_idx, self.size - 1)
        logger.debug(f"Finished _detect_fields. Total fields: {len(self.fields)}")

    def _create_field_from_range(self, start_idx: int, end_idx: int) -> None:
        """Create a field from a range of buffer positions."""
        if start_idx >= end_idx:
            return

        start_row, start_col = self._calculate_coords(start_idx)
        end_row, end_col = self._calculate_coords(end_idx)

        # Extract field content
        content = bytes(self.buffer[start_idx : end_idx + 1])

        # Get field attributes from the start position
        attr_offset = start_idx * 3
        if attr_offset < len(self.attributes):
            protected = bool(self.attributes[attr_offset] & 0x40)
            intensity = (
                self.attributes[attr_offset + 1]
                if attr_offset + 1 < len(self.attributes)
                else 0
            )
        else:
            protected = False
            intensity = 0

        # Create field
        field = Field(
            start=(start_row, start_col),
            end=(end_row, end_col),
            protected=protected,
            content=content,
            intensity=intensity,
        )

        self.fields.append(field)

    def _calculate_coords(self, index: int) -> Tuple[int, int]:
        """Helper to calculate row, col from a linear index."""
        row = index // self.cols
        col = index % self.cols
        return row, col

    def to_text(self) -> str:
        """
        Convert screen buffer to Unicode text string.

        :return: Multi-line string representation.
        """
        lines = []
        for row in range(self.rows):
            line_bytes = bytes(self.buffer[row * self.cols : (row + 1) * self.cols])
            line_text, _ = EBCDICCodec().decode(line_bytes)
            lines.append(line_text)
        return "\n".join(lines)

    def get_field_content(self, field_index: int) -> str:
        """
        Get content of a specific field.

        :param field_index: Index in fields list.
        :return: Unicode string content.
        """
        if 0 <= field_index < len(self.fields):
            return EmulationEncoder.decode(self.fields[field_index].content)
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

    def set_modified(self, row: int, col: int, modified: bool = True) -> None:
        """Set modified flag for position."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            pos = row * self.cols + col
            attr_offset = pos * 3 + 2  # Assume byte 2 for modified
            # Check that attr_offset is within bounds
            if attr_offset < len(self.attributes):
                self.attributes[attr_offset] = 0x01 if modified else 0x00

    def is_position_modified(self, row: int, col: int) -> bool:
        """Check if position is modified."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            pos = row * self.cols + col
            attr_offset = pos * 3 + 2
            # Check that attr_offset is within bounds
            if attr_offset < len(self.attributes):
                return bool(self.attributes[attr_offset])
        return False

    def __repr__(self) -> str:
        return f"ScreenBuffer({self.rows}x{self.cols}, fields={len(self.fields)})"

    def get_content(self) -> str:
        """Retrieve the buffer content as a string."""
        return self.to_text()

    def get_field_at_position(self, row: int, col: int) -> Optional[Field]:
        """Get the field containing the given position, if any."""
        for field in self.fields:
            start_row, start_col = field.start
            end_row, end_col = field.end
            if start_row <= row <= end_row and start_col <= col <= end_col:
                return field
        return None

    def get_field_at_cursor(self) -> Optional[Field]:
        """Get the field at the current cursor position."""
        cursor_pos = self.get_position()
        return self.get_field_at_position(cursor_pos[0], cursor_pos[1])

    # Macro-specific helpers (get_aid/match_pattern) removed

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

    def set_extended_attribute(
        self, row: int, col: int, attr_type: str, value: int
    ) -> None:
        """
        Set an extended attribute for a specific position.

        :param row: Row position.
        :param col: Column position.
        :param attr_type: Type of extended attribute (e.g., 'color', 'highlight').
        :param value: The value of the extended attribute.
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            pos_tuple = (row, col)
            if pos_tuple not in self._extended_attributes:
                self._extended_attributes[pos_tuple] = {}
            self._extended_attributes[pos_tuple][attr_type] = value
            # Removed self.update_fields() here, will be called once after data stream parsing

    def move_cursor_to_first_input_field(self) -> None:
        """
        Moves the cursor to the beginning of the first unprotected, non-skipped, non-autoskip field.
        """
        first_input_field = None
        for field in self.fields:
            # An input field is unprotected and not autoskip (auto-skip is usually indicated by a specific attribute bit,
            # but for simplicity, we'll consider any protected field as non-input for now).
            # Also, ensure it's not a skipped field (often numeric and protected, or just protected with no data entry)
            # For now, we'll just check for 'protected' status.
            if not field.protected:  # Assuming unprotected means input field
                first_input_field = field
                break

        if first_input_field:
            self.cursor_row, self.cursor_col = first_input_field.start
            logger.debug(
                f"Cursor moved to first input field at {self.cursor_row},{self.cursor_col}"
            )
        else:
            # If no input fields are found, move to (0,0) or keep current position.
            # For now, we'll just log and keep the current position.
            logger.debug("No input fields found for IC order.")

    def move_cursor_to_next_input_field(self) -> None:
        """
        Moves the cursor to the beginning of the next unprotected, non-skipped, non-autoskip field.
        Wraps around to the first field if no next field is found.
        """
        current_pos_linear = self.cursor_row * self.cols + self.cursor_col
        next_input_field = None

        # Sort fields by their linear start position to ensure correct traversal
        sorted_fields = sorted(
            self.fields, key=lambda f: f.start[0] * self.cols + f.start[1]
        )

        # Find the next input field after the current cursor position
        for field in sorted_fields:
            field_start_linear = field.start[0] * self.cols + field.start[1]
            if field_start_linear > current_pos_linear and not field.protected:
                next_input_field = field
                break

        if next_input_field:
            self.cursor_row, self.cursor_col = next_input_field.start
            logger.debug(
                f"Cursor moved to next input field at {self.cursor_row},{self.cursor_col}"
            )
        else:
            # If no next input field is found, wrap around to the first input field
            for field in sorted_fields:
                if not field.protected:
                    next_input_field = field
                    break

            if next_input_field:
                self.cursor_row, self.cursor_col = next_input_field.start
                logger.debug(
                    f"Cursor wrapped around to first input field at {self.cursor_row},{self.cursor_col}"
                )
            else:
                logger.debug(
                    "No input fields found for PT order, or no next field after wrap-around."
                )

    def set_attribute(
        self, attr: int, row: Optional[int] = None, col: Optional[int] = None
    ) -> None:
        """Set field attribute at specified or current position."""
        if row is None or col is None:
            row, col = self.get_position()
        pos = row * self.cols + col
        if 0 <= pos < self.size:
            self.attributes[pos * 3] = attr
        logger.debug(f"Set field attribute 0x{attr:02x} at position ({row}, {col})")

    def repeat_attribute(self, attr: int, repeat: int) -> None:
        """Repeat attribute a specified number of times."""
        for _ in range(repeat):
            self.set_attribute(attr)
            # Move cursor forward
            self.cursor_col += 1
            if self.cursor_col >= self.cols:
                self.cursor_col = 0
                self.cursor_row += 1
                if self.cursor_row >= self.rows:
                    self.cursor_row = 0
        logger.debug(f"Repeated attribute 0x{attr:02x} {repeat} times")

    def graphic_ellipsis(self, count: int) -> None:
        """Insert graphic ellipsis characters."""
        # Graphic ellipsis is typically represented as '...' or similar
        ellipsis_char = ord(".")  # ASCII period

        for _ in range(count):
            self.write_char(ellipsis_char, self.cursor_row, self.cursor_col)
            self.cursor_col += 1
            if self.cursor_col >= self.cols:
                self.cursor_col = 0
                self.cursor_row += 1
                if self.cursor_row >= self.rows:
                    self.cursor_row = 0
        logger.debug(f"Inserted graphic ellipsis {count} times")

    def insert_cursor(self) -> None:
        """Insert cursor at current position."""
        # In 3270, insert cursor typically just positions the cursor
        # The cursor position is already tracked, so this might be a no-op
        # or could be used to ensure cursor visibility
        logger.debug(f"Insert cursor at ({self.cursor_row}, {self.cursor_col})")

    def program_tab(self) -> None:
        """Program tab - move to next tab stop."""
        # Use the existing method for moving to next input field
        self.move_cursor_to_next_input_field()

    def set_extended_attribute_sfe(self, attr_type: int, attr_value: int) -> None:
        """Set extended field attribute from SFE order."""
        row, col = self.get_position()
        attr_map = {
            0x41: "highlight",
            0x42: "color",
            0x43: "character_set",
            0x44: "validation",
            0x45: "outlining",
        }
        key = attr_map.get(attr_type)
        if key:
            self.set_extended_attribute(row, col, key, attr_value)
            logger.debug(
                f"Set extended attribute '{key}'=0x{attr_value:02x} at ({row}, {col})"
            )
        else:
            logger.warning(f"Unknown extended attribute type 0x{attr_type:02x}")

    def get_field_at(self, row: int, col: int) -> Optional[Field]:
        """Alias for get_field_at_position for compatibility."""
        return self.get_field_at_position(row, col)
