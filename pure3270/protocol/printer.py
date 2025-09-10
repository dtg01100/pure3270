"""Printer session support for TN3270E protocol."""

import asyncio
import logging
from typing import Optional, List, Tuple
from .tn3270e_header import TN3270EHeader
from .utils import (
    SCS_DATA,
    TN3270E_RSF_NO_RESPONSE,
    TN3270E_RSF_ERROR_RESPONSE,
    TN3270E_RSF_ALWAYS_RESPONSE,
    TN3270E_RSF_POSITIVE_RESPONSE,
    TN3270E_RSF_NEGATIVE_RESPONSE,
    PRINT_EOJ,
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IS,
    TN3270E_REQUEST,
    TN3270E_SEND,
    TN3270E_BIND_IMAGE,
    TN3270E_DATA_STREAM_CTL,
    TN3270E_RESPONSES,
    TN3270E_SCS_CTL_CODES,
    TN3270E_SYSREQ,
    TN3270E_IBM_DYNAMIC,
)
from .exceptions import ProtocolError, ParseError

logger = logging.getLogger(__name__)


class PrinterJob:
    """Represents a printer job in a TN3270E printer session."""

    def __init__(self, job_id: str = ""):
        """Initialize a printer job."""
        if not job_id:
            # Generate a default ID if none provided
            import time

            job_id = f"job_{int(time.time() * 1000) % 100000}"
        self.job_id = job_id
        self.data = bytearray()
        self.status = "active"  # active, completed, error
        self.start_time = asyncio.get_event_loop().time()
        self.end_time: Optional[float] = None
        self.pages: List[bytes] = []

    def add_data(self, data: bytes) -> None:
        """Add SCS character data to the job."""
        self.data.extend(data)
        logger.debug(f"Added {len(data)} bytes to printer job {self.job_id}")

    def complete_job(self) -> None:
        """Mark the job as completed."""
        self.status = "completed"
        self.end_time = asyncio.get_event_loop().time()
        logger.info(f"Printer job {self.job_id} completed")

    def set_error(self, error_msg: str) -> None:
        """Mark the job as having an error."""
        self.status = "error"
        self.end_time = asyncio.get_event_loop().time()
        logger.error(f"Printer job {self.job_id} error: {error_msg}")

    def get_duration(self) -> float:
        """Get the job duration in seconds."""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return asyncio.get_event_loop().time() - self.start_time

    def get_page_count(self) -> int:
        """Get the number of pages in the job."""
        # Simple page counting based on form feeds (0x0C)
        page_count = 1  # At least one page
        for byte in self.data:
            if byte == 0x0C:  # Form feed
                page_count += 1
        return page_count

    def get_data_size(self) -> int:
        """Get the size of the job data in bytes."""
        return len(self.data)

    def __repr__(self) -> str:
        """String representation of the printer job."""
        return (
            f"PrinterJob(id='{self.job_id}', status='{self.status}', "
            f"pages={self.get_page_count()}, size={self.get_data_size()} bytes, "
            f"duration={self.get_duration():.2f}s)"
        )


class PrinterSession:
    """TN3270E printer session handler."""

    def __init__(self):
        """Initialize the printer session."""
        self.is_active = False
        self.current_job: Optional[PrinterJob] = None
        self.completed_jobs: List[PrinterJob] = []
        self.sequence_number = 0
        self.max_jobs = 100  # Limit to prevent memory issues
        self.job_counter = 0

    def activate(self) -> None:
        """Activate the printer session."""
        self.is_active = True
        logger.info("Printer session activated")

    def deactivate(self) -> None:
        """Deactivate the printer session."""
        if self.current_job:
            self.current_job.set_error("Session deactivated")
            self._finish_current_job()
        self.is_active = False
        logger.info("Printer session deactivated")

    def start_new_job(self, job_id: str = "") -> PrinterJob:
        """Start a new printer job."""
        if not self.is_active:
            raise ProtocolError("Printer session not active")

        # Finish any existing job
        if self.current_job:
            self.current_job.set_error("New job started before completion")
            self._finish_current_job()

        # Create new job
        if not job_id:
            self.job_counter += 1
            job_id = f"job_{self.job_counter}"

        self.current_job = PrinterJob(job_id)
        logger.info(f"Started new printer job: {job_id}")
        return self.current_job

    def add_scs_data(self, data: bytes) -> None:
        """Add SCS character data to the current job."""
        if not self.is_active:
            raise ProtocolError("Printer session not active")

        if not self.current_job:
            self.start_new_job()

        if self.current_job:
            self.current_job.add_data(data)

    def handle_print_eoj(self) -> None:
        """Handle PRINT-EOJ (End of Job) command."""
        if not self.is_active:
            raise ProtocolError("Printer session not active")

        if self.current_job:
            self.current_job.complete_job()
            self._finish_current_job()
        else:
            logger.warning("PRINT-EOJ received but no active job")

    def _finish_current_job(self) -> None:
        """Finish the current job and add to completed jobs."""
        if self.current_job:
            # Add to completed jobs
            self.completed_jobs.append(self.current_job)

            # Limit the number of stored jobs
            if len(self.completed_jobs) > self.max_jobs:
                # Remove oldest jobs
                self.completed_jobs = self.completed_jobs[-self.max_jobs :]

            # Clear current job
            self.current_job = None
            logger.info("Current printer job finished and stored")

    def get_current_job(self) -> Optional[PrinterJob]:
        """Get the current active job."""
        return self.current_job

    def get_completed_jobs(self) -> List[PrinterJob]:
        """Get the list of completed jobs."""
        return self.completed_jobs.copy()

    def get_job_statistics(self) -> dict:
        """Get printer job statistics."""
        active_job = 1 if self.current_job else 0
        completed_count = len(self.completed_jobs)
        total_pages = sum(job.get_page_count() for job in self.completed_jobs)
        total_bytes = sum(job.get_data_size() for job in self.completed_jobs)

        return {
            "active_jobs": active_job,
            "completed_jobs": completed_count,
            "total_pages": total_pages,
            "total_bytes": total_bytes,
            "average_pages_per_job": total_pages / max(completed_count, 1),
            "average_bytes_per_job": total_bytes / max(completed_count, 1),
        }

    def clear_completed_jobs(self) -> None:
        """Clear the list of completed jobs."""
        self.completed_jobs.clear()
        logger.info("Cleared completed printer jobs")

    def handle_scs_control_code(self, scs_code: int) -> None:
        """Handle SCS control codes."""
        if not self.is_active:
            raise ProtocolError("Printer session not active")

        if scs_code == PRINT_EOJ:
            self.handle_print_eoj()
            logger.debug("Handled SCS PRINT-EOJ control code")
        else:
            logger.warning(f"Unhandled SCS control code: 0x{scs_code:02x}")

    def process_tn3270e_message(self, header: TN3270EHeader, data: bytes) -> None:
        """Process a TN3270E message for printer session."""
        if not self.is_active:
            raise ProtocolError("Printer session not active")

        if header.data_type == SCS_DATA or header.data_type == TN3270E_SCS_CTL_CODES:
            # Add SCS data to current job
            self.add_scs_data(data)
            logger.debug(f"Processed {len(data)} bytes of SCS data")
        elif header.data_type == TN3270E_RESPONSES:
            # Handle response messages
            if header.response_flag == TN3270E_RSF_ERROR_RESPONSE:
                logger.error(
                    f"Received error response for sequence {header.seq_number}"
                )
                if self.current_job:
                    self.current_job.set_error(
                        f"Error response received for sequence {header.seq_number}"
                    )
            elif header.response_flag == TN3270E_RSF_NEGATIVE_RESPONSE:
                logger.warning(
                    f"Received negative response for sequence {header.seq_number}"
                )
        else:
            logger.warning(
                f"Unhandled TN3270E data type: {header.get_data_type_name()}"
            )

    def __repr__(self) -> str:
        """String representation of the printer session."""
        stats = self.get_job_statistics()
        return (
            f"PrinterSession(active={self.is_active}, "
            f"current_job={'Yes' if self.current_job else 'No'}, "
            f"completed_jobs={stats['completed_jobs']})"
        )
