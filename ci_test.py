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
    if platform.system() != 'Linux':
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
CI/CD test script for pure3270.
This script runs a comprehensive set of tests that don't require full setup.
"""

import asyncio
import sys
import os
import logging

# Configure logging to show debug messages
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

# Add the current directory to the path so we can import pure3270
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Note: Limits are applied per test via run_with_limits_sync from tools/memory_limit.py
# Unix-only memory (setrlimit), cross-platform time (process timeout + signal.alarm on Unix).
# Defaults: 5s/100MB for unit/CI tests, configurable via UNIT_TIME_LIMIT, UNIT_MEM_LIMIT env vars.


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        import pure3270
        from pure3270 import Session, AsyncSession
        from pure3270.patching import enable_replacement

        print("  ✓ All imports successful")
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_class_creation():
    """Test that classes can be instantiated."""
    print("Testing class creation...")
    try:
        import pure3270
        from pure3270 import Session, AsyncSession

        # Test Session creation
        session = Session()
        print("  ✓ Session creation")

        # Test AsyncSession creation
        async_session = AsyncSession()
        print("  ✓ AsyncSession creation")

        return True
    except Exception as e:
        print(f"  ✗ Class creation failed: {e}")
        return False


def test_mock_connectivity():
    """Test mock server connectivity."""
    print("Testing mock server connectivity...")
    try:
        # For CI/CD tests, we just check that the mock server class can be imported
        # and that we can create an AsyncSession instance
        from integration_test import MockServer
        import pure3270
        from pure3270 import AsyncSession

        # Create instances to verify they work
        mock_server = MockServer()
        session = AsyncSession("dummy.host", 23)
        
        print("  ✓ Mock server and AsyncSession creation successful")
        return True
    except Exception as e:
        print(f"  ✗ Mock server test failed: {e}")
        return False


def test_navigation_methods():
    """Test that all navigation methods exist."""
    print("Testing navigation methods...")
    try:
        import pure3270
        from pure3270 import AsyncSession

        # Create an AsyncSession instance
        session = AsyncSession("dummy.host", 23)

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
            print(f"  ✗ Missing methods: {', '.join(missing)}")
            return False

        print(f"  ✓ All {len(important_methods)} important navigation methods present")
        return True
    except Exception as e:
        print(f"  ✗ Navigation methods test failed: {e}")
        return False


def test_p3270_patching():
    """Test p3270 patching functionality."""
    print("Testing p3270 patching...")
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
            print("  ✓ p3270 patching works correctly")
            return True
        else:
            print("  ✗ p3270 patching not working")
            return False
    except ImportError as e:
        if "p3270" in str(e):
            print("  ⚠ p3270 not installed, skipping patching test")
            return True  # Consider this a pass since p3270 is optional
        else:
            print(f"  ✗ p3270 patching test failed: {e}")
            return False
    except Exception as e:
        print(f"  ✗ p3270 patching test failed: {e}")
        return False


async def main():
    """Run all CI/CD tests."""
    print("=== Pure3270 CI/CD Test Suite ===\n")

    from tools.memory_limit import run_with_limits_sync, get_unit_limits

    unit_time, unit_mem = get_unit_limits()

    # Run tests with limits
    tests = [
        ("Imports", test_imports),
        ("Class Creation", test_class_creation),
        ("Mock Connectivity", test_mock_connectivity),
        ("Navigation Methods", test_navigation_methods),
        ("p3270 Patching", test_p3270_patching),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"Running {test_name} with limits: {unit_time}s / {unit_mem}MB")
        try:
            success, result = run_with_limits_sync(test_func, unit_time, unit_mem)
            if success and result:
                print(f"  ✓ {test_name} passed within limits")
                results.append((test_name, True))
            elif success and not result:
                print(f"  ✗ {test_name} failed (test logic)")
                results.append((test_name, False))
            else:
                print(f"  ✗ {test_name} failed limits: {result}")
                results.append((test_name, False))
        except Exception as e:
            print(f"  ✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 40)
    print("CI/CD TEST SUMMARY")
    print("=" * 40)

    all_passed = True
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:<20} {status}")
        if not result:
            all_passed = False

    print("=" * 40)
    if all_passed:
        print("🎉 ALL CI/CD TESTS PASSED!")
        return 0
    else:
        print("❌ SOME CI/CD TESTS FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
