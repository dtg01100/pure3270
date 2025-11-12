# TN3270E Subnegotiation Command: IS (RFC 1646/2355)
TN3270E_IS = 0x04
# TN3270E Subnegotiation Command: SEND (RFC 1646/2355)
TN3270E_SEND = 0x08
# TN3270E Subnegotiation Type: DEVICE-TYPE (RFC 1646/2355)
TN3270E_DEVICE_TYPE = 0x02
# TN3270E Subnegotiation Type: FUNCTIONS (RFC 1646/2355)
TN3270E_FUNCTIONS = 0x03
# TN3270E Subnegotiation Type: REQUEST (RFC 1646/2355)
TN3270E_REQUEST = 0x07
# TN3270E Subnegotiation Type: QUERY (RFC 1646/2355)
TN3270E_QUERY = 0x0F
"""Utility functions for TN3270/TN3270E protocol handling.

Typing notes:
- Writer parameters are annotated as `Optional[asyncio.StreamWriter]` to reflect possibility of absent writer during teardown.
- `_schedule_if_awaitable` centralizes best-effort handling of AsyncMock.write returning an awaitable to avoid repeated inline inspection logic.
"""

import asyncio
import inspect
import logging
import struct
from typing import Any, Dict, List, Optional, Tuple, cast

logger = logging.getLogger(__name__)

# Telnet constants
IAC = 0xFF
SB = 0xFA
SE = 0xF0
WILL = 0xFB
WONT = 0xFC
DO = 0xFD
DONT = 0xFE
# Additional IAC commands per RFC 854
GA = 0xF9  # Go Ahead
EL = 0xF8  # Erase Line
EC = 0xF7  # Erase Character
AYT = 0xF6  # Are You There
AO = 0xF5  # Abort Output
IP = 0xF4  # Interrupt Process
BRK = 0xF3  # Break
DM = 0xF2  # Data Mark
NOP = 0xF1  # No Operation
# Legacy aliases
BREAK = 0xF3
# Telnet Options
TELOPT_BINARY = 0x00
TELOPT_ECHO = 0x01
TELOPT_RCP = 0x02
TELOPT_SGA = 0x03
TELOPT_NAMS = 0x04
TELOPT_STATUS = 0x05
TELOPT_TM = 0x06
TELOPT_RCTE = 0x07
TELOPT_NAOL = 0x08
TELOPT_NAOP = 0x09
TELOPT_NAOCRD = 0x0A
TELOPT_NAOHTS = 0x0B
TELOPT_NAOHTD = 0x0C
TELOPT_NAOFFD = 0x0D
TELOPT_NAOVTS = 0x0E
TELOPT_NAOVTD = 0x0F
TELOPT_NAOLFD = 0x10
TELOPT_XASCII = 0x11
TELOPT_LOGOUT = 0x12
TELOPT_BM = 0x13
TELOPT_DET = 0x14
TELOPT_SUPDUP = 0x15
TELOPT_SUPDUPOUTPUT = 0x16
TELOPT_SNDLOC = 0x17
TELOPT_TTYPE = 0x18  # Terminal Type
TTYPE_IS = 0x00  # IS command - send terminal type
TTYPE_SEND = 0x01  # SEND command - request terminal type
TELOPT_EOR = 0x19  # End of Record
TELOPT_TUID = 0x1A
TELOPT_OUTMRK = 0x1B
TELOPT_TTYLOC = 0x1C
TELOPT_3270REGIME = 0x1D
TELOPT_X3PAD = 0x1E
TELOPT_NAWS = 0x1F
TELOPT_TSPEED = 0x20
TELOPT_LFLOW = 0x21
TELOPT_LINEMODE = 0x22
TELOPT_XDISPLOC = 0x23
TELOPT_OLD_ENVIRON = 0x24
TELOPT_AUTHENTICATION = 0x25
TELOPT_ENCRYPT = 0x26
TELOPT_NEW_ENVIRON = 0x27

# NEW_ENVIRON option constants (RFC 1572)
NEW_ENV_IS = 0x00  # IS command - send environment info
NEW_ENV_SEND = 0x01  # SEND command - request environment info
NEW_ENV_INFO = 0x02  # INFO command - provide environment info
NEW_ENV_VAR = 0x00  # VAR - well-known environment variable
NEW_ENV_VALUE = 0x01  # VALUE - variable value
NEW_ENV_ESC = 0x02  # ESC - escape next byte
NEW_ENV_USERVAR = 0x03  # USERVAR - user-defined variable

# TN3270E Telnet option value per RFC 1647 (option 40 decimal = 0x28 hex)
TELOPT_TN3270E = 0x28  # RFC 1647 standard value

TELOPT_XAUTH = 0x29
TELOPT_CHARSET = 0x2A
TELOPT_RSP = 0x2B
TELOPT_COM_PORT_OPTION = 0x2C
TELOPT_SLE = 0x2D
TELOPT_START_TLS = 0x2E
TELOPT_KERBEROS_5 = 0x2F
TELOPT_BIND_UNIT = 0x30
TELOPT_OPAQUE_STRUCTURE = 0x31
TELOPT_PRAGMA_LOGON = 0x32
TELOPT_SSPI_LOGON = 0x33
TELOPT_PRAGMA_HEARTBEAT = 0x34
TELOPT_TERMINAL_LOCATION = 0x24  # RFC 1646, Option 36 decimal = 0x24 hex
TELOPT_EXOPL = 0xFF  # Extended-Options-List

# TN3270E constants
TN3270E = 0x28  # TN3270E Telnet option (duplicate, but kept for clarity)
EOR = 0x19  # End of Record (duplicate, but kept for clarity)

# TN3270E Data Types (RFC 1646 Section 5.1)
TN3270_DATA = 0x00  # 3270-DATA
SCS_DATA = 0x01  # SCS-DATA
RESPONSE = 0x02  # RESPONSE
BIND_IMAGE = 0x03  # BIND-IMAGE
UNBIND = 0x04  # UNBIND
NVT_DATA = 0x05  # NVT-DATA
REQUEST = 0x06  # REQUEST
SSCP_LU_DATA = 0x07  # SSCP-LU-DATA
PRINT_EOJ = 0x08  # PRINT-EOJ
SNA_RESPONSE = 0x09  # New SNA Response Data Type
SNA_RESPONSE_DATA_TYPE = 0x09  # SNA Response Data Type
PRINTER_STATUS_DATA_TYPE = 0x0A  # New data type for Printer Status (TN3270E)

# TN3270E Data Types tuple for validation
TN3270E_DATA_TYPES = (
    TN3270_DATA,
    SCS_DATA,
    RESPONSE,
    BIND_IMAGE,
    UNBIND,
    NVT_DATA,
    REQUEST,
    SSCP_LU_DATA,
    PRINT_EOJ,
    SNA_RESPONSE,
    PRINTER_STATUS_DATA_TYPE,
)

# TN3270E Subnegotiation Message Types
# TN3270E Function Types (bit flags)
# Per RFC 2355, BIND-IMAGE uses bit 0x01 (TN3270E_DATA_STREAM_CTL)
TN3270E_DATA_STREAM_CTL = 0x01
TN3270E_NEW_APPL = 0x02
TN3270E_RESPONSES = 0x03
TN3270E_SCS_CTL_CODES = 0x04
TN3270E_SYSREQ_ATTN = 0x05
# Per tests and common implementations, BIND-IMAGE uses bit 0x01
TN3270E_BIND_IMAGE = 0x01

# TN3270E Sysreq Key Constants
TN3270E_SYSREQ_ATTN = 0x6C  # ATTN key
TN3270E_SYSREQ_BREAK = 0xF3  # Break key
TN3270E_SYSREQ_CANCEL = 0x6D  # Cancel key
TN3270E_SYSREQ_LOGOFF = 0x7B  # Logoff key
TN3270E_SYSREQ_MESSAGE_TYPE = 0x1C  # Message type for sysreq
TN3270E_SYSREQ_PRINT = 0x7C  # Print key
TN3270E_SYSREQ_RESTART = 0x7D  # Restart key

# Additional sense codes for SNA responses
SNA_SENSE_CODE_SUCCESS = 0x0000
SNA_SENSE_CODE_SESSION_FAILURE = 0x082A
SNA_SENSE_CODE_INVALID_FORMAT = 0x1001  # Invalid message format
SNA_SENSE_CODE_NOT_SUPPORTED = 0x1002  # Function not supported
SNA_SENSE_CODE_INVALID_REQUEST = 0x0801  # Invalid Request
SNA_SENSE_CODE_LU_BUSY = 0x080A  # LU Busy
SNA_SENSE_CODE_INVALID_SEQUENCE = 0x1008  # Invalid Sequence
SNA_SENSE_CODE_NO_RESOURCES = 0x080F  # No Resources
SNA_SENSE_CODE_STATE_ERROR = 0x1003  # State Error

# Additional TN3270E Sysreq constants
TN3270E_SYSREQ = 0x05  # System request key (general)
TN3270E_SYSREQ_BREAK = 0x06
TN3270E_SYSREQ_ATTN = 0x05
TN3270E_SYSREQ_CLEAR = 0x07
TN3270E_SYSREQ_TEST = 0x08

# TN3270E Response Flags
TN3270E_RSF_ALWAYS_RESPONSE = 0x02
TN3270E_RSF_ERROR_RESPONSE = 0x01
TN3270E_RSF_NEGATIVE_RESPONSE = 0xFF
TN3270E_RSF_NO_RESPONSE = 0x00
TN3270E_RSF_POSITIVE_RESPONSE = 0x00
TN3270E_RSF_REQUEST = 0x01

# TN3270E Request Flags (RFC 2355 Section 10.4.1)
TN3270E_REQ_ERR_COND_CLEARED = 0x01  # Error condition cleared

# TN3270E Response Mode Constants
TN3270E_RESPONSE_MODE = 0x15  # Response mode subnegotiation option
TN3270E_RESPONSE_MODE_IS = 0x00
TN3270E_RESPONSE_MODE_SEND = 0x01
TN3270E_RESPONSE_MODE_BIND_IMAGE = 0x02

# TN3270E Usable Area Constants
TN3270E_USABLE_AREA = 0x16  # Usable area subnegotiation option
TN3270E_USABLE_AREA_IS = 0x00
TN3270E_USABLE_AREA_SEND = 0x01

# TN3270E Query Constants
TN3270E_QUERY_IS = 0x00
TN3270E_QUERY_SEND = 0x01

# 3270 Data Stream Types and Constants
# NOTE: These are internal data stream type identifiers, NOT TN3270E header types
# TN3270E header types are defined above (lines 126-139) per RFC 2355
# Removed duplicate/conflicting definitions to avoid shadowing RFC values:
# - Use TN3270_DATA (0x00), SCS_DATA (0x01), etc. from RFC section
# - Only unique internal types remain here:
SNA_RESPONSE_DATA_TYPE = 0x02  # Internal: SNA response in data stream
# Note: BIND_IMAGE (0xF2) is an AID code, not a data type - keeping for compatibility

# Structured Field Query Reply Types (all standard IDs)
QUERY_REPLY_SUMMARY = 0x80
QUERY_REPLY_CHARACTERISTICS = 0x81
QUERY_REPLY_PRODUCT_DEFINED_DATA = 0x82
QUERY_REPLY_COLOR = 0x85
QUERY_REPLY_EXTENDED_ATTRIBUTES = 0x86
QUERY_REPLY_LINE_TYPE = 0x87
QUERY_REPLY_CHARACTER_SET = 0x88
QUERY_REPLY_REPLY_MODES = 0x8B
QUERY_REPLY_PORTABLE_CHARACTER_SET = 0x8C
QUERY_REPLY_USABLE_AREA = 0x8D
QUERY_REPLY_DBCS_ASIA = 0x8E
QUERY_REPLY_DBCS_EUROPE = 0x8F
QUERY_REPLY_DBCS_MIDDLE_EAST = 0x90
QUERY_REPLY_IMPLICIT_PARTITION = 0x91
QUERY_REPLY_DDM = 0x92
QUERY_REPLY_DEVICE_TYPE = 0x84
QUERY_REPLY_FIELD_OUTLINING = 0x8A
QUERY_REPLY_GRAPHICS = 0x89
QUERY_REPLY_GRID = 0x8E  # Example
QUERY_REPLY_HIGHLIGHTING = 0x8A  # Example
QUERY_REPLY_OEM_AUXILIARY_DEVICE = 0x8F  # Example
QUERY_REPLY_PROCEDURE = 0x90  # Example
QUERY_REPLY_RPQ_NAMES = 0x91  # Example
QUERY_REPLY_SEGMENT = 0x92  # Example
QUERY_REPLY_SF = 0x93  # Example
QUERY_REPLY_TRANSPARENCY = 0x94  # Example
QUERY_REPLY_FORMAT_STORAGE = 0x95  # Example

# TN3270E Device Type Names
TN3270E_IBM_3278_2 = "IBM-3278-2"
TN3270E_IBM_3278_3 = "IBM-3278-3"
TN3270E_IBM_3278_4 = "IBM-3278-4"
TN3270E_IBM_3278_4_E = "IBM-3278-4-E"
TN3270E_IBM_3278_5 = "IBM-3278-5"
TN3270E_IBM_3279_2 = "IBM-3279-2"
TN3270E_IBM_3279_3 = "IBM-3279-3"
TN3270E_IBM_3279_4 = "IBM-3279-4"
TN3270E_IBM_3279_5 = "IBM-3279-5"
TN3270E_IBM_3179_2 = "IBM-3179-2"
TN3270E_IBM_3483_VI = "IBM-3483-VI"
TN3270E_IBM_3196_A1 = "IBM-3196-A1"
# Additional TN3270E Device Type Names
TN3270E_IBM_DYNAMIC = "IBM-DYNAMIC"
TN3270E_IBM_3270PC_G = "IBM-3270PC-G"
TN3270E_IBM_3270PC_GA = "IBM-3270PC-GA"
TN3270E_IBM_3270PC_GX = "IBM-3270PC-GX"


# Terminal Model Configuration System
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class TerminalCapabilities:
    """Defines the capabilities and characteristics of a 3270 terminal model.

    Based on IBM 3270 Data Stream Programmer's Reference and GA23-0059 documentation.
    """

    screen_size: Tuple[int, int]  # (rows, cols)
    color_support: bool
    extended_attributes: bool
    programmed_symbols: bool
    extended_highlighting: bool
    light_pen_support: bool
    magnetic_slot_reader: bool
    operator_information_area: bool
    max_alternate_screen_size: Optional[Tuple[int, int]] = None
    character_sets: Optional[List[str]] = field(default=None)

    def __post_init__(self) -> None:
        if self.character_sets is None:
            # Default character set support
            self.character_sets = ["EBCDIC", "ASCII"]


# Comprehensive Terminal Model Registry
# Based on IBM 3270 Information Display System specifications
TERMINAL_MODELS: Dict[str, TerminalCapabilities] = {
    # 3278 Display Terminals (Monochrome)
    TN3270E_IBM_3278_2: TerminalCapabilities(
        screen_size=(24, 80),
        color_support=False,
        extended_attributes=True,
        programmed_symbols=False,
        extended_highlighting=True,
        light_pen_support=True,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(24, 80),
    ),
    TN3270E_IBM_3278_3: TerminalCapabilities(
        screen_size=(32, 80),
        color_support=False,
        extended_attributes=True,
        programmed_symbols=False,
        extended_highlighting=True,
        light_pen_support=True,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(32, 80),
    ),
    TN3270E_IBM_3278_4: TerminalCapabilities(
        screen_size=(43, 80),
        color_support=False,
        extended_attributes=True,
        programmed_symbols=False,
        extended_highlighting=True,
        light_pen_support=True,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(43, 80),
    ),
    TN3270E_IBM_3278_5: TerminalCapabilities(
        screen_size=(27, 132),
        color_support=False,
        extended_attributes=True,
        programmed_symbols=False,
        extended_highlighting=True,
        light_pen_support=True,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(27, 132),
    ),
    # 3279 Color Display Terminals
    TN3270E_IBM_3279_2: TerminalCapabilities(
        screen_size=(24, 80),
        color_support=True,
        extended_attributes=True,
        programmed_symbols=True,
        extended_highlighting=True,
        light_pen_support=True,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(24, 80),
    ),
    TN3270E_IBM_3279_3: TerminalCapabilities(
        screen_size=(32, 80),
        color_support=True,
        extended_attributes=True,
        programmed_symbols=True,
        extended_highlighting=True,
        light_pen_support=True,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(32, 80),
    ),
    TN3270E_IBM_3279_4: TerminalCapabilities(
        screen_size=(43, 80),
        color_support=True,
        extended_attributes=True,
        programmed_symbols=True,
        extended_highlighting=True,
        light_pen_support=True,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(43, 80),
    ),
    TN3270E_IBM_3279_5: TerminalCapabilities(
        screen_size=(27, 132),
        color_support=True,
        extended_attributes=True,
        programmed_symbols=True,
        extended_highlighting=True,
        light_pen_support=True,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(27, 132),
    ),
    # 3179 Workstation Terminals
    TN3270E_IBM_3179_2: TerminalCapabilities(
        screen_size=(24, 80),
        color_support=True,
        extended_attributes=True,
        programmed_symbols=True,
        extended_highlighting=True,
        light_pen_support=False,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(25, 80),  # Extra status line
    ),
    # PC-based Terminals
    TN3270E_IBM_3270PC_G: TerminalCapabilities(
        screen_size=(24, 80),
        color_support=True,
        extended_attributes=True,
        programmed_symbols=True,
        extended_highlighting=True,
        light_pen_support=False,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(43, 80),
    ),
    TN3270E_IBM_3270PC_GA: TerminalCapabilities(
        screen_size=(24, 80),
        color_support=True,
        extended_attributes=True,
        programmed_symbols=True,
        extended_highlighting=True,
        light_pen_support=False,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(43, 80),
    ),
    TN3270E_IBM_3270PC_GX: TerminalCapabilities(
        screen_size=(24, 80),
        color_support=True,
        extended_attributes=True,
        programmed_symbols=True,
        extended_highlighting=True,
        light_pen_support=False,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=(43, 80),
    ),
    # Dynamic Terminal (negotiated capabilities)
    TN3270E_IBM_DYNAMIC: TerminalCapabilities(
        screen_size=(24, 80),  # Default, negotiated later
        color_support=True,
        extended_attributes=True,
        programmed_symbols=True,
        extended_highlighting=True,
        light_pen_support=False,
        magnetic_slot_reader=False,
        operator_information_area=True,
        max_alternate_screen_size=None,  # Negotiated
    ),
}

# Default terminal model for backward compatibility
DEFAULT_TERMINAL_MODEL = TN3270E_IBM_3278_2


# Validation helpers
def get_supported_terminal_models() -> List[str]:
    """Get list of all supported terminal model names."""
    return list(TERMINAL_MODELS.keys())


def is_valid_terminal_model(model: str) -> bool:
    """Check if a terminal model is supported."""
    return model in TERMINAL_MODELS


def get_terminal_capabilities(model: str) -> Optional[TerminalCapabilities]:
    """Get capabilities for a specific terminal model."""
    return TERMINAL_MODELS.get(model)


def get_screen_size(model: str) -> Tuple[int, int]:
    """Get screen dimensions for a terminal model."""
    capabilities = get_terminal_capabilities(model)
    if capabilities:
        return capabilities.screen_size
    # Fallback to default model
    return TERMINAL_MODELS[DEFAULT_TERMINAL_MODEL].screen_size


def _schedule_if_awaitable(maybe_awaitable: Any) -> None:
    """Best-effort scheduling or execution of an awaitable.

    Avoids un-awaited coroutine warnings when mocks return coroutines.
    Intentionally swallows all exceptions; this helper is non-critical.
    """
    try:
        if inspect.isawaitable(maybe_awaitable):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(maybe_awaitable)  # type: ignore[arg-type]
            except RuntimeError:
                try:
                    asyncio.run(maybe_awaitable)  # type: ignore[arg-type]
                except Exception as e:
                    logger.error(f"Error in _call_maybe_await: {e}")
    except Exception as e:
        logger.error(f"Error in _call_maybe_await outer: {e}")


def _safe_writer_write(writer: Optional[Any], data: bytes) -> None:
    """Safely write bytes to a writer without awaiting.

    - Works with real asyncio.StreamWriter (write returns None)
    - Works with AsyncMock where write may be coroutine-like
    - Avoids mypy func-returns-value by using Any for writer
    """
    if writer is None:
        return
    try:
        write_fn = getattr(writer, "write", None)
        if write_fn is None:
            return
        if inspect.iscoroutinefunction(write_fn):
            try:
                _schedule_if_awaitable(write_fn(data))
            except Exception:
                pass
        else:
            # Cast to Any to avoid mypy complaining about return value usage
            cast(Any, write_fn)(data)
    except Exception:
        # Swallow non-critical write errors
        return


def send_iac(writer: Optional[asyncio.StreamWriter], command: bytes) -> None:
    """Send an IAC command to the writer.

    Ensures the IAC (0xFF) prefix is present exactly once. If the provided
    command already begins with IAC, it will not be duplicated.
    """
    if writer is None:
        logger.debug("[TELNET] Writer is None, skipping IAC send")
        return
    try:
        payload = (
            command
            if (len(command) > 0 and command[0] == IAC)
            else bytes([IAC]) + command
        )
        # Safe non-blocking write (handles AsyncMock or real StreamWriter)
        _safe_writer_write(writer, payload)
        # Don't await drain here to avoid blocking negotiation
        logger.debug(f"[TELNET] Sent IAC command: {payload.hex()}")
    except Exception as e:
        logger.error(f"[TELNET] Failed to send IAC command: {e}")


def send_subnegotiation(
    writer: Optional[asyncio.StreamWriter], opt: bytes, data: bytes
) -> None:
    """
    Send subnegotiation.

    Args:
        writer: StreamWriter.
        opt: Option byte.
        data: Subnegotiation data.
    """
    if not writer:
        return

    sub = bytes([IAC, SB]) + opt + data + bytes([IAC, SE])
    try:
        _safe_writer_write(writer, sub)
    except Exception:
        return


def strip_telnet_iac(
    data: bytes, handle_eor_ga: bool = False, enable_logging: bool = False
) -> bytes:
    """
    Strip Telnet IAC sequences from data.

    :param data: Raw bytes containing potential IAC sequences.
    :param handle_eor_ga: If True, specifically handle EOR (0x19) and GA (0xf9) commands.
    :param enable_logging: If True, log EOR/GA stripping.
    :return: Cleaned bytes without IAC sequences.
    """
    clean_data = b""
    i = 0
    while i < len(data):
        if data[i] == IAC:
            if i + 1 < len(data):
                cmd = data[i + 1]
                if cmd == SB:
                    # Skip subnegotiation until SE
                    j = i + 2
                    while j < len(data) and data[j] != SE:
                        j += 1
                    if j < len(data) and data[j] == SE:
                        j += 1
                    i = j
                    continue
                elif cmd in (WILL, WONT, DO, DONT):
                    i += 3
                    continue
                elif handle_eor_ga and cmd in (0x19, 0xF9):  # EOR or GA
                    if enable_logging:
                        if cmd == 0x19:
                            logger.debug("Stripping IAC EOR in fallback")
                        else:
                            logger.debug("Stripping IAC GA in fallback")
                    i += 2
                    continue
                else:
                    i += 2
                    continue
            else:
                # Incomplete IAC at end, break to avoid index error
                break
        else:
            clean_data += bytes([data[i]])
            i += 1
    return clean_data


from .parser import BaseParser, ParseError


class BaseStringParser:
    def __init__(self, text: str):
        self._text: str = text
        self._pos: int = 0

    def has_more(self) -> bool:
        return self._pos < len(self._text)

    def remaining(self) -> int:
        return len(self._text) - self._pos

    def peek_char(self) -> str:
        if not self.has_more():
            raise ParseError("Peek at EOF")
        return self._text[self._pos]

    def read_char(self) -> str:
        if not self.has_more():
            raise ParseError("Unexpected end of text")
        char = self._text[self._pos]
        self._pos += 1
        return char

    def advance(self, n: int = 1) -> None:
        self._pos += n
        if self._pos > len(self._text):
            self._pos = len(self._text)
