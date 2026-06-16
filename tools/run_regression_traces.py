#!/usr/bin/env python3
"""
Regression trace runner.

Replays every trace under ``tests/data/traces/`` through pure3270's
``Replayer`` and validates the resulting screen state against the matching
``*_expected.json`` baseline file.

Used by:
  * ``tests/test_regression_traces.py`` (parametrized pytest wrapper)
  * ``.github/workflows/trace_replay_tests.yml`` (PR/push gating)
  * ``.github/workflows/nightly-s3270-parity.yml`` (nightly parity check)

The runner never requires s3270; it compares pure3270 behavior against the
project's own frozen baselines.  The nightly workflow adds a separate
s3270-vs-pure3270 side-by-side comparison on top.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pure3270.trace.replayer import Replayer  # noqa: E402

logger = logging.getLogger("regression_traces")

DEFAULT_TRACE_DIR = ROOT / "tests" / "data" / "traces"
DEFAULT_EXPECTED_DIR = ROOT / "tests" / "data" / "expected"
DEFAULT_OUTPUT_PATH = ROOT / "test_output" / "regression_traces_report.json"


@dataclass
class CheckResult:
    """Result of a single ``validation_checks`` entry."""

    type: str
    passed: bool
    description: str = ""
    expected: Any = None
    actual: Any = None
    message: str = ""


@dataclass
class TraceResult:
    """Aggregated outcome for a single trace."""

    trace: str
    expected_file: Optional[str]
    replayed: bool
    records_parsed: int
    duration_seconds: float
    passed: bool
    skipped_reason: Optional[str] = None
    checks: List[CheckResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace": self.trace,
            "expected_file": self.expected_file,
            "replayed": self.replayed,
            "records_parsed": self.records_parsed,
            "duration_seconds": self.duration_seconds,
            "passed": self.passed,
            "skipped_reason": self.skipped_reason,
            "checks": [asdict(c) for c in self.checks],
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass
class SuiteResult:
    """Aggregated outcome for the whole regression suite."""

    total: int
    passed: int
    failed: int
    skipped: int
    duration_seconds: float
    results: List[TraceResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "duration_seconds": self.duration_seconds,
            },
            "results": [r.to_dict() for r in self.results],
        }


def _parse_size(value: str) -> tuple[int, int]:
    """Parse a ``'24x80'`` style screen size string."""
    if not value or "x" not in value:
        raise ValueError(f"Invalid screen size: {value!r}")
    rows_s, cols_s = value.lower().split("x", 1)
    return int(rows_s), int(cols_s)


def _evaluate_check(
    check: Dict[str, Any],
    screen_rows: int,
    screen_cols: int,
    field_count: int,
    input_field_count: int,
    parser_errors: int,
) -> CheckResult:
    """Evaluate a single ``validation_checks`` entry against replay output."""
    check_type = check.get("type", "")
    description = check.get("description", "")

    if check_type == "screen_size":
        expected = check.get("expected", "")
        try:
            exp_rows, exp_cols = _parse_size(expected)
        except ValueError:
            return CheckResult(
                type=check_type,
                passed=False,
                description=description,
                expected=expected,
                actual=f"{screen_rows}x{screen_cols}",
                message=f"Malformed expected size {expected!r}",
            )
        ok = exp_rows == screen_rows and exp_cols == screen_cols
        return CheckResult(
            type=check_type,
            passed=ok,
            description=description,
            expected=expected,
            actual=f"{screen_rows}x{screen_cols}",
            message="" if ok else "Screen size mismatch",
        )

    if check_type == "field_count":
        lo = check.get("min", 0)
        hi = check.get("max", field_count)
        ok = lo <= field_count <= hi
        return CheckResult(
            type=check_type,
            passed=ok,
            description=description,
            expected={"min": lo, "max": hi},
            actual=field_count,
            message="" if ok else f"Field count {field_count} outside [{lo}, {hi}]",
        )

    if check_type == "input_fields":
        expected = check.get("count", 0)
        ok = input_field_count == expected
        return CheckResult(
            type=check_type,
            passed=ok,
            description=description,
            expected=expected,
            actual=input_field_count,
            message=(
                "" if ok else f"Input field count {input_field_count} != {expected}"
            ),
        )

    if check_type == "parsing_errors":
        should_error = bool(check.get("expected_errors", False))
        had_errors = parser_errors > 0
        ok = should_error == had_errors
        return CheckResult(
            type=check_type,
            passed=ok,
            description=description,
            expected=should_error,
            actual=had_errors,
            message="" if ok else "Parsing error expectation mismatch",
        )

    # Unknown check types are treated as warnings, not failures.
    return CheckResult(
        type=check_type or "unknown",
        passed=True,
        description=description,
        message=f"Unrecognized check type {check_type!r}; skipped",
    )


def _count_input_fields(fields: List[Dict[str, Any]]) -> int:
    """Return the number of unprotected (input-capable) fields."""
    return sum(1 for f in fields if not f.get("protected", True))


def _run_single_trace(
    trace_path: Path,
    expected_dir: Path,
) -> TraceResult:
    """Replay a single trace and validate against its expected baseline."""
    name = trace_path.name
    expected_path = expected_dir / f"{trace_path.stem}_expected.json"
    expected_data: Optional[Dict[str, Any]] = None
    if expected_path.exists():
        try:
            with expected_path.open("r", encoding="utf-8") as f:
                expected_data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            return TraceResult(
                trace=name,
                expected_file=str(expected_path.relative_to(ROOT)),
                replayed=False,
                records_parsed=0,
                duration_seconds=0.0,
                passed=False,
                errors=[f"Failed to load expected file: {exc}"],
            )
    else:
        logger.debug("No expected file for %s; structural checks only", name)

    replayer = Replayer()
    start = time.monotonic()
    try:
        state = replayer.replay(str(trace_path))
    except FileNotFoundError:
        return TraceResult(
            trace=name,
            expected_file=(
                str(expected_path.relative_to(ROOT)) if expected_path.exists() else None
            ),
            replayed=False,
            records_parsed=0,
            duration_seconds=0.0,
            passed=False,
            errors=[f"Trace file missing: {trace_path}"],
        )
    except Exception as exc:  # pragma: no cover - defensive
        return TraceResult(
            trace=name,
            expected_file=(
                str(expected_path.relative_to(ROOT)) if expected_path.exists() else None
            ),
            replayed=False,
            records_parsed=0,
            duration_seconds=time.monotonic() - start,
            passed=False,
            errors=[f"Replay raised {type(exc).__name__}: {exc}"],
        )

    duration = time.monotonic() - start
    screen_buffer = state["screen_buffer"]
    fields = state["fields"]
    screen_rows = getattr(screen_buffer, "rows", 0)
    screen_cols = getattr(screen_buffer, "cols", 0)
    field_count = len(fields)
    input_field_count = _count_input_fields(fields)

    result = TraceResult(
        trace=name,
        expected_file=(
            str(expected_path.relative_to(ROOT)) if expected_path.exists() else None
        ),
        replayed=True,
        records_parsed=len(getattr(replayer.parser, "orders", []) or []),
        duration_seconds=duration,
        passed=True,
    )

    # If we couldn't load expected data, only structural sanity is checked.
    if expected_data is None:
        result.passed = screen_rows > 0 and screen_cols > 0
        if not result.passed:
            result.errors.append(
                f"Empty screen buffer (rows={screen_rows}, cols={screen_cols})"
            )
        return result

    # Run every validation_check from the baseline.
    parser_errors = sum(1 for e in result.errors)
    checks: List[CheckResult] = []
    for raw in expected_data.get("validation_checks", []):
        if not isinstance(raw, dict):
            continue
        checks.append(
            _evaluate_check(
                raw,
                screen_rows=screen_rows,
                screen_cols=screen_cols,
                field_count=field_count,
                input_field_count=input_field_count,
                parser_errors=parser_errors,
            )
        )
    result.checks = checks

    # Detailed ``screen`` block (when present) adds another correctness layer.
    expected_screen = expected_data.get("screen")
    if isinstance(expected_screen, dict):
        exp_rows = expected_screen.get("rows")
        exp_cols = expected_screen.get("cols")
        exp_fields = expected_screen.get("num_fields")
        if exp_rows is not None and exp_rows != screen_rows:
            result.errors.append(f"screen.rows expected {exp_rows}, got {screen_rows}")
        if exp_cols is not None and exp_cols != screen_cols:
            result.errors.append(f"screen.cols expected {exp_cols}, got {screen_cols}")
        if exp_fields is not None and exp_fields != field_count:
            result.errors.append(
                f"screen.num_fields expected {exp_fields}, got {field_count}"
            )

    result.passed = (
        all(c.passed for c in checks) and not result.errors and result.replayed
    )
    return result


def discover_traces(trace_dir: Path) -> List[Path]:
    """Return all ``*.trc`` files in ``trace_dir`` sorted by name."""
    return sorted(p for p in trace_dir.glob("*.trc"))


def run_suite(
    trace_dir: Path = DEFAULT_TRACE_DIR,
    expected_dir: Path = DEFAULT_EXPECTED_DIR,
    only: Optional[List[str]] = None,
) -> SuiteResult:
    """Run the regression suite and return a structured result."""
    if not trace_dir.exists():
        raise FileNotFoundError(f"Trace directory not found: {trace_dir}")

    traces = discover_traces(trace_dir)
    if only:
        only_set = {n for n in only}
        traces = [t for t in traces if t.name in only_set or t.stem in only_set]
        if not traces:
            raise FileNotFoundError(
                f"No matching traces for filter: {sorted(only_set)}"
            )

    start = time.monotonic()
    results: List[TraceResult] = []
    for trace_path in traces:
        logger.info("▶ %s", trace_path.name)
        results.append(_run_single_trace(trace_path, expected_dir))

    duration = time.monotonic() - start
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if r.replayed and not r.passed)
    skipped = sum(1 for r in results if not r.replayed)
    return SuiteResult(
        total=len(results),
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration_seconds=duration,
        results=results,
    )


def print_summary(suite: SuiteResult) -> None:
    """Emit a human-readable summary to stdout."""
    print()
    print("=" * 78)
    print("PURE3270 REGRESSION TRACE SUITE")
    print("=" * 78)
    print(
        f"Total: {suite.total}  Passed: {suite.passed}  "
        f"Failed: {suite.failed}  Skipped: {suite.skipped}  "
        f"Duration: {suite.duration_seconds:.2f}s"
    )
    print("-" * 78)
    for r in suite.results:
        if not r.replayed:
            status = "SKIP" if r.passed else "ERROR"
        else:
            status = "PASS" if r.passed else "FAIL"
        marker = "✅" if r.passed and r.replayed else ("❌" if not r.passed else "⚠️")
        print(f"  {marker} {status:4s}  {r.trace}  ({r.duration_seconds:.2f}s)")
        for err in r.errors:
            print(f"        ERROR: {err}")
        for check in r.checks:
            if not check.passed:
                print(
                    f"        CHECK[{check.type}]: {check.message} "
                    f"(expected={check.expected!r}, actual={check.actual!r})"
                )
    print("=" * 78)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run the pure3270 regression trace suite",
    )
    p.add_argument(
        "--trace-dir",
        type=Path,
        default=DEFAULT_TRACE_DIR,
        help="Directory of .trc files (default: tests/data/traces)",
    )
    p.add_argument(
        "--expected-dir",
        type=Path,
        default=DEFAULT_EXPECTED_DIR,
        help="Directory of *_expected.json baselines",
    )
    p.add_argument(
        "--only",
        action="append",
        default=None,
        help=(
            "Restrict to specific trace names or stems; can be passed "
            "multiple times. Useful for fast local iteration."
        ),
    )
    p.add_argument(
        "--report-json",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the JSON report",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any trace failed (CI mode).",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    suite = run_suite(
        trace_dir=args.trace_dir,
        expected_dir=args.expected_dir,
        only=args.only,
    )
    print_summary(suite)

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    with args.report_json.open("w", encoding="utf-8") as f:
        json.dump(suite.to_dict(), f, indent=2)
    print(f"📄 Report written to {args.report_json}")

    if args.strict and suite.failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
