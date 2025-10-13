"""
PrinterStatusReporter for status tracking and notification system.

Provides comprehensive status tracking for printer operations with configurable
notification mechanisms, health monitoring, and integration with monitoring systems.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from ..utils.logging_utils import log_connection_event, log_session_action

logger = logging.getLogger(__name__)


class PrinterStatus(Enum):
    """Printer operational status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DOWN = "down"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class StatusEvent(Enum):
    """Status event types for notifications."""

    STATUS_CHANGE = "status_change"
    HEALTH_CHECK = "health_check"
    ERROR_OCCURRED = "error_occurred"
    RECOVERY_SUCCESS = "recovery_success"
    PERFORMANCE_ISSUE = "performance_issue"
    RESOURCE_WARNING = "resource_warning"


class NotificationPriority(Enum):
    """Notification priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StatusNotification:
    """Container for status notification data."""

    def __init__(
        self,
        event_type: StatusEvent,
        priority: NotificationPriority,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ):
        """
        Initialize a status notification.

        Args:
            event_type: Type of status event
            priority: Notification priority level
            message: Notification message
            context: Additional context information
            timestamp: Event timestamp (defaults to current time)
        """
        self.event_type = event_type
        self.priority = priority
        self.message = message
        self.context = context or {}
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary format."""
        return {
            "event_type": self.event_type.value,
            "priority": self.priority.value,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp,
        }


class PrinterStatusReporter:
    """
    Status tracking and notification system for printer operations.

    Provides comprehensive status monitoring with configurable notifications,
    health checks, and integration with external monitoring systems.
    """

    def __init__(
        self,
        health_check_interval: float = 60.0,
        status_history_size: int = 1000,
        enable_notifications: bool = True,
        notification_queue_size: int = 100,
    ):
        """
        Initialize the status reporter.

        Args:
            health_check_interval: Interval between health checks (seconds)
            status_history_size: Maximum number of status history entries
            enable_notifications: Whether to enable notifications
            notification_queue_size: Maximum size of notification queue
        """
        self.health_check_interval = health_check_interval
        self.status_history_size = status_history_size
        self.enable_notifications = enable_notifications
        self.notification_queue_size = notification_queue_size

        # Status tracking
        self._current_status: PrinterStatus = PrinterStatus.UNKNOWN
        self._status_history: List[Dict[str, Any]] = []
        self._last_health_check: Optional[float] = None
        self._status_lock = asyncio.Lock()

        # Health metrics
        self._health_metrics: Dict[str, Any] = {}
        self._performance_counters: Dict[str, int] = {}
        self._error_counters: Dict[str, int] = {}

        # Notification system
        self._notification_callbacks: List[Callable[[StatusNotification], None]] = []
        self._notification_queue: asyncio.Queue[StatusNotification] = asyncio.Queue(
            maxsize=notification_queue_size
        )
        self._notification_task: Optional[asyncio.Task[None]] = None

        # Health check task
        self._health_check_task: Optional[asyncio.Task[None]] = None

        logger.info("PrinterStatusReporter initialized")

    async def start(self) -> None:
        """Start the status reporter and background tasks."""
        if self._notification_task is None and self.enable_notifications:
            self._notification_task = asyncio.create_task(self._process_notifications())

        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._run_health_checks())

        logger.info("PrinterStatusReporter started")

    async def stop(self) -> None:
        """Stop the status reporter and cleanup resources."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        if self._notification_task:
            self._notification_task.cancel()
            try:
                await self._notification_task
            except asyncio.CancelledError:
                pass
            self._notification_task = None

        logger.info("PrinterStatusReporter stopped")

    async def update_status(
        self,
        new_status: PrinterStatus,
        reason: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update the current printer status.

        Args:
            new_status: New status to set
            reason: Reason for status change
            context: Additional context information
        """
        context = context or {}
        old_status = self._current_status

        async with self._status_lock:
            self._current_status = new_status

            # Record status change in history
            status_entry = {
                "timestamp": time.time(),
                "status": new_status.value,
                "previous_status": (
                    old_status.value if old_status != new_status else None
                ),
                "reason": reason,
                "context": context,
            }
            self._status_history.append(status_entry)

            # Maintain history size limit
            if len(self._status_history) > self.status_history_size:
                self._status_history.pop(0)

        # Notify about status change
        if old_status != new_status:
            await self._notify_status_change(
                StatusEvent.STATUS_CHANGE,
                (
                    NotificationPriority.MEDIUM
                    if new_status != PrinterStatus.DOWN
                    else NotificationPriority.CRITICAL
                ),
                f"Status changed from {old_status.value} to {new_status.value}: {reason}",
                context,
            )

        logger.info(f"Printer status updated to {new_status.value}: {reason}")

    async def report_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Report an error occurrence.

        Args:
            error_type: Type/category of error
            error_message: Error message
            context: Additional context information
        """
        context = context or {}

        # Update error counters
        self._error_counters[error_type] = self._error_counters.get(error_type, 0) + 1

        # Determine notification priority based on error frequency
        error_count = self._error_counters[error_type]
        priority = NotificationPriority.LOW
        if error_count > 10:
            priority = NotificationPriority.HIGH
        elif error_count > 5:
            priority = NotificationPriority.MEDIUM

        await self._notify_status_change(
            StatusEvent.ERROR_OCCURRED,
            priority,
            f"Error ({error_type}): {error_message}",
            context,
        )

    async def report_recovery(
        self, operation: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Report a successful recovery operation.

        Args:
            operation: Operation that was recovered
            context: Additional context information
        """
        context = context or {}

        await self._notify_status_change(
            StatusEvent.RECOVERY_SUCCESS,
            NotificationPriority.MEDIUM,
            f"Recovery successful for operation: {operation}",
            context,
        )

    async def update_health_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Update health metrics.

        Args:
            metrics: Dictionary of health metrics
        """
        self._health_metrics.update(metrics)
        self._last_health_check = time.time()

        # Check for health status changes based on metrics
        await self._evaluate_health_status()

    async def increment_performance_counter(
        self, counter_name: str, increment: int = 1
    ) -> None:
        """
        Increment a performance counter.

        Args:
            counter_name: Name of the counter
            increment: Amount to increment
        """
        self._performance_counters[counter_name] = (
            self._performance_counters.get(counter_name, 0) + increment
        )

    def get_current_status(self) -> PrinterStatus:
        """Get the current printer status."""
        return self._current_status

    def get_status_history(
        self, limit: Optional[int] = None, since: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Get status history.

        Args:
            limit: Maximum number of entries to return
            since: Only return entries since this timestamp

        Returns:
            List of status history entries
        """
        history = self._status_history

        if since:
            history = [entry for entry in history if entry["timestamp"] >= since]

        if limit:
            history = history[-limit:]

        return history

    def get_health_metrics(self) -> Dict[str, Any]:
        """Get current health metrics."""
        return dict(self._health_metrics)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "counters": dict(self._performance_counters),
            "error_counts": dict(self._error_counters),
            "uptime": time.time()
            - (
                self._status_history[0]["timestamp"]
                if self._status_history
                else time.time()
            ),
        }

    def get_status_summary(self) -> Dict[str, Any]:
        """Get a comprehensive status summary."""
        return {
            "current_status": self._current_status.value,
            "last_health_check": self._last_health_check,
            "health_metrics": self.get_health_metrics(),
            "performance_stats": self.get_performance_stats(),
            "recent_history": self.get_status_history(limit=10),
            "notification_queue_size": (
                self._notification_queue.qsize() if self.enable_notifications else 0
            ),
        }

    def add_notification_callback(
        self, callback: Callable[[StatusNotification], None]
    ) -> None:
        """
        Add a notification callback.

        Args:
            callback: Function to call when notifications occur
        """
        if callback not in self._notification_callbacks:
            self._notification_callbacks.append(callback)
            logger.info("Notification callback added")

    def remove_notification_callback(
        self, callback: Callable[[StatusNotification], None]
    ) -> None:
        """
        Remove a notification callback.

        Args:
            callback: Callback function to remove
        """
        if callback in self._notification_callbacks:
            self._notification_callbacks.remove(callback)
            logger.info("Notification callback removed")

    async def _notify_status_change(
        self,
        event_type: StatusEvent,
        priority: NotificationPriority,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Internal method to create and queue notifications.

        Args:
            event_type: Type of status event
            priority: Notification priority
            message: Notification message
            context: Additional context
        """
        if not self.enable_notifications:
            return

        notification = StatusNotification(event_type, priority, message, context)

        try:
            self._notification_queue.put_nowait(notification)
        except asyncio.QueueFull:
            logger.warning("Notification queue full, dropping notification")

    async def _process_notifications(self) -> None:
        """Process notifications from the queue."""
        while True:
            try:
                notification = await self._notification_queue.get()

                # Call all registered callbacks
                for callback in self._notification_callbacks:
                    try:
                        callback(notification)
                    except Exception as e:
                        logger.error(f"Error in notification callback: {e}")

                self._notification_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing notification: {e}")

    async def _run_health_checks(self) -> None:
        """Run periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)

                # Perform health check
                await self._perform_health_check()

                # Notify about health check
                await self._notify_status_change(
                    StatusEvent.HEALTH_CHECK,
                    NotificationPriority.LOW,
                    "Periodic health check completed",
                    {"health_metrics": self.get_health_metrics()},
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during health check: {e}")

    async def _perform_health_check(self) -> None:
        """Perform a health check (to be overridden by subclasses)."""
        # Default implementation - can be extended
        self._last_health_check = time.time()

    async def _evaluate_health_status(self) -> None:
        """Evaluate overall health status based on metrics."""
        # Simple health evaluation - can be made more sophisticated
        metrics = self._health_metrics

        # Check for critical conditions
        if metrics.get("connection_failures", 0) > 5:
            await self.update_status(
                PrinterStatus.UNHEALTHY, "High connection failure rate"
            )
        elif metrics.get("error_rate", 0) > 0.1:  # 10% error rate
            await self.update_status(PrinterStatus.DEGRADED, "High error rate detected")
        elif self._current_status in [PrinterStatus.UNHEALTHY, PrinterStatus.DOWN]:
            # Check if conditions have improved
            if (
                metrics.get("connection_failures", 0) < 2
                and metrics.get("error_rate", 0) < 0.05
            ):
                await self.update_status(PrinterStatus.HEALTHY, "Conditions improved")

    async def __aenter__(self) -> "PrinterStatusReporter":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit."""
        await self.stop()
