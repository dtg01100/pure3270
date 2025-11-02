#!/usr/bin/env python3
"""
Comprehensive local CI runner that mirrors GitHub Actions CI steps.

Usage examples:
  python run_full_ci.py                  # Full run (matches GA steps as close as possible)
  python run_full_ci.py --fast           # Quick run (smoke + unit + static checks)
  python run_full_ci.py --skip-trace --skip-integration --skip-coverage

Exit with non-zero if any required step fails.
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).parent
PY = shlex.quote(sys.executable)


class Step:
    def __init__(self, name: str, command: str, optional: bool = False):
        self.name = name
        self.command = command
        self.optional = optional
        self.returncode: int | None = None
        self.output_path: Path | None = None

    def run(self) -> int:
        print(f"\n=== {self.name} ===")
        print(self.command)
        # nosec B602: Command string is controlled by this script, not user input
        rc = subprocess.call(self.command, shell=True, cwd=str(ROOT))  # nosec
        self.returncode = rc
        status = "OK" if rc == 0 else ("WARN" if self.optional else "FAIL")
        print(f"[{status}] {self.name} (exit={rc})")
        return rc


def build_steps(args: argparse.Namespace) -> List[Step]:
    steps: List[Step] = []

    # Smoke tests
    steps.append(Step("Quick smoke test", f"{PY} quick_test.py"))

    # Unit tests (non-integration)
    steps.append(
        Step(
            "Unit tests (not integration)",
            f"pytest tests/ -v --tb=short -m 'not integration'",
        )
    )

    # Integration tests
    if not args.skip_integration and not args.fast:
        trace_file = ROOT / "tests/data/traces/login.trc"
        if trace_file.exists():
            steps.append(
                Step(
                    "Integration test (trace replay)",
                    f"{PY} examples/trace_integration_test.py {shlex.quote(str(trace_file))} -c 1",
                    optional=True,  # keep optional to avoid local flakiness
                )
            )

    # Offline validation
    steps.append(
        Step(
            "Offline validation", f"{PY} tools/run_offline_validation.py", optional=True
        )
    )

    # Comprehensive trace testing (heavy)
    if not args.skip_trace and not args.fast:
        steps.append(
            Step(
                "Comprehensive trace testing",
                f"{PY} examples/full_trace_testing.py --all-traces --output-dir test_output/ci_trace_tests",
                optional=True,
            )
        )

    # Static analysis
    if not args.skip_mypy:
        steps.append(Step("mypy", "mypy pure3270/"))
    if not args.skip_pylint:
        steps.append(
            Step("pylint", "pylint pure3270/ --rcfile=.pylintrc", optional=True)
        )
    if not args.skip_flake8:
        steps.append(Step("flake8", "flake8 pure3270/"))
    if not args.skip_bandit:
        steps.append(Step("bandit", "bandit -c .bandit -r pure3270/"))

    # Macro DSL guard
    steps.append(Step("Macro DSL guard", f"{PY} tools/forbid_macros.py"))

    # Pre-commit hooks
    if not args.skip_hooks:
        steps.append(
            Step("pre-commit hooks", "pre-commit run --all-files", optional=True)
        )

    # Coverage
    if not args.skip_coverage and not args.fast:
        steps.append(
            Step(
                "Coverage (not integration)",
                "pytest --cov=pure3270 --cov-report=xml tests/ -m 'not integration'",
                optional=True,
            )
        )

    return steps


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run local CI to mirror GitHub Actions")
    p.add_argument(
        "--fast", action="store_true", help="Run a fast subset (skip heavy steps)"
    )
    p.add_argument("--skip-integration", dest="skip_integration", action="store_true")
    p.add_argument("--skip-trace", dest="skip_trace", action="store_true")
    p.add_argument("--skip-hooks", dest="skip_hooks", action="store_true")
    p.add_argument("--skip-coverage", dest="skip_coverage", action="store_true")
    p.add_argument("--skip-pylint", dest="skip_pylint", action="store_true")
    p.add_argument("--skip-mypy", dest="skip_mypy", action="store_true")
    p.add_argument("--skip-bandit", dest="skip_bandit", action="store_true")
    p.add_argument("--skip-flake8", dest="skip_flake8", action="store_true")
    return p.parse_args(argv)


def summarize(steps: List[Step]) -> Tuple[int, int, int]:
    required = [s for s in steps if not s.optional]
    optional = [s for s in steps if s.optional]

    req_fail = sum(1 for s in required if (s.returncode or 0) != 0)
    opt_fail = sum(1 for s in optional if (s.returncode or 0) != 0)

    print("\n================ CI SUMMARY ================")
    for s in steps:
        status = (
            "OK" if (s.returncode or 0) == 0 else ("WARN" if s.optional else "FAIL")
        )
        print(f" - {s.name:35s}: {status}")
    print("==========================================")
    print(f"Required failures: {req_fail}")
    print(f"Optional failures: {opt_fail}")
    return req_fail, opt_fail, len(steps)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    steps = build_steps(args)

    any_fail = False
    for step in steps:
        rc = step.run()
        if rc != 0 and not step.optional:
            any_fail = True

    req_fail, _, _ = summarize(steps)
    return 1 if any_fail or req_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
