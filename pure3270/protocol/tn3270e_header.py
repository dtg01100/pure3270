"""TN3270E message header structure for pure3270."""

import logging
import struct
import time
from typing import Any, Dict, Optional

from .utils import (
    BIND_IMAGE,
    NVT_DATA,
    PRINT_EOJ,
    PRINTER_STATUS_DATA_TYPE,
    REQUEST,
    RESPONSE,
    SCS_DATA,
    SNA_RESPONSE,
    SSCP_LU_DATA,
    TN3270_DATA,
    TN3270E_RSF_ALWAYS_RESPONSE,
    TN3270E_RSF_ERROR_RESPONSE,
    TN3270E_RSF_NEGATIVE_RESPONSE,
    TN3270E_RSF_NO_RESPONSE,
    TN3270E_RSF_POSITIVE_RESPONSE,
    UNBIND,
)

logger = logging.getLogger(__name__)

from .exceptions import ProtocolError


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
        Parse a TN3270E header from bytes with enhanced malformed data handling.

        Args:
            data: 5 bytes containing the TN3270E header

        Returns:
            TN3270EHeader instance or None if parsing fails
        """
        # Enhanced validation for malformed headers
        if not data:
            logger.debug("TN3270E header parsing failed: empty data")
            return None

        if len(data) < 5:
            logger.debug(
                f"TN3270E header parsing failed: insufficient data length {len(data)}"
            )
            return None

        # Check for obviously malformed headers (all zeros, all 0xFF, etc.)
        if all(b == 0 for b in data[:5]):
            logger.debug("TN3270E header parsing failed: all zeros header")
            return None

        if all(b == 0xFF for b in data[:5]):
            logger.debug("TN3270E header parsing failed: all 0xFF header")
            return None

        # Validate data type is within expected range
        data_type = data[0]
        if data_type > 0xFF:
            logger.debug(
                f"TN3270E header parsing failed: invalid data type 0x{data_type:02x}"
            )
            return None

        # Validate sequence number is reasonable (not extremely large)
        seq_number = (data[3] << 8) | data[4]
        if seq_number > 0xFFFF:
            logger.debug(
                f"TN3270E header parsing failed: invalid sequence number 0x{seq_number:04x}"
            )
            return None

        try:
            # Unpack the 5-byte header with enhanced error handling
            # B = unsigned char (1 byte)
            # H = unsigned short (2 bytes, big-endian)
            data_type, request_flag, response_flag, seq_number = struct.unpack(
                "!BBBH", data[:5]
            )

            # Additional validation of parsed values
            if data_type not in (
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
            ):
                logger.debug(
                    f"TN3270E header parsing failed: unknown data type 0x{data_type:02x}"
                )
                return None

            # Validate response flag is within expected range
            if response_flag not in (
                TN3270E_RSF_NO_RESPONSE,
                TN3270E_RSF_ERROR_RESPONSE,
                TN3270E_RSF_ALWAYS_RESPONSE,
                TN3270E_RSF_POSITIVE_RESPONSE,
                TN3270E_RSF_NEGATIVE_RESPONSE,
            ):
                logger.debug(
                    f"TN3270E header parsing failed: invalid response flag 0x{response_flag:02x}"
                )
                return None

            return cls(data_type, request_flag, response_flag, seq_number)
        except struct.error as e:
            logger.debug(f"TN3270E header parsing failed: struct error {e}")
            return None
        except Exception as e:
            logger.debug(f"TN3270E header parsing failed: unexpected error {e}")
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

    def handle_negative_response(self, data: bytes) -> None:
        """
        Handle negative response by parsing the code and raising ProtocolError with details.

        Args:
            data: Bytes following the header, starting with the negative code byte.

        Raises:
            ProtocolError: With details of the negative response code and sense if applicable.
        """
        if not self.is_negative_response():
            raise ValueError("Not a negative response header")

        if len(data) < 1:
            raise ProtocolError("Negative response missing code byte")

        code = data[0]
        code_map = {
            0x01: "SEGMENT",
            0x02: "USABLE-AREA",
            0x03: "REQUEST",
            0xFF: "SNA_NEGATIVE",
        }
        msg = code_map.get(code, f"UNKNOWN_NEGATIVE_CODE(0x{code:02x})")

        sense = None
        if code == 0xFF and len(data) >= 3:
            # SNA sense code is 2 bytes big-endian
            sense_code = (data[1] << 8) | data[2]
            # Map to known SNA sense codes
            from .utils import (
                SNA_SENSE_CODE_INVALID_FORMAT,
                SNA_SENSE_CODE_INVALID_REQUEST,
                SNA_SENSE_CODE_INVALID_SEQUENCE,
                SNA_SENSE_CODE_LU_BUSY,
                SNA_SENSE_CODE_NO_RESOURCES,
                SNA_SENSE_CODE_NOT_SUPPORTED,
                SNA_SENSE_CODE_SESSION_FAILURE,
                SNA_SENSE_CODE_STATE_ERROR,
                SNA_SENSE_CODE_SUCCESS,
            )

            sense_map = {
                SNA_SENSE_CODE_SUCCESS: "SUCCESS",
                SNA_SENSE_CODE_INVALID_REQUEST: "INVALID_REQUEST",
                SNA_SENSE_CODE_INVALID_FORMAT: "INVALID_FORMAT",
                SNA_SENSE_CODE_INVALID_SEQUENCE: "INVALID_SEQUENCE",
                SNA_SENSE_CODE_LU_BUSY: "LU_BUSY",
                SNA_SENSE_CODE_NO_RESOURCES: "NO_RESOURCES",
                SNA_SENSE_CODE_NOT_SUPPORTED: "NOT_SUPPORTED",
                SNA_SENSE_CODE_SESSION_FAILURE: "SESSION_FAILURE",
                SNA_SENSE_CODE_STATE_ERROR: "STATE_ERROR",
            }
            sense = sense_map.get(sense_code, f"UNKNOWN_SENSE(0x{sense_code:04x})")
            msg += f" with sense {sense}"

        raise ProtocolError(f"Negative TN3270E response: {msg}")


class MalformedDataHandler:
    malformed_data_log: list[dict[str, object]]
    """
    Handles malformed TN3270E data and provides recovery mechanisms.
    """

    def __init__(self) -> None:
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        self.malformed_data_log = []

    def handle_malformed_header(
        self, data: bytes, context: str = ""
    ) -> Optional[TN3270EHeader]:
        """
        Attempt to recover from malformed TN3270E headers.

        Args:
            data: Raw bytes that may contain a malformed header
            context: Context information for logging

        Returns:
            TN3270EHeader instance if recovery successful, None otherwise
        """
        if not data:
            return None

        # Log the malformed data for analysis
        self.malformed_data_log.append(
            {
                "data": data.hex(),
                "length": len(data),
                "context": context,
                "timestamp": time.time(),
            }
        )

        # Limit log size
        if len(self.malformed_data_log) > 100:
            self.malformed_data_log.pop(0)

        # Try various recovery strategies
        recovery_strategies = [
            self._try_truncated_header,
            self._try_padded_header,
            self._try_realigned_header,
            self._try_legacy_format,
        ]

        for strategy in recovery_strategies:
            try:
                header = strategy(data)
                if header:
                    logger.debug(
                        f"Successfully recovered malformed header using {strategy.__name__}"
                    )
                    return header
            except Exception as e:
                logger.debug(f"Recovery strategy {strategy.__name__} failed: {e}")
                continue

        logger.warning(f"Failed to recover malformed TN3270E header in {context}")
        return None

    def _try_truncated_header(self, data: bytes) -> Optional[TN3270EHeader]:
        """Try to parse a header that might be truncated."""
        if len(data) < 3:  # Need at least data type + some flags
            return None

        # Try to construct a minimal valid header
        data_type = (
            data[0] if data[0] in (TN3270_DATA, SCS_DATA, RESPONSE) else TN3270_DATA
        )
        request_flag = data[1] if len(data) > 1 else 0
        response_flag = data[2] if len(data) > 2 else TN3270E_RSF_NO_RESPONSE
        seq_number = 0  # Default sequence number

        return TN3270EHeader(data_type, request_flag, response_flag, seq_number)

    def _try_padded_header(self, data: bytes) -> Optional[TN3270EHeader]:
        """Try to parse a header that might have padding."""
        if len(data) < 5:
            return None

        # Remove potential padding (null bytes)
        cleaned_data = data[:5].rstrip(b"\x00")
        if len(cleaned_data) < 3:
            return None

        try:
            return TN3270EHeader.from_bytes(data[:5])
        except:
            return None

    def _try_realigned_header(self, data: bytes) -> Optional[TN3270EHeader]:
        """Try to parse a header that might be misaligned."""
        if len(data) < 6:  # Need at least 5 bytes + 1 for realignment
            return None

        # Try different alignments
        for offset in range(min(3, len(data) - 4)):  # Try up to 3 different offsets
            try:
                header = TN3270EHeader.from_bytes(data[offset : offset + 5])
                if header:
                    return header
            except Exception as e:
                # Log and continue on header parse error
                import logging

                logging.error(f"TN3270E header parse error: {e}")
                continue

        return None

    def _try_legacy_format(self, data: bytes) -> Optional[TN3270EHeader]:
        """Try to parse using legacy TN3270E format."""
        if len(data) < 5:
            return None

        # Some legacy implementations might use different byte ordering
        try:
            # Try little-endian instead of big-endian
            data_type, request_flag, response_flag, seq_number = struct.unpack(
                "<BBBH", data[:5]
            )
            return TN3270EHeader(data_type, request_flag, response_flag, seq_number)
        except struct.error:
            return None

    def get_malformed_data_stats(self) -> Dict[str, Any]:
        """Get statistics about malformed data encountered."""
        return {
            "total_malformed": len(self.malformed_data_log),
            "recovery_attempts": self.recovery_attempts,
            "successful_recoveries": len(
                [
                    log
                    for log in self.malformed_data_log
                    if "recovered" in str(log.get("context", ""))
                ]
            ),
        }

    def clear_malformed_data_log(self) -> None:
        """Clear the malformed data log."""
        self.malformed_data_log.clear()


# Global instance for handling malformed data
malformed_handler = MalformedDataHandler()


def test_malformed_data_handling() -> None:
    """Test the malformed data handling functionality."""
    print("Testing malformed TN3270E header handling...")

    # Test cases for malformed headers
    test_cases = [
        # Empty data
        (b"", "empty data"),
        # Insufficient data
        (b"\x00\x01", "insufficient data"),
        # All zeros
        (b"\x00\x00\x00\x00\x00", "all zeros"),
        # All 0xFF
        (b"\xff\xff\xff\xff\xff", "all 0xFF"),
        # Invalid data type
        (b"\x99\x00\x00\x00\x00", "invalid data type"),
        # Invalid sequence number
        (b"\x00\x00\x00\xff\xff", "invalid sequence number"),
        # Valid header
        (b"\x00\x00\x00\x00\x00", "valid header (should be rejected due to all zeros)"),
        # Truncated header
        (b"\x00\x01\x02", "truncated header"),
        # Legacy format (little-endian)
        (b"\x00\x00\x00\x00\x00", "legacy format test"),
    ]

    for data, description in test_cases:
        header = TN3270EHeader.from_bytes(data)
        if header:
            print(f"✓ {description}: Successfully parsed header")
        else:
            print(f"✗ {description}: Failed to parse header (expected)")

    # Test malformed data handler
    handler = MalformedDataHandler()

    # Test recovery attempts
    malformed_data = b"\x99\x99\x99\x99\x99"  # Invalid data type
    recovered_header = handler.handle_malformed_header(malformed_data, "test recovery")

    if recovered_header:
        print(f"✓ Recovery successful: {recovered_header}")
    else:
        print("✗ Recovery failed (expected for invalid data)")

    # Test stats
    stats = handler.get_malformed_data_stats()
    print(f"✓ Malformed data stats: {stats}")

    print("Malformed data handling test completed!")


if __name__ == "__main__":
    test_malformed_data_handling()
