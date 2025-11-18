#!/usr/bin/env python3
"""
Example: Connection Management and Pooling Patterns

This example demonstrates connection management strategies for pure3270:
- Connection pooling implementation for regular TN3270 sessions
- Connection reuse patterns
- Resource management and cleanup
- Connection health monitoring
- Load balancing across multiple hosts
- Timeout and retry strategies

Requires: pure3270 installed in venv.
Run: python examples/example_connection_management.py
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Set

from pure3270 import AsyncSession, Session, setup_logging
from pure3270.exceptions import *

# Setup logging to see connection details
setup_logging(level="INFO")


class ConnectionPool:
    """
    Simple connection pool for TN3270 sessions.

    Demonstrates connection reuse, health monitoring, and resource management.
    """

    def __init__(
        self,
        max_connections: int = 5,
        max_idle_time: float = 300.0,  # 5 minutes
        health_check_interval: float = 60.0,  # 1 minute
    ):
        self.max_connections = max_connections
        self.max_idle_time = max_idle_time
        self.health_check_interval = health_check_interval

        # Connection storage
        self._available: List[AsyncSession] = []
        self._in_use: Set[AsyncSession] = set()
        self._last_used: Dict[AsyncSession, float] = {}

        # Pool management
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the connection pool."""
        async with self._lock:
            if self._running:
                return
            self._running = True
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            print("✓ Connection pool started")

    async def stop(self):
        """Stop the connection pool and cleanup all connections."""
        async with self._lock:
            if not self._running:
                return
            self._running = False

            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass

            # Close all connections
            close_tasks = []
            for session in list(self._available) + list(self._in_use):
                close_tasks.append(self._close_session(session))

            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)

            self._available.clear()
            self._in_use.clear()
            self._last_used.clear()
            print("✓ Connection pool stopped")

    @asynccontextmanager
    async def get_connection(self, host: str, port: int = 23, **kwargs):
        """
        Context manager for getting a connection from the pool.

        Usage:
            async with pool.get_connection('host.com') as session:
                # Use session
                pass
        """
        session = await self._acquire_connection(host, port, **kwargs)
        try:
            yield session
        finally:
            await self._release_connection(session)

    async def _acquire_connection(
        self, host: str, port: int = 23, **kwargs
    ) -> AsyncSession:
        """Acquire a connection from the pool."""
        async with self._lock:
            # Try to reuse an existing connection
            for session in self._available:
                if await self._is_connection_healthy(session):
                    self._available.remove(session)
                    self._in_use.add(session)
                    self._last_used[session] = time.time()
                    print(f"✓ Reused connection to {host}:{port}")
                    return session
                else:
                    # Remove unhealthy connection
                    await self._close_session(session)
                    self._available.remove(session)

            # Check pool limits
            total_connections = len(self._available) + len(self._in_use)
            if total_connections >= self.max_connections:
                raise RuntimeError(
                    f"Connection pool limit exceeded: {total_connections}/{self.max_connections}"
                )

            # Create new connection
            session = AsyncSession(**kwargs)
            await session.connect(host, port)
            self._in_use.add(session)
            self._last_used[session] = time.time()
            print(f"✓ Created new connection to {host}:{port}")
            return session

    async def _release_connection(self, session: AsyncSession):
        """Release a connection back to the pool."""
        async with self._lock:
            if session in self._in_use:
                self._in_use.remove(session)

                # Check if connection is still healthy
                if await self._is_connection_healthy(session):
                    self._available.append(session)
                    self._last_used[session] = time.time()
                    print("✓ Connection returned to pool")
                else:
                    await self._close_session(session)
                    print("✓ Unhealthy connection closed")

    async def _is_connection_healthy(self, session: AsyncSession) -> bool:
        """Check if a connection is healthy."""
        try:
            # Basic connectivity check - try a simple operation
            # In a real implementation, you might send a NOOP or check session state
            return session.connected
        except Exception:
            return False

    async def _close_session(self, session: AsyncSession):
        """Close a session safely."""
        try:
            await session.close()
        except Exception as e:
            print(f"Warning: Error closing session: {e}")

    async def _health_check_loop(self):
        """Background health check task."""
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Health check error: {e}")

    async def _perform_health_checks(self):
        """Perform health checks on available connections."""
        async with self._lock:
            unhealthy = []
            current_time = time.time()

            for session in self._available:
                # Check idle timeout
                last_used = self._last_used.get(session, 0)
                if current_time - last_used > self.max_idle_time:
                    unhealthy.append(session)
                    print("✓ Connection expired due to idle timeout")
                elif not await self._is_connection_healthy(session):
                    unhealthy.append(session)
                    print("✓ Unhealthy connection found during health check")

            # Remove unhealthy connections
            for session in unhealthy:
                if session in self._available:
                    self._available.remove(session)
                await self._close_session(session)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            "available": len(self._available),
            "in_use": len(self._in_use),
            "total": len(self._available) + len(self._in_use),
            "max_connections": self.max_connections,
        }


class LoadBalancer:
    """
    Simple load balancer for distributing connections across multiple hosts.
    """

    def __init__(self, hosts: List[str], port: int = 23):
        self.hosts = hosts
        self.port = port
        self._current_index = 0
        self._lock = asyncio.Lock()

    async def get_next_host(self) -> str:
        """Get the next host in round-robin fashion."""
        async with self._lock:
            host = self.hosts[self._current_index]
            self._current_index = (self._current_index + 1) % len(self.hosts)
            return host


async def demo_basic_connection_management():
    """Demonstrate basic connection management patterns."""
    print("=== Basic Connection Management Demo ===")

    # Manual connection management
    print("Manual connection management:")
    session = AsyncSession()
    try:
        # This will fail without a real host, but shows the pattern
        print("Attempting connection (will fail without real TN3270 host)...")
        try:
            await session.connect("demo.host", port=23)
        except Exception as e:
            print(f"✓ Expected connection failure: {type(e).__name__}")

        # Show proper cleanup
        await session.close()
        print("✓ Connection properly closed")

    except Exception as e:
        print(f"Error in manual management: {e}")


async def demo_connection_pooling():
    """Demonstrate connection pooling."""
    print("\n=== Connection Pooling Demo ===")

    pool = ConnectionPool(max_connections=3, max_idle_time=10.0)
    await pool.start()

    try:
        print(f"Pool stats: {pool.get_stats()}")

        # Simulate multiple connection requests
        tasks = []
        for i in range(5):

            async def use_connection(task_id: int):
                try:
                    # Simulate connection usage
                    async with pool.get_connection("demo.host", port=23) as session:
                        print(f"Task {task_id}: Got connection")
                        await asyncio.sleep(0.1)  # Simulate work
                        print(f"Task {task_id}: Released connection")
                except Exception as e:
                    print(
                        f"Task {task_id}: Connection failed (expected): {type(e).__name__}"
                    )

            tasks.append(use_connection(i))

        await asyncio.gather(*tasks)

        print(f"Final pool stats: {pool.get_stats()}")

    finally:
        await pool.stop()


async def demo_load_balancing():
    """Demonstrate load balancing across multiple hosts."""
    print("\n=== Load Balancing Demo ===")

    hosts = ["host1.example.com", "host2.example.com", "host3.example.com"]
    balancer = LoadBalancer(hosts)

    print("Load balancing across hosts:")
    for i in range(6):
        host = await balancer.get_next_host()
        print(f"Request {i+1}: {host}")


async def demo_retry_and_timeout_patterns():
    """Demonstrate retry and timeout patterns."""
    print("\n=== Retry and Timeout Patterns Demo ===")

    async def connect_with_retry(
        host: str, port: int = 23, max_retries: int = 3, timeout: float = 5.0
    ):
        """Connect with retry logic."""
        for attempt in range(max_retries):
            try:
                print(
                    f"Connection attempt {attempt + 1}/{max_retries} to {host}:{port}"
                )
                session = AsyncSession()

                # Use asyncio.wait_for for timeout
                await asyncio.wait_for(session.connect(host, port), timeout=timeout)

                print(f"✓ Connected successfully on attempt {attempt + 1}")
                return session

            except asyncio.TimeoutError:
                print(f"✗ Attempt {attempt + 1} timed out")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0)  # Backoff delay
            except Exception as e:
                print(f"✗ Attempt {attempt + 1} failed: {type(e).__name__}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0)

        raise RuntimeError(f"Failed to connect after {max_retries} attempts")

    # Demonstrate retry pattern (will fail but shows the framework)
    try:
        session = await connect_with_retry(
            "unreachable.host", max_retries=2, timeout=1.0
        )
        await session.close()
    except RuntimeError as e:
        print(f"✓ Retry pattern completed: {e}")


async def demo_resource_management():
    """Demonstrate proper resource management."""
    print("\n=== Resource Management Demo ===")

    @asynccontextmanager
    async def managed_session(host: str, port: int = 23, **kwargs):
        """Context manager for session lifecycle management."""
        session = AsyncSession(**kwargs)
        try:
            await session.connect(host, port)
            print(f"✓ Session established to {host}:{port}")
            yield session
        except Exception as e:
            print(f"✗ Session failed: {e}")
            raise
        finally:
            await session.close()
            print("✓ Session cleaned up")

    # Demonstrate context manager usage
    try:
        async with managed_session("demo.host", port=23) as session:
            print("Using session within context manager...")
            # Session automatically cleaned up on exit
    except Exception as e:
        print(f"✓ Context manager handled error: {type(e).__name__}")


async def demo_connection_monitoring():
    """Demonstrate connection monitoring and metrics."""
    print("\n=== Connection Monitoring Demo ===")

    class ConnectionMonitor:
        """Monitor connection health and collect metrics."""

        def __init__(self):
            self.connections_created = 0
            self.connections_closed = 0
            self.connection_errors = 0
            self._lock = asyncio.Lock()

        async def record_connection_created(self):
            async with self._lock:
                self.connections_created += 1

        async def record_connection_closed(self):
            async with self._lock:
                self.connections_closed += 1

        async def record_connection_error(self):
            async with self._lock:
                self.connection_errors += 1

        def get_metrics(self) -> Dict[str, int]:
            return {
                "connections_created": self.connections_created,
                "connections_closed": self.connections_closed,
                "connection_errors": self.connection_errors,
                "active_connections": self.connections_created
                - self.connections_closed,
            }

    monitor = ConnectionMonitor()

    # Simulate some connection activity
    for i in range(3):
        await monitor.record_connection_created()
        if i % 2 == 0:  # Simulate some errors
            await monitor.record_connection_error()
        await monitor.record_connection_closed()

    print(f"Connection metrics: {monitor.get_metrics()}")


async def main():
    """Run all connection management demonstrations."""
    print("Pure3270 Connection Management and Pooling Patterns Demo")
    print("=" * 70)

    try:
        await demo_basic_connection_management()
        await demo_connection_pooling()
        await demo_load_balancing()
        await demo_retry_and_timeout_patterns()
        await demo_resource_management()
        await demo_connection_monitoring()

        print("\n" + "=" * 70)
        print("✓ All connection management patterns demonstrated")
        print("\nKey takeaways:")
        print("- Always use context managers for automatic cleanup")
        print("- Implement connection pooling for performance")
        print("- Use retry logic with exponential backoff for reliability")
        print("- Monitor connection health and collect metrics")
        print("- Load balance across multiple hosts when available")
        print("- Set appropriate timeouts to prevent hanging")

    except Exception as e:
        print(f"Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
