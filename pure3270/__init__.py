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

from .session import AsyncSession, Session
from .p3270_client import P3270Client


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id
        extra = getattr(record, "pure3270_extra", {})
        log_entry.update(extra)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            if "context" in extra:
                log_entry["context"] = extra["context"]
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
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
    args = parser.parse_args()

    setup_logging("INFO")

    session = Session()
    try:
        session.connect(args.host, port=args.port, ssl_context=args.ssl)
        print(f"Connected to {args.host}:{args.port}")

        # Interactive CLI macro support has been removed.
        if args.script:
            print(
                "Macro scripting/DSL has been removed from pure3270 and will "
                "not return. Script execution via macro DSL is permanently "
                "unsupported."
            )
        else:
            print(
                "Macro scripting/DSL has been removed from pure3270 and will "
                "not return. Interactive macro DSL is permanently unsupported."
            )

    except Exception as e:
        if hasattr(e, "context") and e.context:
            print(f"Connection failed: {e} (Context: {e.context})")
        else:
            print(f"Connection failed: {e}")
    finally:
        session.close()
        print("Disconnected.")


if __name__ == "__main__":
    main()


__all__ = [
    "Session",
    "AsyncSession",
    "P3270Client",
    "setup_logging",
]
