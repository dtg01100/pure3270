#!/usr/bin/env python3
"""
Run tools/compare_replay_with_s3270.py over all traces and produce a machine-readable JSON summary.

Produces: test_output/batch_trace_comparison_results.json
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import helper to detect real s3270 (avoids invoking which repeatedly)
try:
    from tools.compare_replay_with_s3270 import find_real_s3270  # type: ignore
except Exception:
    find_real_s3270 = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
TRACE_DIR = ROOT / "tests" / "data" / "traces"
OUT_PATH = ROOT / "test_output" / "batch_trace_comparison_results.json"
COMPARE_SCRIPT = ROOT / "tools" / "compare_replay_with_s3270.py"
PY = sys.executable or "python3"
# Basic logging configuration for runner visibility
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def gather_traces(trace_dir: Path) -> List[Path]:
    # include any .trc files everywhere under trace_dir
    traces = sorted([p for p in trace_dir.rglob("*.trc")])
    return traces


def extract_diff_snippet(stdout: str, max_lines: int = 200) -> str:
    lines = stdout.splitlines()
    # Try to find unified diff starting marker '--- s3270'
    for i, ln in enumerate(lines):
        if ln.startswith("--- s3270") or ln.startswith("--- s3270\n"):
            snippet = lines[i : i + max_lines]
            return "\n".join(snippet)
    # Fallback: find '[DIFF]' marker and return following lines
    for i, ln in enumerate(lines):
        if ln.startswith("[DIFF]"):
            snippet = lines[i : i + max_lines]
            return "\n".join(snippet)
    # Otherwise return the last max_lines of stdout
    return "\n".join(lines[-max_lines:])


def run_single_compare(
    trace_path: Path, port: int, s3270_path: Optional[Path]
) -> Dict[str, Any]:
    cmd: List[str] = [
        PY,
        str(COMPARE_SCRIPT),
        "--trace",
        str(trace_path),
        "--port",
        str(port),
    ]
    # Use modest timeouts per invocation to avoid long hangs
    cmd += ["--timeout", "60", "--overall-timeout", "120"]
    if s3270_path:
        cmd += ["--s3270-path", str(s3270_path)]
    env = None

    logging.debug(
        "run_single_compare: cmd=%s s3270_path=%s port=%s", cmd, s3270_path, port
    )

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300,
            env=env,
        )
    except subprocess.TimeoutExpired as e:
        return {
            "status": "error",
            "exit_code": None,
            "s3270_available": bool(s3270_path),
            "stdout": "",
            "stderr": f"subprocess timeout: {e}",
            "capture_errors": ["subprocess timeout"],
            "diff_snippet": "",
        }

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    exit_code = proc.returncode

    logging.debug(
        "run_single_compare: finished cmd returncode=%s stdout_len=%d stderr_len=%d",
        exit_code,
        len(stdout),
        len(stderr),
    )

    s3270_available = bool(s3270_path)

    capture_errors: List[str] = []
    if "timed out" in stdout.lower() or "timed out" in stderr.lower():
        capture_errors.append("capture timed out")
    if "Trace not found" in stderr:
        capture_errors.append("trace not found")
    if stderr.strip():
        capture_errors.append("stderr non-empty")

    # Determine status
    if not s3270_available:
        # The compare script prints a warning and returns 0 when s3270 not found.
        # Mark explicitly as blocked so the summary makes the root cause obvious.
        status = "blocked"
        capture_errors.append("s3270 missing")
    else:
        if exit_code == 0:
            status = "ok"
        elif exit_code == 1:
            status = "diff"
        else:
            status = "error"

    logging.debug(
        "run_single_compare: status=%s exit_code=%s s3270_available=%s capture_errors=%s",
        status,
        exit_code,
        s3270_available,
        capture_errors,
    )

    diff_snippet = ""
    if status == "diff":
        diff_snippet = extract_diff_snippet(stdout, max_lines=200)
        if not diff_snippet:
            # also check stderr
            diff_snippet = extract_diff_snippet(stderr, max_lines=200)

    return {
        "status": status,
        "exit_code": exit_code,
        "s3270_available": s3270_available,
        "stdout": stdout,
        "stderr": stderr,
        "capture_errors": capture_errors,
        "diff_snippet": diff_snippet,
    }


def main() -> int:
    traces = gather_traces(TRACE_DIR)
    if not traces:
        print(f"No traces found in {TRACE_DIR}", file=sys.stderr)
        return 2

    # Detect real s3270 once
    real_s3270 = None
    if find_real_s3270:
        try:
            real_s3270 = find_real_s3270(None)
        except Exception:
            real_s3270 = None

    # Fallback: if detection failed, try system which('s3270') directly.
    # In this environment a real /usr/bin/s3270 should be available; if not,
    # the test harness should surface that as an error rather than silently skip.
    if real_s3270 is None:
        try:
            which_path = shutil.which("s3270")
            if which_path:
                real_s3270 = Path(which_path)
        except Exception:
            real_s3270 = None

    results: Dict[str, Any] = {"per_trace": {}, "summary": {}}
    # use explicit 'blocked' to indicate tests not run due to missing s3270
    counts = {"ok": 0, "diff": 0, "blocked": 0, "error": 0}
    port_base = 23240

    for idx, trace in enumerate(traces):
        port = port_base + (idx % 1000)  # avoid extremely large ports
        logging.info("Running compare for %s on port %s ...", trace, port)
        try:
            res = run_single_compare(trace, port, real_s3270)
        except Exception:
            tb = traceback.format_exc()
            res = {
                "status": "error",
                "exit_code": None,
                "s3270_available": bool(real_s3270),
                "stdout": "",
                "stderr": tb,
                "capture_errors": ["exception during run"],
                "diff_snippet": "",
            }

        results["per_trace"][str(trace.relative_to(ROOT))] = res
        st = res.get("status", "error")
        if st in counts:
            counts[st] += 1
        else:
            counts["error"] += 1

    results["summary"] = {
        "total_traces": len(traces),
        "matches": counts["ok"],
        "diffs": counts["diff"],
        "blocked": counts["blocked"],
        "errors": counts["error"],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Wrote results to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
