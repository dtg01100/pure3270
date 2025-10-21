"""
DataFlowController for transparent TCPIP printer session routing.

This module provides the DataFlowController class that coordinates print job detection,
data routing, and session management between main TN3270 sessions and printer sessions.
It enables transparent TCPIP printer support by automatically detecting print jobs in
main session data streams and routing them to appropriate printer sessions.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logging_utils import (
    log_data_processing,
    log_session_action,
    log_session_error,
)
from .exceptions import ProtocolError
from .print_job_detector import PrintJobDetector
from .protocol_translator import ProtocolTranslator
from .tcpip_printer_session_manager import TCPIPPrinterSessionManager
from .tn3270e_header import TN3270EHeader

logger = logging.getLogger(__name__)


@dataclass
class DataFlowStats:
    """Statistics for data flow operations."""

    total_bytes_processed: int = 0
    print_jobs_detected: int = 0
    print_jobs_routed: int = 0
    active_printer_sessions: int = 0
    errors_encountered: int = 0


class DataFlowController:
    """
    Coordinates transparent routing of print jobs between main sessions and printer sessions.

    This class serves as the central coordinator for transparent TCPIP printer support,
    automatically detecting print jobs in main session data streams and routing them
    to printer sessions without requiring application intervention.

    The controller integrates with:
    - PrintJobDetector: For detecting print jobs in data streams
    - ProtocolTranslator: For translating between main and printer session protocols
    - TCPIPPrinterSessionManager: For managing printer session lifecycle and data transmission

    Key Features:
    - Automatic print job detection and extraction
    - Transparent protocol translation
    - Session lifecycle management
    - Thread-safe async operations
    - Comprehensive error handling and logging
    """

    def __init__(
        self,
        session_manager: TCPIPPrinterSessionManager,
        job_detector: Optional[PrintJobDetector] = None,
        protocol_translator: Optional[ProtocolTranslator] = None,
    ):
        """
        Initialize the DataFlowController.

        Args:
            session_manager: TCPIPPrinterSessionManager for printer session operations
            job_detector: PrintJobDetector for detecting print jobs (created if None)
            protocol_translator: ProtocolTranslator for protocol conversion (created if None)
        """
        self.session_manager = session_manager
        self.job_detector = job_detector or PrintJobDetector()
        self.protocol_translator = protocol_translator or ProtocolTranslator()

        # Flow state tracking
        self._active_flows: Dict[str, Dict[str, Any]] = {}
        self._flow_lock = asyncio.Lock()

        # Statistics
        self.stats = DataFlowStats()

        # Controller state
        self._started = False

        logger.info("DataFlowController initialized")

    async def start(self) -> None:
        """Start the data flow controller."""
        if self._started:
            return

        # Start the session manager if not already started
        await self.session_manager.start()
        self._started = True

        logger.info("DataFlowController started")

    async def stop(self) -> None:
        """Stop the data flow controller and cleanup resources."""
        if not self._started:
            return

        # Close all active flows
        async with self._flow_lock:
            flow_ids = list(self._active_flows.keys())

        close_tasks = []
        for flow_id in flow_ids:
            close_tasks.append(self._close_flow(flow_id))

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        # Stop session manager
        await self.session_manager.stop()
        self._started = False

        logger.info("DataFlowController stopped")

    async def process_main_session_data(
        self,
        data: bytes,
        header: Optional[TN3270EHeader] = None,
        main_session_id: str = "main",
        printer_host: Optional[str] = None,
        printer_port: int = 23,
    ) -> Tuple[bytes, Optional[TN3270EHeader]]:
        """
        Process data from main session, detecting and routing print jobs transparently.

        This is the main entry point for data processing. The method analyzes incoming
        data from the main session, detects print jobs, and routes print data to
        printer sessions while returning non-print data to the main session.

        Args:
            data: Raw data from main session
            header: Optional TN3270E header associated with the data
            main_session_id: Identifier for the main session (for flow tracking)
            printer_host: Target printer host (if not provided, uses default routing)
            printer_port: Target printer port (default 23)

        Returns:
            Tuple of (main_session_data, main_session_header) - data that should
            continue to the main session (print data is extracted and routed separately)

        Raises:
            RuntimeError: If controller not started
        """
        if not self._started:
            raise RuntimeError("DataFlowController not started")

        self.stats.total_bytes_processed += len(data)
        log_data_processing(
            logger,
            "processing main session data",
            f"{len(data)} bytes from session {main_session_id}",
        )

        try:
            # Detect print jobs in the data
            print_job_detected = self.job_detector.detect_print_job(data, header)

            if print_job_detected:
                self.stats.print_jobs_detected += 1
                logger.debug(f"Print job detected in session {main_session_id}")

                # Extract print data from main session data
                main_data, print_data = self.job_detector.extract_print_data(
                    data, header
                )

                if print_data:
                    # Route print data to printer session
                    await self._route_print_data(
                        print_data, header, main_session_id, printer_host, printer_port
                    )

                # Return remaining main session data
                return main_data, header
            else:
                # No print job detected, return all data to main session
                return data, header

        except Exception as e:
            self.stats.errors_encountered += 1
            log_session_error(logger, "process_main_session_data", e)
            raise ProtocolError(
                "Failed to process main session data", original_exception=e
            )

    async def _route_print_data(
        self,
        print_data: bytes,
        header: Optional[TN3270EHeader],
        main_session_id: str,
        printer_host: Optional[str],
        printer_port: int,
    ) -> None:
        """
        Route print data to an appropriate printer session.

        Args:
            print_data: The print data to route
            header: Original TN3270E header
            main_session_id: Source main session identifier
            printer_host: Target printer host
            printer_port: Target printer port
        """
        flow_id = f"{main_session_id}_printer"

        try:
            async with self._flow_lock:
                flow_info = self._active_flows.get(flow_id)
                if not flow_info:
                    # Create new flow for this session
                    flow_info = await self._create_printer_flow(
                        flow_id, main_session_id, printer_host, printer_port
                    )
                    self._active_flows[flow_id] = flow_info

            # Get printer session ID from flow
            printer_session_id = flow_info["printer_session_id"]

            # Translate data to printer session format
            translated_header, translated_data = (
                self.protocol_translator.translate_to_printer_session(
                    print_data, header, session_type="tn3270e"
                )
            )

            # Send data through printer session
            await self.session_manager.send_print_job(
                printer_session_id, translated_data
            )

            self.stats.print_jobs_routed += 1
            log_session_action(
                logger,
                "route_print_data",
                f"routed {len(print_data)} bytes via {printer_session_id}",
            )

        except Exception as e:
            self.stats.errors_encountered += 1
            log_session_error(logger, "_route_print_data", e)
            # Cleanup flow on error
            await self._close_flow(flow_id)
            raise ProtocolError("Failed to route print data", original_exception=e)

    async def _create_printer_flow(
        self,
        flow_id: str,
        main_session_id: str,
        printer_host: Optional[str],
        printer_port: int,
    ) -> Dict[str, Any]:
        """
        Create a new printer flow for routing print jobs.

        Args:
            flow_id: Unique flow identifier
            main_session_id: Source main session ID
            printer_host: Target printer host
            printer_port: Target printer port

        Returns:
            Flow information dictionary

        Raises:
            RuntimeError: If printer session creation fails
        """
        if not printer_host:
            raise ValueError("Printer host must be specified for print job routing")

        # Create printer session
        printer_session = await self.session_manager.create_printer_session(
            host=printer_host, port=printer_port, session_id=f"{flow_id}_session"
        )

        # Activate printer session in translator
        self.protocol_translator.activate_printer_session("tn3270e")

        flow_info = {
            "flow_id": flow_id,
            "main_session_id": main_session_id,
            "printer_session_id": printer_session.session_id,
            "printer_host": printer_host,
            "printer_port": printer_port,
            "created_at": asyncio.get_event_loop().time(),
        }

        self.stats.active_printer_sessions += 1
        log_session_action(
            logger,
            "create_printer_flow",
            f"flow {flow_id} -> {printer_session.session_id}",
        )

        return flow_info

    async def _close_flow(self, flow_id: str) -> None:
        """
        Close a printer flow and cleanup associated resources.

        Args:
            flow_id: Flow identifier to close
        """
        async with self._flow_lock:
            flow_info = self._active_flows.pop(flow_id, None)

        if flow_info:
            try:
                printer_session_id = flow_info["printer_session_id"]

                # Send end-of-job if translator is active
                if self.protocol_translator.is_printer_session_active():
                    eoj_header, eoj_data = (
                        self.protocol_translator.handle_print_job_end()
                    )
                    if eoj_data:
                        await self.session_manager.send_print_job(
                            printer_session_id, eoj_data
                        )

                # Close printer session
                await self.session_manager.close_printer_session(printer_session_id)

                # Deactivate printer session in translator
                self.protocol_translator.deactivate_printer_session()

                self.stats.active_printer_sessions -= 1
                log_session_action(logger, "close_flow", f"closed flow {flow_id}")

            except Exception as e:
                log_session_error(logger, "_close_flow", e)
                raise ProtocolError("Failed to close flow", original_exception=e)

    async def handle_print_job_completion(self, main_session_id: str) -> None:
        """
        Handle completion of a print job and cleanup associated flow.

        Args:
            main_session_id: Main session identifier
        """
        flow_id = f"{main_session_id}_printer"
        await self._close_flow(flow_id)

    def get_flow_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about data flow operations."""
        return {
            "controller_stats": {
                "started": self._started,
                "active_flows": len(self._active_flows),
            },
            "data_flow_stats": {
                "total_bytes_processed": self.stats.total_bytes_processed,
                "print_jobs_detected": self.stats.print_jobs_detected,
                "print_jobs_routed": self.stats.print_jobs_routed,
                "active_printer_sessions": self.stats.active_printer_sessions,
                "errors_encountered": self.stats.errors_encountered,
            },
            "session_manager_stats": self.session_manager.get_manager_stats(),
            "active_flows": list(self._active_flows.keys()),
        }

    def get_active_flows(self) -> List[Dict[str, Any]]:
        """Get information about all active flows."""
        return list(self._active_flows.values())

    async def __aenter__(self) -> "DataFlowController":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit."""
        await self.stop()
