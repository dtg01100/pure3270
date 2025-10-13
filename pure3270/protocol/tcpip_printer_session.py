"""
TCPIPPrinterSession for transparent TCPIP printer session support.

Provides individual printer session management with state tracking,
error handling, and integration with TN3270Handler for RFC compliance.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, Optional

from ..session_manager import SessionManager
from ..utils.logging_utils import (
    log_connection_event,
    log_session_action,
    log_session_error,
)
from .tn3270_handler import TN3270Handler

logger = logging.getLogger(__name__)


class PrinterSessionState(Enum):
    """States for printer session lifecycle."""

    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    NEGOTIATING = "NEGOTIATING"
    CONNECTED = "CONNECTED"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    CLOSING = "CLOSING"


class TCPIPPrinterSession:
    """
    Individual printer session wrapper for TCPIP printer connections.

    Manages session state, connection lifecycle, and provides high-level
    interface for printer operations with proper error handling and logging.
    """

    def __init__(
        self,
        host: str,
        port: int = 23,
        ssl_context: Optional[Any] = None,
        session_id: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize printer session.

        Args:
            host: Target host for printer connection
            port: Target port (default 23 for Telnet)
            ssl_context: SSL context for secure connections
            session_id: Optional unique identifier for this session
            timeout: Connection and operation timeout in seconds
        """
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.session_id = session_id or f"printer_{id(self)}"
        self.timeout = timeout

        # Core components
        self.session_manager: Optional[SessionManager] = None
        self.handler: Optional[TN3270Handler] = None

        # State management
        self.state = PrinterSessionState.DISCONNECTED
        self.state_lock = asyncio.Lock()
        self.last_activity = time.time()
        self.error_count = 0
        self.created_at = time.time()

        # Session metadata
        self.lu_name: Optional[str] = None
        self.device_type: Optional[str] = None
        self.printer_status: Optional[int] = None

        logger.info(
            f"TCPIPPrinterSession {self.session_id} initialized for {host}:{port}"
        )

    async def connect(self) -> None:
        """
        Establish printer session connection.

        Performs full connection sequence: socket setup, negotiation,
        and printer session initialization.

        Raises:
            ConnectionError: If connection fails
            TimeoutError: If connection times out
            NegotiationError: If TN3270E negotiation fails
        """
        async with self.state_lock:
            if self.state != PrinterSessionState.DISCONNECTED:
                logger.warning(
                    f"Session {self.session_id} already in state {self.state}"
                )
                return

            try:
                await self._set_state(
                    PrinterSessionState.CONNECTING, "starting connection"
                )

                # Create session manager
                self.session_manager = SessionManager(
                    host=self.host, port=self.port, ssl_context=self.ssl_context
                )

                # Setup connection
                await asyncio.wait_for(
                    self.session_manager.setup_connection(), timeout=self.timeout
                )

                # Create handler for printer session
                self.handler = TN3270Handler(
                    reader=self.session_manager.reader,
                    writer=self.session_manager.writer,
                    host=self.host,
                    port=self.port,
                    ssl_context=self.ssl_context,
                    is_printer_session=True,
                    force_mode="tn3270e",  # Printer sessions require TN3270E
                    allow_fallback=True,
                )

                await self._set_state(
                    PrinterSessionState.NEGOTIATING, "starting negotiation"
                )

                # Perform negotiation
                await asyncio.wait_for(self.handler.connect(), timeout=self.timeout)

                # Verify printer session
                if not self.handler.is_printer_session:
                    raise ValueError("Handler not configured as printer session")

                await self._set_state(
                    PrinterSessionState.CONNECTED, "connection established"
                )

                # Update metadata
                self.lu_name = self.handler.lu_name
                self.device_type = self.handler.negotiator.negotiated_device_type
                self.printer_status = self.handler.printer_status

                log_connection_event(logger, "established", self.host, self.port)

            except Exception as e:
                await self._set_state(
                    PrinterSessionState.ERROR, f"connection failed: {e}"
                )
                log_session_error(logger, "connect", e)
                await self._cleanup_on_error()
                raise

    async def activate(self) -> None:
        """
        Activate the printer session for data transmission.

        Transitions from connected to active state, ready for print jobs.

        Raises:
            RuntimeError: If session not in connected state
        """
        async with self.state_lock:
            if self.state != PrinterSessionState.CONNECTED:
                raise RuntimeError(f"Cannot activate session in state {self.state}")

            await self._set_state(PrinterSessionState.ACTIVE, "session activated")
            log_session_action(logger, "activate", f"session {self.session_id}")

    async def send_print_data(self, data: bytes) -> None:
        """
        Send print data through the session.

        Args:
            data: SCS print data to send

        Raises:
            RuntimeError: If session not active
            ConnectionError: If send fails
        """
        if self.state != PrinterSessionState.ACTIVE:
            raise RuntimeError(f"Cannot send data in state {self.state}")

        if not self.handler:
            raise RuntimeError("No handler available")

        try:
            await asyncio.wait_for(
                self.handler.send_scs_data(data), timeout=self.timeout
            )
            self.last_activity = time.time()
            logger.debug(f"Sent {len(data)} bytes of print data")

        except Exception as e:
            self.error_count += 1
            log_session_error(logger, "send_print_data", e)
            await self._set_state(PrinterSessionState.ERROR, f"send failed: {e}")
            raise

    async def send_printer_status(self, status_code: int) -> None:
        """
        Send printer status update.

        Args:
            status_code: Status code to send

        Raises:
            RuntimeError: If session not active
        """
        if self.state != PrinterSessionState.ACTIVE:
            raise RuntimeError(f"Cannot send status in state {self.state}")

        if not self.handler:
            raise RuntimeError("No handler available")

        try:
            await self.handler.send_printer_status_sf(status_code)
            self.printer_status = status_code
            self.last_activity = time.time()
            logger.debug(f"Sent printer status: 0x{status_code:02x}")

        except Exception as e:
            self.error_count += 1
            log_session_error(logger, "send_printer_status", e)
            raise

    async def receive_data(self, timeout: Optional[float] = None) -> bytes:
        """
        Receive data from the printer session.

        Args:
            timeout: Receive timeout (uses session default if None)

        Returns:
            Received data bytes

        Raises:
            RuntimeError: If session not active
            TimeoutError: If receive times out
        """
        if self.state != PrinterSessionState.ACTIVE:
            raise RuntimeError(f"Cannot receive data in state {self.state}")

        if not self.handler:
            raise RuntimeError("No handler available")

        receive_timeout = timeout or self.timeout

        try:
            data = await asyncio.wait_for(
                self.handler.receive_data(receive_timeout), timeout=receive_timeout
            )
            self.last_activity = time.time()
            return data

        except Exception as e:
            self.error_count += 1
            log_session_error(logger, "receive_data", e)
            raise

    async def close(self) -> None:
        """
        Close the printer session gracefully.

        Performs cleanup and state transition to disconnected.
        """
        async with self.state_lock:
            if self.state in [
                PrinterSessionState.DISCONNECTED,
                PrinterSessionState.CLOSING,
            ]:
                return

            try:
                await self._set_state(PrinterSessionState.CLOSING, "closing session")

                if self.handler:
                    await self.handler.close()

                if self.session_manager:
                    await self.session_manager.teardown_connection()

                await self._set_state(
                    PrinterSessionState.DISCONNECTED, "session closed"
                )
                log_connection_event(logger, "closed", self.host, self.port)

            except Exception as e:
                logger.error(f"Error during session close: {e}")
                await self._set_state(PrinterSessionState.ERROR, f"close failed: {e}")
                raise

    async def _set_state(self, new_state: PrinterSessionState, reason: str) -> None:
        """Set session state with logging."""
        old_state = self.state
        self.state = new_state
        self.last_activity = time.time()

        logger.info(
            f"Session {self.session_id} state: {old_state.value} -> {new_state.value} ({reason})"
        )

    async def _cleanup_on_error(self) -> None:
        """Cleanup resources on error."""
        try:
            if self.handler:
                await self.handler.close()
        except Exception:
            pass

        try:
            if self.session_manager:
                await self.session_manager.teardown_connection()
        except Exception:
            pass

    @property
    def is_connected(self) -> bool:
        """Check if session is connected and active."""
        return self.state in [PrinterSessionState.CONNECTED, PrinterSessionState.ACTIVE]

    @property
    def is_active(self) -> bool:
        """Check if session is active for data transmission."""
        return self.state == PrinterSessionState.ACTIVE

    def get_session_info(self) -> Dict[str, Any]:
        """Get session information for monitoring/debugging."""
        return {
            "session_id": self.session_id,
            "host": self.host,
            "port": self.port,
            "state": self.state.value,
            "lu_name": self.lu_name,
            "device_type": self.device_type,
            "printer_status": self.printer_status,
            "error_count": self.error_count,
            "last_activity": self.last_activity,
            "created_at": self.created_at,
            "uptime": time.time() - self.created_at,
        }
