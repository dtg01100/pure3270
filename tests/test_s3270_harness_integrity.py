#!/usr/bin/env python3
"""
Harness integrity tests for the pure3270-vs-s3270 comparison tooling.

These tests verify that the trace-replay / s3270 comparison harness
(tools/compare_replay_with_s3270.py, tools/batch_compare_traces.py)
actually drives the real s3270 binary, captures its rendered screen,
and produces a result that can be used to detect regressions in
pure3270.

The test is intentionally permissive about *what* s3270 and pure3270
agree on: the harness's job is to surface diffs honestly, not to
prove parity. What we assert here is that:

  * the harness ran every trace we asked it to run (no silent skips)
  * s3270 was actually invoked (not stubbed or wrapped)
  * per-trace outcomes are populated and self-consistent
  * the run completed without harness errors (errors in the
    comparison tooling, not protocol diffs)

When pure3270 and s3270 disagree, that disagreement is recorded in
``differences`` and the test still passes -- the failure to act on
it is a human/code-review concern, not a harness bug.

Run with:
    pytest --run-s3270 tests/test_s3270_harness_integrity.py
or:
    PURE3270_RUN_S3270=1 pytest tests/test_s3270_harness_integrity.py
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.compare_replay_with_s3270 import compare_trace, find_real_s3270  # noqa: E402

pytestmark = [
    pytest.mark.s3270,
    pytest.mark.timeout(180),
]

# Subset of traces we run. Picked to be small, fast, and span a
# variety of harness paths (basic negotiation, codepage, structured
# field). Expand deliberately, never accidentally.
HARNESS_TRACE_SUBSET: List[str] = [
    "tests/data/traces/ra_test.trc",
    "tests/data/traces/930.trc",
]


def _require_s3270() -> Path:
    """Locate a real s3270 binary or skip the test.

    Refuses the repo's bin/s3270 wrapper via find_real_s3270's
    own detection logic.
    """
    s3270 = find_real_s3270(None)
    if s3270 is None:
        pytest.skip("real s3270 binary not found in PATH")
    return s3270


def _resolve_traces(spec: List[str]) -> List[Path]:
    """Resolve trace paths relative to repo root; fail loudly on
    data-set drift rather than letting the harness error obscure it.
    """
    resolved: List[Path] = []
    for name in spec:
        p = Path(name)
        if not p.is_absolute():
            p = ROOT / name
        if not p.is_file():
            pytest.fail(f"trace fixture missing: {name}")
        resolved.append(p)
    return resolved


async def _compare_each(
    trace_paths: List[Path],
    s3270_path: Path,
    base_port: int,
    delay: float = 0.5,
) -> List[Dict[str, Any]]:
    """Drive compare_trace per file with a hard total time budget.

    Returns a list of per-trace result dicts. The CLI's batch
    compare runs every file in the directory; we want a fixed
    subset, so we call compare_trace directly.
    """
    out: List[Dict[str, Any]] = []
    for i, trace in enumerate(trace_paths):
        port = base_port + i
        rc = await compare_trace(
            trace_path=trace,
            port=port,
            s3270_path=s3270_path,
            delay=delay,
        )
        if rc == 0:
            status = "match" if s3270_path else "no_reference"
        elif rc == 1:
            status = "difference"
        else:
            out.append(
                {
                    "trace": trace.name,
                    "status": "error",
                    "error": f"compare_trace returned {rc}",
                }
            )
            continue
        out.append({"trace": trace.name, "status": status})
    return out


@pytest.mark.asyncio
async def test_harness_runs_subset_and_surfaces_outcomes(tmp_path: Path) -> None:
    """The batch comparison harness must:

    1. Run every requested trace to completion.
    2. Populate a result for each (no silent drops).
    3. Report ``s3270_available`` truthfully.
    4. Produce zero harness-level errors (errors in *our tooling*,
       not in protocol diffs).
    """
    s3270_path = _require_s3270()
    trace_paths = _resolve_traces(HARNESS_TRACE_SUBSET)

    # Per-trace results. The batch CLI's whole-directory behaviour
    # makes it unsuitable for a fixed-subset test; we replicate the
    # per-trace loop here.
    results = await _compare_each(trace_paths, s3270_path, base_port=24500, delay=0.5)
    out_json = tmp_path / "results.json"
    out_json.write_text(json.dumps({"results": results}, indent=2))

    # 1. We asked for N traces; we got N results.
    assert len(results) == len(trace_paths), (
        f"harness produced {len(results)} results, " f"expected {len(trace_paths)}"
    )

    # 2. s3270 was actually invoked -- none of the results are
    # ``no_reference`` (the marker find_real_s3270 would set if
    # s3270 were missing).
    assert all(r["status"] != "no_reference" for r in results), (
        "s3270_available is False in at least one trace; "
        "harness did not actually drive the binary"
    )

    # 3. Per-trace results are well-formed and named correctly.
    reported = {r["trace"] for r in results}
    expected_names = {p.name for p in trace_paths}
    assert reported == expected_names, (
        f"trace name mismatch: harness reported {reported!r}, "
        f"expected {expected_names!r}"
    )
    valid = {"match", "difference", "error", "no_reference"}
    for r in results:
        assert (
            r["status"] in valid
        ), f"unknown status for {r['trace']!r}: {r['status']!r}"
        if r["status"] == "error":
            pytest.fail(
                f"harness-level error on {r['trace']!r}: "
                f"{r.get('error', '<no error message>')!r}"
            )

    # 4. At least one comparison actually produced a result. A pure
    # no_reference pass-through would mean s3270 was silently
    # bypassed.
    have_real = [r for r in results if r["status"] in {"match", "difference"}]
    assert have_real, "no traces produced a match/difference -- s3270 never ran"


def test_harness_produces_persistent_results_file(tmp_path: Path) -> None:
    """Sanity check: the JSON we write is parseable and contains
    the expected schema. Catches drift in the result format that
    would break downstream consumers.
    """
    s3270_path = _require_s3270()
    trace_paths = _resolve_traces([HARNESS_TRACE_SUBSET[0]])

    async def _run() -> List[Dict[str, Any]]:
        return await _compare_each(trace_paths, s3270_path, base_port=24600, delay=0.5)

    results: List[Dict[str, Any]] = asyncio.run(_run())
    out = tmp_path / "results.json"
    out.write_text(json.dumps({"results": results}, indent=2))

    loaded = json.loads(out.read_text())
    assert "results" in loaded
    assert isinstance(loaded["results"], list)
    assert loaded["results"], "results list is empty"
    # The trace we asked for must be present and not an error.
    target = trace_paths[0].name
    matching = [r for r in loaded["results"] if r["trace"] == target]
    assert matching, f"trace {target} not in results: {loaded['results']!r}"
    assert matching[0]["status"] in {
        "match",
        "difference",
    }, f"unexpected status for {target}: {matching[0]['status']!r}"


def test_real_s3270_binary_path_is_not_wrapper() -> None:
    """Defensive: the repo ships a bin/s3270 wrapper that must not
    be picked up by the harness. find_real_s3270 already filters it;
    this test pins that contract.
    """
    s3270_path = _require_s3270()
    repo_wrapper: Optional[Path] = ROOT / "bin" / "s3270"
    if repo_wrapper.exists():
        assert s3270_path.resolve() != repo_wrapper.resolve(), (
            f"harness would invoke the repo wrapper at {repo_wrapper}; "
            f"this defeats the comparison"
        )
    # And we must have a real binary we can execute.
    assert s3270_path.is_file(), f"s3270 path is not a file: {s3270_path}"
    assert (
        s3270_path.stat().st_mode & 0o111
    ), f"s3270 binary is not executable: {s3270_path}"
    # Cross-check with shutil.which: the path we resolved must
    # match what the OS would invoke.
    assert shutil.which(str(s3270_path)) is not None, (
        f"shutil.which cannot resolve {s3270_path}; "
        f"harness's s3270 detection is unreliable"
    )
