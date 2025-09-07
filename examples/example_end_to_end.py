#!/usr/bin/env python3
"""
Example: End-to-end usage of p3270 after pure3270 patching.

This script applies patching, then uses p3270.Session for a full session:
connect to a host, send input (e.g., key press and string), read screen output,
and close. Uses a mock host for demonstration; replace with real TN3270 server.

Requires: pure3270 and p3270 installed in venv. If p3270 absent, simulates.
Run: python examples/example_end_to_end.py
"""

import logging

# Setup logging
from pure3270 import setup_logging
setup_logging(level='INFO')

# Apply patching before importing p3270
from pure3270 import enable_replacement
manager = enable_replacement(patch_sessions=True, patch_commands=True, strict_version=False)

try:
    # Import p3270 after patching
    import p3270
    print("p3270 imported after patching. Proceeding with end-to-end session.")
    
    # Create session
    session = p3270.Session()
    
    # Mock connection (fails without real host, but shows flow)
    host = 'mock-tn3270-host.example.com'  # Replace with real host, e.g., 'tn3270.example.com'
    port = 23  # or 992 for SSL
    ssl = False  # Set True for secure connections
    
    try:
        session.connect(host, port=port, ssl=ssl)
        print(f"Connected to {host}:{port} (mock - in reality, would negotiate TN3270).")
        
        # Send a string input and key press (macro-like)
        session.send('String(Hello, World!)')  # Type into current field
        session.send('key Enter')  # Submit
        print("Sent input: 'Hello, World!' + Enter key.")
        
        # Read screen output
        screen_text = session.read()
        print("Screen content after input:")
        print(screen_text)
        print("(In real usage, this would show the host response in ASCII-translated EBCDIC.)")
        
    except Exception as e:
        print(f"Session operations failed (expected for mock host): {e}")
        print("For real end-to-end: Use a valid TN3270 host/port. Enable DEBUG logging for protocol traces.")
        print("Example real host: A test IBM z/OS system or emulator like x3270 simulator.")
    
    # Always close
    session.close()
    print("Session closed.")
    
except ImportError:
    print("p3270 not installed. Cannot demonstrate end-to-end with p3270.")
    print("Install: pip install p3270")
    print("Patching applied; use standalone example for pure3270 directly.")

print("End-to-end demonstration complete. Check logs for patching and session details.")