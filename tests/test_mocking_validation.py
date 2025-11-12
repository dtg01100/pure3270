"""
Validation test for the new mocking infrastructure.

This test verifies that all the mock components work correctly
without requiring complex session setup.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from tests.mocks.auth_flows import (
    MockAuthSession,
    create_mock_auth_screen_generator,
    create_mock_auth_session,
)
from tests.mocks.factory import (
    MockAsyncSessionFactory,
    MockScenarioFactory,
    scenario_factory,
)
from tests.mocks.network_handlers import (
    MockAsyncReader,
    MockAsyncWriter,
    MockConnection,
    create_basic_telnet_connection,
    create_tn3270e_connection,
)
from tests.mocks.protocol_responses import (
    MockNegotiationHandler,
    MockProtocolResponseGenerator,
    create_mock_negotiation_handler,
    create_mock_protocol_responses,
)
from tests.mocks.tn3270_server import (
    MockTN3270Server,
    create_auth_mock_server,
    create_basic_mock_server,
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestMockingInfrastructure:

    async def test_mock_connection_basic(self):
        """Test basic mock connection functionality."""
        # Test basic telnet connection
        connection = create_basic_telnet_connection()
        assert connection is not None
        assert connection.reader is not None
        assert connection.writer is not None
        assert connection.connected

        # Test connection reset
        connection.reset()
        assert connection.connected

        # Test connection close
        connection.close()
        assert not connection.connected

    async def test_mock_reader_writer(self):
        """Test mock reader and writer operations."""
        # Test reader with responses
        reader = MockAsyncReader([b"test data", b"more data"])

        # Read first response
        data1 = await reader.read(9)
        assert data1 == b"test data"

        # Read second response
        data2 = await reader.read(9)
        assert data2 == b"more data"

        # Test readexactly
        reader2 = MockAsyncReader([b"exact"])
        data_exact = await reader2.readexactly(5)
        assert data_exact == b"exact"

        # Test writer
        writer = MockAsyncWriter()
        await writer.write(b"test write")
        await writer.drain()

        written_data = writer.get_written_data()
        assert b"test write" in written_data

    async def test_mock_negotiation_handler(self):
        """Test mock negotiation handler."""
        # Create test connection
        connection = create_basic_telnet_connection()

        # Create negotiation handler
        handler = create_mock_negotiation_handler("standard")
        assert handler is not None
        assert handler.enable_tn3270e

        # Test negotiation sequence tracking
        sequence = handler.get_negotiation_sequence()
        assert isinstance(sequence, list)

        # Test reset
        handler.reset_negotiation()
        sequence_after_reset = handler.get_negotiation_sequence()
        assert len(sequence_after_reset) == 0

    async def test_mock_auth_session(self):
        """Test mock authentication session."""
        # Create auth session
        auth_session = create_mock_auth_session("standard")
        assert auth_session is not None

        # Test successful authentication
        result = await auth_session.authenticate("testuser", "testpass")
        assert result["authenticated"] is True
        assert "session_id" in result
        assert result["username"] == "testuser"

        # Test invalid authentication
        invalid_result = await auth_session.authenticate("invalid", "wrong")
        assert invalid_result["authenticated"] is False

        # Test session validation
        session_id = result["session_id"]
        validation = auth_session.validate_session(session_id)
        assert validation["valid"] is True
        assert validation["username"] == "testuser"

        # Test timeout scenario
        timeout_session = create_mock_auth_session("timeout")
        temp_result = await timeout_session.authenticate("timeoutuser", "timeoutpass")
        assert temp_result["authenticated"] is True

        # Simulate timeout by manually setting session to expired state
        session_id = temp_result["session_id"]
        # Force the session to appear expired by manipulating the timestamp
        if session_id in timeout_session.authenticated_sessions:
            timeout_session.authenticated_sessions[session_id]["created"] = 0
            timeout_session.authenticated_sessions[session_id]["last_access"] = 0

        validation = timeout_session.validate_session(session_id)
        assert validation["valid"] is False

    async def test_mock_protocol_responses(self):
        """Test mock protocol response generation."""
        # Test standard responses
        responses = create_mock_protocol_responses("standard")
        assert len(responses) > 0
        assert all(isinstance(r, bytes) for r in responses)

        # Test fallback responses
        fallback_responses = create_mock_protocol_responses("fallback")
        assert len(fallback_responses) > 0

        # Test error responses
        error_responses = create_mock_protocol_responses("error")
        assert len(error_responses) > 0

    async def test_mock_screen_buffer_generator(self):
        """Test mock screen buffer update generator."""
        # Create screen buffer
        screen_buffer = ScreenBuffer(rows=24, cols=80)

        # Create generator
        from tests.mocks.protocol_responses import MockScreenUpdateGenerator

        generator = MockScreenUpdateGenerator(screen_buffer)

        # Test empty screen update
        empty_screen = generator.create_empty_screen_update()
        assert len(empty_screen) > 0
        assert empty_screen.startswith(b"\x00\x00\x00\x00")

        # Test text screen update
        text_screen = generator.create_text_screen_update("TEST")
        assert len(text_screen) > 0

        # Test cursor position update
        cursor_screen = generator.create_cursor_position_update(5, 10)
        assert len(cursor_screen) > 0

    async def test_scenario_factory(self):
        """Test scenario factory functionality."""
        # Test basic session scenario
        basic_scenario = scenario_factory.create_basic_session_scenario()
        assert "connection" in basic_scenario
        assert "screen_buffer" in basic_scenario
        assert basic_scenario["connection"] is not None

        # Test authenticated session scenario
        auth_scenario = scenario_factory.create_authenticated_session_scenario()
        assert "auth_session" in auth_scenario
        assert "auth_negotiator" in auth_scenario

        # Test error scenario
        error_scenario = scenario_factory.create_error_scenario("connection_reset")
        assert "connection" in error_scenario
        assert error_scenario["error_type"] == "connection_reset"

    async def test_mock_tn3270_server(self):
        """Test mock TN3270 server functionality."""
        # Test basic server
        server = create_basic_mock_server()
        assert server is not None
        assert server.model == "IBM-3278-2"

        # Test auth server
        auth_server = create_auth_mock_server("testuser", "testpass")
        assert auth_server is not None
        assert auth_server.username == "testuser"
        assert auth_server.password == "testpass"

    async def test_mock_connection_manager(self):
        """Test mock connection manager."""
        from tests.mocks.network_handlers import MockConnectionManager

        manager = MockConnectionManager()

        # Test creating and retrieving connections
        connection1 = create_basic_telnet_connection()
        manager.create_connection("test1", connection1)

        retrieved = manager.get_connection("test1")
        assert retrieved is connection1

        # Test creating new connections
        new_connection = manager.create_new_connection("basic")
        assert new_connection is not None

        # Test reset all
        manager.reset_all()
        # Reset should work without errors

    async def test_factory_functions(self):
        """Test factory functions from factory module."""
        from tests.mocks.factory import (
            create_mock_connection,
            create_mock_session,
            create_test_scenario,
        )

        # Test create_mock_session
        session = create_mock_session("basic")
        assert session is not None

        # Test create_mock_connection
        connection = create_mock_connection("basic")
        assert connection is not None

        # Test create_test_scenario
        scenario = create_test_scenario("basic")
        assert scenario is not None
        assert "connection" in scenario
