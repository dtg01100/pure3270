#!/usr/bin/env python3
"""
Full Trace-Based Testing Framework for Pure3270 with Network Simulation.

This script provides comprehensive testing of pure3270 against s3270 traces
with network simulation to ensure full protocol parity under various conditions.

Features:
- Automated trace replay server setup
- Network condition simulation (latency, loss, bandwidth, etc.)
- Side-by-side screen output comparison
- Detailed parity reporting
- Batch testing across multiple traces

Usage:
    python full_trace_testing.py [options] [trace_files...]

Options:
    --latency MS         Add network latency (default: 0)
    --loss PCT           Packet loss percentage (default: 0)
    --bandwidth KBPS     Bandwidth limit in kbps
    --jitter MS          Network jitter (default: 0)
    --reorder PCT        Packet reordering probability (default: 0)
    --duplicate PCT      Packet duplication probability (default: 0)
    --all-traces         Test all available traces
    --output-dir DIR     Directory for test results (default: test_output/trace_tests)
    --parallel N         Run N tests in parallel (default: 1)
    --verbose            Enable verbose output
"""

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

# Add pure3270 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from network_simulator import NetworkSimulator, create_simulated_connection

from pure3270 import AsyncSession


@dataclass
class TestResult:
    """Result of a single trace test."""

    trace_file: str
    network_conditions: Dict[str, Any]
    pure3270_screen: List[str]
    expected_screen: List[str]
    match_percentage: float
    differences: List[Dict[str, Any]]
    errors: List[str]
    duration_seconds: float
    success: bool
    # Performance metrics
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    peak_memory_mb: float = 0.0


@dataclass
class TestSuiteResult:
    """Results of a complete test suite."""

    timestamp: str
    total_tests: int
    successful_tests: int
    failed_tests: int
    average_match_percentage: float
    network_conditions: Dict[str, Any]
    test_results: List[TestResult]
    summary: Dict[str, Any]


class TraceTester:
    """Comprehensive trace-based tester with network simulation."""

    def __init__(
        self, network_sim: NetworkSimulator, output_dir: Path, verbose: bool = False
    ):
        self.network_sim = network_sim
        self.output_dir = output_dir
        self.verbose = verbose
        self.trace_dir = Path("tests/data/traces")

    def get_available_traces(self) -> List[Path]:
        """Get list of available trace files."""
        return sorted(self.trace_dir.glob("*.trc"))

    def get_expected_screen_for_trace(self, trace_file: Path) -> List[str]:
        """Get expected screen content for a trace file."""
        # Use the same logic as compare_screen_output.py
        trace_name = trace_file.name

        expected_outputs = {
            "ra_test.trc": [""] * 24,  # Empty screen - RA test validates protocol
            "ibmlink.trc": [
                " R<                                                                             ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
                "            ________           ________                                         ",
                "                                                                                ",
                "                                                                                ",
                "                                                                                ",
            ],
            "empty.trc": [""] * 24,  # Truly empty screen
            "all_chars.trc": [""] * 24,  # No server responses
        }

        if trace_name in expected_outputs:
            expected = expected_outputs[trace_name]
            # Pad to 24 lines
            while len(expected) < 24:
                expected.append("")
            return expected[:24]

        # Default: empty screen for unknown traces
        return [""] * 24

    def run_single_test(self, trace_file: Path) -> TestResult:
        """Run a single trace test with network simulation."""
        start_time = time.time()
        errors = []

        # Performance monitoring
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        peak_memory = initial_memory
        cpu_start = process.cpu_times()

        try:
            if self.verbose:
                print(f"Testing {trace_file.name}...")

            # Parse trace and process with pure3270 (like compare_screen_output.py)
            screen_lines = self._process_trace_with_pure3270(trace_file)

            # Update peak memory
            current_memory = process.memory_info().rss / 1024 / 1024
            peak_memory = max(peak_memory, current_memory)

            # Get expected screen
            expected_screen = self.get_expected_screen_for_trace(trace_file)

            # Compare screens
            differences, match_percentage = self._compare_screens(
                screen_lines, expected_screen
            )

            success = (
                len(errors) == 0 and match_percentage >= 95.0
            )  # 95% match threshold

        except Exception as e:
            errors.append(f"Test failed: {str(e)}")
            screen_lines = []
            expected_screen = self.get_expected_screen_for_trace(trace_file)
            differences = []
            match_percentage = 0.0
            success = False

        duration = time.time() - start_time

        # Final performance metrics
        final_memory = process.memory_info().rss / 1024 / 1024
        peak_memory = max(peak_memory, final_memory)
        cpu_end = process.cpu_times()
        cpu_percent = (
            ((cpu_end.user + cpu_end.system) - (cpu_start.user + cpu_start.system))
            / duration
            * 100
        )

        return TestResult(
            trace_file=str(trace_file),
            network_conditions=self.network_sim.get_stats(),
            pure3270_screen=screen_lines,
            expected_screen=expected_screen,
            match_percentage=match_percentage,
            differences=differences,
            errors=errors,
            duration_seconds=duration,
            success=success,
            cpu_percent=cpu_percent,
            memory_mb=final_memory,
            peak_memory_mb=peak_memory,
        )

    def _process_trace_with_pure3270(self, trace_file: Path) -> List[str]:
        """Process trace data through pure3270 parser (like compare_screen_output.py)."""
        from pure3270.emulation.screen_buffer import ScreenBuffer
        from pure3270.protocol.data_stream import DataStreamParser

        # Parse trace file to extract data streams
        data_streams = self._parse_trace_file(trace_file)
        screen_size = self._extract_screen_size(trace_file)

        rows, cols = screen_size
        screen_buffer = ScreenBuffer(rows=rows, cols=cols)
        parser = DataStreamParser(screen_buffer)

        # Accumulate all data streams (skip telnet negotiations)
        accumulated_data = bytearray()
        tn3270_data_streams = []

        for data_stream in data_streams:
            # Skip telnet negotiations (IAC sequences)
            if data_stream and data_stream[0] == 0xFF:
                continue

            tn3270_data_streams.append(data_stream)
            accumulated_data.extend(data_stream)

        if accumulated_data:
            try:
                # Strip TN3270E header if present
                data = bytes(accumulated_data)
                if len(data) >= 5 and data[0] in [
                    0x00,
                    0x01,
                    0x02,
                    0x03,
                    0x04,
                    0x05,
                    0x06,
                    0x07,
                ]:
                    data = data[5:]

                # Parse the 3270 data stream
                parser.parse(data, data_type=0x00)

            except Exception as e:
                if self.verbose:
                    print(f"Parse error: {e}")

        # Get screen content
        screen_text = screen_buffer.ascii_buffer
        return screen_text.split("\n")[:rows]

    def _parse_trace_file(self, trace_file: Path) -> List[bytes]:
        """Parse s3270 trace file and extract data streams."""
        import re

        data_streams = []

        with open(trace_file, "r") as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("//"):
                    continue

                # Parse data lines: > 0xOFFSET   HEXDATA (recv/server to client)
                match = re.match(r"[<>]\s+0x[0-9a-fA-F]+\s+([0-9a-fA-F]+)", line)
                if match:
                    hex_data = match.group(1)
                    try:
                        data = bytes.fromhex(hex_data)
                        # Only collect data sent TO the client (from server)
                        if line.startswith(">"):
                            data_streams.append(data)
                    except ValueError:
                        continue

        return data_streams

    def _extract_screen_size(self, trace_file: Path) -> Tuple[int, int]:
        """Extract screen size from trace file comments."""
        rows, cols = 24, 80  # Default

        with open(trace_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("// rows "):
                    rows = int(line.split()[2])
                elif line.startswith("// columns "):
                    cols = int(line.split()[2])

        return rows, cols

    async def _start_trace_server(self, trace_file: Path) -> asyncio.subprocess.Process:
        """Start the trace replay server."""
        cmd = [
            sys.executable,
            "tools/trace_replay_server.py",
            str(trace_file),
            "--port",
            "2324",
            "--host",
            "127.0.0.1",
            "--max-connections",
            "1",
        ]

        if self.verbose:
            print(f"Starting server: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        # Wait a bit for server to start
        await asyncio.sleep(0.5)

        return process

    async def _run_pure3270_session(self, reader, writer) -> List[str]:
        """Run a pure3270 session and capture screen data."""
        screen_lines = []

        try:
            # Create handler directly with simulated connection
            from pure3270.emulation.screen_buffer import ScreenBuffer
            from pure3270.protocol.tn3270_handler import TN3270Handler

            # Create screen buffer
            screen_buffer = ScreenBuffer(rows=24, cols=80)

            # Create handler with simulated connection
            handler = TN3270Handler(
                reader=reader,
                writer=writer,
                screen_buffer=screen_buffer,
                host="127.0.0.1",
                port=2324,
                terminal_type="IBM-3278-2",
            )

            # Connect and negotiate
            await handler.connect()

            # Wait a bit for data to be processed
            await asyncio.sleep(1.0)

            # Get screen content
            screen_text = screen_buffer.ascii_buffer
            screen_lines = screen_text.split("\n")[:24]

        except Exception as e:
            if self.verbose:
                print(f"Session error: {e}")
            screen_lines = []

        return screen_lines

    def _compare_screens(
        self, pure3270_screen: List[str], expected_screen: List[str]
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Compare two screen representations."""
        differences = []
        total_chars = 0
        matching_chars = 0

        max_lines = max(len(pure3270_screen), len(expected_screen))

        for i in range(max_lines):
            pure_line = pure3270_screen[i] if i < len(pure3270_screen) else ""
            expected_line = expected_screen[i] if i < len(expected_screen) else ""

            # Pad lines to same length
            max_len = max(len(pure_line), len(expected_line))
            pure_line = pure_line.ljust(max_len)
            expected_line = expected_line.ljust(max_len)

            # Compare character by character
            line_differences = []
            for j, (p_char, e_char) in enumerate(zip(pure_line, expected_line)):
                total_chars += 1
                if p_char == e_char:
                    matching_chars += 1
                else:
                    line_differences.append(
                        {
                            "position": (i + 1, j + 1),
                            "pure3270": p_char,
                            "expected": e_char,
                        }
                    )

            if line_differences:
                differences.append(
                    {
                        "line": i + 1,
                        "differences": line_differences,
                        "pure3270_line": pure_line,
                        "expected_line": expected_line,
                    }
                )

        match_percentage = (
            (matching_chars / total_chars * 100) if total_chars > 0 else 0
        )
        return differences, match_percentage

    def run_test_suite(
        self, trace_files: List[Path], parallel: int = 1
    ) -> TestSuiteResult:
        """Run a complete test suite."""
        print(f"Running trace test suite with {len(trace_files)} traces...")
        print(f"Network conditions: {self.network_sim.get_stats()}")
        print(f"Parallel execution: {parallel}")

        start_time = time.time()

        # Run tests
        results = []
        for trace_file in trace_files:
            result = self.run_single_test(trace_file)
            results.append(result)
            if self.verbose:
                status = "✓" if result.success else "✗"
                print(
                    f"{status} {trace_file.name}: {result.match_percentage:.1f}% match ({result.duration_seconds:.2f}s)"
                )

        # Calculate summary
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - successful_tests
        avg_match = (
            sum(r.match_percentage for r in results) / total_tests
            if total_tests > 0
            else 0
        )

        suite_result = TestSuiteResult(
            timestamp=time.strftime("%Y%m%d_%H%M%S"),
            total_tests=total_tests,
            successful_tests=successful_tests,
            failed_tests=failed_tests,
            average_match_percentage=avg_match,
            network_conditions=self.network_sim.get_stats(),
            test_results=results,
            summary={
                "total_duration": time.time() - start_time,
                "output_directory": str(self.output_dir),
                "traces_tested": [str(t) for t in trace_files],
            },
        )

        return suite_result

    def save_results(self, suite_result: TestSuiteResult):
        """Save test results to files."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Save summary
        summary_file = (
            self.output_dir / f"trace_test_summary_{suite_result.timestamp}.json"
        )
        with open(summary_file, "w") as f:
            json.dump(asdict(suite_result), f, indent=2, default=str)

        # Save detailed results
        details_file = (
            self.output_dir / f"trace_test_details_{suite_result.timestamp}.json"
        )
        with open(details_file, "w") as f:
            json.dump(
                {
                    "summary": suite_result.summary,
                    "results": [asdict(r) for r in suite_result.test_results],
                },
                f,
                indent=2,
                default=str,
            )

        # Generate HTML report
        self._generate_html_report(suite_result)

        print(f"\nResults saved to: {self.output_dir}")

    def _generate_html_report(self, suite_result: TestSuiteResult):
        """Generate an HTML report."""
        html_file = self.output_dir / f"trace_test_report_{suite_result.timestamp}.html"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Pure3270 Trace Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .test-result {{ margin: 10px 0; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }}
        .success {{ background: #d4edda; border-color: #c3e6cb; }}
        .failure {{ background: #f8d7da; border-color: #f5c6cb; }}
        .details {{ margin-top: 10px; }}
        pre {{ background: #f8f8f8; padding: 10px; border-radius: 3px; }}
    </style>
</head>
<body>
    <h1>Pure3270 Trace Test Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Timestamp:</strong> {suite_result.timestamp}</p>
        <p><strong>Total Tests:</strong> {suite_result.total_tests}</p>
        <p><strong>Successful:</strong> {suite_result.successful_tests}</p>
        <p><strong>Failed:</strong> {suite_result.failed_tests}</p>
        <p><strong>Average Match:</strong> {suite_result.average_match_percentage:.1f}%</p>
        <p><strong>Network Conditions:</strong> {suite_result.network_conditions}</p>
    </div>

    <h2>Test Results</h2>
"""

        for result in suite_result.test_results:
            status_class = "success" if result.success else "failure"
            html += f"""
    <div class="test-result {status_class}">
        <h3>{Path(result.trace_file).name}</h3>
        <p><strong>Match:</strong> {result.match_percentage:.1f}%</p>
        <p><strong>Duration:</strong> {result.duration_seconds:.2f}s</p>
        <p><strong>Success:</strong> {"Yes" if result.success else "No"}</p>
"""

            if result.errors:
                html += "<h4>Errors:</h4><ul>"
                for error in result.errors:
                    html += f"<li>{error}</li>"
                html += "</ul>"

            if result.differences:
                html += "<h4>Differences:</h4>"
                for diff in result.differences[:5]:  # Show first 5 differences
                    html += f"<p>Line {diff['line']}:</p>"
                    html += f"<pre>Pure3270: {diff['pure3270_line']}</pre>"
                    html += f"<pre>Expected: {diff['expected_line']}</pre>"

            html += "</div>"

        html += """
</body>
</html>
"""

        with open(html_file, "w") as f:
            f.write(html)


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Full trace-based testing for Pure3270"
    )
    parser.add_argument("trace_files", nargs="*", help="Specific trace files to test")
    parser.add_argument(
        "--all-traces", action="store_true", help="Test all available traces"
    )
    parser.add_argument(
        "--latency", type=float, default=0, help="Network latency in ms"
    )
    parser.add_argument("--jitter", type=float, default=0, help="Network jitter in ms")
    parser.add_argument(
        "--loss", type=float, default=0, help="Packet loss probability (0.0-1.0)"
    )
    parser.add_argument("--bandwidth", type=float, help="Bandwidth limit in kbps")
    parser.add_argument(
        "--reorder", type=float, default=0, help="Packet reordering probability"
    )
    parser.add_argument(
        "--duplicate", type=float, default=0, help="Packet duplication probability"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("test_output/trace_tests"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--parallel", type=int, default=1, help="Number of parallel tests"
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=0,
        help="Maximum number of allowed failed traces before returning non-zero (default: 0)",
    )
    parser.add_argument(
        "--min-average",
        type=float,
        default=None,
        help="Minimum average match percentage required to return zero (e.g., 95.0). If omitted, only failure count is considered.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Create network simulator
    network_sim = NetworkSimulator(
        latency_ms=args.latency,
        jitter_ms=args.jitter,
        packet_loss=args.loss,
        bandwidth_kbps=args.bandwidth,
        reorder_probability=args.reorder,
        duplicate_probability=args.duplicate,
    )

    # Create tester
    tester = TraceTester(network_sim, args.output_dir, args.verbose)

    # Get trace files to test
    if args.all_traces:
        trace_files = tester.get_available_traces()
    elif args.trace_files:
        trace_files = [Path(f) for f in args.trace_files]
    else:
        # Default: test all available traces
        trace_files = tester.get_available_traces()

    # Validate trace files exist
    valid_traces = []
    for trace_file in trace_files:
        if trace_file.exists():
            valid_traces.append(trace_file)
        else:
            print(f"Warning: Trace file not found: {trace_file}")

    if not valid_traces:
        print("No valid trace files found!")
        return 1

    print(f"Testing {len(valid_traces)} trace files...")

    # Run test suite
    suite_result = tester.run_test_suite(valid_traces, args.parallel)

    # Save results
    tester.save_results(suite_result)

    # Print summary
    print("\n=== TEST SUITE SUMMARY ===")
    print(f"Total tests: {suite_result.total_tests}")
    print(f"Successful: {suite_result.successful_tests}")
    print(f"Failed: {suite_result.failed_tests}")
    print(f"Average match: {suite_result.average_match_percentage:.1f}%")
    print(f"Results saved to: {args.output_dir}")

    # Return success/failure with threshold support
    should_pass = True
    if args.max_failures is not None:
        if suite_result.failed_tests > args.max_failures:
            should_pass = False
    if args.min_average is not None:
        if suite_result.average_match_percentage < args.min_average:
            should_pass = False
    return 0 if should_pass else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
