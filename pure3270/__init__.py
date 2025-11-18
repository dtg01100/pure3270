"""
pure3270 package init.
Exports core classes and functions for 3270 terminal emulation.
"""

import argparse
import datetime
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

from .p3270_client import P3270Client
from .protocol.printer import PrinterSession
from .session import AsyncSession, Session


class JSONFormatter(logging.Formatter):
    """Enhanced JSON formatter with structured logging support."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Add session correlation
        session_id = getattr(record, "session_id", None)
        if session_id:
            log_entry["session_id"] = session_id

        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add operation timing
        operation_start = getattr(record, "operation_start", None)
        if operation_start:
            duration = (
                datetime.datetime.now() - operation_start
            ).total_seconds() * 1000
            log_entry["duration_ms"] = round(duration, 2)

        # Add protocol-specific fields
        protocol_phase = getattr(record, "protocol_phase", None)
        if protocol_phase:
            log_entry["protocol_phase"] = protocol_phase

        packet_type = getattr(record, "packet_type", None)
        if packet_type:
            log_entry["packet_type"] = packet_type

        sequence_number = getattr(record, "sequence_number", None)
        if sequence_number is not None:
            log_entry["sequence_number"] = sequence_number

        # Add extra structured data
        extra = getattr(record, "pure3270_extra", {})
        if extra:
            log_entry.update(extra)

        # Handle exceptions
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            context = extra.get("context") if extra else None
            if context:
                log_entry["context"] = context

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class StructuredLogger:
    """Enhanced logger with structured logging capabilities."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log_operation(
        self,
        level: int,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Log an operation with structured data."""
        extra: Dict[str, Any] = {"pure3270_extra": {"operation": operation}}
        if details is not None:
            extra["pure3270_extra"].update(details)
        extra.update(kwargs)

        self.logger.log(level, f"Operation: {operation}", extra=extra)

    def log_protocol_event(
        self,
        level: int,
        event: str,
        phase: Optional[str] = None,
        packet_type: Optional[str] = None,
        sequence: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Log protocol-specific events."""
        extra: Dict[str, Any] = {"pure3270_extra": {"event": event}}
        if phase is not None:
            extra["protocol_phase"] = phase
        if packet_type is not None:
            extra["packet_type"] = packet_type
        if sequence is not None:
            extra["sequence_number"] = sequence
        extra.update(kwargs)

        self.logger.log(level, f"Protocol event: {event}", extra=extra)

    def log_performance(
        self,
        operation: str,
        start_time: datetime.datetime,
        success: bool = True,
        **kwargs: Any,
    ) -> None:
        """Log performance metrics."""
        extra: Dict[str, Any] = {
            "operation_start": start_time,
            "pure3270_extra": {"operation": operation, "success": success},
        }
        extra.update(kwargs)

        level = logging.INFO if success else logging.WARNING
        status = "completed" if success else "failed"
        self.logger.log(level, f"Performance: {operation} {status}", extra=extra)


def setup_logging(level: str = "WARNING") -> None:
    """
    Setup basic logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    use_json = os.environ.get("PURE3270_LOG_JSON", "false").lower() == "true"
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper()))
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    if use_json:
        handler = logging.StreamHandler()
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        root.addHandler(handler)
    else:
        logging.basicConfig(level=getattr(logging, level.upper()))


def main() -> None:
    """CLI entry point for s3270-compatible interface."""
    parser = argparse.ArgumentParser(description="pure3270 - 3270 Terminal Emulator")
    parser.add_argument("host", help="Host to connect to")
    parser.add_argument(
        "port", type=int, nargs="?", default=23, help="Port (default 23)"
    )
    parser.add_argument("--ssl", action="store_true", help="Use SSL/TLS")
    parser.add_argument("--script", help="Script file to execute")
    parser.add_argument(
        "--console",
        action="store_true",
        help="Force console (stdout) output instead of structured logging",
    )
    args = parser.parse_args()

    setup_logging("WARNING")

    # Set console mode for downstream modules to decide on print vs log
    console_mode = bool(getattr(args, "console", False))
    # Preserve existing environment setting and restore it after we exit so
    # running the CLI in tests doesn't leave a global env var that alters
    # behavior for subsequent tests. This avoids subtle test ordering flakiness.
    prev_console_mode = os.environ.get("PURE3270_CONSOLE_MODE", None)
    if console_mode:
        os.environ["PURE3270_CONSOLE_MODE"] = "true"
    else:
        os.environ.pop("PURE3270_CONSOLE_MODE", None)

    session = Session()
    try:
        session.connect(args.host, port=args.port, ssl_context=args.ssl)
        msg = f"Connected to {args.host}:{args.port}"
        if os.environ.get("PURE3270_CONSOLE_MODE", "false").lower() == "true":
            print(msg)
        else:
            logging.getLogger(__name__).info(msg)

        # Interactive CLI macro support has been removed.
        if args.script:
            msg = (
                "Macro scripting/DSL has been removed from pure3270 and will "
                "not return. Script execution via macro DSL is permanently "
                "unsupported."
            )
        else:
            msg = (
                "Macro scripting/DSL has been removed from pure3270 and will "
                "not return. Interactive macro DSL is permanently unsupported."
            )
        if os.environ.get("PURE3270_CONSOLE_MODE", "false").lower() == "true":
            print(msg)
        else:
            logging.getLogger(__name__).info(msg)

    except Exception as e:
        context = getattr(e, "context", None)
        if context:
            msg = f"Connection failed: {e} (Context: {context})"
        else:
            msg = f"Connection failed: {e}"
        if os.environ.get("PURE3270_CONSOLE_MODE", "false").lower() == "true":
            print(msg)
        else:
            logging.getLogger(__name__).error(msg)
    finally:
        session.close()
        if os.environ.get("PURE3270_CONSOLE_MODE", "false").lower() == "true":
            print("Disconnected.")
        else:
            logging.getLogger(__name__).info("Disconnected.")
        # Restore previous environment value to avoid leaking console mode
        # into other tests or environments that import/execute CLI code.
        if prev_console_mode is None:
            os.environ.pop("PURE3270_CONSOLE_MODE", None)
        else:
            os.environ["PURE3270_CONSOLE_MODE"] = prev_console_mode


if __name__ == "__main__":
    main()


__all__ = [
    "Session",
    "AsyncSession",
    "PrinterSession",
    "P3270Client",
    "setup_logging",
]
