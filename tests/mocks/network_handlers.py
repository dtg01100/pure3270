"""
Mock Network Connection Handlers.

Provides comprehensive mocking of network I/O operations for testing
network-dependent functionality without requiring actual network connections.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Union
from unittest.mock import AsyncMock, MagicMock

from pure3270.emulation.ebcdic import EBCDICCodec
from pure3270.emulation.screen_buffer import ScreenBuffer


class MockAsyncReader:
    """Mock async reader that simulates network input with configurable responses."""

    def __init__(self, responses: Optional[list] = None, response_delay: float = 0.0):
        """
        Initialize mock async reader.

        Args:
            responses: List of bytes to return on each read call
            response_delay: Delay in seconds before returning response
        """
        self.responses = responses or []
        # Track the identity of the responses list so we can auto-reset the
        # read index when tests replace the list object between reads.
        self._responses_ref_id = id(self.responses)
        self.current_index = 0
        self.response_delay = response_delay
        self.closed = False

    async def read(self, n: int = -1) -> bytes:
        """Read up to n bytes from the mock connection."""
        if self.closed:
            raise ConnectionError("Mock reader is closed")

        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)

        # Auto-reset if the responses list object was replaced by the test
        # code (e.g., scenario["reader"].responses = [new_data]).
        if id(self.responses) != self._responses_ref_id:
            self._responses_ref_id = id(self.responses)
            self.current_index = 0

        if self.current_index >= len(self.responses):
            # Return empty bytes to signal end of data
            return b""

        response = self.responses[self.current_index]
        self.current_index += 1
        return response

    async def readexactly(self, n: int) -> bytes:
        """Read exactly n bytes from the mock connection."""
        if self.closed:
            raise ConnectionError("Mock reader is closed")

        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)

        # Auto-reset on list replacement between reads
        if id(self.responses) != self._responses_ref_id:
            self._responses_ref_id = id(self.responses)
            self.current_index = 0

        if self.current_index >= len(self.responses):
            raise asyncio.IncompleteReadError(b"", 0)

        response = self.responses[self.current_index]
        if len(response) < n:
            raise asyncio.IncompleteReadError(response, n - len(response))

        self.current_index += 1
        return response[:n]

    def close(self) -> None:
        """Close the mock reader."""
        self.closed = True

    def reset(self) -> None:
        """Reset the reader to start of responses."""
        self.current_index = 0
        self.closed = False

    def add_response(self, response: bytes) -> None:
        """Add a response to the queue."""
        self.responses.append(response)


class MockAsyncWriter:
    """Mock async writer that simulates network output with configurable expectations."""

    def __init__(self, expected_data: Optional[list] = None):
        """
        Initialize mock async writer.

        Args:
            expected_data: List of expected data to be written
        """
        self.expected_data = expected_data or []
        self.written_data = []
        self.closed = False
        self.drain_delay = 0.0

    async def write(self, data: bytes) -> None:
        """Write data to the mock connection."""
        if self.closed:
            raise ConnectionError("Mock writer is closed")

        self.written_data.append(data)

        # If we have expected data and this doesn't match, log it
        if self.expected_data and len(self.written_data) <= len(self.expected_data):
            expected = self.expected_data[len(self.written_data) - 1]
            if data != expected:
                logging.getLogger(__name__).warning(
                    f"Mock writer received unexpected data: {data!r}, expected: {expected!r}"
                )

    async def drain(self) -> None:
        """Drain the mock connection (simulate network flush)."""
        if self.closed:
            raise ConnectionError("Mock writer is closed")

        if self.drain_delay > 0:
            await asyncio.sleep(self.drain_delay)

    def close(self) -> None:
        """Close the mock writer."""
        self.closed = True

    def get_written_data(self) -> list:
        """Get all data that has been written."""
        return self.written_data.copy()

    def get_last_written(self) -> Optional[bytes]:
        """Get the most recently written data."""
        return self.written_data[-1] if self.written_data else None

    def reset(self) -> None:
        """Reset the writer."""
        self.written_data = []
        self.closed = False


class MockConnection:
    """Mock network connection that provides reader/writer for testing."""

    def __init__(
        self,
        reader_responses: Optional[list] = None,
        writer_expected: Optional[list] = None,
    ):
        """
        Initialize mock connection.

        Args:
            reader_responses: List of responses the reader should provide
            writer_expected: List of data the writer should expect
        """
        self.reader = MockAsyncReader(reader_responses)
        self.writer = MockAsyncWriter(writer_expected)
        self.connected = True

    def close(self) -> None:
        """Close the mock connection."""
        self.reader.close()
        self.writer.close()
        self.connected = False

    def reset(self) -> None:
        """Reset the mock connection."""
        self.reader.reset()
        self.writer.reset()
        self.connected = True

    def set_response_delay(self, delay: float) -> None:
        """Set delay for reader responses."""
        self.reader.response_delay = delay

    def set_drain_delay(self, delay: float) -> None:
        """Set delay for writer drain operations."""
        self.writer.drain_delay = delay


# Predefined mock connection scenarios for common test cases


def create_basic_telnet_connection() -> MockConnection:
    """Create a basic Telnet negotiation connection."""
    responses = [
        b"\xff\xfd\x1b",  # Client IAC DO TN3270E
        b"\xff\xfa\x1b\x00\x01\xff\xf0",  # Server SB TN3270E DEVICE-TYPE REQUEST (ignored by mock)
        b"\x00\x00\x00\x00" + b"\xf5" + b"\x40" * 1920 + b"\x19",  # Screen data
    ]
    return MockConnection(reader_responses=responses)


def create_tn3270e_connection() -> MockConnection:
    """Create a TN3270E connection with full negotiation."""
    responses = [
        b"\xff\xfd\x1b",  # Client IAC DO TN3270E
        b"\xff\xfa\x1b\x00\x02IBM-3278-2-E\xff\xf0",  # Device type response
        b"\xff\xfa\x1b\x02\x00\x01\x00\x07\x01\xff\xf0",  # Functions support
        b"\x00\x00\x00\x00" + b"\xf5" + b"\x40" * 1920 + b"\x19",  # Screen data
    ]
    return MockConnection(reader_responses=responses)


def create_slow_connection(delay: float = 0.1) -> MockConnection:
    """Create a connection with response delays for timeout testing."""
    connection = create_basic_telnet_connection()
    connection.set_response_delay(delay)
    return connection


def create_error_connection(error_type: str = "connection_reset") -> MockConnection:
    """Create a connection that simulates various network errors."""
    if error_type == "connection_reset":
        responses = [b"\xff\xfd\x1b"]  # Start negotiation
    elif error_type == "timeout":
        # Simulate a slow/unresponsive connection by providing benign data
        # interspersed with a measurable response delay that tests can assert.
        responses = [b"\xff\xfd\x1b"] * 100
    elif error_type == "incomplete_read":
        responses = [b"\xff"]  # Incomplete IAC sequence
    else:
        responses = [b"\xff\xfd\x1b"]

    conn = MockConnection(reader_responses=responses)
    if error_type == "timeout":
        # Ensure timeout scenarios have a non-zero delay so tests can verify
        # that the reader is configured for slow responses.
        conn.set_response_delay(0.1)
    return conn


def create_interactive_connection(screen_updates: list) -> MockConnection:
    """Create a connection for testing interactive scenarios."""
    # Start with basic negotiation
    responses = [b"\xff\xfd\x1b"]  # Client agrees to TN3270E

    # Add screen updates
    for update in screen_updates:
        if isinstance(update, str):
            # Convert string to screen data
            ebcdic = EBCDICCodec()
            screen_data = ebcdic.encode(update)
            screen_with_header = b"\x00\x00\x00\x00" + b"\xf5" + screen_data + b"\x19"
            responses.append(screen_with_header)
        else:
            # Assume bytes
            responses.append(update)

    return MockConnection(reader_responses=responses)


class MockConnectionManager:
    """Manages multiple mock connections for complex test scenarios."""

    def __init__(self):
        self.connections = {}
        self.connection_counter = 0

    def create_connection(self, name: str, connection: MockConnection) -> None:
        """Register a named connection."""
        self.connections[name] = connection

    def get_connection(self, name: str) -> Optional[MockConnection]:
        """Get a named connection."""
        return self.connections.get(name)

    def create_new_connection(self, connection_type: str = "basic") -> MockConnection:
        """Create and register a new connection with auto-generated name."""
        self.connection_counter += 1
        name = f"connection_{self.connection_counter}"

        if connection_type == "basic":
            connection = create_basic_telnet_connection()
        elif connection_type == "tn3270e":
            connection = create_tn3270e_connection()
        elif connection_type == "slow":
            connection = create_slow_connection()
        elif connection_type.startswith("error"):
            error_type = (
                connection_type.split("_", 1)[1]
                if "_" in connection_type
                else "connection_reset"
            )
            connection = create_error_connection(error_type)
        else:
            connection = create_basic_telnet_connection()

        self.create_connection(name, connection)
        return connection

    def reset_all(self) -> None:
        """Reset all connections."""
        for connection in self.connections.values():
            connection.reset()

    def close_all(self) -> None:
        """Close all connections."""
        for connection in self.connections.values():
            connection.close()
