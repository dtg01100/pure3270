#!/usr/bin/env python3
"""
Comprehensive test script for pure3270 that tests:
1. Mock server connectivity
2. Navigation method availability
3. Basic functionality without requiring full Docker setup
"""

import asyncio
import sys
import os

# Add the current directory to the path so we can import pure3270
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from consolidated_docker_tests import test_with_mock_server
import pure3270
from pure3270 import AsyncSession


async def test_mock_server_connectivity():
    """Test mock server connectivity."""
    print("1. Testing mock server connectivity...")
    try:
        result = await test_with_mock_server()
        print(f"   Mock server test: {'✓ PASSED' if result else '✗ FAILED'}")
        return result
    except Exception as e:
        print(f"   Mock server test: ✗ FAILED with exception: {e}")
        return False


def test_async_session_navigation_methods():
    """Test that all expected navigation methods exist on AsyncSession."""
    print("2. Testing AsyncSession navigation methods...")

    # Create an AsyncSession instance (no connection needed for method existence check)
    session = AsyncSession("dummy.host", 23)

    # List of expected navigation methods
    expected_methods = [
        "move_cursor",
        "page_up",
        "page_down",
        "newline",
        "field_end",
        "erase_input",
        "erase_eof",
        "left",
        "right",
        "up",
        "down",
        "backspace",
        "tab",
        "backtab",
        "home",
        "end",
        "pf",
        "pa",
        "enter",
        "clear",
        "delete",
        "insert_text",
        "erase",
        "delete_field",
        "circum_not",
        "flip",
        "move_cursor1",
        "next_word",
        "previous_word",
        "restore_input",
        "save_input",
        "toggle_reverse",
        "cursor_select",
        "dup",
        "field_mark",
        "toggle_insert",
        "insert",
        "close_session",
        "disconnect",
        "info",
        "paste_string",
        "script",
        "bell",
        "pause",
        "ansi_text",
        "hex_string",
        "show",
        "snap",
        "left2",
        "right2",
        "mono_case",
        "nvt_text",
        "print_text",
        "prompt",
        "read_buffer",
        "reconnect",
        "screen_trace",
        "source",
        "subject_names",
        "sys_req",
        "toggle_option",
        "trace",
        "transfer",
        "wait_condition",
        "compose",
        "cookie",
        "expect",
        "fail",
        "load_resource_definitions",
    ]

    missing_methods = []

    for method_name in expected_methods:
        if hasattr(session, method_name):
            print(f"   ✓ {method_name}")
        else:
            missing_methods.append(method_name)
            print(f"   ✗ {method_name} (MISSING)")

    if missing_methods:
        print(f"   Missing methods: {', '.join(missing_methods)}")
        return False

    print(f"   All {len(expected_methods)} navigation methods are present!")
    return True


def test_p3270_patched_navigation_methods():
    """Test that p3270 patched client has expected navigation methods."""
    print("3. Testing p3270 patched navigation methods...")

    # Enable pure3270 replacement
    pure3270.enable_replacement()
    import p3270

    try:
        # Create a p3270 client (no connection needed for method existence check)
        client = p3270.P3270Client()

        # List of expected p3270 methods
        expected_methods = [
            "moveTo",
            "moveToFirstInputField",
            "moveCursorUp",
            "moveCursorDown",
            "moveCursorLeft",
            "moveCursorRight",
            "sendPF",
            "sendPA",
            "sendEnter",
            "clearScreen",
            "sendText",
            "delChar",
            "eraseChar",
            "sendBackSpace",
            "sendTab",
            "sendBackTab",
            "sendHome",
            "delField",
            "delWord",
            "printScreen",
            "saveScreen",
        ]

        missing_methods = []

        for method_name in expected_methods:
            if hasattr(client, method_name):
                print(f"   ✓ {method_name}")
            else:
                missing_methods.append(method_name)
                print(f"   ✗ {method_name} (MISSING)")

        if missing_methods:
            print(f"   Missing methods: {', '.join(missing_methods)}")
            return False

        print(f"   All {len(expected_methods)} p3270 patched methods are present!")
        return True

    except Exception as e:
        print(f"   Failed to create p3270 client: {e}")
        return False


async def test_basic_functionality():
    """Test basic functionality of pure3270 without network connection."""
    print("4. Testing basic functionality...")

    try:
        # Test Session creation
        session = pure3270.Session()
        print("   ✓ Session creation")

        # Test AsyncSession creation
        async_session = pure3270.AsyncSession()
        print("   ✓ AsyncSession creation")

        # Test enable_replacement
        pure3270.enable_replacement()
        print("   ✓ enable_replacement")

        # Test that we can import p3270 after enabling replacement
        import p3270

        print("   ✓ p3270 import after replacement")

        # Test that p3270 client can be created
        client = p3270.P3270Client()
        print("   ✓ p3270.P3270Client creation")

        return True
    except Exception as e:
        print(f"   Basic functionality test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=== Pure3270 Comprehensive Test Suite ===\n")

    # Run all tests
    results = []

    # Test 1: Mock server connectivity
    result1 = await test_mock_server_connectivity()
    results.append(("Mock Server Connectivity", result1))

    # Test 2: AsyncSession navigation methods
    result2 = test_async_session_navigation_methods()
    results.append(("AsyncSession Navigation Methods", result2))

    # Test 3: p3270 patched navigation methods
    result3 = test_p3270_patched_navigation_methods()
    results.append(("p3270 Patched Methods", result3))

    # Test 4: Basic functionality
    result4 = await test_basic_functionality()
    results.append(("Basic Functionality", result4))

    # Summary
    print("\n" + "=" * 50)
    print("COMPREHENSIVE TEST SUMMARY")
    print("=" * 50)

    all_passed = True
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:<30} {status}")
        if not result:
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("🎉 ALL COMPREHENSIVE TESTS PASSED!")
        print("\nPure3270 is functioning correctly:")
        print("  • Mock server connectivity works")
        print("  • All navigation methods are implemented")
        print("  • p3270 patching works correctly")
        print("  • Basic functionality is available")
    else:
        print("❌ SOME COMPREHENSIVE TESTS FAILED!")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
