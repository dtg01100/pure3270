"""
Utilities package for pure3270.

Contains common utility functions and classes used across the pure3270 codebase.
"""

from datetime import datetime, timezone


def utcnow_iso_z() -> str:
    """Return the current UTC time as an ISO-8601 string with a
    ``Z`` suffix (e.g. ``2026-06-14T16:52:28.123456Z``).

    Centralised so snapshot timestamps and DRY-violation report
    timestamps stay in lockstep for downstream correlation.
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


from .logging_utils import (
    log_command_error,
    log_command_handling,
    log_connection_event,
    log_data_processing,
    log_debug_operation,
    log_negotiation_event,
    log_parsing_warning,
    log_protocol_event,
    log_session_action,
    log_session_error,
)

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
    "utcnow_iso_z",
]
