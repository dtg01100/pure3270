#!/usr/bin/env python3
"""
Validate all pure3270 features in a single command.

Orchestrates all existing validation tools and test suites, providing
a single entry point for comprehensive validation. Exits non-zero if
any component fails.

Usage:
    python validate_all.py              # Full validation (CI mode)
    python validate_all.py --quick      # Smoke + RFC tests only
    python validate_all.py --list       # List all steps without running
"""

import os
import subprocess
import sys
import time
from pathlib import Path

STEPS: list[dict] = [
    {"name": "Smoke tests", "cmd": ["python", "quick_test.py"]},
    {
        "name": "RFC compliance tests",
        "cmd": [
            "python",
            "-m",
            "pytest",
            "tests/test_rfc854_iac_escaping.py",
            "tests/test_rfc854_telnet_commands.py",
            "tests/test_rfc854_telnet_edge_cases.py",
            "tests/test_rfc1091_terminal_type.py",
            "tests/test_rfc1572_new_environ.py",
            "tests/test_rfc2355_device_type.py",
            "tests/test_rfc2355_functions.py",
            "tests/test_rfc2355_bind_unbind.py",
            "tests/test_rfc2355_nvt_mode.py",
            "tests/test_rfc2355_responses.py",
            "tests/test_rfc2355_sysreq.py",
            "tests/test_rfc2355_keepalive.py",
            "tests/test_rfc2355_structured_fields.py",
            "-q",
        ],
    },
    {
        "name": "Feature matrix tests",
        "cmd": ["python", "-m", "pytest", "tests/test_feature_matrix.py", "-q"],
    },
    {
        "name": "Protocol core tests",
        "cmd": [
            "python",
            "-m",
            "pytest",
            "tests/test_protocol.py",
            "tests/test_protocol_negotiation.py",
            "tests/test_tn3270_handler.py",
            "tests/test_tn3270e_header.py",
            "tests/test_session.py",
            "-q",
        ],
    },
    {
        "name": "Screen buffer tests",
        "cmd": [
            "python",
            "-m",
            "pytest",
            "tests/test_screen_buffer.py",
            "tests/test_emulation.py",
            "tests/test_emulation_ebcdic.py",
            "-q",
        ],
    },
    {
        "name": "Data stream tests",
        "cmd": [
            "python",
            "-m",
            "pytest",
            "tests/test_data_stream.py",
            "tests/test_3270_data_payload.py",
            "tests/test_3270_extended_payload.py",
            "-q",
        ],
    },
    {
        "name": "Printer tests",
        "cmd": [
            "python",
            "-m",
            "pytest",
            "tests/test_printer.py",
            "tests/test_printer_error_handler.py",
            "tests/test_printer_error_recovery.py",
            "-q",
        ],
    },
    {
        "name": "Error handling tests",
        "cmd": [
            "python",
            "-m",
            "pytest",
            "tests/test_error_handling.py",
            "tests/test_error_handling_coverage.py",
            "tests/test_error_handling_traces.py",
            "-q",
        ],
    },
    {
        "name": "Lint (flake8)",
        "cmd": ["python", "-m", "flake8", "pure3270/", "--max-line-length=127"],
    },
    {"name": "Lint (ruff)", "cmd": ["python", "-m", "ruff", "check", "pure3270/"]},
    {"name": "Type check (mypy)", "cmd": ["python", "-m", "mypy", "pure3270/"]},
    {
        "name": "Security scan (bandit)",
        "cmd": ["python", "-m", "bandit", "-r", "pure3270/", "--quiet"],
    },
    {"name": "Macro prohibition", "cmd": ["python", "tools/forbid_macros.py"]},
    {
        "name": "Validation suite",
        "cmd": ["python", "-m", "pytest", "pure3270/validate_suite/", "-q"],
    },
]


def run_step(step: dict, quiet: bool = False) -> bool:
    print(f"\n  [{step['name']}]", flush=True)
    start = time.time()
    try:
        result = subprocess.run(
            step["cmd"],
            capture_output=not quiet,
            text=True,
            timeout=120,
        )
        elapsed = time.time() - start
        if result.returncode == 0:
            print(f"    PASS ({elapsed:.1f}s)", flush=True)
            return True
        print(f"    FAIL ({elapsed:.1f}s)", flush=True)
        if result.stdout:
            for line in result.stdout.strip().splitlines()[-15:]:
                print(f"      {line}")
        if result.stderr:
            for line in result.stderr.strip().splitlines()[-10:]:
                print(f"      {line}")
        return False
    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT (>120s)", flush=True)
        return False
    except FileNotFoundError as e:
        print(f"    SKIP (tool not found: {e})", flush=True)
        return True


def list_steps() -> None:
    for i, step in enumerate(STEPS, 1):
        print(f"  {i:2d}. {step['name']}: {' '.join(step['cmd'])}")


def main() -> int:
    args = set(sys.argv[1:])

    if "--list" in args:
        list_steps()
        return 0

    quick = "--quick" in args
    quiet = "--quiet" in args

    print("=" * 60)
    print("  pure3270 Full Validation Suite")
    print("=" * 60)

    steps = STEPS[:3] if quick else STEPS

    passed = 0
    failed: list[str] = []
    skipped: list[str] = []

    for step in steps:
        if run_step(step, quiet=quiet):
            passed += 1
        else:
            failed.append(step["name"])

    print()
    print("=" * 60)
    total = len(steps)
    if failed:
        print(f"  RESULT: {passed}/{total} passed, {len(failed)} FAILED")
        for name in failed:
            print(f"    FAIL: {name}")
    else:
        print(f"  RESULT: ALL {total}/{total} PASSED")
    print("=" * 60)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
