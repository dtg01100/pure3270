#!/usr/bin/env python3
"""
Comprehensive unit tests for printer_error_recovery.py

Tests circuit breaker patterns, error recovery mechanisms, retry logic,
timeout handling, and various error conditions for printer operations.
"""

import asyncio
import time
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from pure3270.protocol.printer_error_recovery import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerState,
    PrinterErrorRecovery,
    RecoveryManager,
    RecoveryPolicy,
)
from pure3270.protocol.printer_status_reporter import (
    PrinterStatus,
    PrinterStatusReporter,
)

# No module-level async marking - individual test functions handle their own async/sync nature


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig class."""

    def test_default_initialization(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.success_threshold == 3
        assert config.monitoring_window == 300.0
        assert config.half_open_max_calls == 3

    def test_custom_initialization(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=120.0,
            success_threshold=5,
            monitoring_window=600.0,
            half_open_max_calls=5,
        )
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 120.0
        assert config.success_threshold == 5
        assert config.monitoring_window == 600.0
        assert config.half_open_max_calls == 5


class TestCircuitBreaker:
    """Test CircuitBreaker class functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
            success_threshold=2,
            half_open_max_calls=2,
        )

    @pytest.fixture
    def status_reporter(self):
        """Create mock status reporter."""
        return AsyncMock(spec=PrinterStatusReporter)

    @pytest_asyncio.fixture
    async def circuit_breaker(self, config, status_reporter):
        """Create circuit breaker instance."""
        cb = CircuitBreaker("test_circuit", config, status_reporter)
        yield cb
        # Cleanup any pending tasks
        await asyncio.sleep(0)

    @pytest.mark.asyncio
    async def test_initial_state_closed(self, circuit_breaker):
        """Test circuit breaker starts in CLOSED state."""
        assert circuit_breaker.get_state() == CircuitBreakerState.CLOSED
        metrics = circuit_breaker.get_metrics()
        assert metrics["state"] == "closed"
        assert metrics["failure_count"] == 0
        assert metrics["success_count"] == 0

    @pytest.mark.asyncio
    async def test_successful_call(self, circuit_breaker):
        """Test successful function call."""

        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.get_state() == CircuitBreakerState.CLOSED

        metrics = circuit_breaker.get_metrics()
        assert metrics["total_calls"] == 1
        assert metrics["total_successes"] == 1
        assert metrics["total_failures"] == 0

    @pytest.mark.asyncio
    async def test_failed_call_opens_circuit(self, circuit_breaker):
        """Test failed calls eventually open the circuit."""

        async def fail_func():
            raise ValueError("Test failure")

        # First failure
        with pytest.raises(ValueError):
            await circuit_breaker.call(fail_func)
        assert circuit_breaker.get_state() == CircuitBreakerState.CLOSED

        # Second failure
        with pytest.raises(ValueError):
            await circuit_breaker.call(fail_func)
        assert circuit_breaker.get_state() == CircuitBreakerState.CLOSED

        # Third failure - should open circuit
        with pytest.raises(ValueError):
            await circuit_breaker.call(fail_func)
        assert circuit_breaker.get_state() == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_blocks_calls(self, circuit_breaker):
        """Test open circuit blocks calls without fallback."""
        # Force circuit open
        await circuit_breaker.force_open("Test open")

        async def success_func():
            return "success"

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await circuit_breaker.call(success_func)

        assert "test_circuit" in str(exc_info.value)
        assert exc_info.value.circuit_name == "test_circuit"

    @pytest.mark.asyncio
    async def test_open_circuit_uses_fallback(self, circuit_breaker):
        """Test open circuit uses fallback function."""
        await circuit_breaker.force_open("Test open")

        async def fallback_func():
            return "fallback_result"

        result = await circuit_breaker.call(lambda: None, fallback_func)
        assert result == "fallback_result"

    @pytest.mark.asyncio
    async def test_half_open_recovery_attempt(self, circuit_breaker):
        """Test half-open state allows limited calls for recovery."""
        # Open the circuit
        await circuit_breaker.force_open("Test open")
        assert circuit_breaker.get_state() == CircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        async def success_func():
            return "recovered"

        # First call in half-open should succeed but stay in half-open until success threshold
        result = await circuit_breaker.call(success_func)
        assert result == "recovered"
        # With success_threshold=2, it should still be half-open after first success
        assert circuit_breaker.get_state() == CircuitBreakerState.HALF_OPEN

        # Second success should close the circuit
        result = await circuit_breaker.call(success_func)
        assert result == "recovered"
        assert circuit_breaker.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_returns_to_open(self, circuit_breaker):
        """Test half-open failure returns circuit to open state."""
        await circuit_breaker.force_open("Test open")
        await asyncio.sleep(1.1)  # Wait for recovery

        async def fail_func():
            raise RuntimeError("Still failing")

        with pytest.raises(RuntimeError):
            await circuit_breaker.call(fail_func)

        assert circuit_breaker.get_state() == CircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_call_limit(self, circuit_breaker):
        """Test half-open state limits concurrent calls."""
        await circuit_breaker.force_open("Test open")
        await asyncio.sleep(1.1)

        # Use up all half-open calls
        async def slow_func():
            await asyncio.sleep(0.5)
            return "success"

        # Start multiple calls
        tasks = []
        for _ in range(3):  # More than half_open_max_calls (2)
            task = asyncio.create_task(circuit_breaker.call(slow_func))
            tasks.append(task)

        # First two should proceed, third should fail
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r == "success")
        exception_count = sum(
            1 for r in results if isinstance(r, CircuitBreakerOpenError)
        )

        assert success_count == 2
        assert exception_count == 1

    @pytest.mark.asyncio
    async def test_reset_functionality(self, circuit_breaker):
        """Test circuit breaker reset."""

        # Cause some failures
        async def fail_func():
            raise ValueError("fail")

        for _ in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(fail_func)

        assert circuit_breaker.get_state() == CircuitBreakerState.OPEN

        # Reset
        circuit_breaker.reset()
        assert circuit_breaker.get_state() == CircuitBreakerState.CLOSED

        metrics = circuit_breaker.get_metrics()
        assert metrics["failure_count"] == 0
        assert metrics["success_count"] == 0
        assert metrics["total_calls"] == 0

    @pytest.mark.asyncio
    async def test_force_open_functionality(self, circuit_breaker):
        """Test force open functionality."""
        assert circuit_breaker.get_state() == CircuitBreakerState.CLOSED

        await circuit_breaker.force_open("Manual override")
        assert circuit_breaker.get_state() == CircuitBreakerState.OPEN

        # Verify last failure time is set
        metrics = circuit_breaker.get_metrics()
        assert metrics["last_failure_time"] is not None

    @pytest.mark.asyncio
    async def test_status_reporter_notifications(
        self, circuit_breaker, status_reporter
    ):
        """Test status reporter is notified of state changes."""
        # Open circuit
        await circuit_breaker.force_open("Test")
        status_reporter.update_status.assert_called()

        # Reset to test close notification
        circuit_breaker.reset()
        await asyncio.sleep(1.1)  # Wait for recovery

        async def success_func():
            return "ok"

        await circuit_breaker.call(success_func)
        # Should have called update_status for state changes

    @pytest.mark.asyncio
    async def test_sync_fallback_function(self, circuit_breaker):
        """Test synchronous fallback function."""
        await circuit_breaker.force_open("Test")

        def sync_fallback():
            return "sync_result"

        result = await circuit_breaker.call(lambda: None, sync_fallback)
        assert result == "sync_result"

    @pytest.mark.asyncio
    async def test_fallback_exception_handling(self, circuit_breaker):
        """Test fallback function exceptions are propagated."""
        await circuit_breaker.force_open("Test")

        async def bad_fallback():
            raise ConnectionError("Fallback failed")

        with pytest.raises(ConnectionError):
            await circuit_breaker.call(lambda: None, bad_fallback)


class TestRecoveryManager:
    """Test RecoveryManager class functionality."""

    @pytest.fixture
    def status_reporter(self):
        """Create mock status reporter."""
        return AsyncMock(spec=PrinterStatusReporter)

    @pytest_asyncio.fixture
    async def recovery_manager(self, status_reporter):
        """Create recovery manager instance."""
        manager = RecoveryManager(status_reporter)
        yield manager

    @pytest.mark.asyncio
    async def test_add_circuit_breaker(self, recovery_manager):
        """Test adding circuit breakers."""
        config = CircuitBreakerConfig()
        cb = recovery_manager.add_circuit_breaker("test_cb", config)

        assert isinstance(cb, CircuitBreaker)
        assert cb.name == "test_cb"
        assert recovery_manager.get_circuit_breaker("test_cb") is cb

    @pytest.mark.asyncio
    async def test_add_duplicate_circuit_breaker_fails(self, recovery_manager):
        """Test adding duplicate circuit breaker names fails."""
        config = CircuitBreakerConfig()
        recovery_manager.add_circuit_breaker("duplicate", config)

        with pytest.raises(ValueError, match="already exists"):
            recovery_manager.add_circuit_breaker("duplicate", config)

    @pytest.mark.asyncio
    async def test_add_recovery_policy(self, recovery_manager):
        """Test adding recovery policies."""
        recovery_manager.add_recovery_policy(
            "test_op", RecoveryPolicy.EXPONENTIAL_BACKOFF
        )

        stats = recovery_manager.get_recovery_stats()
        assert "test_op" in stats["recovery_policies"]
        assert (
            stats["recovery_policies"]["test_op"] == RecoveryPolicy.EXPONENTIAL_BACKOFF
        )

    @pytest.mark.asyncio
    async def test_custom_recovery_policy(self, recovery_manager):
        """Test custom recovery policy."""

        async def custom_recovery():
            await asyncio.sleep(0.1)

        recovery_manager.add_recovery_policy(
            "custom_op", RecoveryPolicy.CUSTOM, custom_recovery
        )

        stats = recovery_manager.get_recovery_stats()
        assert stats["recovery_policies"]["custom_op"] == RecoveryPolicy.CUSTOM

    @pytest.mark.asyncio
    async def test_custom_policy_requires_function(self, recovery_manager):
        """Test custom policy requires custom function."""
        with pytest.raises(ValueError, match="requires a custom function"):
            recovery_manager.add_recovery_policy("custom_op", RecoveryPolicy.CUSTOM)

    @pytest.mark.asyncio
    async def test_execute_with_recovery_success(self, recovery_manager):
        """Test successful execution with recovery."""

        async def success_func():
            return "success"

        result = await recovery_manager.execute_with_recovery("test_op", success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_recovery_failure(self, recovery_manager):
        """Test failed execution with recovery attempts."""
        call_count = 0

        async def fail_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError(f"Attempt {call_count}")

        with pytest.raises(ConnectionError, match="Attempt 3"):
            await recovery_manager.execute_with_recovery(
                "test_op", fail_func, max_attempts=3
            )

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_circuit_breaker(self, recovery_manager):
        """Test execution with circuit breaker protection."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0)
        cb = recovery_manager.add_circuit_breaker("test_cb", config)

        call_count = 0

        async def fail_func():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Connection timeout")

        # Fail enough times to open circuit
        for _ in range(2):
            try:
                await recovery_manager.execute_with_recovery(
                    "test_op", fail_func, "test_cb", max_attempts=1
                )
            except (TimeoutError, CircuitBreakerOpenError):
                pass  # Expected

        assert cb.get_state() == CircuitBreakerState.OPEN

        # Next call should use circuit breaker fallback behavior
        with pytest.raises(CircuitBreakerOpenError):
            await recovery_manager.execute_with_recovery(
                "test_op", fail_func, "test_cb", max_attempts=1
            )

    @pytest.mark.asyncio
    async def test_recovery_policy_immediate(self, recovery_manager):
        """Test immediate recovery policy (no delay)."""
        recovery_manager.add_recovery_policy("immediate_op", RecoveryPolicy.IMMEDIATE)

        start_time = time.time()

        async def fail_func():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await recovery_manager.execute_with_recovery(
                "immediate_op", fail_func, max_attempts=2
            )

        elapsed = time.time() - start_time
        # Should be very fast (no delays)
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_recovery_policy_linear_backoff(self, recovery_manager):
        """Test linear backoff recovery policy."""
        recovery_manager.add_recovery_policy("linear_op", RecoveryPolicy.LINEAR_BACKOFF)

        start_time = time.time()

        async def fail_func():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await recovery_manager.execute_with_recovery(
                "linear_op", fail_func, max_attempts=3
            )

        elapsed = time.time() - start_time
        # Should have delays: 2s + 4s = 6s total delay
        assert elapsed >= 6.0

    @pytest.mark.asyncio
    async def test_recovery_policy_exponential_backoff(self, recovery_manager):
        """Test exponential backoff recovery policy."""
        recovery_manager.add_recovery_policy(
            "exp_op", RecoveryPolicy.EXPONENTIAL_BACKOFF
        )

        start_time = time.time()

        async def fail_func():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await recovery_manager.execute_with_recovery(
                "exp_op", fail_func, max_attempts=4
            )

        elapsed = time.time() - start_time
        # Should have delays: 1s + 2s + 4s = 7s total delay
        assert elapsed >= 7.0

    @pytest.mark.asyncio
    async def test_recovery_policy_custom(self, recovery_manager):
        """Test custom recovery policy."""
        custom_delays = []

        async def custom_recovery():
            delay = len(custom_delays) * 0.5 + 0.5  # 0.5s, 1.0s, 1.5s...
            custom_delays.append(delay)
            await asyncio.sleep(delay)

        recovery_manager.add_recovery_policy(
            "custom_op", RecoveryPolicy.CUSTOM, custom_recovery
        )

        start_time = time.time()

        async def fail_func():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await recovery_manager.execute_with_recovery(
                "custom_op", fail_func, max_attempts=3
            )

        elapsed = time.time() - start_time
        assert len(custom_delays) == 2  # Two retries
        assert custom_delays == [0.5, 1.0]

    @pytest.mark.asyncio
    async def test_get_recovery_stats(self, recovery_manager):
        """Test recovery statistics collection."""
        config = CircuitBreakerConfig()
        recovery_manager.add_circuit_breaker("stats_cb", config)
        recovery_manager.add_recovery_policy("stats_op", RecoveryPolicy.LINEAR_BACKOFF)

        stats = recovery_manager.get_recovery_stats()

        assert "circuit_breakers" in stats
        assert "stats_cb" in stats["circuit_breakers"]
        assert "recovery_policies" in stats
        assert stats["recovery_policies"]["stats_op"] == RecoveryPolicy.LINEAR_BACKOFF

    @pytest.mark.asyncio
    async def test_reset_all_circuit_breakers(self, recovery_manager):
        """Test resetting all circuit breakers."""
        config = CircuitBreakerConfig()
        cb1 = recovery_manager.add_circuit_breaker("cb1", config)
        cb2 = recovery_manager.add_circuit_breaker("cb2", config)

        # Cause failures
        async def fail_func():
            raise ValueError("fail")

        for cb in [cb1, cb2]:
            for _ in range(5):  # More than default threshold of 5
                with pytest.raises(ValueError):
                    await cb.call(fail_func)
            assert cb.get_state() == CircuitBreakerState.OPEN

        # Reset all
        recovery_manager.reset_all_circuit_breakers()

        for cb in [cb1, cb2]:
            assert cb.get_state() == CircuitBreakerState.CLOSED


class TestPrinterErrorRecovery:
    """Test PrinterErrorRecovery integration class."""

    @pytest.fixture
    def status_reporter(self):
        """Create mock status reporter."""
        return AsyncMock(spec=PrinterStatusReporter)

    @pytest.fixture
    def default_config(self):
        """Create default circuit breaker config."""
        return CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1.0,
            success_threshold=2,
        )

    @pytest_asyncio.fixture
    async def error_recovery(self, status_reporter, default_config):
        """Create PrinterErrorRecovery instance."""
        recovery = PrinterErrorRecovery(status_reporter, default_config)
        yield recovery

    @pytest.mark.asyncio
    async def test_initialization(self, error_recovery):
        """Test initialization."""
        assert error_recovery.status_reporter is not None
        assert error_recovery.default_circuit_config is not None
        assert isinstance(error_recovery.recovery_manager, RecoveryManager)

    @pytest.mark.asyncio
    async def test_add_operation_circuit(self, error_recovery):
        """Test adding operation-specific circuit breaker."""
        cb = error_recovery.add_operation_circuit("print_job")

        assert isinstance(cb, CircuitBreaker)
        assert cb.name == "circuit_print_job"

        # Verify it's registered
        retrieved_cb = error_recovery.get_operation_circuit("print_job")
        assert retrieved_cb is cb

    @pytest.mark.asyncio
    async def test_add_recovery_policy(self, error_recovery):
        """Test adding recovery policy."""
        error_recovery.add_recovery_policy(
            "test_op", RecoveryPolicy.EXPONENTIAL_BACKOFF
        )

        # Verify policy is set
        stats = error_recovery.get_recovery_stats()
        assert (
            stats["recovery_policies"]["test_op"] == RecoveryPolicy.EXPONENTIAL_BACKOFF
        )

    @pytest.mark.asyncio
    async def test_execute_operation_success(self, error_recovery):
        """Test successful operation execution."""

        async def success_func():
            return "printed"

        result = await error_recovery.execute_operation("success_op", success_func)
        assert result == "printed"

    @pytest.mark.asyncio
    async def test_execute_operation_with_circuit_breaker(self, error_recovery):
        """Test operation execution with circuit breaker."""
        # Add circuit for operation
        error_recovery.add_operation_circuit("protected_op")

        call_count = 0

        async def fail_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError(f"Fail {call_count}")

        # Should eventually open circuit and raise CircuitBreakerOpenError
        for i in range(5):  # More than threshold
            try:
                await error_recovery.execute_operation(
                    "protected_op", fail_func, use_circuit_breaker=True, max_attempts=1
                )
            except (ConnectionError, CircuitBreakerOpenError) as e:
                if isinstance(e, CircuitBreakerOpenError):
                    break
        else:
            pytest.fail("Circuit breaker should have opened")

    @pytest.mark.asyncio
    async def test_execute_operation_circuit_open_error(self, error_recovery):
        """Test CircuitBreakerOpenError handling."""
        error_recovery.add_operation_circuit("circuit_op")

        # Force circuit open
        cb = error_recovery.get_operation_circuit("circuit_op")
        await cb.force_open("Test")

        async def dummy_func():
            return "should not execute"

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await error_recovery.execute_operation("circuit_op", dummy_func)

        assert "circuit_op" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_operation_circuit_none(self, error_recovery):
        """Test getting circuit for non-existent operation."""
        cb = error_recovery.get_operation_circuit("nonexistent")
        assert cb is None

    @pytest.mark.asyncio
    async def test_get_recovery_stats(self, error_recovery):
        """Test comprehensive recovery statistics."""
        error_recovery.add_operation_circuit("stats_op")
        error_recovery.add_recovery_policy("stats_policy", RecoveryPolicy.IMMEDIATE)

        stats = error_recovery.get_recovery_stats()

        assert "circuit_breakers" in stats
        assert "recovery_policies" in stats
        assert "operation_circuits" in stats
        assert stats["operation_circuits"]["stats_op"] == "circuit_stats_op"

    @pytest.mark.asyncio
    async def test_reset_operation_circuit(self, error_recovery):
        """Test resetting specific operation circuit."""
        error_recovery.add_operation_circuit("reset_op")

        cb = error_recovery.get_operation_circuit("reset_op")
        await cb.force_open("Test")

        assert cb.get_state() == CircuitBreakerState.OPEN

        error_recovery.reset_operation_circuit("reset_op")
        assert cb.get_state() == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_reset_operation_circuit_nonexistent(self, error_recovery):
        """Test resetting non-existent operation circuit."""
        # Should not raise exception
        error_recovery.reset_operation_circuit("nonexistent")

    @pytest.mark.asyncio
    async def test_reset_all_circuits(self, error_recovery):
        """Test resetting all circuits."""
        error_recovery.add_operation_circuit("op1")
        error_recovery.add_operation_circuit("op2")

        for op in ["op1", "op2"]:
            cb = error_recovery.get_operation_circuit(op)
            await cb.force_open("Test")

        error_recovery.reset_all_circuits()

        for op in ["op1", "op2"]:
            cb = error_recovery.get_operation_circuit(op)
            assert cb.get_state() == CircuitBreakerState.CLOSED


class TestCircuitBreakerOpenError:
    """Test CircuitBreakerOpenError exception."""

    def test_error_initialization(self):
        """Test error initialization."""
        error = CircuitBreakerOpenError("Circuit open", "test_circuit", 123456.789)

        assert str(error) == "Circuit open"
        assert error.circuit_name == "test_circuit"
        assert error.last_failure_time == 123456.789

    def test_error_initialization_no_time(self):
        """Test error initialization without failure time."""
        error = CircuitBreakerOpenError("Circuit open", "test_circuit")

        assert error.circuit_name == "test_circuit"
        assert error.last_failure_time is None


class TestRecoveryPolicy:
    """Test RecoveryPolicy enum."""

    def test_policy_values(self):
        """Test recovery policy enum values."""
        assert RecoveryPolicy.IMMEDIATE.value == "immediate"
        assert RecoveryPolicy.LINEAR_BACKOFF.value == "linear_backoff"
        assert RecoveryPolicy.EXPONENTIAL_BACKOFF.value == "exponential_backoff"
        assert RecoveryPolicy.CUSTOM.value == "custom"
        assert RecoveryPolicy.RETRY.value == "retry"  # Alias for immediate


class TestCircuitBreakerState:
    """Test CircuitBreakerState enum."""

    def test_state_values(self):
        """Test circuit breaker state enum values."""
        assert CircuitBreakerState.CLOSED.value == "closed"
        assert CircuitBreakerState.OPEN.value == "open"
        assert CircuitBreakerState.HALF_OPEN.value == "half_open"
