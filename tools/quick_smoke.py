#!/usr/bin/env python3
"""
Quick smoke test for pure3270 (moved out of repo root to avoid pytest collection).

This script provides the same quick checks but uses non-test function names
so pytest won't collect them as test cases.
"""

import sys
import time
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def smoke_imports():
    """Verify that core modules can be imported without exceptions."""
    try:
        import pure3270
        from pure3270 import Session, setup_logging
        from pure3270.emulation import ebcdic, screen_buffer
        from pure3270.protocol import data_stream, negotiator

        print("✓ All core imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def smoke_session_creation():
    """Validate Session object creation and configuration."""
    try:
        from pure3270 import Session

        session = Session(host="mock-host.example.com", port=23)
        assert session._host == "mock-host.example.com"
        assert session._port == 23
        print("✓ Session creation and configuration successful")
        return True
    except Exception as e:
        print(f"✗ Session creation failed: {e}")
        return False


def smoke_screen_buffer():
    """Basic screen buffer smoke checks."""
    from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
    from pure3270.emulation.screen_buffer import ScreenBuffer

    try:
        buffer = ScreenBuffer(24, 80)
        buffer.clear()
        hello_bytes = translate_ascii_to_ebcdic("Hello World")
        for i, byte in enumerate(hello_bytes):
            if i < 11:
                buffer.write_char(byte, 0, i)
        buffer.set_position(5, 10)
        assert buffer.cursor_row == 5
        assert buffer.cursor_col == 10
        assert len(buffer.to_text()) > 0
        print("✓ Screen buffer operations successful")
        return True
    except Exception as e:
        print(f"✗ Screen buffer test failed: {e}")
        return False


def smoke_ebcdic_conversion():
    """Test EBCDIC to ASCII conversion."""
    try:
        from pure3270.emulation.ebcdic import (
            translate_ascii_to_ebcdic,
            translate_ebcdic_to_ascii,
        )

        test_text = "Hello World"
        ebcdic_bytes = translate_ascii_to_ebcdic(test_text)
        converted_back = translate_ebcdic_to_ascii(ebcdic_bytes)
        assert len(converted_back) > 0

        test_char = "A"
        ebcdic_a = translate_ascii_to_ebcdic(test_char)
        ascii_a = translate_ebcdic_to_ascii(ebcdic_a)
        assert len(ascii_a) > 0
        print("✓ EBCDIC conversion successful")
        return True
    except Exception as e:
        print(f"✗ EBCDIC conversion failed: {e}")
        return False


def smoke_mock_connectivity():
    """Test mock connectivity handling (no real connection)."""
    try:
        from pure3270 import Session

        session = Session(host="mock-tn3270-host.example.com", port=23)
        try:
            session.connect()
            print("✗ Unexpected successful connection to mock host")
            return False
        except Exception:
            pass
        session.close()
        print("✓ Mock connectivity handling successful")
        return True
    except Exception as e:
        print(f"✗ Mock connectivity test failed: {e}")
        return False


def smoke_navigation_methods():
    """Test that common navigation APIs exist on Session."""
    try:
        from pure3270 import Session

        session = Session(host="mock-host.example.com", port=23)
        assert hasattr(session, "connect")
        assert hasattr(session, "close")
        assert hasattr(session, "send")
        assert hasattr(session, "read")
        assert hasattr(session, "screen_buffer") or hasattr(session, "screen")
        print("✓ Navigation methods available")
        return True
    except Exception as e:
        print(f"✗ Navigation methods test failed: {e}")
        return False


def smoke_api_compatibility():
    """Test various session configurations to ensure API compatibility."""
    try:
        import ssl

        from pure3270 import Session

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


def run_all_smoke_tests():
    tests = [
        smoke_imports,
        smoke_session_creation,
        smoke_screen_buffer,
        smoke_ebcdic_conversion,
        smoke_mock_connectivity,
        smoke_navigation_methods,
        smoke_api_compatibility,
    ]
    passed = 0
    total = len(tests)
    start_time = time.time()
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
    print(f"📊 Test Results: {passed}/{total} tests passed")
    print(f"⏱️  Execution time: {duration:.2f} seconds")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_all_smoke_tests())
