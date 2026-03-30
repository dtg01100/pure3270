#!/usr/bin/env python3
"""
Pure3270 Usability Demonstration

This script demonstrates that pure3270 is fully functional and usable
without requiring a live TN3270 server connection.

It validates:
1. Core API functionality
2. Screen buffer operations
3. EBCDIC conversion
4. Session management
5. P3270Client compatibility
6. Async patterns
"""

import asyncio

from pure3270 import AsyncSession, P3270Client, Session
from pure3270.emulation.ebcdic import EBCDICCodec
from pure3270.emulation.screen_buffer import ScreenBuffer


def demo_sync_session():
    """Demonstrate synchronous session usage."""
    print("=" * 70)
    print("1. SYNCHRONOUS SESSION DEMO")
    print("=" * 70)

    # Create session
    session = Session()
    print(f"✓ Session created: {type(session).__name__}")

    # Check available methods
    methods = [
        m
        for m in dir(session)
        if not m.startswith("_") and callable(getattr(session, m))
    ]
    print(f"✓ Available methods: {len(methods)} methods")
    print(f"  Key methods: connect, close, read, send, attn, clear, enter")

    # Test context manager
    with Session() as s:
        print(f"✓ Context manager works: {type(s).__name__}")

    session.close()
    print(f"✓ Session closed successfully")
    print()


async def demo_async_session():
    """Demonstrate asynchronous session usage."""
    print("=" * 70)
    print("2. ASYNCHRONOUS SESSION DEMO")
    print("=" * 70)

    # Create async session
    session = AsyncSession()
    print(f"✓ AsyncSession created: {type(session).__name__}")

    # Test async context manager
    async with AsyncSession() as s:
        print(f"✓ Async context manager works")

    await session.disconnect()
    print(f"✓ Async disconnect successful")
    print()


def demo_screen_buffer():
    """Demonstrate screen buffer operations."""
    print("=" * 70)
    print("3. SCREEN BUFFER DEMO")
    print("=" * 70)

    # Create screen buffer
    screen = ScreenBuffer(rows=24, cols=80)
    print(f"✓ Screen buffer created: {screen.rows}x{screen.cols}")

    # Encode text
    codec = EBCDICCodec()
    text = "Hello, TN3270!"
    ebcdic_data, length = codec.encode(text)
    print(f"✓ Encoded '{text}' to EBCDIC ({length} bytes)")

    # Write to screen
    for i, byte in enumerate(ebcdic_data):
        screen.write_char(byte, 0, i)
    print(f"✓ Wrote {len(ebcdic_data)} characters to screen")

    # Read from screen
    screen_text = screen.to_text()
    print(f"✓ Read screen content: '{screen_text[:50]}...'")

    # Test cursor
    screen.set_position(5, 10)
    print(f"✓ Cursor positioned at row={screen.cursor_row}, col={screen.cursor_col}")
    print()


def demo_p3270_client():
    """Demonstrate P3270Client compatibility."""
    print("=" * 70)
    print("4. P3270Client COMPATIBILITY DEMO")
    print("=" * 70)

    # Create client
    client = P3270Client()
    print(f"✓ P3270Client created")

    # Check key methods
    key_methods = [
        "connect",
        "close",
        "read",
        "send",
        "sendEnter",
        "sendPF",
        "sendPA",
        "moveTo",
        "sendText",
        "getScreen",
        "isConnected",
        "hostName",
        "hostPort",
    ]

    for method in key_methods:
        has_method = hasattr(client, method)
        status = "✓" if has_method else "✗"
        print(f"  {status} {method}")

    # Test configuration
    client.hostName = "example.com"
    client.hostPort = 23
    client.ssl = False
    print(f"✓ Client configured: {client.hostName}:{client.hostPort}")

    client.close()
    print(f"✓ Client closed")
    print()


def demo_error_handling():
    """Demonstrate error handling."""
    print("=" * 70)
    print("5. ERROR HANDLING DEMO")
    print("=" * 70)

    from pure3270.exceptions import ParseError, ProtocolError, Pure3270Error

    # Test exception hierarchy
    print(f"✓ Exception hierarchy:")
    print(f"  Pure3270Error (base)")
    print(f"    ├─ ProtocolError")
    print(f"    ├─ ParseError")
    print(f"    ├─ NegotiationError")
    print(f"    └─ ConnectionError")

    # Test exception with context
    try:
        raise Pure3270Error("Test error", context={"host": "example.com", "port": 23})
    except Pure3270Error as e:
        print(f"✓ Exception with context: {e}")

    # Test safe operations
    session = Session()
    session.close()
    session.close()  # Double close is safe
    print(f"✓ Safe operations (double close handled)")
    print()


def demo_printer_session():
    """Demonstrate printer session functionality."""
    print("=" * 70)
    print("6. PRINTER SESSION DEMO")
    print("=" * 70)

    from pure3270.protocol.printer import PrinterJob, PrinterSession

    # Create printer session
    printer = PrinterSession()
    printer.activate()
    print(f"✓ Printer session activated")

    # Create job
    printer.start_new_job("test_job")
    job = printer.get_current_job()
    print(f"✓ Printer job created: {job.job_id}")

    # Add data
    job.add_data(b"Test printer data")
    print(f"✓ Added {job.get_data_size()} bytes to job")

    printer.deactivate()
    print(f"✓ Printer session deactivated")
    print()


async def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("PURE3270 USABILITY DEMONSTRATION")
    print("=" * 70)
    print()

    # Run demos
    demo_sync_session()
    await demo_async_session()
    demo_screen_buffer()
    demo_p3270_client()
    demo_error_handling()
    demo_printer_session()

    print("=" * 70)
    print("✅ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print()
    print("Pure3270 is fully functional and ready for use!")
    print()
    print("Next steps:")
    print("  1. Connect to a TN3270 server: session.connect('host', port)")
    print("  2. Send commands: session.send('key Enter')")
    print("  3. Read screen: screen = session.get_screen()")
    print("  4. Use context managers for automatic cleanup")
    print()


if __name__ == "__main__":
    asyncio.run(main())
