#!/usr/bin/env python3
"""Validation CLI entry point.

Usage:
    python -m pure3270.validation [--rfc-matrix] [--wire] [--acceptance] [--fuzz] [--all]
                                   [--report-json FILE] [--ci] [--verbose] [--skip-slow]
"""

import argparse
import asyncio
import json
import sys
import time

from pure3270.validation.matrix.checker import RfcMatrix
from pure3270.validation.matrix.reporter import build_rfc_report
from pure3270.validation.report import ValidationReport


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pure3270 Formal Validation Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--rfc-matrix", action="store_true", help="Run RFC compliance matrix check"
    )
    parser.add_argument(
        "--wire", action="store_true", help="Run wire-level protocol tests"
    )
    parser.add_argument(
        "--acceptance", action="store_true", help="Run end-to-end acceptance scenarios"
    )
    parser.add_argument("--fuzz", action="store_true", help="Run fuzzing tests")
    parser.add_argument("--all", action="store_true", help="Run everything (default)")
    parser.add_argument("--report-json", type=str, help="Write JSON report to FILE")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Strict mode: exit non-zero on any gap/failure",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Detailed per-test output"
    )
    parser.add_argument(
        "--skip-slow", action="store_true", help="Skip acceptance and fuzz (fast mode)"
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if not any([args.rfc_matrix, args.wire, args.acceptance, args.fuzz, args.all]):
        args.all = True

    report = ValidationReport(ci_mode=args.ci, start_time=time.time())

    if args.all or args.rfc_matrix:
        matrix = RfcMatrix()
        matrix.load_all()
        build_rfc_report(matrix, report)

    if args.all or args.wire:
        from pure3270.validation.wire.runner import load_vectors, run_vector

        vectors = load_vectors()
        sec = report.add_section("Wire-Level Vectors")
        sec.total = len(vectors)
        for v in vectors:
            result = asyncio.run(run_vector(v))
            if result["passed"]:
                sec.passed += 1
            else:
                sec.failed += 1
                sec.details.append(f"  FAIL: {v.id} - {result.get('error', 'unknown')}")

    if args.all or args.acceptance:
        from pure3270.validation.acceptance.runner import ScenarioRunner
        from pure3270.validation.acceptance.scenarios import create_default_scenarios

        scenarios = create_default_scenarios()
        sec = report.add_section("Acceptance Scenarios")
        sec.total = len(scenarios)
        runner = ScenarioRunner(target="mock")
        for scenario in scenarios:
            result = asyncio.run(runner.run_scenario(scenario))
            if result["passed"]:
                sec.passed += 1
                sec.details.append(
                    f"  PASS: {scenario.name} ({result['steps_passed']}/{result['steps_total']} steps)"
                )
            else:
                sec.failed += 1
                sec.details.append(
                    f"  FAIL: {scenario.name} - {result.get('error', 'unknown')}"
                )

    if args.all or args.fuzz:
        sec = report.add_section("Fuzzing")
        sec.details.append("  Not yet implemented")

    report.end_time = time.time()

    has_failures = any(s.failed > 0 for s in report.sections.values())
    if args.ci and has_failures:
        report.exit_code = 2
    elif has_failures:
        report.exit_code = 1
    else:
        report.exit_code = 0

    print(report.summary())
    if args.report_json:
        with open(args.report_json, "w") as f:
            json.dump(report.to_json(), f, indent=2)

    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
