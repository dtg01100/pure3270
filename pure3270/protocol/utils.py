"""Utility functions for TN3270 protocol handling."""

import logging

logger = logging.getLogger(__name__)

# Telnet constants
IAC = 0xFF
SB = 0xFA
SE = 0xF0
WILL = 0xFB
WONT = 0xFC
DO = 0xFD
DONT = 0xFE

# TN3270E constants
TN3270E = 0x28  # TN3270E Telnet option
EOR = 0x19  # End of Record

# TN3270E Data Types
TN3270_DATA = 0x00
SCS_DATA = 0x01
RESPONSE = 0x02
BIND_IMAGE = 0x03
UNBIND = 0x04
NVT_DATA = 0x05
REQUEST = 0x06
SSCP_LU_DATA = 0x07
PRINT_EOJ = 0x08

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


def send_iac(writer, data: bytes) -> None:
    """
    Send IAC command.

    Args:
        writer: StreamWriter.
        data: Data bytes after IAC.
    """
    if writer:
        writer.write(bytes([IAC]) + data)
        # drain() should be awaited in async context
        # The caller is responsible for awaiting drain() if needed


def send_subnegotiation(writer, opt: bytes, data: bytes) -> None:
    """
    Send subnegotiation.

    Args:
        writer: StreamWriter.
        opt: Option byte.
        data: Subnegotiation data.
    """
    if writer:
        sub = bytes([IAC, SB]) + opt + data + bytes([IAC, SE])
        writer.write(sub)
        # drain() should be awaited in async context
        # The caller is responsible for awaiting drain() if needed


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
