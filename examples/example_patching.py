#!/usr/bin/env python3
"""
Example: Demonstrating the patching process for p3270 integration.

This script shows how to apply pure3270 patches to p3270, verify the redirection,
and perform basic operations. Run in a venv with pure3270 and optionally p3270 installed.

For real usage, replace 'mock-host' with a valid TN3270 host (e.g., a test IBM mainframe).
If p3270 is not installed, it will simulate with mocks and log warnings.
"""

import logging
import sys

# Setup logging to see patching logs
from pure3270 import setup_logging
setup_logging(level='INFO')

# Enable the replacement patching
from pure3270 import enable_replacement
manager = enable_replacement(patch_sessions=True, patch_commands=True, strict_version=False)

try:
    # Import p3270 after patching
    import p3270
    print("p3270 imported successfully after patching.")
    
    # Create a session - this should use pure3270 under the hood
    session = p3270.Session()
    print("p3270.Session created - patching applied.")
    
    # Verify patching by checking if the session has a _pure_session attribute (from patch)
    if hasattr(session, '_pure_session'):
        print("Patching verified: _pure_session attribute present.")
    else:
        print("Warning: Patching may not have applied fully (check logs).")
    
    # Attempt a mock connection (will fail without real host, but demonstrates flow)
    try:
        session.connect('mock-host.example.com', port=23, ssl=False)
        # If successful (unlikely without real host), send and read
        session.send('key Enter')
        screen = session.read()
        print(f"Mock screen content: {screen[:100]}...")  # Truncate for display
    except Exception as e:
        print(f"Mock connection failed as expected (no real host): {e}")
        print("For real usage: Replace 'mock-host.example.com' with a valid TN3270 host.")
    
    # Close the session
    session.close()
    print("Session closed.")
    
except ImportError:
    print("p3270 not installed. Patching simulates with mocks (check logs for details).")
    print("Install with: pip install p3270")
    print("Patching still applied for when p3270 is available.")

print("Patching demonstration complete. Check logs above for patch application details.")