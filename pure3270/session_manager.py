"""
SessionManager for pure3270, handling connection setup, teardown, and negotiation.
"""

import asyncio
import logging
from asyncio import StreamReader, StreamWriter
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Shared manager for connection setup, teardown, and protocol negotiation calls.
    Handles socket creation, state management, and common negotiation sequences.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 23,
        ssl_context: Optional[Any] = None,
    ):
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.reader: Optional[StreamReader] = None
        self.writer: Optional[StreamWriter] = None
        self.connected: bool = False

    async def setup_connection(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        ssl_context: Optional[Any] = None,
    ) -> None:
        """
        Establish the socket connection.

        Overrides host/port/ssl if provided.
        """
        if host is not None:
            self.host = host
        if port is not None:
            self.port = port
        if ssl_context is not None:
            self.ssl_context = ssl_context
        if not self.host:
            raise ValueError(
                "Host must be provided either at initialization or in setup_connection call."
            )
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port, ssl=self.ssl_context
            )
        except Exception as e:
            raise ConnectionError(f"Connection failed: {str(e)}") from e
        self.connected = True

    async def teardown_connection(self) -> None:
        """Close the socket connection and reset state."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None
        self.reader = None
        self.connected = False

    async def perform_telnet_negotiation(self, negotiator) -> None:
        """Perform Telnet negotiation (TTYPE, BINARY, etc.)."""
        await negotiator.negotiate()

    async def perform_tn3270_negotiation(
        self, negotiator, timeout: Optional[float] = None
    ) -> None:
        """Perform TN3270 negotiation using the handler's method if available."""
        if negotiator.handler and hasattr(negotiator.handler, "_negotiate_tn3270"):
            await negotiator.handler._negotiate_tn3270(timeout=timeout)
        else:
            await negotiator._negotiate_tn3270(timeout=timeout)
