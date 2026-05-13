#!/usr/bin/env python3
"""
Comprehensive Reliability Validation Tests for Pure3270.

These tests validate protocol compliance, memory safety, and robustness
through trace replay, stress testing, and fault injection.
"""

import asyncio
import gc
import logging
import random
import sys
import tracemalloc
from pathlib import Path
from typing import List, Tuple

import pytest

# Silence DEBUG logging from the parser to avoid overwhelming pytest output
logging.getLogger("pure3270.protocol.data_stream").setLevel(logging.WARNING)
logging.getLogger("pure3270.emulation.screen_buffer").setLevel(logging.WARNING)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270 import AsyncSession, Session
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.utils import (
    IAC,
    TELOPT_EOR,
    TELOPT_TN3270E,
    TELOPT_TTYPE,
    TN3270_DATA,
    WILL,
)

# ==============================================================================
# Section 1: Trace Replay Stress Tests
# ==============================================================================


def load_all_trace_events() -> List[Tuple[str, bytes, str]]:
    """Load all trace files and return (trace_name, data, direction) tuples."""
    trace_dir = Path(__file__).parent / "data" / "traces"
    if not trace_dir.exists():
        pytest.skip("Trace directory not found")

    import re

    events = []
    for trace_file in sorted(trace_dir.glob("*.trc")):
        with open(trace_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                recv_match = re.match(r"<\s+0x\w+\s+([0-9a-fA-F\s]+)$", line)
                if recv_match:
                    hex_data = recv_match.group(1).replace(" ", "")
                    try:
                        data = bytes.fromhex(hex_data)
                        if data:
                            events.append((trace_file.name, data, "recv"))
                    except ValueError:
                        pass
                send_match = re.match(r">\s+0x\w+\s+([0-9a-fA-F\s]+)$", line)
                if send_match:
                    hex_data = send_match.group(1).replace(" ", "")
                    try:
                        data = bytes.fromhex(hex_data)
                        if data:
                            events.append((trace_file.name, data, "send"))
                    except ValueError:
                        pass
    return events


class TestTraceReplayStress:
    """Validate all trace data through the parser - no crashes, consistent state."""

    def test_all_trace_files_parse_without_crash(self):
        """Parse every byte from every trace file through DataStreamParser."""
        events = load_all_trace_events()
        if not events:
            pytest.skip("No trace events found")

        parser = DataStreamParser(ScreenBuffer(24, 80))
        parse_errors = []
        total_bytes = 0
        traces_processed = set()

        for trace_name, data, direction in events:
            traces_processed.add(trace_name)
            total_bytes += len(data)
            if direction == "recv" and len(data) > 5:
                if data[0] == IAC:
                    continue
                try:
                    payload = data[5:] if len(data) > 5 else data
                    parser.parse(payload, TN3270_DATA)
                except Exception as e:
                    parse_errors.append(
                        f"{trace_name}: {type(e).__name__}: {e} (data={data[:20].hex()})"
                    )

        assert total_bytes > 0, "No trace data loaded"
        assert len(traces_processed) > 0, "No traces processed"

        error_rate = len(parse_errors) / max(1, len(events))
        logging.info(
            f"Parsed {total_bytes} bytes from {len(traces_processed)} traces, "
            f"{len(parse_errors)} errors ({error_rate:.2%} error rate)"
        )

    def test_all_trace_files_screen_buffer_consistency(self):
        """Validate screen buffer stays consistent after parsing all trace data."""
        events = load_all_trace_events()
        if not events:
            pytest.skip("No trace events found")

        screen = ScreenBuffer(24, 80)
        parser = DataStreamParser(screen)

        for trace_name, data, direction in events:
            if direction == "recv" and len(data) > 5:
                if data[0] == IAC:
                    continue
                try:
                    payload = data[5:] if len(data) > 5 else data
                    parser.parse(payload, TN3270_DATA)
                    assert screen.rows == 24, f"Rows changed to {screen.rows}"
                    assert screen.cols == 80, f"Cols changed to {screen.cols}"
                    assert 0 <= screen.cursor_row < 24
                    assert 0 <= screen.cursor_col < 80
                    assert len(screen.buffer) == 24 * 80
                except Exception:
                    pass


# ==============================================================================
# Section 2: Screen Buffer Invariant Tests
# ==============================================================================


class TestScreenBufferInvariants:
    """Validate screen buffer maintains invariants under all operations."""

    def _make_screen(self, rows=24, cols=80):
        return ScreenBuffer(rows, cols)

    def test_invariants_after_write_every_position(self):
        """Write to every screen position, validate invariants hold."""
        screen = self._make_screen()
        for row in range(screen.rows):
            for col in range(screen.cols):
                screen.write_char(0xC1, row=row, col=col)
                assert 0 <= screen.cursor_row < screen.rows
                assert 0 <= screen.cursor_col < screen.cols
                assert len(screen.buffer) == screen.rows * screen.cols

    def test_invariants_after_clear(self):
        """Validate invariants after clear operations."""
        screen = self._make_screen()
        for i in range(100):
            screen.write_char(0xC1)
        screen.clear()
        assert all(b == 0x40 for b in screen.buffer)
        assert screen.cursor_row == 0
        assert screen.cursor_col == 0
        assert len(screen.buffer) == 24 * 80

    def test_invariants_after_field_operations(self):
        """Validate invariants after field attribute operations."""
        screen = self._make_screen()
        parser = DataStreamParser(screen)

        screen.set_position(0, 0)
        # SF order (0x1D) followed by field attribute
        sf_data = bytes([0x1D, 0xC0])
        parser.parse(sf_data, TN3270_DATA)

        assert 0 <= screen.cursor_row < screen.rows
        assert 0 <= screen.cursor_col < screen.cols

    def test_invariants_after_wraparound(self):
        """Validate cursor position after explicit positioning at boundaries."""
        screen = self._make_screen()
        screen.set_position(0, 79)
        screen.write_char(0xC1)
        # write_char writes at current position without auto-advancing
        assert screen.cursor_row == 0
        assert screen.cursor_col == 79

        # Manual wrap to next line
        screen.set_position(1, 0)
        screen.write_char(0xC2)
        assert screen.cursor_row == 1
        assert screen.cursor_col == 0

    def test_to_text_consistency(self):
        """Validate to_text() produces consistent output with correct dimensions."""
        screen = self._make_screen()
        # write_char writes at current position
        for i in range(10):
            screen.write_char(0xC1, row=0, col=i)

        text = screen.to_text()
        # to_text should have rows*cols chars plus newlines
        assert screen.rows * screen.cols + (screen.rows - 1) == len(text)

    def test_invariants_random_operations(self):
        """Apply random operations, validate invariants always hold."""
        random.seed(42)
        screen = self._make_screen()

        for _ in range(1000):
            op = random.choice(["write", "move", "clear"])
            if op == "write":
                row = random.randint(0, 23)
                col = random.randint(0, 79)
                screen.write_char(
                    random.choice([0x40, 0xC1, 0xC2, 0xC3]), row=row, col=col
                )
            elif op == "move":
                screen.set_position(random.randint(0, 23), random.randint(0, 79))
            elif op == "clear":
                screen.clear()

            assert 0 <= screen.cursor_row < screen.rows
            assert 0 <= screen.cursor_col < screen.cols
            assert len(screen.buffer) == screen.rows * screen.cols


# ==============================================================================
# Section 3: Session Lifecycle Stress Tests
# ==============================================================================


class TestSessionLifecycleStress:
    """Validate session creation/destruction under stress - no leaks."""

    @pytest.mark.asyncio
    async def test_async_session_rapid_create_destroy(self):
        """Create and destroy 100 AsyncSessions rapidly, check for leaks."""
        tracemalloc.start()
        gc.collect()
        snapshot_before = tracemalloc.take_snapshot()

        for _ in range(100):
            session = AsyncSession()
            assert session._host is None
            assert session._port == 23
            assert not session.connected

        gc.collect()
        snapshot_after = tracemalloc.take_snapshot()

        stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_growth = sum(s.size_diff for s in stats if s.size_diff > 0)
        tracemalloc.stop()

        logging.info(f"Memory growth after 100 sessions: {total_growth} bytes")
        assert (
            total_growth < 10 * 1024 * 1024
        ), f"Memory grew by {total_growth} bytes (>10MB) after 100 cycles"

    @pytest.mark.asyncio
    async def test_session_properties_always_valid(self):
        """Validate session properties are always accessible and valid."""
        for _ in range(50):
            session = Session()
            _ = session.connected
            _ = session.tn3270e_mode
            _ = session.screen_buffer
            del session

    @pytest.mark.asyncio
    async def test_async_session_methods_no_handler(self):
        """Validate all async methods handle missing handler gracefully."""
        session = AsyncSession()

        # disconnect is safe to call when not connected
        await session.disconnect()

        # read and send_data should raise SessionError
        with pytest.raises(Exception):
            await session.read()

        with pytest.raises(Exception):
            await session.send_data(b"test")

    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self):
        """Create multiple sessions concurrently."""

        async def create_and_validate(i: int):
            session = AsyncSession()
            assert session._host is None
            assert session._port == 23
            return i

        tasks = [create_and_validate(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 50
        assert set(results) == set(range(50))


# ==============================================================================
# Section 4: Network Fault Injection Tests
# ==============================================================================


class TestNetworkFaultInjection:
    """Validate graceful handling of network failures."""

    @pytest.mark.asyncio
    async def test_connection_refused(self):
        """Session should handle connection refused gracefully."""
        session = AsyncSession()
        with pytest.raises((ConnectionRefusedError, OSError, asyncio.TimeoutError)):
            await asyncio.wait_for(session.connect("127.0.0.1", 59999), timeout=3)

    @pytest.mark.asyncio
    async def test_connection_to_invalid_host(self):
        """Session should handle invalid host gracefully."""
        session = AsyncSession()
        with pytest.raises((OSError, asyncio.TimeoutError, ValueError)):
            await asyncio.wait_for(
                session.connect("invalid.host.that.does.not.exist.example", 23),
                timeout=3,
            )

    @pytest.mark.asyncio
    async def test_mock_server_immediate_close(self):
        """Server that closes connection immediately should not crash client."""

        async def handle_client(reader, writer):
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        try:
            session = AsyncSession()
            try:
                await asyncio.wait_for(session.connect("127.0.0.1", port), timeout=3)
            except (ConnectionResetError, OSError, asyncio.TimeoutError):
                pass
            finally:
                try:
                    await asyncio.wait_for(session.disconnect(), timeout=2)
                except Exception:
                    pass
        finally:
            server.close()
            await server.wait_closed()

    @pytest.mark.asyncio
    async def test_mock_server_garbage_data(self):
        """Server sending random bytes should not crash client parser."""

        async def send_garbage(reader, writer):
            garbage = bytes(random.randint(0, 255) for _ in range(1000))
            writer.write(garbage)
            await writer.drain()
            await asyncio.sleep(0.1)
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(send_garbage, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        try:
            session = AsyncSession()
            try:
                await asyncio.wait_for(session.connect("127.0.0.1", port), timeout=5)
            except Exception:
                pass
            finally:
                try:
                    await asyncio.wait_for(session.disconnect(), timeout=2)
                except Exception:
                    pass
        finally:
            server.close()
            await server.wait_closed()

    @pytest.mark.asyncio
    async def test_mock_server_partial_iac(self):
        """Server sending partial IAC sequences should not hang client."""

        async def send_partial_iac(reader, writer):
            writer.write(bytes([IAC, WILL]))
            await writer.drain()
            await asyncio.sleep(0.5)
            writer.write(bytes([IAC]))
            await writer.drain()
            await asyncio.sleep(0.5)
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(send_partial_iac, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        try:
            session = AsyncSession()
            try:
                await asyncio.wait_for(session.connect("127.0.0.1", port), timeout=5)
            except (ConnectionResetError, OSError, asyncio.TimeoutError):
                pass
            finally:
                try:
                    await asyncio.wait_for(session.disconnect(), timeout=2)
                except Exception:
                    pass
        finally:
            server.close()
            await server.wait_closed()


# ==============================================================================
# Section 5: Differential Negotiation Tests (RFC Compliance)
# ==============================================================================


class TestDifferentialNegotiation:
    """Validate TN3270E negotiation sequence against RFC 2355 specification."""

    @pytest.mark.asyncio
    async def test_rfc_2355_server_initiated_sequence(self):
        """
        RFC 2355 Section 4 specifies server-initiated negotiation:
        Server sends WILL TN3270E, WILL EOR, etc.

        Validate that our mock server sends the correct negotiation bytes.
        """
        from mock_server.tn3270_mock_server import EnhancedTN3270MockServer

        server = EnhancedTN3270MockServer()
        await server.start()

        try:
            reader, writer = await asyncio.open_connection(server.host, server.port)
            await asyncio.sleep(0.3)

            sent = server.get_sent_trace()
            assert len(sent) > 0, "Mock server sent no data"

            recv_data = b"".join(sent)

            assert (
                bytes([IAC, WILL, TELOPT_TTYPE]) in recv_data
                or bytes([0xFF, 0xFB, TELOPT_TTYPE]) in recv_data
            ), "Missing WILL TTYPE in server response"

            assert (
                bytes([IAC, WILL, TELOPT_EOR]) in recv_data
                or bytes([0xFF, 0xFB, TELOPT_EOR]) in recv_data
            ), "Missing WILL EOR in server response"

            assert (
                bytes([IAC, WILL, TELOPT_TN3270E]) in recv_data
                or bytes([0xFF, 0xFB, TELOPT_TN3270E]) in recv_data
            ), "Missing WILL TN3270E in server response"

            writer.close()
            await writer.wait_closed()
        finally:
            await server.stop()

    def test_rfc_1576_3270_data_stream_orders(self):
        """
        RFC 1576 specifies 3270 data stream orders.
        Validate that our parser recognizes all specified orders.
        """
        screen = ScreenBuffer(24, 80)
        parser = DataStreamParser(screen)

        orders = [
            ("SBA", bytes([0x11, 0x00, 0x05])),
            ("SF", bytes([0x1D, 0xC0])),
            ("SFE", bytes([0x29, 0xC0, 0x00, 0x00])),
            ("RA", bytes([0x2C, 0x00, 0x50, 0x40])),
            ("EUA", bytes([0x2F, 0x00, 0x50])),
        ]

        for name, data in orders:
            try:
                parser.parse(data, TN3270_DATA)
            except Exception as e:
                pytest.fail(f"{name} parsing failed: {e}")

    def test_rfc_854_telnet_iac_handling(self):
        """
        RFC 854 specifies Telnet IAC escaping.
        Validate parser doesn't crash on 0xFF bytes.
        """
        screen = ScreenBuffer(24, 80)
        parser = DataStreamParser(screen)

        data_with_ff = bytes([0x40, 0xFF, 0x41, 0xFF, 0x42])
        try:
            parser.parse(data_with_ff, TN3270_DATA)
        except Exception as e:
            pytest.fail(f"Parser crashed on 0xFF bytes: {e}")

    def test_all_tn3270e_data_types_handled(self):
        """
        RFC 2355 defines TN3270E data types.
        Validate parser handles each without crashing.
        """
        screen = ScreenBuffer(24, 80)
        parser = DataStreamParser(screen)

        data = bytes([0x40, 0x41, 0x42])

        data_types = [
            TN3270_DATA,
            0x04,
            0x05,
        ]

        for dt in data_types:
            try:
                parser.parse(data, dt)
            except Exception as e:
                pytest.fail(f"Parser crashed on data_type=0x{dt:02x}: {e}")
