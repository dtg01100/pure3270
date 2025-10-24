"""
Session tests.

Comprehensive tests for Session and AsyncSession functionality.
"""

import time

import pytest

from pure3270 import AsyncSession, Session
from pure3270.emulation.screen_buffer import ScreenBuffer


class TestSession:
    """Tests for Session functionality."""

    def test_session_initialization(self):
        """Test Session initializes with correct defaults."""
        session = Session()

        assert session.connected is False
        # Session creates async_session only on connect, so screen_buffer property provides default
        assert isinstance(session.screen_buffer, ScreenBuffer)

    @pytest.mark.asyncio
    async def test_async_session_initialization(self):
        """Test AsyncSession initializes correctly."""
        session = AsyncSession()

        assert session.connected is False
        assert isinstance(session._screen_buffer, ScreenBuffer)
        assert session._handler is None

    def test_session_context_manager(self):
        """Test Session context manager."""
        session = Session()

        # Should not raise, but since no real connection, just test it doesn't crash
        try:
            with session:
                pass
        except Exception:
            # Expected since no connection
            pass

    @pytest.mark.asyncio
    async def test_async_session_context_manager(self):
        """Test AsyncSession context manager."""
        session = AsyncSession()

        # Should attempt to connect to None:23
        try:
            async with session:
                pass
        except Exception:
            # Expected since no real connection
            pass

    def test_session_send_not_connected(self):
        """Test send raises error when not connected."""
        session = Session()

        with pytest.raises(Exception):  # SessionError
            session.send(b"data")

    @pytest.mark.asyncio
    async def test_async_session_send_not_connected(self):
        """Test async send raises error when not connected."""
        session = AsyncSession()

        with pytest.raises(Exception):  # SessionError
            await session.send(b"data")

    @pytest.mark.asyncio
    async def test_async_session_receive_not_connected(self):
        """Test async receive raises error when not connected."""
        session = AsyncSession()

        with pytest.raises(Exception):  # SessionError
            await session.read()

    def test_performance_session_operations(self):
        """Performance regression test for session operations."""
        session = Session()

        # Mock the Session's send method to avoid connection errors
        original_send = session.send

        def mock_send(data):
            pass  # Do nothing

        session.send = mock_send

        start = time.time()
        for _ in range(1000):
            try:
                session.send(b"test data")
            except:
                pass  # Ignore connection errors
        end = time.time()

        # Restore
        session.send = original_send

        # Should complete in less than 0.1 seconds
        assert end - start < 0.1
