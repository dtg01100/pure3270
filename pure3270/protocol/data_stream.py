"""Data stream parser and sender for 3270 protocol."""

from typing import List, Tuple, Optional
import logging
from typing import TYPE_CHECKING
from ..emulation.screen_buffer import ScreenBuffer # Import ScreenBuffer
from ..emulation.printer_buffer import PrinterBuffer # Import PrinterBuffer
from .utils import (
    TN3270_DATA, SCS_DATA, RESPONSE, BIND_IMAGE, UNBIND, NVT_DATA, REQUEST, SSCP_LU_DATA, PRINT_EOJ,
    SNA_RESPONSE as SNA_RESPONSE_TYPE, TN3270E_SCS_CTL_CODES
)

if TYPE_CHECKING:
    from ..emulation.screen_buffer import ScreenBuffer
    from ..emulation.printer_buffer import PrinterBuffer
    from .negotiator import Negotiator

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
WRITE = 0x05
EOA = 0x0D
SCS_CTL_CODES = 0x04
DATA_STREAM_CTL = 0x40
STRUCTURED_FIELD = 0x3C  # '<'
SFE = 0x28 # Start Field Extended (RFC 1576)
IC = 0x0F # Insert Cursor
PT = 0x0E # Program Tab
BIND = 0xF9 # Placeholder for BIND command, not officially part of 3270 orders but used in context
# Printer Status related orders/commands (research needed for exact values)
# These are placeholders and need to be verified against 3270 printer protocol specs.
WRITE_STRUCTURED_FIELD_PRINTER = 0x11 # Example: Write Structured Field for printer
PRINTER_STATUS_SF = 0x01 # Example: Structured Field type for printer status
SOH = 0x01 # Start of Header (SCS command for printer status) - often 0x01 in SCS
# Other potential status indicators
DEVICE_END = 0x00 # Placeholder for device end status
INTERVENTION_REQUIRED = 0x01 # Placeholder for intervention required status

# Structured Field Types
BIND_SF_TYPE = 0x03 # BIND-IMAGE Structured Field Type
SNA_RESPONSE_SF_TYPE = 0x01 # Example: assuming a specific SF type for SNA responses
PRINTER_STATUS_SF_TYPE = 0x02 # Placeholder for printer status structured field type

# BIND-IMAGE Subfield IDs (RFC 2355, Section 5.1)
BIND_SF_SUBFIELD_PSC = 0x01 # Presentation Space Control
BIND_SF_SUBFIELD_QUERY_REPLY_IDS = 0x02 # Query Reply IDs

class BindImage:
    """Represents a parsed BIND-IMAGE Structured Field."""
    def __init__(self, rows: Optional[int] = None, cols: Optional[int] = None, query_reply_ids: Optional[List[int]] = None):
        self.rows = rows
        self.cols = cols
        self.query_reply_ids = query_reply_ids if query_reply_ids is not None else []

    def __repr__(self):
        return (f"BindImage(rows={self.rows}, cols={self.cols}, "
                f"query_reply_ids={self.query_reply_ids})")


# Extended Attribute Types (for SF_EXT)
EXT_ATTR_HIGHLIGHT = 0x41 # Extended highlighting
EXT_ATTR_COLOR = 0x42 # Color
EXT_ATTR_CHARACTER_SET = 0x43 # Character set
EXT_ATTR_FIELD_VALID = 0x44 # Field validation
EXT_ATTR_OUTLINE = 0x45 # Outlining

# Extended Highlighting Values (RFC 1576, Section 2.1.1.1)
HIGHLIGHT_NONE = 0xF0
HIGHLIGHT_BLINK = 0xF1
HIGHLIGHT_REVERSE_VIDEO = 0xF2
HIGHLIGHT_UNDERSCORE = 0xF4
HIGHLIGHT_INTENSIFIED = 0xF8

# Color Values (RFC 1576, Section 2.1.1.2)
COLOR_DEFAULT = 0xF0
COLOR_BLUE = 0xF1
COLOR_RED = 0xF2
COLOR_PINK = 0xF3
COLOR_GREEN = 0xF4
COLOR_TURQUOISE = 0xF5
COLOR_YELLOW = 0xF6
COLOR_WHITE = 0xF7 # Default foreground
COLOR_BLACK = 0xF8 # Default background

# Field Validation Values (RFC 1576, Section 2.1.1.4)
VALID_NONE = 0x00
VALID_MANDATORY_FILL = 0x01
VALID_MANDATORY_ENTRY = 0x02
VALID_TRIGGER = 0x04

# Outlining Values (RFC 1576, Section 2.1.1.5)
OUTLINE_NONE = 0x00
OUTLINE_UNDERSCORE = 0x01
OUTLINE_RIGHT_VERTICAL = 0x02
OUTLINE_OVERLINE = 0x04
OUTLINE_LEFT_VERTICAL = 0x08

# Data Stream Types (for parse method)
TN3270_DATA = 0x00
SCS_DATA = 0x07 # As per RFC 2355 Section 6.1
SNA_RESPONSE_DATA_TYPE = 0x08 # New data type for SNA responses
PRINTER_STATUS_DATA_TYPE = 0x0A # New data type for Printer Status (TN3270E)

# SOH Status Message Formats (placeholders, research needed)
SOH_SUCCESS = 0x00 # SOH success
SOH_DEVICE_END = 0x40 # SOH device end
SOH_INTERVENTION_REQUIRED = 0x80 # SOH intervention required

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

# SNA Response Codes (Examples, these would need to be researched from SNA documentation)
SNA_COMMAND_RESPONSE = 0x01 # General command response
SNA_DATA_RESPONSE = 0x02    # General data response
SNA_RESPONSE_CODE_POSITIVE_ACK = 0x40 # Example: DR1 (Definite Response 1)
SNA_RESPONSE_CODE_NEGATIVE_ACK = 0x80 # Example: ER (Exception Response)

# SNA Response Flags (Examples, these would need to be researched from SNA documentation)
# These flags are often embedded within the response code byte itself or a separate byte.
# For simplicity, we'll introduce a separate flags byte for now.
SNA_FLAGS_NONE = 0x00
SNA_FLAGS_DEFINITE_RESPONSE_1 = 0x01 # Request for DR1 (Definite Response 1)
SNA_FLAGS_DEFINITE_RESPONSE_2 = 0x02 # Request for DR2 (Definite Response 2)
SNA_FLAGS_EXCEPTION_RESPONSE = 0x04 # Indicates an exception response
SNA_FLAGS_RSP = 0x08 # Response indicator (often 0x08 for response, 0x00 for request)
SNA_FLAGS_CHAIN_MIDDLE = 0x10 # Middle of chain
SNA_FLAGS_CHAIN_LAST = 0x20 # Last in chain
SNA_FLAGS_CHAIN_FIRST = 0x40 # First in chain


# SNA Sense Codes (Examples, these would need to be researched from SNA documentation)
SNA_SENSE_CODE_SUCCESS = 0x0000 # No error
SNA_SENSE_CODE_INVALID_FORMAT = 0x1001 # Invalid message format
SNA_SENSE_CODE_NOT_SUPPORTED = 0x1002 # Function not supported
SNA_SENSE_CODE_SESSION_FAILURE = 0x2001 # Session failure
SNA_SENSE_CODE_INVALID_REQUEST = 0x0801 # Invalid Request
SNA_SENSE_CODE_LU_BUSY = 0x080A # LU Busy
SNA_SENSE_CODE_INVALID_SEQUENCE = 0x1008 # Invalid Sequence
SNA_SENSE_CODE_NO_RESOURCES = 0x080F # No Resources
SNA_SENSE_CODE_STATE_ERROR = 0x1003 # State Error

class SnaResponse:
    """Represents a parsed SNA response."""
    def __init__(self, response_type: int, flags: Optional[int] = None, sense_code: Optional[int] = None, data: Optional[bytes] = None):
        self.response_type = response_type
        self.flags = flags
        self.sense_code = sense_code
        self.data = data

    def __repr__(self):
        flags_str = f"0x{self.flags:02x}" if self.flags is not None else "None"
        sense_code_str = f"0x{self.sense_code:04x}" if self.sense_code is not None else "None"
        return (f"SnaResponse(type=0x{self.response_type:02x}, "
                f"flags={flags_str}, "
                f"sense_code={sense_code_str}, "
                f"data={self.data.hex() if self.data else 'None'})")

    def is_positive(self) -> bool:
        """Check if the response is positive."""
        # A response is positive if it's not an exception response and sense code is success or None
        return (self.flags is None or not (self.flags & SNA_FLAGS_EXCEPTION_RESPONSE)) and \
               (self.sense_code is None or self.sense_code == SNA_SENSE_CODE_SUCCESS)

    def is_negative(self) -> bool:
        """Check if the response is negative."""
        # A response is negative if it's an exception response or has a non-success sense code
        return (self.flags is not None and (self.flags & SNA_FLAGS_EXCEPTION_RESPONSE)) or \
               (self.sense_code is not None and self.sense_code != SNA_SENSE_CODE_SUCCESS)

    def get_sense_code_name(self) -> str:
        """Get a human-readable name for the sense code."""
        sense_names = {
            SNA_SENSE_CODE_SUCCESS: "SUCCESS",
            SNA_SENSE_CODE_INVALID_FORMAT: "INVALID_FORMAT",
            SNA_SENSE_CODE_NOT_SUPPORTED: "NOT_SUPPORTED",
            SNA_SENSE_CODE_SESSION_FAILURE: "SESSION_FAILURE",
            SNA_SENSE_CODE_INVALID_REQUEST: "INVALID_REQUEST",
            SNA_SENSE_CODE_LU_BUSY: "LU_BUSY",
            SNA_SENSE_CODE_INVALID_SEQUENCE: "INVALID_SEQUENCE",
            SNA_SENSE_CODE_NO_RESOURCES: "NO_RESOURCES",
            SNA_SENSE_CODE_STATE_ERROR: "STATE_ERROR",
        }
        return sense_names.get(self.sense_code, f"UNKNOWN_SENSE(0x{self.sense_code:04x})")

    def get_response_type_name(self) -> str:
        """Get a human-readable name for the response type."""
        response_type_names = {
            SNA_COMMAND_RESPONSE: "COMMAND_RESPONSE",
            SNA_DATA_RESPONSE: "DATA_RESPONSE",
            SNA_RESPONSE_CODE_POSITIVE_ACK: "POSITIVE_ACKNOWLEDGMENT",
            SNA_RESPONSE_CODE_NEGATIVE_ACK: "NEGATIVE_ACKNOWLEDGMENT",
        }
        return response_type_names.get(self.response_type, f"UNKNOWN_RESPONSE_TYPE(0x{self.response_type:02x})")

    def get_flags_name(self) -> str:
        """Get a human-readable name for the flags."""
        if self.flags is None:
            return "NO_FLAGS"
        flag_names = []
        if self.flags & SNA_FLAGS_DEFINITE_RESPONSE_1:
            flag_names.append("DR1")
        if self.flags & SNA_FLAGS_DEFINITE_RESPONSE_2:
            flag_names.append("DR2")
        if self.flags & SNA_FLAGS_EXCEPTION_RESPONSE:
            flag_names.append("ER")
        if self.flags & SNA_FLAGS_RSP:
            flag_names.append("RSP")
        if self.flags & SNA_FLAGS_CHAIN_FIRST:
            flag_names.append("FC")
        if self.flags & SNA_FLAGS_CHAIN_MIDDLE:
            flag_names.append("MC")
        if self.flags & SNA_FLAGS_CHAIN_LAST:
            flag_names.append("LC")
        if not flag_names:
            return f"UNKNOWN_FLAGS(0x{self.flags:02x})"
        return "|".join(flag_names)


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

    def __init__(self, screen_buffer: "ScreenBuffer", printer_buffer: Optional["PrinterBuffer"] = None, negotiator: Optional["Negotiator"] = None):
        """
        Initialize the DataStreamParser.

        :param screen_buffer: ScreenBuffer to update.
        :param printer_buffer: PrinterBuffer to update for printer sessions.
        :param negotiator: Negotiator instance for communicating dimension updates.
        """
        self.screen = screen_buffer
        self.printer = printer_buffer
        self.negotiator = negotiator
        self._data = b""
        self._pos = 0
        self.wcc = None  # Write Control Character
        self.aid = None  # Attention ID
        self._is_scs_data_stream = False # Flag to indicate if the current stream is SCS data

    def get_aid(self) -> Optional[int]:
        """Get the current AID value."""
        return self.aid

    def parse(self, data: bytes, data_type: int = TN3270_DATA) -> None:
        """
        Parse 3270 data stream or other data types.
        
        Args:
            data: Bytes to parse.
            data_type: TN3270E data type (default TN3270_DATA).
        
        Raises:
            ParseError: For parsing errors.
        """
        logger.debug(f"Parsing data of type {data_type:02x}: {data.hex()[:50]}...")
        
        if data_type == NVT_DATA:
            logger.info("Received NVT_DATA - passing to NVT handler")
            # For now, just log; actual NVT handling would go here
            return
        elif data_type == SSCP_LU_DATA:
            logger.info("Received SSCP_LU_DATA - handling SSCP-LU communication")
            # Handle SSCP-LU data (e.g., BIND, UNBIND)
            return
        elif data_type == PRINT_EOJ:
            logger.info("Received PRINT_EOJ - end of print job")
            if self.printer:
                self.printer.end_job()
            return
        elif data_type == BIND_IMAGE:
            logger.info(f"Received BIND_IMAGE data type: {data.hex()}. Parsing as BIND-IMAGE structured field.")
            bind_image = self._parse_bind_image(data)
            if self.negotiator:
                self.negotiator.handle_bind_image(bind_image)
            return
        elif data_type == TN3270E_SCS_CTL_CODES:
            logger.info(f"Received TN3270E_SCS_CTL_CODES data type: {data.hex()}. Processing SCS control codes.")
            self._handle_scs_ctl_codes(data)
            return
        elif data_type not in [TN3270_DATA, SCS_DATA]:
            logger.warning(f"Unhandled TN3270E data type: 0x{data_type:02x}. Processing as TN3270_DATA.")
            data_type = TN3270_DATA
        
        if data_type == SCS_DATA and self.printer:
            logger.info("Received SCS_DATA - routing to printer buffer")
            self._handle_scs_data(data)
            return
        
        self._data = data
        self._pos = 0
        self.wcc = None
        self.aid = None
        
        try:
            while self._pos < len(self._data):
                order = self._data[self._pos]
                self._pos += 1
                
                if order == WCC:
                    wcc = self._read_byte()
                    self._handle_wcc(wcc)
                elif order == SBA:
                    self._handle_sba()
                elif order == SF:
                    self._handle_sf()
                elif order == RA:
                    self._handle_ra()
                elif order == GE:
                    self._handle_ge()
                elif order == IC:
                    self._handle_ic()
                elif order == PT:
                    self._handle_pt()
                elif order == WRITE:
                    self._handle_write()
                elif order == EOA:
                    self._handle_eoa()
                elif order == AID:
                    aid = self._read_byte()
                    self._handle_aid(aid)
                elif order == READ_PARTITION:
                    self._handle_read_partition()
                elif order == SFE:
                    self._handle_sfe()
                elif order == STRUCTURED_FIELD:
                    self._handle_structured_field()
                elif order == BIND:
                    self._handle_bind()
                elif order == SOH:
                    self._handle_soh()
                else:
                    # Unknown order - raise ParseError
                    raise ParseError(f"Unknown or unhandled 3270 order: 0x{order:02x}")
                
            logger.debug("Data stream parsing completed successfully")
        except ParseError as e:
            logger.warning(f"Parse error during data stream processing: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during parsing: {e}", exc_info=True)
            raise ParseError(f"Parsing failed: {e}")

    def _read_byte(self) -> int:
        """Read next byte from stream."""
        if self._pos >= len(self._data):
            raise ParseError("Unexpected end of data")
        byte = self._data[self._pos]
        self._pos += 1
        return byte

    def _insert_data(self, byte: int) -> None:
        """Insert data byte into screen buffer at current position."""
        row, col = self.screen.get_position()
        if 0 <= row < self.screen.rows and 0 <= col < self.screen.cols:
            self.screen.buffer[row * self.screen.cols + col] = byte
            self.screen.set_position(row, col + 1)
        else:
            logger.warning(f"Position out of bounds: ({row}, {col})")

    def _handle_wcc(self, wcc: int) -> None:
        """Handle Write Control Character."""
        self.wcc = wcc
        logger.debug(f"Set WCC to 0x{wcc:02x}")
        # Set screen state based on WCC
        # For now, just store

    def _handle_sba(self) -> None:
        """Handle Set Buffer Address."""
        row = self._read_byte()
        col = self._read_byte()
        self.screen.set_position(row, col)
        logger.debug(f"Set buffer address to ({row}, {col})")

    def _handle_sf(self) -> None:
        """Handle Start Field."""
        attr = self._read_byte()
        self.screen.set_attribute(attr)
        logger.debug(f"Start field with attribute 0x{attr:02x}")

    def _handle_ra(self) -> None:
        """Handle Repeat to Address."""
        attr = self._read_byte()
        repeat = self._read_byte()
        self.screen.repeat_attribute(attr, repeat)
        logger.debug(f"Repeat attribute 0x{attr:02x} {repeat} times")

    def _handle_ge(self) -> None:
        """Handle Graphic Ellipsis."""
        # GE (Graphic Ellipsis) - may not take parameters in some implementations
        logger.debug("Graphic ellipsis - not fully implemented")

    def _handle_ic(self) -> None:
        """Handle Insert Cursor."""
        self.screen.move_cursor_to_first_input_field()
        logger.debug("Insert cursor - moved to first input field")

    def _handle_pt(self) -> None:
        """Handle Program Tab."""
        self.screen.program_tab()
        logger.debug("Program tab")

    def _handle_write(self) -> None:
        """Handle Write order."""
        self.screen.clear()
        logger.debug("Write order - screen cleared")

    def _handle_eoa(self) -> None:
        """Handle End of Aid."""
        logger.debug("End of Aid")

    def _handle_aid(self, aid: int) -> None:
        """Handle Attention ID."""
        self.aid = aid
        logger.debug(f"Attention ID 0x{aid:02x}")

    def _handle_read_partition(self) -> None:
        """Handle Read Partition."""
        logger.debug("Read Partition - not implemented")
        # Would trigger read from keyboard, but for parser, just log

    def _handle_sfe(self) -> None:
        """Handle Start Field Extended."""
        attr_type = self._read_byte()
        attr_value = self._read_byte()
        self.screen.set_extended_attribute_sfe(attr_type, attr_value)
        logger.debug(f"Start Field Extended: type 0x{attr_type:02x}, value 0x{attr_value:02x}")

    def _handle_bind(self) -> None:
        """Handle BIND order."""
        logger.debug("BIND order - not fully implemented")
        # BIND order doesn't contain screen dimensions, so create a default BindImage
        if self.negotiator:
            default_bind_image = BindImage(rows=24, cols=80)  # Default dimensions
            self.negotiator.handle_bind_image(default_bind_image)

    def _handle_structured_field(self) -> None:
        """Handle Structured Field."""
        length = self._read_byte()  # Length of the structured field
        sf_type = self._read_byte()  # Structured Field Type
        logger.debug(f"Structured Field: length={length}, type=0x{sf_type:02x}")
        
        if sf_type == BIND_SF_TYPE:
            # Parse BIND-IMAGE
            bind_image = self._parse_bind_image(self._data[self._pos - length + 3 : self._pos])
            if self.negotiator:
                self.negotiator.handle_bind_image(bind_image)
        else:
            self._skip_structured_field(sf_type, self._data[self._pos - length + 3 : self._pos])

    def _skip_structured_field(self, sf_type: int, data: bytes) -> None:
        """Skip unknown structured field."""
        logger.debug(f"Skipping unknown structured field type 0x{sf_type:02x}, data length {len(data)}")

    def _handle_scs_data(self, data: bytes) -> None:
        """Handle SCS data by routing it to the printer buffer."""
        if self.printer:
            self.printer.write_scs_data(data)
            logger.debug(f"Routed {len(data)} bytes of SCS data to printer buffer")
        else:
            logger.warning("Received SCS data but no printer buffer available")

    def _handle_scs_ctl_codes(self, data: bytes) -> None:
        """Handle SCS control codes."""
        if len(data) >= 1:
            ctl_code = data[0]
            logger.debug(f"Processing SCS control code: 0x{ctl_code:02x}")
            # Handle specific SCS control codes
            if ctl_code == 0x01:  # PRINT_EOJ
                if self.printer:
                    self.printer.end_job()
                    logger.debug("Processed PRINT_EOJ control code")
            else:
                logger.debug(f"Unhandled SCS control code: 0x{ctl_code:02x}")
        else:
            logger.warning("Received empty SCS control codes data")

    def _handle_soh(self) -> None:
        """Handle Start of Header (SOH) for printer status."""
        # Read the status byte that follows SOH
        status = self._read_byte()
        logger.debug(f"Received SOH with status: 0x{status:02x}")
        if self.printer:
            self.printer.update_status(status)
        else:
            logger.warning(f"Received SOH status 0x{status:02x} but no printer buffer available")

    def _parse_bind_image(self, data: bytes) -> BindImage:
        """Parse BIND-IMAGE structured field."""
        pos = 0
        rows = None
        cols = None
        query_reply_ids = []
        
        while pos < len(data):
            subfield_len = data[pos]
            pos += 1
            if pos >= len(data):
                break
            subfield_id = data[pos]
            pos += 1
            
            if subfield_id == BIND_SF_SUBFIELD_PSC:
                # PSC subfield: rows (2 bytes), cols (2 bytes)
                if pos + 4 <= len(data):
                    rows = (data[pos] << 8) | data[pos+1]
                    cols = (data[pos+2] << 8) | data[pos+3]
                    pos += 4
            elif subfield_id == BIND_SF_SUBFIELD_QUERY_REPLY_IDS:
                # Query Reply IDs: variable length list
                num_ids = (len(data) - pos - 1) // 1  # Each ID is 1 byte
                for i in range(num_ids):
                    if pos < len(data):
                        query_reply_ids.append(data[pos])
                        pos += 1
                    else:
                        break
            else:
                # Skip unknown subfield
                pos += subfield_len - 2  # length and id already read
            
            if pos >= len(data):
                break
        
        return BindImage(rows=rows, cols=cols, query_reply_ids=query_reply_ids)


class DataStreamSender:
    """Data stream sender for building 3270 protocol data streams."""

    def build_read_modified_all(self) -> bytes:
        """Build a read modified all command."""
        # AID (0x7D = ENTER) + Read Partition (0xF1)
        return b"\x7d\xf1"

    def build_read_modified_fields(self) -> bytes:
        """Build a read modified fields command."""
        # AID (0x7D) + AID order (0xF6) + 0xF0 (?)
        return b"\x7d\xf6\xf0"

    def build_key_press(self, aid: int) -> bytes:
        """Build a key press command."""
        return bytes([aid])

    def build_write(self, data: bytes) -> bytes:
        """Build a write command."""
        # WCC (0xF5) + some control + WRITE (0x05) + data + EOA (0x0D)
        return b"\xf5\xc1\x05" + data + b"\x0d"

    def build_input_stream(self, modified_fields: List[Tuple[int, bytes]], aid: int, cols: int) -> bytes:
        """Build input stream from modified fields."""
        # This is a simplified implementation
        stream = bytearray()
        stream.append(aid)  # AID
        
        for pos, field_data in modified_fields:
            # SBA to position
            row = pos // cols
            col = pos % cols
            sba_addr = (row << 6) | col  # Simplified addressing
            stream.extend([SBA, sba_addr])
            stream.extend(field_data)
        
        stream.append(EOA)  # End of Area
        return bytes(stream)

    def build_sba(self, row: int, col: int) -> bytes:
        """Build Set Buffer Address command."""
        # SBA + 2-byte address
        addr_high = (row >> 4) & 0x3F  # High 6 bits of row
        addr_low = ((row & 0x0F) << 4) | (col & 0x3F)  # Low 4 bits of row + 6 bits of col
        return bytes([SBA, addr_high, addr_low])

    def build_scs_ctl_codes(self, code: int) -> bytes:
        """Build SCS control codes."""
        return bytes([SCS_CTL_CODES, code])

    def build_data_stream_ctl(self, code: int) -> bytes:
        """Build data stream control."""
        return bytes([DATA_STREAM_CTL, code])

    def build_query_sf(self, query_type: int) -> bytes:
        """Build query structured field."""
        # Length is 1 (just the query_type byte)
        return bytes([STRUCTURED_FIELD, 0x00, 0x01, query_type])

    def build_printer_status_sf(self, status_code: int) -> bytes:
        """Build printer status structured field."""
        # SF payload: type + status_code
        payload = bytes([PRINTER_STATUS_SF_TYPE, status_code])
        # Length includes type byte and length field itself? Wait, let's check the test
        # expected_sf = bytes([STRUCTURED_FIELD]) + (len(expected_sf_payload) + 2).to_bytes(2, 'big') + expected_sf_payload
        # expected_sf_payload = bytes([PRINTER_STATUS_SF_TYPE, status_code])
        # So length = len(payload) + 2 = 2 + 2 = 4
        length = len(payload) + 2  # +2 for the length field itself?
        return bytes([STRUCTURED_FIELD]) + length.to_bytes(2, 'big') + payload

    def build_soh_message(self, status_code: int) -> bytes:
        """Build SOH (Start of Header) message."""
        return bytes([SOH, status_code])
