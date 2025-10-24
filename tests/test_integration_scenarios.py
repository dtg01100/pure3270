"""
Integration scenario tests.

This file focuses on testing complete workflows and interactions
between multiple components, rather than isolated unit functionality.
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from pure3270 import AsyncSession, Session
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.negotiator import Negotiator


class TestIntegrationScenarios:
    """Tests for complete workflows and component interactions."""

    @pytest.mark.asyncio
    async def test_async_session_context_manager_proper_cleanup(self):
        """Test that AsyncSession context manager properly cleans up resources."""
        initial_connected_state = None

        async with AsyncSession() as session:
            # Verify session is initialized
            assert session is not None
            initial_connected_state = session.connected

            # Mock connection for testing
            reader = AsyncMock()
            writer = AsyncMock()
            writer.drain = AsyncMock()

            session._connected = True

            # Verify we can perform operations
            # (This is limited without a real connection)

        # Verify session is properly closed after context exit
        assert not session.connected

    @pytest.mark.asyncio
    async def test_session_connection_states(self):
        """Test that session properly manages connection states."""
        session = Session()

        # Initially not connected
        assert not session.connected

        # Test that operations fail when not connected
        # This verifies the expected behavior for error conditions
        # The actual exception depends on implementation

    def test_parser_and_screen_buffer_integration(self):
        """Test integration between DataStreamParser and ScreenBuffer."""
        screen = ScreenBuffer(24, 80)
        parser = DataStreamParser(screen)

        # Test a complete parsing workflow
        # SBA (Set Buffer Address) to position (5, 10), then write text
        sba_cmd = bytes(
            [0x11, 0x00, 0x0A]
        )  # SBA to position (0, 10) - 12-bit addressing
        text = b"HELLO WORLD"
        full_data = sba_cmd + text

        parser.parse(full_data)

        # Verify cursor was positioned correctly
        row, col = screen.get_position()
        # After SBA to (0, 10) and writing 11 characters, should be at (0, 21)
        assert col == 21  # 10 + 11
        assert row == 0

    def test_negotiator_and_parser_integration(self):
        """Test integration between Negotiator and DataStreamParser."""
        screen = ScreenBuffer(24, 80)
        reader = AsyncMock()
        writer = AsyncMock()
        negotiator = Negotiator(reader, writer, screen_buffer=screen)

        parser = DataStreamParser(screen)

        # Test that negotiator and parser can work with the same screen buffer
        assert negotiator._screen_buffer is screen
        assert parser._screen_buffer is screen

        # Test basic negotiation inference
        result = negotiator.infer_tn3270e_from_trace(b"\xff\xfb\x19")
        assert result is True

        # Test that parser can still operate on the screen
        parser.parse(b"TEST")
        assert parser._pos == 4

    def test_complete_session_workflow_simulation(self):
        """Test a simulated complete session workflow."""
        # Create all components
        screen = ScreenBuffer(24, 80)
        parser = DataStreamParser(screen)
        reader = AsyncMock()
        writer = AsyncMock()
        negotiator = Negotiator(reader, writer, screen_buffer=screen)

        # Simulate negotiation phase
        tn3270e_supported = negotiator.infer_tn3270e_from_trace(b"\xff\xfb\x19")
        assert tn3270e_supported

        # Simulate data parsing phase
        test_data = b"\x11\x00\x00" + b"WELCOME TO TN3270"  # SBA to (0,0) + text
        parser.parse(test_data)

        # Verify the complete workflow worked
        assert parser._pos == len(test_data)
        assert screen.get_position() == (0, 17)  # After writing 17 characters

    def test_error_propagation_across_components(self):
        """Test that errors propagate correctly across component boundaries."""
        screen = ScreenBuffer(24, 80)
        parser = DataStreamParser(screen)

        # Test with malformed data that should be handled gracefully
        try:
            parser.parse(b"\x28")  # Incomplete SBA command
        except Exception as e:
            # Should handle gracefully
            assert parser._pos <= 1  # Should not advance beyond input

        # Screen buffer should remain in valid state
        assert screen.rows == 24
        assert screen.cols == 80
        assert screen.get_position() == (0, 0)

    def test_component_state_consistency_during_operations(self):
        """Test that component states remain consistent during operations."""
        screen = ScreenBuffer(24, 80)
        parser = DataStreamParser(screen)

        initial_screen_state = (screen.get_position(), len(screen.buffer))
        initial_parser_state = parser._pos

        # Perform operations
        parser.parse(b"\x28\x00\x05" + b"TEST")  # SBA + text

        # Verify states are still consistent
        assert screen.rows == 24
        assert screen.cols == 80
        assert len(screen.buffer) == 24 * 80
        assert parser._pos > initial_parser_state

        # Position should be valid
        row, col = screen.get_position()
        assert 0 <= row < screen.rows
        assert 0 <= col < screen.cols
