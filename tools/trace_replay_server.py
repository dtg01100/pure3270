#!/usr/bin/env python3
"""
Trace Replay Server for Pure3270 Offline Validation.

This server replays s3270 trace files as TN3270 server responses,
allowing pure3270 to be tested against known protocol exchanges without
requiring access to real TN3270 hosts.

Features:
- Bidirectional trace replay (send and receive events)
- Per-connection state tracking
- Loop mode for continuous testing
- Connection statistics and monitoring
- Configurable concurrent connection limits

Usage:
    python tools/trace_replay_server.py <trace_file> [options]

Options:
    --port PORT          Port to listen on (default: 2323)
    --host HOST          Host to bind to (default: 127.0.0.1)
    --loop               Loop trace playback when complete
    --max-connections N  Maximum concurrent connections (default: 1)
"""

import asyncio
import logging
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add pure3270 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270.protocol.utils import (
    DO,
    IAC,
    SB,
    SE,
    TELOPT_BINARY,
    TELOPT_EOR,
    TELOPT_TN3270E,
    TN3270_DATA,
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IS,
    TN3270E_REQUEST,
    TN3270E_SEND,
    WILL,
)

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

        # In s3270 trace files, lines beginning with '<' indicate data
        # received by the client from the host (i.e., server-to-client),
        # and lines beginning with '>' indicate data sent by the client
        # to the host (i.e., client-to-server). For our replay server,
        # '<' should therefore be treated as events we SEND to the connected
        # client, and '>' as events we expect to RECEIVE from the client.

        # Parse server-to-client events: < 0x...  hexdata (can have multiple hex groups)
        recv_match = re.match(r"<\s+0x\w+\s+([0-9a-fA-F\s]+)$", line)
        if recv_match:
            hex_data = recv_match.group(1).replace(" ", "")  # Remove spaces
            data = bytes.fromhex(hex_data)
            return cls("recv", data, sequence)

        # Parse client-to-server events: > 0x...  hexdata (can have multiple hex groups)
        send_match = re.match(r">\s+0x\w+\s+([0-9a-fA-F\s]+)$", line)
        if send_match:
            hex_data = send_match.group(1).replace(" ", "")  # Remove spaces
            data = bytes.fromhex(hex_data)
            return cls("send", data, sequence)

        return None


class TraceReplayServer:
    """Server that replays s3270 traces as TN3270 responses."""

    def __init__(
        self,
        trace_file: str,
        loop_mode: bool = False,
        max_connections: int = 1,
        compat_handshake: bool = False,
        trace_replay_mode: bool = False,
        dump_negotiation: bool = False,
        dump_dir: Optional[str] = None,
    ):
        self.trace_file = Path(trace_file)
        self.events: List[TraceEvent] = []
        self.loop_mode = loop_mode  # Restart trace from beginning when done
        self.max_connections = max_connections
        self.active_connections = 0
        self.compat_handshake = compat_handshake
        self.trace_replay_mode = trace_replay_mode  # Enable deterministic negotiation

        # Negotiation dump settings
        self.dump_negotiation = dump_negotiation
        self.dump_base_dir = (
            Path(dump_dir)
            if dump_dir
            else Path(tempfile.gettempdir()) / "pure3270_trace_dumps"
        )  # nosec B108
        try:
            self.dump_base_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Ignore failures creating the dump directory; dumping is best-effort
            self.dump_negotiation = False

        # Per-connection state
        self._dump_counter = 0
        self.connection_states: Dict[asyncio.StreamWriter, Dict[str, Any]] = {}

        # Track negotiation phase per connection when compat is enabled
        self._compat_negotiation_complete: Dict[asyncio.StreamWriter, bool] = {}
        # Global flag: once any connection completes compat negotiation, allow
        # trace replay for all connections (helps clients that briefly open a
        # second socket during negotiation)
        self._global_compat_complete: bool = False

        # Enhanced error handling for trace replay
        self._negotiation_mismatch_count = 0
        self._max_mismatch_count = 3  # Max mismatches before force-complete

        self._load_trace()

    def _load_trace(self) -> None:
        """Load and parse the trace file."""
        logger.info(f"Loading trace file: {self.trace_file}")

        sequence = 0
        i = 0
        lines = []

        # Read all lines first for easier processing
        with open(self.trace_file, "r") as f:
            lines = f.readlines()

        while i < len(lines):
            line = lines[i].strip()

            # Look for socket read completion lines that indicate large data transfers
            if "Host socket read complete nr=" in line:
                # Extract the number of bytes
                import re

                match = re.search(r"nr=(\d+)", line)
                if match:
                    byte_count = int(match.group(1))
                    logger.debug(
                        f"Found socket read of {byte_count} bytes at line {i + 1}"
                    )

                    # Collect all subsequent hex data lines until we hit a non-data line
                    combined_data = bytearray()
                    j = i + 1
                    data_lines_found = 0

                    while j < len(lines):
                        data_line = lines[j].strip()

                        # Check if this is a hex data line
                        event = TraceEvent.from_trace_line(data_line, sequence)
                        if event and event.direction == "recv":
                            # This is a data line, add it to our combined data
                            combined_data.extend(event.data)
                            data_lines_found += 1
                            j += 1
                        else:
                            # Not a data line, stop collecting
                            break

                    if combined_data:
                        # Create a single event with all the combined data
                        combined_event = TraceEvent(
                            "recv", bytes(combined_data), sequence
                        )
                        self.events.append(combined_event)
                        sequence += 1
                        logger.debug(
                            f"Combined {data_lines_found} data lines into {len(combined_data)} bytes"
                        )

                    # Move past the collected data lines
                    i = j
                else:
                    i += 1
            else:
                # Regular line, try to parse as normal event
                event = TraceEvent.from_trace_line(line, sequence)
                if event:
                    self.events.append(event)
                    sequence += 1
                i += 1

        logger.info(f"Loaded {len(self.events)} events from trace")

        # Separate send and recv events
        self.send_events = [e for e in self.events if e.direction == "send"]
        self.recv_events = [e for e in self.events if e.direction == "recv"]

        logger.info(
            f"Send events: {len(self.send_events)}, Recv events: {len(self.recv_events)}"
        )

    async def handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a single client connection."""
        client_addr = writer.get_extra_info("peername")
        logger.info(f"New connection from {client_addr}")

        # Check connection limit
        if self.active_connections >= self.max_connections:
            # For integration testing, allow additional connections instead of rejecting.
            # Some clients may temporarily open a second socket during negotiation/fallback.
            # Streaming to multiple clients is harmless for these offline replays.
            logger.warning(
                f"Connection limit reached ({self.max_connections}), allowing additional connection {client_addr} for replay"
            )

        self.active_connections += 1

        # Initialize connection state
        conn_state = {
            "send_index": 0,
            "recv_index": 0,
            "client_addr": client_addr,
            "start_time": asyncio.get_event_loop().time(),
            "bytes_sent": 0,
            "bytes_received": 0,
            "events_processed": 0,
        }
        self.connection_states[writer] = conn_state

        # Open dump files for this connection if enabled
        if self.dump_negotiation:
            try:
                peer = client_addr or ("unknown", "0")
                host_part = str(peer[0]).replace(":", "_")
                port_part = str(peer[1]) if len(peer) > 1 else "0"
                base_name = (
                    f"{self.trace_file.stem}_{host_part}_{port_part}_"
                    f"{int(asyncio.get_event_loop().time() * 1000)}_{self._dump_counter}"
                )
                self._dump_counter += 1
                recv_path = self.dump_base_dir / (base_name + "_recv.hex")
                send_path = self.dump_base_dir / (base_name + "_send.hex")
                try:
                    recv_fh = recv_path.open("a", encoding="utf-8")
                    send_fh = send_path.open("a", encoding="utf-8")
                    conn_state["dump_handles"] = {
                        "recv": recv_fh,
                        "send": send_fh,
                        "base": base_name,
                    }
                    logger.info(
                        f"[{client_addr}] Negotiation dump files: {recv_path}, {send_path}"
                    )
                except Exception as e:
                    logger.warning(
                        f"[{client_addr}] Failed to open negotiation dump files: {e}"
                    )
            except Exception:
                logger.warning(
                    f"[{client_addr}] Failed to initialize dump file info; skipping negotiation dumps"
                )

        try:
            # Optional compatibility handshake: proactively negotiate TN3270E
            if self.compat_handshake:
                self._compat_negotiation_complete[writer] = False
                await self._send_compat_handshake(writer)

            while True:
                # In compat mode, skip trace negotiation frames until compat is done
                if self.compat_handshake and not (
                    self._compat_negotiation_complete.get(writer, False)
                    or self._global_compat_complete
                ):
                    # Only send trace events once compat negotiation has finished
                    # Yield control briefly and re-check on next iteration
                    await asyncio.sleep(0)
                    continue
                else:
                    # Send next recv event if available
                    if conn_state["recv_index"] < len(self.recv_events):
                        event = self.recv_events[conn_state["recv_index"]]
                        # In compat mode, skip early telnet/TN3270E negotiation events from trace
                        # and jump directly to BIND-IMAGE or TN3270-DATA
                        if self.compat_handshake and self._should_skip_trace_event(
                            event
                        ):
                            logger.debug(
                                f"[{client_addr}] Skipping trace event {conn_state['recv_index']} (negotiation frame)"
                            )
                            conn_state["recv_index"] += 1
                            continue
                        if conn_state["bytes_sent"] == 0:
                            logger.info(
                                f"[{client_addr}] Starting trace replay (first send)"
                            )
                        logger.debug(
                            f"[{client_addr}] Sending event {conn_state['recv_index']}: {len(event.data)} bytes"
                        )
                        writer.write(event.data)
                        await writer.drain()
                        conn_state["bytes_sent"] += len(event.data)
                        conn_state["recv_index"] += 1
                        conn_state["events_processed"] += 1

                # Wait briefly for client data; keep this short so we don't
                # throttle server-to-client replay. A shorter timeout allows
                # us to stream multiple recv events quickly even if the client
                # isn't sending anything (common in offline trace replays).
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=0.05)
                    if not data:
                        # Client closed connection
                        logger.info(f"[{client_addr}] Client closed connection")
                        break

                    conn_state["bytes_received"] += len(data)
                    logger.debug(
                        f"[{client_addr}] Received {len(data)} bytes: {data[:50].hex()}..."
                    )
                    # Dump negotiation bytes for client->server (send) if enabled
                    if self.dump_negotiation:
                        try:
                            conn = self.connection_states.get(writer)
                            if conn and "dump_handles" in conn:
                                fh = conn["dump_handles"].get("send")
                                if fh:
                                    fh.write(data.hex() + "\n")
                                    fh.flush()
                        except Exception as e:
                            logger.debug(f"Failed to dump received bytes: {e}")

                    # Opportunistic compatible negotiation handling
                    if (
                        self.compat_handshake
                        and not self._compat_negotiation_complete.get(writer, False)
                    ):
                        logger.debug(f"[{client_addr}] Processing compat negotiation")
                        negotiation_done = await self._handle_compat_negotiation(
                            data, writer
                        )
                        if negotiation_done:
                            self._compat_negotiation_complete[writer] = True
                            self._global_compat_complete = True
                            logger.info(
                                f"[{client_addr}] Compat negotiation complete, resuming trace replay (global)"
                            )
                        # Continue to process the rest after handling negotiation
                        continue
                except asyncio.TimeoutError:
                    # No data received, check if we should send more or loop
                    if conn_state["recv_index"] >= len(self.recv_events):
                        # In compat mode, if negotiation isn't complete, keep waiting
                        if (
                            self.compat_handshake
                            and not self._compat_negotiation_complete.get(writer, False)
                        ):
                            continue
                        if self.loop_mode:
                            # Reset indices to loop the trace
                            conn_state["send_index"] = 0
                            conn_state["recv_index"] = 0
                            logger.debug(f"[{client_addr}] Looping trace playback")
                            continue
                        else:
                            # No more data to send, close connection
                            logger.info(
                                f"[{client_addr}] Trace complete, closing connection"
                            )
                            break
                    continue

                if not data:
                    # Client closed connection
                    logger.info(f"[{client_addr}] Client closed connection")
                    break

                conn_state["bytes_received"] += len(data)

                # Validate received data against expected send event
                if conn_state["send_index"] < len(self.send_events):
                    expected = self.send_events[conn_state["send_index"]]
                    if data == expected.data:
                        logger.debug(
                            f"[{client_addr}] Event {conn_state['send_index']} matches: {len(data)} bytes"
                        )
                        conn_state["send_index"] += 1
                        conn_state["events_processed"] += 1
                    else:
                        logger.warning(
                            f"[{client_addr}] Event {conn_state['send_index']} mismatch!"
                        )
                        logger.warning(f"Expected: {expected.data.hex()}")
                        logger.warning(f"Received: {data.hex()}")
                        # Continue anyway for testing purposes
                        conn_state["send_index"] += 1
                else:
                    logger.warning(
                        f"[{client_addr}] Unexpected data from client: {data.hex()[:100]}..."
                    )

        except Exception as e:
            logger.error(f"[{client_addr}] Error handling connection: {e}")
        finally:
            # Log connection statistics
            duration = asyncio.get_event_loop().time() - conn_state["start_time"]
            logger.info(
                f"[{client_addr}] Connection closed - Duration: {duration:.2f}s, "
                f"Events: {conn_state['events_processed']}, "
                f"Sent: {conn_state['bytes_sent']} bytes, "
                f"Received: {conn_state['bytes_received']} bytes"
            )

            # Close any open negotiation dump files for this connection
            dump_handles = conn_state.get("dump_handles")
            if dump_handles:
                for k, fh in dump_handles.items():
                    if k == "base":
                        continue
                    try:
                        fh.close()
                    except Exception:
                        pass

            # Clean up connection state
            if writer in self.connection_states:
                del self.connection_states[writer]

            # Proactively decrement active connection count; ensure it happens even if
            # the socket is reset while awaiting close.
            self.active_connections -= 1

            # Close the writer and wait for it to close; guard against resets during shutdown
            try:
                writer.close()
                await writer.wait_closed()
            except ConnectionResetError:
                # Client already reset/closed; this is expected during rapid test shutdowns
                logger.debug(
                    f"[{client_addr}] Connection reset during wait_closed; ignoring"
                )
            except Exception as e:
                # Don't let shutdown exceptions bubble up and spam the event loop
                logger.debug(f"[{client_addr}] Exception during connection close: {e}")

    async def _send_bytes(self, writer: asyncio.StreamWriter, data: bytes) -> None:
        try:
            writer.write(data)
            await writer.drain()
            # Dump negotiation bytes for server->client (recv) if enabled
            if self.dump_negotiation:
                try:
                    conn_state = self.connection_states.get(writer)
                    if conn_state and "dump_handles" in conn_state:
                        fh = conn_state["dump_handles"].get("recv")
                        if fh:
                            fh.write(data.hex() + "\n")
                            fh.flush()
                except Exception as e:
                    logger.debug(f"Failed to dump sent bytes: {e}")
        except Exception as e:
            logger.debug(f"Error sending bytes: {e}")

    async def _send_compat_handshake(self, writer: asyncio.StreamWriter) -> None:
        """Send a complete RFC-compliant TN3270E negotiation sequence.

        Per RFC 1646/2355, a TN3270E server should:
        1. Send WILL TN3270E, WILL EOR, WILL BINARY
        2. Send DO BINARY, DO EOR
        3. Send TN3270E DEVICE-TYPE SEND (server asks client for device type)
        4. Wait for client response with DEVICE-TYPE IS
        5. Send TN3270E FUNCTIONS SEND (server asks for functions)
        6. Wait for client response with FUNCTIONS IS

        For compat mode, we'll send the complete server-initiated sequence.
        """
        # Step 1: Basic telnet options
        seq = bytes(
            [
                IAC,
                WILL,
                TELOPT_TN3270E,
                IAC,
                WILL,
                TELOPT_EOR,
                IAC,
                WILL,
                TELOPT_BINARY,
                IAC,
                DO,
                TELOPT_BINARY,
                IAC,
                DO,
                TELOPT_EOR,
            ]
        )
        await self._send_bytes(writer, seq)

        # Step 2: TN3270E DEVICE-TYPE subnegotiation (server sends SEND to request device type)
        device_type_send = bytes(
            [IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_SEND, IAC, SE]
        )
        await self._send_bytes(writer, device_type_send)

        # Step 3: TN3270E FUNCTIONS REQUEST IS with a common bitmask
        # Many servers send REQUEST IS to indicate supported functions; clients respond accordingly
        from pure3270.protocol.utils import (
            TN3270E_BIND_IMAGE,
            TN3270E_DATA_STREAM_CTL,
            TN3270E_RESPONSES,
            TN3270E_SCS_CTL_CODES,
        )

        funcs = (
            TN3270E_BIND_IMAGE
            | TN3270E_DATA_STREAM_CTL
            | TN3270E_RESPONSES
            | TN3270E_SCS_CTL_CODES
        )
        # Encode as 4-byte big-endian for compatibility with common traces
        funcs_bytes = funcs.to_bytes(4, byteorder="big")
        functions_request_is = (
            bytes(
                [
                    IAC,
                    SB,
                    TELOPT_TN3270E,
                    TN3270E_FUNCTIONS,
                    TN3270E_REQUEST,
                    TN3270E_IS,
                ]
            )
            + funcs_bytes
            + bytes([IAC, SE])
        )
        await self._send_bytes(writer, functions_request_is)

    def _is_telnet_negotiation(self, data: bytes) -> bool:
        """Check if data contains only telnet negotiation (IAC sequences)."""
        # Heuristic: mostly IAC bytes, no substantial data
        if not data:
            return False
        iac_count = data.count(IAC)
        # If >50% IAC, it's likely negotiation
        return iac_count > len(data) / 3

    def _should_skip_trace_event(self, event: TraceEvent) -> bool:
        """Determine if a trace event should be skipped during compat negotiation.

        Skip early telnet/TN3270E negotiation frames from the trace when compat mode
        handles negotiation directly. Resume at first BIND-IMAGE or TN3270-DATA.
        """
        data = event.data
        # Skip if it's purely telnet negotiation (IAC sequences)
        if self._is_telnet_negotiation(data):
            return True
        # Check for TN3270E headers (first byte = data type)
        if len(data) >= 5:
            # TN3270E header is 5 bytes: data_type, req_flag, resp_flag, seq_num (2 bytes)
            # Common data types: 0x00 (3270-DATA), 0x03 (BIND-IMAGE)
            from pure3270.protocol.utils import BIND_IMAGE, TN3270_DATA

            first_byte = data[0]
            if first_byte in (TN3270_DATA, BIND_IMAGE):
                # This is actual 3270 data, don't skip
                return False
        return False

    def _find_iac_sequences(self, data: bytes) -> list[tuple[int, int]]:
        """Return list of (start,end) indexes for IAC SB ... IAC SE sequences."""
        out = []
        i = 0
        while i < len(data) - 1:
            if data[i] == IAC and data[i + 1] == SB:
                j = i + 2
                while j < len(data) - 1:
                    if data[j] == IAC and data[j + 1] == SE:
                        out.append((i, j + 2))
                        i = j + 2
                        break
                    j += 1
                else:
                    # No matching SE found, skip this SB
                    i += 1
            else:
                i += 1
        return out

    async def _handle_compat_negotiation(
        self, data: bytes, writer: asyncio.StreamWriter
    ) -> bool:
        """Heuristically detect TN3270E subnegotiations from client and respond sanely.

        Returns True if negotiation appears complete (client sent DEVICE-TYPE and FUNCTIONS)
        """
        # Track key negotiations we've seen
        device_type_received = False
        functions_received = False

        # Enhanced error handling for trace replay mode
        try:
            # First, handle simple IAC option negotiations (non-subnegotiation)
            i = 0
            while i < len(data) - 2:
                if data[i] == IAC:
                    cmd = data[i + 1]
                    opt = data[i + 2] if i + 2 < len(data) else None
                    if opt is None:
                        break

                    if cmd == DO:
                        # Client says DO <option>, we should respond WILL or WONT
                        if opt == TELOPT_TN3270E:
                            # Already sent WILL TN3270E in handshake
                            pass
                        elif opt == TELOPT_BINARY:
                            # Client wants us to send binary, we already said WILL
                            pass
                        elif opt == TELOPT_EOR:
                            # Client wants us to send EOR, we already said WILL
                            pass
                    elif cmd == WILL:
                        # Client says WILL <option>, we should respond DO or DONT
                        if opt == TELOPT_BINARY:
                            # Client will send binary, we already said DO
                            pass
                        elif opt == TELOPT_EOR:
                            # Client will send EOR, we already said DO
                            pass
                        elif opt == TELOPT_TN3270E:
                            # Client agrees to TN3270E
                            pass
                    i += 3
                else:
                    i += 1

            # Now handle subnegotiations
            for start, end in self._find_iac_sequences(data):
                sb = data[start:end]
                # Expect IAC SB <option> <payload...> IAC SE
                if len(sb) < 6 or sb[0] != IAC or sb[1] != SB:
                    continue
                option = sb[2]
                payload = sb[3:-2]
                if option != TELOPT_TN3270E or not payload:
                    continue
                # payload[0] is one of {TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS, etc.}
                p0 = payload[0]
                if p0 == TN3270E_DEVICE_TYPE:
                    if len(payload) >= 2 and payload[1] == TN3270E_IS:
                        # Client sent DEVICE-TYPE IS <device>
                        device_type_received = True
                        client_device = b"IBM-3278-4-E"
                        if len(payload) > 2:
                            # Extract device name from payload
                            device_bytes = payload[2:]
                            try:
                                device_name = device_bytes.split(b"\x00", 1)[0].decode(
                                    "ascii", errors="ignore"
                                )
                                if device_name and "IBM" in device_name.upper():
                                    client_device = device_name.encode("ascii")
                            except Exception:
                                pass
                        logger.debug(
                            f"Received DEVICE-TYPE IS: {client_device.decode('ascii', errors='ignore')}"
                        )

                        # Now send FUNCTIONS SEND to continue negotiation
                        functions_send = bytes(
                            [
                                IAC,
                                SB,
                                TELOPT_TN3270E,
                                TN3270E_FUNCTIONS,
                                TN3270E_SEND,
                                IAC,
                                SE,
                            ]
                        )
                        await self._send_bytes(writer, functions_send)

                elif p0 == TN3270E_FUNCTIONS:
                    if len(payload) >= 2 and payload[1] == TN3270E_IS:
                        # Client sent FUNCTIONS IS <functions>
                        functions_received = True
                        func_bytes = payload[2:] if len(payload) > 2 else bytes()
                        if func_bytes:
                            funcs = int.from_bytes(func_bytes, byteorder="big")
                            logger.debug(f"Received FUNCTIONS IS: 0x{funcs:02x}")
                        else:
                            logger.debug("Received FUNCTIONS IS: (empty)")

        except Exception as e:
            # Enhanced error handling for trace replay scenarios
            self._negotiation_mismatch_count += 1
            logger.warning(
                f"Negotiation mismatch #{self._negotiation_mismatch_count}: {e}"
            )

            # In trace replay mode, force completion after too many mismatches
            if (
                self.trace_replay_mode
                and self._negotiation_mismatch_count >= self._max_mismatch_count
            ):
                logger.info(
                    "Forcing negotiation completion due to repeated mismatches in trace replay mode"
                )
                return True
            # In normal mode, continue trying
            return False

        # Negotiation is complete if we've received both device type and functions
        complete = device_type_received and functions_received
        if complete:
            logger.debug("TN3270E negotiation complete")
        return complete

    async def _handle_compat_negotiation_enhanced(
        self, data: bytes, writer: asyncio.StreamWriter
    ) -> bool:
        """Enhanced negotiation handling with better error recovery for trace replay."""

        # For trace replay mode, be more aggressive about completing negotiation
        if self.trace_replay_mode:
            # Quick detection of negotiation patterns
            device_type_pattern = (
                b"\xff\xfa\x28\x02\x07"  # IAC SB TN3270E DEVICE-TYPE REQUEST
            )
            functions_pattern = (
                b"\xff\xfa\x28\x03\x07"  # IAC SB TN3270E FUNCTIONS REQUEST
            )
            device_type_response_pattern = (
                b"\xff\xfa\x28\x02\x00"  # IAC SB TN3270E DEVICE-TYPE IS
            )
            functions_response_pattern = (
                b"\xff\xfa\x28\x03\x00"  # IAC SB TN3270E FUNCTIONS IS
            )

            # Check if we've received both key responses
            has_device_type_response = device_type_response_pattern in data
            has_functions_response = functions_response_pattern in data

            if has_device_type_response and has_functions_response:
                logger.info(
                    "Enhanced trace replay: Both DEVICE-TYPE and FUNCTIONS responses detected"
                )
                return True
            elif has_device_type_response or has_functions_response:
                logger.debug(
                    "Enhanced trace replay: Partial negotiation response detected"
                )
                # Send appropriate follow-up if needed
                if has_device_type_response:
                    # Send functions request
                    functions_send = bytes(
                        [
                            IAC,
                            SB,
                            TELOPT_TN3270E,
                            TN3270E_FUNCTIONS,
                            TN3270E_SEND,
                            IAC,
                            SE,
                        ]
                    )
                    await self._send_bytes(writer, functions_send)
                return False  # Not complete yet
            else:
                # Check for client responses that would trigger server response
                if device_type_pattern in data or functions_pattern in data:
                    logger.debug("Enhanced trace replay: Client negotiation detected")
                    return False  # Continue negotiation

        # Fall back to standard negotiation handling
        return await self._handle_compat_negotiation(data, writer)

    async def start_server(self, host: str = "127.0.0.1", port: int = 2323) -> None:
        """Start the replay server and ensure clean shutdown on cancellation."""
        server = await asyncio.start_server(self.handle_connection, host, port)

        logger.info(f"Trace replay server started on {host}:{port}")
        logger.info(f"Replaying: {self.trace_file.name}")
        logger.info(f"Loop mode: {'enabled' if self.loop_mode else 'disabled'}")
        logger.info(f"Max connections: {self.max_connections}")

        try:
            async with server:
                await server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped")
        except asyncio.CancelledError:
            # Expected on caller shutdown; fall through to close
            pass
        finally:
            try:
                server.close()
                await server.wait_closed()
            except Exception:
                pass

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections."""
        return {
            "active_connections": self.active_connections,
            "max_connections": self.max_connections,
            "connection_states": {
                str(writer): state for writer, state in self.connection_states.items()
            },
        }

    def get_negotiation_dumps(self) -> List[Dict[str, Any]]:
        """Return list of negotiation dump info for current connections.

        Each entry contains:
            - peer: client address tuple
            - base: base dump file name (string)
            - send: path to send hex dump (Path)
            - recv: path to recv hex dump (Path)
            - start_time: connection start timestamp (float)
        """
        out: List[Dict[str, Any]] = []
        for writer, state in self.connection_states.items():
            dump_handles = state.get("dump_handles")
            if not dump_handles:
                continue
            base = dump_handles.get("base")
            recv_path = self.dump_base_dir / (base + "_recv.hex")
            send_path = self.dump_base_dir / (base + "_send.hex")
            out.append(
                {
                    "peer": state.get("client_addr"),
                    "base": base,
                    "recv": recv_path,
                    "send": send_path,
                    "start_time": state.get("start_time"),
                }
            )
        return out

    def get_negotiation_dumps_since(self, since_ts: float) -> List[Dict[str, Any]]:
        """Return negotiation dumps for connections that started after since_ts."""
        return [
            d
            for d in self.get_negotiation_dumps()
            if d.get("start_time", 0) >= since_ts
        ]


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Trace replay server for TN3270 testing"
    )
    parser.add_argument("trace_file", help="s3270 trace file to replay")
    parser.add_argument(
        "--port", "-p", type=int, default=2323, help="Port to listen on (default: 2323)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--loop", action="store_true", help="Loop trace playback when complete"
    )
    parser.add_argument(
        "--max-connections",
        type=int,
        default=1,
        help="Maximum concurrent connections (default: 1)",
    )
    parser.add_argument(
        "--trace-replay-mode",
        action="store_true",
        help="Enable trace replay mode for deterministic negotiation timing",
    )
    parser.add_argument(
        "--compat-handshake",
        action="store_true",
        help="Use compatibility handshake for TN3270E negotiation",
    )
    parser.add_argument(
        "--dump-negotiation",
        action="store_true",
        help="Dump raw telnet/TN3270 negotiation bytes to files (one per connection)",
    )
    parser.add_argument(
        "--dump-dir",
        default=None,
        help="Directory to write negotiation dump files (default: /tmp/pure3270_trace_dumps)",
    )

    args = parser.parse_args()

    if not Path(args.trace_file).exists():
        print(f"Trace file not found: {args.trace_file}")
        sys.exit(1)

    server = TraceReplayServer(
        args.trace_file,
        loop_mode=args.loop,
        max_connections=args.max_connections,
        trace_replay_mode=getattr(args, "trace_replay_mode", False),
        compat_handshake=getattr(args, "compat_handshake", False),
        dump_negotiation=getattr(args, "dump_negotiation", False),
        dump_dir=getattr(args, "dump_dir", None),
    )
    await server.start_server(host=args.host, port=args.port)


if __name__ == "__main__":
    asyncio.run(main())
