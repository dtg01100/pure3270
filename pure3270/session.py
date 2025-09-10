"""
Session management for pure3270, handling synchronous and asynchronous 3270 connections.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Any, Dict, List
from .protocol.tn3270_handler import TN3270Handler
from .emulation.screen_buffer import ScreenBuffer
from .protocol.exceptions import NegotiationError
from .protocol.data_stream import DataStreamParser

logger = logging.getLogger(__name__)


class SessionError(Exception):
    """Base exception for session-related errors."""

    pass


class ConnectionError(SessionError):
    """Raised when connection fails."""

    pass


class MacroError(SessionError):
    """Raised during macro execution errors."""

    pass


class Session:
    """
    Synchronous wrapper for AsyncSession.

    This class provides a synchronous interface to the asynchronous 3270 session.
    All methods use asyncio.run() to execute async operations.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 23,
        ssl_context: Optional[Any] = None,
    ):
        """
        Initialize a synchronous session.

        Args:
            host: The target host IP or hostname (can be set later in connect()).
            port: The target port (default 23 for Telnet).
            ssl_context: Optional SSL context for secure connections.

        Raises:
            ConnectionError: If connection initialization fails.
        """
        self._host = host
        self._port = port
        self._ssl_context = ssl_context
        self._async_session = None

    def connect(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        ssl_context: Optional[Any] = None,
    ) -> None:
        """Connect to the 3270 host synchronously.

        Args:
            host: Optional host override.
            port: Optional port override (default 23).
            ssl_context: Optional SSL context override.

        Raises:
            ConnectionError: If connection fails.
        """
        if host is not None:
            self._host = host
        if port is not None:
            self._port = port
        if ssl_context is not None:
            self._ssl_context = ssl_context
        self._async_session = AsyncSession(self._host, self._port, self._ssl_context)
        asyncio.run(self._async_session.connect())

    def send(self, data: bytes) -> None:
        """
        Send data to the session.

        Args:
            data: Bytes to send.

        Raises:
            SessionError: If send fails.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.send(data))

    def read(self, timeout: float = 5.0) -> bytes:
        """
        Read data from the session.

        Args:
            timeout: Read timeout in seconds.

        Returns:
            Received bytes.

        Raises:
            SessionError: If read fails.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        return asyncio.run(self._async_session.read(timeout))

    def execute_macro(
        self, macro: str, vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a macro synchronously.

        Args:
            macro: Macro script to execute.
            vars: Optional dictionary for variable substitution.

        Returns:
            Dict with execution results, e.g., {'success': bool, 'output': list}.

        Raises:
            MacroError: If macro execution fails.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        return asyncio.run(self._async_session.execute_macro(macro, vars))

    def close(self) -> None:
        """Close the session synchronously."""
        if self._async_session:
            asyncio.run(self._async_session.close())
            self._async_session = None

    def open(self, host: str, port: int = 23) -> None:
        """Open connection synchronously (s3270 Open() action)."""
        self.connect(host, port)

    def close_script(self) -> None:
        """Close script synchronously (s3270 CloseScript() action)."""
        if self._async_session:
            asyncio.run(self._async_session.close_script())

    def ascii(self, data: bytes) -> str:
        """
        Convert EBCDIC data to ASCII text (s3270 Ascii() action).

        Args:
            data: EBCDIC bytes to convert.

        Returns:
            ASCII string representation.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        return self._async_session.ascii(data)

    def ebcdic(self, text: str) -> bytes:
        """
        Convert ASCII text to EBCDIC data (s3270 Ebcdic() action).

        Args:
            text: ASCII text to convert.

        Returns:
            EBCDIC bytes representation.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        return self._async_session.ebcdic(text)

    def ascii1(self, byte_val: int) -> str:
        """
        Convert a single EBCDIC byte to ASCII character (s3270 Ascii1() action).

        Args:
            byte_val: EBCDIC byte value.

        Returns:
            ASCII character.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        return self._async_session.ascii1(byte_val)

    def ebcdic1(self, char: str) -> int:
        """
        Convert a single ASCII character to EBCDIC byte (s3270 Ebcdic1() action).

        Args:
            char: ASCII character to convert.

        Returns:
            EBCDIC byte value.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        return self._async_session.ebcdic1(char)

    def ascii_field(self, field_index: int) -> str:
        """
        Convert field content to ASCII text (s3270 AsciiField() action).

        Args:
            field_index: Index of field to convert.

        Returns:
            ASCII string representation of field content.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        return self._async_session.ascii_field(field_index)

    def cursor_select(self) -> None:
        """
        Select field at cursor (s3270 CursorSelect() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.cursor_select())

    def delete_field(self) -> None:
        """
        Delete field at cursor (s3270 DeleteField() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.delete_field())

    def echo(self, text: str) -> None:
        """Echo text (s3270 Echo() action)."""
        print(text)

    def circum_not(self) -> None:
        """
        Toggle circumvention of field protection (s3270 CircumNot() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.circum_not())

    def script(self, commands: str) -> None:
        """
        Execute script (s3270 Script() action).

        Args:
            commands: Script commands.

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.script(commands))

    def execute(self, command: str) -> str:
        """Execute external command synchronously (s3270 Execute() action)."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        return asyncio.run(self._async_session.execute(command))

    def capabilities(self) -> str:
        """Get capabilities synchronously (s3270 Capabilities() action)."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        return asyncio.run(self._async_session.capabilities())

    def interrupt(self) -> None:
        """Send interrupt synchronously (s3270 Interrupt() action)."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.interrupt())

    def key(self, keyname: str) -> None:
        """Send key synchronously (s3270 Key() action)."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.key(keyname))

    def query(self, query_type: str = "All") -> str:
        """Query screen synchronously (s3270 Query() action)."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        return asyncio.run(self._async_session.query(query_type))

    def set_option(self, option: str, value: str) -> None:
        """Set option synchronously (s3270 Set() action)."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.set(option, value))

    def exit(self) -> None:
        """Exit synchronously (s3270 Exit() action)."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.exit())

    def keyboard_disable(self) -> None:
        """Disable keyboard input (s3270 KeyboardDisable() action)."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        self._async_session.keyboard_disabled = True
        logger.info("Keyboard disabled")

    def enter(self) -> None:
        """Send Enter key synchronously (s3270 Enter() action)."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.enter())

    def erase(self) -> None:
        """
        Erase character at cursor (s3270 Erase() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.erase())

    def erase_eof(self) -> None:
        """
        Erase from cursor to end of field (s3270 EraseEOF() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.erase_eof())

    def home(self) -> None:
        """
        Move cursor to home position (s3270 Home() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.home())

    def left(self) -> None:
        """
        Move cursor left one position (s3270 Left() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.left())

    def right(self) -> None:
        """
        Move cursor right one position (s3270 Right() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.right())

    def up(self) -> None:
        """
        Move cursor up one row (s3270 Up() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.up())

    def down(self) -> None:
        """
        Move cursor down one row (s3270 Down() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.down())

    def backspace(self) -> None:
        """
        Send backspace (s3270 BackSpace() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.backspace())

    def tab(self) -> None:
        """
        Move cursor to next field or right (s3270 Tab() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.tab())

    def backtab(self) -> None:
        """
        Move cursor to previous field or left (s3270 BackTab() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.backtab())

    def compose(self, text: str) -> None:
        """
        Compose special characters or key combinations (s3270 Compose() action).

        Args:
            text: Text to compose, which may include special character sequences.

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.compose(text))

    def cookie(self, cookie_string: str) -> None:
        """
        Set HTTP cookie for web-based emulators (s3270 Cookie() action).

        Args:
            cookie_string: Cookie in "name=value" format.

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.cookie(cookie_string))

    def expect(self, pattern: str, timeout: float = 10.0) -> bool:
        """
        Wait for a pattern to appear on the screen (s3270 Expect() action).

        Args:
            pattern: Text pattern to wait for.
            timeout: Maximum time to wait in seconds.

        Returns:
            True if pattern is found, False if timeout occurs.

        Raises:
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        return asyncio.run(self._async_session.expect(pattern, timeout))

    def fail(self, message: str) -> None:
        """
        Cause script to fail with a message (s3270 Fail() action).

        Args:
            message: Error message to display.

        Raises:
            SessionError: If not connected.
            Exception: Always raises an exception with the provided message.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.fail(message))

    def pf(self, n: int) -> None:
        """
        Send PF (Program Function) key synchronously (s3270 PF() action).

        Args:
            n: PF key number (1-24).

        Raises:
            ValueError: If invalid PF key number.
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.pf(n))

    def pa(self, n: int) -> None:
        """
        Send PA (Program Attention) key synchronously (s3270 PA() action).

        Args:
            n: PA key number (1-3).

        Raises:
            ValueError: If invalid PA key number.
            SessionError: If not connected.
        """
        if not self._async_session:
            raise SessionError("Session not connected.")
        asyncio.run(self._async_session.pa(n))

    @property
    def screen_buffer(self) -> ScreenBuffer:
        """Get the screen buffer property."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        return self._async_session.screen_buffer

    @property
    def connected(self) -> bool:
        """Check if session is connected."""
        if self._async_session is None:
            return False
        return self._async_session.connected


class AsyncSession:
    """
    Asynchronous 3270 session handler.

    Manages connection, data exchange, and screen emulation for 3270 terminals.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 23,
        ssl_context: Optional[Any] = None,
    ):
        """
        Initialize the async session.

        Args:
            host: The target host IP or hostname (can be set later in connect()).
            port: The target port (default 23 for Telnet).
            ssl_context: Optional SSL context for secure connections.

        Raises:
            ValueError: If host or port is invalid.
        """
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self._handler: Optional[TN3270Handler] = None
        self.screen_buffer = ScreenBuffer()
        self._connected = False
        self.tn3270_mode = False
        self.tn3270e_mode = False
        self._lu_name: Optional[str] = None
        self.insert_mode = False
        self.circumvent_protection = False
        self.resources = {}
        self.model = "2"
        self.color_mode = False
        self.color_palette = [(0, 0, 0)] * 16
        self.font = "fixed"
        self.keymap = None
        self._resource_mtime = 0
        self.keyboard_disabled = False
        self.logger = logging.getLogger(__name__)

    async def connect(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        ssl_context: Optional[Any] = None,
    ) -> None:
        """
        Establish connection to the 3270 host.
        Performs TN3270 negotiation.
        Args:
            host: Optional override for host.
            port: Optional override for port (default 23).
            ssl_context: Optional override for SSL context.
        Raises:
            ValueError: If no host specified.
            ConnectionError: On connection failure.
            NegotiationError: On negotiation failure.
        """
        if host is not None:
            self.host = host
        if port is not None:
            self.port = port
        if ssl_context is not None:
            self.ssl_context = ssl_context
        if not self.host:
            raise ValueError(
                "Host must be provided either at initialization or in connect call."
            )
        reader, writer = await asyncio.open_connection(
            self.host, self.port, ssl=self.ssl_context
        )
        self._handler = TN3270Handler(reader, writer)
        await self._handler.negotiate()
        self._connected = True
        # Fallback to ASCII if negotiation fails
        try:
            await self._handler._negotiate_tn3270()
            self.tn3270_mode = True
            self.tn3270e_mode = self._handler.negotiated_tn3270e
            self._lu_name = self._handler.lu_name
            self.screen_buffer.rows = self._handler.screen_rows
            self.screen_buffer.cols = self._handler.screen_cols
        except NegotiationError as e:
            logger.warning(
                f"TN3270 negotiation failed, falling back to ASCII mode: {e}"
            )
            if self._handler:
                self._handler.set_ascii_mode()

    async def send(self, data: bytes) -> None:
        """
        Send data asynchronously.

        Args:
            data: Bytes to send.

        Raises:
            SessionError: If send fails.
        """
        if not self._connected or not self._handler:
            raise SessionError("Session not connected.")
        await self._handler.send_data(data)

    async def read(self, timeout: float = 5.0) -> bytes:
        """
        Read data asynchronously with timeout.

        Args:
            timeout: Read timeout in seconds (default 5.0).

        Returns:
            Received bytes.

        Raises:
            asyncio.TimeoutError: If timeout exceeded.
        """
        if not self._connected or not self._handler:
            raise SessionError("Session not connected.")

        data = await self._handler.receive_data(timeout)

        # Parse the received data if in TN3270 mode
        if self.tn3270_mode and data:
            parser = DataStreamParser(self.screen_buffer)
            parser.parse(data)

        return data

    async def _execute_single_command(self, cmd: str, vars: Dict[str, str]) -> str:
        """
        Execute a single simple command.

        Args:
            cmd: The command string.
            vars: Variables dict.

        Returns:
            Output string.

        Raises:
            MacroError: If execution fails.
        """
        try:
            await self.send(cmd.encode("ascii"))
            output = await self.read()
            return output.decode("ascii", errors="ignore")
        except Exception as e:
            raise MacroError(f"Command execution failed: {e}")

    def _evaluate_condition(self, condition: str) -> bool:
        """
        Evaluate a simple condition.

        Args:
            condition: Condition string like 'connected' or 'error'.

        Returns:
            bool evaluation result.

        Raises:
            MacroError: Unknown condition.
        """
        if condition == "connected":
            return self._connected
        elif condition == "error":
            # Simplified: assume no error for now; could track last_error
            return False
        else:
            raise MacroError(f"Unknown condition: {condition}")

    async def execute_macro(
        self, macro: str, vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute a macro asynchronously with advanced parsing support.

        Supports conditional branching (e.g., 'if connected: command'),
        variable substitution (e.g., '${var}'), and nested macros (e.g., 'macro nested').

        Args:
            macro: Macro script string, commands separated by ';'.
            vars: Optional dict for variables and nested macros.

        Returns:
            Dict with {'success': bool, 'output': list of str/dict, 'vars': dict}.

        Raises:
            MacroError: On parsing or execution errors.
            SessionError: If not connected.
        """
        if vars is None:
            vars = {}
        if not self._connected or not self._handler:
            raise SessionError("Session not connected.")

        # Variable substitution
        for key, value in vars.items():
            macro = macro.replace(f"${{{key}}}", str(value))

        # Parse commands
        commands = [cmd.strip() for cmd in macro.split(";") if cmd.strip()]
        results = {"success": True, "output": [], "vars": vars.copy()}
        i = 0
        while i < len(commands):
            cmd = commands[i]
            try:
                if cmd.startswith("if "):
                    if ":" not in cmd:
                        raise MacroError("Invalid if syntax: missing ':'")
                    condition_part, command_part = cmd.split(":", 1)
                    condition = condition_part[3:].strip()
                    command_part = command_part.strip()
                    if self._evaluate_condition(condition):
                        sub_output = await self._execute_single_command(
                            command_part, vars
                        )
                        results["output"].append(sub_output)
                elif cmd.startswith("macro "):
                    macro_name = cmd[6:].strip()
                    nested_macro = vars.get(macro_name)
                    if nested_macro:
                        sub_results = await self.execute_macro(nested_macro, vars)
                        results["output"].append(sub_results)
                    else:
                        raise MacroError(
                            f"Nested macro '{macro_name}' not found in vars"
                        )
                elif cmd.startswith("LoadResource(") and cmd.endswith(")"):
                    file_path = cmd[
                        13:-1
                    ].strip()  # Start from index 13 to skip "LoadResource("
                    await self.load_resource_definitions(file_path)
                    results["output"].append(
                        f"Loaded resource definitions from {file_path}"
                    )
                else:
                    # Backward compatible simple command
                    sub_output = await self._execute_single_command(cmd, vars)
                    results["output"].append(sub_output)
            except Exception as e:
                results["success"] = False
                results["output"].append(f"Error in command '{cmd}': {e}")
            i += 1
        return results

    async def close(self) -> None:
        """Close the async session."""
        if self._handler:
            await self._handler.close()
        self._handler = None
        self._connected = False

    async def execute(self, command: str) -> str:
        """Execute external command (s3270 Execute() action)."""
        import subprocess

        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr

    async def exit(self) -> None:
        """Exit session (s3270 Exit() action, alias to close)."""
        await self.close()
        logger.info("Session exited (Exit action)")

    async def quit(self) -> None:
        """Quit session (s3270 Quit() action, alias to close)."""
        await self.close()
        logger.info("Session quit (Quit action)")

    async def capabilities(self) -> str:
        """Return session capabilities (s3270 Capabilities() action)."""
        caps = f"TN3270: {self.tn3270_mode}, TN3270E: {self.tn3270e_mode}, LU: {self._lu_name or 'None'}, Screen: {self.screen_buffer.rows}x{self.screen_buffer.cols}"
        logger.info(f"Capabilities: {caps}")
        return caps

    async def interrupt(self) -> None:
        """Send interrupt (s3270 Interrupt() action, ATTN key)."""
        await self.submit(0x7E)  # ATTN AID
        logger.info("Interrupt sent")

    async def key(self, keyname: str) -> None:
        """Send key (s3270 Key() action)."""
        # Comprehensive AID mapping for all supported keys
        AID_MAP = {
            "enter": 0x7D,
            "pf1": 0xF1,
            "pf2": 0xF2,
            "pf3": 0xF3,
            "pf4": 0xF4,
            "pf5": 0xF5,
            "pf6": 0xF6,
            "pf7": 0xF7,
            "pf8": 0xF8,
            "pf9": 0xF9,
            "pf10": 0x7A,
            "pf11": 0x7B,
            "pf12": 0x7C,
            "pf13": 0xC1,
            "pf14": 0xC2,
            "pf15": 0xC3,
            "pf16": 0xC4,
            "pf17": 0xC5,
            "pf18": 0xC6,
            "pf19": 0xC7,
            "pf20": 0xC8,
            "pf21": 0xC9,
            "pf22": 0xCA,
            "pf23": 0xCB,
            "pf24": 0xCC,
            "pa1": 0x6C,
            "pa2": 0x6E,
            "pa3": 0x6B,
            "clear": 0x6D,
            "attn": 0x7E,
            "reset": 0x7F,
        }
        aid = AID_MAP.get(keyname.lower())
        if aid is None:
            raise ValueError(f"Unknown key: {keyname}")
        await self.submit(aid)
        logger.info(f"Key sent: {keyname}")

    async def query(self, query_type: str = "All") -> str:
        """Query screen (s3270 Query() action, using screen_buffer)."""
        if query_type == "Format":
            return f"Screen format: {self.screen_buffer.rows}x{self.screen_buffer.cols}, Fields: {len(self.screen_buffer.fields)}"
        elif query_type == "All":
            return self.screen_buffer.to_text()
        else:
            raise ValueError(f"Unknown query type: {query_type}")
        logger.info(f"Query {query_type} executed")

    async def set(self, option: str, value: str) -> None:
        """Set option (s3270 Set() action)."""
        if not hasattr(self, "_options"):
            self._options = {}
        self._options[option] = value
        logger.info(f"Set {option} to {value}")

    @asynccontextmanager
    async def managed(self):
        """
        Async context manager for the session.

        Usage:
            async with session.managed():
                await session.connect()
                # operations
        """
        try:
            yield self
        finally:
            await self.close()

    @property
    def connected(self) -> bool:
        """Check if session is connected."""
        return self._connected

    @property
    def tn3270_mode(self) -> bool:
        """Check if TN3270 mode is active."""
        return self._tn3270_mode

    @tn3270_mode.setter
    def tn3270_mode(self, value: bool) -> None:
        self._tn3270_mode = value

    @property
    def tn3270e_mode(self) -> bool:
        """Check if TN3270E mode is active."""
        return self._tn3270e_mode

    @tn3270e_mode.setter
    def tn3270e_mode(self, value: bool) -> None:
        self._tn3270e_mode = value

    @property
    def lu_name(self) -> Optional[str]:
        """Get the LU name."""
        return self._lu_name

    @lu_name.setter
    def lu_name(self, value: Optional[str]) -> None:
        """Set the LU name."""
        self._lu_name = value

    @property
    def screen(self) -> ScreenBuffer:
        """Get the screen buffer (alias for screen_buffer for compatibility)."""
        return self.screen_buffer

    @property
    def handler(self) -> Optional[TN3270Handler]:
        """Get the handler (public interface for compatibility)."""
        return self._handler

    @handler.setter
    def handler(self, value: Optional[TN3270Handler]) -> None:
        """Set the handler (public interface for compatibility)."""
        self._handler = value

    async def macro(self, commands: List[str]) -> None:
        """
        Execute a list of macro commands using a dispatcher for maintainability.

        Args:
            commands: List of macro command strings.
                     Supported formats:
                     - 'String(text)' - Send text as EBCDIC
                     - 'key Enter' - Send Enter key
                     - 'key <keyname>' - Send other keys (PF1-PF24, PA1-PA3, etc.)
                     Examples:
                         - String(Hello World)
                         - key enter
                         - Execute(ls -l)

        Raises:
            MacroError: If command parsing or execution fails.
            SessionError: If not connected.
        """
        if not self._connected or not self.handler:
            raise SessionError("Session not connected.")

        from .protocol.data_stream import DataStreamSender
        from .emulation.ebcdic import translate_ascii_to_ebcdic

        sender = DataStreamSender()

        # AID mapping for common keys
        AID_MAP = {
            "enter": 0x7D,
            "pf1": 0xF1,
            "pf2": 0xF2,
            "pf3": 0xF3,
            "pf4": 0xF4,
            "pf5": 0xF5,
            "pf6": 0xF6,
            "pf7": 0xF7,
            "pf8": 0xF8,
            "pf9": 0xF9,
            "pf10": 0x7A,
            "pf11": 0x7B,
            "pf12": 0x7C,
            "pf13": 0xC1,
            "pf14": 0xC2,
            "pf15": 0xC3,
            "pf16": 0xC4,
            "pf17": 0xC5,
            "pf18": 0xC6,
            "pf19": 0xC7,
            "pf20": 0xC8,
            "pf21": 0xC9,
            "pf22": 0xCA,
            "pf23": 0xCB,
            "pf24": 0xCC,
            "pa1": 0x6C,
            "pa2": 0x6E,
            "pa3": 0x6B,
            "clear": 0x6D,
            "attn": 0x7E,
            "reset": 0x7F,
        }

        # Command dispatcher for simple actions
        simple_actions = {
            "Interrupt()": self.interrupt,
            "CircumNot()": self.circum_not,
            "CursorSelect()": self.cursor_select,
            "Delete()": self.delete,
            "DeleteField()": self.delete_field,
            "Dup()": self.dup,
            "End()": self.end,
            "Erase()": self.erase,
            "EraseEOF()": self.erase_eof,
            "EraseInput()": self.erase_input,
            "FieldEnd()": self.field_end,
            "FieldMark()": self.field_mark,
            "Flip()": self.flip,
            "Insert()": self.insert,
            "NextWord()": self.next_word,
            "PreviousWord()": self.previous_word,
            "RestoreInput()": self.restore_input,
            "SaveInput()": self.save_input,
            "Tab()": self.tab,
            "ToggleInsert()": self.toggle_insert,
            "ToggleReverse()": self.toggle_reverse,
            "Clear()": self.clear,
            "Close()": self.close_session,
            "CloseScript()": self.close_script,
            "Disconnect()": self.disconnect,
            "Exit()": self.exit,
            "Info()": self.info,
            "Quit()": self.quit,
            "Newline()": self.newline,
            "PageDown()": self.page_down,
            "PageUp()": self.page_up,
            "Bell()": self.bell,
            "Show()": self.show,
            "Snap()": self.snap,
            "Left2()": self.left2,
            "Right2()": self.right2,
            "MonoCase()": self.mono_case,
            "Compose()": self.compose,
            "Cookie()": self.cookie,
            "Expect()": self.expect,
            "Fail()": self.fail,
        }

        for command in commands:
            command = command.strip()
            try:
                if command in simple_actions:
                    await simple_actions[command]()
                elif command.startswith("String(") and command.endswith(")"):
                    text = command[7:-1]
                    await self.insert_text(text)
                elif command.startswith("key "):
                    key_name = command[4:].strip().lower()
                    aid = AID_MAP.get(key_name)
                    if aid is not None:
                        await self.submit(aid)
                    else:
                        raise MacroError(f"Unsupported key: {key_name}")
                elif command.startswith("Key("):
                    key_name = command[4:-1].strip().lower()
                    await self.key(key_name)
                elif command.startswith("Execute("):
                    cmd = command[8:-1].strip()
                    result = await self.execute(cmd)
                    print(result)
                elif command == "Capabilities()":
                    result = await self.capabilities()
                    print(result)
                elif command.startswith("Query("):
                    query_type = command[6:-1].strip()
                    result = await self.query(query_type)
                    print(result)
                elif command.startswith("Set("):
                    args = command[4:-1].split(",")
                    if len(args) == 2:
                        option = args[0].strip()
                        value = args[1].strip()
                        await self.set(option, value)
                    else:
                        raise MacroError("Invalid Set format")
                elif command.startswith("MoveCursor("):
                    args = command[11:-1].split(",")
                    if len(args) == 2:
                        row = int(args[0].strip())
                        col = int(args[1].strip())
                        await self.move_cursor(row, col)
                    else:
                        raise MacroError("Invalid MoveCursor format")
                elif command.startswith("MoveCursor1("):
                    args = command[12:-1].split(",")
                    if len(args) == 2:
                        row = int(args[0].strip())
                        col = int(args[1].strip())
                        await self.move_cursor1(row, col)
                    else:
                        raise MacroError("Invalid MoveCursor1 format")
                elif command.startswith("PasteString("):
                    text = command[12:-1]
                    await self.paste_string(text)
                elif command.startswith("Script("):
                    script = command[7:-1]
                    await self.script(script)
                elif command.startswith("Pause("):
                    secs = float(command[6:-1])
                    await self.pause(secs)
                elif command.startswith("AnsiText("):
                    data = command[9:-1].encode()
                    result = await self.ansi_text(data)
                    print(result)
                elif command.startswith("HexString("):
                    hex_str = command[10:-1]
                    result = await self.hex_string(hex_str)
                    print(result)
                elif command.startswith("NvtText("):
                    text = command[8:-1]
                    await self.nvt_text(text)
                elif command.startswith("PrintText("):
                    text = command[10:-1]
                    await self.print_text(text)
                elif command.startswith("Prompt("):
                    message = command[7:-1]
                    result = await self.prompt(message)
                    print(result)
                elif command == "ReadBuffer()":
                    buffer = await self.read_buffer()
                    print(buffer)
                elif command == "Reconnect()":
                    await self.reconnect()
                elif command == "ScreenTrace()":
                    await self.screen_trace()
                elif command.startswith("Source("):
                    file = command[7:-1]
                    await self.source(file)
                elif command == "SubjectNames()":
                    await self.subject_names()
                elif command == "SysReq()":
                    await self.sys_req()
                elif command.startswith("Toggle("):
                    option = command[7:-1]
                    await self.toggle_option(option)
                elif command.startswith("Trace("):
                    on = command[6:-1].lower() == "on"
                    await self.trace(on)
                elif command.startswith("Transfer("):
                    file = command[9:-1]
                    await self.transfer(file)
                elif command.startswith("LoadResource("):
                    file_path = command[12:-1].strip()
                    await self.load_resource_definitions(file_path)
                elif command.startswith("Wait("):
                    condition = command[5:-1]
                    await self.wait_condition(condition)
                else:
                    raise MacroError(f"Unsupported command format: {command}")
            except Exception as e:
                raise MacroError(f"Failed to execute command '{command}': {e}")

    async def pf(self, n: int) -> None:
        """
        Send PF (Program Function) key (s3270 PF() action).

        Args:
            n: PF key number (1-24).

        Raises:
            ValueError: If invalid PF key number.
            SessionError: If not connected.
        """
        if not 1 <= n <= 24:
            raise ValueError(f"PF key must be between 1 and 24, got {n}")

        # PF1-12 map directly, PF13-24 map to shifted keys
        if n <= 12:
            aid = 0xF0 + n  # PF1=0xF1, PF2=0xF2, etc.
        else:
            # PF13-24 map to other AIDs (simplified mapping)
            aid_map = {
                13: 0xC1,
                14: 0xC2,
                15: 0xC3,
                16: 0xC4,
                17: 0xC5,
                18: 0xC6,
                19: 0xC7,
                20: 0xC8,
                21: 0xC9,
                22: 0xCA,
                23: 0xCB,
                24: 0xCC,
            }
            aid = aid_map.get(n, 0xF1)  # Default to PF1

        if not self._connected or not self.handler:
            raise SessionError("Session not connected.")

        await self.submit(aid)

    async def pa(self, n: int) -> None:
        """
        Send PA (Program Attention) key (s3270 PA() action).

        Args:
            n: PA key number (1-3).

        Raises:
            ValueError: If invalid PA key number.
            SessionError: If not connected.
        """
        if not 1 <= n <= 3:
            raise ValueError(f"PA key must be between 1 and 3, got {n}")

        aid_map = {1: 0x6C, 2: 0x6E, 3: 0x6B}  # Standard PA1-PA3 AIDs
        aid = aid_map[n]

        if not self._connected or not self.handler:
            raise SessionError("Session not connected.")

        await self.submit(aid)

    async def submit(self, aid: int) -> None:
        """
        Submit modified fields with the given AID.

        Args:
            aid: Attention ID byte.

        Raises:
            SessionError: If not connected.
        """
        if not self._connected or not self.handler:
            raise SessionError("Session not connected.")

        from .protocol.data_stream import DataStreamSender

        sender = DataStreamSender()
        modified_fields = self.screen_buffer.read_modified_fields()
        # Convert to bytes
        modified_bytes = []
        for pos, content in modified_fields:
            ebcdic_bytes = self.ebcdic(content)  # Assuming ebcdic method exists
            modified_bytes.append((pos, ebcdic_bytes))

        input_stream = sender.build_input_stream(
            modified_bytes, aid, self.screen_buffer.cols
        )
        await self.send(input_stream)
        # Reset modified flags for sent fields
        for field in self.screen_buffer.fields:
            if field.modified:
                field.modified = False

    def ascii(self, data: bytes) -> str:
        """
        Convert EBCDIC data to ASCII text.

        Args:
            data: EBCDIC bytes.

        Returns:
            ASCII string.
        """
        from .emulation.ebcdic import translate_ebcdic_to_ascii

        return translate_ebcdic_to_ascii(data)

    def ebcdic(self, text: str) -> bytes:
        """
        Convert ASCII text to EBCDIC data.

        Args:
            text: ASCII text.

        Returns:
            EBCDIC bytes.
        """
        from .emulation.ebcdic import translate_ascii_to_ebcdic

        return translate_ascii_to_ebcdic(text)

    def ascii1(self, byte_val: int) -> str:
        """
        Convert a single EBCDIC byte to ASCII character.

        Args:
            byte_val: EBCDIC byte value.

        Returns:
            ASCII character.
        """
        from .emulation.ebcdic import translate_ebcdic_to_ascii

        return translate_ebcdic_to_ascii(bytes([byte_val]))

    def ebcdic1(self, char: str) -> int:
        """
        Convert a single ASCII character to EBCDIC byte.

        Args:
            char: ASCII character.

        Returns:
            EBCDIC byte value.
        """
        from .emulation.ebcdic import translate_ascii_to_ebcdic

        ebcdic_bytes = translate_ascii_to_ebcdic(char)
        return ebcdic_bytes[0] if ebcdic_bytes else 0

    def ascii_field(self, field_index: int) -> str:
        """
        Convert field content to ASCII text.

        Args:
            field_index: Index of field.

        Returns:
            ASCII string.
        """
        return self.screen_buffer.get_field_content(field_index)

    async def insert_text(self, text: str) -> None:
        """
        Insert text at current cursor position.

        Args:
            text: Text to insert.
        """
        ebcdic_bytes = self.ebcdic(text)
        for byte in ebcdic_bytes:
            row, col = self.screen_buffer.get_position()
            self.screen_buffer.write_char(
                byte, row, col, circumvent_protection=self.circumvent_protection
            )
            await self.right()

    async def backtab(self) -> None:
        """
        Move cursor to previous field or left (s3270 BackTab() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._connected or not self.handler:
            raise SessionError("Session not connected.")

        # Simple implementation: move left
        await self.left()

    async def home(self) -> None:
        """
        Move cursor to home position (row 0, col 0) (s3270 Home() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._connected or not self.handler:
            raise SessionError("Session not connected.")

        self.screen_buffer.set_position(0, 0)

    async def left(self) -> None:
        """
        Move cursor left one position (s3270 Left() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._connected or not self.handler:
            raise SessionError("Session not connected.")

        row, col = self.screen_buffer.get_position()
        if col > 0:
            col -= 1
        else:
            col = self.screen_buffer.cols - 1
            row = max(0, row - 1)  # Wrap to previous row
        self.screen_buffer.set_position(row, col)

    async def right(self) -> None:
        """
        Move cursor right one position (s3270 Right() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._connected or not self.handler:
            raise SessionError("Session not connected.")

        row, col = self.screen_buffer.get_position()
        col += 1
        if col >= self.screen_buffer.cols:
            col = 0
            row = min(self.screen_buffer.rows - 1, row + 1)  # Wrap to next row
        self.screen_buffer.set_position(row, col)

    async def up(self) -> None:
        """
        Move cursor up one row (s3270 Up() action).

        Raises:
            SessionError: If not connected.
        """
        # Cursor movement doesn't require connection
        row, col = self.screen_buffer.get_position()
        if row > 0:
            row -= 1
        else:
            row = self.screen_buffer.rows - 1  # Wrap to bottom
        self.screen_buffer.set_position(row, col)

    async def down(self) -> None:
        """
        Move cursor down one row (s3270 Down() action).

        Raises:
            SessionError: If not connected.
        """
        # Cursor movement doesn't require connection
        row, col = self.screen_buffer.get_position()
        row += 1
        if row >= self.screen_buffer.rows:
            row = 0  # Wrap to top
        self.screen_buffer.set_position(row, col)

    async def backspace(self) -> None:
        """
        Send backspace (s3270 BackSpace() action).

        Raises:
            SessionError: If not connected.
        """
        await self.left()

    async def tab(self) -> None:
        """
        Move cursor to next field or right (s3270 Tab() action).

        Raises:
            SessionError: If not connected.
        """
        if not self._connected or not self.handler:
            raise SessionError("Session not connected.")

        # Simple implementation: move right
        await self.right()

    async def enter(self) -> None:
        """Send Enter key (s3270 Enter() action)."""
        await self.submit(0x7D)

    async def toggle_insert(self) -> None:
        """Toggle insert mode (s3270 ToggleInsert() action)."""
        self.insert_mode = not self.insert_mode

    async def insert(self) -> None:
        """Insert character at cursor (s3270 Insert() action)."""
        # Toggle insert mode
        self.insert_mode = not self.insert_mode

    async def delete(self) -> None:
        """Delete character at cursor (s3270 Delete() action)."""
        row, col = self.screen_buffer.get_position()
        # Shift characters left in the field
        # Simplified: assume unprotected
        for c in range(col, self.screen_buffer.cols - 1):
            pos = row * self.screen_buffer.cols + c
            next_pos = pos + 1
            if next_pos < self.screen_buffer.size:
                self.screen_buffer.buffer[pos] = self.screen_buffer.buffer[next_pos]
        # Clear last position
        last_pos = row * self.screen_buffer.cols + self.screen_buffer.cols - 1
        if last_pos < self.screen_buffer.size:
            self.screen_buffer.buffer[last_pos] = 0x40  # Space in EBCDIC

    async def erase(self) -> None:
        """Erase character at cursor (s3270 Erase() action)."""
        row, col = self.screen_buffer.get_position()
        pos = row * self.screen_buffer.cols + col
        if pos < self.screen_buffer.size:
            self.screen_buffer.buffer[pos] = 0x40  # Space

    async def erase_eof(self) -> None:
        """Erase from cursor to end of field (s3270 EraseEOF() action)."""
        row, col = self.screen_buffer.get_position()
        # Find end of field
        end_col = self.screen_buffer.cols - 1
        for c in range(col, self.screen_buffer.cols):
            pos = row * self.screen_buffer.cols + c
            if pos < self.screen_buffer.size:
                self.screen_buffer.buffer[pos] = 0x40

    async def end(self) -> None:
        """Move cursor to end of field (s3270 End() action)."""
        row, col = self.screen_buffer.get_position()
        # Move to end of row for simplicity
        self.screen_buffer.set_position(row, self.screen_buffer.cols - 1)

    async def field_end(self) -> None:
        """Move cursor to end of field (s3270 FieldEnd() action)."""
        await self.end()  # Alias

    async def erase_input(self) -> None:
        """Erase all input fields (s3270 EraseInput() action)."""
        for field in self.screen_buffer.fields:
            if not field.protected:
                field.content = b"\x40" * len(field.content)  # Space
                field.modified = True

    async def delete_field(self) -> None:
        """Delete field at cursor (s3270 DeleteField() action)."""
        row, col = self.screen_buffer.get_position()
        field = self.screen_buffer.get_field_at_position(row, col)

        if field and not field.protected:
            # Remove the field from the buffer
            self.screen_buffer.remove_field(field)
            # Update cursor position
            self.screen_buffer.set_position(row, 0)
            # Refresh screen
            self.screen_buffer.update_fields()

    async def dup(self) -> None:
        """Duplicate field (s3270 Dup() action)."""
        # Placeholder
        pass

    async def field_mark(self) -> None:
        """Mark field (s3270 FieldMark() action)."""
        # Placeholder
        pass

    async def flip(self) -> None:
        """Flip between insert and overstrike mode (s3270 Flip() action)."""
        await self.toggle_insert()

    async def move_cursor(self, row: int, col: int) -> None:
        """Move cursor to specified position (s3270 MoveCursor() action)."""
        self.screen_buffer.set_position(row, col)

    async def move_cursor1(self, row: int, col: int) -> None:
        """Move cursor to specified position (1-based) (s3270 MoveCursor1() action)."""
        self.screen_buffer.set_position(row - 1, col - 1)

    async def next_word(self) -> None:
        """Move cursor to next word (s3270 NextWord() action)."""
        # Simple: move right
        await self.right()

    async def previous_word(self) -> None:
        """Move cursor to previous word (s3270 PreviousWord() action)."""
        await self.left()

    async def restore_input(self) -> None:
        """Restore input from saved (s3270 RestoreInput() action)."""
        # Placeholder
        pass

    async def save_input(self) -> None:
        """Save current input (s3270 SaveInput() action)."""
        # Placeholder
        pass

    async def toggle_reverse(self) -> None:
        """Toggle reverse video (s3270 ToggleReverse() action)."""
        # Placeholder
        pass

    async def circum_not(self) -> None:
        """Toggle circumvention of field protection (s3270 CircumNot() action)."""
        self.circumvent_protection = not self.circumvent_protection

    async def cursor_select(self) -> None:
        """Select field at cursor (s3270 CursorSelect() action)."""
        row, col = self.screen_buffer.get_position()
        field = self.screen_buffer.get_field_at_position(row, col)
        if field:
            field.selected = True
            # Update screen buffer to reflect selection if needed
            self.screen_buffer.update_fields()

    async def clear(self) -> None:
        """Clear the screen (s3270 Clear() action)."""
        self.screen_buffer.clear()

    async def close_session(self) -> None:
        """Close the session (s3270 Close() action)."""
        await self.close()
        logger.info("Session closed (Close action)")

    async def close_script(self) -> None:
        """Close the script session (s3270 CloseScript() action)."""
        await self.close()
        logger.info("Script session closed (CloseScript action)")

    async def open(self, host: str, port: int = 23) -> None:
        """Open connection (s3270 Open() action, alias to connect with default port)."""
        await self.connect(host, port)

    async def disconnect(self) -> None:
        """Disconnect from host (s3270 Disconnect() action)."""
        await self.close()
        logger.info(f"Disconnected from {self.host}:{self.port}")

    async def info(self) -> None:
        """Display session information (s3270 Info() action)."""
        print(
            f"Connected: {self._connected}, TN3270 mode: {self.tn3270_mode}, LU: {self._lu_name}"
        )

    async def newline(self) -> None:
        """Move to next line (s3270 Newline() action)."""
        await self.down()
        # Move to start of line
        row, col = self.screen_buffer.get_position()
        self.screen_buffer.set_position(row, 0)

    async def page_down(self) -> None:
        """Page down (s3270 PageDown() action)."""
        for _ in range(self.screen_buffer.rows):
            await self.down()

    async def page_up(self) -> None:
        """Page up (s3270 PageUp() action)."""
        # Move to top of screen
        row, col = self.screen_buffer.get_position()
        self.screen_buffer.set_position(0, col)

    async def paste_string(self, text: str) -> None:
        """Paste string (s3270 PasteString() action)."""
        await self.insert_text(text)

    async def script(self, commands: str) -> None:
        """Execute script (s3270 Script() action)."""
        # Parse and execute commands line by line
        for line in commands.split("\n"):
            cmd = line.strip()
            if cmd and not cmd.startswith("#"):
                # Assume cmd is a method name like "cursor_select"
                # Strip parentheses if present
                if cmd.endswith("()"):
                    cmd = cmd[:-2]
                try:
                    method = getattr(self, cmd, None)
                    if method:
                        await method()
                    else:
                        logger.warning(f"Unknown script command: {cmd}")
                except Exception as e:
                    logger.error(f"Error executing script command '{cmd}': {e}")

    async def set_option(self, option: str, value: str) -> None:
        """Set option (s3270 Set() action)."""
        # Placeholder
        pass

    async def bell(self) -> None:
        """Ring bell (s3270 Bell() action)."""
        print("\a", end="")  # Bell character

    async def pause(self, seconds: float = 1.0) -> None:
        """Pause for seconds (s3270 Pause() action)."""
        import asyncio

        await asyncio.sleep(seconds)

    async def ansi_text(self, data: bytes) -> str:
        """Convert EBCDIC to ANSI text (s3270 AnsiText() action)."""
        return self.ascii(data)

    async def hex_string(self, hex_str: str) -> bytes:
        """Convert hex string to bytes (s3270 HexString() action)."""
        return bytes.fromhex(hex_str)

    async def show(self) -> None:
        """Show screen content (s3270 Show() action)."""
        print(self.screen_buffer.to_text(), end="")

    async def snap(self) -> None:
        """Save screen snapshot (s3270 Snap() action)."""
        # Placeholder
        pass

    async def left2(self) -> None:
        """Move cursor left by 2 positions (s3270 Left2() action)."""
        await self.left()
        await self.left()

    async def right2(self) -> None:
        """Move cursor right by 2 positions (s3270 Right2() action)."""
        await self.right()
        await self.right()

    async def mono_case(self) -> None:
        """Toggle monocase mode (s3270 MonoCase() action)."""
        # Placeholder: toggle case sensitivity
        pass

    async def nvt_text(self, text: str) -> None:
        """Send NVT text (s3270 NvtText() action)."""
        # Send as ASCII
        data = text.encode("ascii")
        await self.send(data)

    async def print_text(self, text: str) -> None:
        """Print text (s3270 PrintText() action)."""
        print(text)

    async def prompt(self, message: str) -> str:
        """Prompt for input (s3270 Prompt() action)."""
        return input(message)

    async def read_buffer(self) -> bytes:
        """Read buffer (s3270 ReadBuffer() action)."""
        return bytes(self.screen_buffer.buffer)

    async def reconnect(self) -> None:
        """Reconnect to host (s3270 Reconnect() action)."""
        await self.close()
        await self.connect()

    async def screen_trace(self) -> None:
        """Trace screen (s3270 ScreenTrace() action)."""
        # Placeholder
        pass

    async def source(self, file: str) -> None:
        """Source script file (s3270 Source() action)."""
        # Placeholder
        pass

    async def subject_names(self) -> None:
        """Display SSL subject names (s3270 SubjectNames() action)."""
        # Placeholder
        pass

    async def sys_req(self) -> None:
        """Send system request (s3270 SysReq() action)."""
        # Placeholder
        pass

    async def toggle_option(self, option: str) -> None:
        """Toggle option (s3270 Toggle() action)."""
        # Placeholder
        pass

    async def trace(self, on: bool) -> None:
        """Enable/disable tracing (s3270 Trace() action)."""
        # Placeholder
        pass

    async def transfer(self, file: str) -> None:
        """Transfer file (s3270 Transfer() action)."""
        # Placeholder
        pass

    async def wait_condition(self, condition: str) -> None:
        """Wait for condition (s3270 Wait() action)."""
        # Placeholder
        pass

    async def compose(self, text: str) -> None:
        """
        Compose special characters or key combinations (s3270 Compose() action).

        Args:
            text: Text to compose, which may include special character sequences.
        """
        # For now, we'll treat this as inserting text
        # A more complete implementation might handle special character sequences
        await self.insert_text(text)

    async def cookie(self, cookie_string: str) -> None:
        """
        Set HTTP cookie for web-based emulators (s3270 Cookie() action).

        Args:
            cookie_string: Cookie in "name=value" format.
        """
        # Initialize cookies dict if it doesn't exist
        if not hasattr(self, "_cookies"):
            self._cookies = {}

        # Parse and store the cookie
        if "=" in cookie_string:
            name, value = cookie_string.split("=", 1)
            self._cookies[name] = value

    async def expect(self, pattern: str, timeout: float = 10.0) -> bool:
        """
        Wait for a pattern to appear on the screen (s3270 Expect() action).

        Args:
            pattern: Text pattern to wait for.
            timeout: Maximum time to wait in seconds.

        Returns:
            True if pattern is found, False if timeout occurs.
        """
        import asyncio
        import time

        start_time = time.time()
        while time.time() - start_time < timeout:
            screen_text = self.screen_buffer.to_text()
            if pattern in screen_text:
                return True
            # Small delay to avoid busy waiting
            await asyncio.sleep(0.1)
        return False

    async def fail(self, message: str) -> None:
        """
        Cause script to fail with a message (s3270 Fail() action).

        Args:
            message: Error message to display.

        Raises:
            Exception: Always raises an exception with the provided message.
        """
        raise Exception(f"Script failed: {message}")

    async def load_resource_definitions(self, file_path: str) -> None:
        """Load resource definitions from xrdb format file (s3270 resource support)."""
        import os

        # Check if file changed
        current_mtime = os.path.getmtime(file_path)
        if self._resource_mtime == current_mtime:
            logger.info(f"Resource file {file_path} unchanged, skipping parse")
            return
        self._resource_mtime = current_mtime

        # Parse xrdb file and store in self.resources
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
        except IOError as e:
            raise SessionError(f"Failed to read resource file {file_path}: {e}")

        self.resources = {}
        i = 0
        while i < len(lines):
            line = lines[i].rstrip("\n\r")
            i += 1

            # Skip comments
            if line.strip().startswith("#") or line.strip().startswith("!"):
                continue

            # Handle multi-line: if ends with \, append next line
            while line.endswith("\\"):
                if i < len(lines):
                    next_line = lines[i].rstrip("\n\r")
                    line = line[:-1].rstrip() + " " + next_line.lstrip()
                    i += 1
                else:
                    break

            if ":" not in line:
                continue

            parts = line.split(":", 1)
            if len(parts) != 2:
                continue

            key = parts[0].strip()
            value = parts[1].strip()

            # Only process s3270.* resources
            if key.startswith("s3270."):
                resource_key = key[6:]  # Remove 's3270.' prefix
                self.resources[resource_key] = value

        logger.info(f"Loaded {len(self.resources)} resources from {file_path}")
        await self.apply_resources()

    async def apply_resources(self) -> None:
        """Apply parsed resources to session state."""
        if not self.resources:
            self.logger.info("No resources to apply")
            return

        for key, value in self.resources.items():
            try:
                if key.startswith("color") and key[5:].isdigit():
                    idx_str = key[5:]
                    if idx_str.isdigit():
                        idx = int(idx_str)
                        if 0 <= idx <= 15:
                            if value.startswith("#") and len(value) == 7:
                                hex_val = value[1:]
                                r = int(hex_val[0:2], 16)
                                g = int(hex_val[2:4], 16)
                                b = int(hex_val[4:6], 16)
                                self.color_palette[idx] = (r, g, b)
                                # Update screen_buffer attributes (simplified: set fg/bg to palette index or value)
                                # For now, set attribute bytes to RGB values, assuming buffer uses 0-255
                                # Actual integration may need palette index mapping
                                if idx < len(self.screen_buffer.attributes) // 3:
                                    # Example: set default fg (idx 1) or bg
                                    if idx == 1:  # default fg
                                        for i in range(
                                            1, len(self.screen_buffer.attributes), 3
                                        ):
                                            self.screen_buffer.attributes[i] = (
                                                r  # Use red as example
                                            )
                                    self.logger.info(
                                        f"Applied color{idx}: RGB({r},{g},{b}) to buffer"
                                    )
                            else:
                                raise ValueError("Invalid hex format")
                        else:
                            self.logger.warning(f"Color index {idx} out of range 0-15")
                elif key == "font":
                    self.font = value
                    self.logger.info(f"Font set to {value}")
                    # Handler may not support, skip
                elif key == "keymap":
                    self.keymap = value
                    self.logger.info(f"Keymap set to {value}")
                    # Handler may not support, skip
                elif key == "ssl":
                    val = value.lower()
                    self.logger.info(
                        f"SSL option set to {val} (cannot change mid-session)"
                    )
                elif key == "model":
                    self.model = value
                    self.color_mode = value == "3"  # 3279 is color model
                    if self.tn3270_mode and self.handler:
                        # If connected, may need to renegotiate model, but skip for now
                        pass
                    self.logger.info(
                        f"Model set to {value}, color mode: {self.color_mode}"
                    )
                else:
                    self.logger.debug(f"Unknown resource {key}: {value}")
            except ValueError as e:
                self.logger.warning(f"Invalid resource {key}: {e}")
                # Don't raise an exception, just continue with other resources
                continue
            except Exception as e:
                self.logger.error(f"Error applying resource {key}: {e}")

        self.logger.info("Resources applied successfully")

    def set_field_attribute(self, field_index: int, attr: str, value: int) -> None:
        """Set field attribute (extended beyond basic protection/numeric)."""
        if 0 <= field_index < len(self.screen_buffer.fields):
            field = self.screen_buffer.fields[field_index]
            if attr == "color":
                # Set color in attributes
                for row in range(field.start[0], field.end[0] + 1):
                    for col in range(field.start[1], field.end[1] + 1):
                        pos = row * self.screen_buffer.cols + col
                        attr_offset = pos * 3 + 1  # Foreground
                        if attr_offset < len(self.screen_buffer.attributes):
                            self.screen_buffer.attributes[attr_offset] = value
            elif attr == "highlight":
                for row in range(field.start[0], field.end[0] + 1):
                    for col in range(field.start[1], field.end[1] + 1):
                        pos = row * self.screen_buffer.cols + col
                        attr_offset = pos * 3 + 2  # Background/highlight
                        if attr_offset < len(self.screen_buffer.attributes):
                            self.screen_buffer.attributes[attr_offset] = value
            # Add more as needed
