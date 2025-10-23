#!/usr/bin/env python3
"""
Example: Advanced Screen Buffer Operations and Field Manipulation

This example demonstrates advanced screen buffer operations including:
- Direct screen buffer manipulation
- Field detection and navigation
- EBCDIC/ASCII conversion
- Cursor positioning and text input
- Screen reading and parsing

Requires: pure3270 installed in venv.
Run: python examples/example_advanced_screen_operations.py
"""

import time
from typing import Any

from pure3270 import Session, setup_logging

# Setup logging to see what's happening
setup_logging(level="INFO")


def demo_screen_buffer_manipulation() -> None:
    """Demonstrate direct screen buffer operations."""
    print("=== Screen Buffer Manipulation Demo ===")

    with Session(terminal_type="IBM-3278-2") as session:
        print(f"Screen size: {session.screen_buffer.rows}x{session.screen_buffer.cols}")

        # Get screen buffer reference
        sb = session.screen_buffer

        # Write text directly to buffer at specific positions
        sb.write_char(ord("H"), row=5, col=10)
        sb.write_char(ord("e"), row=5, col=11)
        sb.write_char(ord("l"), row=5, col=12)
        sb.write_char(ord("l"), row=5, col=13)
        sb.write_char(ord("o"), row=5, col=14)

        # Read the text back
        text = ""
        for col in range(10, 15):
            char_code = sb.buffer[5 * sb.cols + col]
            text += chr(char_code)

        print(f"Text written to buffer: '{text}'")

        # Demonstrate buffer clearing
        sb.clear()
        print("Screen buffer cleared")


def demo_field_operations() -> None:
    """Demonstrate field detection and operations."""
    print("\n=== Field Operations Demo ===")

    with Session() as session:
        sb = session.screen_buffer

        # Create some fields programmatically (simulating host data)
        # In real usage, fields would come from the host system

        # Simulate unprotected field (input field)
        start_pos = 6 * sb.cols + 20  # Row 6, column 20
        field_length = 10

        # Mark field as unprotected (writable) - in EBCDIC
        sb.buffer[start_pos - 1] = 0x3C  # Start field attribute byte (<)
        for i in range(field_length):
            sb.buffer[start_pos + i] = 0x40  # Fill with spaces

        # Mark end of field
        sb.buffer[start_pos + field_length] = 0x3E  # End field attribute byte (>)

        print(f"Created field markers at row 6, col 20 with length {field_length}")
        print("Note: Field parsing requires TN3270 protocol data from host system")


def demo_text_input_and_navigation() -> None:
    """Demonstrate text input and cursor navigation."""
    print("\n=== Text Input and Navigation Demo ===")

    with Session() as session:
        sb = session.screen_buffer

        # Start at home position
        sb.set_position(0, 0)
        print(
            f"Cursor position: row={sb.get_position()[0]}, col={sb.get_position()[1]}"
        )

        # Move down to row 10
        for _ in range(10):
            row, col = sb.get_position()
            sb.set_position(row + 1, col)
        print(
            f"After moving down: row={sb.get_position()[0]}, col={sb.get_position()[1]}"
        )

        # Move right to column 30
        row, col = sb.get_position()
        sb.set_position(row, col + 30)
        print(
            f"After moving right: row={sb.get_position()[0]}, col={sb.get_position()[1]}"
        )

        # Input some text
        session.string("Hello World!")
        print("Entered text: 'Hello World!'")

        # Demonstrate tab navigation (simulated)
        row, col = sb.get_position()
        sb.set_position(row, col + 8)  # Simulate tab stop
        print(
            f"After simulated tab: row={sb.get_position()[0]}, col={sb.get_position()[1]}"
        )


def demo_ebcdic_ascii_conversion() -> None:
    """Demonstrate EBCDIC/ASCII conversions."""
    print("\n=== EBCDIC/ASCII Conversion Demo ===")

    with Session() as session:
        # ASCII to EBCDIC conversion
        ascii_text = "HELLO WORLD"
        ebcdic_bytes = session.ebcdic(ascii_text)
        print(f"ASCII '{ascii_text}' -> EBCDIC bytes: {ebcdic_bytes.hex()}")

        # EBCDIC to ASCII conversion
        ascii_converted = session.ascii(ebcdic_bytes)
        print(f"EBCDIC bytes -> ASCII '{ascii_converted}'")

        # Test some special characters
        special_ascii = "A@#§"
        ebcdic_special = session.ebcdic(special_ascii)
        ascii_back = session.ascii(ebcdic_special)
        print(
            f"Special chars: '{special_ascii}' -> {ebcdic_special.hex()} -> '{ascii_back}'"
        )


def demo_screen_reading() -> None:
    """Demonstrate various screen reading operations."""
    print("\n=== Screen Reading Demo ===")

    with Session(terminal_type="IBM-3278-3") as session:  # Wider screen
        sb = session.screen_buffer
        print(f"Screen dimensions: {sb.rows}x{sb.cols}")

        # Fill some content for demonstration
        content = "Welcome to pure3270 Terminal Emulation Demo!"
        row, col = 2, 5
        for i, char in enumerate(content):
            if col + i < sb.cols:
                sb.write_char(ord(char), row=row, col=col + i)

        # Different ways to read screen content
        full_screen = sb.to_text()
        print(f"Full screen text (first 200 chars): {repr(full_screen[:200])}")

        # Read specific line
        line_2 = ""
        for col in range(sb.cols):
            pos = 2 * sb.cols + col
            if pos < len(sb.buffer):
                char_code = sb.buffer[pos]
                if char_code != 0x40:  # Skip spaces for readability
                    line_2 += chr(char_code)

        print(f"Line 2 content: '{line_2}'")

        # Demonstrate screen area reading (rectangle)
        # Read rows 1-3, columns 0-40
        area_content = []
        for r in range(1, 4):
            row_text = ""
            for c in range(min(40, sb.cols)):
                pos = r * sb.cols + c
                if pos < len(sb.buffer):
                    char_code = sb.buffer[pos]
                    row_text += chr(char_code) if char_code != 0x40 else " "
            area_content.append(row_text.rstrip())

        print("Area content (rows 1-3, cols 0-40):")
        for i, line in enumerate(area_content):
            print("2d")


def demo_cursor_manipulation() -> None:
    """Demonstrate cursor positioning and manipulation."""
    print("\n=== Cursor Manipulation Demo ===")

    with Session() as session:
        sb = session.screen_buffer

        # Set cursor to various positions
        positions = [
            (0, 0),  # Home
            (5, 10),  # Middle of screen
            (sb.rows - 1, sb.cols - 1),  # Bottom right
            (10, 20),  # Specific location
        ]

        for row, col in positions:
            sb.set_position(row, col)
            current_row, current_col = sb.get_position()
            print(
                f"Set cursor to ({row}, {col}) - actual: ({current_row}, {current_col})"
            )

        # Demonstrate boundary checking
        sb.set_position(100, 200)  # Way out of bounds
        final_row, final_col = sb.get_position()
        print(f"Out of bounds set (100, 200) - clamped to: ({final_row}, {final_col})")


if __name__ == "__main__":
    print("Pure3270 Advanced Screen Operations Demo")
    print("=" * 50)

    try:
        demo_screen_buffer_manipulation()
        demo_field_operations()
        demo_text_input_and_navigation()
        demo_ebcdic_ascii_conversion()
        demo_screen_reading()
        demo_cursor_manipulation()

        print("\n=== Demo Complete ===")
        print("All screen buffer and field operations demonstrated successfully!")

    except Exception as e:
        print(f"Demo failed: {e}")
        print("This demo uses offline screen buffer manipulation.")
        print("For live TN3270 host interaction, replace with real host connection.")
