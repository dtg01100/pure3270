#!/usr/bin/env python3
"""
Batch comparison script to run the comparison tool across multiple trace files and collect results.

This script:
- Discovers all .trc files in tests/data/traces/
- Runs comparison for each trace using compare_replay_with_s3270.py logic
- Collects results in a structured format
- Outputs summary to JSON and console

Usage:
    python tools/batch_compare_traces.py [--output results.json] [--s3270-path /path/to/s3270]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.compare_replay_with_s3270 import compare_trace, find_real_s3270

logger = logging.getLogger("batch_compare")


class BatchResult:
    """Container for batch comparison results."""

    def __init__(self) -> None:
        self.results: List[Dict[str, Any]] = []
        self.summary = {
            "total_traces": 0,
            "matches": 0,
            "differences": 0,
            "errors": 0,
            "s3270_available": False,
        }

    def add_result(
        self,
        trace_path: str,
        status: str,
        diff: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Add a single trace result."""
        result = {
            "trace": trace_path,
            "status": status,
        }
        if diff:
            result["diff"] = diff
        if error:
            result["error"] = error

        self.results.append(result)

        if status == "match":
            self.summary["matches"] += 1
        elif status == "difference":
            self.summary["differences"] += 1
        elif status == "error":
            self.summary["errors"] += 1

    def set_s3270_available(self, available: bool) -> None:
        """Set whether real s3270 was available for comparison."""
        self.summary["s3270_available"] = available

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": self.summary,
            "results": self.results,
        }


async def run_batch_comparison(
    traces_dir: Path,
    s3270_path: Optional[Path],
    base_port: int = 23230,
    delay: float = 1.0,
) -> BatchResult:
    """Run comparison across all traces in the directory."""
    result = BatchResult()
    result.set_s3270_available(s3270_path is not None)

    # Find all .trc files
    trace_files = list(traces_dir.glob("*.trc"))
    result.summary["total_traces"] = len(trace_files)

    if not trace_files:
        logger.warning("No .trc files found in %s", traces_dir)
        return result

    logger.info("Found %d trace files to compare", len(trace_files))

    # Run comparisons sequentially to avoid port conflicts
    for i, trace_path in enumerate(sorted(trace_files)):
        port = base_port + i
        trace_name = trace_path.name

        logger.info("Comparing trace: %s (port %d)", trace_name, port)

        try:
            # Capture the comparison result
            # Since compare_trace prints to stdout, we need to capture it
            # But for simplicity, we'll modify to return more structured data
            rc = await compare_trace(trace_path, port, s3270_path, delay=delay)

            if rc == 0:
                status = "match" if s3270_path else "no_reference"
                result.add_result(trace_name, status)
            elif rc == 1:
                status = "difference"
                # Note: diff is printed to stdout, but for batch we might want to capture it
                # For now, just record the status
                result.add_result(trace_name, status)
            else:
                result.add_result(
                    trace_name, "error", error=f"Unexpected return code: {rc}"
                )

        except Exception as e:
            logger.error("Error comparing %s: %s", trace_name, e)
            result.add_result(trace_name, "error", error=str(e))

    return result


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Batch compare pure3270 vs s3270 across multiple traces"
    )
    ap.add_argument(
        "--traces-dir",
        default="tests/data/traces",
        help="Directory containing .trc files",
    )
    ap.add_argument(
        "--output", default="batch_comparison_results.json", help="Output JSON file"
    )
    ap.add_argument("--s3270-path", default=None, help="Path to real s3270 binary")
    ap.add_argument(
        "--base-port", type=int, default=23230, help="Starting port for replay servers"
    )
    ap.add_argument(
        "--delay", type=float, default=1.0, help="Seconds to wait before capture"
    )
    ap.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return ap.parse_args(argv)


async def amain(ns: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.DEBUG if ns.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    traces_dir = Path(ns.traces_dir).resolve()
    if not traces_dir.exists() or not traces_dir.is_dir():
        print(f"Traces directory not found: {traces_dir}", file=sys.stderr)
        return 1

    real_s3270 = find_real_s3270(ns.s3270_path)
    if real_s3270 is None:
        logger.warning(
            "Real s3270 binary not found. Comparisons will skip reference side."
        )
    else:
        logger.info("Using real s3270 at: %s", real_s3270)

    # Run batch comparison
    result = await run_batch_comparison(traces_dir, real_s3270, ns.base_port, ns.delay)

    # Output results
    output_data = result.to_dict()

    # Write to file
    with open(ns.output, "w") as f:
        json.dump(output_data, f, indent=2)

    # Print summary to console
    summary = output_data["summary"]
    print(f"\nBatch Comparison Summary:")
    print(f"Total traces: {summary['total_traces']}")
    print(f"Matches: {summary['matches']}")
    print(f"Differences: {summary['differences']}")
    print(f"Errors: {summary['errors']}")
    print(f"s3270 available: {summary['s3270_available']}")
    print(f"Results saved to: {ns.output}")

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    ns = parse_args(argv)
    return asyncio.run(amain(ns))


if __name__ == "__main__":
    sys.exit(main())
