"""
Centralized logging utilities for pure3270.

Provides standardized logging functions for common scenarios to reduce duplication
and ensure consistent log formatting across the codebase.
"""

import logging
from typing import Any, Optional


def log_command_handling(
    logger: logging.Logger, command_name: str, details: str = ""
) -> None:
    """Log the start of command handling with consistent format."""
    detail_str = f": {details}" if details else ""
    logger.info(f"Handling {command_name} command{detail_str}")


def log_command_error(
    logger: logging.Logger, command_name: str, cmd: str, error: Exception
) -> None:
    """Log command execution errors with consistent format."""
    logger.error(f"Error handling {command_name} command '{cmd}': {error}")


def log_session_action(
    logger: logging.Logger, action_name: str, details: str = ""
) -> None:
    """Log session action execution with consistent format."""
    detail_str = f": {details}" if details else ""
    logger.info(f"Executing {action_name} action{detail_str}")


def log_session_error(
    logger: logging.Logger, action_name: str, error: Exception
) -> None:
    """Log session action errors with consistent format."""
    logger.error(f"Error executing {action_name} action: {error}")


def log_protocol_event(
    logger: logging.Logger, event_type: str, details: str = ""
) -> None:
    """Log protocol events with consistent format."""
    detail_str = f": {details}" if details else ""
    logger.info(f"[PROTOCOL] {event_type}{detail_str}")


def log_negotiation_event(
    logger: logging.Logger, event_type: str, details: str = ""
) -> None:
    """Log negotiation events with consistent format."""
    detail_str = f": {details}" if details else ""
    logger.info(f"[NEGOTIATION] {event_type}{detail_str}")


def log_parsing_warning(logger: logging.Logger, operation: str, reason: str) -> None:
    """Log parsing warnings with consistent format."""
    logger.warning(f"{operation}: {reason}")


# Categorized warning support
try:
    from pure3270.warnings import CategorizedLogger, WarningCategory

    def log_categorized_warning(
        logger: logging.Logger,
        category: WarningCategory,
        operation: str,
        reason: str,
        filters: Optional[Any] = None,
    ) -> None:
        """Log parsing warnings with category support."""
        if filters is not None:
            # Use categorized logger if filters provided
            categorized_logger = CategorizedLogger(logger, filters)
            categorized_logger.log_parsing_warning(f"{operation}: {reason}")
        else:
            # Fallback to regular warning
            logger.warning(f"[{category.value.upper()}] {operation}: {reason}")

    def log_protocol_warning(
        logger: logging.Logger,
        operation: str,
        reason: str,
        filters: Optional[Any] = None,
    ) -> None:
        """Log protocol-related warnings."""
        log_categorized_warning(
            logger, WarningCategory.PROTOCOL_NEGOTIATION, operation, reason, filters
        )

    def log_data_stream_warning(
        logger: logging.Logger,
        operation: str,
        reason: str,
        filters: Optional[Any] = None,
    ) -> None:
        """Log data stream warnings."""
        log_categorized_warning(
            logger, WarningCategory.DATA_STREAM, operation, reason, filters
        )

    def log_configuration_warning(
        logger: logging.Logger,
        operation: str,
        reason: str,
        filters: Optional[Any] = None,
    ) -> None:
        """Log configuration warnings."""
        log_categorized_warning(
            logger, WarningCategory.CONFIGURATION, operation, reason, filters
        )

    def log_performance_warning(
        logger: logging.Logger,
        operation: str,
        reason: str,
        filters: Optional[Any] = None,
    ) -> None:
        """Log performance warnings."""
        log_categorized_warning(
            logger, WarningCategory.PERFORMANCE, operation, reason, filters
        )

    def log_state_warning(
        logger: logging.Logger,
        operation: str,
        reason: str,
        filters: Optional[Any] = None,
    ) -> None:
        """Log state management warnings."""
        log_categorized_warning(
            logger, WarningCategory.STATE_MANAGEMENT, operation, reason, filters
        )

    def log_network_warning(
        logger: logging.Logger,
        operation: str,
        reason: str,
        filters: Optional[Any] = None,
    ) -> None:
        """Log network warnings."""
        log_categorized_warning(
            logger, WarningCategory.NETWORK, operation, reason, filters
        )

    def log_ssl_warning(
        logger: logging.Logger,
        operation: str,
        reason: str,
        filters: Optional[Any] = None,
    ) -> None:
        """Log SSL/TLS warnings."""
        log_categorized_warning(
            logger, WarningCategory.SSL_TLS, operation, reason, filters
        )

    def log_security_warning(
        logger: logging.Logger,
        operation: str,
        reason: str,
        filters: Optional[Any] = None,
    ) -> None:
        """Log security warnings."""
        log_categorized_warning(
            logger, WarningCategory.SECURITY, operation, reason, filters
        )

    # Export categorized warning functions
    __all__ = [
        "log_command_handling",
        "log_command_error",
        "log_session_action",
        "log_session_error",
        "log_protocol_event",
        "log_negotiation_event",
        "log_parsing_warning",
        "log_debug_operation",
        "log_connection_event",
        "log_data_processing",
        # Categorized warnings
        "log_categorized_warning",
        "log_protocol_warning",
        "log_data_stream_warning",
        "log_configuration_warning",
        "log_performance_warning",
        "log_state_warning",
        "log_network_warning",
        "log_ssl_warning",
        "log_security_warning",
    ]

except ImportError:
    # If warnings module not available, use regular warnings
    __all__ = [
        "log_command_handling",
        "log_command_error",
        "log_session_action",
        "log_session_error",
        "log_protocol_event",
        "log_negotiation_event",
        "log_parsing_warning",
        "log_debug_operation",
        "log_connection_event",
        "log_data_processing",
    ]


def log_debug_operation(
    logger: logging.Logger, operation: str, details: Any = None
) -> None:
    """Log debug information for operations."""
    if details is not None:
        logger.debug(f"{operation}: {details}")
    else:
        logger.debug(f"{operation}")


def log_connection_event(
    logger: logging.Logger, event_type: str, host: str = "", port: int = 0
) -> None:
    """Log connection events with consistent format."""
    if host and port:
        logger.info(f"[CONNECTION] {event_type} - {host}:{port}")
    else:
        logger.info(f"[CONNECTION] {event_type}")


def log_data_processing(
    logger: logging.Logger, operation: str, data_info: str = ""
) -> None:
    """Log data processing operations with consistent format."""
    info_str = f" - {data_info}" if data_info else ""
    logger.debug(f"[DATA] {operation}{info_str}")
