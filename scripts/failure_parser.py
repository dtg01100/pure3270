#!/usr/bin/env python3
"""
Simple JUnit XML failure parser.

Usage:
  python scripts/failure_parser.py <junit_xml_path> [logs_dir]

Outputs a JSON payload to stdout with the following shape:
{
  "num_failures": int,
  "failures": [
    {
      "test": "suite.class::test_name",
      "message": "failure message (truncated)",
      "file": "optional filename",
      "line": optional_line_number
    },
    ...
  ]
}

This is intentionally lightweight to avoid extra dependencies in CI.
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET  # nosec B405 - parses local CI artifacts only
from pathlib import Path
from typing import Any, Dict, List, Optional


def _truncate(text: str, limit: int = 500) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def parse_junit(xml_path: Path) -> Dict[str, Any]:
    if not xml_path.exists():
        return {"num_failures": 0, "failures": []}

    try:
        tree = ET.parse(str(xml_path))  # nosec B314 - safe: local file under CI control
        root = tree.getroot()
    except ET.ParseError:
        return {"num_failures": 0, "failures": []}

    failures: List[Dict[str, Any]] = []

    # Handle both <testsuite> root and <testsuites> containers
    testcases = []
    if root.tag.endswith("testsuites"):
        for suite in root.findall("testsuite"):
            testcases.extend(suite.findall("testcase"))
    else:
        testcases = (
            root.findall("testcase")
            if root.tag.endswith("testsuite")
            else root.findall(".//testcase")
        )

    for tc in testcases:
        cls = tc.attrib.get("classname", "")
        name = tc.attrib.get("name", "")
        fqname = f"{cls}::{name}" if cls else name
        # Collect both <failure> and <error> nodes
        for tag in ("failure", "error"):
            for node in tc.findall(tag):
                msg = node.attrib.get("message") or (node.text or "").strip()
                entry: Dict[str, Any] = {
                    "test": fqname,
                    "message": _truncate(msg or tag.upper()),
                }
                # Best-effort extract of file and line from message when present as 'file:line: msg'
                text = (node.text or "").strip()
                if ":" in text:
                    parts = text.split(":", 2)
                    if len(parts) >= 2 and parts[1].isdigit():
                        entry["file"] = parts[0]
                        entry["line"] = int(parts[1])
                failures.append(entry)

    return {"num_failures": len(failures), "failures": failures}


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print(json.dumps({"num_failures": 0, "failures": []}))
        return 0
    xml_path = Path(argv[1])
    payload = parse_junit(xml_path)
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
