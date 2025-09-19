"""Utility functions for TN3270/TN3270E protocol handling.

Typing notes:
- Writer parameters are annotated as `Optional[asyncio.StreamWriter]` to reflect possibility of absent writer during teardown.
- `_schedule_if_awaitable` centralizes best-effort handling of AsyncMock.write returning an awaitable to avoid repeated inline inspection logic.
"""

import asyncio
import inspect
import logging
import struct
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Telnet constants
IAC = 0xFF
SB = 0xFA
SE = 0xF0
WILL = 0xFB
WONT = 0xFC
DO = 0xFD
DONT = 0xFE
IP = 0xF7  # Interrupt Process
AO = 0xF5  # Abort Output
BRK = 0xF3  # Break Process
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
TELOPT_TN3270E = 0x28  # TN3270E Telnet option
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

# TN3270E Data Types
TN3270_DATA = 0x00
TN3270E_DATA = 0x01
SCS_DATA = 0x01
RESPONSE = 0x02
BIND_IMAGE = 0x03
UNBIND = 0x04
NVT_DATA = 0x05
REQUEST = 0x06
SSCP_LU_DATA = 0x07
PRINT_EOJ = 0x08
SNA_RESPONSE = 0x09  # New SNA Response Data Type
SNA_RESPONSE_DATA_TYPE = 0x09  # SNA Response Data Type
PRINTER_STATUS_DATA_TYPE = 0x0A  # New data type for Printer Status (TN3270E)

# TN3270E Data Types tuple for validation
TN3270E_DATA_TYPES = (
    TN3270_DATA,
    TN3270E_DATA,
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

# TN3270E SYSREQ Subnegotiation Message Type and Commands
TN3270E_SYSREQ_MESSAGE_TYPE = 0x03
TN3270E_SYSREQ_ATTN = 0x01
TN3270E_SYSREQ_BREAK = 0x02
TN3270E_SYSREQ_CANCEL = 0x03
TN3270E_SYSREQ_RESTART = 0x04
TN3270E_SYSREQ_PRINT = 0x05
TN3270E_SYSREQ_LOGOFF = 0x06

# TN3270E Request Flags
TN3270E_RQF_ERR_COND_CLEARED = 0x00
TN3270E_RQF_MORE_THAN_ONE_RQST = 0x01
TN3270E_RQF_CANCEL_RQST = 0x02

# TN3270E Response Flags
TN3270E_RSF_NO_RESPONSE = 0x00
TN3270E_RSF_ERROR_RESPONSE = 0x01
TN3270E_RSF_ALWAYS_RESPONSE = 0x02
TN3270E_RSF_POSITIVE_RESPONSE = 0x00
TN3270E_RSF_NEGATIVE_RESPONSE = 0x02

# Structured Field Constants
STRUCTURED_FIELD = 0x3C  # '<' character
QUERY_REPLY_SF = 0x88
READ_PARTITION_QUERY = 0x02
READ_PARTITION_QUERY_LIST = 0x03

# Query Reply Types
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
                except Exception:
                    pass
    except Exception:
        pass


def send_iac(writer: Optional[asyncio.StreamWriter], data: bytes) -> None:
    """
    Send IAC command.

    Args:
        writer: StreamWriter.
        data: Data bytes after IAC.
    """
    if not writer:
        return

    # Call write; AsyncMock.write may return a coroutine that needs awaiting.
    try:
        result = writer.write(bytes([IAC]) + data)
        _schedule_if_awaitable(result)
    except Exception:
        try:
            result = writer.write(bytes([IAC]) + data)
            _schedule_if_awaitable(result)
        except Exception:
            return


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
        writer.write(sub)
    except Exception:
        try:
            writer.write(sub)
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


class ParseError(Exception):
    """Error during parsing."""

    pass


class BaseParser:
    def __init__(self, data: bytes):
        self._data: bytes = data
        self._pos: int = 0

    def has_more(self) -> bool:
        return self._pos < len(self._data)

    def remaining(self) -> int:
        return len(self._data) - self._pos

    def peek_byte(self) -> int:
        if not self.has_more():
            raise ParseError("Peek at EOF")
        return self._data[self._pos]

    def read_byte(self) -> int:
        if not self.has_more():
            raise ParseError("Unexpected end of data stream")
        byte = self._data[self._pos]
        self._pos += 1
        return byte

    def read_u16(self) -> int:
        high = self.read_byte()
        low = self.read_byte()
        result = struct.unpack(">H", bytes([high, low]))[0]
        return int(result)

    def read_fixed(self, length: int) -> bytes:
        if self.remaining() < length:
            raise ParseError("Insufficient data for fixed length read")
        start = self._pos
        self._pos += length
        return self._data[start : self._pos]


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
