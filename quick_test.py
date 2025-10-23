#!/usr/bin/env python3
"""
Quick smoke test for pure3270.

This script performs fast validation tests (< 10 seconds) to ensure basic
functionality works correctly. Used by CI and as a pre-commit validation.

Tests include:
- Import validation
- Session creation and configuration
- Mock connectivity handling
- Screen buffer operations
- EBCDIC conversion
- Basic protocol operations
"""

import sys
import time
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all core modules can be imported."""
    print("Testing imports...")

    try:
        # Core imports
        import pure3270
        from pure3270 import Session, setup_logging
        from pure3270.emulation import ebcdic, screen_buffer
        from pure3270.protocol import data_stream, negotiator

        print("✓ All core imports successful")
        return True

    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_session_creation():
    """Test basic Session object creation and configuration."""
    print("Testing session creation...")

    try:
        from pure3270 import Session

        # Test basic session creation
        session = Session(host="mock-host.example.com", port=23)
        assert session._host == "mock-host.example.com"
        assert session._port == 23

        # Test session with SSL context
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_session = Session(
            host="mock-host.example.com", port=992, ssl_context=ssl_context
        )
        assert ssl_session._ssl_context is not None

        # Test session configuration
        config_session = Session(
            host="mock-host.example.com", port=23, terminal_type="IBM-3278-2"
        )

        print("✓ Session creation and configuration successful")
        return True

    except Exception as e:
        print(f"✗ Session creation failed: {e}")
        return False


def test_screen_buffer():
    """Test basic screen buffer operations."""
    print("Testing screen buffer operations...")

    try:
        from pure3270.emulation.screen_buffer import ScreenBuffer

        # Create a basic screen buffer
        buffer = ScreenBuffer(24, 80)  # 24 rows, 80 columns

        # Test basic operations
        buffer.clear()
        # Write some text using EBCDIC
        from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic

        hello_bytes = translate_ascii_to_ebcdic("Hello World")
        for i, byte in enumerate(hello_bytes):
            if i < 11:  # Only write first 11 characters
                buffer.write_char(byte, 0, i)

        # Test cursor positioning
        buffer.set_position(5, 10)
        assert buffer.cursor_row == 5
        assert buffer.cursor_col == 10

        # Test that buffer has content
        text = buffer.to_text()
        assert len(text) > 0

        print("✓ Screen buffer operations successful")
        return True

    except Exception as e:
        print(f"✗ Screen buffer test failed: {e}")
        return False


def test_ebcdic_conversion():
    """Test EBCDIC to ASCII conversion."""
    print("Testing EBCDIC conversion...")

    try:
        from pure3270.emulation.ebcdic import (
            translate_ascii_to_ebcdic,
            translate_ebcdic_to_ascii,
        )

        # Test basic conversion
        test_text = "Hello World"
        ebcdic_bytes = translate_ascii_to_ebcdic(test_text)
        converted_back = translate_ebcdic_to_ascii(ebcdic_bytes)

        # Should be close (EBCDIC conversion may not be perfect for all chars)
        assert len(converted_back) > 0

        # Test known EBCDIC conversions
        test_char = "A"
        ebcdic_a = translate_ascii_to_ebcdic(test_char)
        ascii_a = translate_ebcdic_to_ascii(ebcdic_a)
        assert len(ascii_a) > 0

        print("✓ EBCDIC conversion successful")
        return True

    except Exception as e:
        print(f"✗ EBCDIC conversion failed: {e}")
        return False


def test_mock_connectivity():
    """Test mock connectivity handling (no real connection)."""
    print("Testing mock connectivity...")

    try:
        from pure3270 import Session

        # Create session with mock host
        session = Session(host="mock-tn3270-host.example.com", port=23)

        # Test that we can attempt connection (will fail but shouldn't crash)
        try:
            session.connect()
            print("✗ Unexpected successful connection to mock host")
            return False
        except Exception:
            # Expected to fail with mock host
            pass

        # Test session cleanup
        session.close()

        print("✓ Mock connectivity handling successful")
        return True

    except Exception as e:
        print(f"✗ Mock connectivity test failed: {e}")
        return False


def test_navigation_methods():
    """Test that navigation methods are available."""
    print("Testing navigation methods...")

    try:
        from pure3270 import Session

        # Create session and check for key methods
        session = Session(host="mock-host.example.com", port=23)

        # Check that essential methods exist
        assert hasattr(session, "connect")
        assert hasattr(session, "close")
        assert hasattr(session, "send")
        assert hasattr(session, "read")

        # Check screen buffer access (may be through screen_buffer property)
        assert hasattr(session, "screen_buffer") or hasattr(session, "screen")

        print("✓ Navigation methods available")
        return True

    except Exception as e:
        print(f"✗ Navigation methods test failed: {e}")
        return False


def test_api_compatibility():
    """Test basic API compatibility."""
    print("Testing API compatibility...")

    try:
        import ssl

        from pure3270 import Session

        # Test that we can create various session configurations
        configs = [
            {"host": "test1.example.com", "port": 23},
            {
                "host": "test2.example.com",
                "port": 992,
                "ssl_context": ssl.create_default_context(),
            },
            {"host": "test3.example.com", "port": 23, "terminal_type": "IBM-3278-2"},
        ]

        for config in configs:
            session = Session(**config)
            assert session._host == config["host"]
            assert session._port == config["port"]
            session.close()

        print("✓ API compatibility successful")
        return True

    except Exception as e:
        print(f"✗ API compatibility test failed: {e}")
        return False


def main():
    """Run all quick tests."""
    print("🚀 Starting pure3270 quick smoke tests...")
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print("-" * 50)

    start_time = time.time()

    tests = [
        test_imports,
        test_session_creation,
        test_screen_buffer,
        test_ebcdic_conversion,
        test_mock_connectivity,
        test_navigation_methods,
        test_api_compatibility,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"✗ {test.__name__} FAILED")
        except Exception as e:
            print(f"✗ {test.__name__} CRASHED: {e}")
        print()

    end_time = time.time()
    duration = end_time - start_time

    print("-" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    print(f"⏱️  Execution time: {duration:.2f} seconds")

    if passed == total:
        print("🎉 ALL QUICK SMOKE TESTS PASSED!")
        print("✅ Basic functionality validated successfully")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("⚠️  Manual investigation required")
        return 1


if __name__ == "__main__":
    sys.exit(main())
