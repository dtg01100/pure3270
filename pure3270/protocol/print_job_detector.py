"""
Print job detection and extraction for transparent TCPIP printer session support.

This module provides classes for detecting print jobs in data streams and extracting
print data from regular session data.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .tn3270e_header import TN3270EHeader
from .utils import PRINT_EOJ, SCS_DATA, TN3270_DATA

logger = logging.getLogger(__name__)


class PrintJobDetector:
    """
    Detects print jobs in data streams and extracts print data.

    This class analyzes incoming data streams to identify print job boundaries,
    SCS data sequences, and protocol transitions between main session and printer
    session modes.
    """

    def __init__(self) -> None:
        """Initialize the print job detector."""
        self._in_print_job = False
        self._print_job_start_pos = 0
        self._current_job_data: List[bytes] = []
        self._job_sequence_number = 0
        self._last_header: Optional[TN3270EHeader] = None

    def detect_print_job(
        self, data: bytes, header: Optional[TN3270EHeader] = None
    ) -> bool:
        """
        Detect if the given data contains or starts a print job.

        Args:
            data: Raw data bytes to analyze
            header: Optional TN3270E header associated with the data

        Returns:
            True if a print job is detected, False otherwise
        """
        if header:
            self._last_header = header

            # Check for explicit print job indicators in header
            if header.data_type == SCS_DATA:
                if not self._in_print_job:
                    self._start_print_job()
                return True

            if header.data_type == PRINT_EOJ:
                if self._in_print_job:
                    self._end_print_job()
                return True

            # Check for SCS control codes that indicate print jobs
            if header.data_type == TN3270_DATA and self._contains_scs_indicators(data):
                if not self._in_print_job:
                    self._start_print_job()
                return True

        # Check data content for SCS patterns even without header
        if self._contains_scs_indicators(data):
            if not self._in_print_job:
                self._start_print_job()
            return True

        return self._in_print_job

    def extract_print_data(
        self, data: bytes, header: Optional[TN3270EHeader] = None
    ) -> Tuple[bytes, bytes]:
        """
        Extract print data from mixed session data.

        Args:
            data: Raw data that may contain both session and print data
            header: Optional TN3270E header

        Returns:
            Tuple of (session_data, print_data) where print_data is extracted
        """
        if not self.detect_print_job(data, header):
            return data, b""

        # If we're in a print job, all data is considered print data
        if self._in_print_job:
            self._current_job_data.append(data)
            return b"", data

        # Check for embedded SCS sequences in TN3270 data
        if header and header.data_type == TN3270_DATA:
            session_data, print_data = self._extract_embedded_scs(data)
            if print_data:
                self._current_job_data.append(print_data)
            return session_data, print_data

        return data, b""

    def is_in_print_job(self) -> bool:
        """Check if currently processing a print job."""
        return self._in_print_job

    def get_current_job_data(self) -> bytes:
        """Get the accumulated data for the current print job."""
        return b"".join(self._current_job_data)

    def get_job_info(self) -> Dict[str, Any]:
        """Get information about the current or last print job."""
        return {
            "in_print_job": self._in_print_job,
            "job_sequence_number": self._job_sequence_number,
            "job_data_length": len(self.get_current_job_data()),
            "start_position": self._print_job_start_pos,
            "last_header_type": (
                self._last_header.data_type if self._last_header else None
            ),
        }

    def reset(self) -> None:
        """Reset the detector state."""
        self._in_print_job = False
        self._print_job_start_pos = 0
        self._current_job_data.clear()
        self._last_header = None

    def _start_print_job(self) -> None:
        """Start tracking a new print job."""
        self._in_print_job = True
        self._print_job_start_pos = 0  # Would be set to current stream position
        self._current_job_data.clear()
        self._job_sequence_number += 1
        logger.debug(f"Started print job #{self._job_sequence_number}")

    def _end_print_job(self) -> None:
        """End the current print job."""
        if self._in_print_job:
            logger.debug(
                f"Ended print job #{self._job_sequence_number}, "
                f"total data: {len(self.get_current_job_data())} bytes"
            )
        self._in_print_job = False

    def _contains_scs_indicators(self, data: bytes) -> bool:
        """
        Check if data contains SCS (SNA Character String) indicators.

        SCS data typically starts with control codes and contains specific
        patterns that distinguish it from regular TN3270 data.
        """
        if len(data) < 2:
            return False

        # Check for common SCS control code patterns
        scs_indicators = [
            b"\x01",  # SOH (Start of Header)
            b"\x0C",  # FF (Form Feed)
            b"\x0D",  # CR (Carriage Return)
            b"\x0A",  # LF (Line Feed)
            b"\x09",  # HT (Horizontal Tab)
            b"\x2B",  # SC (Set Channel)
            b"\x2D",  # IC (Insert Cursor)
        ]

        # Look for SCS control sequences at the start
        for indicator in scs_indicators:
            if data.startswith(indicator):
                return True

        # Check for embedded SCS sequences (multiple control codes)
        control_count = sum(1 for byte in data[:20] if byte < 0x20 or byte == 0x40)
        if control_count >= 3:  # Arbitrary threshold for SCS-like data
            return True

        return False

    def _extract_embedded_scs(self, data: bytes) -> Tuple[bytes, bytes]:
        """
        Extract embedded SCS sequences from TN3270 data.

        This is a simplified implementation. In practice, SCS data would be
        clearly separated by protocol boundaries.
        """
        # For now, if we detect SCS indicators, consider the whole chunk as print data
        if self._contains_scs_indicators(data):
            return b"", data

        return data, b""
