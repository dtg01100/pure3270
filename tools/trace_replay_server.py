#!/usr/bin/env python3
"""
Trace Replay Server for Pure3270 Offline Validation.

This server replays s3270 trace files as TN3270 server responses,
allowing pure3270 to be tested against known protocol exchanges without
requiring access to real TN3270 hosts.

Usage:
    python tools/trace_replay_server.py <trace_file> [--port PORT]
"""

import asyncio
import logging
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Add pure3270 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270.protocol.utils import TN3270_DATA

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TraceEvent:
    """Represents a single event in a s3270 trace."""

    def __init__(self, direction: str, data: bytes, sequence: int = 0):
        self.direction = direction  # 'send' or 'recv'
        self.data = data
        self.sequence = sequence

    @classmethod
    def from_trace_line(cls, line: str, sequence: int) -> Optional["TraceEvent"]:
        """Parse a trace line into a TraceEvent."""
        line = line.strip()

        # Skip comments
        if not line or line.startswith("//"):
            return None

        # Parse send lines: < 0x0   hexdata
        send_match = re.match(r"<\s+0x\w+\s+([0-9a-fA-F]+)", line)
        if send_match:
            hex_data = send_match.group(1)
            data = bytes.fromhex(hex_data)
            return cls("send", data, sequence)

        # Parse recv lines: > 0x0   hexdata
        recv_match = re.match(r">\s+0x\w+\s+([0-9a-fA-F]+)", line)
        if recv_match:
            hex_data = recv_match.group(1)
            data = bytes.fromhex(hex_data)
            return cls("recv", data, sequence)

        return None


class TraceReplayServer:
    """Server that replays s3270 traces as TN3270 responses."""

    def __init__(self, trace_file: str):
        self.trace_file = Path(trace_file)
        self.events: List[TraceEvent] = []
        self.send_index = 0  # Index of next send event to expect
        self.recv_index = 0  # Index of next recv event to send

        self._load_trace()

    def _load_trace(self):
        """Load and parse the trace file."""
        logger.info(f"Loading trace file: {self.trace_file}")

        sequence = 0
        with open(self.trace_file, "r") as f:
            for line in f:
                event = TraceEvent.from_trace_line(line, sequence)
                if event:
                    self.events.append(event)
                    sequence += 1

        logger.info(f"Loaded {len(self.events)} events from trace")

        # Separate send and recv events
        self.send_events = [e for e in self.events if e.direction == "send"]
        self.recv_events = [e for e in self.events if e.direction == "recv"]

        logger.info(
            f"Send events: {len(self.send_events)}, Recv events: {len(self.recv_events)}"
        )

    async def handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Handle a single client connection."""
        client_addr = writer.get_extra_info("peername")
        logger.info(f"New connection from {client_addr}")

        try:
            # Reset indices for this connection
            self.send_index = 0
            self.recv_index = 0

            while True:
                # Send next recv event if available
                if self.recv_index < len(self.recv_events):
                    event = self.recv_events[self.recv_index]
                    logger.debug(f"Sending event {self.recv_index}: {event.data.hex()}")
                    writer.write(event.data)
                    await writer.drain()
                    self.recv_index += 1

                # Wait for client data with timeout
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
                except asyncio.TimeoutError:
                    # No data received, check if we should send more
                    if self.recv_index >= len(self.recv_events):
                        # No more data to send, close connection
                        break
                    continue

                if not data:
                    # Client closed connection
                    break

                # Validate received data against expected send event
                if self.send_index < len(self.send_events):
                    expected = self.send_events[self.send_index]
                    if data == expected.data:
                        logger.debug(f"Event {self.send_index} matches: {data.hex()}")
                        self.send_index += 1
                    else:
                        logger.warning(f"Event {self.send_index} mismatch!")
                        logger.warning(f"Expected: {expected.data.hex()}")
                        logger.warning(f"Received: {data.hex()}")
                        # Continue anyway for now
                        self.send_index += 1
                else:
                    logger.warning(f"Unexpected data from client: {data.hex()}")

        except Exception as e:
            logger.error(f"Error handling connection: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"Connection closed for {client_addr}")

    async def start_server(self, host: str = "127.0.0.1", port: int = 2323):
        """Start the replay server."""
        server = await asyncio.start_server(self.handle_connection, host, port)

        logger.info(f"Trace replay server started on {host}:{port}")
        logger.info(f"Replaying: {self.trace_file.name}")

        try:
            async with server:
                await server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python tools/trace_replay_server.py <trace_file> [--port PORT]")
        sys.exit(1)

    trace_file = sys.argv[1]
    port = 2323

    # Parse optional port argument
    if len(sys.argv) > 2 and sys.argv[2] == "--port":
        port = int(sys.argv[3])

    if not Path(trace_file).exists():
        print(f"Trace file not found: {trace_file}")
        sys.exit(1)

    server = TraceReplayServer(trace_file)
    await server.start_server(port=port)


if __name__ == "__main__":
    asyncio.run(main())
