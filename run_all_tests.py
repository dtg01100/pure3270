#!/usr/bin/env python3
"""
Run all non-Docker tests for pure3270.
"""

import asyncio
import subprocess
import sys
import os


def run_command(cmd, timeout=60):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


async def main():
    """Run all non-Docker tests."""
    print("=== Running All Pure3270 Tests ===\n")

    # Activate virtual environment if it exists
    venv_activate = ""
    if os.path.exists("venv/bin/activate"):
        venv_activate = "source venv/bin/activate && "

    tests = [
        ("Quick Smoke Test", f"{venv_activate}timeout 30 python quick_test.py"),
        ("Integration Test", f"{venv_activate}timeout 60 python integration_test.py"),
        ("CI Test", f"{venv_activate}timeout 30 python ci_test.py"),
        (
            "Comprehensive Test",
            f"{venv_activate}timeout 60 python comprehensive_test.py",
        ),
        ("Navigation Method Test", f"{venv_activate}python navigation_method_test.py"),
        (
            "Release Validation Test",
            f"{venv_activate}timeout 90 python release_test.py",
        ),
    ]

    results = []

    for test_name, command in tests:
        print(f"Running {test_name}...")
        success, stdout, stderr = run_command(command)
        results.append((test_name, success))

        if success:
            print(f"  ✓ {test_name} PASSED")
        else:
            print(f"  ✗ {test_name} FAILED")
            if stderr:
                print(f"    Error: {stderr}")

    # Summary
    print("\n" + "=" * 50)
    print("ALL TESTS SUMMARY")
    print("=" * 50)

    all_passed = True
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name:<30} {status}")
        if not success:
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("Pure3270 is functioning correctly.")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please check the failed tests above.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
