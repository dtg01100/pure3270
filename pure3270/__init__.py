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

from .patching import enable_replacement
from .session import AsyncSession, Session


class JSONFormatter(logging.Formatter):
    def format(self, record):
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


def setup_logging(level="INFO"):
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


def main():
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

        if args.script:
            # Execute script file
            with open(args.script, "r") as f:
                commands = [line.strip() for line in f if line.strip()]
            result = session.execute_macro(";".join(commands))
            print("Script executed:", result)
        else:
            # Interactive mode
            print(
                "Enter commands (e.g., 'String(hello)', 'key Enter'). Type 'quit' to exit."
            )
            # Only enter blocking input loop when running interactively
            if sys.stdin.isatty():
                while True:
                    try:
                        command = input("> ").strip()
                        if command.lower() in ("quit", "exit"):
                            break
                        result = session.execute_macro(command)
                        print("Result:", result)
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        print(f"Error: {e}")
            else:
                print("Non-interactive session: skipping interactive prompt.")

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


from .protocol.exceptions import MacroError

__all__ = [
    "Session",
    "AsyncSession",
    "enable_replacement",
    "setup_logging",
    "MacroError",
]
