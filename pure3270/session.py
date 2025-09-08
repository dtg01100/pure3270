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

    def __init__(self, host: str, port: int = 23, ssl_context: Optional[Any] = None):
        """
        Initialize a synchronous session.
        
        Args:
            host: The target host IP or hostname.
            port: The target port (default 23 for Telnet).
            ssl_context: Optional SSL context for secure connections.
        
        Raises:
            ConnectionError: If connection initialization fails.
        """
        self._host = host
        self._port = port
        self._ssl_context = ssl_context
        self._async_session = None

    def connect(self) -> None:
        """Connect to the 3270 host synchronously."""
        asyncio.run(self._connect_async())

    async def _connect_async(self) -> None:
        """Async connect helper."""
        self._async_session = AsyncSession(self._host, self._port, self._ssl_context)
        await self._async_session.connect()

    def send(self, data: bytes) -> None:
        """
        Send data to the session.
        
        Args:
            data: Bytes to send.
        
        Raises:
            SessionError: If send fails.
        """
        asyncio.run(self._send_async(data))

    async def _send_async(self, data: bytes) -> None:
        """Async send helper."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        await self._async_session.send(data)

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
        return asyncio.run(self._read_async(timeout))

    async def _read_async(self, timeout: float = 5.0) -> bytes:
        """Async read helper."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        return await self._async_session.read(timeout)

    def execute_macro(self, macro: str, vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
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
        return asyncio.run(self._execute_macro_async(macro, vars))

    async def _execute_macro_async(self, macro: str, vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Async macro helper."""
        if not self._async_session:
            raise SessionError("Session not connected.")
        return await self._async_session.execute_macro(macro, vars)

    def close(self) -> None:
        """Close the session synchronously."""
        asyncio.run(self._close_async())

    async def _close_async(self) -> None:
        """Async close helper."""
        if self._async_session:
            await self._async_session.close()
            self._async_session = None

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
    def __init__(self, host: str, port: int = 23, ssl_context: Optional[Any] = None):
        """
        Initialize the async session.
        
        Args:
            host: The target host IP or hostname.
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

    async def connect(self) -> None:
        """
        Establish connection to the 3270 host.
        
        Performs TN3270 negotiation.
        
        Raises:
            ConnectionError: On connection failure.
            NegotiationError: On negotiation failure.
        """
        reader, writer = await asyncio.open_connection(self.host, self.port, ssl=self.ssl_context)
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
            logger.warning(f"TN3270 negotiation failed, falling back to ASCII mode: {e}")
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
            await self.send(cmd.encode('ascii'))
            output = await self.read()
            return output.decode('ascii', errors='ignore')
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
        if condition == 'connected':
            return self._connected
        elif condition == 'error':
            # Simplified: assume no error for now; could track last_error
            return False
        else:
            raise MacroError(f"Unknown condition: {condition}")

    async def execute_macro(self, macro: str, vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
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
            macro = macro.replace(f'${{{key}}}', str(value))
        
        # Parse commands
        commands = [cmd.strip() for cmd in macro.split(';') if cmd.strip()]
        results = {'success': True, 'output': [], 'vars': vars.copy()}
        i = 0
        while i < len(commands):
            cmd = commands[i]
            try:
                if cmd.startswith('if '):
                    if ':' not in cmd:
                        raise MacroError("Invalid if syntax: missing ':'")
                    condition_part, command_part = cmd.split(':', 1)
                    condition = condition_part[3:].strip()
                    command_part = command_part.strip()
                    if self._evaluate_condition(condition):
                        sub_output = await self._execute_single_command(command_part, vars)
                        results['output'].append(sub_output)
                elif cmd.startswith('macro '):
                    macro_name = cmd[6:].strip()
                    nested_macro = vars.get(macro_name)
                    if nested_macro:
                        sub_results = await self.execute_macro(nested_macro, vars)
                        results['output'].append(sub_results)
                    else:
                        raise MacroError(f"Nested macro '{macro_name}' not found in vars")
                else:
                    # Backward compatible simple command
                    sub_output = await self._execute_single_command(cmd, vars)
                    results['output'].append(sub_output)
            except Exception as e:
                results['success'] = False
                results['output'].append(f"Error in command '{cmd}': {e}")
            i += 1
        return results

    async def close(self) -> None:
        """Close the async session."""
        if self._handler:
            await self._handler.close()
        self._handler = None
        self._connected = False

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
        Execute a list of macro commands.
        
        Args:
            commands: List of macro command strings.
                     Supported formats:
                     - 'String(text)' - Send text as EBCDIC
                     - 'key Enter' - Send Enter key
                     - 'key <keyname>' - Send other keys
        
        Raises:
            MacroError: If command parsing or execution fails.
            SessionError: If not connected.
        """
        if not self._connected or not self.handler:
            raise SessionError("Session not connected.")
        
        from .protocol.data_stream import DataStreamSender
        from .emulation.ebcdic import translate_ascii_to_ebcdic
        
        sender = DataStreamSender()
        
        for command in commands:
            command = command.strip()
            try:
                if command.startswith('String(') and command.endswith(')'):
                    # Extract text from String(text)
                    text = command[7:-1]  # Remove 'String(' and ')'
                    # Convert to EBCDIC and send
                    ebcdic_data = translate_ascii_to_ebcdic(text)
                    await self.send(ebcdic_data)
                elif command.startswith('key '):
                    # Extract key name
                    key_name = command[4:].strip()
                    if key_name.lower() == 'enter':
                        # Send Enter AID (0x7D)
                        key_data = sender.build_key_press(0x7D)
                        await self.send(key_data)
                    else:
                        raise MacroError(f"Unsupported key: {key_name}")
                else:
                    raise MacroError(f"Unsupported command format: {command}")
            except Exception as e:
                raise MacroError(f"Failed to execute command '{command}': {e}")
