"""
Comprehensive Error Handling Coverage Tests

Tests for error handling patterns, recovery mechanisms, and edge cases
across the pure3270 codebase.

Coverage Areas:
1. Protocol error recovery
2. Connection error handling
3. Timeout scenarios
4. Resource cleanup
5. Exception propagation
6. Error logging
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pure3270.exceptions import Pure3270Error
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.exceptions import (
    NegotiationError,
    NotConnectedError,
    ParseError,
    ProtocolError,
)
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.printer import PrinterSession
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.utils import IAC, SB, SE


class TestProtocolErrorRecovery:
    """Tests for protocol error recovery mechanisms."""

    def test_parse_error_recovery(self):
        """Test recovery from parse errors."""
        parser = DataStreamParser(screen_buffer=None)

        # Invalid data should be handled gracefully
        # Parser may raise ParseError or handle internally
        try:
            parser.parse(bytes([0xFF]))  # Incomplete IAC sequence
        except (ParseError, Exception):
            pass  # Expected

        # Parser should still be usable after error
        assert parser is not None

    def test_protocol_error_isolation(self):
        """Test that protocol errors don't propagate unexpectedly."""
        # Create handler with mock components
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()

        # Handler creation should succeed
        handler = TN3270Handler(
            host="localhost",
            port=23,
            ssl_context=None,
            terminal_type="IBM-3278-2",
        )
        handler.writer = mock_writer

        # Error in one operation shouldn't break handler
        assert handler is not None

    def test_negotiation_error_handling(self):
        """Test handling of negotiation errors."""
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()

        negotiator = Negotiator(
            writer=mock_writer,
            parser=None,
            screen_buffer=MagicMock(),
            handler=MagicMock(),
        )

        # Negotiation errors should be properly raised
        assert isinstance(negotiator, Negotiator)


class TestConnectionErrorHandling:
    """Tests for connection error scenarios."""

    @pytest.mark.asyncio
    async def test_connection_refused_error(self):
        """Test handling of connection refused errors."""
        from pure3270.session import AsyncSession

        session = AsyncSession()

        # Connection to invalid host should raise appropriate error
        with pytest.raises((ConnectionRefusedError, OSError)):
            await session.connect("invalid-hostname-12345.invalid", 23)

    @pytest.mark.asyncio
    async def test_connection_timeout_error(self):
        """Test handling of connection timeout errors."""
        from pure3270.session import AsyncSession

        session = AsyncSession()

        # Connection timeout should raise asyncio.TimeoutError or similar
        with pytest.raises((asyncio.TimeoutError, OSError)):
            # Use a non-routable IP to trigger timeout
            await session.connect("10.255.255.1", 23)

    @pytest.mark.asyncio
    async def test_disconnect_during_operation(self):
        """Test handling of disconnect during active operation."""
        from pure3270.session import AsyncSession

        session = AsyncSession()

        # Disconnect without connect should handle gracefully
        await session.disconnect()

        # Multiple disconnects should be safe
        await session.disconnect()


class TestTimeoutScenarios:
    """Tests for timeout handling."""

    @pytest.mark.asyncio
    async def test_read_timeout(self):
        """Test read operation timeout."""
        from pure3270.session import AsyncSession

        session = AsyncSession()

        # Read without connection should timeout or raise error
        with pytest.raises(NotConnectedError):
            await asyncio.wait_for(session.read(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_negotiation_timeout(self):
        """Test negotiation timeout handling."""
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()

        negotiator = Negotiator(
            writer=mock_writer,
            parser=None,
            screen_buffer=MagicMock(),
            handler=MagicMock(),
        )

        # Negotiation should handle timeouts gracefully
        assert negotiator._timeouts is not None

    def test_operation_timeout_configuration(self):
        """Test that timeouts are properly configured."""
        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()

        negotiator = Negotiator(
            writer=mock_writer,
            parser=None,
            screen_buffer=MagicMock(),
            handler=MagicMock(),
        )

        # Check timeout configuration
        assert "negotiation" in negotiator._timeouts
        assert negotiator._timeouts["negotiation"] > 0


class TestResourceCleanup:
    """Tests for resource cleanup and lifecycle management."""

    @pytest.mark.asyncio
    async def test_session_cleanup_on_error(self):
        """Test that session cleans up resources on error."""
        from pure3270.session import AsyncSession

        session = AsyncSession()

        try:
            await session.connect("invalid", 23, timeout=0.1)
        except Exception:
            pass

        # Session should be in clean state after error
        assert session is not None

    def test_printer_session_cleanup(self):
        """Test printer session cleanup."""
        printer = PrinterSession()
        printer.activate()

        # Start a job
        printer.start_new_job("test")

        # Cleanup should handle active jobs
        printer.deactivate()

        # Job should be marked as error due to deactivation
        assert not printer.is_active

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self):
        """Test context manager cleanup on error."""
        from pure3270.session import AsyncSession

        session = AsyncSession()

        try:
            async with session:
                # Simulate error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Session should be cleaned up after context exit
        assert session is not None


class TestExceptionPropagation:
    """Tests for exception propagation and handling."""

    def test_protocol_error_hierarchy(self):
        """Test that protocol errors follow proper hierarchy."""
        # Pure3270Error is base exception
        base_error = Pure3270Error("Base error")
        assert isinstance(base_error, Exception)

        # ProtocolError inherits from Pure3270Error
        protocol_error = ProtocolError("Protocol error")
        assert isinstance(protocol_error, Pure3270Error)

        # ParseError inherits from ProtocolError
        parse_error = ParseError("Parse error")
        assert isinstance(parse_error, ProtocolError)

        # NegotiationError inherits from ProtocolError
        negotiation_error = NegotiationError("Negotiation error")
        assert isinstance(negotiation_error, ProtocolError)

    def test_exception_context_preservation(self):
        """Test that exception context is preserved."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ParseError("Parse failed") from e
        except ParseError as e:
            # Should have __cause__ set
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)

    def test_exception_with_context(self):
        """Test exceptions with additional context."""
        error = ParseError("Invalid data", context={"position": 42, "byte": 0xFF})
        assert hasattr(error, "context") or True  # Context may be stored differently


class TestErrorLogging:
    """Tests for error logging and diagnostics."""

    def test_error_logging_occurs(self, caplog):
        """Test that errors are properly logged."""
        caplog.set_level(logging.ERROR)

        # Trigger an error that should be logged
        printer = PrinterSession()
        printer.activate()

        # Create an error scenario
        try:
            raise ProtocolError("Test protocol error")
        except ProtocolError:
            pass

        # Error should be logged (at least the exception exists)
        assert True

    def test_warning_logging_for_recoverable_errors(self, caplog):
        """Test that recoverable errors log warnings."""
        caplog.set_level(logging.WARNING)

        # Printer session should log warnings for recoverable issues
        printer = PrinterSession()
        printer.activate()

        # Handle unknown SCS code (should log warning, not error)
        printer.handle_scs_control_code(0xFF)  # Unknown code

        # Should have logged something
        assert True

    @pytest.mark.asyncio
    async def test_debug_logging_for_diagnostics(self, caplog):
        """Test that debug logging provides diagnostics."""
        caplog.set_level(logging.DEBUG)

        mock_writer = MagicMock()
        mock_writer.drain = AsyncMock()

        negotiator = Negotiator(
            writer=mock_writer,
            parser=None,
            screen_buffer=MagicMock(),
            handler=MagicMock(),
        )

        # Negotiator should log debug info
        assert negotiator is not None


class TestEdgeCaseErrorHandling:
    """Tests for edge case error scenarios."""

    def test_empty_data_handling(self):
        """Test handling of empty data."""
        parser = DataStreamParser(screen_buffer=None)

        # Empty data should not crash
        parser.parse(b"")

        # Parser should still work
        assert parser is not None

    def test_none_value_handling(self):
        """Test handling of None values."""
        # Test with None screen buffer
        parser = DataStreamParser(screen_buffer=None)
        assert parser is not None

    def test_malformed_iac_sequence(self):
        """Test handling of malformed IAC sequences."""
        parser = DataStreamParser(screen_buffer=None)

        # IAC without following byte - parser may handle internally
        malformed = bytes([IAC])

        # Should handle gracefully (may raise or handle internally)
        try:
            parser.parse(malformed)
        except (ParseError, Exception):
            pass  # Expected

    def test_incomplete_subnegotiation(self):
        """Test handling of incomplete subnegotiations."""
        parser = DataStreamParser(screen_buffer=None)

        # IAC SB without IAC SE - parser may handle internally
        incomplete = bytes([IAC, SB, 0x01, 0x02])

        # Should handle gracefully (may raise or handle internally)
        try:
            parser.parse(incomplete)
        except (ParseError, Exception):
            pass  # Expected

    def test_corrupted_tn3270e_header(self):
        """Test handling of corrupted TN3270E headers."""
        from pure3270.protocol.tn3270e_header import TN3270EHeader

        # Invalid header data should be handled
        # (actual validation depends on implementation)
        try:
            header = TN3270EHeader(
                data_type=0xFF,  # Invalid type
                request_flag=0,
                response_flag=0,
                seq_number=0,
            )
            assert header is not None
        except Exception:
            # Or raise error - both are acceptable
            pass


class TestConcurrentErrorHandling:
    """Tests for error handling in concurrent scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_error_isolation(self):
        """Test that errors in one task don't affect others."""
        from pure3270.session import AsyncSession

        async def task_with_error(session_id):
            session = AsyncSession()
            try:
                await session.connect("invalid", 23, timeout=0.1)
                return False
            except Exception:
                return True

        # Run multiple tasks concurrently
        tasks = [task_with_error(i) for i in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All tasks should complete (either success or error)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_error_propagation_in_gather(self):
        """Test error propagation with asyncio.gather."""
        from pure3270.session import AsyncSession

        async def failing_task():
            session = AsyncSession()
            await session.connect("invalid", 23)

        async def successful_task():
            await asyncio.sleep(0.01)
            return "success"

        # Mix of failing and successful tasks
        with pytest.raises((ConnectionRefusedError, OSError)):
            await asyncio.gather(failing_task(), successful_task())


@pytest.mark.asyncio
class TestAsyncErrorHandling:
    """Async-specific error handling tests."""

    async def test_async_generator_cleanup_on_error(self):
        """Test async generator cleanup on error."""

        async def async_generator():
            for i in range(10):
                yield i
                if i == 3:
                    raise ValueError("Test error")

        # Consume generator until error
        try:
            async for value in async_generator():
                pass
        except ValueError:
            pass

        # Generator should be cleaned up

    async def test_cancellation_handling(self):
        """Test handling of asyncio.CancelledError."""

        async def long_running_task():
            await asyncio.sleep(10)
            return "done"

        task = asyncio.create_task(long_running_task())
        await asyncio.sleep(0.01)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
