#!/usr/bin/env python3
"""
Render a Markdown summary of ``test_output/regression_traces_report.json``
for ``$GITHUB_STEP_SUMMARY``.

Used by ``.github/workflows/trace_replay_tests.yml`` and the nightly
s3270-parity workflow.  Always exits 0: it's a reporting helper, not a
gate.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_REPORT = Path("test_output/regression_traces_report.json")


def _format_reasons(result: Dict[str, Any]) -> str:
    reasons: List[str] = []
    for check in result.get("checks", []):
        if not check.get("passed", True):
            reasons.append(str(check.get("type", "?")))
    for err in result.get("errors", []):
        reasons.append("error")
    return ", ".join(reasons) if reasons else "unknown"


def render(report_path: Path) -> str:
    if not report_path.exists():
        return (
            f"⚠️ Regression report not found at `{report_path}`.\n"
            "The regression step did not produce output - inspect logs."
        )

    with report_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    results = data.get("results", [])

    total = int(summary.get("total", 0))
    passed = int(summary.get("passed", 0))
    failed = int(summary.get("failed", 0))
    skipped = int(summary.get("skipped", 0))
    duration = float(summary.get("duration_seconds", 0.0))

    lines: List[str] = []
    lines.append("## Regression Trace Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total | {total} |")
    lines.append(f"| Passed | {passed} |")
    lines.append(f"| Failed | {failed} |")
    lines.append(f"| Skipped | {skipped} |")
    lines.append(f"| Duration | {duration:.2f}s |")

    failed_traces = [r for r in results if r.get("replayed") and not r.get("passed")]
    if failed_traces:
        lines.append("")
        lines.append("### Failing traces")
        lines.append("")
        for r in failed_traces:
            lines.append(f"- `{r['trace']}`: {_format_reasons(r)}")

    xfail_traces = [
        r
        for r in results
        if r.get("replayed")
        and r.get("passed")
        and any(
            "xfail" in (c.get("type", "") or "").lower() for c in r.get("checks", [])
        )
    ]
    if xfail_traces:
        lines.append("")
        lines.append(f"### Traces matching xfail ({len(xfail_traces)})")
        lines.append(
            "These traces are expected to fail; remove the `xfail` marker "
            "once the underlying gap is fixed."
        )

    return "\n".join(lines) + "\n"


def main(argv: List[str]) -> int:
    report_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_REPORT
    summary = render(report_path)

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(summary)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
