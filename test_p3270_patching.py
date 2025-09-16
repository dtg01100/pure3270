#!/usr/bin/env python3
"""
Test script to connect to a real TN3270 system using p3270 with pure3270 patching.

This script is for testing purposes only and will not be added to git.
"""

import argparse
import os
import platform
import sys
import time

from dotenv import load_dotenv
from pure3270 import enable_replacement, setup_logging


def main():
    # Load environment variables from .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description="Test connection to a real TN3270 system using p3270 with pure3270 patching")
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

    # Apply patching before importing p3270
    print("Applying pure3270 patching to p3270...")
    enable_replacement(patch_sessions=True, patch_commands=True, strict_version=False)

    # Import p3270 after patching
    import p3270

    print(f"Connecting to {host}:{args.port}...")

    try:
        # Create session
        client = p3270.P3270Client()

        # For p3270, we need to construct the connection string properly
        # Format: Connect(B:host) or Connect(B:host:port)
        connection_string = host
        if args.port != 23:
            connection_string = f"{host}:{args.port}"

        # Connect to the host using the proper s3270 command format
        connected = False
        try:
            # Try the direct connection method first
            client.s3270.Run(f"Connect(B:{connection_string})")
            connected = True
        except Exception as e:
            print(f"Direct connection failed: {e}")
            # Fall back to setting properties and connecting
            try:
                client.hostName = host
                client.hostPort = args.port
                connected = client.connect()
            except Exception as e2:
                print(f"Fallback connection failed: {e2}")

        if not connected:
            print("Failed to connect to the host")
            sys.exit(1)

        print("Connected successfully!")

        # Read initial screen
        print("\n--- Initial Screen ---")
        screen_text = client.getScreen()
        print(screen_text)

        # If user and password provided, attempt login
        if user and password:
            print(f"\n--- Attempting login with {user} ---")
            # Send username
            client.sendText(user)
            client.sendEnter()
            time.sleep(1)

            # Send password
            client.sendText(password)
            client.sendEnter()

            # Wait a moment for response
            time.sleep(2)

            # Read post-login screen
            print("\n--- Post-Login Screen ---")
            screen_text = client.getScreen()
            print(screen_text)

        # Wait for user input before closing (only in interactive mode)
        if sys.stdin.isatty():
            input("\nPress Enter to close the session...")
        else:
            print("Non-interactive environment: closing session without prompt.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Always close the session
        try:
            client.disconnect()
            print("Session closed.")
        except:
            pass


if __name__ == "__main__":
    main()
