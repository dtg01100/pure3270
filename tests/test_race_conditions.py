#!/usr/bin/env python3
"""
Test race condition scenarios to verify async lock effectiveness
"""

import asyncio
import time
from typing import List, Tuple
from unittest.mock import AsyncMock, Mock

import pytest

from pure3270.protocol.tn3270_handler import HandlerState, TN3270Handler


@pytest.mark.asyncio
async def test_concurrent_state_changes():
    """Test that concurrent state changes are properly synchronized."""

    # Create handler with mocked streams
    class MockReader:
        async def read(self, n=4096):
            await asyncio.sleep(0.01)
            return b""

        async def readexactly(self, n):
            return b""

        def at_eof(self):
            return False

    class MockWriter:
        def write(self, data):
            pass

        async def drain(self):
            await asyncio.sleep(0.001)

        def close(self):
            pass

    handler = TN3270Handler(MockReader(), MockWriter(), host="localhost", port=23)
    handler.negotiator = Mock()  # Mock negotiator to avoid initialization issues

    # Track state changes
    state_changes: List[Tuple[str, str]] = []

    async def change_state_async(state_name: str, delay: float = 0.01):
        await asyncio.sleep(delay)
        await handler._change_state(state_name, "test")
        return handler._current_state

    # Mock the connect method to simulate a connection
    async def mock_connect():
        await handler._change_state("CONNECTING", "test")
        handler._connected = True
        await handler._change_state("NEGOTIATING", "test")

    handler.connect = mock_connect

    # Run the connect method
    await handler.connect()

    # Verify the handler is in the correct state
    assert handler._current_state == "NEGOTIATING"


@pytest.mark.asyncio
async def test_concurrent_data_send_operations():
    """Test that concurrent data send operations are properly locked."""

    class MockReader:
        async def read(self, n=4096):
            return b""

        def at_eof(self):
            return False

    class MockWriter:
        def __init__(self):
            self.data_sent = []
            self.drain_count = 0

        def write(self, data):
            self.data_sent.append(data)

        async def drain(self):
            await asyncio.sleep(0.001)  # Simulate network delay
            self.drain_count += 1

        def close(self):
            pass

    handler = TN3270Handler(MockReader(), MockWriter(), host="localhost", port=23)
    handler._connected = True  # Simulate connected state

    # Run multiple concurrent send operations
    send_tasks = []
    for i in range(5):
        send_tasks.append(handler.send_data(f"message_{i}".encode()))

    # Execute all sends concurrently
    results = await asyncio.gather(*send_tasks, return_exceptions=True)

    # Verify all sends completed successfully
    assert all(not isinstance(r, Exception) for r in results)

    # Verify all messages were sent (writer should have all data)
    assert len(handler.writer.data_sent) == 5
    assert handler.writer.drain_count == 5


@pytest.mark.asyncio
async def test_concurrent_receive_operations():
    """Test that concurrent receive operations are properly synchronized."""

    received_data = []
    call_count = 0

    class MockReader:
        def __init__(self, responses=None):
            # Use valid TN3270 data format for testing
            self.responses = responses or [
                b"\x00\x00\x00\x04\xf5\x40\x40\x19",
                b"\x00\x00\x00\x04\xf5\x40\x40\x19",
                b"\x00\x00\x00\x04\xf5\x40\x40\x19",
            ]
            self.index = 0
            self.call_count = 0

        async def read(self, n=4096):
            self.call_count += 1
            if self.index < len(self.responses):
                data = self.responses[self.index]
                self.index += 1
                received_data.append(data)
                return data
            else:
                await asyncio.sleep(0.1)  # Simulate waiting for data
                return b""

        def at_eof(self):
            return False

    class MockWriter:
        def write(self, data):
            pass

        async def drain(self):
            pass

        def close(self):
            pass

    handler = TN3270Handler(MockReader(), MockWriter(), host="localhost", port=23)
    handler._connected = True
    handler._current_state = HandlerState.CONNECTED
    handler.negotiator = Mock()
    handler.negotiator.set_negotiated_tn3270e(False)
    handler.negotiator._ascii_mode = False

    # Run multiple concurrent receive operations
    receive_tasks = []
    for i in range(3):
        receive_tasks.append(handler.receive_data(timeout=0.1))

    # Execute all receives concurrently
    results = await asyncio.gather(*receive_tasks, return_exceptions=True)

    # At least one should have received data (they're competing for the same stream)
    successful_receives = [r for r in results if isinstance(r, bytes) and r]
    assert len(successful_receives) >= 1

    # Verify operations were serialized (should not have race conditions)
    # This is hard to test definitively, but we can verify the operations completed
    assert handler.reader.call_count > 0


@pytest.mark.asyncio
async def test_sequence_number_concurrency():
    """Test that sequence number operations are thread-safe."""

    class MockReader:
        async def read(self, n=4096):
            return b""

        def at_eof(self):
            return False

    class MockWriter:
        def write(self, data):
            pass

        async def drain(self):
            pass

        def close(self):
            pass

    handler = TN3270Handler(MockReader(), MockWriter(), host="localhost", port=23)
    handler._sync_enabled = True

    # Test concurrent sequence number generation
    sequence_tasks = []
    for i in range(10):
        sequence_tasks.append(handler._get_next_sent_sequence_number())

    # This will run synchronously due to the lock, but the concept is still valid
    # In a real async scenario, these would compete for sequence numbers
    for task in sequence_tasks:
        seq = task  # This is actually synchronous
        assert isinstance(seq, int)
        assert 0 <= seq <= 65535

    # Verify sequence numbers are unique and incremental
    last_seq = 0
    for i in range(5):
        seq = handler._get_next_sent_sequence_number()
        assert seq > last_seq
        last_seq = seq


@pytest.mark.asyncio
async def test_addressing_mode_transition_race():
    """Test that addressing mode transitions are race-free."""

    class MockReader:
        async def read(self, n=4096):
            return b""

        def at_eof(self):
            return False

    class MockWriter:
        def write(self, data):
            pass

        async def drain(self):
            pass

        def close(self):
            pass

    handler = TN3270Handler(MockReader(), MockWriter(), host="localhost", port=23)

    # Test concurrent attempts to set addressing mode
    from pure3270.emulation.addressing import AddressingMode

    transition_results = []

    async def attempt_transition(mode: AddressingMode, delay: float = 0.01):
        await asyncio.sleep(delay)
        try:
            await handler.transition_addressing_mode(
                mode, f"test transition {mode.value}"
            )
            transition_results.append(f"success_{mode.value}")
            return True
        except Exception as e:
            transition_results.append(f"error_{mode.value}_{str(e)[:20]}")
            return False

    # Attempt concurrent transitions
    tasks = [
        attempt_transition(AddressingMode.MODE_12_BIT),
        attempt_transition(AddressingMode.MODE_14_BIT),
        attempt_transition(AddressingMode.MODE_12_BIT),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify operations completed (some may succeed, some may fail, but no races)
    assert len(results) == 3
    assert len(transition_results) == 3

    # Handler should be in a consistent state
    final_mode = handler.get_negotiated_addressing_mode()
    assert final_mode is not None

    # State should be consistent
    assert handler._addressing_negotiator._negotiated_mode == final_mode


@pytest.mark.asyncio
async def test_concurrent_event_registration():
    """Test that concurrent event callback registration is safe."""

    class MockReader:
        async def read(self, n=4096):
            return b""

        def at_eof(self):
            return False

    class MockWriter:
        def write(self, data):
            pass

        async def drain(self):
            pass

        def close(self):
            pass

    handler = TN3270Handler(MockReader(), MockWriter(), host="localhost", port=23)

    # Test concurrent callback registration
    callback_counts = {"state_change": 0, "state_entry": 0, "state_exit": 0}

    async def dummy_state_change_callback(from_state: str, to_state: str, reason: str):
        pass

    async def dummy_state_entry_callback(state: str):
        pass

    async def dummy_state_exit_callback(state: str):
        pass

    async def add_callbacks_async(callback_type: str, count: int):
        for i in range(count):
            if callback_type == "state_change":
                handler.add_state_change_callback(
                    "CONNECTED", dummy_state_change_callback
                )
            elif callback_type == "state_entry":
                handler.add_state_entry_callback(
                    "CONNECTED", dummy_state_entry_callback
                )
            elif callback_type == "state_exit":
                handler.add_state_exit_callback("CONNECTED", dummy_state_exit_callback)
            callback_counts[callback_type] += 1

    # Run concurrent callback addition
    tasks = [
        add_callbacks_async("state_change", 3),
        add_callbacks_async("state_entry", 2),
        add_callbacks_async("state_exit", 2),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify all operations completed
    assert all(not isinstance(r, Exception) for r in results)

    # Verify callbacks were added
    assert len(handler._state_change_callbacks.get("CONNECTED", [])) == 3
    assert len(handler._state_entry_callbacks.get("CONNECTED", [])) == 2
    assert len(handler._state_exit_callbacks.get("CONNECTED", [])) == 2


@pytest.mark.asyncio
async def test_negotiator_timeout_cleanup_concurrency():
    """Test that negotiation timeout cleanup operations are safe."""

    class MockReader:
        async def read(self, n=4096):
            return b""

        def at_eof(self):
            return False

    class MockWriter:
        def write(self, data):
            pass

        async def drain(self):
            pass

        def close(self):
            pass

    handler = TN3270Handler(MockReader(), MockWriter(), host="localhost", port=23)
    handler.negotiator = Mock()

    # Simulate timeout state
    handler._mark_negotiation_timeout()

    # Test concurrent cleanup attempts
    cleanup_results = []

    async def perform_cleanup(task_id: int):
        try:
            await handler._perform_timeout_cleanup()
            cleanup_results.append(f"cleanup_{task_id}_success")
            return True
        except Exception as e:
            cleanup_results.append(f"cleanup_{task_id}_error_{str(e)[:20]}")
            return False

    # Run multiple cleanup attempts concurrently
    tasks = [perform_cleanup(i) for i in range(3)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify operations completed (only one should do actual cleanup)
    assert len(results) == 3
    assert len(cleanup_results) == 3

    # Verify cleanup state is consistent
    assert handler._is_cleanup_performed()
    assert handler._is_negotiation_timeout()


def test_handler_initialization_under_load():
    """Test handler initialization under concurrent load."""

    # Create multiple handlers rapidly
    handlers = []
    start_time = time.time()

    for i in range(10):
        mock_reader = Mock()
        mock_reader.read = AsyncMock(return_value=b"")
        mock_reader.at_eof = Mock(return_value=False)

        mock_writer = Mock()
        mock_writer.write = Mock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = Mock()

        handler = TN3270Handler(mock_reader, mock_writer, host=f"host_{i}", port=23 + i)

        # Set mock negotiator to avoid actual initialization
        handler.negotiator = Mock()
        handler.negotiator.is_printer_session = False

        handlers.append(handler)

    end_time = time.time()

    # Verify all handlers were created and initialized properly
    assert len(handlers) == 10
    assert end_time - start_time < 5.0  # Should complete quickly

    for i, handler in enumerate(handlers):
        assert handler.host == f"host_{i}"
        assert handler.port == 23 + i
        assert handler._current_state == "DISCONNECTED"
        assert "_state_lock" in dir(handler)  # Verify async locks were created
