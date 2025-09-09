"""
pure3270 package init.
Exports core classes and functions for 3270 terminal emulation.
"""

import logging
import sys
import argparse
from .session import Session, AsyncSession
from .patching import enable_replacement


def setup_logging(level="INFO"):
    """
    Setup basic logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
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
        session.connect(args.host, port=args.port, ssl=args.ssl)
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

    except Exception as e:
        print(f"Connection failed: {e}")
    finally:
        session.close()
        print("Disconnected.")


if __name__ == "__main__":
    main()


__all__ = ["Session", "AsyncSession", "enable_replacement", "setup_logging"]
