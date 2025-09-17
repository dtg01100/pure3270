"""TN3270E message header structure for pure3270."""

import logging
import struct
from typing import Optional

from .utils import (BIND_IMAGE, NVT_DATA, PRINT_EOJ, PRINTER_STATUS_DATA_TYPE,
                    REQUEST, RESPONSE, SCS_DATA, SNA_RESPONSE, SSCP_LU_DATA,
                    TN3270_DATA, TN3270E_RSF_ALWAYS_RESPONSE,
                    TN3270E_RSF_ERROR_RESPONSE, TN3270E_RSF_NEGATIVE_RESPONSE,
                    TN3270E_RSF_NO_RESPONSE, TN3270E_RSF_POSITIVE_RESPONSE,
                    UNBIND)

logger = logging.getLogger(__name__)


class TN3270EHeader:
    """
    TN3270E Message Header Structure (RFC 2355 Section 3).

    The TN3270E header is a 5-byte structure with the following fields:

    Byte 0: DATA-TYPE
    Byte 1: REQUEST-FLAG
    Byte 2: RESPONSE-FLAG
    Byte 3-4: SEQ-NUMBER (16-bit big-endian)
    """

    def __init__(
        self,
        data_type: int = TN3270_DATA,
        request_flag: int = 0,
        response_flag: int = TN3270E_RSF_NO_RESPONSE,
        seq_number: int = 0,
    ):
        """
        Initialize a TN3270E header.

        Args:
            data_type: Type of data (TN3270_DATA, SCS_DATA, etc.)
            request_flag: Request flags
            response_flag: Response flags
            seq_number: Sequence number (0-65535)
        """
        self.data_type = data_type
        self.request_flag = request_flag
        self.response_flag = response_flag
        self.seq_number = seq_number

    @classmethod
    def from_bytes(cls, data: bytes) -> Optional["TN3270EHeader"]:
        """
        Parse a TN3270E header from bytes.

        Args:
            data: 5 bytes containing the TN3270E header

        Returns:
            TN3270EHeader instance or None if parsing fails
        """
        if len(data) < 5:
            return None

        try:
            # Unpack the 5-byte header
            # B = unsigned char (1 byte)
            # H = unsigned short (2 bytes, big-endian)
            data_type, request_flag, response_flag, seq_number = struct.unpack(
                "!BBBH", data[:5]
            )
            return cls(data_type, request_flag, response_flag, seq_number)
        except struct.error:
            return None

    def to_bytes(self) -> bytes:
        """
        Convert the header to bytes.

        Returns:
            5 bytes representing the TN3270E header
        """
        return struct.pack(
            "!BBBH",
            self.data_type,
            self.request_flag,
            self.response_flag,
            self.seq_number,
        )

    def __repr__(self) -> str:
        """String representation of the header."""
        data_type_name = self.get_data_type_name()
        response_flag_name = self.get_response_flag_name()
        return f"TN3270EHeader(data_type={data_type_name}, request_flag=0x{self.request_flag:02x}, response_flag={response_flag_name}, seq_number={self.seq_number})"

    def is_tn3270_data(self) -> bool:
        """Check if this is TN3270_DATA type."""
        return self.data_type == TN3270_DATA

    def is_scs_data(self) -> bool:
        """Check if this is SCS_DATA type."""
        return self.data_type == SCS_DATA

    def is_response(self) -> bool:
        """Check if this is RESPONSE type."""
        return self.data_type == RESPONSE

    def is_error_response(self) -> bool:
        """Check if this is an error response."""
        return self.response_flag == TN3270E_RSF_ERROR_RESPONSE

    def is_negative_response(self) -> bool:
        """Check if this is a negative response."""
        return self.response_flag == TN3270E_RSF_NEGATIVE_RESPONSE

    def is_positive_response(self) -> bool:
        """Check if this is a positive response."""
        return self.response_flag == TN3270E_RSF_POSITIVE_RESPONSE

    def is_always_response(self) -> bool:
        """Check if this is an always response."""
        return self.response_flag == TN3270E_RSF_ALWAYS_RESPONSE

    def get_data_type_name(self) -> str:
        """Get human-readable name for data type."""
        names = {
            TN3270_DATA: "TN3270_DATA",
            SCS_DATA: "SCS_DATA",
            RESPONSE: "RESPONSE",
            BIND_IMAGE: "BIND_IMAGE",
            UNBIND: "UNBIND",
            NVT_DATA: "NVT_DATA",
            REQUEST: "REQUEST",
            SSCP_LU_DATA: "SSCP_LU_DATA",
            PRINT_EOJ: "PRINT_EOJ",
            SNA_RESPONSE: "SNA_RESPONSE",
            PRINTER_STATUS_DATA_TYPE: "PRINTER_STATUS_DATA_TYPE",
        }
        return names.get(self.data_type, f"UNKNOWN(0x{self.data_type:02x})")

    def get_response_flag_name(self) -> str:
        """Get human-readable name for response flag."""
        names = {
            TN3270E_RSF_NO_RESPONSE: "NO_RESPONSE",
            TN3270E_RSF_ERROR_RESPONSE: "ERROR_RESPONSE",
            TN3270E_RSF_ALWAYS_RESPONSE: "ALWAYS_RESPONSE",
            TN3270E_RSF_POSITIVE_RESPONSE: "POSITIVE_RESPONSE",
            TN3270E_RSF_NEGATIVE_RESPONSE: "NEGATIVE_RESPONSE",
        }
        return names.get(
            self.response_flag, f"UNKNOWN_RESPONSE_FLAG(0x{self.response_flag:02x})"
        )
