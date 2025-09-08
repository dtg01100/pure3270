"""Data stream parser and sender for 3270 protocol."""

import logging
from typing import Optional
from ..emulation.screen_buffer import ScreenBuffer

logger = logging.getLogger(__name__)

class ParseError(Exception):
    """Error during data stream parsing."""
    pass

class DataStreamParser:
    """Parses incoming 3270 data streams and updates the screen buffer."""

    def __init__(self, screen_buffer: ScreenBuffer):
        """
        Initialize the DataStreamParser.

        :param screen_buffer: ScreenBuffer to update.
        """
        self.screen = screen_buffer
        self._data = b""
        self._pos = 0
        self.wcc = None  # Write Control Character
        self.aid = None  # Attention ID

    def parse(self, data: bytes) -> None:
        """
        Parse 3270 data stream.

        :param data: Incoming 3270 data stream bytes.
        :raises ParseError: If parsing fails.
        """
        self._data = data
        self._pos = 0
        logger.debug(f"Parsing {len(data)} bytes of data stream")

        try:
            while self._pos < len(self._data):
                order = self._data[self._pos]
                self._pos += 1

                if order == 0xF5:  # WCC (Write Control Character)
                    if self._pos < len(self._data):
                        self.wcc = self._data[self._pos]
                        self._pos += 1
                        self._handle_wcc(self.wcc)
                    else:
                        logger.error("Unexpected end of data stream")
                        raise ParseError("Unexpected end of data stream")
                elif order == 0xF6:  # AID (Attention ID)
                    if self._pos < len(self._data):
                        self.aid = self._data[self._pos]
                        self._pos += 1
                        logger.debug(f"AID received: 0x{self.aid:02x}")
                    else:
                        logger.error("Unexpected end of data stream")
                        raise ParseError("Unexpected end of data stream")
                elif order == 0xF1:  # Read Partition
                    pass  # Handle if needed
                elif order == 0x10:  # SBA (Set Buffer Address)
                    self._handle_sba()
                elif order == 0x1D:  # SF (Start Field)
                    self._handle_sf()
                elif order == 0xF3:  # RA (Repeat to Address)
                    self._handle_ra()
                elif order == 0x29:  # GE (Graphic Escape)
                    self._handle_ge()
                elif order == 0x28:  # BIND
                    logger.debug("BIND received, configuring terminal type")
                    self._pos = len(self._data)
                elif order == 0x05:  # W (Write)
                    self._handle_write()
                elif order == 0x0D:  # EOA (End of Addressable)
                    break
                else:
                    self._handle_data(order)

        except IndexError:
            raise ParseError("Unexpected end of data stream")

    def _handle_wcc(self, wcc: int):
        """Handle Write Control Character."""
        # Simplified: set buffer state based on WCC bits
        # e.g., bit 0: reset modified flags
        if wcc & 0x01:
            self.screen.clear()
        logger.debug(f"WCC: 0x{wcc:02x}")

    def _handle_sba(self):
        """Handle Set Buffer Address."""
        if self._pos + 1 < len(self._data):
            addr_high = self._data[self._pos]
            addr_low = self._data[self._pos + 1]
            self._pos += 2
            address = (addr_high << 8) | addr_low
            row = address // self.screen.cols
            col = address % self.screen.cols
            self.screen.set_position(row, col)
            logger.debug(f"SBA to row {row}, col {col}")
        else:
            logger.error("Unexpected end of data stream")
            raise ParseError("Unexpected end of data stream")

    def _handle_sf(self):
        """Handle Start Field."""
        if self._pos + 1 < len(self._data):
            attr = self._data[self._pos]
            self._pos += 1
            protected = bool(attr & 0x40)  # Bit 6: protected
            numeric = bool(attr & 0x20)    # Bit 5: numeric
            # Update field attributes at current position
            row, col = self.screen.get_position()
            self.screen.write_char(0x40, row, col, protected=protected)  # Space with attr
            logger.debug(f"SF: protected={protected}, numeric={numeric}")

    def _handle_ra(self):
        """Handle Repeat to Address (basic)."""
        # Simplified: repeat char to address
        if self._pos + 3 < len(self._data):
            repeat_char = self._data[self._pos]
            addr_high = self._data[self._pos + 1]
            addr_low = self._data[self._pos + 2]
            self._pos += 3
            count = (addr_high << 8) | addr_low
            # Implement repeat logic...
            logger.debug(f"RA: repeat 0x{repeat_char:02x} {count} times")

    def _handle_ge(self):
        """Handle Graphic Escape (stub)."""
        logger.debug("GE encountered (graphics not supported)")

    def _handle_write(self):
        """Handle Write order: clear and write data."""
        self.screen.clear()
        # Subsequent data is written to buffer
        logger.debug("Write order: clearing and writing")

    def _handle_data(self, byte: int):
        """Handle data byte."""
        row, col = self.screen.get_position()
        self.screen.write_char(byte, row, col)
        col += 1
        if col >= self.screen.cols:
            col = 0
            row += 1
        self.screen.set_position(row, col)

    def _handle_bind(self, data: bytes):
        """Handle BIND image (basic)."""
        # Parse BIND for usable area, etc.
        logger.debug("BIND received, configuring terminal type")
        # Assume default 24x80 for now

    def get_aid(self) -> Optional[int]:
        """Get the last received AID."""
        return self.aid

class DataStreamSender:
    """Constructs outgoing 3270 data streams."""

    def __init__(self):
        """Initialize the DataStreamSender."""
        self.screen = ScreenBuffer()

    def build_read_modified_all(self) -> bytes:
        """Build Read Modified All (RMA) command."""
        # AID for Enter + Read Modified All
        stream = bytearray([0x7D, 0xF1])  # AID Enter, Read Partition (simplified for RMA)
        return bytes(stream)

    def build_read_modified_fields(self) -> bytes:
        """Build Read Modified Fields (RMF) command."""
        stream = bytearray([0x7D, 0xF6, 0xF0])  # AID Enter, Read Modified, all fields
        return bytes(stream)

    def build_key_press(self, aid: int) -> bytes:
        """
        Build data stream for key press (AID).

        :param aid: Attention ID (e.g., 0x7D for Enter).
        """
        stream = bytearray([aid])
        return bytes(stream)

    def build_write(self, data: bytes, wcc: int = 0xC1) -> bytes:
        """
        Build Write command with data.

        :param data: Data to write.
        :param wcc: Write Control Character.
        """
        stream = bytearray([0xF5, wcc, 0x05])  # WCC, Write
        stream.extend(data)
        stream.append(0x0D)  # EOA
        return bytes(stream)

    def build_sba(self, row: int, col: int) -> bytes:
        """
        Build Set Buffer Address.

        :param row: Row.
        :param col: Column.
        """
        address = (row * self.screen.cols) + col
        high = (address >> 8) & 0xFF
        low = address & 0xFF
        return bytes([0x10, high, low])  # SBA

    def build_sf(self, protected: bool = True, numeric: bool = False) -> bytes:
        """
        Build Start Field.

        :param protected: Protected attribute.
        :param numeric: Numeric attribute.
        """
        attr = 0x00
        if protected:
            attr |= 0x40
        if numeric:
            attr |= 0x20
        return bytes([0x1D, attr])  # SF

# Note: screen reference needed for build_sba; assume passed or global for basics
