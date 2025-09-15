"""Screen buffer management for 3270 emulation."""

from typing import List, Tuple, Optional
import logging
import re
from .ebcdic import EmulationEncoder
from collections import namedtuple

Field = namedtuple('Field', ['start', 'end', 'protected', 'numeric', 'modified', 'selected', 'intensity', 'color', 'background', 'validation', 'outlining', 'character_set', 'sfe_highlight', 'content'])

from .buffer_writer import BufferWriter

logger = logging.getLogger(__name__)



class ScreenBuffer(BufferWriter):
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
        # Extended attributes: dictionary mapping (row, col) to another dictionary of ext_attr_type: value
        self._extended_attributes = {}
        # List of fields
        self.fields: List[Field] = []
        # Cursor position
        self.cursor_row = 0
        self.cursor_col = 0
        # Default field attributes
        self._default_protected = True
        self._default_numeric = False
        self._current_aid = None

    def clear(self):
        """Clear the screen buffer and reset fields."""
        self.buffer = bytearray(b"\x40" * self.size)
        self.attributes = bytearray(self.size * 3)
        self._extended_attributes = {}
        self.fields = []
        self.set_position(0, 0)


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
        for idx, field in enumerate(self.fields):
            start_row, start_col = field.start
            end_row, end_col = field.end
    
            # Check if the position is within this field
            if start_row <= row <= end_row and (
                start_row != end_row or (start_col <= col <= end_col)
            ):
                # Position is within this field, mark as modified
                new_field = field._replace(modified=True)
                self.fields[idx] = new_field
    
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
        logger.debug("Starting _detect_fields")
        self.fields = []
        field_start_idx = -1

        for i in range(self.size):
            row, col = self._calculate_coords(i)
            attr_offset = i * 3

            has_basic_attribute = (attr_offset < len(self.attributes) and self.attributes[attr_offset] != 0x00)
            has_extended_attribute = (self._extended_attributes.get((row, col)) is not None)

            is_attribute_position = has_basic_attribute or has_extended_attribute
            logger.debug(f"Pos ({row},{col}) (idx {i}): basic_attr={has_basic_attribute}, ext_attr={has_extended_attribute}, is_attr_pos={is_attribute_position}, field_start_idx={field_start_idx}")

            if is_attribute_position:
                if field_start_idx != -1:
                    logger.debug(f"Ending previous field from {field_start_idx} to {i-1}")
                    self._create_field_from_range(field_start_idx, i - 1)
                logger.debug(f"Starting new field at {i}")
                field_start_idx = i
            elif field_start_idx != -1 and i == self.size - 1:
                logger.debug(f"Ending current field at end of screen from {field_start_idx} to {i}")
                self._create_field_from_range(field_start_idx, i)

        # Handle any remaining open field at the end of the buffer
        if field_start_idx != -1:
            logger.debug(f"Ending final field from {field_start_idx} to {self.size - 1} after loop")
            self._create_field_from_range(field_start_idx, self.size - 1)
        logger.debug(f"Finished _detect_fields. Total fields: {len(self.fields)}")

    def _create_field_from_range(self, start_idx: int, end_idx: int):
        """Helper to create a Field object from a range of buffer indices."""
        start_row, start_col = self._calculate_coords(start_idx)
        end_row, end_col = self._calculate_coords(end_idx)

        # Get the attribute byte for the start of the field
        attr_offset = start_idx * 3
        if attr_offset >= len(self.attributes):
            logger.warning(f"Attribute offset {attr_offset} out of bounds for buffer size {len(self.attributes)}. Skipping field creation.")
            return

        attr_byte = self.attributes[attr_offset]

        # Extract basic 3270 attributes
        protected = bool(attr_byte & 0x20)  # Bit 5: protected
        numeric = bool(attr_byte & 0x10)  # Bit 4: numeric
        modified = bool(attr_byte & 0x04)  # Bit 2: modified data tag

        # Get extended attributes from the _extended_attributes dictionary
        ext_attrs = self._extended_attributes.get((start_row, start_col), {})
        logger.debug(f"Extended attributes for ({start_row}, {start_col}): {ext_attrs}")

        # Map SFE highlight to basic intensity
        sfe_highlight_val = ext_attrs.get('highlight', 0)
        intensity_val = 0
        if sfe_highlight_val == 0xF0: # HIGHLIGHT_NONE
            intensity_val = 0 # Normal
        elif sfe_highlight_val == 0xF1: # HIGHLIGHT_BLINK
            intensity_val = 3 # Blink
        elif sfe_highlight_val == 0xF2: # HIGHLIGHT_REVERSE_VIDEO
            intensity_val = 1 # Highlighted (reverse video)
        elif sfe_highlight_val == 0xF4: # HIGHLIGHT_UNDERSCORE
            intensity_val = 1 # Highlighted (underscore)
        elif sfe_highlight_val == 0xF8: # HIGHLIGHT_INTENSIFIED
            intensity_val = 1 # Highlighted (intensified)
        else:
            # Fallback to basic 3270 intensity if no SFE highlight or unknown SFE highlight
            intensity_val = (attr_byte >> 3) & 0x03 # Basic 3270 intensity

        # Extract other extended attributes
        color_val = ext_attrs.get('color', 0)
        background_val = ext_attrs.get('background', 0)
        validation_val = ext_attrs.get('validation', attr_byte & 0x03) # Fallback to basic validation
        outlining_val = ext_attrs.get('outlining', 0)
        character_set_val = ext_attrs.get('character_set', 0)

        # Get content for the field.
        # For SFE, the content of the field starts at the attribute's position.
        content = bytes(self.buffer[start_idx : end_idx + 1])


        field = Field(
            start=(start_row, start_col),
            end=(end_row, end_col),
            protected=protected,
            numeric=numeric,
            modified=modified,
            selected=False, # Not directly determined by SF byte, assuming false for now
            intensity=intensity_val,
            color=color_val,
            background=background_val,
            validation=validation_val,
            outlining=outlining_val,
            character_set=character_set_val,
            sfe_highlight=sfe_highlight_val,
            content=content
        )
        self.fields.append(field)
        logger.debug(f"Created field: {field}")

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
            line_text = EmulationEncoder.decode(line_bytes)
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

    def get_field_at(self, pos: Tuple[int, int]) -> Optional[Field]:
        """Get the field at the given position (row, col)."""
        return self.get_field_at_position(pos[0], pos[1])

    def get_field_at_cursor(self) -> Optional[Field]:
        """Get the field at the current cursor position."""
        cursor_pos = self.get_position()
        return self.get_field_at_position(cursor_pos[0], cursor_pos[1])

    def get_aid(self) -> Optional[int]:
        """Get the current Attention ID (AID) from the last screen update."""
        return self._current_aid

    def match_pattern(self, regex: str) -> bool:
        """Check if the screen text matches the given regex pattern."""
        return bool(re.search(regex, self.to_text()))

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

    def set_extended_attribute(self, row: int, col: int, attr_type: str, value: int):
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

    def move_cursor_to_first_input_field(self):
        """
        Moves the cursor to the beginning of the first unprotected, non-skipped, non-autoskip field.
        """
        first_input_field = None
        for field in self.fields:
            # An input field is unprotected and not autoskip (auto-skip is usually indicated by a specific attribute bit,
            # but for simplicity, we'll consider any protected field as non-input for now).
            # Also, ensure it's not a skipped field (often numeric and protected, or just protected with no data entry)
            # For now, we'll just check for 'protected' status.
            if not field.protected: # Assuming unprotected means input field
                first_input_field = field
                break

        if first_input_field:
            self.cursor_row, self.cursor_col = first_input_field.start
            logger.debug(f"Cursor moved to first input field at {self.cursor_row},{self.cursor_col}")
        else:
            # If no input fields are found, move to (0,0) or keep current position.
            # For now, we'll just log and keep the current position.
            logger.debug("No input fields found for IC order.")

    def move_cursor_to_next_input_field(self):
        """
        Moves the cursor to the beginning of the next unprotected, non-skipped, non-autoskip field.
        Wraps around to the first field if no next field is found.
        """
        current_pos_linear = self.cursor_row * self.cols + self.cursor_col
        next_input_field = None
        
        # Sort fields by their linear start position to ensure correct traversal
        sorted_fields = sorted(self.fields, key=lambda f: f.start[0] * self.cols + f.start[1])

        # Find the next input field after the current cursor position
        for field in sorted_fields:
            field_start_linear = field.start[0] * self.cols + field.start[1]
            if field_start_linear > current_pos_linear and not field.protected:
                next_input_field = field
                break
        
        if next_input_field:
            self.cursor_row, self.cursor_col = next_input_field.start
            logger.debug(f"Cursor moved to next input field at {self.cursor_row},{self.cursor_col}")
        else:
            # If no next input field is found, wrap around to the first input field
            for field in sorted_fields:
                if not field.protected:
                    next_input_field = field
                    break
            
            if next_input_field:
                self.cursor_row, self.cursor_col = next_input_field.start
                logger.debug(f"Cursor wrapped around to first input field at {self.cursor_row},{self.cursor_col}")
            else:
                logger.debug("No input fields found for PT order, or no next field after wrap-around.")

    def set_attribute(self, attr: int) -> None:
        """Set field attribute at current cursor position."""
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
        ellipsis_char = ord('.')  # ASCII period
        
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
            0x41: 'highlight',
            0x42: 'color',
            0x43: 'character_set',
            0x44: 'validation',
            0x45: 'outlining',
        }
        key = attr_map.get(attr_type)
        if key:
            self.set_extended_attribute(row, col, key, attr_value)
            logger.debug(f"Set extended attribute '{key}'=0x{attr_value:02x} at ({row}, {col})")
        else:
            logger.warning(f"Unknown extended attribute type 0x{attr_type:02x}")

    def get_field_at(self, row: int, col: int) -> Optional[Field]:
        """Alias for get_field_at_position for compatibility."""
        return self.get_field_at_position(row, col)
