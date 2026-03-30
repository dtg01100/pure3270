#!/usr/bin/env python3
"""
Comprehensive Project Validation Script

This script validates that pure3270 is actually usable by testing:
1. Core imports and API availability
2. Session creation and lifecycle
3. Screen buffer operations
4. EBCDIC conversion
5. Protocol handling
6. Error handling
7. Real-world usage patterns
"""

import sys
import traceback
from typing import List, Tuple


class ValidationResult:
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message


def test_core_imports() -> List[ValidationResult]:
    """Test that all core components can be imported."""
    results = []

    try:
        import pure3270

        results.append(ValidationResult("Import pure3270", True))
    except Exception as e:
        results.append(ValidationResult("Import pure3270", False, str(e)))
        return results

    # Test main classes
    try:
        from pure3270 import AsyncSession, P3270Client, Session

        results.append(
            ValidationResult("Import Session, AsyncSession, P3270Client", True)
        )
    except Exception as e:
        results.append(
            ValidationResult("Import Session, AsyncSession, P3270Client", False, str(e))
        )

    # Test protocol components
    try:
        from pure3270.protocol import data_stream, negotiator, tn3270_handler

        results.append(ValidationResult("Import protocol modules", True))
    except Exception as e:
        results.append(ValidationResult("Import protocol modules", False, str(e)))

    # Test emulation components
    try:
        from pure3270.emulation import ebcdic, screen_buffer

        results.append(ValidationResult("Import emulation modules", True))
    except Exception as e:
        results.append(ValidationResult("Import emulation modules", False, str(e)))

    return results


def test_session_lifecycle() -> List[ValidationResult]:
    """Test session creation and lifecycle management."""
    results = []

    # Test sync session
    try:
        from pure3270 import Session

        session = Session()
        assert session is not None
        assert hasattr(session, "connect")
        assert hasattr(session, "close")
        assert hasattr(session, "read")
        assert hasattr(session, "send")
        results.append(ValidationResult("Sync Session creation", True))

        # Test context manager
        try:
            with Session() as s:
                assert s is not None
            results.append(ValidationResult("Sync Session context manager", True))
        except Exception as e:
            results.append(
                ValidationResult("Sync Session context manager", False, str(e))
            )

        session.close()
    except Exception as e:
        results.append(ValidationResult("Sync Session creation", False, str(e)))

    # Test async session (sync close for validation purposes)
    try:
        from pure3270 import AsyncSession

        session = AsyncSession()
        assert session is not None
        assert hasattr(session, "connect")
        assert hasattr(session, "close")
        assert hasattr(session, "read")
        assert hasattr(session, "send")
        results.append(ValidationResult("Async Session creation", True))
        # Note: AsyncSession.close() is async, but we're just checking it exists
    except Exception as e:
        results.append(ValidationResult("Async Session creation", False, str(e)))

    return results


def test_screen_buffer() -> List[ValidationResult]:
    """Test screen buffer operations."""
    results = []

    try:
        from pure3270.emulation.ebcdic import EBCDICCodec
        from pure3270.emulation.screen_buffer import ScreenBuffer

        # Create screen buffer (use 'cols' not 'columns')
        screen = ScreenBuffer(rows=24, cols=80)
        assert screen is not None
        results.append(ValidationResult("ScreenBuffer creation", True))

        # Test write operations
        codec = EBCDICCodec()
        test_text = "HELLO"
        ebcdic_data, _ = codec.encode(test_text)

        # Write to screen
        for i, char in enumerate(ebcdic_data):
            screen.write_char(i % screen.cols, i // screen.cols, char)
        results.append(ValidationResult("ScreenBuffer write operations", True))

        # Test read operations
        content = screen.to_text()
        assert content is not None
        results.append(ValidationResult("ScreenBuffer read operations", True))

        # Test cursor operations
        screen.set_position(5, 10)
        cursor_row, cursor_col = screen.cursor_row, screen.cursor_col
        assert cursor_row == 5
        assert cursor_col == 10
        results.append(ValidationResult("ScreenBuffer cursor operations", True))

    except Exception as e:
        results.append(ValidationResult("ScreenBuffer operations", False, str(e)))
        traceback.print_exc()

    return results


def test_ebcdic_conversion() -> List[ValidationResult]:
    """Test EBCDIC encoding/decoding."""
    results = []

    try:
        from pure3270.emulation.ebcdic import EBCDICCodec

        codec = EBCDICCodec()
        results.append(ValidationResult("EBCDICCodec creation", True))

        # Test round-trip conversion (encode/decode return tuples)
        test_strings = [
            "Hello, World!",
            "TN3270 Terminal",
            "Mainframe Access",
            "Special chars: @#$%",
        ]

        for test_str in test_strings:
            encoded, enc_len = codec.encode(test_str)
            decoded, dec_len = codec.decode(encoded)
            assert decoded == test_str, f"Round-trip failed: {test_str} != {decoded}"

        results.append(ValidationResult("EBCDIC round-trip conversion", True))

        # Test specific character mappings
        encoded_a, _ = codec.encode("A")
        assert encoded_a != b"A", "EBCDIC should differ from ASCII"
        results.append(ValidationResult("EBCDIC encoding differs from ASCII", True))

    except Exception as e:
        results.append(ValidationResult("EBCDIC conversion", False, str(e)))
        traceback.print_exc()

    return results


def test_protocol_handling() -> List[ValidationResult]:
    """Test protocol components."""
    results = []

    try:
        from pure3270.protocol.data_stream import DataStreamParser
        from pure3270.protocol.negotiator import Negotiator
        from pure3270.protocol.utils import IAC, SB, SE, TN3270E_IS, TN3270E_SEND

        # Test parser creation
        parser = DataStreamParser(screen_buffer=None)
        results.append(ValidationResult("DataStreamParser creation", True))

        # Test protocol constants
        assert IAC == 0xFF
        assert SB == 0xFA
        assert SE == 0xF0
        results.append(ValidationResult("Protocol constants defined", True))

        # Test basic parsing (empty data)
        parser.parse(b"")
        results.append(ValidationResult("DataStreamParser empty parse", True))

    except Exception as e:
        results.append(ValidationResult("Protocol handling", False, str(e)))
        traceback.print_exc()

    return results


def test_error_handling() -> List[ValidationResult]:
    """Test error handling and exceptions."""
    results = []

    try:
        from pure3270.exceptions import (
            NegotiationError,
            NotConnectedError,
            ParseError,
            ProtocolError,
            Pure3270Error,
        )

        # Test exception hierarchy
        assert issubclass(ProtocolError, Pure3270Error)
        assert issubclass(ParseError, Pure3270Error)
        assert issubclass(NegotiationError, Pure3270Error)
        results.append(ValidationResult("Exception hierarchy", True))

        # Test exception instantiation
        try:
            raise Pure3270Error("Test error")
        except Pure3270Error as e:
            assert str(e) == "Test error"
        results.append(ValidationResult("Exception raising", True))

        # Test session error handling
        from pure3270 import Session

        session = Session()
        session.close()  # Should not raise
        session.close()  # Double close should be safe
        results.append(ValidationResult("Session error handling", True))

    except Exception as e:
        results.append(ValidationResult("Error handling", False, str(e)))
        traceback.print_exc()

    return results


def test_p3270_compatibility() -> List[ValidationResult]:
    """Test p3270 API compatibility."""
    results = []

    try:
        from pure3270 import P3270Client

        # Test client creation
        client = P3270Client()
        assert client is not None
        results.append(ValidationResult("P3270Client creation", True))

        # Test required methods exist (using actual P3270Client method names)
        required_methods = [
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
        ]

        for method in required_methods:
            assert hasattr(client, method), f"Missing method: {method}"
        results.append(ValidationResult("P3270Client API methods", True))

        # Test close method exists (context manager not supported by P3270Client)
        assert hasattr(client, "close")
        results.append(ValidationResult("P3270Client close method", True))

    except Exception as e:
        results.append(ValidationResult("P3270Client compatibility", False, str(e)))
        traceback.print_exc()

    return results


def test_async_patterns() -> List[ValidationResult]:
    """Test async/await patterns."""
    import asyncio

    results = []

    async def run_async_tests():
        try:
            from pure3270 import AsyncSession

            # Test async context manager
            async with AsyncSession() as session:
                assert session is not None
            results.append(ValidationResult("AsyncSession async context manager", True))

            # Test disconnect without connect
            session = AsyncSession()
            await session.disconnect()
            results.append(ValidationResult("AsyncSession disconnect safety", True))

        except Exception as e:
            results.append(ValidationResult("Async patterns", False, str(e)))
            traceback.print_exc()

    try:
        asyncio.run(run_async_tests())
    except Exception as e:
        results.append(ValidationResult("Async event loop", False, str(e)))

    return results


def test_printer_session() -> List[ValidationResult]:
    """Test printer session functionality."""
    results = []

    try:
        from pure3270.protocol.printer import PrinterJob, PrinterSession

        # Test printer session creation
        printer = PrinterSession()
        assert printer is not None
        results.append(ValidationResult("PrinterSession creation", True))

        # Test job creation
        printer.activate()
        printer.start_new_job("test_job")
        job = printer.get_current_job()
        assert job is not None
        results.append(ValidationResult("PrinterJob creation", True))

        # Test data addition
        job.add_data(b"Test printer data")
        assert job.get_data_size() > 0
        results.append(ValidationResult("PrinterJob data handling", True))

        printer.deactivate()

    except Exception as e:
        results.append(ValidationResult("Printer session", False, str(e)))
        traceback.print_exc()

    return results


def main():
    """Run all validation tests."""
    print("=" * 80)
    print("PURE3270 PROJECT VALIDATION")
    print("=" * 80)
    print()

    all_results = []

    # Run all test categories
    test_categories = [
        ("Core Imports", test_core_imports),
        ("Session Lifecycle", test_session_lifecycle),
        ("Screen Buffer", test_screen_buffer),
        ("EBCDIC Conversion", test_ebcdic_conversion),
        ("Protocol Handling", test_protocol_handling),
        ("Error Handling", test_error_handling),
        ("P3270 Compatibility", test_p3270_compatibility),
        ("Async Patterns", test_async_patterns),
        ("Printer Session", test_printer_session),
    ]

    for category_name, test_func in test_categories:
        print(f"Testing {category_name}...")
        results = test_func()
        all_results.extend(results)

        # Print category results
        for result in results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"  {status}: {result.name}")
            if result.message:
                print(f"         {result.message}")
        print()

    # Summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in all_results if r.passed)
    failed = sum(1 for r in all_results if not r.passed)
    total = len(all_results)

    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    print()

    if failed > 0:
        print("FAILED TESTS:")
        for result in all_results:
            if not result.passed:
                print(f"  ✗ {result.name}: {result.message}")
        print()

    # Determine overall status
    if failed == 0:
        print("✅ ALL VALIDATION TESTS PASSED - PROJECT IS USABLE")
        return 0
    elif passed / total >= 0.8:
        print("⚠️  MOST TESTS PASSED - PROJECT IS MOSTLY USABLE WITH MINOR ISSUES")
        return 1
    else:
        print("❌ CRITICAL TESTS FAILED - PROJECT NEEDS WORK BEFORE PRODUCTION USE")
        return 2


if __name__ == "__main__":
    sys.exit(main())
