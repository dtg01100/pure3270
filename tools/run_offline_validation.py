#!/usr/bin/env python3
"""
Run the complete offline validation suite for Pure3270.

This script runs all offline validation tests to ensure Pure3270
correctness without requiring network access.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔍 {description}")
    print(f"   Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"   ✅ {description} PASSED")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"   ❌ {description} FAILED")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"   ⏰ {description} TIMED OUT")
        return False
    except Exception as e:
        print(f"   💥 {description} ERROR: {e}")
        return False


def main() -> int:
    """Run all offline validation tests."""
    print("🚀 Pure3270 Offline Validation Suite")
    print("=" * 50)

    # Ensure we're in the project root directory
    # In CI, the repo is checked out into a subdirectory named after the repo
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Check if we're already in the right place (has tests/ and pure3270/ directories)
    if (project_root / "tests").exists() and (project_root / "pure3270").exists():
        os.chdir(project_root)
    else:
        # We're in the nested repo directory, go up one more level
        project_root = script_dir.parent.parent
        if (project_root / "tests").exists() and (project_root / "pure3270").exists():
            os.chdir(project_root)
        else:
            # Last resort: find the directory containing both tests/ and pure3270/
            current = Path.cwd()
            for parent in [current] + list(current.parents):
                if (parent / "tests").exists() and (parent / "pure3270").exists():
                    os.chdir(parent)
                    break
            else:
                # If we can't find it, assume we're already in the right place
                pass

    print(f"Working directory: {os.getcwd()}")
    print(f"Script directory: {script_dir}")
    print(f"Project root: {project_root}")

    tests_passed = 0
    total_tests = 0

    # 1. Terminal Model Tests (optional if file exists)
    term_models = Path("tests/test_terminal_models.py")
    if term_models.exists():
        total_tests += 1
        if run_command(
            [sys.executable, "-m", "pytest", str(term_models), "-q"],
            "Terminal Model Validation (68 tests)",
        ):
            tests_passed += 1
    else:
        print(
            "Skipping Terminal Model Validation: tests/test_terminal_models.py not present in repository"
        )

    # 2. Protocol State Machine Tests (optional if file exists)
    proto_sm = Path("tests/test_protocol_state_machine.py")
    if proto_sm.exists():
        total_tests += 1
        if run_command(
            [sys.executable, str(proto_sm)],
            "Protocol State Machine Tests",
        ):
            tests_passed += 1
    else:
        print(
            "Skipping Protocol State Machine Tests: tests/test_protocol_state_machine.py not present in repository"
        )

    # 3. Synthetic Data Generation
    total_tests += 1
    if run_command(
        [
            sys.executable,
            "tools/synthetic_data_generator.py",
            "generate",
            "test_output/validation_synth",
            "2",
        ],
        "Synthetic Data Generation",
    ):
        tests_passed += 1

    # 4. Synthetic Data Testing
    total_tests += 1
    if run_command(
        [
            sys.executable,
            "tools/synthetic_data_generator.py",
            "test",
            "test_output/validation_synth/synthetic_test_cases.json",
        ],
        "Synthetic Data Stream Testing",
    ):
        tests_passed += 1

    # 5. Edge Case Testing
    total_tests += 1
    if run_command(
        [
            sys.executable,
            "tools/synthetic_data_generator.py",
            "edge_cases",
            "test_output/validation_edge",
        ],
        "Edge Case Generation",
    ):
        tests_passed += 1

    # 6. Edge Case Testing
    total_tests += 1
    if run_command(
        [
            sys.executable,
            "tools/synthetic_data_generator.py",
            "test",
            "test_output/validation_edge/edge_cases.json",
        ],
        "Edge Case Testing",
    ):
        tests_passed += 1

    # 7. Screen Buffer Regression
    total_tests += 1
    if run_command(
        [
            sys.executable,
            "tools/screen_buffer_regression_test.py",
            "generate",
            "test_output/validation_screen",
            "2",
        ],
        "Screen Buffer Regression Generation",
    ):
        tests_passed += 1

    # 8. Screen Buffer Testing
    total_tests += 1
    if run_command(
        [
            sys.executable,
            "tools/screen_buffer_regression_test.py",
            "run",
            "test_output/validation_screen",
        ],
        "Screen Buffer Regression Testing",
    ):
        tests_passed += 1

    # 9. Trace Replay Validation (multiple traces)
    trace_files = [
        "tests/data/traces/target.trc",
        "tests/data/traces/login.trc",
        "tests/data/traces/apl.trc",
        "tests/data/traces/empty-user.trc",
    ]

    trace_tests_passed = 0
    for trace_file in trace_files:
        if run_command(
            [
                "timeout",
                "15s",
                sys.executable,
                "tools/test_trace_replay.py",
                trace_file,
            ],
            f"Trace Replay: {Path(trace_file).name}",
        ):
            trace_tests_passed += 1

    total_tests += 1
    if trace_tests_passed == len(trace_files):
        tests_passed += 1
        print(f"   ✅ All {len(trace_files)} trace replay tests passed")
    else:
        print(
            f"   ⚠️  {trace_tests_passed}/{len(trace_files)} trace replay tests passed"
        )

    # Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION RESULTS")
    print("=" * 50)
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    print(".1f")

    if tests_passed == total_tests:
        print("🎉 ALL OFFLINE VALIDATION TESTS PASSED!")
        print("Pure3270 offline validation is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
