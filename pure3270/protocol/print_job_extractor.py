"""
Print job extraction and separation from regular session data.

This module provides classes for extracting and separating print data from
regular session data in transparent TCPIP printer sessions.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from .print_job_detector import PrintJobDetector
from .protocol_translator import ProtocolTranslator
from .tn3270e_header import TN3270EHeader
from .utils import SCS_DATA, TN3270_DATA

logger = logging.getLogger(__name__)


class PrintJobExtractor:
    """
    Extracts and separates print data from regular session data.

    This class coordinates print job detection and protocol translation to
    cleanly separate printer data streams from main session data streams.
    """

    def __init__(self) -> None:
        """Initialize the print job extractor."""
        self.detector = PrintJobDetector()
        self.translator = ProtocolTranslator()
        self._extraction_callbacks: List[Callable[[bytes, TN3270EHeader], None]] = []
        self._job_completion_callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def process_data_stream(
        self, data: bytes, header: Optional[TN3270EHeader] = None
    ) -> Tuple[bytes, Optional[bytes]]:
        """
        Process a data stream and extract any print job data.

        Args:
            data: Raw data stream that may contain mixed session/print data
            header: TN3270E header associated with the data

        Returns:
            Tuple of (session_data, print_data) where print_data is None if no print job
        """
        # First, detect if this data contains print job information
        has_print_job = self.detector.detect_print_job(data, header)

        if not has_print_job:
            # No print job detected, return all data as session data
            return data, None

        # Extract print data from the stream
        session_data, print_data = self.detector.extract_print_data(data, header)

        if print_data:
            # Translate print data to appropriate protocol format
            translated_header, translated_data = (
                self.translator.translate_to_printer_session(print_data, header)
            )

            # Notify callbacks about extracted print data
            self._notify_extraction_callbacks(translated_data, translated_header)

            return session_data, translated_data

        return session_data, None

    def register_extraction_callback(
        self, callback: Callable[[bytes, TN3270EHeader], None]
    ) -> None:
        """
        Register a callback to be notified when print data is extracted.

        Args:
            callback: Function that takes (print_data, header) as arguments
        """
        self._extraction_callbacks.append(callback)

    def register_job_completion_callback(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register a callback to be notified when a print job completes.

        Args:
            callback: Function that takes job_info dict as argument
        """
        self._job_completion_callbacks.append(callback)

    def end_print_job(self) -> Optional[Tuple[TN3270EHeader, bytes]]:
        """
        Signal the end of the current print job.

        Returns:
            Tuple of (header, data) for the job completion message, or None if no active job
        """
        if not self.detector.is_in_print_job():
            return None

        # Get job completion message from translator
        header, data = self.translator.handle_print_job_end()

        # Notify job completion callbacks
        job_info = self.detector.get_job_info()
        job_info["completion_time"] = None  # Could add timestamp
        self._notify_job_completion_callbacks(job_info)

        # Reset detector state
        self.detector.reset()

        # Ensure header is not None for return type
        if header is not None:
            return header, data
        return None

    def get_current_job_info(self) -> Dict[str, Any]:
        """Get information about the current print job."""
        detector_info = self.detector.get_job_info()
        translator_info = self.translator.get_session_info()

        return {
            **detector_info,
            **translator_info,
        }

    def is_processing_print_job(self) -> bool:
        """Check if currently processing a print job."""
        return self.detector.is_in_print_job()

    def reset(self) -> None:
        """Reset the extractor state."""
        self.detector.reset()
        self.translator.deactivate_printer_session()

    def _notify_extraction_callbacks(
        self, print_data: bytes, header: Optional[TN3270EHeader]
    ) -> None:
        """Notify all registered extraction callbacks."""
        if header is None:
            # Create a default header for callbacks
            header = TN3270EHeader(data_type=SCS_DATA)

        for callback in self._extraction_callbacks:
            try:
                callback(print_data, header)
            except Exception as e:
                logger.error(f"Error in extraction callback: {e}")

    def _notify_job_completion_callbacks(self, job_info: Dict[str, Any]) -> None:
        """Notify all registered job completion callbacks."""
        for callback in self._job_completion_callbacks:
            try:
                callback(job_info)
            except Exception as e:
                logger.error(f"Error in job completion callback: {e}")

    def configure_printer_session(self, session_type: str = "tn3270e") -> None:
        """
        Configure the printer session type.

        Args:
            session_type: Either 'tn3270e' or 'tn3270'
        """
        self.translator.activate_printer_session(session_type)
        logger.debug(f"Configured printer session type: {session_type}")

    def handle_printer_status(
        self, status_code: int
    ) -> Tuple[Optional[TN3270EHeader], bytes]:
        """
        Handle printer status updates.

        Args:
            status_code: Printer status code

        Returns:
            Tuple of (header, status_data) for the status response
        """
        return self.translator.translate_status_response(status_code)

    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about print data extraction."""
        job_info = self.get_current_job_info()

        return {
            "jobs_processed": job_info.get("job_sequence_number", 0),
            "currently_processing": job_info.get("in_print_job", False),
            "total_data_extracted": job_info.get("job_data_length", 0),
            "session_type": job_info.get("session_type"),
            "extraction_callbacks": len(self._extraction_callbacks),
            "completion_callbacks": len(self._job_completion_callbacks),
        }
