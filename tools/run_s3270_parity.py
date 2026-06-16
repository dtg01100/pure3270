#!/usr/bin/env python3
"""
Run pure3270-vs-s3270 parity checks for a curated set of regression traces.

This is the batch driver used by ``.github/workflows/nightly-s3270-parity.yml``.
For every trace in the key trace set it:
  1. spins up a local TraceReplayServer
  2. connects with both pure3270 and the real s3270 (if available)
  3. captures the screen text
  4. emits a unified diff
  5. records the result in a JSON report

Traces that match s3270 are reported as ``parity: true``; mismatches are
``parity: false`` and the diff is included for triage.  The script never
fails the build on its own -- the calling workflow decides what to do
with the JSON.
"""

from __future__ import annotations

import argparse
import asyncio
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

from tools.compare_replay_with_s3270 import (  # noqa: E402
    find_real_s3270,
    normalize_screen_text,
    run_pure3270_capture,
    run_real_s3270_capture,
)
from tools.trace_replay_server import TraceReplayServer  # noqa: E402

logger = logging.getLogger("s3270_parity")

DEFAULT_OUTPUT = ROOT / "test_output" / "s3270_parity_report.json"

# Curated set of regression traces that exercise the most representative
# negotiation and screen-rendering paths.  Kept small to keep the nightly
# job under a few minutes.
KEY_TRACES: List[str] = [
    "smoke.trc",
    "login.trc",
    "tn3270e-renegotiate.trc",
    "elf.trc",
    "wrap.trc",
    "wrap_field.trc",
    "nvt-data.trc",
    "korean.trc",
    "sscp-lu.trc",
]


@dataclass
class ParityResult:
    trace: str
    parity: Optional[bool]
    s3270_available: bool
    duration_seconds: float
    pure_screen: str = ""
    s3270_screen: str = ""
    diff: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ParityReport:
    s3270_path: Optional[str]
    total: int
    matched: int
    mismatched: int
    skipped: int
    errors: int
    duration_seconds: float
    results: List[ParityResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "s3270_path": self.s3270_path,
            "summary": {
                "total": self.total,
                "matched": self.matched,
                "mismatched": self.mismatched,
                "skipped": self.skipped,
                "errors": self.errors,
                "duration_seconds": self.duration_seconds,
            },
            "results": [r.to_dict() for r in self.results],
        }


async def _capture_pair(
    trace_path: Path,
    port: int,
    s3270_path: Optional[Path],
    delay: float,
    capture_timeout: float,
) -> ParityResult:
    """Capture screens from pure3270 and (optionally) s3270, then compare."""
    start = time.monotonic()
    server = TraceReplayServer(str(trace_path), loop_mode=False, compat_handshake=False)
    server_task = asyncio.create_task(server.start_server(host="127.0.0.1", port=port))
    await asyncio.sleep(0.2)

    result = ParityResult(
        trace=trace_path.name,
        parity=None,
        s3270_available=s3270_path is not None,
        duration_seconds=0.0,
    )

    try:
        is_printer = trace_path.name == "smoke.trc"
        pure3270_terminal = "IBM-3278-2" if is_printer else "IBM-3278-4"
        try:
            p_screen = await asyncio.wait_for(
                run_pure3270_capture(
                    "127.0.0.1",
                    port,
                    delay=delay,
                    is_printer=is_printer,
                    terminal_type=pure3270_terminal,
                ),
                timeout=capture_timeout,
            )
        except asyncio.TimeoutError:
            result.error = "pure3270 capture timed out"
            return result
        except Exception as exc:  # pragma: no cover - defensive
            result.error = f"pure3270 capture raised {type(exc).__name__}: {exc}"
            return result
        p_norm = normalize_screen_text(p_screen)
        result.pure_screen = p_norm

        if s3270_path is None:
            result.parity = None  # s3270 missing: can't compare
            return result

        s3270_model = "3278-2" if is_printer else "3278-4"
        try:
            s_out, _ = await asyncio.wait_for(
                run_real_s3270_capture(
                    s3270_path,
                    "127.0.0.1",
                    port,
                    delay=delay,
                    model=s3270_model,
                ),
                timeout=capture_timeout,
            )
        except asyncio.TimeoutError:
            result.error = "s3270 capture timed out"
            return result
        except Exception as exc:  # pragma: no cover - defensive
            result.error = f"s3270 capture raised {type(exc).__name__}: {exc}"
            return result

        s_lines = [
            ln[len("data:") :].lstrip()
            for ln in s_out.splitlines()
            if ln.startswith("data:")
        ]
        s_text = "\n".join(s_lines) if s_lines else s_out
        s_norm = normalize_screen_text(s_text)
        result.s3270_screen = s_norm

        if p_norm == s_norm:
            result.parity = True
        else:
            result.parity = False
            import difflib

            result.diff = list(
                difflib.unified_diff(
                    s_norm.splitlines(),
                    p_norm.splitlines(),
                    fromfile="s3270",
                    tofile="pure3270",
                    lineterm="",
                )
            )
    finally:
        try:
            server_task.cancel()
            import contextlib

            with contextlib.suppress(asyncio.CancelledError, Exception):
                await server_task
        except Exception:  # pragma: no cover - defensive
            pass
        result.duration_seconds = time.monotonic() - start

    return result


async def _run_batch(
    trace_dir: Path,
    s3270_path: Optional[Path],
    traces: List[str],
    base_port: int,
    delay: float,
    capture_timeout: float,
) -> ParityReport:
    start = time.monotonic()
    results: List[ParityResult] = []
    for i, name in enumerate(traces):
        trace_path = trace_dir / name
        if not trace_path.exists():
            results.append(
                ParityResult(
                    trace=name,
                    parity=None,
                    s3270_available=s3270_path is not None,
                    duration_seconds=0.0,
                    error=f"trace not found: {trace_path}",
                )
            )
            continue
        port = base_port + i
        logger.info("▶ %s on port %d", name, port)
        results.append(
            await _capture_pair(trace_path, port, s3270_path, delay, capture_timeout)
        )

    duration = time.monotonic() - start
    matched = sum(1 for r in results if r.parity is True)
    mismatched = sum(1 for r in results if r.parity is False)
    skipped = sum(1 for r in results if r.parity is None and not r.error)
    errors = sum(1 for r in results if r.error is not None)
    return ParityReport(
        s3270_path=str(s3270_path) if s3270_path else None,
        total=len(results),
        matched=matched,
        mismatched=mismatched,
        skipped=skipped,
        errors=errors,
        duration_seconds=duration,
        results=results,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run pure3270-vs-s3270 parity checks against key traces",
    )
    p.add_argument(
        "--trace-dir",
        type=Path,
        default=ROOT / "tests" / "data" / "traces",
    )
    p.add_argument(
        "--s3270-path",
        type=str,
        default=None,
        help="Path to real s3270 binary (auto-detected if omitted)",
    )
    p.add_argument(
        "--traces",
        nargs="*",
        default=KEY_TRACES,
        help="Trace filenames to compare (default: curated key set)",
    )
    p.add_argument(
        "--base-port",
        type=int,
        default=23400,
        help="Base port for replay servers; one per trace",
    )
    p.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait for screen capture",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-capture timeout in seconds",
    )
    p.add_argument(
        "--report-json",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any trace mismatches or errors",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    s3270 = find_real_s3270(args.s3270_path)
    if s3270 is None:
        logger.warning(
            "Real s3270 not found; running pure3270-only side of the comparison"
        )
    else:
        logger.info("Using s3270 at: %s", s3270)

    report = asyncio.run(
        _run_batch(
            trace_dir=args.trace_dir,
            s3270_path=s3270,
            traces=args.traces,
            base_port=args.base_port,
            delay=args.delay,
            capture_timeout=args.timeout,
        )
    )

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    with args.report_json.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)
    print(f"📄 Parity report written to {args.report_json}")

    summary = (
        f"\n=== s3270 Parity Summary ===\n"
        f"Total: {report.total}  Matched: {report.matched}  "
        f"Mismatched: {report.mismatched}  Skipped: {report.skipped}  "
        f"Errors: {report.errors}\n"
    )
    print(summary)
    for r in report.results:
        status = "OK" if r.parity else ("DIFF" if r.parity is False else "SKIP")
        marker = "✅" if r.parity else ("❌" if r.parity is False else "⚠️")
        line = f"  {marker} {status:4s}  {r.trace}  ({r.duration_seconds:.2f}s)"
        if r.error:
            line += f"  err: {r.error}"
        print(line)
        if r.parity is False and r.diff:
            for d in r.diff[:20]:
                print(f"        {d}")
            if len(r.diff) > 20:
                print(f"        ... ({len(r.diff) - 20} more diff lines)")

    if args.strict and (report.mismatched > 0 or report.errors > 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
