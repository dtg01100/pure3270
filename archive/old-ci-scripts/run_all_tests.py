#!/usr/bin/env python3
"""
Run all non-Docker tests for pure3270.
Supports configurable unit and integration timeouts and memory limits via CLI arguments:
--unit-timeout INT (default: 5) - Timeout for unit tests (seconds)
--unit-mem INT (default: 100) - Memory limit for unit tests (MB)
--int-timeout INT (default: 10) - Timeout for integration tests (seconds)
--int-mem INT (default: 200) - Memory limit for integration tests (MB)
"""

import argparse
import asyncio
import os
import subprocess
import sys


def run_command(cmd, timeout=300, env=None):
    """Run a command and return the result. Supports custom env for limit propagation."""
    print(f"[RUN TESTS DEBUG] Running command: {cmd} with timeout {timeout}")
    try:
        kwargs = {
            "shell": True,
            "capture_output": True,
            "text": True,
            "timeout": timeout,
        }
        if env is not None:
            kwargs["env"] = env
        result = subprocess.run(cmd, **kwargs)
        print(
            f"[RUN TESTS DEBUG] Command completed with returncode {result.returncode}"
        )
        print(
            f"[RUN TESTS DEBUG] Stdout: {result.stdout[:500]}..."
            if result.stdout
            else "[RUN TESTS DEBUG] No stdout"
        )
        print(
            f"[RUN TESTS DEBUG] Stderr: {result.stderr[:500]}..."
            if result.stderr
            else "[RUN TESTS DEBUG] No stderr"
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print(f"[RUN TESTS DEBUG] Command timed out after {timeout}s")
        return False, "", "Command timed out"
    except Exception as e:
        print(f"[RUN TESTS DEBUG] Exception in command: {e}")
        return False, "", str(e)


async def main():
    """Run all non-Docker tests."""
    print("=== Running All Pure3270 Tests ===\n")

    # Parse CLI arguments for runner-level limit overrides
    parser = argparse.ArgumentParser(
        description="Run all pure3270 tests with configurable limits"
    )
    parser.add_argument(
        "--unit-timeout", type=int, default=5, help="Timeout for unit tests (seconds)"
    )
    parser.add_argument(
        "--unit-mem", type=int, default=100, help="Memory limit for unit tests (MB)"
    )
    parser.add_argument(
        "--int-timeout",
        type=int,
        default=10,
        help="Timeout for integration tests (seconds)",
    )
    parser.add_argument(
        "--int-mem",
        type=int,
        default=200,
        help="Memory limit for integration tests (MB)",
    )
    args = parser.parse_args()

    # Test type classification for limit propagation (unit vs integration)
    test_types = {
        "Quick Smoke Test": "unit",
        "Integration Test": "integration",
        "CI Test": "unit",
        "Comprehensive Test": "integration",
        "Navigation Method Test": "unit",
        "Release Validation Test": "integration",
        "Property Tests": "unit",
    }

    # Activate virtual environment if it exists
    venv_activate = ""
    if os.path.exists("venv/bin/activate"):
        venv_activate = ". venv/bin/activate && "

    tests = [
        ("Quick Smoke Test", f"{venv_activate}timeout 30 python quick_test.py"),
        # Use the same conditional venv activation approach for Integration Test to
        # avoid hard failure when venv/ is not present (will run without venv then)
        ("Integration Test", f"{venv_activate}python integration_test.py"),
        ("CI Test", f"{venv_activate}timeout 60 python ci_test.py"),
        (
            "Comprehensive Test",
            f"{venv_activate}timeout 90 python comprehensive_test.py",
        ),
        ("Navigation Method Test", f"{venv_activate}python navigation_method_test.py"),
        (
            "Release Validation Test",
            f"{venv_activate}timeout 90 python release_test.py",
        ),
        (
            "Property Tests",
            f"{venv_activate}timeout 60 pytest tests/property/ -m property -v",
        ),
    ]

    results = []

    for test_name, command in tests:
        # Propagate limits via env vars for standalone tests (used by tools/memory_limit.py wrappers)
        test_type = test_types[test_name]
        env = os.environ.copy()
        if test_type == "unit":
            env["UNIT_TIMEOUT"] = str(args.unit_timeout)
            env["UNIT_MEM"] = str(args.unit_mem)
        else:
            env["INTEGRATION_TIMEOUT"] = str(args.int_timeout)
            env["INTEGRATION_MEM"] = str(args.int_mem)
        print(f"Running {test_name}...")
        success, stdout, stderr = run_command(command, env=env)
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
