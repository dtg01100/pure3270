"""
TCPIPPrinterSessionManager for coordinating printer session operations.

Provides high-level interface for managing printer sessions, connection pooling,
and transparent TCPIP printer support with RFC compliance and error handling.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type

from ..utils.logging_utils import (
    log_connection_event,
    log_session_action,
    log_session_error,
)
from .tcpip_connection_pool import ConnectionPoolConfig, TCPIPConnectionPool
from .tcpip_printer_session import PrinterSessionState, TCPIPPrinterSession

logger = logging.getLogger(__name__)


class TCPIPPrinterSessionManager:
    """
    Core coordinator for TCPIP printer session management.

    Provides high-level interface for printer operations with automatic
    connection pooling, session lifecycle management, and transparent
    TCPIP printer support.
    """

    def __init__(
        self,
        pool_config: Optional[ConnectionPoolConfig] = None,
        default_timeout: float = 30.0,
    ):
        """
        Initialize the session manager.

        Args:
            pool_config: Connection pool configuration
            default_timeout: Default operation timeout
        """
        self.pool_config = pool_config or ConnectionPoolConfig()
        self.default_timeout = default_timeout

        # Core components
        self.connection_pool: Optional[TCPIPConnectionPool] = None

        # Session tracking
        self._active_sessions: Dict[str, TCPIPPrinterSession] = {}
        self._session_lock = asyncio.Lock()

        # Manager state
        self._started = False

        logger.info("TCPIPPrinterSessionManager initialized")

    async def start(self) -> None:
        """Start the session manager and connection pool."""
        if self._started:
            raise RuntimeError("Session manager already started")

        # Use existing injected pool if present (for testing), otherwise create one
        if not self.connection_pool:
            self.connection_pool = TCPIPConnectionPool(self.pool_config)

        await self.connection_pool.start()
        self._started = True

        logger.info("TCPIPPrinterSessionManager started")

    async def stop(self) -> None:
        """Stop the session manager and cleanup resources."""
        if not self._started:
            raise RuntimeError("Session manager not started")

        # Close all active sessions
        async with self._session_lock:
            close_tasks = []
            for session in self._active_sessions.values():
                close_tasks.append(self._close_session_safe(session))
            self._active_sessions.clear()

            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)

        # Stop connection pool
        if self.connection_pool:
            await self.connection_pool.stop()

        self._started = False
        logger.info("TCPIPPrinterSessionManager stopped")

    async def create_printer_session(
        self,
        host: str,
        port: int = 23,
        ssl_context: Optional[Any] = None,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """
        Create a new printer session.

        Args:
            host: Target host for printer connection
            port: Target port (default 23 for Telnet)
            ssl_context: SSL context for secure connections
            session_id: Optional unique identifier for this session
            timeout: Connection timeout (uses default if None)

        Returns:
            The created session's identifier

        Raises:
            RuntimeError: If manager not started or session creation fails
        """
        if not self._started or not self.connection_pool:
            raise RuntimeError("Session manager not started")

        connection_timeout = timeout or self.default_timeout

        try:
            # Borrow connection from pool (may return a connection token/tuple)
            await asyncio.wait_for(
                self.connection_pool.borrow_connection(host, port),
                timeout=connection_timeout,
            )

            # Instantiate a printer session (constructor patched in tests)
            session = TCPIPPrinterSession(
                host=host,
                port=port,
                ssl_context=ssl_context,
                session_id=session_id,
                timeout=connection_timeout,
            )

            # Track active session
            async with self._session_lock:
                self._active_sessions[session.session_id] = session

            log_session_action(
                logger, "create", f"session {session.session_id} for {host}:{port}"
            )
            return session.session_id

        except asyncio.TimeoutError as e:
            log_session_error(logger, "create_printer_session", e)
            raise RuntimeError("Failed to create printer session: timeout") from e
        except Exception as e:
            log_session_error(logger, "create_printer_session", e)
            raise RuntimeError(f"Failed to create printer session: {e}") from e

    async def get_printer_session(self, session_id: str) -> TCPIPPrinterSession:
        """
        Get an existing printer session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Active session

        Raises:
            RuntimeError: If session not found or inactive
        """
        async with self._session_lock:
            session = self._active_sessions.get(session_id)
            if session is None:
                raise RuntimeError(f"Session {session_id} not found")
            if not session.is_active:
                raise RuntimeError(f"Session {session_id} is not active")
            return session

    async def send_print_job(
        self, session_id: str, print_data: bytes, timeout: Optional[float] = None
    ) -> None:
        """
        Send print data through an existing session.

        Args:
            session_id: Session identifier
            print_data: SCS print data to send
            timeout: Send timeout (uses default if None)

        Raises:
            RuntimeError: If session not found or not active
            ConnectionError: If send fails
        """
        session = await self.get_printer_session(session_id)

        send_timeout = timeout or self.default_timeout

        try:
            await asyncio.wait_for(
                session.send_print_data(print_data), timeout=send_timeout
            )
            log_session_action(
                logger,
                "send_print_job",
                f"sent {len(print_data)} bytes via {session_id}",
            )

        except Exception as e:
            log_session_error(logger, "send_print_job", e)
            # Mark session as error state
            await self._handle_session_error(session, e)
            raise RuntimeError("Failed to send print job") from e

    async def send_printer_status(
        self, session_id: str, status_code: int, timeout: Optional[float] = None
    ) -> None:
        """
        Send printer status update through a session.

        Args:
            session_id: Session identifier
            status_code: Status code to send
            timeout: Send timeout (uses default if None)

        Raises:
            RuntimeError: If session not found or not active
        """
        session = await self.get_printer_session(session_id)

        send_timeout = timeout or self.default_timeout

        try:
            await asyncio.wait_for(
                session.send_printer_status(status_code), timeout=send_timeout
            )
            log_session_action(
                logger,
                "send_printer_status",
                f"status 0x{status_code:02x} via {session_id}",
            )

        except Exception as e:
            log_session_error(logger, "send_printer_status", e)
            await self._handle_session_error(session, e)
            raise

    async def receive_printer_data(
        self, session_id: str, timeout: Optional[float] = None
    ) -> bytes:
        """
        Receive data from a printer session.

        Args:
            session_id: Session identifier
            timeout: Receive timeout (uses default if None)

        Returns:
            Received data bytes

        Raises:
            RuntimeError: If session not found or not active
            TimeoutError: If receive times out
        """
        session = await self.get_printer_session(session_id)

        receive_timeout = timeout or self.default_timeout

        try:
            data = await asyncio.wait_for(
                session.receive_data(receive_timeout), timeout=receive_timeout
            )
            logger.debug(f"Received {len(data)} bytes from session {session_id}")
            return data

        except Exception as e:
            log_session_error(logger, "receive_printer_data", e)
            await self._handle_session_error(session, e)
            raise

    async def close_printer_session(self, session_id: str) -> None:
        """
        Close a printer session and return connection to pool.

        Args:
            session_id: Session identifier to close

        Raises:
            RuntimeError: If session not found
        """
        async with self._session_lock:
            session = self._active_sessions.get(session_id)
            if not session:
                raise RuntimeError(f"Session {session_id} not found")

            # Remove from active tracking
            del self._active_sessions[session_id]

        try:
            # Close the session first
            await self._close_session_safe(session)

            # Return connection to pool (handles cleanup)
            if self.connection_pool:
                await self.connection_pool.return_connection(session)

            log_connection_event(logger, "closed", session.host, session.port)

        except Exception as e:
            log_session_error(logger, "close_printer_session", e)
            # Force cleanup on error
            await self._close_session_safe(session)

    async def close_all_sessions(self) -> None:
        """Close all active printer sessions."""
        async with self._session_lock:
            session_ids = list(self._active_sessions.keys())

        close_tasks = []
        for session_id in session_ids:
            close_tasks.append(self.close_printer_session(session_id))

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        logger.info("All printer sessions closed")

    async def _handle_session_error(
        self, session: TCPIPPrinterSession, error: Exception
    ) -> None:
        """
        Handle session error by marking session as error state.

        Args:
            session: Session that encountered error
            error: The error that occurred
        """
        try:
            # Mark session as error state
            await session._set_state(PrinterSessionState.ERROR, f"error: {error}")

            # Remove from active sessions
            async with self._session_lock:
                self._active_sessions.pop(session.session_id, None)

            # Return to pool for cleanup
            if self.connection_pool:
                await self.connection_pool.return_connection(session)

        except Exception as cleanup_error:
            logger.error(f"Error during session error handling: {cleanup_error}")

    async def _close_session_safe(self, session: TCPIPPrinterSession) -> None:
        """Safely close a session with error handling."""
        try:
            await session.close()
        except Exception as e:
            logger.debug(f"Error closing session {session.session_id}: {e}")

    def get_active_sessions(self) -> List[str]:
        """Get identifiers for all active sessions."""
        return list(self._active_sessions.keys())

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if self.connection_pool:
            return self.connection_pool.get_pool_stats()
        return {}

    def get_manager_stats(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        return {
            "active_sessions": len(self._active_sessions),
            "started": self._started,
            "pool_stats": self.get_pool_stats(),
            "session_details": self.get_active_sessions(),
        }

    async def __aenter__(self) -> "TCPIPPrinterSessionManager":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit."""
        await self.stop()
