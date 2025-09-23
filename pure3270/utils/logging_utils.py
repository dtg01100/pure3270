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
