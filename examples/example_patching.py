#!/usr/bin/env python3
"""
Example: Demonstrating the patching process for p3270 integration.

This script shows how to apply pure3270 patches to p3270, verify the redirection,
and perform basic operations. Run in a venv with pure3270 and optionally p3270 installed.

For real usage, replace 'mock-host' with a valid TN3270 host (e.g., a test IBM mainframe).
If p3270 is not installed, it will simulate with mocks and log warnings.
"""

import logging
import time
import argparse
import asyncio
from pure3270.protocol.tn3270_handler import TN3270Handler

# Setup logging to see patching logs
from pure3270 import setup_logging
setup_logging(level='DEBUG')

parser = argparse.ArgumentParser(
    description='Patching demonstration for pure3270 with p3270.'
)
parser.add_argument('--host', default='localhost', help='Host to connect to')
parser.add_argument('--port', type=int, default=23, help='Port to connect to')
parser.add_argument('--user', default='guest', help='Username for login')
parser.add_argument(
    '--password', default='guest', help='Password for login'
)
parser.add_argument('--ssl', action='store_true', default=False, help='Use SSL connection')
args = parser.parse_args()

# Enable the replacement patching
from pure3270 import enable_replacement
manager = enable_replacement(
    patch_sessions=True, patch_commands=True, strict_version=False
)

try:
    # Import p3270 after patching
    import p3270
    print("p3270 imported successfully after patching.")
    
    # Create a client - this should use pure3270 under the hood
    session = p3270.P3270Client()
    print("p3270.P3270Client created - patching applied.")
    
    # Verify patching by checking if the session has a _pure_session attribute (from patch)
    if hasattr(session, '_pure_session'):
        print("Patching verified: _pure_session attribute present.")
    else:
        print("Warning: Patching may not have applied fully (check logs).")

    # Temporarily patch TN3270Handler.connect to export initial login screen
    from pure3270.protocol.tn3270_handler import TN3270Handler
    logger = logging.getLogger("pure3270.protocol.tn3270_handler")

    async def patched_connect(self):
        try:
            if self.ssl_context:
                self.reader, self.writer = await asyncio.open_connection(
                    self.host, self.port, ssl=self.ssl_context
                )
            else:
                self.reader, self.writer = await asyncio.open_connection(
                    self.host, self.port
                )
            wont_environ = b'\xff\xfc\x27'  # IAC WONT ENVIRON
            self.writer.write(wont_environ)
            await self.writer.drain()
            # Read and capture initial response (login screen)
            try:
                initial_data = await asyncio.wait_for(self.reader.read(1024), timeout=1.0)
                screen_text = initial_data.decode('ascii', errors='ignore')
                print(
                    f"Initial login screen content (first 200 chars): "
                    f"{screen_text[:200]}"
                )
                logger.info(f"Initial data captured")
            except asyncio.TimeoutError:
                print("No initial data received within timeout")
            logger.info(f"Connected to {self.host}:{self.port}")
            # Proceed with negotiation
            await self._negotiate_tn3270()
            # Capture post-negotiation screen for debugging
            try:
                post_data = await asyncio.wait_for(self.reader.read(1024), timeout=1.0)
                post_text = post_data.decode('ascii', errors='ignore')
                print(
                    f"Post-negotiation content (first 200 chars): "
                    f"{post_text[:200]}"
                )
                logger.info(f"Post-negotiation data captured")
            except asyncio.TimeoutError:
                print("No post-negotiation data received within timeout")
        except Exception as e:
            logger.error(f"Handler connection failed: {e}")
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}")

    # Apply the patch to the class
    TN3270Handler.connect = patched_connect
    
    # Attempt a mock connection (will fail without real host, but demonstrates flow)
    try:
        # Test connection with parameters
        session.connect(args.host, port=args.port, ssl=args.ssl)
        # Perform login with test credentials
        session.send(args.user)
        session.send('key Enter')
        session.send(args.password)
        session.send('key Enter')
        time.sleep(2)
        screen = session.read()
        print(f"Screen after login attempt: {screen[:200]}...")
    except Exception as e:
        print(f"Connection or login failed: {e}")
    
    # Close the session
    if hasattr(session, '_pure_session'):
        session._pure_session.close()
        print("Session closed via pure_session.")
    else:
        print("Session close skipped (no _pure_session).")
    
except ImportError:
    print("p3270 not installed. Patching simulates with mocks (check logs for details).")
    print("Install with: pip install p3270")
    print("Patching still applied for when p3270 is available.")

print("Patching demonstration complete. Check logs above for patch application details.")
