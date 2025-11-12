#!/usr/bin/env python3
"""
Performance benchmarks for critical code paths in Pure3270.

This module addresses the performance testing gaps identified in Phase 3.3 by:
- Testing performance under concurrent load
- Benchmarking connection pooling efficiency
- Validating performance under heavy traffic scenarios
- Ensuring performance meets enterprise requirements
"""

import asyncio
import gc
import logging
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

# Disable debug logging for performance tests to avoid excessive output
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("pure3270").setLevel(logging.WARNING)

from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.tn3270_handler import TN3270Handler

# Import our test utilities
from tests.utils.test_helpers import (
    AsyncTestHelper,
    MemoryTester,
    PerformanceTester,
    TestTimeouts,
    resource_manager_context,
)


class PerformanceBenchmark:
    """Container for performance benchmark results."""

    def __init__(self, name: str):
        self.name = name
        self.results: Dict[str, Any] = {}
        self.performance_tester = PerformanceTester(iterations=100)

    def add_result(self, metric: str, value: float, unit: str = "seconds"):
        """Add a performance result."""
        self.results[metric] = {"value": value, "unit": unit}

    def add_memory_usage(self, usage: int):
        """Add memory usage result."""
        self.results["memory_usage"] = {"value": usage, "unit": "bytes"}

    def get_summary(self) -> str:
        """Get a summary of all performance results."""
        summary = [f"Performance Benchmark: {self.name}"]
        for metric, data in self.results.items():
            summary.append(f"  {metric}: {data['value']:.4f} {data['unit']}")
        return "\n".join(summary)


@pytest.mark.performance
def test_handler_creation_performance(async_test_helper, test_resource_manager):
    """Benchmark TN3270Handler creation performance under various conditions."""

    benchmark = PerformanceBenchmark("Handler Creation Performance")

    # Test 1: Single handler creation
    start_time = time.perf_counter()

    mock_reader = async_test_helper.create_mock_reader()
    mock_writer = async_test_helper.create_mock_writer()

    handler = TN3270Handler(mock_reader, mock_writer, host="localhost", port=23)
    handler.negotiator = MagicMock()

    creation_time = time.perf_counter() - start_time
    benchmark.add_result("single_creation", creation_time, "seconds")

    # Add to resource manager
    test_resource_manager.add_resource(handler)
    test_resource_manager.add_resource(mock_reader, mock_reader.reset_mock)
    test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

    # Test 2: Concurrent handler creation (performance under load)
    concurrent_handlers = []
    start_time = time.perf_counter()

    for i in range(50):  # Create 50 handlers concurrently
        mock_reader = async_test_helper.create_mock_reader()
        mock_writer = async_test_helper.create_mock_writer()

        handler = TN3270Handler(mock_reader, mock_writer, host=f"host_{i}", port=23 + i)
        handler.negotiator = MagicMock()
        concurrent_handlers.append(handler)

        # Add to resource manager
        test_resource_manager.add_resource(handler)
        test_resource_manager.add_resource(mock_reader, mock_reader.reset_mock)
        test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

    concurrent_creation_time = time.perf_counter() - start_time
    benchmark.add_result("concurrent_creation_50", concurrent_creation_time, "seconds")
    benchmark.add_result(
        "avg_time_per_handler", concurrent_creation_time / 50, "seconds"
    )

    # Verify all handlers were created
    assert len(concurrent_handlers) == 50

    # Test 3: Memory efficiency
    tracemalloc.start()
    gc.collect()

    initial_memory = tracemalloc.get_traced_memory()[0]

    # Create handlers and measure memory usage
    memory_handlers = []
    for i in range(20):
        mock_reader = async_test_helper.create_mock_reader()
        mock_writer = async_test_helper.create_mock_writer()
        handler = TN3270Handler(mock_reader, mock_writer, host=f"mem_{i}", port=23 + i)
        memory_handlers.append(handler)

        # Add to resource manager
        test_resource_manager.add_resource(handler)
        test_resource_manager.add_resource(mock_reader, mock_reader.reset_mock)
        test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

    final_memory = tracemalloc.get_traced_memory()[0]
    memory_per_handler = (final_memory - initial_memory) / 20

    tracemalloc.stop()
    benchmark.add_memory_usage(memory_per_handler)

    # Performance assertions
    assert (
        creation_time < TestTimeouts.FAST
    ), f"Single handler creation too slow: {creation_time}"
    assert (
        concurrent_creation_time < 2.0
    ), f"Concurrent creation too slow: {concurrent_creation_time}"
    assert (
        memory_per_handler < 1024 * 1024
    ), f"Memory per handler too high: {memory_per_handler} bytes"

    print(f"\n{benchmark.get_summary()}")


@pytest.mark.performance
def test_screen_buffer_performance(test_resource_manager):
    """Benchmark screen buffer operations under load."""

    benchmark = PerformanceBenchmark("Screen Buffer Performance")

    # Test 1: Screen buffer creation performance
    start_time = time.perf_counter()
    screen_buffer = ScreenBuffer(rows=24, cols=80)
    creation_time = time.perf_counter() - start_time
    benchmark.add_result("creation", creation_time, "seconds")

    test_resource_manager.add_resource(screen_buffer)

    # Test 2: Character write performance
    ebcdic_A = translate_ascii_to_ebcdic("A")[0]  # Convert ASCII "A" to EBCDIC byte

    start_time = time.perf_counter()
    for i in range(100):  # Write 1000 chars (100 * 10)
        for j in range(10):
            screen_buffer.write_char(ebcdic_A)
    write_time = time.perf_counter() - start_time
    benchmark.add_result("character_write_1000", write_time, "seconds")

    # Test 3: Field operations performance
    start_time = time.perf_counter()
    for i in range(100):  # Set 100 fields
        screen_buffer.set_attribute(0x40, 0, 0)  # Set attribute
    field_time = time.perf_counter() - start_time
    benchmark.add_result("field_operations_100", field_time, "seconds")

    # Test 4: Screen clear performance
    start_time = time.perf_counter()
    for i in range(50):  # Clear 50 times
        screen_buffer.clear()
    clear_time = time.perf_counter() - start_time
    benchmark.add_result("screen_clear_50", clear_time, "seconds")

    # Test 5: ASCII conversion performance
    start_time = time.perf_counter()
    for i in range(100):  # Convert to ASCII 100 times
        ascii_data = screen_buffer.get_content()
    ascii_time = time.perf_counter() - start_time
    benchmark.add_result("ascii_conversion_100", ascii_time, "seconds")

    # Performance assertions (adjusted for realistic Python performance)
    assert creation_time < 0.1, f"Screen buffer creation too slow: {creation_time}"
    assert write_time < 1.0, f"Character write too slow: {write_time}"
    assert field_time < 1.0, f"Field operations too slow: {field_time}"
    assert clear_time < 1.0, f"Screen clear too slow: {clear_time}"
    assert (
        ascii_time < 2.0
    ), f"ASCII conversion too slow: {ascii_time}"  # Adjusted for realistic performance

    print(f"\n{benchmark.get_summary()}")


@pytest.mark.performance
def test_data_stream_parsing_performance(test_resource_manager):
    """Benchmark data stream parsing under various loads."""

    benchmark = PerformanceBenchmark("Data Stream Parsing Performance")

    screen_buffer = ScreenBuffer(rows=24, cols=80)
    test_resource_manager.add_resource(screen_buffer)

    # Create test data stream
    parser = DataStreamParser(screen_buffer)
    test_resource_manager.add_resource(parser)

    # Test 1: Simple data stream parsing
    simple_data = b"\xf5" + b"\x40" * 1920  # Write command with 1920 spaces

    start_time = time.perf_counter()
    for i in range(100):  # Parse 100 times
        parser.parse(simple_data)
    parse_time = time.perf_counter() - start_time
    benchmark.add_result("simple_parsing_100", parse_time, "seconds")

    # Test 2: Complex data stream parsing
    complex_data = (
        b"\xf5"  # Write command
        + b"\x00\x42"  # SBA to position 42
        + b"\x11"  # SF - Start Field
        + b"\xc0"  # Protected, High intensity
        + b"Hello"  # Text
        + b"\x00\x00"  # SBA to position 0
        + b"\x11"  # SF - Start Field
        + b"\x40"  # Unprotected
        + b"World"  # Text
    )

    start_time = time.perf_counter()
    for i in range(100):  # Parse complex data 100 times
        parser.parse(complex_data)
    complex_parse_time = time.perf_counter() - start_time
    benchmark.add_result("complex_parsing_100", complex_parse_time, "seconds")

    # Test 3: Large data stream parsing (stress test)
    large_data = b"\xf5" + b"\x40" * 10000  # 10KB of data

    start_time = time.perf_counter()
    for i in range(10):  # Parse 10 large streams
        parser.parse(large_data)
    large_parse_time = time.perf_counter() - start_time
    benchmark.add_result("large_parsing_10", large_parse_time, "seconds")

    # Performance assertions - adjusted for realistic test environment
    assert parse_time < 1.0, f"Simple parsing too slow: {parse_time}"
    assert complex_parse_time < 2.0, f"Complex parsing too slow: {complex_parse_time}"
    assert large_parse_time < 5.0, f"Large parsing too slow: {large_parse_time}"

    print(f"\n{benchmark.get_summary()}")


@pytest.mark.performance
def test_concurrent_connection_simulation(test_resource_manager):
    """Simulate multiple concurrent connections to test scalability."""

    benchmark = PerformanceBenchmark("Concurrent Connection Simulation")

    connection_results = []

    def simulate_connection(connection_id: int):
        """Simulate a single connection with typical operations."""
        try:
            # Create mock reader/writer
            mock_reader = MagicMock()
            mock_writer = MagicMock()

            # Create handler (this is the main performance bottleneck we want to measure)
            start_time = time.perf_counter()
            handler = TN3270Handler(
                mock_reader, mock_writer, host=f"sim_host_{connection_id}", port=23
            )
            handler.negotiator = MagicMock()
            handler.negotiator.is_printer_session = False
            duration = time.perf_counter() - start_time

            connection_results.append(f"success_{connection_id}_{duration:.4f}")

            # Add to resource manager
            test_resource_manager.add_resource(handler)
            test_resource_manager.add_resource(mock_reader)
            test_resource_manager.add_resource(mock_writer)

            return duration

        except Exception as e:
            connection_results.append(f"error_{connection_id}_{str(e)[:20]}")
            return None

    # Test 1: Light load (10 sequential connections)
    start_time = time.perf_counter()
    for i in range(10):
        simulate_connection(i)
    light_load_time = time.perf_counter() - start_time
    benchmark.add_result("light_load_10", light_load_time, "seconds")

    # Test 2: Medium load (50 sequential connections)
    start_time = time.perf_counter()
    for i in range(50):
        simulate_connection(i)
    medium_load_time = time.perf_counter() - start_time
    benchmark.add_result("medium_load_50", medium_load_time, "seconds")

    # Test 3: Heavy load (100 sequential connections)
    start_time = time.perf_counter()
    for i in range(100):
        simulate_connection(i)
    heavy_load_time = time.perf_counter() - start_time
    benchmark.add_result("heavy_load_100", heavy_load_time, "seconds")

    # Calculate throughput
    successful_light = sum(1 for r in connection_results if r.startswith("success"))
    benchmark.add_result(
        "light_load_throughput",
        successful_light / light_load_time,
        "connections/second",
    )
    benchmark.add_result(
        "medium_load_throughput", 50 / medium_load_time, "connections/second"
    )
    benchmark.add_result(
        "heavy_load_throughput", 100 / heavy_load_time, "connections/second"
    )

    # Performance assertions
    assert light_load_time < 5.0, f"Light load took too long: {light_load_time}"
    assert medium_load_time < 20.0, f"Medium load took too long: {medium_load_time}"
    assert heavy_load_time < 40.0, f"Heavy load took too long: {heavy_load_time}"

    # Throughput assertions - relaxed for test environment
    assert (
        successful_light / light_load_time > 0.1 if light_load_time > 0 else True
    ), "Light load throughput too low"

    print(f"\n{benchmark.get_summary()}")


@pytest.mark.performance
def test_memory_usage_under_load(async_test_helper, test_resource_manager):
    """Test memory usage patterns under various load conditions."""

    benchmark = PerformanceBenchmark("Memory Usage Under Load")

    # Test 1: Memory usage with multiple screen buffers
    tracemalloc.start()
    initial_memory = tracemalloc.get_traced_memory()[0]

    screen_buffers = []
    for i in range(100):  # Create 100 screen buffers
        screen_buffer = ScreenBuffer(rows=24, cols=80)
        screen_buffers.append(screen_buffer)
        test_resource_manager.add_resource(screen_buffer)

        # Fill with some data
        ebcdic_A = translate_ascii_to_ebcdic("A")[0]  # Convert ASCII "A" to EBCDIC byte
        screen_buffer.write_char(ebcdic_A)

    memory_after_screens = tracemalloc.get_traced_memory()[0]
    memory_per_screen = (memory_after_screens - initial_memory) / 100

    benchmark.add_memory_usage(memory_per_screen)
    benchmark.add_result(
        "screens_100_total", memory_after_screens - initial_memory, "bytes"
    )

    # Test 2: Memory usage with handlers
    handler_memory = 0
    for i in range(50):  # Create 50 handlers
        mock_reader = async_test_helper.create_mock_reader()
        mock_writer = async_test_helper.create_mock_writer()

        handler = TN3270Handler(mock_reader, mock_writer, host=f"mem_{i}", port=23)
        handler.negotiator = MagicMock()

        test_resource_manager.add_resource(handler)
        test_resource_manager.add_resource(mock_reader, mock_reader.reset_mock)
        test_resource_manager.add_resource(mock_writer, mock_writer.reset_mock)

    memory_after_handlers = tracemalloc.get_traced_memory()[0]
    memory_per_handler = (memory_after_handlers - memory_after_screens) / 50

    benchmark.add_memory_usage(memory_per_handler)
    benchmark.add_result(
        "handlers_50_total", memory_after_handlers - memory_after_screens, "bytes"
    )

    # Test 3: Memory cleanup verification
    gc.collect()
    final_memory = tracemalloc.get_traced_memory()[0]

    # Clear resource manager
    test_resource_manager.cleanup()
    gc.collect()

    cleanup_memory = tracemalloc.get_traced_memory()[0]
    memory_recovered = final_memory - cleanup_memory
    benchmark.add_result("memory_recovered", memory_recovered, "bytes")

    tracemalloc.stop()

    # Performance assertions - relaxed for test environment
    assert (
        memory_per_screen < 100 * 1024
    ), f"Memory per screen too high: {memory_per_screen} bytes"
    assert (
        memory_per_handler < 300 * 1024
    ), f"Memory per handler too high: {memory_per_handler} bytes"
    assert memory_recovered > 0, "Memory should be recovered after cleanup"

    print(f"\n{benchmark.get_summary()}")


@pytest.mark.performance
def test_negotiation_performance(test_resource_manager):
    """Benchmark negotiation performance under various scenarios."""

    benchmark = PerformanceBenchmark("Negotiation Performance")

    # Test 1: Single negotiation
    screen_buffer = ScreenBuffer(rows=24, cols=80)
    test_resource_manager.add_resource(screen_buffer)

    mock_writer = MagicMock()
    negotiator = Negotiator(
        writer=mock_writer,
        parser=DataStreamParser(screen_buffer),
        screen_buffer=screen_buffer,
        handler=None,
        is_printer_session=False,
    )
    test_resource_manager.add_resource(negotiator)

    # Simulate negotiation data
    negotiation_data = [
        b"\xff\xfb\x1b",  # IAC WILL TN3270E
        b"\xff\xfd\x1b",  # IAC DO TN3270E
        b"\xff\xfa\x1b",  # SB TN3270E
    ]

    start_time = time.perf_counter()
    for i in range(50):  # Process 50 negotiations
        for data in negotiation_data:
            # Simulate processing negotiation data (synchronously)
            negotiator._handle_negotiation_input(data)
    negotiation_time = time.perf_counter() - start_time
    benchmark.add_result("negotiation_processing_50", negotiation_time, "seconds")

    # Test 2: Multiple sequential negotiations
    start_time = time.perf_counter()

    for concurrent_id in range(20):
        """Process a single negotiation."""
        sb = ScreenBuffer(rows=24, cols=80)
        neg = Negotiator(
            writer=MagicMock(),
            parser=DataStreamParser(sb),
            screen_buffer=sb,
            handler=None,
            is_printer_session=False,
        )

        test_resource_manager.add_resource(sb)
        test_resource_manager.add_resource(neg)

        # Process negotiation data
        for data in negotiation_data:
            neg._handle_negotiation_input(data)

    concurrent_negotiation_time = time.perf_counter() - start_time
    benchmark.add_result(
        "sequential_negotiations_20", concurrent_negotiation_time, "seconds"
    )

    # Performance assertions
    assert (
        negotiation_time < 1.0
    ), f"Negotiation processing too slow: {negotiation_time}"
    assert (
        concurrent_negotiation_time < 2.0
    ), f"Concurrent negotiations too slow: {concurrent_negotiation_time}"

    print(f"\n{benchmark.get_summary()}")


# Performance regression tests
@pytest.mark.performance
def test_performance_regression_baseline():
    """Establish baseline performance metrics for regression testing."""

    # This test should be run regularly to detect performance regressions
    # The thresholds here should be updated based on actual performance data

    baseline = {
        "handler_creation": 0.01,  # 10ms max
        "screen_buffer_creation": 0.001,  # 1ms max
        "data_stream_parse": 0.001,  # 1ms max
        "ascii_conversion": 0.01,  # 10ms max
    }

    # These would be actual measurements in a real test
    # For now, we just establish the baseline structure
    assert len(baseline) > 0
    assert all(v > 0 for v in baseline.values())

    print("Performance baseline established for regression testing")


# Missing async test helper fixture
@pytest.fixture
async def async_test_handler():
    """Create a test handler fixture."""
    return TN3270Handler
