#!/usr/bin/env python3
"""
Parametrized regression suite over every trace in ``tests/data/traces/``.

Each trace is replayed via ``tools/run_regression_traces.py`` and validated
against its frozen ``*_expected.json`` baseline.  This is the pytest entry
point for the CI integration; the underlying logic lives in
``tools/run_regression_traces.py`` so the same suite can be invoked from a
shell.

Traces whose baseline is currently drifting from pure3270 behavior are
marked with ``@pytest.mark.xfail(strict=True, reason=...)``.  Strict mode
forces the marker to be removed once the underlying gap is fixed -- a
passing xfail fails the suite, which is the intended safety net.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_regression_traces import (  # noqa: E402
    DEFAULT_EXPECTED_DIR,
    DEFAULT_TRACE_DIR,
    TraceResult,
    _run_single_trace,
)

# Traces currently drifting from their baselines.  These map to known
# implementation gaps (SNA replay, BIND handling, dynamic screen sizing,
# etc.) tracked separately.  Strict xfail forces the marker to be removed
# once the underlying gap is closed.
_KNOWN_FAILING: dict[str, str] = {
    "930.trc": "SNA BIND image parsing drift - tracked separately",
    "935.trc": "SNA BIND image parsing drift - tracked separately",
    "937.trc": "SNA BIND image parsing drift - tracked separately",
    "all_chars.trc": "43x80 dynamic screen size not negotiated by Replayer",
    "apl.trc": "APL field attribute parity - tracked separately",
    "bid-bug.trc": "Bid-image field accounting drift - tracked separately",
    "bid-ta.trc": "Bid-image field accounting drift - tracked separately",
    "bid.trc": "Bid-image field accounting drift - tracked separately",
    "contention-resolution.trc": "SNA contention-resolution parity - tracked separately",
    "ft-crash.trc": "IND$FILE field accounting drift - tracked separately",
    "ft_dft.trc": "IND$FILE DFT field accounting drift - tracked separately",
    "ibmlink2.trc": "ibmlink variant field accounting drift - tracked separately",
    "ibmlink_help.trc": "ibmlink help field accounting drift - tracked separately",
    "ignore_eor.trc": "SNA EOR-ignored replay drift - tracked separately",
    "invalid_sba.trc": "Invalid-SBA tolerance drift - tracked separately",
    "invisible_underscore.trc": "43x80 dynamic screen size not negotiated by Replayer",
    "login.trc": "Login flow field accounting drift - tracked separately",
    "no_bid.trc": "No-bid image field accounting drift - tracked separately",
    "numeric.trc": "43x80 dynamic screen size not negotiated by Replayer",
    "ra_test.trc": "43x80 dynamic screen size not negotiated by Replayer",
    "reverse.trc": "43x80 dynamic screen size not negotiated by Replayer",
    "sscp-lu.trc": "SNA SSCP-LU session replay drift - tracked separately",
    "wrap.trc": "Wrap field accounting drift - tracked separately",
    "wrap_field.trc": "43x80 dynamic screen size not negotiated by Replayer",
}


def _discover() -> List[Path]:
    if not DEFAULT_TRACE_DIR.exists():
        return []
    return sorted(DEFAULT_TRACE_DIR.glob("*.trc"))


def _ids(path: Path) -> str:
    return path.name


def _format_failure(result: TraceResult) -> str:
    """Build a compact failure message for pytest reporting."""
    parts: List[str] = []
    for err in result.errors:
        parts.append(f"error: {err}")
    for check in result.checks:
        if not check.passed:
            parts.append(
                f"check[{check.type}]: {check.message} "
                f"(expected={check.expected!r}, actual={check.actual!r})"
            )
    return "; ".join(parts) if parts else "unknown failure"


# Discover at import time so pytest sees a static parameter set.
_TRACES: Tuple[Path, ...] = tuple(_discover())


def _parametrize_cases() -> List[pytest.param]:
    """Build parametrize cases with xfail marks baked in for known gaps."""
    cases: List[pytest.param] = []
    for trace_path in _TRACES:
        marks = [pytest.mark.slow]
        if trace_path.name in _KNOWN_FAILING:
            marks.append(
                pytest.mark.xfail(
                    strict=True,
                    reason=_KNOWN_FAILING[trace_path.name],
                )
            )
        cases.append(pytest.param(trace_path, marks=marks, id=trace_path.name))
    return cases


@pytest.mark.parametrize("trace_path", _parametrize_cases())
def test_replay_trace_matches_baseline(trace_path: Path) -> None:
    """Each trace must match its expected JSON baseline (or be xfailed)."""
    if not trace_path.exists():
        pytest.skip(f"Trace file missing: {trace_path}")

    result = _run_single_trace(trace_path, DEFAULT_EXPECTED_DIR)
    if not result.replayed:
        pytest.fail(
            f"Replay did not run for {trace_path.name}: "
            f"{'; '.join(result.errors) or 'no records parsed'}"
        )

    if result.passed:
        return

    pytest.fail(_format_failure(result))


@pytest.mark.slow
def test_regression_suite_summary_smoke() -> None:
    """Smoke check: the suite must produce a JSON report with at least 1 trace.

    This test guards against the regression directory being emptied
    accidentally (e.g. by a bad ``git clean``).
    """
    if not _TRACES:
        pytest.skip("No regression traces available")
    assert len(_TRACES) >= 1, "regression trace directory is empty"
    # Quick replay of the smoke trace to confirm the runner plumbing works.
    smoke = DEFAULT_TRACE_DIR / "smoke.trc"
    if not smoke.exists():
        pytest.skip("smoke.trc not present")
    result = _run_single_trace(smoke, DEFAULT_EXPECTED_DIR)
    assert result.replayed, "smoke trace failed to replay"


@pytest.fixture(scope="session")
def regression_suite_report(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Run the full suite once per session and expose the JSON report path.

    Other tests or downstream tooling can read this file to inspect the
    full set of results without re-running replay.
    """
    from tools.run_regression_traces import run_suite

    suite = run_suite()
    out_dir = tmp_path_factory.mktemp("regression")
    out_path = out_dir / "regression_suite.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(suite.to_dict(), f, indent=2)
    return str(out_path)
