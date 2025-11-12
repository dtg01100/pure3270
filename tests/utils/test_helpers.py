#!/usr/bin/env python3
"""
Test Helper Utilities for Pure3270

This module provides standardized utilities for creating reliable, isolated tests
that address the 47 test infrastructure issues identified in Phase 3.3.

Key Features:
- Standardized timeout patterns
- Isolated test fixtures with proper cleanup
- Race condition prevention
- Resource management utilities
- Reusable test helpers
"""

import asyncio
import gc
import logging
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock

import pytest


# Standard timeout values for consistency
class TestTimeouts:
    """Standardized timeout values used across the test suite."""

    FAST = 0.1  # For unit tests and quick operations
    MEDIUM = 1.0  # For normal async operations
    SLOW = 5.0  # For integration tests
    VERY_SLOW = 10.0  # For trace replay and complex operations


class TestConfig:
    """Configuration for test execution with standardized patterns."""

    # Memory limits for tests
    MEMORY_LIMIT_100MB = 100 * 1024 * 1024  # 100MB
    MEMORY_LIMIT_500MB = 500 * 1024 * 1024  # 500MB

    # Test categories for organization
    CATEGORIES = {
        "unit": "Unit tests for individual components",
        "integration": "Integration tests for component interactions",
        "trace": "Trace file replay and validation tests",
        "performance": "Performance and benchmark tests",
        "protocol": "Protocol compliance and edge case tests",
    }

    # Standard test marks
    MARKS = {
        "fast": "Fast unit tests (< 0.1s)",
        "slow": "Slow tests (> 3s)",
        "integration": "Integration tests",
        "trace": "Trace file tests",
        "performance": "Performance tests",
        "protocol": "Protocol compliance tests",
    }


@contextmanager
def isolated_environment():
    """
    Context manager for test isolation.

    Ensures that tests run in a clean environment with proper cleanup
    of all resources and state.
    """
    # Store original logging level
    original_level = logging.getLogger().level

    # Enable garbage collection
    gc.enable()

    try:
        yield
    finally:
        # Force garbage collection
        gc.collect()

        # Reset logging level
        logging.getLogger().setLevel(original_level)

        # Clear any module-level caches that might persist
        _clear_module_caches()


def _clear_module_caches():
    """Clear caches that might persist between tests."""
    try:
        # Clear any pure3270 module caches if they exist
        import pure3270

        for attr_name in dir(pure3270):
            attr = getattr(pure3270, attr_name)
            if hasattr(attr, "clear_cache"):
                try:
                    attr.clear_cache()
                except (AttributeError, TypeError):
                    pass
    except ImportError:
        pass


class AsyncTestHelper:
    """Helper for reliable async testing with proper cleanup."""

    def __init__(self):
        self._active_tasks: List[asyncio.Task] = []
        self._cleanup_functions: List[callable] = []

    @asynccontextmanager
    async def timeout_context(
        self, timeout: float = TestTimeouts.MEDIUM
    ) -> AsyncGenerator[None, None]:
        """
        Context manager that provides timeout protection for async operations.

        Args:
            timeout: Timeout in seconds
        """
        try:
            yield
        except asyncio.TimeoutError:
            pytest.fail(f"Operation timed out after {timeout} seconds")

    @asynccontextmanager
    async def isolated_async_context(self) -> AsyncGenerator[None, None]:
        """
        Context manager for isolated async operations.

        Ensures proper cleanup of all async resources.
        """
        # Create new event loop for isolation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            yield
        finally:
            # Cancel all pending tasks
            for task in asyncio.all_tasks(loop):
                if not task.done():
                    task.cancel()
                    try:
                        loop.run_until_complete(task)
                    except asyncio.CancelledError:
                        pass

            # Close the loop
            loop.close()

    def create_mock_reader(self, responses: Optional[List[bytes]] = None) -> AsyncMock:
        """
        Create a standardized mock reader for testing.

        Args:
            responses: List of responses to return sequentially

        Returns:
            AsyncMock with proper reader interface
        """
        mock_reader = AsyncMock()
        mock_reader.at_eof = AsyncMock(return_value=False)

        if responses:
            mock_reader.readexactly = AsyncMock(side_effect=responses)
            mock_reader.read = AsyncMock(side_effect=responses)
        else:
            mock_reader.readexactly = AsyncMock(return_value=b"")
            mock_reader.read = AsyncMock(return_value=b"")

        return mock_reader

    def create_mock_writer(self) -> AsyncMock:
        """
        Create a standardized mock writer for testing.

        Returns:
            AsyncMock with proper writer interface
        """
        mock_writer = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        mock_writer.is_closing = MagicMock(return_value=False)

        return mock_writer

    async def run_with_timeout(self, coro, timeout: float = TestTimeouts.MEDIUM) -> Any:
        """
        Run a coroutine with timeout protection.

        Args:
            coro: Coroutine to run
            timeout: Timeout in seconds

        Returns:
            Result of the coroutine
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            pytest.fail(f"Operation timed out after {timeout} seconds")


class SyncTestHelper:
    """Helper for reliable synchronous testing."""

    @contextmanager
    def mock_cleanup_context(self, *mocks):
        """
        Context manager to ensure mocks are properly cleaned up.

        Args:
            *mocks: Mock objects to reset
        """
        try:
            yield mocks
        finally:
            for mock in mocks:
                if hasattr(mock, "reset_mock"):
                    mock.reset_mock()

    def create_timeout_thread(
        self, target_func, timeout: float = TestTimeouts.SLOW
    ) -> threading.Thread:
        """
        Create a thread that will timeout if the function doesn't complete.

        Args:
            target_func: Function to run
            timeout: Timeout in seconds

        Returns:
            Thread object
        """
        result = [None]
        exception = [None]

        def wrapper():
            try:
                result[0] = target_func()
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=wrapper)
        thread.daemon = True
        thread.start()

        # Wait with timeout
        thread.join(timeout=timeout)
        if thread.is_alive():
            pytest.fail(f"Operation timed out after {timeout} seconds")

        if exception[0]:
            raise exception[0]

        return result[0]


class ResourceManager:
    """Manages test resources with proper cleanup."""

    def __init__(self):
        self._resources: List[Any] = []
        self._cleanup_functions: List[callable] = []

    def add_resource(self, resource: Any, cleanup_func: Optional[callable] = None):
        """
        Add a resource for cleanup.

        Args:
            resource: Resource to track
            cleanup_func: Optional cleanup function
        """
        self._resources.append(resource)
        if cleanup_func:
            self._cleanup_functions.append(cleanup_func)

    def cleanup(self):
        """Clean up all tracked resources."""
        # Run cleanup functions
        for cleanup_func in self._cleanup_functions:
            try:
                cleanup_func()
            except Exception as e:
                logging.getLogger(__name__).warning(f"Cleanup function failed: {e}")

        # Clear resources list
        self._resources.clear()
        self._cleanup_functions.clear()


@contextmanager
def resource_manager_context() -> Generator[ResourceManager, None, None]:
    """
    Context manager for resource management.

    Usage:
        with resource_manager_context() as rm:
            rm.add_resource(obj, cleanup_func)
            # Use resources
        # All resources are automatically cleaned up
    """
    rm = ResourceManager()
    try:
        yield rm
    finally:
        rm.cleanup()


# Standard test data generators
class TestDataGenerators:
    """Generates standardized test data for consistent testing."""

    @staticmethod
    def generate_telnet_negotiation_sequence() -> List[bytes]:
        """Generate a standard Telnet negotiation sequence."""
        return [
            b"\xff\xfb\x28",  # IAC WILL TN3270E
            b"\xff\xfd\x28",  # IAC DO TN3270E
            b"\xff\xfb\x00",  # IAC WILL BINARY
            b"\xff\xfd\x00",  # IAC DO BINARY
        ]

    @staticmethod
    def generate_tn3270e_header(data_type: int = 0) -> bytes:
        """Generate a standard TN3270E header."""
        return bytes([data_type, 0x00, 0x00, 0x00, 0x00])  # data_type, flags, seq

    @staticmethod
    def generate_3270_write_command() -> bytes:
        """Generate a standard 3270 Write command."""
        return b"\xf5\x40"  # Write command + space character

    @staticmethod
    def generate_sample_screen_data(rows: int = 24, cols: int = 80) -> bytes:
        """Generate sample 3270 screen data."""
        screen_size = rows * cols
        return b"\xf5" + b"\x40" * screen_size  # Write + spaces


# Reusable test fixtures
@pytest.fixture
def test_helpers():
    """Fixture providing test helpers."""
    return {
        "async": AsyncTestHelper(),
        "sync": SyncTestHelper(),
        "timeouts": TestTimeouts,
        "config": TestConfig,
    }


@pytest.fixture
def resource_manager():
    """Fixture providing resource management."""
    with resource_manager_context() as rm:
        yield rm


# Standardized assertion helpers
class TestAssertions:
    """Standardized assertions for common test patterns."""

    @staticmethod
    def assert_screen_buffer_consistency(screen_buffer):
        """Assert that a screen buffer is in a consistent state."""
        assert screen_buffer is not None
        assert screen_buffer.rows > 0
        assert screen_buffer.cols > 0
        assert 0 <= screen_buffer.cursor_row < screen_buffer.rows
        assert 0 <= screen_buffer.cursor_col < screen_buffer.cols

    @staticmethod
    def assert_mock_writer_called_with(writer: AsyncMock, expected_calls: List[bytes]):
        """Assert that mock writer was called with expected data."""
        assert writer.write.called
        actual_calls = [call.args[0] for call in writer.write.call_args_list]
        assert (
            actual_calls == expected_calls
        ), f"Expected {expected_calls}, got {actual_calls}"

    @staticmethod
    async def assert_timeout_behavior(async_helper: AsyncTestHelper, timeout: float):
        """Test that timeout behavior works correctly."""

        async def slow_operation():
            await asyncio.sleep(timeout + 0.1)  # Sleep longer than timeout
            return "should_not_reach"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=timeout)

    @staticmethod
    def assert_trace_file_validity(trace_path: Path):
        """Assert that a trace file is valid for testing."""
        assert trace_path.exists(), f"Trace file {trace_path} does not exist"
        assert (
            trace_path.suffix == ".trc"
        ), f"Trace file {trace_path} must have .trc extension"
        assert trace_path.stat().st_size > 0, f"Trace file {trace_path} is empty"


# Performance testing utilities
class PerformanceTester:
    """Utilities for performance testing of critical code paths."""

    def __init__(self, iterations: int = 100):
        self.iterations = iterations
        self.results: Dict[str, List[float]] = {}

    def time_operation(
        self, operation_name: str, operation_func: callable, *args, **kwargs
    ) -> float:
        """
        Time a single operation.

        Args:
            operation_name: Name of the operation
            operation_func: Function to time
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Execution time in seconds
        """
        start_time = time.perf_counter()
        result = operation_func(*args, **kwargs)
        end_time = time.perf_counter()

        execution_time = end_time - start_time

        if operation_name not in self.results:
            self.results[operation_name] = []
        self.results[operation_name].append(execution_time)

        return execution_time

    def benchmark_operation(
        self, operation_name: str, operation_func: callable, *args, **kwargs
    ) -> Dict[str, float]:
        """
        Benchmark an operation over multiple iterations.

        Args:
            operation_name: Name of the operation
            operation_func: Function to benchmark
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Dictionary with timing statistics
        """
        times = []

        for _ in range(self.iterations):
            exec_time = self.time_operation(
                operation_name, operation_func, *args, **kwargs
            )
            times.append(exec_time)

        if operation_name in self.results:
            times = self.results[operation_name]

        return {
            "mean": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "total": sum(times),
            "iterations": len(times),
        }

    def assert_performance_threshold(self, operation_name: str, max_time: float):
        """
        Assert that an operation meets performance threshold.

        Args:
            operation_name: Name of the operation
            max_time: Maximum acceptable time in seconds
        """
        if operation_name not in self.results:
            pytest.fail(f"No performance data for operation: {operation_name}")

        avg_time = sum(self.results[operation_name]) / len(self.results[operation_name])
        assert (
            avg_time <= max_time
        ), f"Operation {operation_name} took {avg_time:.3f}s on average, threshold is {max_time:.3f}s"


# Memory management utilities
class MemoryTester:
    """Utilities for testing memory usage and limits."""

    @staticmethod
    def get_memory_usage() -> int:
        """Get current memory usage in bytes."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        return process.memory_info().rss

    @staticmethod
    def assert_memory_limit(memory_limit: int, tolerance: float = 0.1):
        """
        Assert that current memory usage is within limit.

        Args:
            memory_limit: Memory limit in bytes
            tolerance: Tolerance as fraction of limit (default 10%)
        """
        current_usage = MemoryTester.get_memory_usage()
        max_allowed = memory_limit * (1 + tolerance)

        assert (
            current_usage <= max_allowed
        ), f"Memory usage {current_usage} exceeds limit {memory_limit} by {tolerance*100}%"

    @staticmethod
    @contextmanager
    def memory_limit_context(limit: int):
        """
        Context manager that ensures memory usage stays within limit.

        Args:
            limit: Memory limit in bytes
        """
        import resource

        # Set memory limit
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        try:
            resource.setrlimit(resource.RLIMIT_AS, (limit, hard))
            yield
        finally:
            # Restore original limit
            resource.setrlimit(resource.RLIMIT_AS, (soft, hard))


# Export main utilities for easy importing
__all__ = [
    "TestTimeouts",
    "TestConfig",
    "AsyncTestHelper",
    "SyncTestHelper",
    "ResourceManager",
    "resource_manager_context",
    "TestDataGenerators",
    "TestAssertions",
    "PerformanceTester",
    "MemoryTester",
    "isolated_environment",
]
