"""
PrinterErrorRecovery for error recovery mechanisms and circuit breaker patterns.

Provides circuit breaker implementation, error recovery strategies, and fault
tolerance mechanisms for printer operations with configurable thresholds and
recovery policies.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from .printer_error_handler import ErrorCategory, ErrorSeverity, RecoveryStrategy
from .printer_status_reporter import PrinterStatus, PrinterStatusReporter

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker operational states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing recovery


class RecoveryPolicy(Enum):
    """Recovery policy types."""

    IMMEDIATE = "immediate"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    CUSTOM = "custom"


class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
        monitoring_window: float = 300.0,  # 5 minutes
        half_open_max_calls: int = 3,
    ):
        """
        Initialize circuit breaker configuration.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery (seconds)
            success_threshold: Number of successes needed to close circuit
            monitoring_window: Time window for failure tracking (seconds)
            half_open_max_calls: Maximum calls allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.monitoring_window = monitoring_window
        self.half_open_max_calls = half_open_max_calls


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig,
        status_reporter: Optional[PrinterStatusReporter] = None,
    ):
        """
        Initialize the circuit breaker.

        Args:
            name: Unique name for this circuit breaker
            config: Circuit breaker configuration
            status_reporter: Optional status reporter for notifications
        """
        self.name = name
        self.config = config
        self.status_reporter = status_reporter

        # State management
        self._state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls: int = 0
        self._state_lock = asyncio.Lock()

        # Metrics
        self._total_calls: int = 0
        self._total_failures: int = 0
        self._total_successes: int = 0

        logger.info(f"CircuitBreaker '{name}' initialized")

    async def call(
        self, func: Callable[[], Any], fallback: Optional[Callable[[], Any]] = None
    ) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Function to execute
            fallback: Optional fallback function if circuit is open

        Returns:
            Result of the function call

        Raises:
            CircuitBreakerOpenError: If circuit is open and no fallback provided
            Exception: Original exception if call fails
        """
        async with self._state_lock:
            self._total_calls += 1

            if self._state == CircuitBreakerState.OPEN:
                if self._should_attempt_recovery():
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._half_open_calls = 0
                    await self._notify_state_change(
                        "Entering half-open state for recovery"
                    )
                else:
                    if fallback:
                        logger.debug(f"Circuit '{self.name}' open, using fallback")
                        return await self._execute_fallback(fallback)
                    else:
                        raise CircuitBreakerOpenError(
                            f"Circuit breaker '{self.name}' is open",
                            self.name,
                            self._last_failure_time,
                        )

            if self._state == CircuitBreakerState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    logger.warning(
                        f"Circuit '{self.name}' half-open call limit reached"
                    )
                    if fallback:
                        return await self._execute_fallback(fallback)
                    else:
                        raise CircuitBreakerOpenError(
                            f"Circuit breaker '{self.name}' half-open call limit exceeded",
                            self.name,
                            self._last_failure_time,
                        )
                self._half_open_calls += 1

        # Execute the function
        try:
            result = await func()
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise e

    async def _execute_fallback(self, fallback: Callable[[], Any]) -> Any:
        """Execute fallback function."""
        try:
            if asyncio.iscoroutinefunction(fallback):
                return await fallback()
            else:
                return fallback()
        except Exception as e:
            logger.error(f"Fallback execution failed for circuit '{self.name}': {e}")
            raise e

    def _should_attempt_recovery(self) -> bool:
        """Check if recovery should be attempted."""
        if self._last_failure_time is None:
            return False

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.recovery_timeout

    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._state_lock:
            self._total_successes += 1

            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    await self._close_circuit()
            else:
                # Reset failure count on success in closed state
                self._failure_count = 0

    async def _record_failure(self) -> None:
        """Record a failed call."""
        async with self._state_lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitBreakerState.HALF_OPEN:
                await self._open_circuit()
            elif (
                self._state == CircuitBreakerState.CLOSED
                and self._failure_count >= self.config.failure_threshold
            ):
                await self._open_circuit()

    async def _open_circuit(self) -> None:
        """Open the circuit breaker."""
        self._state = CircuitBreakerState.OPEN
        self._success_count = 0
        await self._notify_state_change("Circuit opened due to failures")

    async def _close_circuit(self) -> None:
        """Close the circuit breaker."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        await self._notify_state_change("Circuit closed - recovered successfully")

    async def _notify_state_change(self, message: str) -> None:
        """Notify about circuit breaker state changes."""
        if self.status_reporter:
            await self.status_reporter.update_status(
                (
                    PrinterStatus.DEGRADED
                    if self._state == CircuitBreakerState.OPEN
                    else PrinterStatus.HEALTHY
                ),
                f"Circuit breaker '{self.name}': {message}",
            )

        logger.info(f"CircuitBreaker '{self.name}': {message}")

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "last_failure_time": self._last_failure_time,
            "half_open_calls": self._half_open_calls,
        }

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        logger.info(f"CircuitBreaker '{self.name}' reset")


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(
        self, message: str, circuit_name: str, last_failure_time: Optional[float] = None
    ):
        """
        Initialize the circuit breaker open error.

        Args:
            message: Error message
            circuit_name: Name of the circuit breaker
            last_failure_time: Timestamp of last failure
        """
        super().__init__(message)
        self.circuit_name = circuit_name
        self.last_failure_time = last_failure_time


class RecoveryManager:
    """Manages recovery policies and strategies."""

    def __init__(self, status_reporter: Optional[PrinterStatusReporter] = None):
        """
        Initialize the recovery manager.

        Args:
            status_reporter: Optional status reporter for notifications
        """
        self.status_reporter = status_reporter
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._recovery_policies: Dict[str, RecoveryPolicy] = {}
        self._custom_policies: Dict[str, Callable[[], Any]] = {}

        logger.info("RecoveryManager initialized")

    def add_circuit_breaker(
        self, name: str, config: CircuitBreakerConfig
    ) -> CircuitBreaker:
        """
        Add a circuit breaker.

        Args:
            name: Unique name for the circuit breaker
            config: Circuit breaker configuration

        Returns:
            The created circuit breaker
        """
        if name in self._circuit_breakers:
            raise ValueError(f"Circuit breaker '{name}' already exists")

        circuit_breaker = CircuitBreaker(name, config, self.status_reporter)
        self._circuit_breakers[name] = circuit_breaker

        logger.info(f"Circuit breaker '{name}' added to recovery manager")
        return circuit_breaker

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """
        Get a circuit breaker by name.

        Args:
            name: Circuit breaker name

        Returns:
            Circuit breaker instance or None if not found
        """
        return self._circuit_breakers.get(name)

    def add_recovery_policy(
        self,
        operation: str,
        policy: RecoveryPolicy,
        custom_func: Optional[Callable[[], Any]] = None,
    ) -> None:
        """
        Add a recovery policy for an operation.

        Args:
            operation: Operation name
            policy: Recovery policy type
            custom_func: Custom recovery function (required for CUSTOM policy)
        """
        if policy == RecoveryPolicy.CUSTOM and custom_func is None:
            raise ValueError("Custom recovery policy requires a custom function")

        self._recovery_policies[operation] = policy
        if custom_func:
            self._custom_policies[operation] = custom_func

        logger.info(
            f"Recovery policy '{policy.value}' added for operation '{operation}'"
        )

    async def execute_with_recovery(
        self,
        operation: str,
        func: Callable[[], Any],
        circuit_breaker: Optional[str] = None,
        max_attempts: int = 3,
    ) -> Any:
        """
        Execute a function with recovery mechanisms.

        Args:
            operation: Operation name for policy lookup
            func: Function to execute
            circuit_breaker: Optional circuit breaker name to use
            max_attempts: Maximum recovery attempts

        Returns:
            Result of the function execution

        Raises:
            Exception: If all recovery attempts fail
        """
        cb = None
        if circuit_breaker:
            cb = self._circuit_breakers.get(circuit_breaker)
            if not cb:
                logger.warning(f"Circuit breaker '{circuit_breaker}' not found")

        policy = self._recovery_policies.get(operation, RecoveryPolicy.IMMEDIATE)

        for attempt in range(max_attempts):
            try:
                if cb:
                    return await cb.call(func)
                else:
                    return await func()
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed for operation '{operation}': {e}"
                )

                if attempt < max_attempts - 1:
                    await self._apply_recovery_policy(policy, operation, attempt)
                else:
                    # Final attempt failed
                    if self.status_reporter:
                        await self.status_reporter.report_error(
                            "recovery_failed",
                            f"All recovery attempts failed for operation '{operation}'",
                            {
                                "operation": operation,
                                "attempts": max_attempts,
                                "error": str(e),
                            },
                        )
                    raise e

    async def _apply_recovery_policy(
        self, policy: RecoveryPolicy, operation: str, attempt: int
    ) -> None:
        """
        Apply a recovery policy with delay.

        Args:
            policy: Recovery policy to apply
            operation: Operation name
            attempt: Current attempt number (0-based)
        """
        if policy == RecoveryPolicy.IMMEDIATE:
            return  # No delay
        elif policy == RecoveryPolicy.LINEAR_BACKOFF:
            delay = (attempt + 1) * 2.0  # 2s, 4s, 6s...
        elif policy == RecoveryPolicy.EXPONENTIAL_BACKOFF:
            delay = 2**attempt  # 1s, 2s, 4s, 8s...
        elif policy == RecoveryPolicy.CUSTOM:
            custom_func = self._custom_policies.get(operation)
            if custom_func:
                await custom_func()
            return
        else:
            delay = 1.0  # type: ignore[unreachable]  # Default delay for unknown policies

        logger.debug(
            f"Applying {policy.value} delay of {delay}s for operation '{operation}'"
        )
        await asyncio.sleep(delay)

    def get_recovery_stats(self) -> Dict[str, Any]:
        """
        Get recovery statistics.

        Returns:
            Dictionary with recovery metrics
        """
        circuit_breaker_stats = {}
        for name, cb in self._circuit_breakers.items():
            circuit_breaker_stats[name] = cb.get_metrics()

        stats = {
            "circuit_breakers": circuit_breaker_stats,
            "recovery_policies": dict(self._recovery_policies),
        }

        return stats

    def reset_all_circuit_breakers(self) -> None:
        """Reset all circuit breakers."""
        for cb in self._circuit_breakers.values():
            cb.reset()
        logger.info("All circuit breakers reset")


class PrinterErrorRecovery:
    """
    Comprehensive error recovery system with circuit breakers and policies.

    Integrates circuit breaker patterns, recovery policies, and status reporting
    for robust fault tolerance in printer operations.
    """

    def __init__(
        self,
        status_reporter: Optional[PrinterStatusReporter] = None,
        default_circuit_config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize the error recovery system.

        Args:
            status_reporter: Optional status reporter for notifications
            default_circuit_config: Default circuit breaker configuration
        """
        self.status_reporter = status_reporter
        self.default_circuit_config = default_circuit_config or CircuitBreakerConfig()
        self.recovery_manager = RecoveryManager(status_reporter)

        # Operation-specific circuit breakers
        self._operation_circuits: Dict[str, str] = {}

        logger.info("PrinterErrorRecovery initialized")

    def add_operation_circuit(
        self, operation: str, circuit_config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Add a circuit breaker for a specific operation.

        Args:
            operation: Operation name
            circuit_config: Circuit breaker configuration (uses default if None)

        Returns:
            The created circuit breaker
        """
        config = circuit_config or self.default_circuit_config
        circuit_name = f"circuit_{operation}"

        circuit_breaker = self.recovery_manager.add_circuit_breaker(
            circuit_name, config
        )
        self._operation_circuits[operation] = circuit_name

        logger.info(f"Circuit breaker added for operation '{operation}'")
        return circuit_breaker

    def add_recovery_policy(
        self,
        operation: str,
        policy: RecoveryPolicy,
        custom_func: Optional[Callable[[], Any]] = None,
    ) -> None:
        """
        Add a recovery policy for an operation.

        Args:
            operation: Operation name
            policy: Recovery policy type
            custom_func: Custom recovery function (for CUSTOM policy)
        """
        self.recovery_manager.add_recovery_policy(operation, policy, custom_func)

    async def execute_operation(
        self,
        operation: str,
        func: Callable[[], Any],
        use_circuit_breaker: bool = True,
        max_attempts: int = 3,
    ) -> Any:
        """
        Execute an operation with error recovery.

        Args:
            operation: Operation name
            func: Function to execute
            use_circuit_breaker: Whether to use circuit breaker protection
            max_attempts: Maximum recovery attempts

        Returns:
            Result of the operation

        Raises:
            Exception: If operation fails after all recovery attempts
        """
        circuit_name = (
            self._operation_circuits.get(operation) if use_circuit_breaker else None
        )

        try:
            result = await self.recovery_manager.execute_with_recovery(
                operation, func, circuit_name, max_attempts
            )

            # Report successful recovery if applicable
            if self.status_reporter and max_attempts > 1:
                await self.status_reporter.report_recovery(operation)

            return result

        except CircuitBreakerOpenError as e:
            if self.status_reporter:
                await self.status_reporter.report_error(
                    "circuit_open",
                    f"Circuit breaker open for operation '{operation}': {e}",
                    {"operation": operation, "circuit": e.circuit_name},
                )
            raise e
        except Exception as e:
            if self.status_reporter:
                await self.status_reporter.report_error(
                    "operation_failed",
                    f"Operation '{operation}' failed after recovery attempts: {e}",
                    {"operation": operation, "max_attempts": max_attempts},
                )
            raise e

    def get_operation_circuit(self, operation: str) -> Optional[CircuitBreaker]:
        """
        Get the circuit breaker for an operation.

        Args:
            operation: Operation name

        Returns:
            Circuit breaker instance or None if not configured
        """
        circuit_name = self._operation_circuits.get(operation)
        if circuit_name:
            return self.recovery_manager.get_circuit_breaker(circuit_name)
        return None

    def get_recovery_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive recovery statistics.

        Returns:
            Dictionary with recovery and circuit breaker metrics
        """
        stats = self.recovery_manager.get_recovery_stats()
        stats["operation_circuits"] = dict(self._operation_circuits)
        return stats

    def reset_operation_circuit(self, operation: str) -> None:
        """
        Reset the circuit breaker for an operation.

        Args:
            operation: Operation name
        """
        circuit = self.get_operation_circuit(operation)
        if circuit:
            circuit.reset()
            logger.info(f"Circuit breaker reset for operation '{operation}'")
        else:
            logger.warning(f"No circuit breaker configured for operation '{operation}'")

    def reset_all_circuits(self) -> None:
        """Reset all circuit breakers."""
        self.recovery_manager.reset_all_circuit_breakers()
