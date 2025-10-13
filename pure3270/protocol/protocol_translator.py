"""
Protocol translation between main session and printer session protocols.

This module provides classes for translating between TN3270 main session protocols
and printer session protocols (TN3270E and basic TN3270).
"""

import logging
from typing import Any, Dict, Optional, Tuple, Union

from .tn3270e_header import TN3270EHeader
from .utils import (
    PRINT_EOJ,
    REQUEST,
    RESPONSE,
    SCS_DATA,
    TN3270_DATA,
    TN3270E_RSF_NO_RESPONSE,
)

logger = logging.getLogger(__name__)


class ProtocolTranslator:
    """
    Translates between main session and printer session protocols.

    This class handles the protocol differences between regular TN3270 sessions
    and printer sessions, including TN3270E header translation and data format
    conversion.
    """

    def __init__(self) -> None:
        """Initialize the protocol translator."""
        self._printer_session_active = False
        self._sequence_number = 0
        self._session_type: Optional[str] = None  # 'tn3270e' or 'tn3270'

    def translate_to_printer_session(
        self,
        data: bytes,
        source_header: Optional[TN3270EHeader] = None,
        session_type: str = "tn3270e",
    ) -> Tuple[Optional[TN3270EHeader], bytes]:
        """
        Translate data from main session to printer session format.

        Args:
            data: Data to translate
            source_header: Original TN3270E header (if any)
            session_type: Target printer session type ('tn3270e' or 'tn3270')

        Returns:
            Tuple of (translated_header, translated_data)
        """
        self._session_type = session_type

        if session_type == "tn3270e":
            return self._translate_to_tn3270e_printer(data, source_header)
        elif session_type == "tn3270":
            return self._translate_to_tn3270_printer(data, source_header)
        else:
            logger.warning(f"Unknown session type: {session_type}")
            return source_header, data

    def translate_from_printer_session(
        self,
        data: bytes,
        printer_header: Optional[TN3270EHeader] = None,
        target_session_type: str = "tn3270e",
    ) -> Tuple[Optional[TN3270EHeader], bytes]:
        """
        Translate data from printer session back to main session format.

        Args:
            data: Data from printer session
            printer_header: Printer session header
            target_session_type: Target main session type

        Returns:
            Tuple of (translated_header, translated_data)
        """
        if target_session_type == "tn3270e":
            return self._translate_from_tn3270e_printer(data, printer_header)
        else:
            logger.warning(f"Unsupported target session type: {target_session_type}")
            return printer_header, data

    def activate_printer_session(self, session_type: str = "tn3270e") -> None:
        """Activate printer session mode."""
        self._printer_session_active = True
        self._session_type = session_type
        self._sequence_number = 0
        logger.debug(f"Activated printer session: {session_type}")

    def deactivate_printer_session(self) -> None:
        """Deactivate printer session mode."""
        self._printer_session_active = False
        self._session_type = None
        logger.debug("Deactivated printer session")

    def is_printer_session_active(self) -> bool:
        """Check if printer session is currently active."""
        return self._printer_session_active

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session state."""
        return {
            "printer_session_active": self._printer_session_active,
            "session_type": self._session_type,
            "sequence_number": self._sequence_number,
        }

    def _translate_to_tn3270e_printer(
        self, data: bytes, source_header: Optional[TN3270EHeader]
    ) -> Tuple[Optional[TN3270EHeader], bytes]:
        """Translate to TN3270E printer session format."""
        # Create new header for printer session
        header = TN3270EHeader(
            data_type=SCS_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_NO_RESPONSE,
            seq_number=self._sequence_number,
        )
        self._sequence_number += 1

        # Data remains largely unchanged for SCS, but may need formatting
        translated_data = self._format_scs_data(data)

        return header, translated_data

    def _translate_to_tn3270_printer(
        self, data: bytes, source_header: Optional[TN3270EHeader]
    ) -> Tuple[Optional[TN3270EHeader], bytes]:
        """Translate to basic TN3270 printer session format."""
        # Basic TN3270 printer sessions don't use TN3270E headers
        # Data is sent directly as SCS data
        translated_data = self._format_scs_data(data)
        return None, translated_data

    def _translate_from_tn3270e_printer(
        self, data: bytes, printer_header: Optional[TN3270EHeader]
    ) -> Tuple[Optional[TN3270EHeader], bytes]:
        """Translate from TN3270E printer session back to main session."""
        if not printer_header:
            # No header, assume it's response data
            header = TN3270EHeader(
                data_type=RESPONSE,
                request_flag=0,
                response_flag=TN3270E_RSF_NO_RESPONSE,
                seq_number=self._sequence_number,
            )
            self._sequence_number += 1
            return header, data

        # Convert printer response to main session response
        header = TN3270EHeader(
            data_type=RESPONSE,
            request_flag=printer_header.request_flag,
            response_flag=printer_header.response_flag,
            seq_number=printer_header.seq_number,
        )

        return header, data

    def _format_scs_data(self, data: bytes) -> bytes:
        """
        Format data as SCS (SNA Character String) data.

        This ensures the data conforms to SCS protocol expectations.
        """
        if not data:
            return data

        # Basic SCS formatting - ensure proper control codes
        # In a real implementation, this would handle various SCS commands
        formatted_data = data

        # Ensure data ends with appropriate terminator if it's a complete job
        # For now, just return the data as-is
        return formatted_data

    def handle_print_job_end(self) -> Tuple[Optional[TN3270EHeader], bytes]:
        """Handle the end of a print job."""
        # Send PRINT_EOJ to signal job completion
        header = TN3270EHeader(
            data_type=PRINT_EOJ,
            request_flag=0,
            response_flag=TN3270E_RSF_NO_RESPONSE,
            seq_number=self._sequence_number,
        )
        self._sequence_number += 1

        # Empty data for EOJ
        return header, b""

    def translate_status_response(
        self, status_code: int
    ) -> Tuple[Optional[TN3270EHeader], bytes]:
        """
        Translate printer status into protocol response.

        Args:
            status_code: Printer status code (e.g., 0x00 success, 0x40 device end)

        Returns:
            Tuple of (header, status_data)
        """
        header = TN3270EHeader(
            data_type=RESPONSE,
            request_flag=0,
            response_flag=TN3270E_RSF_NO_RESPONSE,
            seq_number=self._sequence_number,
        )
        self._sequence_number += 1

        # Status data (single byte status code)
        status_data = bytes([status_code])

        return header, status_data
