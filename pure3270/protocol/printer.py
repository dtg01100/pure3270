"""Advanced printer session support for TN3270E protocol with comprehensive SCS control codes."""

import asyncio
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .exceptions import ParseError, ProtocolError
from .tn3270e_header import TN3270EHeader
from .utils import (  # Additional constants for advanced printer support
    BIND_IMAGE,
    NVT_DATA,
    PRINT_EOJ,
    PRINTER_STATUS_DATA_TYPE,
    REQUEST,
    RESPONSE,
    SCS_DATA,
    SSCP_LU_DATA,
    TN3270_DATA,
    TN3270E_BIND_IMAGE,
    TN3270E_DATA_STREAM_CTL,
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IBM_DYNAMIC,
    TN3270E_IS,
    TN3270E_REQUEST,
    TN3270E_RESPONSES,
    TN3270E_RSF_ALWAYS_RESPONSE,
    TN3270E_RSF_ERROR_RESPONSE,
    TN3270E_RSF_NEGATIVE_RESPONSE,
    TN3270E_RSF_NO_RESPONSE,
    TN3270E_RSF_POSITIVE_RESPONSE,
    TN3270E_SCS_CTL_CODES,
    TN3270E_SEND,
    TN3270E_SYSREQ,
    UNBIND,
)

logger = logging.getLogger(__name__)


class PrinterJob:
    """Represents a printer job in a TN3270E printer session with advanced features."""

    def __init__(self, job_id: str = "", max_data_size: int = 1048576):
        """Initialize a printer job with thread-safe operations."""
        if not job_id:
            # Generate a default ID if none provided
            job_id = f"job_{int(time.time() * 1000) % 100000}"
        self.job_id = job_id
        self.max_data_size = max_data_size
        self.data = bytearray()
        self.status = "active"  # active, completed, error, paused
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.pages: List[bytes] = []
        self.scs_control_codes: List[int] = []
        self.page_count = 0
        self.line_count = 0
        self.error_message: Optional[str] = None
        self.lock = threading.Lock()  # Thread safety
        self.metadata: Dict[str, Any] = {}

    def add_data(self, data: bytes) -> None:
        """Add SCS character data to the job with thread safety."""
        with self.lock:
            self.data.extend(data)
            if len(self.data) > self.max_data_size:
                self.data = self.data[-self.max_data_size :]
            logger.debug(f"Added {len(data)} bytes to printer job {self.job_id}")

    def add_scs_control_code(self, scs_code: int) -> None:
        """Add SCS control code to the job."""
        with self.lock:
            self.scs_control_codes.append(scs_code)
            logger.debug(
                f"Added SCS control code 0x{scs_code:02x} to printer job {self.job_id}"
            )

    def increment_line_count(self) -> None:
        """Increment line count for the job."""
        with self.lock:
            self.line_count += 1

    def increment_page_count(self) -> None:
        """Increment page count for the job."""
        with self.lock:
            self.page_count += 1

    def complete_job(self) -> None:
        """Mark the job as completed with thread safety."""
        with self.lock:
            if self.status == "active":
                self.status = "completed"
                self.end_time = time.time()
                logger.info(f"Printer job {self.job_id} completed successfully")

    def set_error(self, error_msg: str) -> None:
        """Mark the job as having an error with thread safety."""
        with self.lock:
            self.status = "error"
            self.end_time = time.time()
            self.error_message = error_msg
            logger.error(f"Printer job {self.job_id} error: {error_msg}")

    def pause_job(self) -> None:
        """Pause the job with thread safety."""
        with self.lock:
            if self.status == "active":
                self.status = "paused"
                logger.info(f"Printer job {self.job_id} paused")

    def resume_job(self) -> None:
        """Resume the job with thread safety."""
        with self.lock:
            if self.status == "paused":
                self.status = "active"
                logger.info(f"Printer job {self.job_id} resumed")

    def get_duration(self) -> float:
        """Get the job duration in seconds."""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return time.time() - self.start_time

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
            f"pages={self.get_page_count()}, lines={self.line_count}, "
            f"size={self.get_data_size()} bytes, "
            f"scs_codes={len(self.scs_control_codes)}, "
            f"duration={self.get_duration():.2f}s)"
        )

    def get_scs_control_codes(self) -> List[int]:
        """Get the list of SCS control codes."""
        with self.lock:
            return self.scs_control_codes.copy()

    def get_error_message(self) -> Optional[str]:
        """Get the error message if any."""
        with self.lock:
            return self.error_message

    def is_thread_safe(self) -> bool:
        """Check if the job supports thread-safe operations."""
        return True


class PrinterSession:
    """Advanced TN3270E printer session handler with comprehensive SCS support."""

    def __init__(self) -> None:
        """Initialize the printer session with thread safety."""
        self.is_active = False
        self.current_job: Optional[PrinterJob] = None
        self.completed_jobs: List[PrinterJob] = []
        self.sequence_number = 0
        self.max_jobs = 50  # Limit to prevent memory issues
        self.job_counter = 0
        self.lock = threading.Lock()  # Thread safety
        self.scs_handlers: Dict[int, Callable[..., None]] = {}
        self.tn3270e_functions: Set[int] = set()
        self.device_type = TN3270E_IBM_DYNAMIC
        self.last_activity = time.time()
        self.error_count = 0
        self.max_errors = 10

    def activate(self) -> None:
        """Activate the printer session with thread safety."""
        with self.lock:
            self.is_active = True
            self.last_activity = time.time()
            self._initialize_scs_handlers()
            logger.info(
                f"Printer session activated with device type: {self.device_type}"
            )

    def deactivate(self) -> None:
        """Deactivate the printer session with thread safety."""
        with self.lock:
            if self.current_job:
                self.current_job.set_error("Session deactivated")
                self._finish_current_job()
            self.is_active = False
            logger.info("Printer session deactivated")

    def _initialize_scs_handlers(self) -> None:
        """Initialize SCS control code handlers."""
        self.scs_handlers = {
            PRINT_EOJ: self._handle_print_eoj_scs,  # 0x08 - PRINT-EOJ
            0x01: self._handle_soh_scs,  # Start of Header
            0x03: self._handle_cr_scs,  # Carriage Return
            0x04: self._handle_nl_scs,  # New Line
            0x05: self._handle_ff_scs,  # Form Feed
            0x06: self._handle_ht_scs,  # Horizontal Tab
            0x07: self._handle_vt_scs,  # Vertical Tab
            # 0x08 is PRINT_EOJ, not Backspace in SCS context
            0x09: self._handle_lf_scs,  # Line Feed
            0x0A: self._handle_ir_scs,  # Index Return
            0x0B: self._handle_vcs_scs,  # Vertical Channel Select
            0x0C: self._handle_ff_scs,  # Form Feed (duplicate)
            0x0D: self._handle_cr_scs,  # Carriage Return (duplicate)
            0x0E: self._handle_so_scs,  # Shift Out
            0x0F: self._handle_si_scs,  # Shift In
            0x10: self._handle_trn_scs,  # Transparent
            0x11: self._handle_it_scs,  # Indent Tab
            0x12: self._handle_irs_scs,  # Intermittent Right Space
            0x13: self._handle_suo_scs,  # Set Uppercase On
            0x14: self._handle_suf_scs,  # Set Uppercase Off
            0x15: self._handle_bel_scs,  # Bell
            0x16: self._handle_ea_scs,  # Enable Alarm
            0x17: self._handle_da_scs,  # Disable Alarm
            0x18: self._handle_nop_scs,  # No Operation
            0x19: self._handle_ems_scs,  # End of Message Set
            0x1A: self._handle_ubs_scs,  # Unit Backspace
            0x1B: self._handle_cuu_scs,  # Cursor Up
            0x1C: self._handle_cud_scs,  # Cursor Down
            0x1D: self._handle_cuf_scs,  # Cursor Forward
            0x1E: self._handle_cub_scs,  # Cursor Backward
            0x1F: self._handle_cuu_scs,  # Cursor Up (duplicate)
        }

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

    def prune(self) -> None:
        """Prune completed jobs to the last max_jobs."""
        if len(self.completed_jobs) > self.max_jobs:
            self.completed_jobs = self.completed_jobs[-self.max_jobs :]
            logger.debug(f"Pruned completed jobs to last {self.max_jobs}")

    def get_current_job(self) -> Optional[PrinterJob]:
        """Get the current active job."""
        return self.current_job

    def get_completed_jobs(self) -> List[PrinterJob]:
        """Get the list of completed jobs."""
        return self.completed_jobs.copy()

    def get_job_statistics(self) -> Dict[str, Any]:
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

    def close(self) -> None:
        """Close the printer session and clear all jobs."""
        self.deactivate()
        self.clear_completed_jobs()
        logger.info("Printer session closed and jobs cleared")

    def handle_scs_control_code(self, scs_code: int) -> None:
        """Handle SCS control codes with comprehensive support."""
        if not self.is_active:
            raise ProtocolError("Printer session not active")

        with self.lock:
            self.last_activity = time.time()

            if scs_code in self.scs_handlers:
                try:
                    self.scs_handlers[scs_code]()
                    if self.current_job:
                        self.current_job.add_scs_control_code(scs_code)
                except Exception as e:
                    logger.error(
                        f"Error handling SCS control code 0x{scs_code:02x}: {e}"
                    )
                    self.error_count += 1
                    if self.error_count > self.max_errors:
                        logger.error("Too many SCS errors, deactivating session")
                        self.deactivate()
            else:
                logger.warning(f"Unhandled SCS control code: 0x{scs_code:02x}")

    # SCS Control Code Handlers
    def _handle_print_eoj_scs(self) -> None:
        """Handle PRINT-EOJ SCS control code."""
        self.handle_print_eoj()
        logger.debug("Handled SCS PRINT-EOJ control code")

    def _handle_soh_scs(self) -> None:
        """Handle Start of Header SCS control code."""
        logger.debug("Handled SCS SOH (Start of Header)")

    def _handle_cr_scs(self) -> None:
        """Handle Carriage Return SCS control code."""
        if self.current_job:
            self.current_job.increment_line_count()
        logger.debug("Handled SCS CR (Carriage Return)")

    def _handle_nl_scs(self) -> None:
        """Handle New Line SCS control code."""
        if self.current_job:
            self.current_job.increment_line_count()
        logger.debug("Handled SCS NL (New Line)")

    def _handle_ff_scs(self) -> None:
        """Handle Form Feed SCS control code."""
        if self.current_job:
            self.current_job.increment_page_count()
        logger.debug("Handled SCS FF (Form Feed)")

    def _handle_ht_scs(self) -> None:
        """Handle Horizontal Tab SCS control code."""
        logger.debug("Handled SCS HT (Horizontal Tab)")

    def _handle_vt_scs(self) -> None:
        """Handle Vertical Tab SCS control code."""
        logger.debug("Handled SCS VT (Vertical Tab)")

    def _handle_bs_scs(self) -> None:
        """Handle Backspace SCS control code."""
        logger.debug("Handled SCS BS (Backspace)")

    def _handle_lf_scs(self) -> None:
        """Handle Line Feed SCS control code."""
        if self.current_job:
            self.current_job.increment_line_count()
        logger.debug("Handled SCS LF (Line Feed)")

    def _handle_ir_scs(self) -> None:
        """Handle Index Return SCS control code."""
        logger.debug("Handled SCS IR (Index Return)")

    def _handle_vcs_scs(self) -> None:
        """Handle Vertical Channel Select SCS control code."""
        logger.debug("Handled SCS VCS (Vertical Channel Select)")

    def _handle_so_scs(self) -> None:
        """Handle Shift Out SCS control code."""
        logger.debug("Handled SCS SO (Shift Out)")

    def _handle_si_scs(self) -> None:
        """Handle Shift In SCS control code."""
        logger.debug("Handled SCS SI (Shift In)")

    def _handle_trn_scs(self) -> None:
        """Handle Transparent SCS control code."""
        logger.debug("Handled SCS TRN (Transparent)")

    def _handle_it_scs(self) -> None:
        """Handle Indent Tab SCS control code."""
        logger.debug("Handled SCS IT (Indent Tab)")

    def _handle_irs_scs(self) -> None:
        """Handle Intermittent Right Space SCS control code."""
        logger.debug("Handled SCS IRS (Intermittent Right Space)")

    def _handle_suo_scs(self) -> None:
        """Handle Set Uppercase On SCS control code."""
        logger.debug("Handled SCS SUO (Set Uppercase On)")

    def _handle_suf_scs(self) -> None:
        """Handle Set Uppercase Off SCS control code."""
        logger.debug("Handled SCS SUF (Set Uppercase Off)")

    def _handle_bel_scs(self) -> None:
        """Handle Bell SCS control code."""
        logger.debug("Handled SCS BEL (Bell)")

    def _handle_ea_scs(self) -> None:
        """Handle Enable Alarm SCS control code."""
        logger.debug("Handled SCS EA (Enable Alarm)")

    def _handle_da_scs(self) -> None:
        """Handle Disable Alarm SCS control code."""
        logger.debug("Handled SCS DA (Disable Alarm)")

    def _handle_nop_scs(self) -> None:
        """Handle No Operation SCS control code."""
        logger.debug("Handled SCS NOP (No Operation)")

    def _handle_ems_scs(self) -> None:
        """Handle End of Message Set SCS control code."""
        logger.debug("Handled SCS EMS (End of Message Set)")

    def _handle_ubs_scs(self) -> None:
        """Handle Unit Backspace SCS control code."""
        logger.debug("Handled SCS UBS (Unit Backspace)")

    def _handle_cuu_scs(self) -> None:
        """Handle Cursor Up SCS control code."""
        logger.debug("Handled SCS CUU (Cursor Up)")

    def _handle_cud_scs(self) -> None:
        """Handle Cursor Down SCS control code."""
        logger.debug("Handled SCS CUD (Cursor Down)")

    def _handle_cuf_scs(self) -> None:
        """Handle Cursor Forward SCS control code."""
        logger.debug("Handled SCS CUF (Cursor Forward)")

    def _handle_cub_scs(self) -> None:
        """Handle Cursor Backward SCS control code."""
        logger.debug("Handled SCS CUB (Cursor Backward)")

    def process_tn3270e_message(self, header: TN3270EHeader, data: bytes) -> None:
        """Process a TN3270E message for printer session with comprehensive support."""
        if not self.is_active:
            raise ProtocolError("Printer session not active")

        with self.lock:
            self.last_activity = time.time()

            # Handle different TN3270E data types
            if header.data_type == SCS_DATA:
                # Add SCS data to current job
                self.add_scs_data(data)
                logger.debug(f"Processed {len(data)} bytes of SCS data")
            elif header.data_type == TN3270E_SCS_CTL_CODES:
                # Handle SCS control codes
                if data:
                    scs_code = data[0]
                    self.handle_scs_control_code(scs_code)
                logger.debug(f"Processed SCS control codes: {data.hex()}")
            elif header.data_type == TN3270E_RESPONSES:
                # Handle response messages with enhanced error handling
                self._handle_tn3270e_response(header, data)
            elif header.data_type == BIND_IMAGE:
                # Handle BIND-IMAGE structured field
                self._handle_bind_image_message(header, data)
            elif header.data_type == REQUEST:
                # Handle REQUEST messages
                self._handle_request_message(header, data)
            elif header.data_type == RESPONSE:
                # Handle RESPONSE messages
                self._handle_response_message(header, data)
            elif header.data_type == TN3270_DATA:
                # Handle 3270 data stream
                self._handle_3270_data_message(header, data)
            elif header.data_type == NVT_DATA:
                # Handle NVT data
                logger.debug(f"Received NVT data: {data!r}")
            elif header.data_type == SSCP_LU_DATA:
                # Handle SSCP-LU data
                logger.debug(f"Received SSCP-LU data: {data.hex()}")
            elif header.data_type == UNBIND:
                # Handle UNBIND
                logger.info("Received UNBIND message")
            elif header.data_type == PRINTER_STATUS_DATA_TYPE:
                # Handle printer status data
                self._handle_printer_status_message(header, data)
            else:
                logger.warning(
                    f"Unhandled TN3270E data type: {header.get_data_type_name()}"
                )

    def _handle_tn3270e_response(self, header: TN3270EHeader, data: bytes) -> None:
        """Handle TN3270E response messages."""
        if header.response_flag == TN3270E_RSF_ERROR_RESPONSE:
            logger.error(f"Received error response for sequence {header.seq_number}")
            if self.current_job:
                self.current_job.set_error(
                    f"Error response received for sequence {header.seq_number}"
                )
        elif header.response_flag == TN3270E_RSF_NEGATIVE_RESPONSE:
            logger.warning(
                f"Received negative response for sequence {header.seq_number}"
            )
            # Try to parse negative response details
            if len(data) > 0:
                code = data[0]
                logger.warning(f"Negative response code: 0x{code:02x}")
        elif header.response_flag == TN3270E_RSF_POSITIVE_RESPONSE:
            logger.debug(f"Received positive response for sequence {header.seq_number}")
        elif header.response_flag == TN3270E_RSF_ALWAYS_RESPONSE:
            logger.debug(f"Received always response for sequence {header.seq_number}")

    def _handle_bind_image_message(self, header: TN3270EHeader, data: bytes) -> None:
        """Handle BIND-IMAGE messages."""
        logger.debug(f"Received BIND-IMAGE message: {data.hex()}")
        # BIND-IMAGE handling would be implemented here
        # This could update device capabilities, screen dimensions, etc.

    def _handle_request_message(self, header: TN3270EHeader, data: bytes) -> None:
        """Handle REQUEST messages."""
        logger.debug(f"Received REQUEST message: {data.hex()}")

    def _handle_response_message(self, header: TN3270EHeader, data: bytes) -> None:
        """Handle RESPONSE messages."""
        logger.debug(f"Received RESPONSE message: {data.hex()}")

    def _handle_3270_data_message(self, header: TN3270EHeader, data: bytes) -> None:
        """Handle 3270 data stream messages."""
        logger.debug(f"Received 3270 data message: {data.hex()}")

    def _handle_printer_status_message(
        self, header: TN3270EHeader, data: bytes
    ) -> None:
        """Handle printer status messages."""
        logger.debug(f"Received printer status message: {data.hex()}")

    def __repr__(self) -> str:
        """String representation of the printer session."""
        stats = self.get_job_statistics()
        return (
            f"PrinterSession(active={self.is_active}, "
            f"current_job={'Yes' if self.current_job else 'No'}, "
            f"completed_jobs={stats['completed_jobs']}, "
            f"total_pages={stats['total_pages']}, "
            f"total_bytes={stats['total_bytes']}, "
            f"errors={self.error_count}, "
            f"device_type={self.device_type})"
        )

    def get_session_info(self) -> Dict[str, Any]:
        """Get comprehensive session information."""
        with self.lock:
            stats = self.get_job_statistics()
            return {
                "is_active": self.is_active,
                "device_type": self.device_type,
                "current_job_id": self.current_job.job_id if self.current_job else None,
                "completed_jobs": stats["completed_jobs"],
                "total_pages": stats["total_pages"],
                "total_bytes": stats["total_bytes"],
                "error_count": self.error_count,
                "last_activity": self.last_activity,
                "tn3270e_functions": list(self.tn3270e_functions),
                "scs_handlers_count": len(self.scs_handlers),
            }

    def set_device_type(self, device_type: str) -> None:
        """Set the device type for the printer session."""
        with self.lock:
            self.device_type = device_type
            logger.info(f"Printer session device type set to: {device_type}")

    def add_tn3270e_function(self, function: int) -> None:
        """Add a supported TN3270E function."""
        with self.lock:
            self.tn3270e_functions.add(function)
            logger.debug(f"Added TN3270E function: 0x{function:02x}")

    def supports_tn3270e_function(self, function: int) -> bool:
        """Check if a TN3270E function is supported."""
        with self.lock:
            return function in self.tn3270e_functions

    def get_error_rate(self) -> float:
        """Get the current error rate."""
        with self.lock:
            total_operations = len(self.completed_jobs) + (1 if self.current_job else 0)
            if total_operations == 0:
                return 0.0
            return self.error_count / total_operations

    def is_healthy(self) -> bool:
        """Check if the session is healthy."""
        with self.lock:
            return (
                self.is_active
                and self.error_count <= self.max_errors
                and self.get_error_rate() < 0.1
            )
