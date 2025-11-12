"""
Comprehensive Mock Factory and Reusable Components.

Provides factory functions and utilities for creating complex mock scenarios
for integration testing without requiring actual network connections.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.session import AsyncSession
from tests.mocks.auth_flows import (
    MockAuthNegotiator,
    MockAuthScreenGenerator,
    MockAuthSession,
    MockMultiFactorAuth,
    create_mock_auth_negotiator,
    create_mock_auth_screen_generator,
    create_mock_auth_session,
)
from tests.mocks.network_handlers import (
    MockAsyncReader,
    MockAsyncWriter,
    MockConnection,
    MockConnectionManager,
    create_basic_telnet_connection,
    create_error_connection,
    create_interactive_connection,
    create_slow_connection,
    create_tn3270e_connection,
)
from tests.mocks.protocol_responses import (
    MockNegotiationHandler,
    MockProtocolResponseGenerator,
    MockScreenUpdateGenerator,
    create_mock_negotiation_handler,
    create_mock_protocol_responses,
)
from tests.mocks.tn3270_server import (
    MockTN3270Server,
    MockTN3270ServerWithAuth,
    MockTN3270ServerWithScript,
    create_auth_mock_server,
    create_basic_mock_server,
    create_error_mock_server,
    create_scripted_mock_server,
)


class MockScenarioFactory:
    """Factory for creating complex test scenarios with multiple mock components."""

    def __init__(self):
        self.connection_manager = MockConnectionManager()
        self.scenarios = {}

    def create_basic_session_scenario(self) -> Dict[str, Any]:
        """Create a basic session connection scenario."""
        connection = create_basic_telnet_connection()
        self.connection_manager.create_connection("basic", connection)

        negotiation_handler = create_mock_negotiation_handler("standard")
        screen_buffer = ScreenBuffer(rows=24, cols=80)
        screen_generator = MockScreenUpdateGenerator(screen_buffer)

        return {
            "connection": connection,
            "negotiation_handler": negotiation_handler,
            "screen_buffer": screen_buffer,
            "screen_generator": screen_generator,
            "reader": connection.reader,
            "writer": connection.writer,
        }

    def create_authenticated_session_scenario(self) -> Dict[str, Any]:
        """Create an authenticated session scenario."""
        connection = create_tn3270e_connection()
        self.connection_manager.create_connection("auth", connection)

        # Create authentication components
        auth_session = create_mock_auth_session("standard")
        auth_screen_generator = create_mock_auth_screen_generator(
            ScreenBuffer(rows=24, cols=80)
        )
        auth_negotiator = create_mock_auth_negotiator(
            auth_session, auth_screen_generator
        )

        negotiation_handler = create_mock_negotiation_handler("standard")
        screen_buffer = ScreenBuffer(rows=24, cols=80)
        screen_generator = MockScreenUpdateGenerator(screen_buffer)

        return {
            "connection": connection,
            "auth_session": auth_session,
            "auth_negotiator": auth_negotiator,
            "negotiation_handler": negotiation_handler,
            "screen_buffer": screen_buffer,
            "screen_generator": screen_generator,
            "reader": connection.reader,
            "writer": connection.writer,
        }

    def create_error_scenario(
        self, error_type: str = "connection_reset"
    ) -> Dict[str, Any]:
        """Create a scenario that simulates various error conditions."""
        connection = create_error_connection(error_type)
        self.connection_manager.create_connection(f"error_{error_type}", connection)

        return {
            "connection": connection,
            "error_type": error_type,
            "reader": connection.reader,
            "writer": connection.writer,
        }

    def create_scripted_scenario(self, script_responses: List[bytes]) -> Dict[str, Any]:
        """Create a scenario with scripted responses."""
        connection = create_interactive_connection([])
        self.connection_manager.create_connection("scripted", connection)

        mock_server = create_scripted_mock_server(script_responses)
        screen_buffer = ScreenBuffer(rows=24, cols=80)
        screen_generator = MockScreenUpdateGenerator(screen_buffer)

        return {
            "connection": connection,
            "mock_server": mock_server,
            "screen_buffer": screen_buffer,
            "screen_generator": screen_generator,
            "reader": connection.reader,
            "writer": connection.writer,
        }

    def create_mfa_scenario(self) -> Dict[str, Any]:
        """Create a multi-factor authentication scenario."""
        connection = create_tn3270e_connection()
        self.connection_manager.create_connection("mfa", connection)

        # Create MFA components
        primary_session = create_mock_auth_session("standard")
        mfa = MockMultiFactorAuth(
            primary_session=primary_session, otp_secrets={"testuser": "secret123"}
        )

        auth_session = create_mock_auth_session("standard")
        auth_screen_generator = create_mock_auth_screen_generator(
            ScreenBuffer(rows=24, cols=80)
        )
        auth_negotiator = create_mock_auth_negotiator(
            auth_session, auth_screen_generator
        )

        screen_buffer = ScreenBuffer(rows=24, cols=80)
        screen_generator = MockScreenUpdateGenerator(screen_buffer)

        return {
            "connection": connection,
            "mfa": mfa,
            "primary_session": primary_session,
            "auth_session": auth_session,
            "auth_negotiator": auth_negotiator,
            "screen_buffer": screen_buffer,
            "screen_generator": screen_generator,
            "reader": connection.reader,
            "writer": connection.writer,
        }

    def get_connection(self, name: str) -> Optional[MockConnection]:
        """Get a connection by name."""
        return self.connection_manager.get_connection(name)

    def reset_all_connections(self) -> None:
        """Reset all connections."""
        self.connection_manager.reset_all()

    def close_all_connections(self) -> None:
        """Close all connections."""
        self.connection_manager.close_all()


class MockAsyncSessionFactory:
    """Factory for creating AsyncSession instances with mocked dependencies."""

    def __init__(self, scenario_factory: MockScenarioFactory):
        self.scenario_factory = scenario_factory
        self.mocked_sessions = []

    def create_mocked_session(self, scenario: str = "basic", **kwargs) -> AsyncSession:
        """Create an AsyncSession with mocked network I/O."""
        # Prefer any scenario registered by an isolated_test context so that
        # the test's `scenario` object and the session's mocked I/O share
        # the same underlying objects. Fall back to creating a fresh
        # scenario via the scenario factory when none is registered.
        if isolation_manager.active_scenarios:
            scenario_data = isolation_manager.active_scenarios[-1]["data"]
        else:
            if scenario == "basic":
                scenario_data = self.scenario_factory.create_basic_session_scenario()
            elif scenario == "authenticated":
                scenario_data = (
                    self.scenario_factory.create_authenticated_session_scenario()
                )
            elif scenario.startswith("error"):
                error_type = (
                    scenario.split("_", 1)[1] if "_" in scenario else "connection_reset"
                )
                scenario_data = self.scenario_factory.create_error_scenario(error_type)
            elif scenario == "mfa":
                scenario_data = self.scenario_factory.create_mfa_scenario()
            else:
                scenario_data = self.scenario_factory.create_basic_session_scenario()

        # Create AsyncSession with mocked connection
        session = AsyncSession("localhost", 23, **kwargs)

        # If the session constructor didn't create an internal handler (the
        # real code creates the handler during connect()), provide a minimal
        # mock handler that forwards send_data calls to the scenario writer so
        # tests can exercise macro/key flows without performing a real
        # network connect.
        if not getattr(session, "_handler", None):

            class _MinimalHandler:
                def __init__(self, reader, writer, screen_buffer):
                    self.reader = reader
                    self.writer = writer
                    self.screen_buffer = screen_buffer
                    self.connected = True
                    self.negotiated_tn3270e = True

                async def send_data(self, data: bytes) -> None:
                    try:
                        # Writer in mocks exposes write() and get_written_data()
                        if hasattr(self.writer, "write"):
                            res = self.writer.write(data)
                            # writer.write may be a coroutine in mocks - await it
                            if asyncio.iscoroutine(res):
                                await res
                            # Some mock writers provide drain; await if coroutine
                            drain = getattr(self.writer, "drain", None)
                            if asyncio.iscoroutinefunction(drain):
                                await drain()
                    except Exception:
                        pass

                async def close(self) -> None:
                    return None

                async def receive_data(self, timeout: float = 5.0) -> bytes:
                    """Minimal receive_data for mocks: read from the mock reader with a timeout."""
                    try:
                        # Some mock readers expose read(n) or read(); prefer read(4096)
                        read_coro = None
                        try:
                            read_coro = self.reader.read(4096)
                        except TypeError:
                            read_coro = self.reader.read()

                        if asyncio.iscoroutine(read_coro) or hasattr(
                            read_coro, "__await__"
                        ):
                            return await asyncio.wait_for(read_coro, timeout=timeout)
                        # If read returned bytes synchronously
                        return read_coro  # type: ignore[return-value]
                    except asyncio.TimeoutError:
                        return b""
                    except Exception:
                        return b""

            session._handler = _MinimalHandler(
                scenario_data["reader"], scenario_data["writer"], session._screen_buffer
            )
        else:
            # Replace the handler's reader and writer with our mocks
            session._handler.reader = scenario_data["reader"]
            session._handler.writer = scenario_data["writer"]

        # Store the mock session for cleanup
        self.mocked_sessions.append(session)

        return session

    def create_session_with_mocks(
        self,
        scenario_data: Dict[str, Any],
        session_kwargs: Optional[Dict[str, Any]] = None,
    ) -> AsyncSession:
        """Create a session with specific mock data."""
        session_kwargs = session_kwargs or {}
        session = AsyncSession("localhost", 23, **session_kwargs)

        if hasattr(session, "_handler") and session._handler:
            session._handler.reader = scenario_data["reader"]
            session._handler.writer = scenario_data["writer"]

        self.mocked_sessions.append(session)
        return session

    def cleanup_all_sessions(self) -> None:
        """Close and cleanup all mocked sessions."""
        for session in self.mocked_sessions:
            try:
                if hasattr(session, "close"):
                    session.close()
            except Exception:
                pass  # Ignore cleanup errors
        self.mocked_sessions.clear()


class TestIsolationManager:
    """Manages test isolation and cleanup for integration tests."""

    def __init__(self):
        self.active_scenarios = []
        self.global_state = {}
        self.cleanup_hooks = []

    def register_scenario(self, name: str, scenario_data: Dict[str, Any]) -> None:
        """Register a scenario for cleanup."""
        self.active_scenarios.append(
            {"name": name, "data": scenario_data, "cleanup_handles": []}
        )

    def add_cleanup_hook(self, hook_func, *args, **kwargs) -> None:
        """Add a cleanup hook to be called during isolation cleanup."""
        self.cleanup_hooks.append((hook_func, args, kwargs))

    def save_global_state(self, key: str, value: Any) -> None:
        """Save global state that should be restored after test."""
        self.global_state[key] = value

    def restore_global_state(self) -> None:
        """Restore saved global state."""
        # Implementation would restore any modified global state
        self.global_state.clear()

    def cleanup_all_scenarios(self) -> None:
        """Cleanup all registered scenarios and run cleanup hooks."""
        # Run cleanup hooks
        for hook_func, args, kwargs in self.cleanup_hooks:
            try:
                hook_func(*args, **kwargs)
            except Exception as e:
                logging.getLogger(__name__).warning(f"Cleanup hook failed: {e}")

        # Reset connections
        for scenario in self.active_scenarios:
            if "connection" in scenario["data"]:
                try:
                    scenario["data"]["connection"].reset()
                except Exception:
                    pass

        # Clear active scenarios
        self.active_scenarios.clear()
        self.cleanup_hooks.clear()

        # Restore global state
        self.restore_global_state()


# Global instances for use across tests
scenario_factory = MockScenarioFactory()
isolation_manager = TestIsolationManager()


# Convenience factory functions


def create_mock_session(scenario: str = "basic", **kwargs) -> AsyncSession:
    """Create a mocked AsyncSession for testing."""
    factory = MockAsyncSessionFactory(scenario_factory)
    return factory.create_mocked_session(scenario, **kwargs)


def create_mock_connection(scenario: str = "basic") -> MockConnection:
    """Create a mock connection for testing."""
    if scenario == "basic":
        return create_basic_telnet_connection()
    elif scenario == "tn3270e":
        return create_tn3270e_connection()
    elif scenario == "slow":
        return create_slow_connection()
    elif scenario.startswith("error"):
        error_type = (
            scenario.split("_", 1)[1] if "_" in scenario else "connection_reset"
        )
        return create_error_connection(error_type)
    else:
        return create_basic_telnet_connection()


def create_test_scenario(scenario_type: str) -> Dict[str, Any]:
    """Create a complete test scenario."""
    return scenario_factory.create_basic_session_scenario()


# Context managers for test isolation


class IsolatedTestContext:
    """Context manager for test isolation."""

    def __init__(self, scenario_name: str, scenario_data: Dict[str, Any]):
        self.scenario_name = scenario_name
        self.scenario_data = scenario_data
        self.isolation_manager = isolation_manager

    async def __aenter__(self):
        self.isolation_manager.register_scenario(self.scenario_name, self.scenario_data)
        return self.scenario_data

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.isolation_manager.cleanup_all_scenarios()
        return False


def isolated_test(scenario_name: str, scenario_data: Dict[str, Any]):
    """Decorator for test isolation."""

    def decorator(test_func):
        async def wrapper(*args, **kwargs):
            # If the caller provided an empty scenario_data, generate a
            # default basic session scenario from the global factory so
            # tests receive a populated scenario with reader/writer, etc.
            effective_scenario = (
                scenario_data
                if scenario_data
                else scenario_factory.create_basic_session_scenario()
            )
            async with IsolatedTestContext(
                scenario_name, effective_scenario
            ) as scenario:
                if asyncio.iscoroutinefunction(test_func):
                    return await test_func(*args, scenario, **kwargs)
                else:
                    return test_func(*args, scenario, **kwargs)

        return wrapper

    return decorator
