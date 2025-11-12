# ATTRIBUTION NOTICE
# =================================================================================
# This module contains code ported from or inspired by: IBM s3270/x3270
# Source: https://github.com/rhacker/x3270
# Licensed under BSD-3-Clause
#
# DESCRIPTION
# --------------------
# TCPIPPrinterSessionManager tests.
#
# Comprehensive tests for printer session management functionality.
# """

import asyncio
import unittest.mock
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from pure3270.protocol.tcpip_connection_pool import ConnectionPoolConfig
from pure3270.protocol.tcpip_printer_session import PrinterSessionState
from pure3270.protocol.tcpip_printer_session_manager import TCPIPPrinterSessionManager


class TestTCPIPPrinterSessionManager:
    """Tests for TCPIPPrinterSessionManager functionality."""

    @pytest.fixture
    def mock_connection_pool(self):
        """Create a mock connection pool."""
        pool = AsyncMock()
        pool.start = AsyncMock()
        pool.stop = AsyncMock()
        pool.borrow_connection = AsyncMock()
        pool.return_connection = AsyncMock()
        pool.get_pool_stats = Mock(return_value={"active": 1, "idle": 0})
        return pool

    @pytest.fixture
    def mock_printer_session(self):
        """Create a mock printer session."""
        session = AsyncMock()
        session.session_id = "test_session_123"
        session.host = "test.host.com"
        session.port = 23
        session.is_active = True
        session.send_print_data = AsyncMock()
        session.send_printer_status = AsyncMock()
        session.receive_data = AsyncMock(return_value=b"test data")
        session.close = AsyncMock()
        session.get_session_info = Mock(
            return_value={"id": "test_session_123", "host": "test.host.com"}
        )
        session._set_state = AsyncMock()
        return session

    @pytest.fixture
    def session_manager(self, mock_connection_pool):
        """Create a session manager with mocked dependencies."""
        manager = TCPIPPrinterSessionManager()
        manager.connection_pool = mock_connection_pool
        return manager

    @pytest.mark.asyncio
    async def test_initialization_default_config(self):
        """Test initialization with default configuration."""
        manager = TCPIPPrinterSessionManager()
        assert manager.pool_config is not None
        assert isinstance(manager.pool_config, ConnectionPoolConfig)
        assert not manager._started
        assert manager._active_sessions == {}

    @pytest.mark.asyncio
    async def test_initialization_custom_config(self):
        """Test initialization with custom configuration."""
        config = ConnectionPoolConfig(max_connections=10, connection_timeout=30.0)
        manager = TCPIPPrinterSessionManager(pool_config=config)
        assert manager.pool_config == config
        assert not manager._started

    @pytest.mark.asyncio
    async def test_start_manager(self, session_manager, mock_connection_pool):
        """Test starting the session manager."""
        await session_manager.start()
        assert session_manager._started
        mock_connection_pool.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_manager_already_started(self, session_manager):
        """Test starting an already started manager."""
        session_manager._started = True
        with pytest.raises(RuntimeError, match="Session manager already started"):
            await session_manager.start()

    @pytest.mark.asyncio
    async def test_stop_manager(
        self, session_manager, mock_connection_pool, mock_printer_session
    ):
        """Test stopping the session manager."""
        session_manager._started = True
        session_manager._active_sessions = {"test": mock_printer_session}

        await session_manager.stop()

        assert not session_manager._started
        assert session_manager._active_sessions == {}
        mock_connection_pool.stop.assert_called_once()
        mock_printer_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_manager_not_started(
        self, session_manager, mock_connection_pool
    ):
        """Test stopping a manager that hasn't been started."""
        with pytest.raises(RuntimeError, match="Session manager not started"):
            await session_manager.stop()

    @pytest.mark.asyncio
    async def test_create_printer_session_success(
        self, session_manager, mock_connection_pool, mock_printer_session
    ):
        """Test successful printer session creation."""
        session_manager._started = True
        mock_connection_pool.borrow_connection.return_value = ("host", 23)

        # Mock the session creation
        with unittest.mock.patch(
            "pure3270.protocol.tcpip_printer_session_manager.TCPIPPrinterSession",
            return_value=mock_printer_session,
        ):
            session_id = await session_manager.create_printer_session(
                "test.host.com", 23
            )

            assert session_id == "test_session_123"
            assert session_id in session_manager._active_sessions
            mock_connection_pool.borrow_connection.assert_called_once_with(
                "test.host.com", 23
            )

    @pytest.mark.asyncio
    async def test_create_printer_session_manager_not_started(self, session_manager):
        """Test session creation when manager is not started."""
        with pytest.raises(RuntimeError, match="Session manager not started"):
            await session_manager.create_printer_session("test.host.com", 23)

    @pytest.mark.asyncio
    async def test_create_printer_session_timeout(
        self, session_manager, mock_connection_pool
    ):
        """Test session creation timeout."""
        session_manager._started = True
        mock_connection_pool.borrow_connection.side_effect = asyncio.TimeoutError()

        with pytest.raises(RuntimeError, match="Failed to create printer session"):
            await session_manager.create_printer_session("test.host.com", 23)

    @pytest.mark.asyncio
    async def test_get_printer_session_active(
        self, session_manager, mock_printer_session
    ):
        """Test getting an active printer session."""
        session_manager._started = True
        session_manager._active_sessions = {"test_session_123": mock_printer_session}

        session = await session_manager.get_printer_session("test_session_123")
        assert session == mock_printer_session

    @pytest.mark.asyncio
    async def test_get_printer_session_inactive(
        self, session_manager, mock_printer_session
    ):
        """Test getting an inactive printer session."""
        session_manager._started = True
        mock_printer_session.is_active = False
        session_manager._active_sessions = {"test_session_123": mock_printer_session}

        with pytest.raises(
            RuntimeError, match="Session test_session_123 is not active"
        ):
            await session_manager.get_printer_session("test_session_123")

    @pytest.mark.asyncio
    async def test_get_printer_session_not_found(self, session_manager):
        """Test getting a non-existent printer session."""
        session_manager._started = True

        with pytest.raises(RuntimeError, match="Session nonexistent not found"):
            await session_manager.get_printer_session("nonexistent")

    @pytest.mark.asyncio
    async def test_send_print_job_success(self, session_manager, mock_printer_session):
        """Test successful print job sending."""
        session_manager._started = True
        session_manager._active_sessions = {"test_session_123": mock_printer_session}

        await session_manager.send_print_job("test_session_123", b"print data")

        mock_printer_session.send_print_data.assert_called_once_with(b"print data")

    @pytest.mark.asyncio
    async def test_send_print_job_session_not_found(self, session_manager):
        """Test print job sending for non-existent session."""
        session_manager._started = True

        with pytest.raises(RuntimeError, match="Session nonexistent not found"):
            await session_manager.send_print_job("nonexistent", b"print data")

    @pytest.mark.asyncio
    async def test_send_print_job_send_error(
        self, session_manager, mock_printer_session
    ):
        """Test print job sending with send error."""
        session_manager._started = True
        session_manager._active_sessions = {"test_session_123": mock_printer_session}
        mock_printer_session.send_print_data.side_effect = Exception("Send failed")

        with pytest.raises(RuntimeError, match="Failed to send print job"):
            await session_manager.send_print_job("test_session_123", b"print data")

    @pytest.mark.asyncio
    async def test_send_printer_status_success(
        self, session_manager, mock_printer_session
    ):
        """Test successful printer status sending."""
        session_manager._started = True
        session_manager._active_sessions = {"test_session_123": mock_printer_session}

        await session_manager.send_printer_status("test_session_123", 0x01)

        mock_printer_session.send_printer_status.assert_called_once_with(0x01)

    @pytest.mark.asyncio
    async def test_send_printer_status_session_not_found(self, session_manager):
        """Test printer status sending for non-existent session."""
        session_manager._started = True

        with pytest.raises(RuntimeError, match="Session nonexistent not found"):
            await session_manager.send_printer_status("nonexistent", 0x01)

    @pytest.mark.asyncio
    async def test_receive_printer_data_success(
        self, session_manager, mock_printer_session
    ):
        """Test successful printer data reception."""
        session_manager._started = True
        session_manager._active_sessions = {"test_session_123": mock_printer_session}

        data = await session_manager.receive_printer_data("test_session_123")

        assert data == b"test data"
        mock_printer_session.receive_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_printer_data_session_not_found(self, session_manager):
        """Test printer data reception for non-existent session."""
        session_manager._started = True

        with pytest.raises(RuntimeError, match="Session nonexistent not found"):
            await session_manager.receive_printer_data("nonexistent")

    @pytest.mark.asyncio
    async def test_close_printer_session_success(
        self, session_manager, mock_connection_pool, mock_printer_session
    ):
        """Test successful printer session closing."""
        session_manager._started = True
        session_manager._active_sessions = {"test_session_123": mock_printer_session}

        await session_manager.close_printer_session("test_session_123")

        assert "test_session_123" not in session_manager._active_sessions
        mock_printer_session.close.assert_called_once()
        mock_connection_pool.return_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_printer_session_not_found(self, session_manager):
        """Test closing a non-existent printer session."""
        session_manager._started = True

        with pytest.raises(RuntimeError, match="Session nonexistent not found"):
            await session_manager.close_printer_session("nonexistent")

    @pytest.mark.asyncio
    async def test_close_all_sessions(self, session_manager, mock_printer_session):
        """Test closing all printer sessions."""
        session_manager._started = True
        session_manager._active_sessions = {
            "session1": mock_printer_session,
            "session2": mock_printer_session,
        }

        await session_manager.close_all_sessions()

        assert session_manager._active_sessions == {}
        assert mock_printer_session.close.call_count == 2

    def test_get_active_sessions(self, session_manager, mock_printer_session):
        """Test getting active sessions list."""
        session_manager._active_sessions = {"test_session_123": mock_printer_session}

        sessions = session_manager.get_active_sessions()
        assert len(sessions) == 1
        assert "test_session_123" in sessions

    def test_get_pool_stats(self, session_manager, mock_connection_pool):
        """Test getting connection pool statistics."""
        session_manager._started = True

        stats = session_manager.get_pool_stats()
        assert stats == {"active": 1, "idle": 0}
        mock_connection_pool.get_pool_stats.assert_called_once()

    def test_get_pool_stats_no_pool(self, session_manager):
        """Test getting pool stats when no pool is available."""
        session_manager._started = True
        session_manager.connection_pool = None

        stats = session_manager.get_pool_stats()
        assert stats == {}

    def test_get_manager_stats(
        self, session_manager, mock_connection_pool, mock_printer_session
    ):
        """Test getting manager statistics."""
        session_manager._started = True
        session_manager._active_sessions = {"test_session_123": mock_printer_session}

        stats = session_manager.get_manager_stats()
        assert stats["started"] is True
        assert stats["active_sessions"] == 1
        assert "pool_stats" in stats

    @pytest.mark.asyncio
    async def test_context_manager(self, session_manager, mock_connection_pool):
        """Test async context manager functionality."""
        async with session_manager:
            assert session_manager._started

        assert not session_manager._started
        mock_connection_pool.start.assert_called_once()
        mock_connection_pool.stop.assert_called_once()
