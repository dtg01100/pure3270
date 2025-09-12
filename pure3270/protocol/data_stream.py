"""Data stream parser and sender for 3270 protocol."""

from typing import List, Tuple, Optional
import logging
from typing import TYPE_CHECKING
from ..emulation.screen_buffer import ScreenBuffer # Import ScreenBuffer
from ..emulation.printer_buffer import PrinterBuffer # Import PrinterBuffer
from .utils import (
    TN3270_DATA, SCS_DATA, RESPONSE, BIND_IMAGE, UNBIND, NVT_DATA, REQUEST, SSCP_LU_DATA, PRINT_EOJ,
    SNA_RESPONSE as SNA_RESPONSE_TYPE # Use an alias to avoid name conflict with SNA_RESPONSE class
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
        return (f"SnaResponse(type=0x{self.response_type:02x}, "
                f"flags=0x{self.flags:02x if self.flags is not None else 'None'}, "
                f"sense_code=0x{self.sense_code:04x if self.sense_code is not None else 'None'}, "
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

    def parse(self, data: bytes, data_type: int = 0x00) -> None: # 0x00 is TN3270_DATA
        """
        Parse 3270 data stream.

        :param data: Incoming 3270 data stream bytes.
        :param data_type: The type of data (e.g., TN3270_DATA, SCS_DATA).
        :raises ParseError: If parsing fails.
        """
        self._data = data
        self._pos = 0
        self._is_scs_data_stream = (data_type == SCS_DATA)
        logger.debug(f"Parsing {len(data)} bytes of data stream (Type: {data_type})")

        if data_type == SCS_DATA:
            self._handle_scs_data(data)
            return
        elif data_type == NVT_DATA:
            logger.info(f"Received NVT_DATA: {data.hex()}. This data type is typically handled by a VT100 parser.")
            # NVT_DATA is not 3270 data, so the 3270 parser should not process it.
            # The TN3270Handler is responsible for routing this to a VT100 parser if in ASCII mode.
            return
        elif data_type == RESPONSE:
            logger.info(f"Received RESPONSE data type: {data.hex()}. This is a TN3270E response message.")
            # Response data is typically handled by the Negotiator for correlation.
            return
        elif data_type == REQUEST:
            logger.info(f"Received REQUEST data type: {data.hex()}. This is a TN3270E request message.")
            # Request data is typically handled by the Negotiator.
            return
        elif data_type == SSCP_LU_DATA:
            logger.info(f"Received SSCP_LU_DATA data type: {data.hex()}.")
            # SSCP-LU Data is typically handled at a higher level for LU management.
            return
        elif data_type == PRINT_EOJ:
            logger.info(f"Received PRINT_EOJ data type: {data.hex()}. This indicates End of Job for printer sessions.")
            # PRINT_EOJ is handled by SCS control codes as well.
            return
        elif data_type == BIND_IMAGE:
            # BIND_IMAGE data type is handled by processing the structured field within the data.
            # The actual structured field will be parsed below.
            logger.info(f"Received BIND_IMAGE data type. Processing as 3270 data stream.")
        elif data_type == SNA_RESPONSE_DATA_TYPE:
            logger.info(f"Received SNA_RESPONSE data type: {data.hex()}. Parsing as SNA response.")
            self._handle_sna_response_data(data)
            return
        elif data_type == PRINTER_STATUS_DATA_TYPE:
            logger.info(f"Received PRINTER_STATUS data type: {data.hex()}. Parsing as printer status.")
            self._handle_printer_status_data(data)
            return
        elif data_type != TN3270_DATA:
            logger.warning(f"Unhandled TN3270E data type: 0x{data_type:02x}. Processing as TN3270_DATA.")

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
                    self._handle_read_partition_query()
                elif order == SBA:  # SBA (Set Buffer Address)
                    self._handle_sba()
                elif order == SF:  # SF (Start Field)
                    self._handle_sf()
                elif order == RA:  # RA (Repeat to Address)
                    self._handle_ra()
                elif order == GE:  # GE (Graphic Escape)
                    self._handle_ge()
                elif order == WRITE:  # W (Write)
                    self._handle_write()
                elif order == EOA:  # EOA (End of Addressable)
                    break
                elif order == SCS_CTL_CODES:  # SCS Control Codes
                    self._handle_scs_ctl_codes()
                elif order == DATA_STREAM_CTL:  # Data Stream Control
                    self._handle_data_stream_ctl()
                elif order == STRUCTURED_FIELD: # Structured Field
                    self._handle_structured_field()
                elif order == IC: # Insert Cursor
                    self._handle_ic()
                elif order == PT: # Program Tab
                    self._handle_pt()
                elif order == SOH: # SOH (Start of Header) for printer status
                    self._handle_soh_message()
                else:
                    # If it's not a recognized order, treat it as a data character
                    self._handle_data(order)

        except IndexError:
            raise ParseError("Unexpected end of data stream")
        finally:
            self.screen.update_fields() # Ensure fields are updated after parsing

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
        # If a printer buffer is available, pass the SCS data to it.
        if self.printer:
            logger.debug(f"Passing SCS data to printer buffer: {data.hex()}")
            self.printer.write_scs_data(data)
        else:
            logger.warning("No printer buffer available to handle SCS data.")

    def _handle_data(self, byte: int):
        """Handle data byte."""
        row, col = self.screen.get_position()
        self.screen.write_char(byte, row, col)
        col += 1
        if col >= self.screen.cols:
            col = 0
            row += 1
        self.screen.set_position(row, col)

    def _handle_sna_response_data(self, data: bytes):
        """
        Handle incoming SNA response data.

        This method is called when the TN3270E header indicates
        SNA_RESPONSE_DATA_TYPE. The data payload is expected to contain
        the SNA response structure.
        """
        logger.debug(f"Handling SNA response data: {data.hex()}")
        # Parse the SNA response data.
        # For simplicity, assume a fixed format:
        # Byte 0: Response Type (e.g., SNA_COMMAND_RESPONSE, SNA_DATA_RESPONSE)
        # Bytes 1-2: Sense Code (if present, 2 bytes)
        # Remaining bytes: Optional additional data

        response_type = data[0] if len(data) > 0 else 0x00
        sense_code = None
        response_payload = b""

        flags = None
        if len(data) >= 2:
            flags = data[1]
        
        if len(data) >= 4:
            sense_code = (data[2] << 8) | data[3]
            response_payload = data[4:]
        elif len(data) >= 2: # If only type and flags are present
            response_payload = data[2:]
        elif len(data) >= 1:
            response_payload = data[1:]

        sna_response = SnaResponse(response_type, flags, sense_code, response_payload)
        logger.info(f"Parsed SNA Response: {sna_response}")

        # Pass the parsed SNA response to the negotiator for further handling
        if self.negotiator:
            self.negotiator._handle_sna_response(sna_response)
        else:
            logger.warning("Negotiator not available to handle SNA response.")


    def _handle_structured_field(self):
        """Handle Structured Field command."""
        logger.debug("Structured Field command received")
        # Structured Field format: SF_ID (0x3C), Length (2 bytes), SF_Type (1 byte), Data
        if self._pos + 3 >= len(self._data):
            logger.warning("Incomplete Structured Field header.")
            self._pos = len(self._data) # Skip to end
            return

        sf_len = (self._data[self._pos] << 8) | self._data[self._pos + 1]
        sf_type_pos = self._pos + 2
        self._pos += 3 # Move past length and SF_Type byte

        if self._pos + sf_len - 3 > len(self._data): # sf_len includes the type byte itself, so subtract 3 (len bytes + type byte)
            logger.warning(f"Structured Field data truncated. Expected {sf_len}, got {len(self._data) - self._pos + 3}")
            self._pos = len(self._data) # Skip to end
            return

        sf_type = self._data[sf_type_pos]
        sf_data_start = sf_type_pos + 1 # Data starts after SF_Type
        sf_data_end = sf_type_pos + sf_len # Data ends at sf_type_pos + sf_len - 1

        if sf_type == QUERY_REPLY_SF:
            if sf_data_start >= len(self._data):
                logger.warning("Incomplete Query Reply Structured Field.")
                return

            query_reply_type = self._data[sf_data_start]
            logger.debug(f"Query Reply SF received. Type: 0x{query_reply_type:02x}")

            if query_reply_type == QUERY_REPLY_CHARACTERISTICS:
                if sf_len >= 5 and sf_data_start + 4 <= sf_data_end:
                    rows = (self._data[sf_data_start + 1] << 8) | self._data[sf_data_start + 2]
                    cols = (self._data[sf_data_start + 3] << 8) | self._data[sf_data_start + 4]
                    logger.info(f"Parsed QUERY_REPLY_CHARACTERISTICS: Rows={rows}, Cols={cols}")
                    if self.negotiator:
                        self.negotiator._set_screen_dimensions_from_query_reply(rows, cols)
                    else:
                        logger.warning("Negotiator not available to update screen dimensions.")
                else:
                    logger.warning("Incomplete QUERY_REPLY_CHARACTERISTICS data.")
            else:
                logger.debug(f"Unhandled Query Reply Type: 0x{query_reply_type:02x}")
        elif sf_type == SFE: # Handle Start Field Extended
            self._handle_sfe_attributes(self._data[sf_data_start:sf_data_end])
        elif sf_type == BIND_SF_TYPE:
            self._handle_bind_sf(self._data[sf_data_start:sf_data_end])
        elif sf_type == SNA_RESPONSE_SF_TYPE:
            self._handle_sna_response_data(self._data[sf_data_start:sf_data_end])
        elif sf_type == PRINTER_STATUS_SF_TYPE:
            logger.info(f"Received PRINTER_STATUS_SF_TYPE. Data: {self._data[sf_data_start:sf_data_end].hex()}")
            self._handle_printer_status_sf(self._data[sf_data_start:sf_data_end])
        else:
            logger.debug(f"Unhandled Structured Field Type: 0x{sf_type:02x}")

        # Advance position past the structured field data
        self._pos = sf_type_pos + sf_len

    def _handle_sfe_attributes(self, sfe_data: bytes):
        """
        Handle Start Field Extended (SFE) attributes.
        Parses the SFE data and applies extended attributes to the screen buffer.
        """
        logger.debug(f"Handling SFE attributes: {sfe_data.hex()}")
        current_row, current_col = self.screen.get_position()
        i = 0
        while i < len(sfe_data):
            ext_attr_type = sfe_data[i]
            i += 1
            if i >= len(sfe_data):
                logger.warning("Incomplete SFE attribute: type without value.")
                break

            ext_attr_value = sfe_data[i]
            i += 1

            if ext_attr_type == EXT_ATTR_HIGHLIGHT:
                self.screen.set_extended_attribute(current_row, current_col, 'highlight', ext_attr_value)
            elif ext_attr_type == EXT_ATTR_COLOR:
                self.screen.set_extended_attribute(current_row, current_col, 'color', ext_attr_value)
            elif ext_attr_type == EXT_ATTR_CHARACTER_SET:
                self.screen.set_extended_attribute(current_row, current_col, 'character_set', ext_attr_value)
            elif ext_attr_type == EXT_ATTR_FIELD_VALID:
                self.screen.set_extended_attribute(current_row, current_col, 'validation', ext_attr_value)
            elif ext_attr_type == EXT_ATTR_OUTLINE:
                self.screen.set_extended_attribute(current_row, current_col, 'outlining', ext_attr_value)
            else:
                logger.warning(f"Unknown SFE extended attribute type: 0x{ext_attr_type:02x}")

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
                BIND, # Added BIND here
                WRITE,
                EOA,
                SCS_CTL_CODES,
                DATA_STREAM_CTL,
                STRUCTURED_FIELD,
            ]:
                break
            self._pos += 1
        logger.debug("Skipped structured field")

    def _handle_bind_sf(self, bind_data: bytes):
        """
        Handle BIND Structured Field.
        Parses the BIND-IMAGE content and passes it to the negotiator.
        """
        logger.info(f"Received BIND Structured Field: {bind_data.hex()}")
        
        # Initialize BindImage object
        bind_image = BindImage()

        # Parse BIND-IMAGE subfields (RFC 2355, Section 5.1)
        # The BIND-IMAGE data consists of a sequence of subfields, each with a length and ID.
        offset = 0
        while offset < len(bind_data):
            if offset + 1 >= len(bind_data):
                logger.warning("Incomplete BIND-IMAGE subfield header (length byte missing).")
                break
            
            subfield_len = bind_data[offset]
            subfield_id = bind_data[offset + 1]
            
            # Ensure the subfield data is within bounds
            if offset + subfield_len > len(bind_data):
                logger.warning(f"Truncated BIND-IMAGE subfield (ID: 0x{subfield_id:02x}, expected len: {subfield_len}, actual remaining: {len(bind_data) - offset}).")
                break
            
            subfield_data = bind_data[offset + 2 : offset + subfield_len]
            
            if subfield_id == BIND_SF_SUBFIELD_PSC:
                # Presentation Space Control (PSC) subfield
                # Format: Length (1 byte), ID (0x01), Rows (2 bytes), Columns (2 bytes)
                if len(subfield_data) >= 4:
                    rows = (subfield_data[0] << 8) | subfield_data[1]
                    cols = (subfield_data[2] << 8) | subfield_data[3]
                    bind_image.rows = rows
                    bind_image.cols = cols
                    logger.debug(f"Parsed BIND-IMAGE PSC: Rows={rows}, Cols={cols}")
                else:
                    logger.warning(f"Incomplete PSC subfield data: {subfield_data.hex()}")
            elif subfield_id == BIND_SF_SUBFIELD_QUERY_REPLY_IDS:
                # Query Reply IDs subfield
                # Format: Length (1 byte), ID (0x02), List of Query Reply IDs (1 byte each)
                bind_image.query_reply_ids = list(subfield_data)
                logger.debug(f"Parsed BIND-IMAGE Query Reply IDs: {bind_image.query_reply_ids}")
            else:
                logger.warning(f"Unknown BIND-IMAGE subfield ID: 0x{subfield_id:02x} with data: {subfield_data.hex()}")
            
            offset += subfield_len # Move to the next subfield

        # Pass the parsed BindImage object to the negotiator
        if self.negotiator:
            self.negotiator.handle_bind_image(bind_image)
        else:
            logger.warning("Negotiator not available to handle BIND-IMAGE.")

    def _handle_printer_status_sf(self, status_data: bytes):
        """
        Handle incoming Printer Status Structured Field data.
        This is a placeholder; actual parsing depends on the specific SF format.
        """
        logger.info(f"Processing printer status SF data: {status_data.hex()}")
        # Example: if the status data is a single byte representing a status code
        if len(status_data) >= 1:
            status_code = status_data[0]
            logger.info(f"Printer Status Code: 0x{status_code:02x}")
            # Update negotiator/handler state with the printer status
            if self.negotiator:
                self.negotiator.update_printer_status(status_code)
            if self.printer:
                self.printer.update_status(status_code) # Assuming PrinterBuffer can take status updates
        else:
            logger.warning("Empty printer status SF data.")

    def _handle_soh_message(self):
        """
        Handle SOH (Start of Header) messages for printer status.
        This is a placeholder; actual parsing depends on the specific SOH format.
        """
        # SOH messages are typically followed by a status byte or sequence.
        # For simplicity, assume the next byte is the status.
        if self._pos < len(self._data):
            soh_status = self._data[self._pos]
            self._pos += 1
            logger.info(f"Received SOH message with status: 0x{soh_status:02x}")
            # Update negotiator/handler state with the printer status
            if self.negotiator:
                self.negotiator.update_printer_status(soh_status)
            if self.printer:
                self.printer.update_status(soh_status) # Assuming PrinterBuffer can take status updates
        else:
            logger.warning("SOH message received but no status byte followed.")

    def _handle_printer_status_data(self, data: bytes):
        """
        Handle incoming PRINTER_STATUS_DATA_TYPE.
        This method is called when the TN3270E header indicates PRINTER_STATUS_DATA_TYPE.
        The data payload is expected to contain the printer status structure.
        """
        logger.debug(f"Handling printer status data: {data.hex()}")
        # This could be a raw status byte, or a more complex structure.
        # For now, assuming it's a single status byte directly.
        if len(data) >= 1:
            status_code = data[0]
            logger.info(f"Printer Status (from TN3270E DATA-TYPE): 0x{status_code:02x}")
            if self.negotiator:
                self.negotiator.update_printer_status(status_code)
            if self.printer:
                self.printer.update_status(status_code) # Assuming PrinterBuffer can take status updates
        else:
            logger.warning("Empty PRINTER_STATUS_DATA_TYPE received.")

    def _handle_read_partition_query(self):
        """Handle Read Partition Query command."""
        logger.debug("Read Partition Query command received")
        # In a full implementation, this would trigger sending Query Reply SFs
        # to inform the host about our capabilities

    def _handle_ic(self):
        """Handle Insert Cursor (IC) order."""
        logger.debug("IC (Insert Cursor) order received")
        self.screen.move_cursor_to_first_input_field()

    def _handle_pt(self):
        """Handle Program Tab (PT) order."""
        logger.debug("PT (Program Tab) order received")
        self.screen.move_cursor_to_next_input_field()

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
        # AID for Enter + Read Partition (simplified for RMA)
        stream = bytearray([0x7D, 0xF1])
        return bytes(stream)

    def build_query_sf(self, query_type: int) -> bytes:
        """
        Build a Query Structured Field (SF).

        :param query_type: The type of query (e.g., QUERY_REPLY_CHARACTERISTICS).
        :return: Query Structured Field bytes.
        """
        sf = bytearray()
        sf.append(STRUCTURED_FIELD)  # SF identifier (0x3C)
        # Length of data following the length field itself (1 byte for query_type)
        length = 1 # For simple query SFs, length is 1 (the query_type itself)
        sf.append((length >> 8) & 0xFF) # High byte of length
        sf.append(length & 0xFF)       # Low byte of length
        sf.append(query_type)          # Query Type
        return bytes(sf)

    def build_printer_status_sf(self, status_code: int) -> bytes:
        """
        Build a Printer Status Structured Field.

        :param status_code: The status code to send (e.g., DEVICE_END, INTERVENTION_REQUIRED).
        :return: Printer Status Structured Field bytes.
        """
        sf = bytearray()
        sf.append(STRUCTURED_FIELD) # SF identifier (0x3C)
        # Length of data following the length field itself (1 byte for SF_TYPE, 1 byte for status_code)
        length = 2
        sf.append((length >> 8) & 0xFF) # High byte of length
        sf.append(length & 0xFF)       # Low byte of length
        sf.append(PRINTER_STATUS_SF_TYPE) # Printer Status SF type
        sf.append(status_code)         # Printer Status Code
        return bytes(sf)

    def build_soh_message(self, status_code: int) -> bytes:
        """
        Build an SOH (Start of Header) message for printer status.

        :param status_code: The status code to send (e.g., SOH_SUCCESS, SOH_DEVICE_END).
        :return: SOH message bytes.
        """
        # SOH messages are simple: SOH byte followed by status byte.
        return bytes([SOH, status_code])

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
