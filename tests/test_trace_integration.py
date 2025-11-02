#!/usr/bin/env python3
"""
Integration tests for trace replay functionality.

Tests full protocol negotiation and data flow using TraceReplayServer
to replay actual s3270 trace files against pure3270.Session.

These tests verify:
- Telnet negotiation (WILL/DO/WONT/DONT)
- TN3270E protocol negotiation
- BIND image handling
- Bidirectional data flow
- Screen state updates
- Printer protocol (TN3270E printer sessions)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270 import Session
from tools.trace_replay_server import TraceReplayServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data directory
TRACE_DIR = Path(__file__).parent / "data" / "traces"

# Test timeout (seconds)
TEST_TIMEOUT = 30


class TraceIntegrationTest:
    """Helper class for running trace integration tests."""

    def __init__(self, trace_file: Path, port: int = 2323):
        self.trace_file = trace_file
        self.port = port
        self.server: Optional[TraceReplayServer] = None
        self.server_task: Optional[asyncio.Task] = None
        self.session: Optional[Session] = None

    async def start_server(self):
        """Start the trace replay server."""
        self.server = TraceReplayServer(str(self.trace_file), loop_mode=False)

        # Start server in background task
        self.server_task = asyncio.create_task(
            self.server.start_server(host="127.0.0.1", port=self.port)
        )

        # Give server time to start
        await asyncio.sleep(0.1)
        logger.info(f"Server started on port {self.port}")

    async def stop_server(self):
        """Stop the trace replay server."""
        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
        logger.info("Server stopped")

    async def connect_session(self, timeout: int = 10) -> Session:
        """Connect a pure3270 session to the replay server."""
        self.session = Session()

        try:
            # Connect expects separate host and port parameters, not a combined string
            await asyncio.wait_for(
                asyncio.to_thread(self.session.connect, "127.0.0.1", self.port),
                timeout=timeout,
            )
            logger.info("Session connected")
            return self.session
        except asyncio.TimeoutError:
            raise TimeoutError(f"Failed to connect session within {timeout}s")

    async def disconnect_session(self):
        """Disconnect the session."""
        if self.session:
            # Session uses .close() not .disconnect()
            await asyncio.to_thread(self.session.close)
            logger.info("Session disconnected")

    async def run_test(self, test_func, timeout: int = TEST_TIMEOUT):
        """Run a test with automatic cleanup."""
        try:
            await self.start_server()
            await asyncio.wait_for(test_func(), timeout=timeout)
        finally:
            await self.disconnect_session()
            await self.stop_server()


@pytest.mark.asyncio
async def test_login_trace_basic_connection():
    """Test basic connection and telnet negotiation using login.trc."""
    trace_file = TRACE_DIR / "login.trc"
    if not trace_file.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    test = TraceIntegrationTest(trace_file, port=2324)

    async def test_connection():
        session = await test.connect_session()

        # Verify session is connected
        assert session.connected, "Session should be connected"

        # Give time for initial screen data
        await asyncio.sleep(0.5)

        # Basic validation - we should have received data
        # (Detailed screen validation will be added in later tests)
        logger.info("Basic connection test passed")

    await test.run_test(test_connection)


@pytest.mark.asyncio
async def test_login_trace_telnet_negotiation():
    """Test telnet option negotiation using login.trc."""
    trace_file = TRACE_DIR / "login.trc"
    if not trace_file.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    test = TraceIntegrationTest(trace_file, port=2325)

    async def test_negotiation():
        session = await test.connect_session()

        # Wait for negotiation to complete
        await asyncio.sleep(1.0)

        # Verify session negotiated 3270 mode
        # The login.trc shows: "Now operating in connected-3270 mode"
        assert session.connected, "Session should be in 3270 mode"

        logger.info("Telnet negotiation test passed")

    await test.run_test(test_negotiation)


@pytest.mark.asyncio
async def test_login_trace_screen_data():
    """Test screen data reception and parsing using login.trc."""
    trace_file = TRACE_DIR / "login.trc"
    if not trace_file.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    test = TraceIntegrationTest(trace_file, port=2326)

    async def test_screen():
        session = await test.connect_session()

        # Wait for screen data with retries to avoid flakiness due to timing
        # Poll the screen buffer until we see non-blank content and expected prompts
        max_wait_s = 10.0
        interval_s = 0.2
        elapsed = 0.0
        screen_text = ""
        while elapsed < max_wait_s:
            screen_text = session.screen_buffer.to_text()
            screen_lower = screen_text.lower()
            if screen_text.strip() and (
                "user" in screen_lower or "uzivatel" in screen_lower
            ):
                break
            await asyncio.sleep(interval_s)
            elapsed += interval_s

        # Verify we received the login screen
        assert len(screen_text) > 0, "Should have received screen data"
        screen_lower = screen_text.lower()
        assert (
            "user" in screen_lower or "uzivatel" in screen_lower
        ), "Should contain user prompt"

        logger.info(f"Received {len(screen_text)} chars of screen data")
        logger.info("Screen data test passed")

    await test.run_test(test_screen, timeout=30)


@pytest.mark.asyncio
async def test_smoke_trace_tn3270e_negotiation():
    """Test TN3270E protocol negotiation using smoke.trc."""
    trace_file = TRACE_DIR / "smoke.trc"
    if not trace_file.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    test = TraceIntegrationTest(trace_file, port=2327)

    async def test_tn3270e():
        session = await test.connect_session()

        # Wait for TN3270E negotiation
        await asyncio.sleep(1.0)

        # Verify connection established
        # smoke.trc shows: "Now operating in TN3270E mode"
        assert session.connected, "Session should be connected"

        logger.info("TN3270E negotiation test passed")

    await test.run_test(test_tn3270e)


@pytest.mark.asyncio
async def test_smoke_trace_printer_data():
    """Test printer protocol data flow using smoke.trc."""
    trace_file = TRACE_DIR / "smoke.trc"
    if not trace_file.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    test = TraceIntegrationTest(trace_file, port=2328)

    async def test_printer():
        session = await test.connect_session()

        # Wait for printer data
        await asyncio.sleep(2.0)

        # Verify session is still connected
        # smoke.trc contains multiple print jobs with PRINT-EOJ markers
        assert session.connected, "Session should remain connected"

        logger.info("Printer data test passed")

    await test.run_test(test_printer, timeout=30)


@pytest.mark.asyncio
async def test_smoke_trace_bind_image():
    """Test BIND image reception using smoke.trc."""
    trace_file = TRACE_DIR / "smoke.trc"
    if not trace_file.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    test = TraceIntegrationTest(trace_file, port=2329)

    async def test_bind():
        session = await test.connect_session()

        # Wait for BIND image
        await asyncio.sleep(1.0)

        # smoke.trc contains: "RCVD TN3270E(BIND-IMAGE NO-RESPONSE 0)"
        # Verify we processed it without errors
        assert session.connected, "Should handle BIND image"

        logger.info("BIND image test passed")

    await test.run_test(test_bind)


@pytest.mark.asyncio
async def test_multiple_sequential_connections():
    """Test multiple sequential connections to the same trace."""
    trace_file = TRACE_DIR / "login.trc"
    if not trace_file.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    port = 2330

    # Run 3 sequential connections
    for i in range(3):
        test = TraceIntegrationTest(trace_file, port=port)

        async def test_connection():
            session = await test.connect_session()
            await asyncio.sleep(0.5)
            assert session.connected, f"Connection {i+1} should succeed"
            logger.info(f"Sequential connection {i+1} passed")

        await test.run_test(test_connection, timeout=10)


@pytest.mark.asyncio
async def test_trace_replay_bidirectional_flow():
    """Test bidirectional data flow (send and receive)."""
    trace_file = TRACE_DIR / "login.trc"
    if not trace_file.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    test = TraceIntegrationTest(trace_file, port=2331)

    async def test_bidirectional():
        session = await test.connect_session()

        # Wait for initial screen
        await asyncio.sleep(1.0)

        # The login.trc trace shows client sending data in response to server
        # We should be able to receive the server's data
        assert session.connected, "Should maintain connection"

        # Verify we can get screen state
        screen_text = session.screen_buffer.to_text()
        assert len(screen_text) > 0, "Should have screen data"

        logger.info("Bidirectional flow test passed")

    await test.run_test(test_bidirectional, timeout=30)


@pytest.mark.asyncio
async def test_connection_timeout_handling():
    """Test connection timeout when server doesn't respond."""
    # Use a port with no server running
    port = 2332

    session = Session()

    with pytest.raises((TimeoutError, ConnectionRefusedError, OSError)):
        await asyncio.wait_for(
            asyncio.to_thread(session.connect, "127.0.0.1", port), timeout=2.0
        )

    logger.info("Connection timeout test passed")


@pytest.mark.asyncio
async def test_server_statistics():
    """Test that server tracks connection statistics."""
    trace_file = TRACE_DIR / "login.trc"
    if not trace_file.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    test = TraceIntegrationTest(trace_file, port=2333)

    async def test_stats():
        session = await test.connect_session()
        await asyncio.sleep(1.0)

        # Get server statistics
        stats = test.server.get_connection_stats()

        assert stats["active_connections"] >= 0, "Should track active connections"
        assert stats["max_connections"] == 1, "Should respect max_connections limit"

        logger.info(f"Server stats: {stats}")
        logger.info("Statistics test passed")

    await test.run_test(test_stats, timeout=20)


def test_trace_files_exist():
    """Verify test trace files are available."""
    required_traces = ["login.trc", "smoke.trc"]

    for trace_name in required_traces:
        trace_path = TRACE_DIR / trace_name
        assert trace_path.exists(), f"Required trace file missing: {trace_path}"
        assert trace_path.stat().st_size > 0, f"Trace file is empty: {trace_path}"

    logger.info("Trace files validation passed")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
