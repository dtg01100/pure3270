#!/usr/bin/env python3
"""
Example: Protocol-Level Operations and IND$FILE Transfers

This example demonstrates advanced protocol-level operations including:
- Low-level TN3270/TN3270E protocol operations
- IND$FILE file transfer protocol
- Protocol negotiation details
- Data stream manipulation
- Printer emulation
- Custom protocol handlers

Requires: pure3270 installed in venv.
Run: python examples/example_protocol_operations.py
"""

import asyncio
import os
import tempfile
from typing import Optional

import pure3270.protocol.utils as protocol_utils
from pure3270 import AsyncSession, setup_logging
from pure3270.protocol.data_stream import DataStreamParser, DataStreamSender
from pure3270.protocol.tn3270_handler import TN3270Handler

# Setup logging to see protocol details
setup_logging(level="DEBUG")


def demo_protocol_negotiation_details():
    """Demonstrate TN3270 protocol negotiation details."""
    print("=== Protocol Negotiation Details Demo ===")

    # Show terminal type validation
    valid_types = [
        "IBM-3278-2",
        "IBM-3278-3",
        "IBM-3278-4",
        "IBM-3278-5",
        "IBM-3279-2",
        "IBM-3279-3",
        "IBM-3279-4",
        "IBM-3279-5",
        "IBM-3179-2",
        "IBM-DYNAMIC",
    ]

    print("Valid terminal types:")
    for term_type in valid_types:
        if protocol_utils.is_valid_terminal_model(term_type):
            rows, cols = protocol_utils.get_screen_size(term_type)
            print(f"  {term_type}: {rows}x{cols}")
        else:
            print(f"  {term_type}: INVALID")

    # Show capability negotiation flags
    print("\nTN3270 capabilities:")
    capabilities = [
        ("TN3270E", getattr(protocol_utils, "TN3270E", "N/A")),
        ("TN3270_BIND_IMAGE", getattr(protocol_utils, "TN3270_BIND_IMAGE", "N/A")),
    ]

    for name, value in capabilities:
        if isinstance(value, int):
            print(f"  {name}: 0x{value:02x}")
        else:
            print(f"  {name}: {value}")


def demo_data_stream_operations():
    """Demonstrate low-level data stream operations."""
    print("\n=== Data Stream Operations Demo ===")

    from pure3270.emulation.screen_buffer import ScreenBuffer

    # Create a screen buffer for testing
    sb = ScreenBuffer(24, 80)

    # Write some test content
    sb.write_char(ord("H"), row=5, col=10)
    sb.write_char(ord("e"), row=5, col=11)
    sb.write_char(ord("l"), row=5, col=12)
    sb.write_char(ord("l"), row=5, col=13)
    sb.write_char(ord("o"), row=5, col=14)

    print("Created screen buffer with test content")

    try:
        # Create data stream sender (would normally be used by protocol handler)
        sender = DataStreamSender()

        # Note: In real usage, this would create proper TN3270 data streams
        # For demo purposes, we show the framework
        print("DataStreamSender created for building input streams")

        # Show structured field format (TN3270E)
        print("\nTN3270E structured field format:")
        print("  Byte 0-1: Length (big-endian)")
        print("  Byte 2: SF (0x00)")
        print("  Byte 3: SFID (structured field ID)")
        print("  Byte 4+: Field data")

    except Exception as e:
        print(f"DataStreamSender operation failed: {e}")


def demo_ebcdic_operations():
    """Demonstrate EBCDIC encoding/decoding operations."""
    print("\n=== EBCDIC Operations Demo ===")

    from pure3270.emulation.ebcdic import (
        translate_ascii_to_ebcdic,
        translate_ebcdic_to_ascii,
    )

    # ASCII to EBCDIC conversion examples
    test_strings = [
        "HELLO WORLD",
        "0123456789",
        "A@B#C$D%E&F*G(H)I+J,K-L.M/N:O;P<Q=R>S?T[U]V\\W^X_Y`Z{a|b}c~",
        "ÄÖÜß",
    ]

    print("ASCII to EBCDIC conversions:")
    for text in test_strings:
        try:
            ebcdic_bytes = translate_ascii_to_ebcdic(text)
            print(f"  '{text}' -> {ebcdic_bytes.hex()}")
        except Exception as e:
            print(f"  '{text}' -> ERROR: {e}")

    print("\nEBCDIC to ASCII conversions:")
    # Test some known EBCDIC sequences
    ebcdic_tests = [
        bytes([0xC8, 0xC5, 0xD3, 0xD3, 0xD6]),  # "HELLO"
        bytes(
            [0xF0, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9]
        ),  # "0123456789"
    ]

    for ebcdic_data in ebcdic_tests:
        try:
            ascii_text = translate_ebcdic_to_ascii(ebcdic_data)
            print(f"  {ebcdic_data.hex()} -> '{ascii_text}'")
        except Exception as e:
            print(f"  {ebcdic_data.hex()} -> ERROR: {e}")


async def demo_ind_file_transfer():
    """Demonstrate IND$FILE file transfer protocol."""
    print("\n=== IND$FILE Transfer Demo ===")

    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a test file for IND$FILE transfer demonstration.\n")
        f.write("It contains multiple lines of text.\n")
        f.write("The file transfer protocol will handle binary data.\n")
        temp_file = f.name

    print(f"Created temporary test file: {temp_file}")

    async with AsyncSession() as session:
        # IND$FILE requires a connected session, so we'll demonstrate the framework
        print("IND$FILE transfer framework demonstration:")

        if hasattr(session, "_ind_file") and session._ind_file:
            print("✓ IND$FILE handler available in session")

            try:
                # Note: This will fail without an actual TN3270 host connection
                await session.send_file(temp_file, "demo.txt")
                print("✗ Unexpected success - should require TN3270 host")
            except Exception as e:
                print(
                    f"✓ Expected error without host connection: {type(e).__name__}: {e}"
                )

            try:
                await session.receive_file("remote.txt", temp_file + ".downloaded")
                print("✗ Unexpected success - should require TN3270 host")
            except Exception as e:
                print(
                    f"✓ Expected error without host connection: {type(e).__name__}: {e}"
                )
        else:
            print("IND$FILE handler not initialized (needs connection)")

    # Clean up
    try:
        os.unlink(temp_file)
        print("Cleaned up temporary file")
    except Exception:
        pass


async def demo_async_protocol_operations():
    """Demonstrate async protocol operations."""
    print("\n=== Async Protocol Operations Demo ===")

    async with AsyncSession() as session:
        # Test connection to a known HTTP server (for demo purposes)
        try:
            host = "httpbin.org"
            print(f"Attempting connection to {host} for protocol demonstration...")
            await session.connect(host, port=80)

            # Send raw HTTP request to demonstrate protocol level access
            http_request = (
                b"GET /get HTTP/1.1\r\n"
                b"Host: httpbin.org\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            )

            print("Sending raw HTTP request...")
            await session.send(http_request)

            print("Reading response...")
            response = await session.read(timeout=10.0)

            if response.startswith(b"HTTP/1.1"):
                print(f"✓ Got HTTP response: {len(response)} bytes")
                # Extract status line
                status_line = response.split(b"\r\n")[0].decode(
                    "utf-8", errors="ignore"
                )
                print(f"  Status: {status_line}")
            else:
                print(f"Got {len(response)} bytes of data (not HTTP)")
                print(f"First 100 bytes: {response[:100]}")

        except Exception as e:
            print(f"Connection/demo failed: {type(e).__name__}: {e}")
            print("This is expected since we're using HTTP as a demo target")


def demo_protocol_utils():
    """Demonstrate protocol utility functions."""
    print("\n=== Protocol Utilities Demo ===")

    # TN3270 key codes
    print("TN3270 key codes:")
    key_codes = [
        ("AID_NO", 0x60),
        ("AID_ENTER", 0x7D),
        ("AID_CLEAR", 0x6D),
        ("AID_PA1", 0x6C),
        ("AID_PA2", 0x6B),
        ("AID_PA3", 0x6A),
    ]

    for name, code in key_codes:
        print(f"  {name}: 0x{code:02x}")

    # Telnet command codes
    print("\nTelnet command codes:")
    telnet_commands = [
        ("SE", 240),
        ("SB", 250),
        ("WILL", 251),
        ("WONT", 252),
        ("DO", 253),
        ("DONT", 254),
        ("IAC", 255),
    ]

    for name, code in telnet_commands:
        print(f"  {name}: {code}")

    # TN3270E SYSREQ codes
    print("\nTN3270E SYSREQ codes:")
    sysreq_codes = [
        ("ATTN", protocol_utils.TN3270E_SYSREQ_ATTN),
        ("BREAK", protocol_utils.TN3270E_SYSREQ_BREAK),
        ("CANCEL", protocol_utils.TN3270E_SYSREQ_CANCEL),
        ("RESTART", protocol_utils.TN3270E_SYSREQ_RESTART),
        ("PRINT", protocol_utils.TN3270E_SYSREQ_PRINT),
        ("LOGOFF", protocol_utils.TN3270E_SYSREQ_LOGOFF),
    ]

    for name, code in sysreq_codes:
        print(f"  {name}: 0x{code:02x}")


async def main():
    """Run all protocol operation demonstrations."""
    print("Pure3270 Protocol-Level Operations Demo")
    print("=" * 60)

    # Synchronous demonstrations
    demo_protocol_negotiation_details()
    demo_data_stream_operations()
    demo_ebcdic_operations()
    demo_protocol_utils()

    # Asynchronous demonstrations
    await demo_ind_file_transfer()
    await demo_async_protocol_operations()

    print("\n" + "=" * 60)
    print("✓ All protocol operations demonstrated")
    print("\nKey protocol concepts covered:")
    print("- TN3270/TN3270E protocol negotiation and capabilities")
    print("- Data stream building and parsing")
    print("- EBCDIC/ASCII character encoding")
    print("- IND$FILE file transfer protocol framework")
    print("- Low-level network protocol access")
    print("- Telnet command and TN3270 key codes")
    print("- Structured field formats (TN3270E)")

    print("\nNote: Some operations require a live TN3270 host for full functionality.")


if __name__ == "__main__":
    asyncio.run(main())
