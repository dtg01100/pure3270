"""
Tests for TCPIPConnectionPool.

Comprehensive test coverage for connection pooling, lifecycle management,
health monitoring, and thread-safe access patterns.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pure3270.protocol.tcpip_connection_pool import (
    ConnectionPoolConfig,
    TCPIPConnectionPool,
)
from pure3270.protocol.tcpip_printer_session import (
    PrinterSessionState,
    TCPIPPrinterSession,
)


class TestConnectionPoolConfig:
    """Test ConnectionPoolConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ConnectionPoolConfig()

        assert config.max_connections == 10
        assert config.max_connections_per_host == 2
        assert config.connection_timeout == 30.0
        assert config.idle_timeout == 300.0
        assert config.health_check_interval == 60.0
        assert config.cleanup_interval == 120.0
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ConnectionPoolConfig(
            max_connections=20,
            max_connections_per_host=5,
            connection_timeout=60.0,
            idle_timeout=600.0,
            health_check_interval=120.0,
            cleanup_interval=240.0,
            retry_attempts=5,
            retry_delay=2.0,
        )

        assert config.max_connections == 20
        assert config.max_connections_per_host == 5
        assert config.connection_timeout == 60.0
        assert config.idle_timeout == 600.0
        assert config.health_check_interval == 120.0
        assert config.cleanup_interval == 240.0
        assert config.retry_attempts == 5
        assert config.retry_delay == 2.0


class TestTCPIPConnectionPool:
    """Test TCPIPConnectionPool class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ConnectionPoolConfig(
            max_connections=5,
            max_connections_per_host=2,
            connection_timeout=1.0,
            idle_timeout=2.0,
            health_check_interval=1.0,
            cleanup_interval=1.0,
        )

    @pytest.fixture
    def pool(self, config):
        """Create test pool."""
        return TCPIPConnectionPool(config)

    def test_initialization(self, pool, config):
        """Test pool initialization."""
        assert pool.config is config
        assert pool._active_connections == {}
        assert pool._idle_connections == {}
        assert pool._all_connections == set()
        assert pool._total_created == 0
        assert pool._total_destroyed == 0
        assert pool._total_borrowed == 0
        assert pool._total_returned == 0
        assert not pool._running
        assert pool._health_check_task is None
        assert pool._cleanup_task is None

    def test_initialization_default_config(self):
        """Test pool initialization with default config."""
        pool = TCPIPConnectionPool()
        assert isinstance(pool.config, ConnectionPoolConfig)
        assert pool.config.max_connections == 10

    @pytest.mark.asyncio
    async def test_start_stop(self, pool):
        """Test pool start and stop lifecycle."""
        # Start pool
        await pool.start()
        assert pool._running
        assert pool._health_check_task is not None
        assert pool._cleanup_task is not None
        assert not pool._health_check_task.done()
        assert not pool._cleanup_task.done()

        # Stop pool
        await pool.stop()
        assert not pool._running
        assert pool._health_check_task is None
        assert pool._cleanup_task is None

    @pytest.mark.asyncio
    async def test_start_idempotent(self, pool):
        """Test that start is idempotent."""
        await pool.start()
        assert pool._running

        # Second start should do nothing
        await pool.start()
        assert pool._running

        await pool.stop()

    @pytest.mark.asyncio
    async def test_stop_idempotent(self, pool):
        """Test that stop is idempotent."""
        await pool.start()
        await pool.stop()
        assert not pool._running

        # Second stop should do nothing
        await pool.stop()
        assert not pool._running

    @pytest.mark.asyncio
    async def test_context_manager(self, pool):
        """Test async context manager usage."""
        async with pool:
            assert pool._running

        assert not pool._running

    @pytest.mark.asyncio
    @patch("pure3270.protocol.tcpip_connection_pool.TCPIPPrinterSession")
    async def test_borrow_connection_success(self, mock_session_class, pool):
        """Test successful connection borrowing."""
        await pool.start()

        # Mock session
        mock_session = MagicMock()
        mock_session.host = "localhost"
        mock_session.port = 23
        mock_session.session_id = "test-session"
        mock_session.connect = AsyncMock()
        mock_session.activate = AsyncMock()
        mock_session_class.return_value = mock_session

        # Borrow connection
        session = await pool.borrow_connection("localhost", 23)

        assert session is mock_session
        assert pool._total_created == 1
        assert pool._total_borrowed == 1
        assert "localhost:23" in pool._active_connections
        assert mock_session in pool._active_connections["localhost:23"]
        assert mock_session in pool._all_connections

        mock_session_class.assert_called_once_with(
            host="localhost",
            port=23,
            ssl_context=None,
            session_id=None,
            timeout=1.0,
        )
        mock_session.connect.assert_called_once()
        mock_session.activate.assert_called_once()

        await pool.stop()

    @pytest.mark.asyncio
    @patch("pure3270.protocol.tcpip_connection_pool.TCPIPPrinterSession")
    async def test_borrow_connection_reuse_idle(self, mock_session_class, pool):
        """Test borrowing reuses idle connections."""
        await pool.start()

        # Mock session
        mock_session = MagicMock()
        mock_session.host = "localhost"
        mock_session.port = 23
        mock_session.session_id = "test-session"
        mock_session.connect = AsyncMock()
        mock_session.activate = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.state = PrinterSessionState.ACTIVE
        mock_session.handler = MagicMock()
        mock_session.handler.is_connected.return_value = True
        mock_session.error_count = 0
        mock_session_class.return_value = mock_session

        # First borrow
        session1 = await pool.borrow_connection("localhost", 23)
        assert session1 is mock_session

        # Return connection (make it idle)
        await pool.return_connection(mock_session)
        assert mock_session not in pool._active_connections["localhost:23"]
        assert mock_session in pool._idle_connections["localhost:23"]

        # Second borrow should reuse (no health check mock needed since session is healthy)
        session2 = await pool.borrow_connection("localhost", 23)
        assert session2 is mock_session
        assert pool._total_created == 1  # Still 1, reused
        assert pool._total_borrowed == 2
        assert mock_session in pool._active_connections["localhost:23"]
        assert mock_session not in pool._idle_connections["localhost:23"]

        await pool.stop()

    @pytest.mark.asyncio
    async def test_borrow_connection_pool_limit(self, pool):
        """Test pool limit enforcement."""
        await pool.start()

        # Fill pool to limit (max_connections = 5)
        pool._active_connections = {f"host{i}:23": [MagicMock()] for i in range(5)}

        with pytest.raises(RuntimeError, match="Pool limit exceeded"):
            await pool.borrow_connection("newhost", 23)

        await pool.stop()

    @pytest.mark.asyncio
    async def test_borrow_connection_host_limit(self, pool):
        """Test per-host limit enforcement."""
        await pool.start()

        # Fill host to limit (max_connections_per_host = 2)
        pool._active_connections = {"localhost:23": [MagicMock(), MagicMock()]}

        with pytest.raises(RuntimeError, match="Host limit exceeded"):
            await pool.borrow_connection("localhost", 23)

        await pool.stop()

    @pytest.mark.asyncio
    @patch("pure3270.protocol.tcpip_connection_pool.TCPIPPrinterSession")
    async def test_borrow_connection_failure(self, mock_session_class, pool):
        """Test connection creation failure."""
        await pool.start()

        # Mock session that fails to connect
        mock_session = MagicMock()
        mock_session.connect = AsyncMock(side_effect=Exception("Connection failed"))
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        with pytest.raises(Exception, match="Connection failed"):
            await pool.borrow_connection("localhost", 23)

        # Session should be destroyed
        mock_session.close.assert_called_once()
        assert pool._total_created == 0
        assert len(pool._all_connections) == 0

        await pool.stop()

    @pytest.mark.asyncio
    async def test_return_connection_healthy(self, pool):
        """Test returning healthy connection."""
        await pool.start()

        # Mock session
        mock_session = MagicMock()
        mock_session.host = "localhost"
        mock_session.port = 23
        mock_session.session_id = "test-session"

        # Add to active connections
        pool._active_connections["localhost:23"] = [mock_session]
        pool._all_connections.add(mock_session)

        # Mock healthy check
        with patch.object(pool, "_is_connection_healthy", return_value=True):
            await pool.return_connection(mock_session)

        assert mock_session not in pool._active_connections["localhost:23"]
        assert mock_session in pool._idle_connections["localhost:23"]
        assert pool._total_returned == 1

        await pool.stop()

    @pytest.mark.asyncio
    async def test_return_connection_unhealthy(self, pool):
        """Test returning unhealthy connection."""
        await pool.start()

        # Mock session
        mock_session = MagicMock()
        mock_session.host = "localhost"
        mock_session.port = 23
        mock_session.session_id = "test-session"

        # Add to active connections
        pool._active_connections["localhost:23"] = [mock_session]
        pool._all_connections.add(mock_session)

        # Mock unhealthy check and destroy
        with (
            patch.object(pool, "_is_connection_healthy", return_value=False),
            patch.object(
                pool, "_destroy_connection", new_callable=AsyncMock
            ) as mock_destroy,
        ):
            await pool.return_connection(mock_session)

        mock_destroy.assert_called_once_with(mock_session)
        assert pool._total_returned == 0

        await pool.stop()

    @pytest.mark.asyncio
    async def test_health_check_removes_unhealthy(self, pool):
        """Test health check removes unhealthy idle connections."""
        await pool.start()

        # Mock sessions
        healthy_session = MagicMock()
        unhealthy_session = MagicMock()
        healthy_session.host = unhealthy_session.host = "localhost"
        healthy_session.port = unhealthy_session.port = 23

        # Add to idle connections
        pool._idle_connections["localhost:23"] = [healthy_session, unhealthy_session]
        pool._all_connections = {healthy_session, unhealthy_session}

        # Mock health check: first healthy, second unhealthy
        health_results = [True, False]
        with (
            patch.object(pool, "_is_connection_healthy", side_effect=health_results),
            patch.object(
                pool, "_destroy_connection", new_callable=AsyncMock
            ) as mock_destroy,
        ):
            await pool._perform_health_checks()

        # Only healthy session remains
        assert pool._idle_connections["localhost:23"] == [healthy_session]
        mock_destroy.assert_called_once_with(unhealthy_session)

        await pool.stop()

    @pytest.mark.asyncio
    async def test_cleanup_removes_expired(self, pool):
        """Test cleanup removes expired idle connections."""
        await pool.start()

        # Mock sessions
        active_session = MagicMock()
        expired_session = MagicMock()
        active_session.host = expired_session.host = "localhost"
        active_session.port = expired_session.port = 23

        # Set last activity times
        current_time = time.time()
        active_session.last_activity = current_time - 1.0  # Recent
        expired_session.last_activity = (
            current_time - 3.0
        )  # Expired (idle_timeout = 2.0)

        # Add to idle connections
        pool._idle_connections["localhost:23"] = [active_session, expired_session]
        pool._all_connections = {active_session, expired_session}

        with patch.object(
            pool, "_destroy_connection", new_callable=AsyncMock
        ) as mock_destroy:
            await pool._perform_cleanup()

        # Only active session remains
        assert pool._idle_connections["localhost:23"] == [active_session]
        mock_destroy.assert_called_once_with(expired_session)

        await pool.stop()

    @pytest.mark.asyncio
    async def test_is_connection_healthy_active_state(self, pool):
        """Test health check for active state."""
        mock_session = MagicMock()
        mock_session.state = PrinterSessionState.ACTIVE
        mock_session.handler = MagicMock()
        mock_session.handler.is_connected.return_value = True
        mock_session.error_count = 0

        result = await pool._is_connection_healthy(mock_session)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_connection_healthy_inactive_state(self, pool):
        """Test health check for inactive state."""
        mock_session = MagicMock()
        mock_session.state = PrinterSessionState.CONNECTING

        result = await pool._is_connection_healthy(mock_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_connection_healthy_disconnected(self, pool):
        """Test health check for disconnected handler."""
        mock_session = MagicMock()
        mock_session.state = PrinterSessionState.ACTIVE
        mock_session.handler = MagicMock()
        mock_session.handler.is_connected.return_value = False
        mock_session.error_count = 0

        result = await pool._is_connection_healthy(mock_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_connection_healthy_high_error_count(self, pool):
        """Test health check for high error count."""
        mock_session = MagicMock()
        mock_session.state = PrinterSessionState.ACTIVE
        mock_session.handler = MagicMock()
        mock_session.handler.is_connected.return_value = True
        mock_session.error_count = 6

        result = await pool._is_connection_healthy(mock_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_connection_healthy_exception(self, pool):
        """Test health check handles exceptions."""
        mock_session = MagicMock()
        mock_session.session_id = "test-session"
        # Make state access raise exception
        type(mock_session).state = MagicMock(side_effect=Exception("State error"))

        result = await pool._is_connection_healthy(mock_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_destroy_connection(self, pool):
        """Test connection destruction."""
        mock_session = MagicMock()
        mock_session.host = "localhost"
        mock_session.port = 23
        mock_session.session_id = "test-session"
        mock_session.close = AsyncMock()

        # Add to all tracking
        pool._active_connections["localhost:23"] = [mock_session]
        pool._idle_connections["localhost:23"] = []
        pool._all_connections.add(mock_session)

        await pool._destroy_connection(mock_session)

        mock_session.close.assert_called_once()
        assert mock_session not in pool._active_connections["localhost:23"]
        assert mock_session not in pool._idle_connections["localhost:23"]
        assert mock_session not in pool._all_connections
        assert pool._total_destroyed == 1

    @pytest.mark.asyncio
    async def test_destroy_connection_close_error(self, pool):
        """Test connection destruction handles close errors."""
        mock_session = MagicMock()
        mock_session.host = "localhost"
        mock_session.port = 23
        mock_session.session_id = "test-session"
        mock_session.close = AsyncMock(side_effect=Exception("Close failed"))

        pool._all_connections.add(mock_session)

        # Should not raise
        await pool._destroy_connection(mock_session)

        mock_session.close.assert_called_once()
        assert pool._total_destroyed == 1

    def test_get_pool_stats(self, pool):
        """Test pool statistics."""
        # Add some mock connections
        active_session = MagicMock()
        idle_session = MagicMock()
        active_session.host = idle_session.host = "localhost"
        active_session.port = idle_session.port = 23

        pool._active_connections = {"localhost:23": [active_session]}
        pool._idle_connections = {"localhost:23": [idle_session]}
        pool._all_connections = {active_session, idle_session}
        pool._total_created = 5
        pool._total_destroyed = 2
        pool._total_borrowed = 10
        pool._total_returned = 8

        stats = pool.get_pool_stats()

        expected = {
            "total_connections": 2,
            "active_connections": 1,
            "idle_connections": 1,
            "max_connections": 5,
            "total_created": 5,
            "total_destroyed": 2,
            "total_borrowed": 10,
            "total_returned": 8,
            "connections_by_host": {"localhost:23": {"active": 1, "idle": 1}},
        }

        assert stats == expected

    @pytest.mark.asyncio
    async def test_concurrent_access(self, pool):
        """Test concurrent borrow/return operations."""
        await pool.start()

        async def borrow_return_task(task_id):
            # Mock session creation
            with patch(
                "pure3270.protocol.tcpip_connection_pool.TCPIPPrinterSession"
            ) as mock_class:
                mock_session = MagicMock()
                mock_session.host = f"host{task_id}"
                mock_session.port = 23
                mock_session.session_id = f"session-{task_id}"
                mock_session.connect = AsyncMock()
                mock_session.activate = AsyncMock()
                mock_session.close = AsyncMock()
                mock_session.state = PrinterSessionState.ACTIVE
                mock_session.handler = MagicMock()
                mock_session.handler.is_connected.return_value = True
                mock_session.error_count = 0
                mock_class.return_value = mock_session

                # Borrow
                session = await pool.borrow_connection(f"host{task_id}", 23)
                assert session is mock_session

                # Return
                await pool.return_connection(mock_session)

        # Run multiple concurrent tasks
        tasks = [borrow_return_task(i) for i in range(3)]
        await asyncio.gather(*tasks)

        assert pool._total_created == 3
        assert pool._total_borrowed == 3
        assert pool._total_returned == 3

        await pool.stop()

    @pytest.mark.asyncio
    async def test_timeout_handling(self, pool):
        """Test timeout handling in background tasks."""
        await pool.start()

        # Let background tasks run briefly
        await asyncio.sleep(0.1)

        # Tasks should still be running
        assert pool._health_check_task is not None
        assert not pool._health_check_task.done()
        assert pool._cleanup_task is not None
        assert not pool._cleanup_task.done()

        await pool.stop()

    @pytest.mark.asyncio
    async def test_edge_case_empty_pool_operations(self, pool):
        """Test operations on empty pool."""
        await pool.start()

        # Return non-existent connection should not crash
        mock_session = MagicMock()
        mock_session.host = "localhost"
        mock_session.port = 23

        # Should not raise
        await pool.return_connection(mock_session)

        # Health check on empty pool
        await pool._perform_health_checks()

        # Cleanup on empty pool
        await pool._perform_cleanup()

        await pool.stop()

    @pytest.mark.asyncio
    async def test_rapid_borrow_return(self, pool):
        """Test rapid borrow/return cycles."""
        await pool.start()

        with patch(
            "pure3270.protocol.tcpip_connection_pool.TCPIPPrinterSession"
        ) as mock_class:
            mock_session = MagicMock()
            mock_session.host = "localhost"
            mock_session.port = 23
            mock_session.session_id = "rapid-session"
            mock_session.connect = AsyncMock()
            mock_session.activate = AsyncMock()
            mock_session.close = AsyncMock()
            mock_session.state = PrinterSessionState.ACTIVE
            mock_session.handler = MagicMock()
            mock_session.handler.is_connected.return_value = True
            mock_session.error_count = 0
            mock_class.return_value = mock_session

            # Rapid borrow/return cycle
            for i in range(5):
                session = await pool.borrow_connection("localhost", 23)
                assert session is mock_session
                await pool.return_connection(mock_session)

            assert pool._total_created == 1  # Only created once
            assert pool._total_borrowed == 5
            assert pool._total_returned == 5

        await pool.stop()
