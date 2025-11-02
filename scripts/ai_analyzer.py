#!/usr/bin/env python3
"""
Minimal AI analysis placeholder.

Usage:
  python scripts/ai_analyzer.py <payload_json_path> <output_dir>

Behavior:
  - If OPENAI_API_KEY is set, this script could be extended to call an API.
  - Without a key, it generates a basic markdown report from payload JSON.

This ensures the GitHub Actions job never hard-fails when the secret is
missing, while still producing a useful artifact for human review.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, cast


def load_payload(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"num_failures": 0, "failures": []}
    try:
        return cast(Dict[str, Any], json.loads(path.read_text()))
    except Exception:
        return {"num_failures": 0, "failures": []}


def generate_report(payload: Dict[str, Any]) -> str:
    num = int(payload.get("num_failures") or payload.get("numErrors") or 0)
    failures = payload.get("failures") or []
    lines = []
    lines.append("# Regression Analysis Report")
    lines.append("")
    lines.append(f"Detected failures: {num}")
    lines.append("")
    if failures:
        lines.append("## Failures")
        for f in failures[:50]:  # Limit output size
            test = f.get("test", "unknown")
            msg = f.get("message", "")
            file = f.get("file")
            line = f.get("line")
            loc = f" ({file}:{line})" if file and line else ""
            lines.append(f"- {test}{loc}: {msg}")
    else:
        lines.append("No failures were found in the provided payload.")
    lines.append("")
    lines.append("---")
    lines.append("This report was generated without external AI services.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: ai_analyzer.py <payload_json_path> <output_dir>", file=sys.stderr)
        return 2
    payload_path = Path(argv[1])
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = load_payload(payload_path)

    # In future, if OPENAI_API_KEY is provided, you can enrich this report.
    _openai_key = os.getenv("OPENAI_API_KEY", "")

    report = generate_report(payload)
    report_path = out_dir / "regression_analysis.md"
    report_path.write_text(report)
    print(f"Wrote report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
