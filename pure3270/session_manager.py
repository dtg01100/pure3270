"""
SessionManager for pure3270, handling connection setup, teardown, and negotiation.
"""

import asyncio
import inspect
import logging
from asyncio import StreamReader, StreamWriter
from contextlib import suppress
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

    async def perform_telnet_negotiation(self, negotiator: Any) -> None:
        """Perform Telnet negotiation (TTYPE, BINARY, etc.)."""
        if not hasattr(negotiator, "negotiate"):
            return

        # Send initial negotiation
        negotiate_fn = negotiator.negotiate
        try:
            result = negotiate_fn()
        except TypeError:
            # Not callable (could be Mock without spec) -> nothing to do
            return
        if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
            await result
        # else synchronous -> already executed

        # Now read and process server responses
        if hasattr(negotiator, 'handler') and self.reader:
            handler = negotiator.handler
            if hasattr(handler, '_process_telnet_stream'):
                try:
                    # Read server responses with timeout
                    data = await asyncio.wait_for(self.reader.read(4096), timeout=3.0)
                    if data:
                        logger.info(f"[TELNET] Processing server response: {data.hex()}")
                        # Process through handler's telnet stream processor
                        processed = handler._process_telnet_stream(data)
                        if inspect.isawaitable(processed):
                            await processed
                except asyncio.TimeoutError:
                    logger.info("[TELNET] No server response within timeout - continuing")
                except Exception as e:
                    logger.warning(f"[TELNET] Error processing server response: {e}")
        else:
            logger.debug("[TELNET] No handler available for processing server responses")

    async def perform_tn3270_negotiation(
        self, negotiator: Any, timeout: Optional[float] = None
    ) -> None:
        """Perform TN3270 negotiation using the handler's method if available."""
        # Prefer the handler implementation when available (it manages a reader loop)
        target = None
        if getattr(negotiator, "handler", None) and hasattr(
            negotiator.handler, "_negotiate_tn3270"
        ):
            target = negotiator.handler._negotiate_tn3270
        elif hasattr(negotiator, "_negotiate_tn3270"):
            target = negotiator._negotiate_tn3270
        if target is None:
            return
        try:
            result = target(timeout=timeout)
        except TypeError:
            # If target is a Mock without a spec that rejects parameters, try without
            try:
                result = target()
            except Exception:
                return
        # Await only if it's awaitable (AsyncMock, coroutine, Future, etc.)
        if inspect.isawaitable(result):
            with suppress(asyncio.CancelledError):
                await result
