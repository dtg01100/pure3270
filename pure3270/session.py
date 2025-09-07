"""Main Session class integrating emulation and protocol layers."""

import logging
import asyncio
from typing import Optional, List, Sequence
from contextlib import asynccontextmanager

from .emulation.screen_buffer import ScreenBuffer
from .protocol.tn3270_handler import TN3270Handler, sync_connect, sync_send, sync_receive, sync_close
from .protocol.data_stream import DataStreamParser, DataStreamSender, ParseError
from .protocol.ssl_wrapper import SSLWrapper, SSLError


logger = logging.getLogger(__name__)


class Pure3270Error(Exception):
    """Base exception for Pure3270 errors."""
    pass


class SessionError(Pure3270Error):
    """Error in session operations."""
    pass


class AsyncSession:
    """Asynchronous 3270 session handler."""

    def __init__(self, rows: int = 24, cols: int = 80):
        """
        Initialize the AsyncSession.

        :param rows: Screen rows (default 24).
        :param cols: Screen columns (default 80).
        """
        self.screen = ScreenBuffer(rows, cols)
        self.parser = DataStreamParser(self.screen)
        self.sender = DataStreamSender()
        self.handler: Optional[TN3270Handler] = None
        self._connected = False

    async def connect(self, host: str, port: int = 23, ssl: bool = False) -> None:
        """
        Connect to the TN3270 host.

        :param host: Hostname or IP.
        :param port: Port (default 23).
        :param ssl: Use SSL/TLS if True.
        :raises SessionError: If connection fails.
        """
        try:
            ssl_context = None
            if ssl:
                wrapper = SSLWrapper(verify=True)
                ssl_context = wrapper.get_context()
                logger.info(f"SSL enabled for {host}:{port}")

            self.handler = TN3270Handler(host, port, ssl_context)
            await self.handler.connect()
            self._connected = True
            logger.info(f"Connected to {host}:{port}")
        except (ConnectionError, NegotiationError, SSLError) as e:
            raise SessionError(f"Connection failed: {e}")

    async def send(self, command: str) -> None:
        """
        Send a command or key to the host.

        :param command: Command or key (e.g., "key Enter", "String(hello)").
        :raises SessionError: If send fails.
        """
        if not self._connected or not self.handler:
            raise SessionError("Not connected")

        try:
            if command.startswith("key "):
                key = command[4:]
                # Map key to AID (simplified)
                aid_map = {"Enter": 0x7D, "PF3": 0xF1, "Clear": 0x6D}
                aid = aid_map.get(key, 0x7D)
                data = self.sender.build_key_press(aid)
            elif command.startswith("String("):
                text = command[7:-1]
                # Build data stream for string input (simplified)
                data = self.sender.build_write(self.screen.buffer[:])  # Placeholder
            else:
                # Assume AID for unknown
                data = self.sender.build_key_press(0x7D)

            await self.handler.send_data(data)
            logger.debug(f"Sent command: {command}")
        except ProtocolError as e:
            raise SessionError(f"Send failed: {e}")

    async def read(self) -> str:
        """
        Read the current screen content.

        :return: Screen text as string.
        :raises SessionError: If read fails.
        """
        if not self._connected or not self.handler:
            raise SessionError("Not connected")

        try:
            data = await self.handler.receive_data()
            self.parser.parse(data)
            text = self.screen.to_text()
            logger.debug("Screen read successfully")
            return text
        except ParseError as e:
            raise SessionError(f"Parse failed: {e}")

    async def macro(self, sequence: Sequence[str]) -> None:
        """
        Execute a macro sequence of commands.

        :param sequence: List of commands.
        """
        for cmd in sequence:
            await self.send(cmd)
            await asyncio.sleep(0.1)  # Small delay between commands

    async def close(self) -> None:
        """Close the session."""
        if self.handler:
            await self.handler.close()
            self._connected = False
            logger.info("Session closed")

    @property
    def connected(self) -> bool:
        """Check if connected."""
        return self._connected

    @asynccontextmanager
    async def managed(self):
        """Context manager for the session."""
        if not self._connected:
            raise SessionError("Must connect before using context manager")
        try:
            yield self
        finally:
            await self.close()


# Synchronous wrappers
class Session:
    """Synchronous 3270 session handler (wraps AsyncSession)."""

    def __init__(self, rows: int = 24, cols: int = 80):
        """
        Initialize the Session.

        :param rows: Screen rows (default 24).
        :param cols: Screen columns (default 80).
        """
        self._async_session = AsyncSession(rows, cols)

    def connect(self, host: str, port: int = 23, ssl: bool = False) -> None:
        """
        Connect to the TN3270 host (sync).

        :param host: Hostname or IP.
        :param port: Port (default 23).
        :param ssl: Use SSL/TLS if True.
        :raises SessionError: If connection fails.
        """
        try:
            sync_connect(self._async_session.handler)  # Note: handler needs to be set first, but use asyncio.run
            asyncio.run(self._async_session.connect(host, port, ssl))
            self._async_session._connected = True
        except Exception as e:
            raise SessionError(f"Connection failed: {e}")

    def send(self, command: str) -> None:
        """
        Send a command or key (sync).

        :param command: Command or key.
        :raises SessionError: If send fails.
        """
        asyncio.run(self._async_session.send(command))

    def read(self) -> str:
        """
        Read the current screen content (sync).

        :return: Screen text.
        :raises SessionError: If read fails.
        """
        return asyncio.run(self._async_session.read())

    def macro(self, sequence: Sequence[str]) -> None:
        """
        Execute a macro sequence (sync).

        :param sequence: List of commands.
        """
        asyncio.run(self._async_session.macro(sequence))

    def close(self) -> None:
        """Close the session (sync)."""
        asyncio.run(self._async_session.close())

    @property
    def connected(self) -> bool:
        """Check if connected."""
        return self._async_session.connected

    def __enter__(self):
        """Sync context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()


# Logging setup (basic)
def setup_logging(level: str = "INFO"):
    """Setup logging for the library."""
    logging.basicConfig(level=level)
    logging.getLogger("pure3270").setLevel(level)