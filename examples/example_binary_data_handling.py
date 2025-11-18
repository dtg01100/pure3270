#!/usr/bin/env python3
"""
Example: Binary Data and EBCDIC Handling

This example demonstrates binary data handling patterns in pure3270:
- EBCDIC/ASCII character encoding conversions
- Binary file transfer operations
- Binary data stream processing
- Handling mixed text/binary content
- Character set detection and conversion
- Binary data validation and sanitization

Requires: pure3270 installed in venv.
Run: python examples/example_binary_data_handling.py
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pure3270 import AsyncSession, Session, setup_logging
from pure3270.emulation.ebcdic import (
    EBCDICCodec,
    translate_ascii_to_ebcdic,
    translate_ebcdic_to_ascii,
)
from pure3270.protocol.utils import get_screen_size, is_valid_terminal_model

# Setup logging to see data handling details
setup_logging(level="INFO")


def demo_character_encoding():
    """Demonstrate EBCDIC/ASCII character encoding."""
    print("=== Character Encoding Demo ===")

    # Initialize EBCDIC codec
    ebcdic_codec = EBCDICCodec()

    # Test strings with various characters
    test_strings = [
        "HELLO WORLD",
        "Hello World 123",
        "A@B#C$D%E&F*G(H)I",
        "ÄÖÜß",  # German umlauts
        "¡Hola! ¿Cómo estás?",  # Spanish with inverted punctuation
        "café résumé naïve",  # French with accents
    ]

    print("ASCII to EBCDIC conversions:")
    for text in test_strings:
        try:
            ebcdic_result = ebcdic_codec.encode(text)
            ebcdic_bytes, length = ebcdic_result
            print(f"  '{text}' -> {ebcdic_bytes.hex()} (length: {length})")

            # Verify round-trip conversion
            back_to_ascii = ebcdic_codec.decode(ebcdic_bytes)
            match = "✓" if back_to_ascii == text else "✗"
            print(f"    Round-trip: {match} '{back_to_ascii}'")

        except Exception as e:
            print(f"  '{text}' -> ERROR: {e}")

    print("\nEBCDIC to ASCII conversions:")
    # Some known EBCDIC byte sequences
    ebcdic_samples = [
        bytes([0xC8, 0xC5, 0xD3, 0xD3, 0xD6]),  # "HELLO"
        bytes([0xE6, 0xD6, 0xE5, 0xD3, 0xC4]),  # "WORLD"
        bytes([0xF1, 0xF2, 0xF3, 0xF4, 0xF5]),  # "12345"
        bytes([0x4B, 0x4C, 0x4D, 0x4E, 0x4F]),  # "«»¬­®" (special chars)
    ]

    for ebcdic_data in ebcdic_samples:
        try:
            ascii_text = ebcdic_codec.decode(ebcdic_data)
            print(f"  {ebcdic_data.hex()} -> '{ascii_text}'")
        except Exception as e:
            print(f"  {ebcdic_data.hex()} -> ERROR: {e}")


def demo_binary_file_operations():
    """Demonstrate binary file operations."""
    print("\n=== Binary File Operations Demo ===")

    # Create test files with different content types
    test_files = {}

    with tempfile.TemporaryDirectory() as temp_dir:
        # Text file
        text_file = Path(temp_dir) / "text_data.txt"
        text_content = (
            "This is a text file with various characters: äöüß\nLine 2: ¡Hola!\n"
        )
        text_file.write_text(text_content, encoding="utf-8")
        test_files["text"] = text_file

        # Binary file (simulate IBM mainframe data)
        binary_file = Path(temp_dir) / "binary_data.bin"
        # Create binary data that looks like EBCDIC with some binary content
        ebcdic_header = translate_ascii_to_ebcdic("HEADER:")
        binary_payload = bytes([0x00, 0x01, 0x02, 0xFF, 0xFE, 0xFD])  # Binary data
        ebcdic_footer = translate_ascii_to_ebcdic(":END")
        binary_content = ebcdic_header + binary_payload + ebcdic_footer
        binary_file.write_bytes(binary_content)
        test_files["binary"] = binary_file

        # Mixed content file
        mixed_file = Path(temp_dir) / "mixed_data.dat"
        mixed_content = (
            b"EBCDIC_START:"
            + translate_ascii_to_ebcdic("Mixed content file")
            + b"\x00\x01\x02"  # Binary markers
            + "ASCII text here".encode("ascii")
            + b"\x03\x04\x05"  # More binary
            + translate_ascii_to_ebcdic(":EBCDIC_END")
        )
        mixed_file.write_bytes(mixed_content)
        test_files["mixed"] = mixed_file

        print("Created test files:")
        for file_type, file_path in test_files.items():
            size = file_path.stat().st_size
            print(f"  {file_type}: {file_path.name} ({size} bytes)")

        # Demonstrate file reading with different encodings
        for file_type, file_path in test_files.items():
            print(f"\nProcessing {file_type} file:")

            # Read as binary
            binary_data = file_path.read_bytes()
            print(f"  Binary: {binary_data.hex()[:100]}...")

            # Try different decoding approaches
            if file_type == "text":
                # Text file - try UTF-8
                try:
                    text_content = file_path.read_text(encoding="utf-8")
                    print(f"  UTF-8: {repr(text_content[:50])}")
                except Exception as e:
                    print(f"  UTF-8 decode failed: {e}")

            elif file_type == "binary":
                # Binary file - try EBCDIC decoding
                try:
                    ascii_content = translate_ebcdic_to_ascii(binary_data)
                    print(f"  EBCDIC: {repr(ascii_content)}")
                except Exception as e:
                    print(f"  EBCDIC decode failed: {e}")

            elif file_type == "mixed":
                # Mixed file - need intelligent parsing
                print("  Mixed content analysis:")
                _analyze_mixed_content(binary_data)


def _analyze_mixed_content(data: bytes):
    """Analyze mixed binary/EBCDIC content."""
    print(f"    Total size: {len(data)} bytes")

    # Look for EBCDIC text segments
    ebcdic_segments = []
    i = 0
    while i < len(data):
        # Try to decode segments as EBCDIC
        segment_start = i
        segment_data = bytearray()

        while i < len(data):
            byte_val = data[i]
            # Check if it's a printable EBCDIC character (rough heuristic)
            if 0x40 <= byte_val <= 0xFE and byte_val not in [0xFF]:
                segment_data.append(byte_val)
                i += 1
            else:
                break

        if len(segment_data) >= 3:  # Minimum segment length
            try:
                text = translate_ebcdic_to_ascii(bytes(segment_data))
                ebcdic_segments.append((segment_start, text))
            except:
                pass
        else:
            i += 1

    print(f"    Found {len(ebcdic_segments)} EBCDIC text segments:")
    for start, text in ebcdic_segments:
        print(f"      Offset {start}: '{text}'")

    # Look for binary patterns
    binary_patterns = []
    i = 0
    while i < len(data):
        if data[i] < 0x40:  # Non-printable bytes
            pattern_start = i
            while i < len(data) and data[i] < 0x40:
                i += 1
            pattern_length = i - pattern_start
            if pattern_length >= 2:
                binary_patterns.append((pattern_start, pattern_length))
        else:
            i += 1

    print(f"    Found {len(binary_patterns)} binary data segments:")
    for start, length in binary_patterns:
        hex_data = data[start : start + length].hex()
        print(f"      Offset {start}: {length} bytes - {hex_data}")


def demo_data_stream_processing():
    """Demonstrate binary data stream processing."""
    print("\n=== Data Stream Processing Demo ===")

    # Simulate TN3270 data stream with mixed content
    def create_sample_data_stream():
        """Create a sample TN3270-like data stream."""
        stream = bytearray()

        # TN3270 command sequence
        stream.extend([0xFF, 0xFA])  # IAC SB
        stream.extend([0x18])  # TN3270E
        stream.extend([0x01])  # SUB-command

        # EBCDIC screen data
        screen_text = "WELCOME TO TN3270 TERMINAL"
        stream.extend(translate_ascii_to_ebcdic(screen_text))

        # Binary field attributes
        stream.extend([0xC0, 0x00, 0xF0, 0x00])  # Field markers

        # More EBCDIC data
        more_text = "ENTER USERID:"
        stream.extend(translate_ascii_to_ebcdic(more_text))

        # Binary cursor position
        stream.extend([0x00, 0x10, 0x00, 0x20])  # Cursor at row 16, col 32

        return bytes(stream)

    data_stream = create_sample_data_stream()
    print(f"Sample data stream: {len(data_stream)} bytes")
    print(f"Hex dump: {data_stream.hex()}")

    # Process the stream
    print("\nProcessing data stream:")

    i = 0
    while i < len(data_stream):
        # Check for Telnet commands
        if i < len(data_stream) - 1 and data_stream[i : i + 2] == b"\xFF\xFA":
            print(f"  Telnet SB at offset {i}")
            i += 2
            # Skip to SE
            while i < len(data_stream) - 1 and data_stream[i : i + 2] != b"\xFF\xF0":
                i += 1
            if data_stream[i : i + 2] == b"\xFF\xF0":
                print(f"  Telnet SE at offset {i}")
                i += 2
        # Check for EBCDIC text
        elif data_stream[i] >= 0xC0:  # Likely EBCDIC alphabetic
            text_start = i
            text_data = bytearray()
            while i < len(data_stream) and data_stream[i] >= 0x40:
                text_data.append(data_stream[i])
                i += 1
            if len(text_data) >= 3:
                try:
                    text = translate_ebcdic_to_ascii(bytes(text_data))
                    print(f"  EBCDIC text at {text_start}: '{text}'")
                except Exception as e:
                    print(f"  Failed to decode EBCDIC at {text_start}: {e}")
                    i = text_start + 1
            else:
                i = text_start + 1
        # Binary data
        else:
            binary_start = i
            while i < len(data_stream) and data_stream[i] < 0x40:
                i += 1
            binary_length = i - binary_start
            if binary_length >= 2:
                hex_data = data_stream[binary_start:i].hex()
                print(
                    f"  Binary data at {binary_start}: {binary_length} bytes - {hex_data}"
                )
            else:
                i = binary_start + 1


def demo_character_set_detection():
    """Demonstrate character set detection and conversion."""
    print("\n=== Character Set Detection Demo ===")

    # Sample data in different encodings
    sample_data = {
        "ASCII": b"Hello World 123",
        "EBCDIC": translate_ascii_to_ebcdic("Hello World 123"),
        "UTF-8": "Hello World 123".encode("utf-8"),
        "Latin-1": "Hello World 123".encode("latin-1"),
        "Mixed": translate_ascii_to_ebcdic("HELLO")
        + b"\x00\x01\x02"
        + "WORLD".encode("ascii"),
    }

    def detect_encoding(data: bytes) -> str:
        """Simple encoding detection heuristic."""
        # Check for EBCDIC characteristics
        ebcdic_score = 0
        ascii_score = 0

        for byte_val in data:
            if 0xC0 <= byte_val <= 0xE0:  # Common EBCDIC letters
                ebcdic_score += 1
            elif 0x40 <= byte_val <= 0x7E:  # ASCII printable
                ascii_score += 1

        ebcdic_ratio = ebcdic_score / len(data) if data else 0
        ascii_ratio = ascii_score / len(data) if data else 0

        if ebcdic_ratio > 0.5:
            return "EBCDIC"
        elif ascii_ratio > 0.5:
            return "ASCII"
        else:
            return "Unknown/Mixed"

    print("Encoding detection results:")
    for name, data in sample_data.items():
        detected = detect_encoding(data)
        print(f"  {name}: {detected} (expected: {name})")
        print(f"    Data: {data.hex()[:50]}...")

        # Try to decode based on detection
        try:
            if detected == "EBCDIC":
                decoded = translate_ebcdic_to_ascii(data)
            elif detected == "ASCII":
                decoded = data.decode("ascii", errors="replace")
            else:
                decoded = data.decode("utf-8", errors="replace")
            print(f"    Decoded: '{decoded}'")
        except Exception as e:
            print(f"    Decode failed: {e}")


async def demo_file_transfer_scenarios():
    """Demonstrate file transfer scenarios with binary data."""
    print("\n=== File Transfer Scenarios Demo ===")

    async with AsyncSession() as session:
        # Note: These operations require a real TN3270 host
        # For demo purposes, we'll show the framework

        print("IND$FILE transfer scenarios:")

        # Scenario 1: Text file transfer
        print("1. Text file transfer:")
        print("   - Convert text to EBCDIC before sending")
        print("   - Handle line endings (CRLF vs LF)")
        print("   - Detect character encoding issues")

        # Scenario 2: Binary file transfer
        print("2. Binary file transfer:")
        print("   - Send raw binary data without conversion")
        print("   - Preserve exact byte sequences")
        print("   - Handle large files with chunking")

        # Scenario 3: Mixed content transfer
        print("3. Mixed content transfer:")
        print("   - Identify text vs binary segments")
        print("   - Convert text portions to EBCDIC")
        print("   - Preserve binary portions unchanged")

        # Demonstrate data preparation
        print("\nData preparation examples:")

        # Text file preparation
        text_data = "Line 1\nLine 2\nLine 3"
        ebcdic_text = translate_ascii_to_ebcdic(text_data)
        print(f"Text conversion: {len(text_data)} -> {len(ebcdic_text)} bytes")

        # Binary data (no conversion needed)
        binary_data = bytes(range(256))  # 0-255
        print(f"Binary data: {len(binary_data)} bytes (unchanged)")

        # Mixed data handling
        mixed_data = ebcdic_text + b"\x00\x01\x02" + binary_data[:10]
        print(f"Mixed data: {len(mixed_data)} bytes (EBCDIC + binary)")


def demo_data_validation():
    """Demonstrate binary data validation and sanitization."""
    print("\n=== Data Validation and Sanitization Demo ===")

    def validate_ebcdic_data(data: bytes) -> Tuple[bool, str]:
        """Validate EBCDIC data."""
        try:
            # Try to decode
            text = translate_ebcdic_to_ascii(data)
            # Check for invalid sequences
            if "\x00" in text or "\xff" in text:
                return False, "Contains null or invalid characters"
            return True, f"Valid EBCDIC: '{text}'"
        except Exception as e:
            return False, f"Invalid EBCDIC: {e}"

    def sanitize_binary_data(data: bytes) -> bytes:
        """Sanitize binary data for safe handling."""
        # Remove or replace problematic bytes
        sanitized = bytearray()
        for byte_val in data:
            if byte_val in [0x00, 0xFF]:  # Null bytes or all-bits-set
                sanitized.append(0x40)  # EBCDIC space
            else:
                sanitized.append(byte_val)
        return bytes(sanitized)

    test_data = [
        translate_ascii_to_ebcdic("VALID TEXT"),
        translate_ascii_to_ebcdic("TEXT\x00WITH\xFFNULL"),
        bytes([0x00, 0x01, 0xFF, 0xFE]),  # Pure binary
        translate_ascii_to_ebcdic("HELLO") + b"\x00\x01\x02",  # Mixed
    ]

    print("Data validation results:")
    for i, data in enumerate(test_data):
        is_valid, message = validate_ebcdic_data(data)
        status = "✓" if is_valid else "✗"
        print(f"  Sample {i+1}: {status} {message}")

        if not is_valid:
            sanitized = sanitize_binary_data(data)
            is_valid_after, message_after = validate_ebcdic_data(sanitized)
            status_after = "✓" if is_valid_after else "✗"
            print(f"    Sanitized: {status_after} {message_after}")


async def main():
    """Run all binary data handling demonstrations."""
    print("Pure3270 Binary Data and EBCDIC Handling Demo")
    print("=" * 60)

    try:
        demo_character_encoding()
        demo_binary_file_operations()
        demo_data_stream_processing()
        demo_character_set_detection()
        await demo_file_transfer_scenarios()
        demo_data_validation()

        print("\n" + "=" * 60)
        print("✓ All binary data handling patterns demonstrated")
        print("\nKey takeaways:")
        print("- Always handle character encoding explicitly (EBCDIC vs ASCII)")
        print("- Use EBCDICCodec for reliable character conversions")
        print("- Validate data before processing to prevent corruption")
        print("- Handle mixed binary/text content carefully")
        print("- Sanitize binary data when necessary for safety")
        print("- Consider data size and memory usage for large transfers")
        print("- Test round-trip conversions to ensure data integrity")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
