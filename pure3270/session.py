"""Main Session class integrating emulation and protocol layers."""

import logging
import asyncio
from typing import Optional, Sequence
from contextlib import asynccontextmanager

from .emulation.screen_buffer import ScreenBuffer
from .protocol.tn3270_handler import (
    TN3270Handler, NegotiationError
)
from .protocol.data_stream import (
    DataStreamParser, DataStreamSender
)
from .protocol.ssl_wrapper import SSLWrapper, SSLError

# Telnet constants
IAC = 0xff
SB = 0xfa
SE = 0xf0
WILL = 0xfb
WONT = 0xfc
DO = 0xfd
DONT = 0xfe

logger = logging.getLogger(__name__)

class Pure3270Error(Exception):
    """Base exception for Pure3270 errors."""
    def __init__(self, message):
        super().__init__(message)
        logger.error(message)

class SessionError(Pure3270Error):
    """Error in session operations."""
    pass

class AsyncSession:
    """Asynchronous 3270 session handler."""

    def __init__(
        self, rows: int = 24, cols: int = 80, force_3270: bool = False
    ):
        """
        Initialize the AsyncSession.

        :param rows: Screen rows (default 24).
        :param cols: Screen columns (default 80).
        :param force_3270: Force TN3270 mode without negotiation (for testing).
        """
        self.screen = ScreenBuffer(rows, cols)
        self.parser = DataStreamParser(self.screen)
        self.sender = DataStreamSender()
        self.handler: Optional[TN3270Handler] = None
        self._connected = False
        self.tn3270_mode = False
        self.tn3270e_mode = False
        self.force_3270 = force_3270
        self.lu_name: Optional[str] = None

    async def connect(
        self, host: str, port: int = 23, ssl: bool = False
    ) -> None:
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
            if self.force_3270:
                if self.handler.ssl_context:
                    self.handler.reader, self.handler.writer = (
                        await asyncio.open_connection(
                            self.handler.host, self.handler.port,
                            ssl=self.handler.ssl_context
                        )
                    )
                else:
                    self.handler.reader, self.handler.writer = (
                        await asyncio.open_connection(
                            self.handler.host, self.handler.port
                        )
                    )
                logger.info(
                    f"Connected to {host}:{port} in forced TN3270 mode, "
                    "skipping negotiation"
                )
                self.tn3270_mode = True
                self.tn3270e_mode = True
                self.lu_name = "DEFAULT"  # Assume default LU for forced mode
            else:
                await self.handler.connect()
                self.tn3270_mode = (
                    self.handler.supports_tn3270
                    and self.handler.negotiated_tn3270e
                )
                self.tn3270e_mode = self.handler.negotiated_tn3270e
                if (
                    hasattr(self.handler, 'lu_name')
                    and self.handler.lu_name
                ):
                    self.lu_name = self.handler.lu_name
                    logger.info(f"LU bound: {self.lu_name}")
                    if (
                        hasattr(self.handler, 'screen_rows')
                        and hasattr(self.handler, 'screen_cols')
                        and (
                            self.handler.screen_rows != self.screen.rows
                            or self.handler.screen_cols != self.screen.cols
                        )
                    ):
                        self.screen = ScreenBuffer(
                            self.handler.screen_rows,
                            self.handler.screen_cols
                        )
                        self.parser = DataStreamParser(self.screen)
                        logger.info(
                            f"Resized screen buffer to "
                            f"{self.handler.screen_rows} x "
                            f"{self.handler.screen_cols}"
                        )
            self._connected = True
            logger.info(f"Connected to {host}:{port}")
        except NegotiationError as e:
            logger.warning(f"TN3270 negotiation failed, falling back to ASCII: {e}")
            self.tn3270_mode = False
            self._connected = True
        except (ConnectionError, SSLError, Exception) as e:
            logger.error(f"Connection failed: {e}")
            self._connected = False
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
            if self.tn3270_mode:
                if command.startswith("key "):
                    key = command[4:]
                    # Map key to AID (simplified)
                    aid_map = {
                        "Enter": 0x7D, "PF3": 0x6D, "Clear": 0x6D, "Tab": 0x05
                    }
                    aid = aid_map.get(key, 0x7D)
                    data = bytes([aid])
                elif command.startswith("String("):
                    text = command[7:-1]
                    # In TN3270, string input is written to buffer and sent with AID
                    # Simplified: send text as is for fallback compatibility
                    data = text.encode('ascii')
                else:
                    data = self.sender.build_key_press(0x7D)
            else:
                # Fallback ASCII mode: send raw telnet bytes
                if command.startswith("key "):
                    key = command[4:].lower()
                    key_map = {
                        "enter": b'\r', "tab": b'\t', "clear": b'\x0c'
                    }
                    data = key_map.get(key, b'\r')
                elif command.startswith("String("):
                    text = command[7:-1]
                    data = text.encode('ascii')
                else:
                    data = command.encode('ascii')

            await self.handler.send_data(data)
            logger.debug(f"Sent command: {command}")
        except Exception as e:
            raise SessionError(f"Send failed: {e}")

    async def read(self) -> str:
        """
        Read the current screen content.

        :return: Screen text as string.
        :raises SessionError: If read fails.
        """
        if not self._connected or not self.handler:
            raise SessionError("Not connected")

        logger.info(
            "Starting blocking read with 10s timeout "
            "(waiting for complete response)"
        )
        try:
            data = await self.handler.receive_data(timeout=10.0)
        except Exception as e:
            logger.warning(f"Receive data failed: {e}")
            data = b''
        try:
            if not self.tn3270_mode:
                # Fallback for non-TN3270: strip Telnet IAC and decode as ASCII
                clean_data = self._strip_telnet_iac(data)
                clean_text = clean_data.decode('ascii', errors='ignore')
                # Format to screen size
                lines = []
                for i in range(0, len(clean_text), self.screen.cols):
                    line = (
                        clean_text[i:i + self.screen.cols].ljust(self.screen.cols)
                    )
                    lines.append(line[:self.screen.cols])
                while len(lines) < self.screen.rows:
                    lines.append(' ' * self.screen.cols)
                text = '\n'.join(lines).strip()
                logger.debug("Fallback ASCII read successful")
                return text
            else:
                if self.tn3270e_mode:
                    logger.debug("TN3270E mode: parsing 3270 data stream")
                self.parser = DataStreamParser(self.screen)
                self.parser.parse(data)
                text = self.screen.to_text().replace('\x00', '').strip()
                logger.info("TN3270E read completed successfully")
                return text
        except Exception as e:
            logger.warning(f"Read partial failure: {e}")
            # Fallback to raw decode if parse fails
            # For fallback ASCII, ensure EOR/GA stripped (handler already does, but double-check)
            clean_data = self._strip_telnet_iac(data)
            clean_text = clean_data.decode('ascii', errors='ignore')
            logger.info("Fallback ASCII read completed")
            return clean_text

    async def macro(self, sequence: Sequence[str]) -> None:
        """
        Execute a macro sequence of commands.

        :param sequence: List of commands.
        """
        for cmd in sequence:
            await self.send(cmd)
            await asyncio.sleep(0.1)  # Small delay between commands

    def _strip_telnet_iac(self, data: bytes) -> bytes:
        """Strip Telnet IAC sequences from data, including EOR and GA for fallback."""
        """Strip Telnet IAC sequences from data, including EOR and GA for fallback."""
        result = b""
        i = 0
        while i < len(data):
            if data[i] == IAC and i + 2 < len(data):
                cmd = data[i + 1]
                if cmd == SB:
                    # Skip subnegotiation until SE
                    j = i + 2
                    while j < len(data) and data[j] != SE:
                        j += 1
                    if j < len(data) and data[j] == SE:
                        j += 1
                    i = j
                    continue
                elif cmd in (WILL, WONT, DO, DONT):
                    i += 3
                    continue
                elif cmd == 0x19:  # EOR
                    logger.debug("Stripping IAC EOR in fallback")
                    i += 2
                    continue
                elif cmd == 0xf9:  # GA
                    logger.debug("Stripping IAC GA in fallback")
                    i += 2
                    continue
                else:
                    i += 2
                    continue
            else:
                result += bytes([data[i]])
                i += 1
        return result

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

    def __init__(
        self, rows: int = 24, cols: int = 80, force_3270: bool = False
    ):
        """
        Initialize the Session.

        :param rows: Screen rows (default 24).
        :param cols: Screen columns (default 80).
        :param force_3270: Force TN3270 mode without negotiation (for testing).
        """
        self._async_session = AsyncSession(rows, cols, force_3270)
        self.loop = None

    def connect(self, host: str, port: int = 23, ssl: bool = False) -> None:
        """
        Connect to the TN3270 host (sync).

        :param host: Hostname or IP.
        :param port: Port (default 23).
        :param ssl: Use SSL/TLS if True.
        :raises SessionError: If connection fails.
        """
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(
                self._async_session.connect(host, port, ssl)
            )
        except Exception as e:
            raise SessionError(f"Connection failed: {e}")

    def send(self, command: str) -> None:
        """
        Send a command or key (sync).

        :param command: Command or key.
        :raises SessionError: If send fails.
        """
        if self.loop is None:
            raise SessionError("Must connect first")
        self.loop.run_until_complete(self._async_session.send(command))

    def read(self) -> str:
        """
        Read the current screen content (sync).

        :return: Screen text.
        :raises SessionError: If read fails.
        """
        if self.loop is None:
            raise SessionError("Must connect first")
        return self.loop.run_until_complete(self._async_session.read())

    def macro(self, sequence: Sequence[str]) -> None:
        """
        Execute a macro sequence (sync).

        :param sequence: List of commands.
        """
        if self.loop is None:
            raise SessionError("Must connect first")
        self.loop.run_until_complete(self._async_session.macro(sequence))

    def close(self) -> None:
        """Close the session (sync)."""
        if self.loop is None:
            return
        self.loop.run_until_complete(self._async_session.close())
        if not self.loop.is_closed():
            self.loop.close()
        self.loop = None

    @property
    def connected(self) -> bool:
        """Check if connected."""
        return self._async_session.connected

    @property
    def tn3270_mode(self) -> bool:
        """Check if TN3270 mode is active."""
        return self._async_session.tn3270_mode

    @property
    def tn3270e_mode(self) -> bool:
        """Check if TN3270E mode is active."""
        return self._async_session.tn3270e_mode

    @property
    def lu_name(self) -> Optional[str]:
        """Get the bound LU name."""
        return self._async_session.lu_name

    def __enter__(self):
        """Sync context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close()
        if self.loop and not self.loop.is_closed():
            self.loop.close()
        self.loop = None

# Logging setup (basic)
def setup_logging(level: str = "INFO"):
    """Setup logging for the library."""
    logging.basicConfig(level=level)
    logging.getLogger("pure3270").setLevel(level)
