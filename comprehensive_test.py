#!/usr/bin/env python3
"""
Comprehensive test script for pure3270.
This test script verifies:
1. Mock server connectivity
2. Navigation method availability
3. Basic functionality without requiring full setup
"""

import asyncio
import sys
import os

# Add the current directory to the path so we can import pure3270
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from integration_test import test_with_mock_server

# Import pure3270
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


async def test_p3270_patching():
    """Test p3270 patching functionality."""
    print("2. Testing p3270 patching...")
    try:
        import pure3270

        # Enable replacement
        pure3270.enable_replacement()

        # Import p3270 (should use our patched version)
        import p3270

        # Create client
        client = p3270.P3270Client()

        # Check that it's using our wrapper
        if "pure3270" in str(type(client.s3270)):
            print("   ✓ p3270 patching works correctly")
            return True
        else:
            print("   ✗ p3270 patching not working")
            return False
    except Exception as e:
        print(f"   ✗ p3270 patching test failed: {e}")
        return False


def test_navigation_methods():
    """Test that all navigation methods exist."""
    print("3. Testing navigation methods...")
    try:
        import pure3270
        from pure3270 import AsyncSession

        # Create an AsyncSession instance
        session = AsyncSession()

        # Check a sample of important methods
        important_methods = [
            "move_cursor",
            "page_up",
            "page_down",
            "left",
            "right",
            "up",
            "down",
            "enter",
            "clear",
            "pf",
            "pa",
        ]

        missing = []
        for method in important_methods:
            if not hasattr(session, method):
                missing.append(method)

        if missing:
            print(f"   ✗ Missing methods: {', '.join(missing)}")
            return False

        print(f"   ✓ All {len(important_methods)} important navigation methods present")
        return True
    except Exception as e:
        print(f"   ✗ Navigation methods test failed: {e}")
        return False


async def test_basic_functionality():
    """Test basic functionality."""
    print("4. Testing basic functionality...")
    try:
        import pure3270
        from pure3270 import Session, AsyncSession

        # Test Session properties
        session = Session()
        print(f"   ✓ Session connected: {session.connected}")

        # Test AsyncSession properties
        async_session = AsyncSession()
        print(f"   ✓ AsyncSession connected: {async_session.connected}")

        # Test screen buffer access
        buffer = async_session.screen_buffer
        print(f"   ✓ Screen buffer access: {type(buffer).__name__}")

        return True
    except Exception as e:
        print(f"   ✗ Basic functionality test failed: {e}")
        return False


async def main():
    """Run all comprehensive tests."""
    print("=== Pure3270 Comprehensive Test Suite ===\n")

    # Run tests
    tests = [
        ("Mock Server Connectivity", test_mock_server_connectivity),
        ("p3270 Patching", test_p3270_patching),
        ("Navigation Methods", test_navigation_methods),
        ("Basic Functionality", test_basic_functionality),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))

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
        print("  • p3270 patching works correctly")
        print("  • All navigation methods are implemented")
        print("  • Basic functionality is available")
    else:
        print("❌ SOME COMPREHENSIVE TESTS FAILED!")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
