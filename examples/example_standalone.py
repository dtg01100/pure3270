#!/usr/bin/env python3
"""
Example: Standalone usage of pure3270 Session without p3270.

This script uses pure3270 directly: create Session, connect to a TN3270 host,
send commands (e.g., string input and key press), read screen output, and close.
Uses a mock host for demonstration; replace with real for actual emulation.

Requires: pure3270 and telnetlib3 installed in venv. No p3270 needed.
Run: python examples/example_standalone.py

For real usage: Set a valid host (e.g., IBM mainframe emulator) and port.
Enable SSL for secure connections (port 992 typically).
"""

# Setup logging to see session events
from pure3270 import Session, setup_logging

setup_logging(level="INFO")

print("Starting standalone pure3270 session demonstration.")

# Create a standalone Session (configurable screen size)
session = Session(host="mock-tn3270-host.example.com", port=23)
print("pure3270.Session created successfully.")

# Define host and port variables for the print statement
host = "mock-tn3270-host.example.com"
port = 23

try:
    # Connect to the host
    session.connect()
    print(f"Connected to mock host (in reality, would handle TN3270 negotiation).")
    print(
        f"Connected to {host}:{port} (mock - in reality, would handle TN3270 negotiation)."
    )

    # Send commands: Type a string and press Enter
    session.send(b"String(User Login)")  # Simulate typing into a field
    session.send(b"key Enter")  # Submit the input
    print("Sent commands: 'String(User Login)' + 'key Enter'.")

    # Optionally, execute a macro sequence
    # session.macro(['String(password)', 'key PF3'])  # Uncomment for multi-step

    # Read the screen content (EBCDIC to ASCII translated)
    screen_text = session.read()
    print("Screen content after commands:")
    print(screen_text)
    print("(In real usage, this displays the 3270 screen scraped as text.)")

except Exception as e:
    print(f"Session operations failed (expected for mock host): {e}")
    print("For real standalone usage:")
    print("- Replace 'mock-tn3270-host.example.com' with a valid TN3270 server.")
    print("- Set ssl=True and port=992 for secure connections.")
    print("- Enable DEBUG logging: setup_logging('DEBUG') for protocol details.")
    print("- Test with a 3270 emulator or mainframe test system.")

finally:
    # Always close the session
    session.close()
    print("Session closed.")

print("Standalone demonstration complete. Pure3270 native implementation.")
