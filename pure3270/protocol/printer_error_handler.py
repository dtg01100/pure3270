"""
PrinterErrorHandler for hierarchical error handling and recovery strategies.

Provides comprehensive error handling for printer operations with configurable
recovery strategies, error classification, and integration with logging systems.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

from ..exceptions import ProtocolError, Pure3270Error
from ..utils.logging_utils import log_session_error

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for targeted recovery strategies."""

    CONNECTION = "connection"
    PROTOCOL = "protocol"
    TIMEOUT = "timeout"
    DATA = "data"
    SESSION = "session"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""

    RETRY = "retry"
    RECONNECT = "reconnect"
    RESET = "reset"
    FAILOVER = "failover"
    ESCALATE = "escalate"
    IGNORE = "ignore"


class PrinterErrorHandler:
    """
    Hierarchical error handler for printer operations.

    Provides configurable error classification, recovery strategies, and
    integration with logging and monitoring systems.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_retry_delay: float = 1.0,
        max_retry_delay: float = 30.0,
        recovery_timeout: float = 60.0,
        enable_escalation: bool = True,
    ):
        """
        Initialize the error handler.

        Args:
            max_retries: Maximum number of retry attempts
            base_retry_delay: Base delay between retries (seconds)
            max_retry_delay: Maximum delay between retries (seconds)
            recovery_timeout: Maximum time for recovery operations (seconds)
            enable_escalation: Whether to escalate critical errors
        """
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        self.max_retry_delay = max_retry_delay
        self.recovery_timeout = recovery_timeout
        self.enable_escalation = enable_escalation

        # Error tracking
        self._error_counts: Dict[str, int] = {}
        self._last_errors: Dict[str, float] = {}
        self._recovery_lock = asyncio.Lock()

        # Recovery strategy mappings
        self._recovery_strategies = self._build_recovery_strategies()

        logger.info("PrinterErrorHandler initialized")

    def _build_recovery_strategies(self) -> Dict[ErrorCategory, List[RecoveryStrategy]]:
        """Build default recovery strategy mappings."""
        return {
            ErrorCategory.CONNECTION: [
                RecoveryStrategy.RECONNECT,
                RecoveryStrategy.RETRY,
                RecoveryStrategy.ESCALATE,
            ],
            ErrorCategory.PROTOCOL: [
                RecoveryStrategy.RESET,
                RecoveryStrategy.RETRY,
                RecoveryStrategy.ESCALATE,
            ],
            ErrorCategory.TIMEOUT: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.RECONNECT,
                RecoveryStrategy.ESCALATE,
            ],
            ErrorCategory.DATA: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.RESET,
                RecoveryStrategy.ESCALATE,
            ],
            ErrorCategory.SESSION: [
                RecoveryStrategy.RECONNECT,
                RecoveryStrategy.RESET,
                RecoveryStrategy.ESCALATE,
            ],
            ErrorCategory.RESOURCE: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.FAILOVER,
                RecoveryStrategy.ESCALATE,
            ],
            ErrorCategory.UNKNOWN: [RecoveryStrategy.RETRY, RecoveryStrategy.ESCALATE],
        }

    def classify_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """
        Classify an error by category and severity.

        Args:
            error: The exception to classify

        Returns:
            Tuple of (category, severity)
        """
        # Connection errors
        if isinstance(error, (ConnectionError, OSError)):
            if "timeout" in str(error).lower():
                return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM
            return ErrorCategory.CONNECTION, ErrorSeverity.HIGH

        # Protocol errors
        if (
            isinstance(error, (ValueError, TypeError))
            or "protocol" in str(error).lower()
        ):
            return ErrorCategory.PROTOCOL, ErrorSeverity.HIGH

        # Timeout errors
        if isinstance(error, asyncio.TimeoutError) or "timeout" in str(error).lower():
            return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM

        # Session errors
        if "session" in str(error).lower() or isinstance(error, RuntimeError):
            return ErrorCategory.SESSION, ErrorSeverity.HIGH

        # Resource errors
        if (
            isinstance(error, (MemoryError, OSError))
            and "resource" in str(error).lower()
        ):
            return ErrorCategory.RESOURCE, ErrorSeverity.CRITICAL

        # Pure3270 specific errors
        if isinstance(error, Pure3270Error):
            context = getattr(error, "context", {})
            if context.get("operation") == "connection":
                return ErrorCategory.CONNECTION, ErrorSeverity.HIGH
            elif context.get("operation") == "protocol":
                return ErrorCategory.PROTOCOL, ErrorSeverity.HIGH
            elif context.get("operation") == "timeout":
                return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM

        # Default classification
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM

    async def handle_error(
        self,
        error: Exception,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        recovery_callback: Optional[Callable[[], Any]] = None,
    ) -> bool:
        """
        Handle an error with appropriate recovery strategy.

        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            context: Additional context information
            recovery_callback: Optional callback for recovery operations

        Returns:
            True if error was handled/recovered, False if it should be re-raised
        """
        context = context or {}
        category, severity = self.classify_error(error)

        # Log the error
        error_msg = f"{operation} failed: {error}"
        if context:
            error_msg += f" (context: {context})"

        if severity == ErrorSeverity.CRITICAL:
            logger.critical(error_msg)
        elif severity == ErrorSeverity.HIGH:
            logger.error(error_msg)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(error_msg)
        else:
            logger.info(error_msg)

        # Track error frequency
        error_key = f"{category.value}:{operation}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
        self._last_errors[error_key] = time.time()

        # Attempt recovery
        return await self._attempt_recovery(
            error, category, severity, operation, recovery_callback
        )

    async def _attempt_recovery(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        operation: str,
        recovery_callback: Optional[Callable[[], Any]] = None,
    ) -> bool:
        """
        Attempt to recover from an error using configured strategies.

        Args:
            error: The original error
            category: Error category
            severity: Error severity
            operation: Operation description
            recovery_callback: Optional recovery callback

        Returns:
            True if recovery succeeded, False otherwise
        """
        strategies = self._recovery_strategies.get(
            category, [RecoveryStrategy.ESCALATE]
        )

        async with self._recovery_lock:
            for strategy in strategies:
                try:
                    if await self._execute_recovery_strategy(
                        strategy,
                        error,
                        category,
                        severity,
                        operation,
                        recovery_callback,
                    ):
                        logger.info(
                            f"Recovery successful for {operation} using {strategy.value}"
                        )
                        return True
                except Exception as recovery_error:
                    logger.warning(
                        f"Recovery strategy {strategy.value} failed: {recovery_error}"
                    )
                    continue

        # All recovery strategies failed
        if severity == ErrorSeverity.CRITICAL and self.enable_escalation:
            logger.critical(f"Critical error escalation for {operation}: {error}")
            # Could integrate with external monitoring/alerting here

        return False

    async def _execute_recovery_strategy(
        self,
        strategy: RecoveryStrategy,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        operation: str,
        recovery_callback: Optional[Callable[[], Any]] = None,
    ) -> bool:
        """
        Execute a specific recovery strategy.

        Args:
            strategy: The recovery strategy to execute
            error: The original error
            category: Error category
            severity: Error severity
            operation: Operation description
            recovery_callback: Optional recovery callback

        Returns:
            True if strategy succeeded, False otherwise
        """
        if strategy == RecoveryStrategy.RETRY:
            return await self._retry_operation(operation, recovery_callback)
        elif strategy == RecoveryStrategy.RECONNECT:
            return await self._reconnect_operation(operation, recovery_callback)
        elif strategy == RecoveryStrategy.RESET:
            return await self._reset_operation(operation, recovery_callback)
        elif strategy == RecoveryStrategy.FAILOVER:
            return await self._failover_operation(operation, recovery_callback)
        elif strategy == RecoveryStrategy.ESCALATE:
            return False  # Escalation means don't recover
        elif strategy == RecoveryStrategy.IGNORE:
            logger.info(f"Ignoring error for {operation}: {error}")
            return True

        # Fallback for any unhandled strategies (should not occur with enum)
        logger.warning(f"Unknown recovery strategy: {strategy}")  # type: ignore[unreachable]
        return False

    async def _retry_operation(
        self, operation: str, recovery_callback: Optional[Callable[[], Any]] = None
    ) -> bool:
        """Retry an operation with exponential backoff."""
        if not recovery_callback:
            return False

        for attempt in range(self.max_retries):
            try:
                delay = min(self.base_retry_delay * (2**attempt), self.max_retry_delay)
                if delay > 0:
                    await asyncio.sleep(delay)

                logger.debug(f"Retrying {operation} (attempt {attempt + 1})")
                await asyncio.wait_for(
                    recovery_callback(), timeout=self.recovery_timeout
                )
                return True
            except Exception as e:
                logger.debug(f"Retry {attempt + 1} failed for {operation}: {e}")
                continue

        return False

    async def _reconnect_operation(
        self, operation: str, recovery_callback: Optional[Callable[[], Any]] = None
    ) -> bool:
        """Attempt reconnection recovery."""
        if not recovery_callback:
            return False

        try:
            logger.debug(f"Attempting reconnection for {operation}")
            await asyncio.wait_for(recovery_callback(), timeout=self.recovery_timeout)
            return True
        except Exception as e:
            logger.debug(f"Reconnection failed for {operation}: {e}")
            raise ProtocolError(
                f"Reconnection failed for {operation}", original_exception=e
            )

    async def _reset_operation(
        self, operation: str, recovery_callback: Optional[Callable[[], Any]] = None
    ) -> bool:
        """Reset operation state."""
        if not recovery_callback:
            return False

        try:
            logger.debug(f"Resetting state for {operation}")
            await asyncio.wait_for(recovery_callback(), timeout=self.recovery_timeout)
            return True
        except Exception as e:
            logger.debug(f"Reset failed for {operation}: {e}")
            raise ProtocolError(f"Reset failed for {operation}", original_exception=e)

    async def _failover_operation(
        self, operation: str, recovery_callback: Optional[Callable[[], Any]] = None
    ) -> bool:
        """Failover to alternative resource."""
        if not recovery_callback:
            return False

        try:
            logger.debug(f"Attempting failover for {operation}")
            await asyncio.wait_for(recovery_callback(), timeout=self.recovery_timeout)
            return True
        except Exception as e:
            logger.debug(f"Failover failed for {operation}: {e}")
            raise ProtocolError(
                f"Failover failed for {operation}", original_exception=e
            )

    def get_error_stats(self) -> Dict[str, Any]:
        """
        Get error statistics for monitoring.

        Returns:
            Dictionary with error counts and recent activity
        """
        current_time = time.time()
        recent_threshold = current_time - 3600  # Last hour

        recent_errors = {
            key: count
            for key, count in self._error_counts.items()
            if self._last_errors.get(key, 0) > recent_threshold
        }

        return {
            "total_errors": sum(self._error_counts.values()),
            "error_counts_by_type": dict(self._error_counts),
            "recent_errors": recent_errors,
            "recent_error_count": sum(recent_errors.values()),
            "last_error_time": (
                max(self._last_errors.values()) if self._last_errors else None
            ),
        }

    def reset_error_stats(self) -> None:
        """Reset error statistics."""
        self._error_counts.clear()
        self._last_errors.clear()
        logger.info("Error statistics reset")

    def add_recovery_strategy(
        self, category: ErrorCategory, strategy: RecoveryStrategy, priority: int = 0
    ) -> None:
        """
        Add a custom recovery strategy for an error category.

        Args:
            category: Error category to add strategy for
            strategy: Recovery strategy to add
            priority: Priority order (lower numbers = higher priority)
        """
        if category not in self._recovery_strategies:
            self._recovery_strategies[category] = []

        strategies = self._recovery_strategies[category]
        if strategy not in strategies:
            strategies.insert(priority, strategy)
            logger.info(
                f"Added recovery strategy {strategy.value} for {category.value}"
            )
