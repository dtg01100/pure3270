#!/usr/bin/env python3
"""
Test runner with forced timeout - ensures no test can run indefinitely.
This script wraps test execution with a hard timeout that kills the process.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from typing import List, Optional


def run_with_timeout(
    command: List[str], timeout_seconds: int = 60, description: str = "Test"
) -> tuple[bool, str, str]:
    """
    Run a command with a hard timeout.

    Args:
        command: Command to run as list of strings
        timeout_seconds: Maximum seconds to allow
        description: Description for logging

    Returns:
        Tuple of (success, stdout, stderr)
    """
    print(f"Running {description} with {timeout_seconds}s timeout...")
    print(f"Command: {' '.join(command)}")

    start_time = time.time()

    try:
        # Use subprocess with timeout
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout_seconds
        )

        elapsed = time.time() - start_time
        success = result.returncode == 0

        print(
            f"  ✓ {description} completed in {elapsed:.2f}s (exit code: {result.returncode})"
        )

        return success, result.stdout, result.stderr

    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - start_time
        print(f"  ✗ {description} TIMED OUT after {elapsed:.2f}s")
        print("  Process was forcibly terminated to prevent hanging")

        return False, "", f"Timeout after {timeout_seconds}s"

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ✗ {description} failed after {elapsed:.2f}s: {e}")

        return False, "", str(e)


def main():
    """Main test runner with timeout protection."""
    parser = argparse.ArgumentParser(description="Run tests with timeout protection")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds")
    parser.add_argument("--test", type=str, help="Specific test file to run")
    parser.add_argument("--all", action="store_true", help="Run all tests")

    args = parser.parse_args()

    print("=== Test Runner with Timeout Protection ===")
    print(f"Global timeout: {args.timeout} seconds")
    print()

    # Define test files and their specific timeouts
    test_files = [
        ("quick_test.py", 30, "Quick Smoke Test"),
        ("simple_integration_test.py", 45, "Simple Integration Test"),
        ("working_integration_test.py", 45, "Working Integration Test"),
        ("simple_mock_server_test.py", 60, "Mock Server Test"),
        ("test_timeout_safety.py", 120, "Timeout Safety Test"),
    ]

    if args.test:
        # Run specific test
        command = [sys.executable, args.test]
        success, stdout, stderr = run_with_timeout(
            command, args.timeout, f"Test: {args.test}"
        )

        if not success:
            print(f"\nTest {args.test} failed!")
            if stderr:
                print(f"Error: {stderr}")
            return 1

        return 0

    elif args.all:
        # Run all tests
        results = []

        for test_file, test_timeout, description in test_files:
            if os.path.exists(test_file):
                command = [sys.executable, test_file]
                success, stdout, stderr = run_with_timeout(
                    command, min(test_timeout, args.timeout), description
                )
                results.append((description, success))
            else:
                print(f"  ⚠ {description} - file {test_file} not found")
                results.append((description, False))

        print("\n" + "=" * 50)
        print("TEST TIMEOUT PROTECTION SUMMARY")
        print("=" * 50)

        all_passed = True
        for description, success in results:
            status = "✓ PASS" if success else "✗ FAIL/TIMEOUT"
            print(f"{description:<25} {status}")
            if not success:
                all_passed = False

        print("=" * 50)
        if all_passed:
            print("🎉 ALL TESTS COMPLETED WITHIN TIMEOUTS!")
        else:
            print("❌ SOME TESTS FAILED OR TIMED OUT!")

        return 0 if all_passed else 1

    else:
        # Show usage
        print("Usage:")
        print(f"  {sys.argv[0]} --test <test_file.py>  # Run specific test")
        print(f"  {sys.argv[0]} --all                  # Run all tests")
        print(f"  {sys.argv[0]} --timeout 30 --all    # Run all with 30s timeout")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
