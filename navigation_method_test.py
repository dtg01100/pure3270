#!/usr/bin/env python3

import platform
import resource


def set_memory_limit(max_memory_mb: int):
    """
    Set maximum memory limit for the current process.

    Args:
        max_memory_mb: Maximum memory in megabytes
    """
    # Only works on Unix systems
    if platform.system() != "Linux":
        return None

    try:
        max_memory_bytes = max_memory_mb * 1024 * 1024
        # RLIMIT_AS limits total virtual memory
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
        return max_memory_bytes
    except Exception:
        return None


# Set memory limit for the script
set_memory_limit(500)

"""
Test script to verify navigation method availability in pure3270.
This test doesn't require a real TN3270 server connection.
"""

import os
import sys

# Add the current directory to the path so we can import pure3270
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import pure3270
from pure3270 import AsyncSession


def test_async_session_navigation_methods():
    """Test that all expected navigation methods exist on AsyncSession."""
    print("Testing AsyncSession navigation methods...")

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
    found_methods = []

    for method_name in expected_methods:
        if hasattr(session, method_name):
            found_methods.append(method_name)
            print(f"  ✓ {method_name}")
        else:
            missing_methods.append(method_name)
            print(f"  ✗ {method_name} (MISSING)")

    print(
        f"\nFound {len(found_methods)} methods, missing {len(missing_methods)} methods"
    )

    if missing_methods:
        print(f"Missing methods: {', '.join(missing_methods)}")
        return False

    print("All navigation methods are present!")
    return True


def test_p3270_patched_navigation_methods():
    """Test that p3270 patched client has expected navigation methods."""
    print("\nTesting p3270 patched navigation methods...")

    try:
        # Enable pure3270 replacement
        pure3270.enable_replacement()
        import p3270

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
        found_methods = []

        for method_name in expected_methods:
            if hasattr(client, method_name):
                found_methods.append(method_name)
                print(f"  ✓ {method_name}")
            else:
                missing_methods.append(method_name)
                print(f"  ✗ {method_name} (MISSING)")

        print(
            f"\nFound {len(found_methods)} methods, missing {len(missing_methods)} methods"
        )

        if missing_methods:
            print(f"Missing methods: {', '.join(missing_methods)}")
            return False

        print("All p3270 patched methods are present!")
        return True

    except ImportError as e:
        if "p3270" in str(e):
            print("⚠ p3270 not installed, skipping p3270 navigation methods test")
            return True  # Consider this a pass since p3270 is optional
        else:
            print(f"Failed to import required modules: {e}")
            return False
    except Exception as e:
        print(f"Failed to create p3270 client: {e}")
        return False


def main():
    """Run all navigation method tests."""
    print("=== Pure3270 Navigation Method Availability Test ===\n")

    # Test AsyncSession methods
    async_result = test_async_session_navigation_methods()

    # Test p3270 patched methods
    p3270_result = test_p3270_patched_navigation_methods()

    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(
        f"AsyncSession navigation methods: {'✓ PASSED' if async_result else '✗ FAILED'}"
    )
    print(f"p3270 patched methods: {'✓ PASSED' if p3270_result else '✗ FAILED'}")
    print("=" * 50)

    if async_result and p3270_result:
        print("🎉 ALL NAVIGATION METHOD TESTS PASSED!")
        return 0
    else:
        print("❌ SOME NAVIGATION METHOD TESTS FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
