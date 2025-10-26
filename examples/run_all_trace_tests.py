#!/usr/bin/env python3
"""
Comprehensive trace-based testing using s3270 reference traces.

This script:
1. Finds all .trc files from the x3270 reference implementation
2. Runs each trace through the trace replay server
3. Compares pure3270 behavior against expected s3270 behavior
4. Reports differences and coverage metrics

Usage:
    python examples/run_all_trace_tests.py [options]

Examples:
    # Run all traces
    python examples/run_all_trace_tests.py

    # Run specific trace
    python examples/run_all_trace_tests.py --trace reference/x3270-main/b3270/Test/reverse.trc

    # Run with detailed output
    python examples/run_all_trace_tests.py --verbose
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def find_all_trace_files() -> List[Path]:
    """Find all .trc files in the local traces directory."""
    # First try local traces directory (preferred)
    traces_dir = Path("tests/data/traces")
    if traces_dir.exists():
        trace_files = list(traces_dir.glob("*.trc"))
        if trace_files:
            return sorted(trace_files)

    # Fallback to reference directory if available
    ref_dir = Path("reference/x3270-main")
    if ref_dir.exists():
        trace_files = list(ref_dir.glob("**/*.trc"))
        return sorted(trace_files)

    return []


async def wait_for_server(host: str, port: int, timeout: float = 10.0) -> bool:
    """Wait for server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=1.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (ConnectionRefusedError, OSError, asyncio.TimeoutError):
            await asyncio.sleep(0.2)
    return False


def run_trace_test(
    trace_file: Path, host: str, port: int, verbose: bool = False
) -> Dict[str, Any]:
    """Run a single trace file test."""
    result = {
        "trace_file": str(trace_file),
        "name": trace_file.stem,
        "success": False,
        "error": None,
        "duration": 0.0,
    }

    start = time.time()

    try:
        # Use the existing trace replay tools
        cmd = [
            sys.executable,
            "tools/test_trace_replay.py",
            str(trace_file),
            "--host",
            host,
            "--port",
            str(port),
        ]

        if verbose:
            print(f"Running: {' '.join(cmd)}")

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30.0)

        result["success"] = proc.returncode == 0
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr

        if proc.returncode != 0 and verbose:
            print(f"  FAILED: {trace_file.name}")
            if proc.stderr:
                print(f"  Error: {proc.stderr[:200]}")

    except subprocess.TimeoutExpired:
        result["error"] = "timeout"
    except Exception as e:
        result["error"] = str(e)

    result["duration"] = time.time() - start
    return result


async def run_all_tests(
    trace_files: List[Path], host: str, port: int, verbose: bool = False
) -> List[Dict[str, Any]]:
    """Run all trace tests."""
    results = []

    print(f"\nRunning {len(trace_files)} trace tests...")
    print("=" * 60)

    for i, trace_file in enumerate(trace_files, 1):
        if verbose:
            print(f"\n[{i}/{len(trace_files)}] {trace_file.name}")
        else:
            print(f"[{i}/{len(trace_files)}] {trace_file.name}...", end=" ", flush=True)

        result = run_trace_test(trace_file, host, port, verbose)
        results.append(result)

        if not verbose:
            status = "✓" if result["success"] else "✗"
            print(status)

    return results


def generate_report(results: List[Dict[str, Any]], output_dir: Path):
    """Generate test report."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Count results
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed

    # JSON report
    json_path = output_dir / "trace_test_results.json"
    with open(json_path, "w") as f:
        json.dump(
            {
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "pass_rate": f"{100.0 * passed / total if total > 0 else 0:.1f}%",
                },
                "results": results,
            },
            f,
            indent=2,
        )

    # Text summary
    summary_path = output_dir / "trace_test_summary.txt"
    with open(summary_path, "w") as f:
        f.write("Trace-Based Test Summary\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total tests: {total}\n")
        f.write(f"Passed: {passed}\n")
        f.write(f"Failed: {failed}\n")
        f.write(f"Pass rate: {100.0 * passed / total if total > 0 else 0:.1f}%\n\n")

        if failed > 0:
            f.write("\nFailed Tests:\n")
            f.write("-" * 60 + "\n")
            for r in results:
                if not r["success"]:
                    f.write(f"- {r['name']}: {r.get('error', 'test failed')}\n")

        # Category breakdown
        f.write("\n\nBy Category:\n")
        f.write("-" * 60 + "\n")
        categories = {}
        for r in results:
            trace_path = Path(r["trace_file"])
            category = trace_path.parent.name
            if category not in categories:
                categories[category] = {"total": 0, "passed": 0}
            categories[category]["total"] += 1
            if r["success"]:
                categories[category]["passed"] += 1

        for cat, stats in sorted(categories.items()):
            rate = 100.0 * stats["passed"] / stats["total"] if stats["total"] > 0 else 0
            f.write(f"{cat}: {stats['passed']}/{stats['total']} ({rate:.1f}%)\n")

    print(f"\n\nReports written to {output_dir}/:")
    print(f"  - trace_test_results.json")
    print(f"  - trace_test_summary.txt")

    return passed, failed


async def run_with_server(args):
    """Run tests with trace replay server."""
    # Find trace files
    if args.trace:
        trace_files = [Path(args.trace)]
    else:
        trace_files = find_all_trace_files()

    if not trace_files:
        print("ERROR: No trace files found")
        print("Make sure reference/x3270-main directory exists with .trc files")
        return 1

    print("=" * 60)
    print("Trace-Based Testing Suite")
    print("=" * 60)
    print(f"Trace files: {len(trace_files)}")
    print(f"Server: {args.host}:{args.port}")
    print()

    # Start trace replay server with first trace
    # (We'll use the existing server infrastructure)

    # Run tests
    results = await run_all_tests(trace_files, args.host, args.port, args.verbose)

    # Generate report
    passed, failed = generate_report(results, Path(args.output))

    # Summary
    print("\n" + "=" * 60)
    print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    print(f"Pass rate: {100.0 * passed / len(results) if results else 0:.1f}%")
    print("=" * 60)

    return 0 if failed == 0 else 1


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive trace-based tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--trace", help="Run specific trace file")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=2323, help="Server port (default: 2323)"
    )
    parser.add_argument(
        "--output",
        default="test_output",
        help="Output directory (default: test_output)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        exit_code = asyncio.run(run_with_server(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(130)


if __name__ == "__main__":
    main()
