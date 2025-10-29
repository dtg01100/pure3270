# ATTRIBUTION NOTICE
# =================================================================================
# This module contains code ported from or inspired by: IBM s3270/x3270
# Source: https://github.com/rhacker/x3270
# Licensed under BSD-3-Clause
#
# DESCRIPTION
# --------------------
# Screen buffer management with EBCDIC support based on s3270 implementation
#
# COMPATIBILITY
# --------------------
# Compatible with s3270 screen buffer handling and field management
#
# MODIFICATIONS
# --------------------
# Adapted for Python with object-oriented design and enhanced field tracking
#
# INTEGRATION POINTS
# --------------------
# - 24x80 and 32x80 screen size support
# - Field attribute processing and protection
# - EBCDIC character handling
# - Cursor positioning and movement
#
# ATTRIBUTION REQUIREMENTS
# ------------------------------
# This attribution must be maintained when this code is modified or
# redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
# Last updated: 2025-10-12
# =================================================================================

"""Screen buffer management for 3270 emulation."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .buffer_writer import BufferWriter
from .ebcdic import EBCDICCodec, EmulationEncoder
from .field_attributes import (
    BackgroundAttribute,
    CharacterSetAttribute,
    ColorAttribute,
    ExtendedAttributeSet,
    HighlightAttribute,
    LightPenAttribute,
    OutliningAttribute,
    ValidationAttribute,
)


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
        light_pen: int = 0,
        content: bytes = b"",
    ) -> None:
        # Normalize start/end coordinates so that start <= end (lexicographically).
        try:
            s_row, s_col = int(start[0]), int(start[1])
            e_row, e_col = int(end[0]), int(end[1])
        except (ValueError, TypeError, IndexError):
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
        self.light_pen = int(light_pen)
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
        # Normalize to uppercase to emulate 3270 field semantics where
        # alphabetic input is typically uppercased before encoding.
        try:
            if isinstance(text, str):
                text = text.upper()
        except Exception:
            pass
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
            "light_pen": self.light_pen,
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
    def _is_file_transfer_content(self, text: str) -> bool:
        """Check if text contains file transfer patterns that should be suppressed from screen display."""
        # Look for IND$FILE commands and file transfer metadata patterns
        file_transfer_patterns = [
            "IND$FILE PUT",
            "IND$FILE GET",
            "IND$FILE",
            "FILE TRANSFER",
            "FT: ",  # File transfer metadata prefix
            "ft-",  # File transfer trace prefix
        ]

        text_upper = text.upper()
        for pattern in file_transfer_patterns:
            if pattern in text_upper:
                return True

        # Check for raw file transfer metadata patterns (hex sequences that might appear as garbage)
        # Look for sequences that commonly appear in file transfer operations
        if any(seq in text for seq in ["\x01\x00", "\x02\x00", "\xff\xfd", "\xff\xfb"]):
            return True

        # Check for lines that are mostly non-printable or control characters
        # which often indicate file transfer data leaking into screen
        printable_chars = sum(1 for c in text if ord(c) >= 32 and ord(c) <= 126)
        total_chars = len(text.strip())
        if total_chars > 10 and printable_chars / total_chars < 0.3:
            return True

        return False

    @property
    def ascii_buffer(self) -> str:
        """Return the entire screen buffer as a decoded ASCII/Unicode string."""
        lines = []
        for row in range(self.rows):
            line_start = row * self.cols
            line_end = (row + 1) * self.cols
            line_bytes = bytearray(self.buffer[line_start:line_end])

            if self._ascii_mode:
                # In ASCII mode, buffer contains ASCII bytes directly
                line_text = line_bytes.decode("ascii", errors="replace")
            else:
                # In 3270 mode, buffer contains EBCDIC bytes that need conversion
                # Do not mask field attributes or cursor positions to match s3270's Ascii() behavior
                decoded, _ = EBCDICCodec().decode(bytes(line_bytes))
                # Clean any control characters that should not appear in screen text
                line_text = "".join(
                    c if ord(c) >= 32 or c in "\t\n\r" else " " for c in decoded
                )

            # Suppress file transfer content from screen display
            if self._is_file_transfer_content(line_text):
                logger.debug(
                    f"Suppressing file transfer content from screen: {line_text!r}"
                )
                continue

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
        # Validate dimensions: must be positive integers. Tests expect a
        # ValueError when invalid dimensions (e.g., rows=-1) are provided.
        if (
            not isinstance(rows, int)
            or not isinstance(cols, int)
            or rows <= 0
            or cols <= 0
        ):
            raise ValueError("rows and cols must be positive integers")

        self.rows = rows
        self.cols = cols
        self.size = rows * cols
        self._ascii_mode = False  # Track whether we're in ASCII or EBCDIC mode
        # EBCDIC character buffer - initialize to spaces
        self.buffer = bytearray([init_value] * self.size)
        # Attributes buffer: 3 bytes per position (protection, foreground, background/highlight)
        self.attributes = bytearray([0] * (self.rows * self.cols * 3))
        # Extended attributes: dictionary mapping (row, col) to ExtendedAttributeSet
        self._extended_attributes: Dict[Tuple[int, int], ExtendedAttributeSet] = {}
        # List of fields
        self.fields: List[Field] = []
        # Cursor position
        self.cursor_row = 0
        self.cursor_col = 0
        # Default field attributes
        self._default_protected = True
        self._default_numeric = False
        self._current_aid = None
        self.light_pen_selected_position: Optional[Tuple[int, int]] = None
        # Bulk update control to suspend expensive field detection
        self._suspend_field_detection: int = 0
        # Dedicated set for field start positions (SFE/SF)
        self._field_starts: set[int] = set()

    def get_field_content(self, field_index: int) -> str:
        """Return the content of the field at the given index as a decoded string."""
        if 0 <= field_index < len(self.fields):
            field = self.fields[field_index]
            if hasattr(field, "content") and field.content:
                from pure3270.emulation.ebcdic import EBCDICCodec

                codec = EBCDICCodec()
                decoded, _ = codec.decode(field.content)
                return decoded
        return ""

    def read_modified_fields(self) -> list[tuple[tuple[int, int], str]]:
        """Return a list of tuples (position, content) for modified fields."""
        result = []
        for field in self.fields:
            if getattr(field, "modified", False):
                position = field.start
                content = field.get_content() if hasattr(field, "get_content") else ""
                result.append((position, content))
        return result

    # Bulk update helpers
    def begin_bulk_update(self) -> None:
        """Suspend field detection until end_bulk_update is called."""
        try:
            self._suspend_field_detection += 1
        except Exception:
            self._suspend_field_detection = 1

    def end_bulk_update(self) -> None:
        """Resume field detection and run a single detection pass."""
        try:
            if self._suspend_field_detection > 0:
                self._suspend_field_detection -= 1
        except Exception:
            self._suspend_field_detection = 0
        # Only run detection when fully resumed
        if self._suspend_field_detection == 0:
            self._detect_fields()

    def clear(self) -> None:
        """Clear the screen buffer and reset fields."""
        init_value = 0x20 if self._ascii_mode else 0x40  # ASCII space vs EBCDIC space
        self.buffer = bytearray([init_value] * self.size)
        self.attributes = bytearray([0] * len(self.attributes))
        self._extended_attributes.clear()
        self._field_starts.clear()
        self.light_pen_selected_position = None
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

    def set_position(
        self, row: int, col: int, wrap: bool = False, strict: bool = False
    ) -> None:
        """Set cursor position with bounds checking or wrapping.

        Args:
            row: Target row position
            col: Target column position
            wrap: If True, allow wrapping to next line; if False, check bounds
            strict: If True, raise IndexError on out of bounds; if False, clamp values

        Raises:
            IndexError: When strict=True and position is out of bounds
        """
        if wrap:
            # Wrapping mode: allow col overflow to wrap to next line
            if col >= self.cols:
                col = 0
                row += 1
            # Clamp row to valid range after wrapping
            row = max(0, min(self.rows - 1, row))
        elif strict:
            # Strict mode: check bounds and raise IndexError if out of bounds
            if row >= self.rows or col >= self.cols or row < 0 or col < 0:
                raise IndexError(
                    f"Position ({row}, {col}) is out of bounds for screen size ({self.rows}, {self.cols})"
                )
        else:
            # Default mode: clamp values to prevent crashes in property tests
            if row >= self.rows or col >= self.cols or row < 0 or col < 0:
                # Log the clamping for debugging but don't fail
                logger.debug(
                    f"Clamping cursor from ({row}, {col}) to valid range "
                    f"for screen size ({self.rows}, {self.cols})"
                )
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
        # Remember whether the caller provided an explicit position.
        # Tests expect that calling write_char() without row/col uses the
        # current cursor position but does NOT advance it. When callers
        # intentionally supply a position (for example, to emulate typing),
        # we advance the cursor so subsequent operations continue after
        # the written character.
        explicit_position = row is not None and col is not None
        # If row/col not provided, use current cursor position
        if not explicit_position:
            current_row, current_col = self.get_position()
            row = current_row
            col = current_col
        else:
            # For explicit position, ensure row and col are not None
            if row is None or col is None:
                raise ValueError(
                    "Explicit position requires both row and col to be specified"
                )

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

            # Advance cursor only when the caller supplied an explicit
            # position. Calling write_char() without explicit coords uses
            # the cursor position but should not move it (tests rely on
            # this behavior). When explicit_position is True we emulate
            # terminal typing and move the cursor forward with wrapping.
            # DBCS characters advance the cursor by 2 positions instead of 1.
            if explicit_position:
                advance = 1
                # Check if this position has DBCS character set (e.g., Katakana)
                attr_set = self._extended_attributes.get((row, col))
                if attr_set:
                    char_set_attr = attr_set.get_attribute("character_set")
                    if char_set_attr and char_set_attr.value == 0x02:  # Katakana DBCS
                        advance = 2
                self.cursor_col += advance
                if self.cursor_col >= self.cols:
                    self.cursor_col = 0
                    self.cursor_row += 1
                    if self.cursor_row >= self.rows:
                        self.cursor_row = 0
            # Update field content and mark as modified if this position belongs to a field
            modified_field_found = self._update_field_content(
                int(row), int(col), ebcdic_byte
            )
            # Avoid heavy field detection for every byte to improve performance on large writes.
            # Only trigger field detection when we just wrote at column 0 (start of a row)
            # or when no fields exist yet and we're populating the screen for the first time.
            if not modified_field_found and self._suspend_field_detection == 0:
                if col == 0 or not self.fields:
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
        Update buffer from a 3270 data stream with progressive limits and graceful handling.

        :param data: Raw 3270 data stream bytes.
        """
        # Progressive buffer size limits with graceful degradation
        max_data_len = self.size * 2  # Allow some overflow but not unlimited
        if len(data) > max_data_len:
            logger.warning(
                f"Data stream too large ({len(data)} bytes), applying progressive limits"
            )
            # Apply progressive truncation with priority preservation
            data = self._apply_progressive_limits(data, max_data_len)

        i = 0
        processed_bytes = 0
        max_processed = self.size * 3  # Allow more processing than buffer size

        while i < len(data) and processed_bytes < max_processed:
            order = data[i]
            i += 1
            processed_bytes += 1

            if order == 0xF5:  # Write
                if i < len(data):
                    i += 1  # skip WCC
                    processed_bytes += 1
                continue
            elif order == 0x10:  # SBA
                if i + 1 < len(data):
                    i += 2  # skip address bytes
                    processed_bytes += 2
                self.set_position(0, 0)  # Address 0x0000 -> row 0, col 0
                continue
            elif order in (0x05, 0x0D):  # Unknown/EOA
                continue
            else:
                # Treat as data byte with graceful overflow handling
                pos = self.cursor_row * self.cols + self.cursor_col
                if pos < self.size:
                    self.buffer[pos] = order
                    self.cursor_col += 1
                    if self.cursor_col >= self.cols:
                        self.cursor_col = 0
                        self.cursor_row += 1
                        # Graceful wraparound with buffer bounds checking
                        if self.cursor_row >= self.rows:
                            logger.debug(
                                "Reached end of screen buffer, wrapping to beginning"
                            )
                            self.cursor_row = 0
                            self.cursor_col = 0
                else:
                    # Graceful overflow: wrap to beginning instead of stopping
                    logger.debug("Buffer overflow, wrapping to beginning")
                    self.cursor_row = 0
                    self.cursor_col = 0
                    if pos < self.size * 2:  # Allow some overflow wrapping
                        self.buffer[0] = order
                        self.cursor_col = 1

        if processed_bytes >= max_processed:
            logger.warning(
                f"Processed maximum bytes ({max_processed}), truncating remaining data"
            )

        # Update fields (basic detection)
        self._detect_fields()

    def _apply_progressive_limits(self, data: bytes, max_len: int) -> bytes:
        """
        Apply progressive limits to data stream with priority preservation.

        :param data: Original data stream
        :param max_len: Maximum allowed length
        :return: Truncated data with preserved priority sections
        """
        if len(data) <= max_len:
            return data

        # Preserve critical TN3270E headers and commands
        critical_markers = [
            b"\xff\xfa\x24",  # TN3270E subnegotiation start
            b"\xff\xfd\x24",  # DO TN3270E
            b"\xff\xfb\x24",  # WILL TN3270E
            b"\x03\x00\x00\x00",  # BIND header
        ]

        # Find the last critical marker within the limit
        truncated_data = data[:max_len]
        best_cut_point = max_len

        for marker in critical_markers:
            marker_pos = truncated_data.rfind(marker)
            if marker_pos > best_cut_point // 2:  # Only consider markers in second half
                best_cut_point = marker_pos + len(marker)

        # Cut at the best point found
        if best_cut_point < max_len:
            best_cut_point = min(best_cut_point + 32, max_len)  # Add some padding

        result = data[:best_cut_point]

        # Log the truncation details
        truncated_bytes = len(data) - len(result)
        logger.info(
            f"Applied progressive limits: kept {len(result)} bytes, "
            f"truncated {truncated_bytes} bytes, "
            f"preserved critical sections"
        )

        return result

    def _create_field_from_range(self, start_idx: int, end_idx: int) -> None:
        """Create a field from a range of buffer positions."""
        if start_idx > end_idx:
            logger.debug(
                f"_create_field_from_range: Invalid range {start_idx} > {end_idx}"
            )
            return

        start_row, start_col = self._calculate_coords(start_idx)
        end_row, end_col = self._calculate_coords(end_idx)
        logger.debug(
            f"_create_field_from_range: Field start=({start_row},{start_col}), end=({end_row},{end_col}), content={self.buffer[start_idx:end_idx+1].hex()}"
        )

        # Extract field content
        content = bytes(self.buffer[start_idx : end_idx + 1])

        # Get basic field attributes from the start position
        attr_offset = start_idx * 3
        basic_attr = 0
        if attr_offset < len(self.attributes):
            basic_attr = self.attributes[attr_offset]
            protected = bool(basic_attr & 0x40)  # FA_PROTECT
            # Extract intensity from basic attribute (bits 4-3)
            intensity_bits = (basic_attr & 0x0C) >> 2  # FA_INTENSITY >> 2
            # Map to intensity value: 0=normal, 1=normal+detectable, 2=intensified+detectable, 3=nondisplay
            if intensity_bits == 0:
                intensity = 0  # Normal, non-detectable
                light_pen = 0
            elif intensity_bits == 1:
                intensity = 1  # Normal, detectable
                light_pen = 1  # Light pen selectable
            elif intensity_bits == 2:
                intensity = 2  # Intensified, detectable
                light_pen = 1  # Light pen selectable
            else:  # intensity_bits == 3
                intensity = 3  # Nondisplay, non-detectable
                light_pen = 0
        else:
            protected = False
            intensity = 0
            light_pen = 0

        # Get extended attributes
        extended_attrs = self._extended_attributes.get((start_row, start_col))
        color = 0
        background = 0
        sfe_highlight = 0
        validation = 0
        outlining = 0
        character_set = 0
        if extended_attrs:
            color_val = extended_attrs.get("color")
            color = int(getattr(color_val, "value", 0) if color_val is not None else 0)

            background_val = extended_attrs.get("background")
            background = int(
                getattr(background_val, "value", 0) if background_val is not None else 0
            )

            sfe_highlight_val = extended_attrs.get("highlight")
            sfe_highlight = int(
                getattr(sfe_highlight_val, "value", 0)
                if sfe_highlight_val is not None
                else 0
            )

            validation_val = extended_attrs.get("validation")
            validation = int(
                getattr(validation_val, "value", 0) if validation_val is not None else 0
            )

            outlining_val = extended_attrs.get("outlining")
            outlining = int(
                getattr(outlining_val, "value", 0) if outlining_val is not None else 0
            )

            character_set_val = extended_attrs.get("character_set")
            character_set = int(
                getattr(character_set_val, "value", 0)
                if character_set_val is not None
                else 0
            )

            light_pen_val = extended_attrs.get("light_pen")
            light_pen = int(
                getattr(light_pen_val, "value", 0) if light_pen_val is not None else 0
            )

            # Map SFE highlight to intensity if present and nonzero
            if sfe_highlight:
                intensity = 1  # Basic mapping: highlighted

        # Create field
        field = Field(
            start=(start_row, start_col),
            end=(end_row, end_col),
            protected=protected,
            content=content,
            intensity=intensity,
            color=color,
            background=background,
            sfe_highlight=sfe_highlight,
            validation=validation,
            outlining=outlining,
            character_set=character_set,
            light_pen=light_pen,
        )

        logger.debug(f"_create_field_from_range: Created field {field}")
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
        lines: List[str] = []
        for row in range(self.rows):
            start = row * self.cols
            end = start + self.cols
            line_bytes = bytearray(self.buffer[start:end])

            if self._ascii_mode:
                try:
                    text = line_bytes.decode("ascii", errors="replace")
                except Exception:
                    text = ""
            else:
                # In 3270 mode, mask field attributes, cursor position and attribute bytes with EBCDIC space
                for col in range(self.cols):
                    pos = start + col
                    # Check if this byte is an attribute byte (0x00-0x3F, 0xC0-0xFF, etc., all possible field attribute ranges)
                    byte_value = line_bytes[col]
                    is_attribute_byte = (byte_value <= 0x3F) or (byte_value >= 0xC0)

                    # Mask all possible field attribute byte ranges (0x00-0x3F, 0xC0-0xFF, etc.)
                    # or positions marked as field starts containing attribute bytes
                    if is_attribute_byte or pos in self._field_starts:
                        line_bytes[col] = 0x40  # EBCDIC space for attributes

                    if row == self.cursor_row and col == self.cursor_col:
                        line_bytes[col] = 0x40  # Hide cursor as space
                try:
                    # Prefer CP037 decoding to align with s3270 Ascii() behavior
                    decoded, _ = EBCDICCodec().decode(bytes(line_bytes))
                    # Clean any control characters that should not appear in screen text
                    text = "".join(
                        c if ord(c) >= 32 or c in "\t\n\r" else " " for c in decoded
                    )
                except Exception:
                    # Fallback to emulator mapping if codec fails
                    text = EmulationEncoder.decode(bytes(line_bytes))
            lines.append(text)
        return "\n".join(lines)

    def _detect_fields(self) -> None:
        # Only log at debug level when explicitly enabled to avoid performance issues
        # in property tests with many iterations
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"_detect_fields: _field_starts={sorted(self._field_starts)}")
        self.fields.clear()
        field_starts = sorted(self._field_starts)
        if not field_starts:
            return
        for idx, start in enumerate(field_starts):
            end = (
                field_starts[idx + 1] - 1
                if idx + 1 < len(field_starts)
                else self.size - 1
            )
            # Removed per-field debug log to prevent test hangs in high-volume scenarios
            self._create_field_from_range(start, end)

    def __repr__(self) -> str:
        return f"ScreenBuffer({self.rows}x{self.cols}, fields={len(self.fields)})"

    def get_content(self) -> str:
        """Retrieve the buffer content as a string."""
        return self.to_text()

    def get_field_at_position(self, row: int, col: int) -> Optional[Field]:
        """Get the field containing the given position, if any (by linear range)."""
        pos = row * self.cols + col
        for field in self.fields:
            start_idx = field.start[0] * self.cols + field.start[1]
            end_idx = field.end[0] * self.cols + field.end[1]
            if start_idx <= pos <= end_idx:
                return field
        return None

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
            if not field.protected and field_start_linear > current_pos_linear:
                next_input_field = field
                break

        # If no next input field is found, wrap around to the first input field
        if not next_input_field:
            for field in sorted_fields:
                if not field.protected:
                    next_input_field = field
                    break

        if next_input_field:
            self.cursor_row, self.cursor_col = next_input_field.start
            logger.debug(
                f"Cursor moved to next input field at {self.cursor_row},{self.cursor_col}"
            )
        else:
            logger.debug("No input fields found for PT order.")

    def set_attribute(
        self, attr: int, row: Optional[int] = None, col: Optional[int] = None
    ) -> None:
        """Set field attribute at specified or current position."""
        if row is None or col is None:
            row, col = self.get_position()
        pos = row * self.cols + col
        if 0 <= pos < self.size:
            # Only update attributes buffer and field starts, matching s3270's behavior
            self.attributes[pos * 3] = attr
            # Mark a field start at this position
            self._field_starts.add(pos)
            # Recompute fields since we changed attributes
            if self._suspend_field_detection == 0:
                self._detect_fields()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Set field attribute 0x{attr:02x} at position ({row}, {col})")

    def repeat_attribute(self, attr: int, repeat: int) -> None:
        """Repeat attribute a specified number of times."""
        # Suspend field detection during bulk operations
        self._suspend_field_detection += 1
        try:
            for _ in range(repeat):
                self.set_attribute(attr)
                # Move cursor forward
                self.cursor_col += 1
                if self.cursor_col >= self.cols:
                    self.cursor_col = 0
                    self.cursor_row += 1
                    if self.cursor_row >= self.rows:
                        self.cursor_row = 0
        finally:
            # Resume field detection and trigger once at the end
            self._suspend_field_detection -= 1
            if self._suspend_field_detection == 0:
                self._detect_fields()
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
        """Accumulate extended field attributes for the field at the current buffer address.

        Important semantics:
        - Extended attributes (from SFE or SA) do NOT consume a display byte and
          must NOT create a field-start marker on their own.
        - Only the base field attribute (set via SF or SFE type 0xC0) occupies a
          buffer position and should be recorded in `_field_starts`.

        This method therefore ONLY updates the accumulated extended attributes
        and does not modify the display buffer or `_field_starts`.
        """
        row, col = self.get_position()
        attr_map = {
            0x41: "highlight",
            0x42: "color",
            0x43: "character_set",
            0x44: "validation",
            0x45: "outlining",  # XA_OUTLINING = 0x45 (RFC, some impls use background)
            0xC1: "validation",  # XA_VALIDATION = 0xc1
            0xC2: "outlining",  # XA_OUTLINING = 0xc2
        }
        key = attr_map.get(attr_type)
        if key:
            # Accumulate all attributes for the field at this position
            pos_tuple = (row, col)
            if pos_tuple not in self._extended_attributes:
                self._extended_attributes[pos_tuple] = ExtendedAttributeSet()
            attr_set = self._extended_attributes[pos_tuple]
            attr_set.set_attribute(key, attr_value)
            logger.debug(
                f"Set extended attribute '{key}'=0x{attr_value:02x} at ({row}, {col}) (accumulated)"
            )
        else:
            logger.warning(f"Unknown extended attribute type 0x{attr_type:02x}")

    def set_extended_attribute(
        self, row: int, col: int, attr_type: str, value: int
    ) -> None:
        """Set an extended attribute at a specific position (used by tests and APIs).

        This also records a field start at that position to align with field-start-driven detection.
        """
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        pos = row * self.cols + col
        if (row, col) not in self._extended_attributes:
            self._extended_attributes[(row, col)] = ExtendedAttributeSet()
        attr_set = self._extended_attributes[(row, col)]

        # Map simple string types to proper attribute classes when available; fall back to raw value
        try:
            if attr_type == "color":
                attr_set.set_attribute(attr_type, ColorAttribute(value))
            elif attr_type == "highlight":
                attr_set.set_attribute(attr_type, HighlightAttribute(value))
            elif attr_type == "background":
                attr_set.set_attribute(attr_type, BackgroundAttribute(value))
            elif attr_type == "validation":
                attr_set.set_attribute(attr_type, ValidationAttribute(value))
            elif attr_type == "outlining":
                attr_set.set_attribute(attr_type, OutliningAttribute(value))
            elif attr_type == "light_pen":
                attr_set.set_attribute(attr_type, LightPenAttribute(value))
            elif attr_type == "character_set":
                attr_set.set_attribute(attr_type, CharacterSetAttribute(value))
            else:
                # Unknown types are stored as raw ints for backward compatibility
                attr_set.set_attribute(attr_type, value)
        except Exception:
            # If class construction fails, store as raw
            attr_set.set_attribute(attr_type, value)

        # Mark the field start for detection. Do not modify the protection bit
        # or other attribute flags here; extended attributes should not imply
        # protection by default. Field detection relies on _field_starts.
        self._field_starts.add(pos)
        # Recompute fields based on updated field starts
        if self._suspend_field_detection == 0:
            self._detect_fields()

    def get_field_at(self, row: int, col: int) -> Optional[Field]:
        """Alias for get_field_at_position for compatibility."""
        return self.get_field_at_position(row, col)

    def get_extended_attributes_at(
        self, row: int, col: int
    ) -> Optional[ExtendedAttributeSet]:
        """Get extended attributes for a specific position.

        Args:
            row: Row position
            col: Column position

        Returns:
            ExtendedAttributeSet if attributes exist, None otherwise
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self._extended_attributes.get((row, col))
        return None

    def set_field_validation(
        self, field: Field, validation_rules: ValidationAttribute
    ) -> None:
        """Set validation rules for a field.

        Args:
            field: The field to set validation for
            validation_rules: Validation attribute with rules
        """
        # Set validation for the start position of the field
        start_row, start_col = field.start
        self.set_extended_attribute(
            start_row, start_col, "validation", validation_rules.value
        )

    def get_field_validation(self, field: Field) -> Optional[ValidationAttribute]:
        """Get validation rules for a field.

        Args:
            field: The field to get validation for

        Returns:
            ValidationAttribute if set, None otherwise
        """
        start_row, start_col = field.start
        attr_set = self.get_extended_attributes_at(start_row, start_col)
        if attr_set:
            attr = attr_set.get_attribute("validation")
            return attr if isinstance(attr, ValidationAttribute) else None
        return None

    def validate_field_input(
        self, field: Field, input_text: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate input against field's validation rules.

        Args:
            field: The field to validate input for
            input_text: The input text to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        validation_attr = self.get_field_validation(field)
        if validation_attr:
            return validation_attr.validate_input(input_text)
        return True, None  # No validation rules, input is valid

    def select_light_pen(self, row: int, col: int) -> Optional[int]:
        """Simulate a light pen selection at the given row and col.

        If the field at the given position is light-pen selectable, this method
        will mark the field as selected, store the selection position, and
        return the light pen AID. Otherwise, it returns None.
        """
        # Ensure fields are up-to-date in case attributes were set just prior
        # to this call (e.g., via set_attribute/set_extended_attribute).
        # Field detection is inexpensive for 24x80 and avoids stale state.
        self._detect_fields()

        field = self.get_field_at_position(row, col)
        if field and field.light_pen:
            # Mark the field as selected
            for i, f in enumerate(self.fields):
                if f is field:
                    self.fields[i] = field._replace(selected=True)
                    break

            # Store the selection position
            self.light_pen_selected_position = (row, col)

            # Change the designator character if it's a '?'
            pos = row * self.cols + col
            if self.buffer[pos] == ord("?"):
                self.buffer[pos] = ord(">")

            # Return the light pen AID
            return 0x7D

        return None
