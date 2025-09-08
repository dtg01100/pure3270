#!/usr/bin/env python3
"""
Example: End-to-end usage of p3270 after pure3270 patching.

This script applies patching, then uses p3270.Session for a full session:
connect to a host, send input (e.g., key press and string), read screen output,
and close. Uses a mock host for demonstration; replace with real TN3270 server.

Requires: pure3270 and p3270 installed in venv. If p3270 absent, simulates.
Run: python examples/example_end_to_end.py
"""

import argparse

import time

# Setup logging
from pure3270 import setup_logging
setup_logging(level='DEBUG')

parser = argparse.ArgumentParser(
    description='End-to-end example for pure3270 with p3270 patching.'
)
parser.add_argument('--host', default='localhost', help='Host to connect to')
parser.add_argument('--port', type=int, default=23, help='Port to connect to')
parser.add_argument('--user', default='guest', help='Username for login')
parser.add_argument(
    '--password', default='guest', help='Password for login'
)
parser.add_argument('--ssl', action='store_true', default=False, help='Use SSL connection')
args = parser.parse_args()

# Apply patching before importing p3270
from pure3270 import enable_replacement
manager = enable_replacement(
    patch_sessions=True, patch_commands=True, strict_version=False
)

try:
    # Import p3270 after patching
    import p3270
    print("p3270 imported after patching. Proceeding with end-to-end session.")

    # Create session
    session = p3270.P3270Client()
    print("p3270.P3270Client created - patching applied.")

    try:
        session.connect(args.host, port=args.port, ssl=args.ssl)
        print(f"Connected to {args.host}:{args.port}.")
        session.send('key Clear')
        print("Sent 'key Clear' to trigger login screen.")
        time.sleep(1)


        initial_screen = session.read()
        print("Login screen:")
        print(initial_screen)
        session.send(args.user)
        session.send('key Tab')  # Move to next field
        session.send(args.password)
        print(
            f"Sent login credentials: '{args.user}' + 'key Tab' + "
            f"'{args.password}'."
        )
        session.send('key Enter')  # Submit
        print("Sent 'key Enter' to submit login.")
        time.sleep(1)


        # Read post-signin screen
        post_signin_screen = session.read()
        print("Post-signin screen:")
        print(post_signin_screen)
        time.sleep(1)

        session.send('signoff')  # Sign out
        session.send('key Enter')
        print("Sent 'signoff' + 'key Enter'.")
        time.sleep(1)

        post_signout_screen = session.read()
        print("Post-signout screen:")
        print(post_signout_screen)

    except Exception as e:
        print(f"Session operations failed: {e}")
        print("Check DEBUG logs for details.")

    # Always close
    session.close()
    print("Session closed.")

except ImportError:
    print("p3270 not installed. Cannot demonstrate end-to-end with p3270.")
    print("Install: pip install p3270")
    print("Patching applied; use standalone example for pure3270 directly.")

print("End-to-end verification complete. Check logs for details.")
