"""Utility functions for TN3270 protocol handling."""

import logging

logger = logging.getLogger(__name__)

# Telnet constants
IAC = 0xff
SB = 0xfa
SE = 0xf0
WILL = 0xfb
WONT = 0xfc
DO = 0xfd
DONT = 0xfe

def send_iac(writer, data: bytes) -> None:
    """
    Send IAC command.
    
    Args:
        writer: StreamWriter.
        data: Data bytes after IAC.
    """
    if writer:
        writer.write(bytes([IAC]) + data)
        writer.drain()

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
        writer.drain()

def strip_telnet_iac(data: bytes, handle_eor_ga: bool = False, enable_logging: bool = False) -> bytes:
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
                elif handle_eor_ga and cmd in (0x19, 0xf9):  # EOR or GA
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