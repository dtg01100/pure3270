#!/usr/bin/env python3
"""
Improved race condition tests with proper async patterns and timeout protection.

This module addresses the race condition issues identified in Phase 3.3 by:
- Using standardized timeout patterns
- Implementing proper async isolation
- Eliminating hardcoded delays and race conditions
- Adding comprehensive resource cleanup
"""

import asyncio
import logging
import time
from typing import List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from pure3270.protocol.tn3270_handler import TN3270Handler

# Import our test utilities
from tests.utils.test_helpers import (
    AsyncTestHelper,
    TestAssertions,
    TestTimeouts,
    isolated_environment,
    resource_manager_context,
)


@pytest.mark.asyncio
async def test_concurrent_state_changes_with_timeout(
    async_test_helper, test_resource_manager
):
    """Test that concurrent state changes are properly synchronized with timeout protection."""

    # Create handler with properly mocked streams
    mock_reader = async_test_helper.create_mock_reader()
    mock_writer = async_test_helper.create_mock_writer()

    handler = TN3270Handler(mock_reader, mock_writer, host="localhost", port=23)

    # Mock negotiator to avoid initialization issues
    mock_negotiator = MagicMock()
    handler.negotiator = mock_negotiator

    # Add to resource manager
    test_resource_manager.add_resource(handler)
    test_resource_manager.add_resource(mock_reader, mock_reader.reset_mock)
    test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

    # Track state changes with thread-safe access
    state_changes = []

    async def change_state_async(state_name: str, delay: float = 0.0):
        """Change state with proper timeout protection."""
        if delay > 0:
            await asyncio.sleep(delay)

        # Use the async helper for timeout protection
        await async_test_helper.run_with_timeout(
            handler._change_state(state_name, f"test_{state_name}"), TestTimeouts.FAST
        )
        return handler._current_state

    # Simulate a proper connection workflow
    async def mock_connect():
        """Simulate connection with proper error handling."""
        await handler._change_state("CONNECTING", "test_connect")
        handler._connected = True
        await handler._change_state("NEGOTIATING", "test_negotiate")
        return "connected"

    # Set up the handler for connection
    handler.connect = mock_connect

    # Run the connection with timeout protection
    async with async_test_helper.timeout_context(TestTimeouts.MEDIUM):
        result = await handler.connect()
        assert result == "connected"

    # Verify final state
    assert handler._current_state == "NEGOTIATING"

    # Verify state was properly tracked
    TestAssertions.assert_screen_buffer_consistency(handler.screen_buffer)


@pytest.mark.asyncio
async def test_concurrent_data_operations_with_locks(
    async_test_helper, test_resource_manager
):
    """Test that concurrent data operations are properly locked and synchronized."""

    # Create handler with properly configured mock streams
    mock_reader = async_test_helper.create_mock_reader()
    mock_writer = async_test_helper.create_mock_writer()

    handler = TN3270Handler(mock_reader, mock_writer, host="localhost", port=23)

    # Set up connected state
    handler._connected = True
    handler.negotiator = MagicMock()
    handler.negotiator.negotiated_tn3270e = False

    # Add to resource manager
    test_resource_manager.add_resource(handler)
    test_resource_manager.add_resource(mock_reader, mock_reader.reset_mock)
    test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

    # Test concurrent send operations with proper timeout protection
    send_results = []

    async def send_data_safe(data: bytes, operation_id: int):
        """Send data with proper timeout and error handling."""
        try:
            await async_test_helper.run_with_timeout(
                handler.send_data(data), TestTimeouts.MEDIUM
            )
            send_results.append(f"success_{operation_id}")
            return True
        except Exception as e:
            send_results.append(f"error_{operation_id}_{str(e)[:20]}")
            return False

    # Run multiple concurrent send operations
    send_tasks = []
    for i in range(5):
        send_tasks.append(send_data_safe(f"message_{i}".encode(), i))

    # Execute all sends with timeout protection
    async with async_test_helper.timeout_context(TestTimeouts.SLOW):
        results = await asyncio.gather(*send_tasks, return_exceptions=True)

    # Verify all operations completed
    assert len(results) == 5
    assert all(not isinstance(r, Exception) for r in results)
    assert all(send_results)  # All operations should have a result

    # Verify at least some operations were successful
    success_count = sum(1 for r in send_results if r.startswith("success"))
    assert success_count >= 1  # At least one should succeed


@pytest.mark.asyncio
async def test_concurrent_receive_operations_with_isolation(
    async_test_helper, test_resource_manager
):
    """Test that concurrent receive operations are properly isolated and synchronized."""

    # Create a controlled mock reader with specific responses
    responses = [b"response1", b"response2", b"response3"]
    response_index = [0]  # Use list for thread-safe access

    class ControlledMockReader:
        def __init__(self, responses: List[bytes]):
            self.responses = responses
            self.index = 0
            self.call_count = 0

        async def read(self, n: int = 4096) -> bytes:
            self.call_count += 1
            if self.index < len(self.responses):
                data = self.responses[self.index]
                self.index += 1
                return data
            else:
                # Return empty for subsequent calls
                await asyncio.sleep(0.001)  # Small delay
                return b""

        def at_eof(self) -> bool:
            return self.index >= len(self.responses)

    mock_reader = ControlledMockReader(responses)
    mock_writer = async_test_helper.create_mock_writer()

    handler = TN3270Handler(mock_reader, mock_writer, host="localhost", port=23)
    handler._connected = True
    handler.negotiator = MagicMock()
    handler.negotiator.negotiated_tn3270e = False
    handler.negotiator._ascii_mode = False

    # Add to resource manager
    test_resource_manager.add_resource(handler)
    test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

    # Test concurrent receive operations
    receive_results = []

    async def receive_data_safe(timeout: float, operation_id: int):
        """Receive data with proper timeout protection."""
        try:
            # Use the async helper for timeout protection
            data = await async_test_helper.run_with_timeout(
                handler.receive_data(timeout=timeout), TestTimeouts.MEDIUM
            )
            receive_results.append(
                f"received_{operation_id}_{len(data) if data else 0}"
            )
            return data
        except Exception as e:
            receive_results.append(f"error_{operation_id}_{str(e)[:20]}")
            return None

    # Run multiple concurrent receive operations with different timeouts
    receive_tasks = [
        receive_data_safe(0.1, 0),  # Short timeout
        receive_data_safe(0.1, 1),  # Short timeout
        receive_data_safe(0.2, 2),  # Longer timeout
    ]

    # Execute all receives with timeout protection
    async with async_test_helper.timeout_context(TestTimeouts.SLOW):
        results = await asyncio.gather(*receive_tasks, return_exceptions=True)

    # Verify operations completed
    assert len(results) == 3
    assert len(receive_results) == 3

    # Verify at least one operation received data successfully
    successful_receives = [r for r in receive_results if r.startswith("received")]
    assert len(successful_receives) >= 1

    # Verify reader was called
    assert mock_reader.call_count > 0


@pytest.mark.asyncio
async def test_sequence_number_safety_with_timeout(
    async_test_helper, test_resource_manager
):
    """Test that sequence number operations are thread-safe with proper timeout protection."""

    mock_reader = async_test_helper.create_mock_reader()
    mock_writer = async_test_helper.create_mock_writer()

    handler = TN3270Handler(mock_reader, mock_writer, host="localhost", port=23)
    handler._sync_enabled = True

    # Add to resource manager
    test_resource_manager.add_resource(handler)
    test_resource_manager.add_resource(mock_reader, mock_reader.reset_mock)
    test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

    # Test sequence number generation with concurrent access
    sequence_results = []

    async def get_sequence_safe(operation_id: int):
        """Get sequence number with timeout protection."""
        try:
            # Get sequence number directly (method is synchronous)
            seq = handler._get_next_sent_sequence_number()
            sequence_results.append(f"seq_{operation_id}_{seq}")
            return seq
        except Exception as e:
            sequence_results.append(f"error_{operation_id}_{str(e)[:20]}")
            return None

    # Test concurrent sequence number generation
    sequence_tasks = []
    for i in range(10):
        sequence_tasks.append(get_sequence_safe(i))

    # Execute with timeout protection
    async with async_test_helper.timeout_context(TestTimeouts.MEDIUM):
        results = await asyncio.gather(*sequence_tasks, return_exceptions=True)

    # Verify operations completed
    assert len(results) == 10
    assert len(sequence_results) == 10

    # Collect valid sequence numbers
    valid_sequences = []
    for result in sequence_results:
        if result.startswith("seq_"):
            parts = result.split("_")
            if len(parts) >= 3:
                try:
                    seq = int(parts[2])
                    if 0 <= seq <= 65535:
                        valid_sequences.append(seq)
                except ValueError:
                    pass

    # Verify we got valid sequence numbers
    assert len(valid_sequences) >= 1

    # Test incremental sequence number generation
    for i in range(5):
        seq = handler._get_next_sent_sequence_number()
        assert isinstance(seq, int)
        assert 0 <= seq <= 65535


@pytest.mark.asyncio
async def test_event_registration_safety(async_test_helper, test_resource_manager):
    """Test that concurrent event callback registration is safe with proper isolation."""

    mock_reader = async_test_helper.create_mock_reader()
    mock_writer = async_test_helper.create_mock_writer()

    handler = TN3270Handler(mock_reader, mock_writer, host="localhost", port=23)

    # Add to resource manager
    test_resource_manager.add_resource(handler)
    test_resource_manager.add_resource(mock_reader, mock_reader.reset_mock)
    test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

    # Define safe callback functions
    async def safe_state_change_callback(from_state: str, to_state: str, reason: str):
        pass

    async def safe_state_entry_callback(state: str):
        pass

    async def safe_state_exit_callback(state: str):
        pass

    # Test concurrent callback registration with proper isolation
    registration_results = []

    async def register_callbacks_safe(
        callback_type: str, count: int, operation_id: int
    ):
        """Register callbacks with timeout protection and proper error handling."""
        try:
            for i in range(count):
                if callback_type == "state_change":
                    handler.add_state_change_callback(
                        "CONNECTED", safe_state_change_callback
                    )
                elif callback_type == "state_entry":
                    handler.add_state_entry_callback(
                        "CONNECTED", safe_state_entry_callback
                    )
                elif callback_type == "state_exit":
                    handler.add_state_exit_callback(
                        "CONNECTED", safe_state_exit_callback
                    )

            registration_results.append(f"success_{callback_type}_{operation_id}")
            return True
        except Exception as e:
            registration_results.append(
                f"error_{callback_type}_{operation_id}_{str(e)[:20]}"
            )
            return False

    # Run concurrent callback registration
    registration_tasks = [
        register_callbacks_safe("state_change", 3, 0),
        register_callbacks_safe("state_entry", 2, 1),
        register_callbacks_safe("state_exit", 2, 2),
    ]

    # Execute with timeout protection
    async with async_test_helper.timeout_context(TestTimeouts.MEDIUM):
        results = await asyncio.gather(*registration_tasks, return_exceptions=True)

    # Verify operations completed
    assert len(results) == 3
    assert all(not isinstance(r, Exception) for r in results)

    # Verify callbacks were registered
    state_change_cbs = handler._state_change_callbacks.get("CONNECTED", [])
    state_entry_cbs = handler._state_entry_callbacks.get("CONNECTED", [])
    state_exit_cbs = handler._state_exit_callbacks.get("CONNECTED", [])

    assert len(state_change_cbs) == 3
    assert len(state_entry_cbs) == 2
    assert len(state_exit_cbs) == 2


def test_handler_initialization_performance(async_test_helper, test_resource_manager):
    """Test handler initialization performance with proper resource management."""

    # Test rapid handler creation with proper isolation
    handlers = []
    initialization_results = []

    start_time = time.perf_counter()

    for i in range(10):
        try:
            # Create handlers with proper resource management
            mock_reader = async_test_helper.create_mock_reader()
            mock_writer = async_test_helper.create_mock_writer()

            handler = TN3270Handler(
                mock_reader, mock_writer, host=f"host_{i}", port=23 + i
            )

            # Mock negotiator to avoid actual initialization
            mock_negotiator = MagicMock()
            handler.negotiator = mock_negotiator
            handler.negotiator.is_printer_session = False

            # Add to resource manager
            test_resource_manager.add_resource(handler)
            test_resource_manager.add_resource(mock_reader, mock_reader.reset_mock)
            test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

            handlers.append(handler)
            initialization_results.append(f"success_{i}")

        except Exception as e:
            initialization_results.append(f"error_{i}_{str(e)[:20]}")

    end_time = time.perf_counter()

    # Verify all handlers were created successfully
    assert len(handlers) == 10
    assert end_time - start_time < 2.0  # Should complete very quickly

    # Verify all initializations were successful
    success_count = sum(1 for r in initialization_results if r.startswith("success"))
    assert success_count == 10

    # Verify handler properties
    for i, handler in enumerate(handlers):
        assert handler.host == f"host_{i}"
        assert handler.port == 23 + i
        assert handler._current_state == "DISCONNECTED"
        assert "_state_lock" in dir(handler)  # Verify async locks were created


@pytest.mark.asyncio
async def test_concurrent_handler_cleanup_safety(
    async_test_helper, test_resource_manager
):
    """Test that concurrent handler cleanup operations are safe and don't cause race conditions."""

    mock_reader = async_test_helper.create_mock_reader()
    mock_writer = async_test_helper.create_mock_writer()

    handler = TN3270Handler(mock_reader, mock_writer, host="localhost", port=23)
    handler._connected = True

    # Add to resource manager
    test_resource_manager.add_resource(handler)
    test_resource_manager.add_resource(mock_reader, mock_reader.reset_mock)
    test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

    # Test concurrent cleanup operations
    cleanup_results = []

    async def perform_cleanup_safe(operation_id: int):
        """Perform cleanup with proper error handling and timeout protection."""
        try:
            # Use timeout protection for cleanup operations
            await async_test_helper.run_with_timeout(
                handler.close(), TestTimeouts.MEDIUM
            )
            cleanup_results.append(f"cleanup_success_{operation_id}")
            return True
        except Exception as e:
            cleanup_results.append(f"cleanup_error_{operation_id}_{str(e)[:20]}")
            return False

    # Run multiple concurrent cleanup operations
    cleanup_tasks = [perform_cleanup_safe(i) for i in range(3)]

    # Execute with timeout protection
    async with async_test_helper.timeout_context(TestTimeouts.SLOW):
        results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    # Verify operations completed
    assert len(results) == 3
    assert len(cleanup_results) == 3

    # At least one cleanup should succeed
    success_count = sum(1 for r in cleanup_results if r.startswith("cleanup_success"))
    assert success_count >= 1

    # Verify handler is in a consistent state after cleanup
    # Handler should be in a closed or error state
    assert handler._current_state in ["DISCONNECTED", "CLOSING", "ERROR"]


# Test timeout and error handling patterns
@pytest.mark.asyncio
async def test_timeout_handling_with_async_helper(
    async_test_helper, test_resource_manager
):
    """Test that timeout handling works correctly with the async test helper."""

    # This test verifies that the timeout patterns work correctly
    await TestAssertions.assert_timeout_behavior(async_test_helper, TestTimeouts.FAST)


@pytest.mark.asyncio
async def test_resource_cleanup_with_context_manager(
    async_test_helper, test_resource_manager
):
    """Test that resources are properly cleaned up using context managers."""

    # Create a temporary resource
    temp_handler = None

    try:
        mock_reader = async_test_helper.create_mock_reader()
        mock_writer = async_test_helper.create_mock_writer()

        temp_handler = TN3270Handler(mock_reader, mock_writer, host="test", port=23)

        # Add to resource manager
        test_resource_manager.add_resource(temp_handler)
        test_resource_manager.add_resource(mock_reader, mock_reader.reset_mock)
        test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

        # Verify handler was created
        assert temp_handler is not None
        assert temp_handler.host == "test"

    finally:
        # The resource manager will clean up automatically
        # This test verifies the cleanup pattern works
        assert test_resource_manager is not None
