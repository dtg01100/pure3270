#!/usr/bin/env python3
"""
Comprehensive trace file testing to expose edge cases.

This test runs trace replay on all available trace files to identify
any edge cases, failures, or unexpected behavior that might not be
covered by the existing integration tests.
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.trace.replayer import Replayer

logger = logging.getLogger(__name__)

# Test data directory
TRACE_DIR = Path(__file__).parent / "data" / "traces"

# Timeout for individual trace replay (seconds)
TRACE_TIMEOUT = 10.0


class TraceTestResult:
    """Result of testing a single trace file."""

    def __init__(self, trace_path: Path):
        self.trace_path = trace_path
        self.trace_name = trace_path.name
        self.success = False
        self.error = None
        self.duration = 0.0
        self.screen_buffer = None
        self.ascii_screen = ""
        self.fields = []
        self.exception = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_name": self.trace_name,
            "success": self.success,
            "duration": self.duration,
            "error": str(self.error) if self.error else None,
            "exception_type": type(self.exception).__name__ if self.exception else None,
            "has_screen_buffer": self.screen_buffer is not None,
            "ascii_screen_length": len(self.ascii_screen),
            "field_count": len(self.fields),
        }


def get_all_trace_files() -> List[Path]:
    """Get all trace files in the test directory."""
    if not TRACE_DIR.exists():
        pytest.skip(f"Trace directory not found: {TRACE_DIR}")

    trace_files = list(TRACE_DIR.glob("*.trc"))
    trace_files.sort()  # Ensure consistent ordering

    if not trace_files:
        pytest.skip(f"No trace files found in {TRACE_DIR}")

    return trace_files


def run_single_trace_file(trace_path: Path) -> TraceTestResult:
    """Helper: Test a single trace file and return detailed results.

    Note: This is a helper function and intentionally not a pytest test.
    It should not be collected directly by pytest (no 'test_' prefix)
    because it expects a concrete Path argument rather than a fixture.
    """
    result = TraceTestResult(trace_path)
    start_time = time.time()

    def replay_with_timeout():
        """Replay the trace file in a separate thread with timeout."""
        try:
            # Temporarily reduce logging level to avoid excessive output
            original_level = logging.getLogger().level
            logging.getLogger().setLevel(logging.WARNING)

            try:
                # Create replayer instance
                replayer = Replayer()

                # Replay the trace file
                replay_result = replayer.replay(str(trace_path))

                # Validate result structure
                if not isinstance(replay_result, dict):
                    raise ValueError(f"Expected dict result, got {type(replay_result)}")

                required_keys = ["screen_buffer", "ascii_screen", "fields"]
                for key in required_keys:
                    if key not in replay_result:
                        raise ValueError(f"Missing required key: {key}")

                # Validate types
                screen_buffer = replay_result["screen_buffer"]
                if not isinstance(screen_buffer, ScreenBuffer):
                    raise ValueError(
                        f"Expected ScreenBuffer, got {type(screen_buffer)}"
                    )

                ascii_screen = replay_result["ascii_screen"]
                if not isinstance(ascii_screen, str):
                    raise ValueError(
                        f"Expected str for ascii_screen, got {type(ascii_screen)}"
                    )

                fields = replay_result["fields"]
                if not isinstance(fields, list):
                    raise ValueError(f"Expected list for fields, got {type(fields)}")

                # Store successful results
                result.success = True
                result.screen_buffer = screen_buffer
                result.ascii_screen = ascii_screen
                result.fields = fields

            finally:
                # Restore original logging level
                logging.getLogger().setLevel(original_level)

        except Exception as e:
            result.success = False
            result.error = str(e)
            result.exception = e

    try:
        logger.info(f"Testing trace file: {trace_path.name}")

        # Create and start thread
        replay_thread = threading.Thread(target=replay_with_timeout)
        replay_thread.start()

        # Wait for completion with timeout
        replay_thread.join(timeout=TRACE_TIMEOUT)

        if replay_thread.is_alive():
            # Thread is still running - timeout occurred
            result.success = False
            result.error = f"Timeout after {TRACE_TIMEOUT} seconds"
            result.exception = TimeoutError(
                f"Replay timed out after {TRACE_TIMEOUT} seconds"
            )
            logger.error(f"✗ {trace_path.name}: TIMEOUT")

        elif result.success:
            logger.info(
                f"✓ {trace_path.name}: {len(result.ascii_screen)} chars, {len(result.fields)} fields"
            )

        else:
            logger.error(f"✗ {trace_path.name}: {result.error}")

    finally:
        result.duration = time.time() - start_time

    return result


@pytest.mark.slow
def test_all_trace_files_comprehensive():
    """
    Comprehensive test of all trace files to expose edge cases.

    This test runs trace replay on all available trace files and collects
    detailed results to identify any failures or edge cases.
    """
    trace_files = get_all_trace_files()
    logger.info(f"Testing {len(trace_files)} trace files")

    results = []
    failures = []
    successes = []

    for trace_path in trace_files:
        result = run_single_trace_file(trace_path)
        results.append(result)

        if result.success:
            successes.append(result)
        else:
            failures.append(result)

    # Log summary
    logger.info(f"Results: {len(successes)} successes, {len(failures)} failures")

    # Detailed failure analysis
    if failures:
        logger.error(f"FAILED TRACES ({len(failures)}):")
        for failure in failures:
            logger.error(f"  - {failure.trace_name}: {failure.error}")

        # Group failures by error type
        error_groups = {}
        for failure in failures:
            error_type = (
                type(failure.exception).__name__ if failure.exception else "Unknown"
            )
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(failure)

        logger.error("FAILURES BY ERROR TYPE:")
        for error_type, error_failures in error_groups.items():
            logger.error(f"  {error_type}: {len(error_failures)} traces")
            for failure in error_failures[:3]:  # Show first 3 examples
                logger.error(f"    - {failure.trace_name}")

    # Performance analysis
    if results:
        durations = [r.duration for r in results]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)

        logger.info(".3f")
        logger.info(".3f")
        logger.info(".3f")

        # Find slowest traces
        slowest = sorted(results, key=lambda r: r.duration, reverse=True)[:5]
        logger.info("SLOWEST TRACES:")
        for result in slowest:
            logger.info(".3f")

    # Assert no failures (skipped traces are acceptable)
    assert (
        len(failures) == 0
    ), f"{len(failures)} trace files failed: {[f.trace_name for f in failures]}"


@pytest.mark.parametrize("trace_file", get_all_trace_files(), ids=lambda p: p.name)
def test_individual_trace_file(trace_file: Path):
    """
    Individual test for each trace file.

    This parametrized test allows running individual trace files
    and getting specific failure information for each one.
    """
    result = run_single_trace_file(trace_file)

    # Allow skipped traces (due to unavailable codepages) but fail on actual errors
    if result.error and "Skipped:" in result.error:
        pytest.skip(f"Trace file {trace_file.name} skipped: {result.error}")
    else:
        assert result.success, f"Trace file {trace_file.name} failed: {result.error}"


def test_trace_file_categories():
    """
    Test trace files grouped by categories to identify patterns.

    This test groups trace files by naming patterns and tests them
    as groups to identify if certain types of traces have issues.
    """
    trace_files = get_all_trace_files()

    # Define categories based on filename patterns
    categories = {
        "bid_related": [f for f in trace_files if "bid" in f.name],
        "file_transfer": [f for f in trace_files if f.name.startswith("ft_")],
        "ibmlink": [f for f in trace_files if "ibmlink" in f.name],
        "short_commands": [f for f in trace_files if f.name.startswith("short_")],
        "invalid_data": [f for f in trace_files if "invalid" in f.name],
        "dbcs": [f for f in trace_files if "dbcs" in f.name or "korean" in f.name],
        "tn3270e": [
            f for f in trace_files if "tn3270e" in f.name or "wont-tn3270e" in f.name
        ],
        "login": [f for f in trace_files if "login" in f.name],
        "smoke": [f for f in trace_files if "smoke" in f.name],
        "other": [],  # Catch-all for uncategorized
    }

    # Add uncategorized files to "other"
    categorized = set()
    for category_files in categories.values():
        categorized.update(category_files)

    categories["other"] = [f for f in trace_files if f not in categorized]

    # Test each category
    category_results = {}

    for category_name, category_files in categories.items():
        if not category_files:
            continue

        logger.info(f"Testing category '{category_name}': {len(category_files)} files")

        category_successes = 0
        category_failures = []

        for trace_file in category_files:
            result = run_single_trace_file(trace_file)
            if result.success:
                category_successes += 1
            else:
                category_failures.append(result)

        category_results[category_name] = {
            "total": len(category_files),
            "successes": category_successes,
            "failures": len(category_failures),
            "failure_details": category_failures,
        }

        success_rate = (category_successes / len(category_files)) * 100
        logger.info(".1f")

        if category_failures:
            logger.error(f"  Failed traces in {category_name}:")
            for failure in category_failures:
                logger.error(f"    - {failure.trace_name}: {failure.error}")

    # Overall category summary
    logger.info("CATEGORY SUMMARY:")
    for category_name, stats in category_results.items():
        success_rate = (stats["successes"] / stats["total"]) * 100
        logger.info(
            f"  {category_name}: {stats['successes']}/{stats['total']} ({success_rate:.1f}%)"
        )

    # Assert all categories have at least 80% success rate
    for category_name, stats in category_results.items():
        success_rate = (stats["successes"] / stats["total"]) * 100
        assert (
            success_rate >= 80.0
        ), f"Category {category_name} has only {success_rate:.1f}% success rate"
