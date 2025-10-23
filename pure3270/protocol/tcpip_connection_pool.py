"""
TCPIPConnectionPool for thread-safe connection pooling.

Provides connection lifecycle management, health monitoring, and
thread-safe access to printer session connections with automatic
cleanup and resource management.
"""

import asyncio
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Type

from ..utils.logging_utils import (
    log_connection_event,
    log_session_action,
    log_session_error,
)
from .tcpip_printer_session import PrinterSessionState, TCPIPPrinterSession

logger = logging.getLogger(__name__)


class ConnectionPoolConfig:
    """Configuration for connection pool behavior."""

    def __init__(
        self,
        max_connections: int = 10,
        max_connections_per_host: int = 2,
        connection_timeout: float = 30.0,
        idle_timeout: float = 300.0,  # 5 minutes
        health_check_interval: float = 60.0,  # 1 minute
        cleanup_interval: float = 120.0,  # 2 minutes
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize pool configuration.

        Args:
            max_connections: Maximum total connections in pool
            max_connections_per_host: Maximum connections per host
            connection_timeout: Connection establishment timeout
            idle_timeout: Idle connection cleanup timeout
            health_check_interval: Health check frequency
            cleanup_interval: Cleanup task frequency
            retry_attempts: Connection retry attempts
            retry_delay: Delay between retries
        """
        self.max_connections = max_connections
        self.max_connections_per_host = max_connections_per_host
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout
        self.health_check_interval = health_check_interval
        self.cleanup_interval = cleanup_interval
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay


class TCPIPConnectionPool:
    """
    Thread-safe connection pool for TCPIP printer sessions.

    Manages a pool of reusable connections with automatic lifecycle management,
    health monitoring, and thread-safe access patterns.
    """

    def __init__(self, config: Optional[ConnectionPoolConfig] = None):
        """
        Initialize connection pool.

        Args:
            config: Pool configuration (uses defaults if None)
        """
        self.config = config or ConnectionPoolConfig()

        # Thread safety
        self._lock = asyncio.Lock()
        self._thread_lock = threading.RLock()

        # Connection storage
        self._active_connections: Dict[str, List[TCPIPPrinterSession]] = {}
        self._idle_connections: Dict[str, List[TCPIPPrinterSession]] = {}
        self._all_connections: Set[TCPIPPrinterSession] = set()

        # Pool statistics
        self._total_created = 0
        self._total_destroyed = 0
        self._total_borrowed = 0
        self._total_returned = 0

        # Background tasks
        self._health_check_task: Optional[asyncio.Task[None]] = None
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._running = False

        # Event loop management
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        logger.info("TCPIPConnectionPool initialized")

    async def start(self) -> None:
        """Start the connection pool background tasks."""
        async with self._lock:
            if self._running:
                return

            self._running = True
            self._loop = asyncio.get_running_loop()

            # Start background tasks
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

            logger.info("Connection pool started")

    async def stop(self) -> None:
        """Stop the connection pool and cleanup all connections."""
        async with self._lock:
            if not self._running:
                return

            try:
                self._running = False

                # Cancel background tasks with proper cleanup using try-finally blocks
                try:
                    if self._health_check_task and not self._health_check_task.done():
                        self._health_check_task.cancel()
                        try:
                            await self._health_check_task
                        except (asyncio.CancelledError, Exception):
                            pass
                    if self._cleanup_task and not self._cleanup_task.done():
                        self._cleanup_task.cancel()
                        try:
                            await self._cleanup_task
                        except (asyncio.CancelledError, Exception):
                            pass
                finally:
                    # Ensure task references are cleared even if cancellation fails
                    try:
                        self._health_check_task = None
                    except Exception:
                        pass
                    try:
                        self._cleanup_task = None
                    except Exception:
                        pass

                # Close all connections with comprehensive try-finally blocks for resource cleanup
                close_tasks = []
                sessions_to_close = list(self._all_connections)

                try:
                    for session in sessions_to_close:
                        try:
                            close_tasks.append(self._force_close_session(session))
                        except Exception as e:
                            logger.debug(f"Error preparing session closure: {e}")

                    if close_tasks:
                        try:
                            await asyncio.gather(*close_tasks, return_exceptions=True)
                        except Exception as gather_error:
                            logger.debug(f"Error gathering close tasks: {gather_error}")
                finally:
                    # Always clear collections even if closure fails to prevent resource leaks
                    try:
                        self._active_connections.clear()
                    except Exception as e:
                        logger.debug(f"Error clearing active connections: {e}")
                    try:
                        self._idle_connections.clear()
                    except Exception as e:
                        logger.debug(f"Error clearing idle connections: {e}")
                    try:
                        self._all_connections.clear()
                    except Exception as e:
                        logger.debug(f"Error clearing all connections: {e}")

                logger.info("Connection pool stopped")

            except Exception as e:
                logger.error(f"[STOP] Error during pool stop operation: {e}")
                # Still clear collections on error to prevent resource leaks using nested try-finally blocks
                try:
                    try:
                        self._active_connections.clear()
                    except Exception:
                        pass
                    try:
                        self._idle_connections.clear()
                    except Exception:
                        pass
                    try:
                        self._all_connections.clear()
                    except Exception:
                        pass
                except Exception:
                    pass
                raise

    async def borrow_connection(
        self,
        host: str,
        port: int = 23,
        ssl_context: Optional[Any] = None,
        session_id: Optional[str] = None,
    ) -> TCPIPPrinterSession:
        """
        Borrow a connection from the pool.

        Returns an existing idle connection if available, otherwise creates a new one.

        Args:
            host: Target host
            port: Target port
            ssl_context: SSL context for connection
            session_id: Optional session identifier

        Returns:
            Active printer session

        Raises:
            RuntimeError: If pool limits exceeded or connection fails
        """
        async with self._lock:
            host_key = f"{host}:{port}"

            # Check pool limits
            total_active = sum(
                len(conns) for conns in self._active_connections.values()
            )
            if total_active >= self.config.max_connections:
                raise RuntimeError(
                    f"Pool limit exceeded: {total_active}/{self.config.max_connections}"
                )

            host_active = len(self._active_connections.get(host_key, []))
            if host_active >= self.config.max_connections_per_host:
                raise RuntimeError(
                    f"Host limit exceeded: {host_active}/{self.config.max_connections_per_host}"
                )

            # Try to get idle connection first
            idle_conns = self._idle_connections.get(host_key, [])
            if idle_conns:
                session = idle_conns.pop()
                if await self._is_connection_healthy(session):
                    # Move to active
                    self._active_connections.setdefault(host_key, []).append(session)
                    self._total_borrowed += 1
                    log_session_action(
                        logger, "borrow", f"reused idle connection {session.session_id}"
                    )
                    return session
                else:
                    # Connection unhealthy, destroy it
                    await self._destroy_connection(session)

            # Create new connection
            session = TCPIPPrinterSession(
                host=host,
                port=port,
                ssl_context=ssl_context,
                session_id=session_id,
                timeout=self.config.connection_timeout,
            )

            try:
                await session.connect()
                await session.activate()

                # Add to tracking
                self._active_connections.setdefault(host_key, []).append(session)
                self._all_connections.add(session)
                self._total_created += 1
                self._total_borrowed += 1

                log_connection_event(logger, "created", host, port)
                return session

            except Exception as e:
                log_session_error(logger, "borrow", e)
                await self._destroy_connection(session)
                raise

    async def return_connection(self, session: TCPIPPrinterSession) -> None:
        """
        Return a connection to the pool.

        If the connection is healthy, it becomes available for reuse.
        Otherwise, it's destroyed.

        Args:
            session: Session to return
        """
        async with self._lock:
            host_key = f"{session.host}:{session.port}"

            # Remove from active connections
            active_conns = self._active_connections.get(host_key, [])
            if session in active_conns:
                active_conns.remove(session)

            # Check if connection should be kept
            if await self._is_connection_healthy(session):
                # Return to idle pool
                self._idle_connections.setdefault(host_key, []).append(session)
                self._total_returned += 1
                log_session_action(
                    logger,
                    "return",
                    f"connection {session.session_id} returned to pool",
                )
            else:
                # Destroy unhealthy connection
                await self._destroy_connection(session)

    async def _health_check_loop(self) -> None:
        """Background task for periodic health checks."""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _cleanup_loop(self) -> None:
        """Background task for periodic cleanup of idle connections."""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._perform_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _perform_health_checks(self) -> None:
        """Perform health checks on idle connections."""
        async with self._lock:
            unhealthy_sessions = []

            for host_key, idle_conns in self._idle_connections.items():
                healthy_conns = []
                for session in idle_conns:
                    if await self._is_connection_healthy(session):
                        healthy_conns.append(session)
                    else:
                        unhealthy_sessions.append(session)

                # Update idle connections, keep only healthy ones
                self._idle_connections[host_key] = healthy_conns

            # Destroy unhealthy connections
            for session in unhealthy_sessions:
                await self._destroy_connection(session)

            if unhealthy_sessions:
                logger.info(
                    f"Health check removed {len(unhealthy_sessions)} unhealthy connections"
                )

    async def _perform_cleanup(self) -> None:
        """Clean up idle connections that have exceeded idle timeout."""
        async with self._lock:
            current_time = time.time()
            expired_sessions = []

            for host_key, idle_conns in self._idle_connections.items():
                active_conns = []
                for session in idle_conns:
                    if current_time - session.last_activity > self.config.idle_timeout:
                        expired_sessions.append(session)
                    else:
                        active_conns.append(session)

                # Update idle connections, keep only active ones
                self._idle_connections[host_key] = active_conns

            # Destroy expired connections
            for session in expired_sessions:
                await self._destroy_connection(session)

            if expired_sessions:
                logger.info(
                    f"Cleanup removed {len(expired_sessions)} expired idle connections"
                )

    async def _is_connection_healthy(self, session: TCPIPPrinterSession) -> bool:
        """
        Check if a connection is healthy.

        Args:
            session: Session to check

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Basic state check
            if session.state != PrinterSessionState.ACTIVE:
                return False

            # Check if underlying handler is still connected
            if session.handler and not session.handler.is_connected():
                return False

            # Check for excessive errors
            if session.error_count > 5:
                return False

            return True

        except Exception as e:
            logger.debug(f"Health check failed for session {session.session_id}: {e}")
            return False

    async def _destroy_connection(self, session: TCPIPPrinterSession) -> None:
        """Destroy a connection and remove from tracking."""
        try:
            await session.close()
        except Exception as e:
            logger.debug(f"Error closing session {session.session_id}: {e}")

        # Remove from all tracking
        host_key = f"{session.host}:{session.port}"

        for conn_list in [self._active_connections, self._idle_connections]:
            if host_key in conn_list and session in conn_list[host_key]:
                conn_list[host_key].remove(session)

        self._all_connections.discard(session)
        self._total_destroyed += 1

        logger.debug(f"Destroyed connection {session.session_id}")

    async def _force_close_session(self, session: TCPIPPrinterSession) -> None:
        """Force close a session without pool management."""
        try:
            await session.close()
        except Exception as e:
            logger.debug(f"Error force closing session {session.session_id}: {e}")

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics for monitoring."""
        total_active = sum(len(conns) for conns in self._active_connections.values())
        total_idle = sum(len(conns) for conns in self._idle_connections.values())

        return {
            "total_connections": len(self._all_connections),
            "active_connections": total_active,
            "idle_connections": total_idle,
            "max_connections": self.config.max_connections,
            "total_created": self._total_created,
            "total_destroyed": self._total_destroyed,
            "total_borrowed": self._total_borrowed,
            "total_returned": self._total_returned,
            "connections_by_host": {
                host: {
                    "active": len(self._active_connections.get(host, [])),
                    "idle": len(self._idle_connections.get(host, [])),
                }
                for host in set(self._active_connections.keys())
                | set(self._idle_connections.keys())
            },
        }

    async def __aenter__(self) -> "TCPIPConnectionPool":
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
