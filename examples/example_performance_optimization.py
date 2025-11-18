#!/usr/bin/env python3
"""
Example: Performance Optimization Techniques

This example demonstrates performance optimization strategies for pure3270:
- Efficient screen reading and parsing
- Batch operations and pipelining
- Connection reuse and pooling
- Memory optimization techniques
- Async patterns for high throughput
- Caching strategies
- Profiling and benchmarking

Requires: pure3270 installed in venv.
Run: python examples/example_performance_optimization.py
"""

import asyncio
import cProfile
import io
import pstats
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

from pure3270 import AsyncSession, Session, setup_logging
from pure3270.emulation.screen_buffer import ScreenBuffer

# Setup logging (minimal for performance)
setup_logging(level="WARNING")


class PerformanceMonitor:
    """Monitor performance metrics during operations."""

    def __init__(self):
        self.start_time = None
        self.operations = 0
        self.total_time = 0.0
        self.min_time = float("inf")
        self.max_time = 0.0

    def start_operation(self):
        """Start timing an operation."""
        self.start_time = time.perf_counter()

    def end_operation(self):
        """End timing an operation."""
        if self.start_time is not None:
            duration = time.perf_counter() - self.start_time
            self.operations += 1
            self.total_time += duration
            self.min_time = min(self.min_time, duration)
            self.max_time = max(self.max_time, duration)
            self.start_time = None
            return duration
        return 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if self.operations == 0:
            return {
                "operations": 0,
                "avg_time": 0,
                "min_time": 0,
                "max_time": 0,
                "total_time": 0,
            }

        return {
            "operations": self.operations,
            "avg_time": self.total_time / self.operations,
            "min_time": self.min_time,
            "max_time": self.max_time,
            "total_time": self.total_time,
            "ops_per_sec": (
                self.operations / self.total_time if self.total_time > 0 else 0
            ),
        }


async def demo_efficient_screen_reading():
    """Demonstrate efficient screen reading techniques."""
    print("=== Efficient Screen Reading Demo ===")

    # Create a session with a large screen for testing
    session = AsyncSession(terminal_type="IBM-3278-4")  # 43x80 screen

    try:
        # Simulate screen content (without actual connection)
        sb = session.screen_buffer

        # Fill screen with test data
        test_content = "This is test content for performance benchmarking. " * 10
        for row in range(min(10, sb.rows)):
            for col in range(min(len(test_content), sb.cols)):
                if col < len(test_content):
                    sb.write_char(ord(test_content[col]), row=row, col=col)

        monitor = PerformanceMonitor()

        # Test 1: Full screen reading
        print("Testing full screen reading...")
        for _ in range(1000):
            monitor.start_operation()
            full_screen = sb.to_text()
            monitor.end_operation()

        stats = monitor.get_stats()
        print(".4f" ".1f")

        # Test 2: Area reading (more efficient for specific regions)
        monitor = PerformanceMonitor()
        print("Testing area reading...")
        for _ in range(1000):
            monitor.start_operation()
            # Read only rows 2-8, columns 10-60
            area_content = ""
            for row in range(2, 9):
                for col in range(10, 61):
                    pos = row * sb.cols + col
                    if pos < len(sb.buffer):
                        char_code = sb.buffer[pos]
                        area_content += chr(char_code) if char_code != 0x40 else " "
            monitor.end_operation()

        stats = monitor.get_stats()
        print(".4f" ".1f")

        # Test 3: Character-by-character reading (least efficient)
        monitor = PerformanceMonitor()
        print("Testing character-by-character reading...")
        for _ in range(1000):
            monitor.start_operation()
            chars = []
            for row in range(sb.rows):
                for col in range(sb.cols):
                    pos = row * sb.cols + col
                    if pos < len(sb.buffer):
                        chars.append(chr(sb.buffer[pos]))
            result = "".join(chars)
            monitor.end_operation()

        stats = monitor.get_stats()
        print(".4f" ".1f")

    finally:
        await session.close()


async def demo_batch_operations():
    """Demonstrate batch operations for improved performance."""
    print("\n=== Batch Operations Demo ===")

    session = AsyncSession()

    try:
        monitor = PerformanceMonitor()

        # Simulate batch string input operations
        print("Testing batch string operations...")
        batch_strings = [
            "USERID",
            "PASSWORD",
            "COMMAND1",
            "COMMAND2",
            "COMMAND3",
        ] * 50  # 250 operations

        for string_data in batch_strings:
            monitor.start_operation()
            # In real usage, this would send to host
            # For demo, we simulate the operation
            simulated_delay = 0.001  # 1ms simulated network delay
            await asyncio.sleep(simulated_delay)
            monitor.end_operation()

        stats = monitor.get_stats()
        print(".4f" ".1f")

        # Demonstrate pipelining concept
        print("Testing pipelined operations...")
        monitor = PerformanceMonitor()

        async def pipelined_operation(op_id: int):
            """Simulate a pipelined operation."""
            # Simulate async operation with some processing
            await asyncio.sleep(0.001)
            return f"result_{op_id}"

        # Execute multiple operations concurrently
        tasks = [pipelined_operation(i) for i in range(100)]
        monitor.start_operation()
        results = await asyncio.gather(*tasks)
        total_time = monitor.end_operation()

        print(".4f" ".1f")

    finally:
        await session.close()


async def demo_connection_reuse():
    """Demonstrate connection reuse for performance."""
    print("\n=== Connection Reuse Demo ===")

    class SimpleConnectionPool:
        """Simple connection pool for demonstration."""

        def __init__(self, pool_size: int = 3):
            self.pool_size = pool_size
            self.available: List[AsyncSession] = []
            self.created = 0

        async def get_connection(self) -> AsyncSession:
            if self.available:
                return self.available.pop()
            elif self.created < self.pool_size:
                self.created += 1
                return AsyncSession()
            else:
                raise RuntimeError("Pool exhausted")

        async def return_connection(self, session: AsyncSession):
            if len(self.available) < self.pool_size:
                self.available.append(session)

    pool = SimpleConnectionPool(pool_size=2)
    monitor = PerformanceMonitor()

    print("Testing connection reuse...")
    for i in range(10):
        monitor.start_operation()

        # Get connection from pool
        session = await pool.get_connection()

        # Simulate usage
        await asyncio.sleep(0.001)

        # Return to pool
        await pool.return_connection(session)

        monitor.end_operation()

    stats = monitor.get_stats()
    print(".4f" ".1f")
    print(f"  Connections created: {pool.created}")


async def demo_memory_optimization():
    """Demonstrate memory optimization techniques."""
    print("\n=== Memory Optimization Demo ===")

    import gc
    import os

    import psutil

    def get_memory_usage():
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    initial_memory = get_memory_usage()
    print(".1f")

    # Test 1: Efficient screen buffer operations
    sessions = []
    for i in range(10):
        session = AsyncSession(terminal_type="IBM-3278-4")  # Large screen
        sessions.append(session)

        # Fill with data
        sb = session.screen_buffer
        for row in range(sb.rows):
            for col in range(sb.cols):
                sb.write_char(ord("X"), row=row, col=col)

    after_creation = get_memory_usage()
    print(".1f")

    # Clean up properly
    for session in sessions:
        await session.close()

    del sessions
    gc.collect()

    after_cleanup = get_memory_usage()
    print(".1f")
    print(".1f")


async def demo_async_patterns():
    """Demonstrate async patterns for high performance."""
    print("\n=== Async Patterns Demo ===")

    async def simulate_host_operation(session_id: int, operation: str) -> str:
        """Simulate a host operation with variable timing."""
        # Simulate network latency
        await asyncio.sleep(0.005 + (session_id * 0.001))
        return f"Session {session_id}: {operation} completed"

    monitor = PerformanceMonitor()

    # Test 1: Sequential operations
    print("Testing sequential operations...")
    monitor.start_operation()
    results = []
    for i in range(10):
        result = await simulate_host_operation(i, f"operation_{i}")
        results.append(result)
    sequential_time = monitor.end_operation()

    print(".4f")

    # Test 2: Concurrent operations
    print("Testing concurrent operations...")
    monitor.start_operation()
    tasks = [simulate_host_operation(i, f"operation_{i}") for i in range(10)]
    results = await asyncio.gather(*tasks)
    concurrent_time = monitor.end_operation()

    print(".4f")
    print(".2f")


async def demo_caching_strategies():
    """Demonstrate caching strategies for performance."""
    print("\n=== Caching Strategies Demo ===")

    class ScreenCache:
        """Simple screen content cache."""

        def __init__(self):
            self.cache: Dict[str, Tuple[str, float]] = {}
            self.max_age = 5.0  # 5 seconds

        def get(self, key: str) -> Optional[str]:
            if key in self.cache:
                content, timestamp = self.cache[key]
                if time.time() - timestamp < self.max_age:
                    return content
                else:
                    del self.cache[key]
            return None

        def put(self, key: str, content: str):
            self.cache[key] = (content, time.time())

        def cleanup(self):
            """Remove expired entries."""
            current_time = time.time()
            expired = [
                key
                for key, (_, timestamp) in self.cache.items()
                if current_time - timestamp >= self.max_age
            ]
            for key in expired:
                del self.cache[key]

    cache = ScreenCache()
    monitor = PerformanceMonitor()

    print("Testing caching performance...")

    # Simulate screen reading with caching
    for i in range(100):
        key = f"screen_{i % 5}"  # Repeat keys to test cache hits

        monitor.start_operation()

        # Check cache first
        cached_content = cache.get(key)
        if cached_content:
            content = cached_content
        else:
            # Simulate expensive screen read
            await asyncio.sleep(0.001)
            content = f"Screen content for {key}"
            cache.put(key, content)

        monitor.end_operation()

    stats = monitor.get_stats()
    print(".4f" ".1f")
    print(f"  Cache size: {len(cache.cache)}")


def demo_profiling():
    """Demonstrate profiling techniques."""
    print("\n=== Profiling Demo ===")

    def expensive_operation():
        """Simulate an expensive operation."""
        session = Session()
        sb = session.screen_buffer

        # Perform many screen operations
        for _ in range(1000):
            for row in range(min(10, sb.rows)):
                for col in range(min(40, sb.cols)):
                    sb.write_char(ord("A"), row=row, col=col)
            sb.to_text()

        session.close()

    print("Profiling expensive screen operations...")

    # Profile the operation
    profiler = cProfile.Profile()
    profiler.enable()

    expensive_operation()

    profiler.disable()

    # Get profiling results
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(10)  # Top 10 functions

    print("Top 10 most time-consuming functions:")
    print(s.getvalue())


async def demo_performance_best_practices():
    """Demonstrate performance best practices."""
    print("\n=== Performance Best Practices Demo ===")

    print("Performance optimization best practices:")
    print("1. Use connection pooling to avoid connection overhead")
    print("2. Read only the screen areas you need")
    print("3. Batch operations when possible")
    print("4. Use async operations for concurrency")
    print("5. Cache frequently accessed data")
    print("6. Profile your code to identify bottlenecks")
    print("7. Use appropriate terminal types for your needs")
    print("8. Close sessions properly to free resources")

    # Demonstrate proper resource management
    @asynccontextmanager
    async def optimized_session(host: str, **kwargs):
        """Optimized session context manager."""
        session = AsyncSession(**kwargs)
        try:
            # Simulate connection (would be real in production)
            print(f"✓ Optimized session created for {host}")
            yield session
        finally:
            await session.close()
            print("✓ Session resources freed")

    # Show usage
    try:
        async with optimized_session(
            "example.com", terminal_type="IBM-3278-2"
        ) as session:
            print("Performing optimized operations...")
            # Operations would go here
    except Exception as e:
        print(f"✓ Error handled gracefully: {type(e).__name__}")


async def main():
    """Run all performance optimization demonstrations."""
    print("Pure3270 Performance Optimization Techniques Demo")
    print("=" * 60)

    try:
        await demo_efficient_screen_reading()
        await demo_batch_operations()
        await demo_connection_reuse()
        await demo_memory_optimization()
        await demo_async_patterns()
        await demo_caching_strategies()
        demo_profiling()
        await demo_performance_best_practices()

        print("\n" + "=" * 60)
        print("✓ All performance optimization techniques demonstrated")
        print("\nKey takeaways:")
        print("- Profile your code to identify performance bottlenecks")
        print("- Use connection pooling and reuse for network efficiency")
        print("- Read screen data efficiently (areas vs full screen)")
        print("- Leverage async operations for concurrency")
        print("- Implement caching for frequently accessed data")
        print("- Batch operations to reduce round trips")
        print("- Monitor memory usage and clean up resources properly")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
