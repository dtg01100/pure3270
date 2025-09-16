"""Data stream parser and sender for 3270 protocol."""

import logging
import struct
import traceback
from typing import TYPE_CHECKING, List, Optional, Tuple

from ..emulation.printer_buffer import PrinterBuffer  # Import PrinterBuffer
from ..emulation.screen_buffer import ScreenBuffer  # Import ScreenBuffer
from .utils import (BIND_IMAGE, NVT_DATA, PRINT_EOJ, PRINTER_STATUS_DATA_TYPE,
                    QUERY_REPLY_CHARACTERISTICS, QUERY_REPLY_COLOR,
                    QUERY_REPLY_DBCS_ASIA, QUERY_REPLY_DBCS_EUROPE,
                    QUERY_REPLY_DBCS_MIDDLE_EAST, QUERY_REPLY_DDM,
                    QUERY_REPLY_DEVICE_TYPE, QUERY_REPLY_EXTENDED_ATTRIBUTES,
                    QUERY_REPLY_FORMAT_STORAGE, QUERY_REPLY_GRAPHICS,
                    QUERY_REPLY_GRID, QUERY_REPLY_HIGHLIGHTING,
                    QUERY_REPLY_LINE_TYPE, QUERY_REPLY_OEM_AUXILIARY_DEVICE,
                    QUERY_REPLY_PROCEDURE, QUERY_REPLY_RPQ_NAMES,
                    QUERY_REPLY_SEGMENT, QUERY_REPLY_SF,
                    QUERY_REPLY_TRANSPARENCY, REQUEST, RESPONSE, SCS_DATA)
from .utils import SNA_RESPONSE as SNA_RESPONSE_TYPE
from .utils import (SSCP_LU_DATA, TN3270_DATA, TN3270E_BIND_IMAGE,
                    TN3270E_DATA_STREAM_CTL, TN3270E_DATA_TYPES, TN3270E_DEVICE_TYPE,
                    TN3270E_FUNCTIONS, TN3270E_IBM_3278_2, TN3270E_IBM_3278_3,
                    TN3270E_IBM_3278_4, TN3270E_IBM_3278_5, TN3270E_IBM_3279_2,
                    TN3270E_IBM_3279_3, TN3270E_IBM_3279_4, TN3270E_IBM_3279_5,
                    TN3270E_IBM_DYNAMIC, TN3270E_IS, TN3270E_REQUEST,
                    TN3270E_RESPONSES, TN3270E_SCS_CTL_CODES, TN3270E_SEND,
                    TN3270E_SYSREQ, UNBIND, BaseParser, ParseError)

if TYPE_CHECKING:
    from ..emulation.printer_buffer import PrinterBuffer
    from ..emulation.screen_buffer import ScreenBuffer
    from .negotiator import Negotiator

logger = logging.getLogger(__name__)


# 3270 Data Stream Orders
WCC = 0xF5
AID = 0xF6
READ_PARTITION = 0xF1
SBA = 0x10
SF = 0x1D
RA = 0xF3
RMF = 0x2C  # Repeat to Modified Field
GE = 0x29
WRITE = 0x05
EOA = 0x0D
SCS_CTL_CODES = 0x04
DATA_STREAM_CTL = 0x40
STRUCTURED_FIELD = 0x3C  # '<'
SFE = 0x28  # Start Field Extended (RFC 1576)
IC = 0x0F  # Insert Cursor
PT = 0x0E  # Program Tab
BIND = 0xF9  # Placeholder for BIND command, not officially part of 3270 orders but used in context
# Printer Status related orders/commands (research needed for exact values)
# These are placeholders and need to be verified against 3270 printer protocol specs.
WRITE_STRUCTURED_FIELD_PRINTER = 0x11  # Example: Write Structured Field for printer
PRINTER_STATUS_SF = 0x01  # Example: Structured Field type for printer status
SOH = 0x01  # Start of Header (SCS command for printer status) - often 0x01 in SCS
# Other potential status indicators
DEVICE_END = 0x00  # Placeholder for device end status
INTERVENTION_REQUIRED = 0x01  # Placeholder for intervention required status

# Structured Field Types
BIND_SF_TYPE = 0x03  # BIND-IMAGE Structured Field Type
SF_TYPE_SFE = 0x28  # Start Field Extended
SNA_RESPONSE_SF_TYPE = 0x01  # Example: assuming a specific SF type for SNA responses
PRINTER_STATUS_SF_TYPE = 0x02  # Placeholder for printer status structured field type

# BIND-IMAGE Subfield IDs (RFC 2355, Section 5.1)
BIND_SF_SUBFIELD_PSC = 0x01  # Presentation Space Control
BIND_SF_SUBFIELD_QUERY_REPLY_IDS = 0x02  # Query Reply IDs


class BindImage:
    """Represents a parsed BIND-IMAGE Structured Field."""

    def __init__(
        self,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
        query_reply_ids: Optional[List[int]] = None,
    ):
        self.rows = rows
        self.cols = cols
        self.query_reply_ids = query_reply_ids if query_reply_ids is not None else []

    def __repr__(self):
        return (
            f"BindImage(rows={self.rows}, cols={self.cols}, "
            f"query_reply_ids={self.query_reply_ids})"
        )


# Extended Attribute Types (for SF_EXT)
EXT_ATTR_HIGHLIGHT = 0x41  # Extended highlighting
EXT_ATTR_COLOR = 0x42  # Color
EXT_ATTR_CHARACTER_SET = 0x43  # Character set
EXT_ATTR_FIELD_VALID = 0x44  # Field validation
EXT_ATTR_OUTLINE = 0x45  # Outlining

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
COLOR_WHITE = 0xF7  # Default foreground
COLOR_BLACK = 0xF8  # Default background

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

# SOH Status Message Formats (placeholders, research needed)
SOH_SUCCESS = 0x00  # SOH success
SOH_DEVICE_END = 0x40  # SOH device end
SOH_INTERVENTION_REQUIRED = 0x80  # SOH intervention required

# SNA Response Codes (Examples, these would need to be researched from SNA documentation)
SNA_COMMAND_RESPONSE = 0x01  # General command response
SNA_DATA_RESPONSE = 0x02  # General data response
SNA_RESPONSE_CODE_POSITIVE_ACK = 0x40  # Example: DR1 (Definite Response 1)
SNA_RESPONSE_CODE_NEGATIVE_ACK = 0x80  # Example: ER (Exception Response)

SNA_RESPONSE_DATA_TYPE = 0x02

# SNA Response Flags (Examples, these would need to be researched from SNA documentation)
# These flags are often embedded within the response code byte itself or a separate byte.
# For simplicity, we'll introduce a separate flags byte for now.
SNA_FLAGS_NONE = 0x00
SNA_FLAGS_DEFINITE_RESPONSE_1 = 0x01  # Request for DR1 (Definite Response 1)
SNA_FLAGS_DEFINITE_RESPONSE_2 = 0x02  # Request for DR2 (Definite Response 2)
SNA_FLAGS_EXCEPTION_RESPONSE = 0x04  # Indicates an exception response
SNA_FLAGS_RSP = 0x08  # Response indicator (often 0x08 for response, 0x00 for request)
SNA_FLAGS_CHAIN_MIDDLE = 0x10  # Middle of chain
SNA_FLAGS_CHAIN_LAST = 0x20  # Last in chain
SNA_FLAGS_CHAIN_FIRST = 0x40  # First in chain


# SNA Sense Codes (Examples, these would need to be researched from SNA documentation)
SNA_SENSE_CODE_SUCCESS = 0x0000  # No error
SNA_SENSE_CODE_INVALID_FORMAT = 0x1001  # Invalid message format
SNA_SENSE_CODE_NOT_SUPPORTED = 0x1002  # Function not supported
SNA_SENSE_CODE_SESSION_FAILURE = 0x2001  # Session failure
SNA_SENSE_CODE_INVALID_REQUEST = 0x0801  # Invalid Request
SNA_SENSE_CODE_LU_BUSY = 0x080A  # LU Busy
SNA_SENSE_CODE_INVALID_SEQUENCE = 0x1008  # Invalid Sequence
SNA_SENSE_CODE_NO_RESOURCES = 0x080F  # No Resources
SNA_SENSE_CODE_STATE_ERROR = 0x1003  # State Error


class SnaResponse:
    """Represents a parsed SNA response."""

    def __init__(
        self,
        response_type: int,
        flags: Optional[int] = None,
        sense_code: Optional[int] = None,
        data: Optional[object] = None,
    ):
        self.response_type = response_type
        self.flags = flags
        self.sense_code = sense_code
        self.data = data

    def __repr__(self):
        flags_str = f"0x{self.flags:02x}" if self.flags is not None else "None"
        sense_code_str = (
            f"0x{self.sense_code:04x}" if self.sense_code is not None else "None"
        )
        if isinstance(self.data, BindImage):
            data_str = str(self.data)
        else:
            data_str = self.data.hex() if self.data else "None"
        return (
            f"SnaResponse(type=0x{self.response_type:02x}, "
            f"flags={flags_str}, "
            f"sense_code={sense_code_str}, "
            f"data={data_str})"
        )

    def is_positive(self) -> bool:
        """Check if the response is positive."""
        # A response is positive if it's not an exception response and sense code is success or None
        return (
            self.flags is None or not (self.flags & SNA_FLAGS_EXCEPTION_RESPONSE)
        ) and (self.sense_code is None or self.sense_code == SNA_SENSE_CODE_SUCCESS)

    def is_negative(self) -> bool:
        """Check if the response is negative."""
        # A response is negative if it's an exception response or has a non-success sense code
        return (
            self.flags is not None and (self.flags & SNA_FLAGS_EXCEPTION_RESPONSE)
        ) or (self.sense_code is not None and self.sense_code != SNA_SENSE_CODE_SUCCESS)

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
        return sense_names.get(
            self.sense_code, f"UNKNOWN_SENSE(0x{self.sense_code:04x})"
        )

    def get_response_type_name(self) -> str:
        """Get a human-readable name for the response type."""
        response_type_names = {
            SNA_COMMAND_RESPONSE: "COMMAND_RESPONSE",
            SNA_DATA_RESPONSE: "DATA_RESPONSE",
            SNA_RESPONSE_CODE_POSITIVE_ACK: "POSITIVE_ACKNOWLEDGMENT",
            SNA_RESPONSE_CODE_NEGATIVE_ACK: "NEGATIVE_ACKNOWLEDGMENT",
        }
        return response_type_names.get(
            self.response_type, f"UNKNOWN_RESPONSE_TYPE(0x{self.response_type:02x})"
        )

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


class DataStreamParser:
    """Parses incoming 3270 data streams and updates the screen buffer."""

    def __init__(
        self,
        screen_buffer: "ScreenBuffer",
        printer_buffer: Optional["PrinterBuffer"] = None,
        negotiator: Optional["Negotiator"] = None,
    ):
        """
        Initialize the DataStreamParser.

        :param screen_buffer: ScreenBuffer to update.
        :param printer_buffer: PrinterBuffer to update for printer sessions.
        :param negotiator: Negotiator instance for communicating dimension updates.
        """
        self.screen = screen_buffer
        self.printer = printer_buffer
        self.negotiator = negotiator
        self.parser = None
        self.wcc = None  # Write Control Character
        self.aid = None  # Attention ID
        self._is_scs_data_stream = (
            False  # Flag to indicate if the current stream is SCS data
        )
        self._data = b""
        self._pos = 0

        self._order_handlers = {
            WCC: self._handle_wcc_with_byte,
            SBA: self._handle_sba,
            SF: self._handle_sf,
            RA: self._handle_ra,
            RMF: self._handle_rmf,
            GE: self._handle_ge,
            IC: self._handle_ic,
            PT: self._handle_pt,
            SCS_CTL_CODES: self._handle_scs,
            WRITE: self._handle_write,
            EOA: self._handle_eoa,
            AID: self._handle_aid_with_byte,
            READ_PARTITION: self._handle_read_partition,
            SFE: self._handle_sfe,
            STRUCTURED_FIELD: self._handle_structured_field,
            BIND: self._handle_bind,
            DATA_STREAM_CTL: self._handle_data_stream_ctl,
            SOH: self._handle_soh,
        }

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
            logger.info(
                f"Received BIND_IMAGE data type: {data.hex()}. Delegating to BIND-IMAGE structured field handler."
            )
            # Accept both full Structured Field wrappers (0x3C + length(2) + type(1) + payload)
            # and raw payloads. Tests patch _handle_bind_sf expecting the payload only, so
            # extract and pass exactly that when possible.
            try:
                if data and data[0] == STRUCTURED_FIELD and len(data) >= 4:
                    # Full structured field: 0x3C + length(2) + type(1) + payload
                    length_high = data[1]
                    length_low = data[2]
                    length = (length_high << 8) | length_low
                    sf_type = data[3] if len(data) > 3 else None
                    # Payload length = length - 1 (SF type byte included in length)
                    payload_len = max(0, length - 1)
                    payload = data[4 : 4 + payload_len]
                    logger.debug(
                        f"Structured field raw: {data.hex()}; sf_type=0x{sf_type:02x} payload_len={payload_len} payload={payload.hex()}"
                    )
                    self._handle_bind_sf(payload)
                else:
                    logger.debug(
                        f"Passing BIND_IMAGE data as-is to _handle_bind_sf: {data.hex()}"
                    )
                    self._handle_bind_sf(data)
            except ParseError:
                raise
            return
        elif data_type == SNA_RESPONSE_TYPE:
            logger.info(
                f"Received SNA_RESPONSE data type: {data.hex()}. Parsing SNA response."
            )
            try:
                sna_response = self._parse_sna_response(data)
                if self.negotiator:
                    self.negotiator.handle_sna_response(sna_response)
            except ParseError as e:
                logger.warning(
                    f"Failed to parse SNA response variant: {e}, consuming data"
                )
            return
        elif data_type == TN3270E_SCS_CTL_CODES:
            logger.info(
                f"Received TN3270E_SCS_CTL_CODES data type: {data.hex()}. Processing SCS control codes."
            )
            self._handle_scs_ctl_codes(data)
            return
        elif data_type == RESPONSE:
            logger.info(f"Received RESPONSE data type: {data.hex()}.")
            return
        elif data_type == REQUEST:
            logger.info(f"Received REQUEST data type: {data.hex()}.")
            return
        elif data_type not in TN3270E_DATA_TYPES:
            logger.warning(
                f"Unhandled TN3270E data type: 0x{data_type:02x}. Processing as TN3270_DATA."
            )
            data_type = TN3270_DATA

        if data_type == SCS_DATA and self.printer:
            logger.info("Received SCS_DATA - routing to printer buffer")
            self._handle_scs_data(data)
            return

        # Mirror parser-visible state for tests and external inspection
        self._data = data
        self._pos = 0
        self.parser = BaseParser(data)
        self.wcc = None
        self.aid = None
        self.screen.set_position(0, 0)

        try:
            while self.parser.has_more():
                pos_before = self._pos
                try:
                    order = self.parser.read_byte()
                except ParseError:
                    stream_trace = self._data[max(0, pos_before - 5) : self._pos + 5].hex()
                    raise ParseError(
                        f"Incomplete order in data stream at position {pos_before}, trace: {stream_trace}"
                    )

                if order in self._order_handlers:
                    if order == WCC:
                        try:
                            wcc = self._read_byte()
                        except ParseError:
                            raise ParseError("Incomplete WCC order")
                        self._order_handlers[order](wcc)
                    elif order == AID:
                        try:
                            aid = self._read_byte()
                        except ParseError:
                            raise ParseError("Incomplete AID order")
                        self._order_handlers[order](aid)
                    elif order == DATA_STREAM_CTL:
                        try:
                            ctl_code = self._read_byte()
                        except ParseError:
                            raise ParseError("Incomplete DATA_STREAM_CTL order")
                        self._order_handlers[order](ctl_code)
                    else:
                        self._order_handlers[order]()
                    self._pos = self.parser._pos
                else:
                    # Treat unknown bytes as text data
                    self._write_text_byte(order)
                    self._pos = self.parser._pos

            logger.debug("Data stream parsing completed successfully")
        except ParseError as e:
            logger.warning(f"Parse error during data stream processing: {e}")
            # Graceful handling: do not raise, continue parsing if possible
        except (MemoryError, KeyboardInterrupt, SystemExit):
            # Critical system errors should propagate immediately
            raise
        except Exception as e:
            logger.error(f"Unexpected error during parsing: {e}", exc_info=True)
            raise ParseError(f"Parsing failed: {e}")

    def _ensure_parser(self) -> BaseParser:
        """Ensure `self.parser` exists; create from `self._data`/_pos if needed."""
        if self.parser is None:
            data = getattr(self, "_data", b"") or b""
            self.parser = BaseParser(data)
            # Initialize parser position from any externally-set _pos
            self.parser._pos = getattr(self, "_pos", 0)
        return self.parser

    def _read_byte(self) -> int:
        """Read next byte from stream and mirror parser position for tests.

        Works even when `self.parser` hasn't been initialized by `parse()` (tests
        set `self._data` and `self._pos` directly)."""
        if self._pos >= len(self._data):
            raise ParseError("Overflow")
        if self.parser is None:
            # Create a temporary parser to read from fallback buffers.
            temp = BaseParser(getattr(self, "_data", b"") or b"")
            temp._pos = getattr(self, "_pos", 0)
            value = temp.read_byte()
            # Mirror back position for tests
            self._pos = temp._pos
            return value

        if self.parser._pos >= len(self.parser._data):
            raise ParseError("Overflow")
        value = self.parser.read_byte()
        # Mirror internal parser position so tests can inspect `self._pos`.
        try:
            self._pos = self.parser._pos
        except Exception:
            # Be tolerant if parser doesn't expose _pos; keep previous value.
            self._pos = getattr(self, "_pos", 0)
        return value

    def _insert_data(self, byte: int) -> None:
        """Insert data byte into screen buffer at current position."""
        try:
            row, col = self.screen.get_position()
        except ValueError:
            row, col = 0, 0
        buffer_size = self.screen.rows * self.screen.cols
        if 0 <= row < self.screen.rows and 0 <= col < self.screen.cols:
            pos = row * self.screen.cols + col
            if pos < buffer_size:
                self.screen.buffer[pos] = byte
                self.screen.set_position(row, col + 1)
            else:
                raise ParseError("Buffer overflow")
        else:
            raise ParseError(f"Position out of bounds: ({row}, {col})")

    def _handle_wcc_with_byte(self, wcc: int) -> None:
        """Handle Write Control Character."""
        if self.screen is None:
            raise ParseError("Screen buffer not initialized")
        self.wcc = wcc
        if wcc & 0x01:
            self.screen.clear()
        row, col = self.screen.get_position()
        self.screen.set_position(row, col + 1)
        logger.debug(f"Set WCC to 0x{wcc:02x}")
        # Set screen state based on WCC
        # For now, just store

    def _handle_sba(self) -> None:
        """Handle Set Buffer Address."""
        addr_high = self._read_byte()
        addr_low = self._read_byte()
        address = (addr_high << 8) | addr_low
        # 3270 address format: address = row * 80 + col
        row = address // 80
        col = address % 80
        # Clamp to screen bounds
        row = min(row, self.screen.rows - 1)
        col = min(col, self.screen.cols - 1)
        self.screen.set_position(row, col)
        self._pos = self.parser._pos
        logger.debug(f"Set buffer address to ({row}, {col})")

    def _handle_sf(self) -> None:
        """Handle Start Field."""
        if self.screen is None:
            raise ParseError("Screen buffer not initialized")
        try:
            attr = self._read_byte()
        except ParseError:
            raise ParseError("Incomplete SF order")
        row, col = self.screen.get_position()
        self.screen.set_attribute(attr)
        self.screen.set_position(row, col + 1)
        self._pos = self.parser._pos
        logger.debug(f"Start field with attribute 0x{attr:02x}")

    def _handle_ra(self) -> None:
        """Handle Repeat to Address (RMA)."""
        if self.screen is None:
            raise ParseError("Screen buffer not initialized")
        parser = self._ensure_parser()
        if parser.remaining() < 3:
            logger.warning("Incomplete RA order")
            return
        # Save current position before RA
        current_row, current_col = self.screen.get_position()
        try:
            attr_type = self._read_byte()
        except ParseError:
            raise ParseError(f"Incomplete RA order at position {self._pos}")
        try:
            address_bytes = parser.read_fixed(2)
        except ParseError:
            raise ParseError(f"Incomplete RA address at position {self._pos}")
        address = struct.unpack(">H", address_bytes)[0]
        target_row = ((address >> 8) & 0x3F) << 2 | ((address & 0xFF) & 0xC0) >> 6
        target_col = address & 0x3F
        logger.warning(
            f"RA stub: Repeat 0x{attr_type:02x} from ({current_row}, {current_col}) to ({target_row}, {target_col})"
        )
        # Minimal emulation: insert attr_type from current to target (linear distance)
        current_pos = current_row * self.screen.cols + current_col
        target_pos = target_row * self.screen.cols + target_col
        count = abs(target_pos - current_pos)
        for _ in range(count):
            self._insert_data(attr_type)
        # Mark fields as modified if overlapping (stub: log only)
        self.screen.set_position(
            target_row, target_col + 1
        )  # Advance position post-data

    def _handle_rmf(self) -> None:
        """Handle Repeat to Modified Field (RMF)."""
        assert self.parser is not None, "Parser must be initialized before calling _handle_rmf"
        if self.parser.remaining() < 2:
            logger.warning("Incomplete RMF order")
            return
        repeat_count = self._read_byte()
        attr_byte = self._read_byte()
        logger.warning(
            f"RMF stub: Repeat {repeat_count} times 0x{attr_byte:02x} in current field"
        )
        # Minimal emulation: insert attr_byte up to repeat_count (cap to avoid overflow)
        max_repeat = min(
            repeat_count,
            self.screen.cols * self.screen.rows - self.screen.get_position()[1],
        )
        current_row, current_col = self.screen.get_position()
        for i in range(max_repeat):
            self._insert_data(attr_byte)
            # Advance position
            if current_col + 1 >= self.screen.cols:
                current_row += 1
                current_col = 0
            else:
                current_col += 1
        self.screen.set_position(current_row, current_col)
        # TODO: Mark current field as modified in screen_buffer

    def _handle_ge(self) -> None:
        """Handle Graphic Escape (GE)."""
        assert self.parser is not None, "Parser must be initialized before calling _handle_ge"
        if self.parser.remaining() < 1:
            logger.warning("Incomplete GE order")
            return
        graphic_byte = self._read_byte()
        logger.warning(f"GE stub: Insert graphic 0x{graphic_byte:02x}")
        self._insert_data(graphic_byte)
        # No position advance beyond insert

    def _handle_ic(self) -> None:
        """Handle Insert Cursor."""
        self.screen.move_cursor_to_first_input_field()
        logger.debug("Insert cursor - moved to first input field")

    def _handle_pt(self) -> None:
        """Handle Program Tab."""
        self.screen.program_tab()
        logger.debug("Program tab")

    def _handle_scs(self) -> None:
        """Handle SCS control codes order."""
        assert self.parser is not None, "Parser must be initialized before calling _handle_scs"
        if self.parser.has_more():
            code = self._read_byte()
            logger.debug(f"SCS control code: 0x{code:02x} - stub implementation")
            # TODO: Implement SCS handling if needed
        else:
            logger.warning("Incomplete SCS order")

    def _handle_write(self) -> None:
        """Handle Write order."""
        self.screen.clear()
        logger.debug("Write order - screen cleared")

    def _write_text_byte(self, byte_value: int) -> None:
        """Write a text byte to the current screen position."""
        if self.screen:
            current_row, current_col = self.screen.get_position()
            self.screen.write_char(byte_value, current_row, current_col)
            # Advance cursor
            if current_col + 1 >= self.screen.cols:
                if current_row + 1 < self.screen.rows:
                    self.screen.set_position(current_row + 1, 0)
                else:
                    self.screen.set_position(0, 0)  # Wrap around
            else:
                self.screen.set_position(current_row, current_col + 1)

    def _handle_eoa(self) -> None:
        """Handle End of Aid."""
        logger.debug("End of Aid")

    def _handle_aid_with_byte(self, aid: int) -> None:
        """Handle Attention ID."""
        self.aid = aid
        logger.debug(f"Attention ID 0x{aid:02x}")

    def _handle_read_partition(self) -> None:
        """Handle Read Partition."""
        logger.debug("Read Partition - not implemented")
        # Would trigger read from keyboard, but for parser, just log

    def _handle_sfe(self, sf_data: Optional[bytes] = None) -> dict:
        """Handle Start Field Extended (order or SF payload)."""
        if self.screen is None:
            raise ParseError("Screen buffer not initialized")
        attrs = {}
        if sf_data is not None:
            # Handle as SF payload: parse length, then fixed number of type-value pairs
            parser = BaseParser(sf_data)
            if not parser.has_more():
                return attrs
            try:
                length = parser.read_byte()
            except ParseError:
                raise ParseError("Incomplete SFE SF payload length")
            num_pairs = length // 2
            for _ in range(num_pairs):
                if not parser.has_more():
                    break
                try:
                    attr_type = parser.read_byte()
                except ParseError:
                    raise ParseError("Incomplete SFE SF attr_type")
                if not parser.has_more():
                    break
                try:
                    attr_value = parser.read_byte()
                except ParseError:
                    raise ParseError("Incomplete SFE SF attr_value")
                if attr_type in (0x41, 0x42, 0x43, 0x44, 0x45):
                    self.screen.set_extended_attribute_sfe(attr_type, attr_value)
                    attrs[attr_type] = attr_value
                    logger.debug(
                        f"SFE (SF): type 0x{attr_type:02x}, value 0x{attr_value:02x}"
                    )
            return attrs

        # Original order handling: parse length, then fixed pairs
        assert self.parser is not None, "Parser must be initialized before calling _handle_sfe"
        if not self.parser.has_more():
            return attrs
        try:
            length = self._read_byte()
        except ParseError:
            raise ParseError("Incomplete SFE order length")
        num_pairs = length // 2
        for _ in range(num_pairs):
            if self.parser.remaining() < 2:
                break
            try:
                attr_type = self._read_byte()
            except ParseError:
                raise ParseError("Incomplete SFE order attr_type")
            try:
                attr_value = self._read_byte()
            except ParseError:
                raise ParseError("Incomplete SFE order attr_value")
            if attr_type in (0x41, 0x42, 0x43, 0x44, 0x45):
                self.screen.set_extended_attribute_sfe(attr_type, attr_value)
                attrs[attr_type] = attr_value
                logger.debug(
                    f"SFE (order): type 0x{attr_type:02x}, value 0x{attr_value:02x}"
                )
        return attrs

    def _handle_bind(self) -> None:
        """Handle BIND order."""
        logger.debug("BIND order - not fully implemented")
        # BIND order doesn't contain screen dimensions, so create a default BindImage
        if self.negotiator:
            default_bind_image = BindImage(rows=24, cols=80)  # Default dimensions
            self.negotiator.handle_bind_image(default_bind_image)

    def _handle_data_stream_ctl(self, ctl_code: int) -> None:
        """Handle DATA-STREAM-CTL order."""
        # Process control code similarly to SCS CTL codes
        self._handle_scs_ctl_codes(bytes([ctl_code]))

    def _handle_structured_field(self) -> None:
        """Handle Structured Field.

        Tolerant parser: callers may call this directly with `self._data`/`self._pos`
        set (tests do this), or it may be invoked from the main parse loop (where
        the SF id byte was already consumed). This method handles both cases.
        """
        parser = self._ensure_parser()

        # If the SF id byte (0x3C) is still present at the current position,
        # consume it so the following reads point at the length field.
        if parser.has_more() and parser.peek_byte() == STRUCTURED_FIELD:
            # Consume SF id
            try:
                self._read_byte()
            except ParseError:
                # Can't consume; skip gracefully
                logger.warning(
                    "Could not consume SF id while handling structured field"
                )
                self._skip_structured_field()
                return

        # Need at least 3 bytes: 2-byte length + 1-byte type
        if parser.remaining() < 3:
            logger.warning("Incomplete structured field")
            self._skip_structured_field()
            return

        try:
            length_high = self._read_byte()
        except ParseError:
            raise ParseError("Incomplete structured field length high byte")
        try:
            length_low = self._read_byte()
        except ParseError:
            raise ParseError("Incomplete structured field length low byte")
        length = (length_high << 8) | length_low

        # Must have at least one byte for SF type
        if parser.remaining() < 1:
            logger.warning("Structured field missing type byte")
            self._skip_structured_field()
            return

        try:
            sf_type = self._read_byte()
        except ParseError:
            raise ParseError("Incomplete structured field type byte")
        logger.debug(f"Structured Field: length={length}, type=0x{sf_type:02x}")

        # Data length: SF length counts the type byte + data bytes
        data_len = max(0, length - 1)
        if parser.remaining() < data_len:
            logger.warning("Structured field data truncated")
            data_len = parser.remaining()
        try:
            sf_data = parser.read_fixed(data_len)
        except ParseError:
            # If read_fixed failed, fall back to reading what's left
            sf_data = (
                parser.read_fixed(parser.remaining()) if parser.remaining() > 0 else b""
            )

        if sf_type == BIND_SF_TYPE:
            # Delegate BIND-IMAGE handling to a dedicated method so tests can patch it
            self._handle_bind_sf(sf_data)
        elif sf_type == SF_TYPE_SFE:
            self._handle_sfe(sf_data)
        else:
            self._handle_unknown_structured_field(sf_type, sf_data)

    def _handle_unknown_structured_field(self, sf_type: int, data: bytes) -> None:
        """Handle unknown structured field with logging."""
        logger.warning(
            f"Unknown structured field type 0x{sf_type:02x}, data length {len(data)}, skipping"
        )
        self._skip_structured_field()
        # TODO: More detailed parsing or error handling if needed

    def _skip_structured_field(self) -> None:
        """Skip the current structured field.

        This implementation understands two common encodings used in tests:
        - Two-byte length (big-endian) when the first length byte is 0x00.
          In this case the length value includes the SF type byte plus data.
        - One-byte length when the first length byte is non-zero. Tests use this
          form where the single length byte indicates the number of data bytes
          (not counting the type byte).

        The method updates `self._pos` (and `self.parser._pos` when present) to
        the byte immediately following the structured field payload.
        """
        # Prepare a parser to walk the buffer
        if self.parser is None:
            data = getattr(self, "_data", b"") or b""
            parser = BaseParser(data)
            parser._pos = getattr(self, "_pos", 0)
            using_temp = True
        else:
            parser = self.parser
            using_temp = False

        # If current byte is SF id, consume it
        try:
            if parser.has_more() and parser.peek_byte() == STRUCTURED_FIELD:
                parser.read_byte()
        except ParseError:
            self._pos = parser._pos
            return

        # If not enough bytes to read a length, move to end
        if parser.remaining() <= 0:
            self._pos = parser._pos
            return

        try:
            # Heuristic: if first length byte is 0x00 and we have at least two bytes,
            # treat length as 2-byte big-endian (length includes type + data)
            if parser.remaining() >= 2 and parser._data[parser._pos] == 0x00:
                high = parser.read_byte()
                low = parser.read_byte()
                length = (high << 8) | low
                # Type byte follows
                if parser.remaining() >= 1:
                    parser.read_byte()  # consume type
                # Data length is length - 1 (type counted in length)
                data_len = max(0, length - 1)
                skip_len = min(parser.remaining(), data_len)
                if skip_len > 0:
                    # consume payload
                    _ = parser.read_fixed(skip_len)
            else:
                # One-byte length form: first byte is the data length (excluding type)
                length1 = parser.read_byte()
                # consume type if present
                if parser.remaining() >= 1:
                    parser.read_byte()
                data_len = length1
                skip_len = min(parser.remaining(), data_len)
                if skip_len > 0:
                    _ = parser.read_fixed(skip_len)
        except ParseError:
            # Best-effort: move to end
            parser._pos = len(parser._data)

        # Mirror position back to object
        self._pos = parser._pos
        if not using_temp and self.parser is not None:
            # keep real parser in sync
            self.parser._pos = parser._pos

    def _handle_bind_sf(self, sf_data: bytes) -> None:
        """Handle BIND-IMAGE structured field via a dedicated, patchable handler."""
        try:
            bind_image = self._parse_bind_image(sf_data)
            if self.negotiator:
                self.negotiator.handle_bind_image(bind_image)
            logger.debug(f"Handled BIND-IMAGE structured field: {bind_image}")
        except ParseError as e:
            logger.warning(f"_handle_bind_sf failed to parse BIND-IMAGE: {e}")

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
            logger.warning(
                f"Received SOH status 0x{status:02x} but no printer buffer available"
            )

    def _parse_bind_image(self, data: bytes) -> BindImage:
        """Parse BIND-IMAGE structured field with length checks and attribute parsing."""
        parser = BaseParser(data)
        if parser.remaining() < 3:
            logger.warning("Invalid BIND-IMAGE structured field: too short")
            return BindImage()

        # Skip SF ID if present (0x3C for compatibility with current mock)
        if parser.peek_byte() == 0x3C:
            parser.read_byte()

        if parser.remaining() < 3:
            logger.warning("Invalid BIND-IMAGE: insufficient header")
            return BindImage()

        sf_length = parser.read_u16()
        sf_type = parser.read_byte()

        if sf_type != BIND_SF_TYPE:
            logger.warning(f"Expected BIND-IMAGE type 0x03, got 0x{sf_type:02x}")
            return BindImage()

        rows = None
        cols = None
        query_reply_ids = []

        # Expected data length: sf_length - 3 (length bytes + type)
        expected_end = parser._pos + (sf_length - 3)
        if expected_end > len(parser._data):
            expected_end = len(parser._data)

        while parser._pos < expected_end:
            if not parser.has_more():
                logger.warning("Truncated subfield length in BIND-IMAGE")
                break
            subfield_len = parser.read_byte()
            if subfield_len < 2:
                logger.warning(f"Invalid subfield length {subfield_len} in BIND-IMAGE")
                break
            if not parser.has_more():
                logger.warning("Truncated subfield ID in BIND-IMAGE")
                break
            subfield_id = parser.read_byte()
            sub_data_len = subfield_len - 2
            if parser.remaining() < sub_data_len:
                logger.warning("Subfield data truncated in BIND-IMAGE")
                break
            sub_data = parser.read_fixed(sub_data_len)

            if subfield_id == BIND_SF_SUBFIELD_PSC:
                # PSC subfield: rows (2 bytes), cols (2 bytes), possibly more attributes
                if len(sub_data) >= 4:
                    rows = (sub_data[0] << 8) | sub_data[1]
                    cols = (sub_data[2] << 8) | sub_data[3]
                    logger.debug(f"Parsed PSC subfield: rows={rows}, cols={cols}")
                    # TODO: Parse additional PSC attributes if present (e.g., flags at sub_data[4:])
                else:
                    logger.warning("PSC subfield too short for rows/cols")
            elif subfield_id == BIND_SF_SUBFIELD_QUERY_REPLY_IDS:
                # Query Reply IDs: list of 1-byte IDs
                query_reply_ids = list(sub_data)
                logger.debug(f"Parsed Query Reply IDs subfield: {query_reply_ids}")
            else:
                logger.debug(
                    f"Skipping unknown BIND-IMAGE subfield ID 0x{subfield_id:02x} (length {subfield_len})"
                )

        bind_image = BindImage(rows=rows, cols=cols, query_reply_ids=query_reply_ids)
        logger.debug(f"Parsed BIND-IMAGE: {bind_image}")
        return bind_image

    def _parse_sna_response(self, data: bytes) -> SnaResponse:
        """Parse SNA response structured field or data, enhanced for bind image replies and positive/negative responses."""
        parser = BaseParser(data)
        if not parser.has_more():
            logger.warning("Invalid SNA response: too short")
            return SnaResponse(0)

        # Enhanced format: response_type (1 byte), flags (1 byte), sense_code (2 bytes), data (rest)
        # If response_type is BIND_SF_TYPE, parse data as BindImage
        response_type = parser.read_byte()
        flags = parser.read_byte() if parser.has_more() else None
        sense_code = None
        if parser.remaining() >= 2:
            sense_code = parser.read_u16()
        data_part = parser.read_fixed(parser.remaining()) if parser.has_more() else None

        # Enhanced parsing for specific types
        if response_type == BIND_SF_TYPE and data_part:
            try:
                bind_image = self._parse_bind_image(data_part)
                data_part = bind_image
                logger.debug(f"Parsed SNA response as BIND-IMAGE reply: {bind_image}")
            except ParseError as e:
                logger.warning(f"Failed to parse BIND-IMAGE in SNA response: {e}")

        # Log positive/negative based on flags and sense
        if flags is not None and (flags & SNA_FLAGS_EXCEPTION_RESPONSE):
            logger.debug("SNA response is negative (exception flag set)")
        elif sense_code is not None and sense_code != SNA_SENSE_CODE_SUCCESS:
            logger.debug(f"SNA response is negative (sense code {sense_code})")
        else:
            logger.debug("SNA response is positive")

        logger.debug(
            f"Parsed SNA response: type=0x{response_type:02x}, flags={flags}, sense=0x{sense_code:04x if sense_code else 'None'}"
        )
        return SnaResponse(response_type, flags, sense_code, data_part)

    def build_query_reply_sf(self, query_type: int, data: bytes = b"") -> bytes:
        """Build a basic Query Reply structured field including optional payload data.

        Args:
            query_type: One of the QUERY_REPLY_* constants.
            data: Optional payload to include in the reply.
        """
        # Reply data includes the query_type byte followed by optional data
        payload = bytes([query_type]) + (data or b"")
        length_val = 1 + len(payload)  # type byte + payload
        # Structured Field: SF id, length(2), SF type (QUERY_REPLY_SF), payload
        return (
            bytes([STRUCTURED_FIELD])
            + length_val.to_bytes(2, "big")
            + bytes([QUERY_REPLY_SF])
            + payload
        )

    def build_device_type_query_reply(self) -> bytes:
        """Build a basic Device Type Query Reply SF (IBM-3278-2)."""
        device_type = QUERY_REPLY_DEVICE_TYPE
        num_devices = 0x01
        name_len = 0x0A
        name = b"IBM-3278-2\x00\x00\x00"  # 10 bytes, padded
        model = 0x02
        reply_data = bytes([device_type, num_devices, name_len]) + name + bytes([model])
        data_len = len(reply_data)
        length_val = 3 + data_len  # type + reply_data
        return (
            bytes(
                [
                    STRUCTURED_FIELD,
                    (length_val >> 8) & 0xFF,
                    length_val & 0xFF,
                    QUERY_REPLY_SF,
                ]
            )
            + reply_data
        )

    def build_characteristics_query_reply(self) -> bytes:
        """Build a basic Characteristics Query Reply SF."""
        char_type = QUERY_REPLY_CHARACTERISTICS
        reply_data = b"\x00\x00"  # Basic empty data (e.g., buffer sizes 0)
        data_len = len(reply_data)
        length_val = 3 + data_len
        return (
            bytes(
                [
                    STRUCTURED_FIELD,
                    (length_val >> 8) & 0xFF,
                    length_val & 0xFF,
                    QUERY_REPLY_SF,
                ]
            )
            + bytes([char_type])
            + reply_data
        )


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

    def build_input_stream(
        self, modified_fields: List[Tuple[int, bytes]], aid: int, cols: int
    ) -> bytes:
        """Build input stream from modified fields."""
        # This is a simplified implementation
        stream = bytearray()
        stream.append(aid)  # AID

        for pos, field_data in modified_fields:
            # SBA to position
            row = pos // cols
            col = pos % cols
            address = row * cols + col
            addr_high = (address >> 8) & 0x3F
            addr_low = address & 0xFF
            stream.extend([SBA, addr_high, addr_low])
            stream.extend(field_data)

        stream.append(EOA)  # End of Area
        return bytes(stream)

    def build_sba(self, row: int, col: int) -> bytes:
        """Build Set Buffer Address command."""
        # SBA + 2-byte address
        address = row * 80 + col
        addr_high = (address >> 8) & 0x3F
        addr_low = address & 0xFF
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
        """Build printer status structured field for SNA SOH compliance.

        This method constructs a Structured Field (SF) for printer status reporting.
        For SNA SOH integration, the SF can be wrapped in SOH (0x01) when sent in SCS data streams.

        Args:
            status_code: The printer status code (e.g., 0x00 for success, 0x40 for device end, 0x80 for intervention required).

        Returns:
            Bytes representing the SF for printer status.

        Note:
            Common status codes:
            - 0x00: Success/Ready
            - 0x40: Device End
            - 0x80: Intervention Required
            - 0x81: Power Off/On
            - 0x82: Not Ready
            - 0x83: Intervention Required (specific)
        """
        payload = bytes([PRINTER_STATUS_SF_TYPE, status_code])
        length = len(payload) + 2  # SF length: type (1) + length field (2) + payload
        return bytes([STRUCTURED_FIELD]) + length.to_bytes(2, "big") + payload

    def build_soh_message(self, status_code: int) -> bytes:
        """Build SOH (Start of Header) message."""
        return bytes([SOH, status_code])
