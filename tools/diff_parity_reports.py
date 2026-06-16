#!/usr/bin/env python3
"""
Diff two ``s3270_parity_report.json`` files and surface new regressions.

Used by the nightly ``nightly-s3270-parity.yml`` workflow to detect
traces that *previously* had parity with s3270 but *now* mismatch, and
vice-versa.  Only newly-introduced mismatches are flagged as
regressions; pre-existing mismatches are informational.

If a history file does not exist (first nightly run), the diff is empty
and we exit 0.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURRENT = ROOT / "test_output" / "s3270_parity_report.json"
DEFAULT_HISTORY = ROOT / "test_output" / "parity_history.json"
DEFAULT_OUTPUT = ROOT / "test_output" / "parity_diff.json"


def _index_results(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Index results by trace filename."""
    return {r["trace"]: r for r in report.get("results", [])}


def diff_reports(
    current: Dict[str, Any], history: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Return a structured diff between the two reports."""
    if history is None:
        return {
            "first_run": True,
            "new_mismatches": [],
            "fixed_mismatches": [],
            "still_mismatching": [],
            "new_errors": [],
            "fixed_errors": [],
        }

    cur = _index_results(current)
    hist = _index_results(history)
    all_traces = sorted(set(cur) | set(hist))

    new_mismatches: List[str] = []
    fixed_mismatches: List[str] = []
    still_mismatching: List[str] = []
    new_errors: List[str] = []
    fixed_errors: List[str] = []

    for trace in all_traces:
        c = cur.get(trace)
        h = hist.get(trace)
        c_mismatch = c is not None and c.get("parity") is False
        h_mismatch = h is not None and h.get("parity") is False
        c_err = c is not None and c.get("error") is not None
        h_err = h is not None and h.get("error") is not None

        if c_mismatch and not h_mismatch:
            new_mismatches.append(trace)
        elif not c_mismatch and h_mismatch:
            fixed_mismatches.append(trace)
        elif c_mismatch and h_mismatch:
            still_mismatching.append(trace)

        if c_err and not h_err:
            new_errors.append(trace)
        elif not c_err and h_err:
            fixed_errors.append(trace)

    return {
        "first_run": False,
        "new_mismatches": new_mismatches,
        "fixed_mismatches": fixed_mismatches,
        "still_mismatching": still_mismatching,
        "new_errors": new_errors,
        "fixed_errors": fixed_errors,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    doc_first_line = (__doc__ or "").splitlines()[0] if __doc__ else ""
    p = argparse.ArgumentParser(description=doc_first_line)
    p.add_argument("--current", type=Path, default=DEFAULT_CURRENT)
    p.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any new regression is detected",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if not args.current.exists():
        print(f"::warning::Current report missing: {args.current}")
        return 0

    with args.current.open("r", encoding="utf-8") as f:
        current = json.load(f)

    history: Optional[Dict[str, Any]] = None
    if args.history.exists():
        try:
            with args.history.open("r", encoding="utf-8") as f:
                history = json.load(f)
        except json.JSONDecodeError:
            print(
                f"::warning::History file {args.history} is not valid JSON; "
                "treating as no history"
            )

    result = diff_reports(current, history)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"📄 Parity diff written to {args.output}")

    if result["first_run"]:
        print("First nightly run; no diff produced.")
        return 0

    print(
        f"New mismatches: {len(result['new_mismatches'])}  "
        f"Fixed mismatches: {len(result['fixed_mismatches'])}  "
        f"Still mismatching: {len(result['still_mismatching'])}"
    )
    for t in result["new_mismatches"]:
        print(f"  ❌ NEW regression: {t}")
    for t in result["fixed_mismatches"]:
        print(f"  ✅ FIXED: {t}")

    if args.strict and result["new_mismatches"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
