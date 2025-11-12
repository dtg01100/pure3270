"""
Mock TN3270 Server Infrastructure.

Provides comprehensive mock TN3270 server implementations for testing
without requiring actual network connections or external servers.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock

from pure3270.emulation.ebcdic import EBCDICCodec
from pure3270.emulation.screen_buffer import ScreenBuffer


class MockTN3270Server:
    """Base mock TN3270 server for testing protocol negotiation and data flows."""

    def __init__(self, model: str = "IBM-3278-2", lu_name: Optional[str] = None):
        self.model = model
        self.lu_name = lu_name
        self.ebcdic_codec = EBCDICCodec()
        self.screen_buffer = ScreenBuffer(rows=24, cols=80)
        self.connected = False
        self.tn3270e_enabled = False
        self.functions_supported = {"BIND-IMAGE": True, "EOR": True}

    async def handle_connection(self, reader: Any, writer: Any) -> None:
        """Handle incoming TN3270 connection with full protocol negotiation."""
        try:
            await self._telnet_negotiation(reader, writer)

            if self.tn3270e_enabled:
                await self._tn3270e_negotiation(reader, writer)

            await self._main_loop(reader, writer)

        except Exception as e:
            logging.getLogger(__name__).error(f"Mock server connection error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _telnet_negotiation(self, reader: Any, writer: Any) -> None:
        """Handle basic Telnet negotiation (WILL/WONT DO/DONT)."""
        # Send IAC WILL TN3270E
        writer.write(b"\xff\xfb\x1b")
        await writer.drain()

        # Handle client response
        data = await reader.readexactly(3)

        if data == b"\xff\xfd\x1b":  # Client agrees to TN3270E
            self.tn3270e_enabled = True
        elif data == b"\xff\xfc\x1b":  # Client refuses TN3270E
            self.tn3270e_enabled = False
        else:
            # Send IAC DONT TN3270E
            writer.write(b"\xff\xfe\x1b")
            await writer.drain()
            self.tn3270e_enabled = False

    async def _tn3270e_negotiation(self, reader: Any, writer: Any) -> None:
        """Handle TN3270E specific negotiation."""
        # Wait for device type request or send our own
        request_sb = b"\xff\xfa\x1b\x00\x01\xff\xf0"  # TN3270E DEVICE-TYPE REQUEST
        writer.write(request_sb)
        await writer.drain()

        # Read device type response
        sb_data = await reader.read(30)  # Read up to 30 bytes for SB

        # Send functions support
        functions_sb = b"\xff\xfa\x1b\x02\x00\x01\x00\x07\x01\xff\xf0"
        writer.write(functions_sb)
        await writer.drain()

        self.connected = True

    async def _main_loop(self, reader: Any, writer: Any) -> None:
        """Main communication loop - send initial screen and handle requests."""
        # Send initial screen data
        await self._send_screen_data(writer)

        # Handle client requests (read until connection closes)
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                await self._handle_client_data(data, writer)
        except asyncio.IncompleteReadError:
            pass  # Normal connection closure

    async def _send_screen_data(self, writer: Any) -> None:
        """Send initial screen data to client."""
        if self.tn3270e_enabled:
            # TN3270E format
            header = b"\x00\x00\x00\x00"  # Type 0, flags 0, seq 0, hlen 0
            screen_size = self.screen_buffer.rows * self.screen_buffer.cols
            screen_data = (
                b"\xf5"  # Write command
                + b"\x40" * screen_size  # All spaces
                + b"\x19"  # EOR (End of Record)
            )
            writer.write(header + screen_data)
            await writer.drain()
        else:
            # Basic TN3270 format
            screen_size = self.screen_buffer.rows * self.screen_buffer.cols
            screen_data = b"\xf5" + b"\x40" * screen_size
            writer.write(screen_data)
            await writer.drain()

    async def _handle_client_data(self, data: bytes, writer: Any) -> None:
        """Handle data received from client."""
        # For testing, just echo back minimal response
        response = b"\xf5" + b"\x40" * 1920  # Write + spaces
        writer.write(response)
        await writer.drain()


class MockTN3270ServerWithAuth(MockTN3270Server):
    """Mock TN3270 server with authentication flow simulation."""

    def __init__(
        self, username: str = "testuser", password: str = "testpass", **kwargs
    ):
        super().__init__(**kwargs)
        self.username = username
        self.password = password
        self.authenticated = False

    async def _main_loop(self, reader: Any, writer: Any) -> None:
        """Main loop with authentication flow."""
        # Send login screen
        await self._send_login_screen(writer)

        # Handle authentication
        await self._handle_authentication(reader, writer)

        if self.authenticated:
            # Continue with normal main loop
            await super()._main_loop(reader, writer)

    async def _send_login_screen(self, writer: Any) -> None:
        """Send a login screen with username and password fields."""
        # Create a simple login screen
        screen_data = (
            b"\xf5"  # Write command
            + b"\x00\x03"  # Set Buffer Address to (0,0)
            + b"LOGIN SCREEN"
            + b"\x00\x00\x20"  # SBA to next line
            + b"Username: "
            + b"\x1d\x00\x00\x20"  # Set Field Attribute (protected) + SBA
            + b"\x00\x00\x30"  # SBA to password line
            + b"Password: "
            + b"\x1d\x00\x00\x40"  # Set Field Attribute (protected) + SBA
            + b"\x19"  # EOR
        )

        if self.tn3270e_enabled:
            header = b"\x00\x00\x00\x00"
            writer.write(header + screen_data)
        else:
            writer.write(screen_data)
        await writer.drain()

    async def _handle_authentication(self, reader: Any, writer: Any) -> None:
        """Handle username/password authentication flow."""
        # Read client input
        try:
            data = await reader.read(1024)

            # Simple authentication check (for testing only)
            if b"testuser" in data and b"testpass" in data:
                self.authenticated = True
                # Send success screen
                await self._send_success_screen(writer)
            else:
                # Send error screen
                await self._send_error_screen(writer)

        except asyncio.IncompleteReadError:
            self.authenticated = False

    async def _send_success_screen(self, writer: Any) -> None:
        """Send success/authenticated screen."""
        screen_data = (
            b"\xf5"  # Write command
            + b"\x00\x03"  # SBA to (0,0)
            + b"Welcome to Mock TN3270 Server"
            + b"\x00\x00\x30"  # SBA to next line
            + b"Authentication successful!"
            + b"\x19"  # EOR
        )

        if self.tn3270e_enabled:
            header = b"\x00\x00\x00\x00"
            writer.write(header + screen_data)
        else:
            writer.write(screen_data)
        await writer.drain()

    async def _send_error_screen(self, writer: Any) -> None:
        """Send authentication error screen."""
        screen_data = (
            b"\xf5"  # Write command
            + b"\x00\x03"  # SBA to (0,0)
            + b"Authentication Failed"
            + b"\x00\x00\x30"  # SBA to next line
            + b"Invalid username or password"
            + b"\x19"  # EOR
        )

        if self.tn3270e_enabled:
            header = b"\x00\x00\x00\x00"
            writer.write(header + screen_data)
        else:
            writer.write(screen_data)
        await writer.drain()


class MockTN3270ServerWithScript(MockTN3270Server):
    """Mock TN3270 server with predefined script response sequence."""

    def __init__(self, script_responses: List[bytes], **kwargs):
        super().__init__(**kwargs)
        self.script_responses = script_responses
        self.current_response = 0

    async def _main_loop(self, reader: Any, writer: Any) -> None:
        """Main loop that follows predefined script."""
        # Send initial screen
        await self._send_screen_data(writer)

        # Handle client data with scripted responses
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break

                if self.current_response < len(self.script_responses):
                    # Send scripted response
                    response = self.script_responses[self.current_response]
                    writer.write(response)
                    await writer.drain()
                    self.current_response += 1
                else:
                    # Fallback to default response
                    response = b"\xf5" + b"\x40" * 1920
                    writer.write(response)
                    await writer.drain()

        except asyncio.IncompleteReadError:
            pass  # Normal connection closure


# Factory functions for common test scenarios


def create_basic_mock_server() -> MockTN3270Server:
    """Create a basic mock TN3270 server for simple tests."""
    return MockTN3270Server()


def create_auth_mock_server(
    username: str = "testuser", password: str = "testpass"
) -> MockTN3270ServerWithAuth:
    """Create a mock TN3270 server with authentication flow."""
    return MockTN3270ServerWithAuth(username=username, password=password)


def create_scripted_mock_server(responses: List[bytes]) -> MockTN3270ServerWithScript:
    """Create a mock TN3270 server with predefined response script."""
    return MockTN3270ServerWithScript(script_responses=responses)


def create_error_mock_server(error_type: str = "connection_reset") -> MockTN3270Server:
    """Create a mock TN3270 server that simulates various error conditions."""
    server = MockTN3270Server()

    if error_type == "connection_reset":
        # Override to simulate connection reset
        async def failing_connection(reader, writer):
            try:
                writer.write(b"\xff\xfb\x1b")
                await writer.drain()
                await asyncio.sleep(0.1)  # Brief delay
                writer.close()  # Simulate abrupt close
            except:
                pass

        server.handle_connection = failing_connection

    return server
