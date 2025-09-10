"""Data stream parser and sender for 3270 protocol."""

from typing import List, Tuple, Optional
import logging
from typing import Optional
from ..emulation.screen_buffer import ScreenBuffer

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Error during data stream parsing."""

    pass


# 3270 Data Stream Orders
WCC = 0xF5
AID = 0xF6
READ_PARTITION = 0xF1
SBA = 0x10
SF = 0x1D
RA = 0xF3
GE = 0x29
BIND = 0x28
WRITE = 0x05
EOA = 0x0D
SCS_CTL_CODES = 0x04
DATA_STREAM_CTL = 0x40
STRUCTURED_FIELD = 0x3C  # '<'

# SCS Control Codes
PRINT_EOJ = 0x01

# TN3270E Subnegotiation Message Types
TN3270E_DEVICE_TYPE = 0x00
TN3270E_FUNCTIONS = 0x01
TN3270E_IS = 0x02
TN3270E_REQUEST = 0x03
TN3270E_SEND = 0x04

# TN3270E Device Types
TN3270E_IBM_DYNAMIC = "IBM-DYNAMIC"
TN3270E_IBM_3278_2 = "IBM-3278-2"
TN3270E_IBM_3278_3 = "IBM-3278-3"
TN3270E_IBM_3278_4 = "IBM-3278-4"
TN3270E_IBM_3278_5 = "IBM-3278-5"
TN3270E_IBM_3279_2 = "IBM-3279-2"
TN3270E_IBM_3279_3 = "IBM-3279-3"
TN3270E_IBM_3279_4 = "IBM-3279-4"
TN3270E_IBM_3279_5 = "IBM-3279-5"

# TN3270E Functions
TN3270E_BIND_IMAGE = 0x01
TN3270E_DATA_STREAM_CTL = 0x02
TN3270E_RESPONSES = 0x04
TN3270E_SCS_CTL_CODES = 0x08
TN3270E_SYSREQ = 0x10

# TN3270E Query Reply Types
QUERY_REPLY_SF = 0x88
QUERY_REPLY_DEVICE_TYPE = 0x01
QUERY_REPLY_CHARACTERISTICS = 0x02
QUERY_REPLY_HIGHLIGHTING = 0x03
QUERY_REPLY_COLOR = 0x04
QUERY_REPLY_EXTENDED_ATTRIBUTES = 0x05
QUERY_REPLY_GRAPHICS = 0x06
QUERY_REPLY_DBCS_ASIA = 0x07
QUERY_REPLY_DBCS_EUROPE = 0x08
QUERY_REPLY_DBCS_MIDDLE_EAST = 0x09
QUERY_REPLY_LINE_TYPE = 0x0A
QUERY_REPLY_OEM_AUXILIARY_DEVICE = 0x0B
QUERY_REPLY_TRANSPARENCY = 0x0C
QUERY_REPLY_FORMAT_STORAGE = 0x0D
QUERY_REPLY_DDM = 0x0E
QUERY_REPLY_RPQ_NAMES = 0x0F
QUERY_REPLY_SEGMENT = 0x10
QUERY_REPLY_PROCEDURE = 0x11
QUERY_REPLY_GRID = 0x12


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

    def get_aid(self) -> Optional[int]:
        """Get the current AID value."""
        return self.aid

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

                if order == WCC:  # WCC (Write Control Character)
                    if self._pos < len(self._data):
                        self.wcc = self._data[self._pos]
                        self._pos += 1
                        self._handle_wcc(self.wcc)
                    else:
                        logger.error("Unexpected end of data stream")
                        raise ParseError("Unexpected end of data stream")
                elif order == AID:  # AID (Attention ID)
                    if self._pos < len(self._data):
                        self.aid = self._data[self._pos]
                        self._pos += 1
                        logger.debug(f"AID received: 0x{self.aid:02x}")
                    else:
                        logger.error("Unexpected end of data stream")
                        raise ParseError("Unexpected end of data stream")
                elif order == READ_PARTITION:  # Read Partition
                    pass  # Handle if needed
                elif order == SBA:  # SBA (Set Buffer Address)
                    self._handle_sba()
                elif order == SF:  # SF (Start Field)
                    self._handle_sf()
                elif order == RA:  # RA (Repeat to Address)
                    self._handle_ra()
                elif order == GE:  # GE (Graphic Escape)
                    self._handle_ge()
                elif order == BIND:  # BIND
                    logger.debug("BIND received, configuring terminal type")
                    self._pos = len(self._data)
                elif order == WRITE:  # W (Write)
                    self._handle_write()
                elif order == EOA:  # EOA (End of Addressable)
                    break
                elif order == SCS_CTL_CODES:  # SCS Control Codes
                    self._handle_scs_ctl_codes()
                elif order == DATA_STREAM_CTL:  # Data Stream Control
                    self._handle_data_stream_ctl()
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
        if self._pos < len(self._data):
            attr = self._data[self._pos]
            self._pos += 1

            # Parse extended field attributes according to IBM 3270 specification
            protected = bool(attr & 0x40)  # Bit 6: protected
            numeric = bool(attr & 0x20)  # Bit 5: numeric
            intensity = (attr >> 3) & 0x03  # Bits 4-3: intensity
            modified = bool(attr & 0x04)  # Bit 2: modified data tag
            validation = attr & 0x03  # Bits 1-0: validation

            # Update field attributes at current position
            row, col = self.screen.get_position()
            self.screen.write_char(
                0x40, row, col, protected=protected
            )  # Space with attr

            # Store extended attributes in the screen buffer's attribute storage
            if 0 <= row < self.screen.rows and 0 <= col < self.screen.cols:
                pos = row * self.screen.cols + col
                attr_offset = pos * 3
                # Byte 0: Protection and basic attributes
                self.screen.attributes[attr_offset] = attr
                # For now, we'll store intensity in byte 1 and validation in byte 2
                # A more complete implementation would map these properly
                self.screen.attributes[attr_offset + 1] = intensity
                self.screen.attributes[attr_offset + 2] = validation

            logger.debug(
                f"SF: protected={protected}, numeric={numeric}, intensity={intensity}, modified={modified}, validation={validation}"
            )
        else:
            logger.error("Unexpected end of data stream")
            raise ParseError("Unexpected end of data stream")

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

    def _handle_scs_ctl_codes(self):
        """Handle SCS Control Codes for printer sessions."""
        if self._pos < len(self._data):
            scs_code = self._data[self._pos]
            self._pos += 1

            if scs_code == PRINT_EOJ:
                logger.debug("SCS PRINT-EOJ received")
                # Handle End of Job processing
                # In a real implementation, this would trigger printer job completion
            else:
                logger.debug(f"Unknown SCS control code: 0x{scs_code:02x}")
        else:
            logger.error("Unexpected end of data stream in SCS control codes")
            raise ParseError("Unexpected end of data stream in SCS control codes")

    def _handle_data_stream_ctl(self):
        """Handle Data Stream Control for printer data streams."""
        if self._pos < len(self._data):
            ctl_code = self._data[self._pos]
            self._pos += 1
            logger.debug(f"Data Stream Control code: 0x{ctl_code:02x}")
            # Implementation would handle specific data stream control functions
        else:
            logger.error("Unexpected end of data stream in data stream control")
            raise ParseError("Unexpected end of data stream in data stream control")

    def _handle_ge(self):
        """Handle Graphic Escape (stub)."""
        logger.debug("GE encountered (graphics not supported)")

    def _handle_write(self):
        """Handle Write order: clear and write data."""
        self.screen.clear()
        # Subsequent data is written to buffer
        logger.debug("Write order: clearing and writing")

    def _handle_scs_data(self, data: bytes):
        """
        Handle SCS character stream data for printer sessions.

        :param data: SCS character data
        """
        # In a full implementation, this would process SCS character data
        # for printer output rather than screen display
        logger.debug(f"SCS data received: {len(data)} bytes")

    def _handle_data(self, byte: int):
        """Handle data byte."""
        row, col = self.screen.get_position()
        self.screen.write_char(byte, row, col)
        col += 1
        if col >= self.screen.cols:
            col = 0
            row += 1
        self.screen.set_position(row, col)

    def _handle_structured_field(self):
        """Handle Structured Field command."""
        logger.debug("Structured Field command received")
        # Skip structured field for now (advanced feature)
        # In a full implementation, this would parse the structured field
        # and handle queries, replies, etc.
        self._skip_structured_field()

    def _skip_structured_field(self):
        """Skip structured field data."""
        # Find end of structured field (next command or end of data)
        while self._pos < len(self._data):
            # Look for next 3270 command
            if self._data[self._pos] in [
                WCC,
                AID,
                READ_PARTITION,
                SBA,
                SF,
                RA,
                GE,
                BIND,
                WRITE,
                EOA,
                SCS_CTL_CODES,
                DATA_STREAM_CTL,
                STRUCTURED_FIELD,
            ]:
                break
            self._pos += 1
        logger.debug("Skipped structured field")

    def _handle_read_partition_query(self):
        """Handle Read Partition Query command."""
        logger.debug("Read Partition Query command received")
        # In a full implementation, this would trigger sending Query Reply SFs
        # to inform the host about our capabilities

    def build_query_reply_sf(self, query_type: int, data: bytes = b"") -> bytes:
        """
        Build Query Reply Structured Field.

        :param query_type: Query reply type
        :param data: Query reply data
        :return: Query Reply Structured Field bytes
        """
        sf = bytearray()
        sf.append(STRUCTURED_FIELD)  # SF identifier
        # Add length (will be filled in later)
        length_pos = len(sf)
        sf.extend([0x00, 0x00])  # Placeholder for length
        sf.append(QUERY_REPLY_SF)  # Query Reply SF type
        sf.append(query_type)  # Query reply type
        sf.extend(data)  # Query reply data

        # Fill in length
        length = len(sf) - 1  # Exclude the SF identifier
        sf[length_pos] = (length >> 8) & 0xFF
        sf[length_pos + 1] = length & 0xFF

        return bytes(sf)

    def build_device_type_query_reply(self) -> bytes:
        """
        Build Device Type Query Reply Structured Field.

        :return: Device Type Query Reply SF bytes
        """
        # For simplicity, we'll report our device type
        device_type = b"IBM-3278-4-E"  # Example device type
        return self.build_query_reply_sf(QUERY_REPLY_DEVICE_TYPE, device_type)

    def build_characteristics_query_reply(self) -> bytes:
        """
        Build Characteristics Query Reply Structured Field.

        :return: Characteristics Query Reply SF bytes
        """
        # Report basic characteristics
        characteristics = bytearray()
        characteristics.append(0x01)  # Flags byte 1
        characteristics.append(0x00)  # Flags byte 2
        characteristics.append(0x00)  # Flags byte 3

        return self.build_query_reply_sf(QUERY_REPLY_CHARACTERISTICS, characteristics)


class DataStreamSender:
    """Constructs outgoing 3270 data streams."""

    def __init__(self):
        """Initialize the DataStreamSender."""
        self.screen = ScreenBuffer()

    def build_read_modified_all(self) -> bytes:
        """Build Read Modified All (RMA) command."""
        # AID for Enter + Read Modified All
        stream = bytearray(
            [0x7D, 0xF1]
        )  # AID Enter, Read Partition (simplified for RMA)
        return bytes(stream)

    def build_read_modified_fields(self) -> bytes:
        """Build Read Modified Fields (RMF) command."""
        stream = bytearray([0x7D, 0xF6, 0xF0])  # AID Enter, Read Modified, all fields
        return bytes(stream)

    def build_scs_ctl_codes(self, scs_code: int) -> bytes:
        """
        Build SCS Control Codes for printer sessions.

        :param scs_code: SCS control code to send
        """
        return bytes([SCS_CTL_CODES, scs_code])

    def build_data_stream_ctl(self, ctl_code: int) -> bytes:
        """
        Build Data Stream Control command.

        :param ctl_code: Data stream control code
        """
        return bytes([DATA_STREAM_CTL, ctl_code])

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

    def build_key_press(self, aid: int) -> bytes:
        """
        Build data stream for key press (AID).

        :param aid: Attention ID (e.g., 0x7D for Enter).
        """
        stream = bytearray([aid])
        return bytes(stream)

    def build_input_stream(
        self,
        modified_fields: List[Tuple[Tuple[int, int], bytes]],
        aid: int,
        cols: int = 80,
    ) -> bytes:
        """
        Build 3270 input data stream for modified fields and AID.

        :param modified_fields: List of ((row, col), content_bytes) for each modified field.
        :param aid: Attention ID byte for the key press.
        :param cols: Number of columns for SBA calculation.
        :return: Complete input data stream bytes.
        """
        self.screen.cols = cols  # Set cols for SBA calculation
        stream = bytearray()
        for start_pos, content in modified_fields:
            row, col = start_pos
            # SBA to field start
            sba = self.build_sba(row, col)
            stream.extend(sba)
            # Field data
            stream.extend(content)
        # Append AID
        stream.append(aid)
        return bytes(stream)
