#!/usr/bin/env python3
"""
Example: End-to-end usage of native P3270Client.

This script uses pure3270's native P3270Client for a full session:
connect to a host, send input (e.g., key press and string), read screen output,
and close. Uses a mock host for demonstration; replace with real TN3270 server.

Requires: pure3270 installed in venv.
Run: python examples/example_end_to_end.py
"""

import argparse
import time

# Setup logging
from pure3270 import setup_logging

setup_logging(level="DEBUG")

parser = argparse.ArgumentParser(
    description="End-to-end example for pure3270 native P3270Client."
)
parser.add_argument("--host", default="localhost", help="Host to connect to")
parser.add_argument("--port", type=int, default=23, help="Port to connect to")
parser.add_argument("--user", default="guest", help="Username for login")
parser.add_argument("--password", default="guest", help="Password for login")
parser.add_argument(
    "--ssl", action="store_true", default=False, help="Use SSL connection"
)
args = parser.parse_args()

# Use native P3270Client - no patching needed
from pure3270 import P3270Client

print("Using pure3270 native P3270Client. Proceeding with end-to-end session.")

# Create session
session = P3270Client()
print("P3270Client created - native implementation.")

try:
    session.hostName = args.host
    session.hostPort = args.port
    session.ssl = args.ssl
    session.connect()
    print(f"Connected to {args.host}:{args.port}.")
    session.send("key Clear")
    print("Sent 'key Clear' to trigger login screen.")
    time.sleep(1)

    initial_screen = session.read()
    print("Login screen:")
    print(initial_screen)
    session.send(args.user)
    session.send("key Tab")  # Move to next field
    session.send(args.password)
    print(f"Sent login credentials: '{args.user}' + 'key Tab' + " f"'{args.password}'.")
    session.send("key Enter")  # Submit
    print("Sent 'key Enter' to submit login.")
    time.sleep(1)

    # Read post-signin screen
    post_signin_screen = session.read()
    print("Post-signin screen:")
    print(post_signin_screen)
    time.sleep(1)

    session.send("signoff")  # Sign out
    session.send("key Enter")
    print("Sent 'signoff' + 'key Enter'.")
    time.sleep(1)

    post_signout_screen = session.read()
    print("Post-signout screen:")
    print(post_signout_screen)

except Exception as e:
    print(f"Session operations failed: {e}")
    print("Check DEBUG logs for details.")

finally:
    # Always close
    session.close()
    print("Session closed.")

print("End-to-end verification complete. Check logs for details.")
