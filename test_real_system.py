#!/usr/bin/env python3
"""
Test script to connect to a real TN3270 system using pure3270.

This script is for testing purposes only and will not be added to git.
"""

import argparse
import os
import platform
import sys
import time

from dotenv import load_dotenv
from pure3270 import Session, setup_logging


def main():
    # Load environment variables from .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description="Test connection to a real TN3270 system")
    parser.add_argument("--host", help="Host to connect to")
    parser.add_argument("--port", type=int, default=23, help="Port to connect to (default: 23)")
    parser.add_argument("--ssl", action="store_true", help="Use SSL/TLS connection")
    parser.add_argument("--user", help="Username for login (optional)")
    parser.add_argument("--password", help="Password for login (optional)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Use environment variables as defaults if not provided via command line
    host = args.host or os.getenv("TN3270_HOST")
    user = args.user or os.getenv("TN3270_USERNAME")
    password = args.password or os.getenv("TN3270_PASSWORD")

    # Validate that we have a host
    if not host:
        print("Error: Host must be provided either via --host argument or TN3270_HOST environment variable")
        sys.exit(1)

    # Setup logging
    setup_logging(level="DEBUG" if args.debug else "INFO")

    # Import limits wrapper
    from tools.memory_limit import get_integration_limits, run_with_limits_sync

    int_time, int_mem = get_integration_limits()
    print(f"Running integration test with limits: {int_time}s / {int_mem}MB")

    def run_test():
        # Create session with SSL context if needed
        if args.ssl:
            import ssl
            ssl_context = ssl.create_default_context()
            session = Session(host=host, port=args.port, ssl_context=ssl_context)
        else:
            session = Session(host=host, port=args.port)

        try:
            print(f"Connecting to {host}:{args.port}...")

            # Connect to the host
            session.connect()
            print("Connected successfully!")
            print(f"Session connected: {session.connected}")

            # Read initial screen
            print("\n--- Initial Screen ---")
            screen_data = session.read()
            print(screen_data.decode('ascii', errors='ignore'))

            # If user and password provided, attempt login
            if user and password:
                print(f"\n--- Attempting login with {user} ---")
                # Send username
                session.send(f"String({user})".encode('ascii'))
                session.send(b"key Tab")  # Move to password field
                # Send password
                session.send(f"String({password})".encode('ascii'))
                session.send(b"key Enter")  # Submit

                # Wait a moment for response
                time.sleep(2)

                # Read post-login screen
                print("\n--- Post-Login Screen ---")
                screen_data = session.read()
                print(screen_data.decode('ascii', errors='ignore'))

            # Wait for user input before closing (only in interactive mode)
            if sys.stdin.isatty():
                input("\nPress Enter to close the session...")
            else:
                print("Non-interactive environment: closing session without prompt.")

            return True

        except Exception as e:
            print(f"Error: {e}")
            return False
        finally:
            # Always close the session
            try:
                session.close()
                print("Session closed.")
            except:
                pass

    success, result = run_with_limits_sync(run_test, int_time, int_mem)
    if not success:
        print(f"Test failed due to limits: {result}")
        sys.exit(1)
    if not result:
        print("Test failed (connection/login issues)")
        sys.exit(1)

    # Note: Limits applied to entire connection/login block via run_with_limits_sync.
    # Unix-only memory, cross-platform time. Defaults: 10s/200MB, env: INT_TIME_LIMIT, INT_MEM_LIMIT.


if __name__ == "__main__":
    main()
