"""Regression testing harness for ScreenBuffer snapshots."""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union, cast

from .screen_buffer import ScreenBuffer
from .snapshot import ScreenSnapshot, SnapshotComparison, compare_snapshots

logger = logging.getLogger(__name__)


class RegressionTestCase:
    """Represents a single regression test case."""

    def __init__(self, name: str, test_function: Callable[[ScreenBuffer], None]):
        """Initialize a test case.

        Args:
            name: Unique name for the test case
            test_function: Function that takes a ScreenBuffer and modifies it
        """
        self.name = name
        self.test_function = test_function
        self.expected_snapshot: Optional[ScreenSnapshot] = None
        self.baseline_path: Optional[str] = None

    def set_expected_snapshot(self, snapshot: ScreenSnapshot) -> None:
        """Set the expected snapshot for this test case."""
        self.expected_snapshot = snapshot

    def set_baseline_path(self, path: str) -> None:
        """Set the baseline snapshot file path."""
        self.baseline_path = path

    def run(self, screen_buffer: ScreenBuffer) -> ScreenSnapshot:
        """Run the test case and return the resulting snapshot."""
        logger.info(f"Running test case: {self.name}")

        # Reset buffer to clean state
        screen_buffer.clear()

        # Run the test function
        self.test_function(screen_buffer)

        # Take snapshot
        actual_snapshot = ScreenSnapshot(screen_buffer)

        return actual_snapshot

    def compare_with_expected(
        self, actual_snapshot: ScreenSnapshot
    ) -> SnapshotComparison:
        """Compare actual snapshot with expected snapshot."""
        if self.expected_snapshot is None:
            raise ValueError(f"No expected snapshot set for test case: {self.name}")

        return compare_snapshots(self.expected_snapshot, actual_snapshot)

    def compare_with_baseline(
        self, actual_snapshot: ScreenSnapshot
    ) -> SnapshotComparison:
        """Compare actual snapshot with baseline file."""
        if self.baseline_path is None:
            raise ValueError(f"No baseline path set for test case: {self.name}")

        baseline_snapshot = ScreenSnapshot.load_from_file(self.baseline_path)
        return compare_snapshots(baseline_snapshot, actual_snapshot)

    def save_as_baseline(self, snapshot: ScreenSnapshot) -> None:
        """Save a snapshot as the baseline for this test case."""
        if self.baseline_path is None:
            raise ValueError(f"No baseline path set for test case: {self.name}")

        snapshot.save_to_file(self.baseline_path)
        logger.info(f"Saved baseline snapshot for {self.name} to {self.baseline_path}")


class RegressionTestSuite:
    """Manages a collection of regression test cases."""

    def __init__(self, name: str, baseline_dir: Optional[str] = None):
        """Initialize a test suite.

        Args:
            name: Name of the test suite
            baseline_dir: Directory to store baseline snapshots
        """
        self.name = name
        self.test_cases: Dict[str, RegressionTestCase] = {}
        self.baseline_dir = baseline_dir or f"test_baselines/{name}"

        # Create baseline directory if it doesn't exist
        Path(self.baseline_dir).mkdir(parents=True, exist_ok=True)

    def add_test_case(self, test_case: RegressionTestCase) -> None:
        """Add a test case to the suite."""
        if test_case.name in self.test_cases:
            raise ValueError(f"Test case {test_case.name} already exists in suite")

        # Set baseline path if not already set
        if test_case.baseline_path is None:
            test_case.set_baseline_path(f"{self.baseline_dir}/{test_case.name}.json")

        self.test_cases[test_case.name] = test_case

    def add_test_case_from_function(
        self, name: str, test_function: Callable[[ScreenBuffer], None]
    ) -> RegressionTestCase:
        """Create and add a test case from a function."""
        test_case = RegressionTestCase(name, test_function)
        self.add_test_case(test_case)
        return test_case

    def run_all_tests(
        self, screen_buffer: ScreenBuffer, fail_on_first_error: bool = True
    ) -> Dict[str, Any]:
        """Run all test cases in the suite.

        Args:
            screen_buffer: ScreenBuffer instance to use for testing
            fail_on_first_error: Whether to stop on first failure

        Returns:
            Dictionary with test results
        """
        results = {
            "suite_name": self.name,
            "total_tests": len(self.test_cases),
            "passed": 0,
            "failed": 0,
            "failures": [],
        }

        for test_name, test_case in self.test_cases.items():
            try:
                logger.info(f"Running test: {test_name}")
                actual_snapshot = test_case.run(screen_buffer)

                # Try to compare with baseline
                try:
                    comparison = test_case.compare_with_baseline(actual_snapshot)

                    if comparison.has_differences():
                        failed_count = cast(int, results["failed"]) + 1
                        results["failed"] = failed_count
                        failure_info = {
                            "test_name": test_name,
                            "error": "Snapshot differs from baseline",
                            "differences": comparison.get_summary(),
                        }
                        failures_list = cast(List[Dict[str, Any]], results["failures"])
                        failures_list.append(failure_info)

                        if fail_on_first_error:
                            break
                    else:
                        passed_count = cast(int, results["passed"]) + 1
                        results["passed"] = passed_count

                except FileNotFoundError:
                    # Baseline doesn't exist, save current as baseline
                    logger.warning(
                        f"No baseline found for {test_name}, creating new baseline"
                    )
                    test_case.save_as_baseline(actual_snapshot)
                    passed_count = cast(int, results["passed"]) + 1
                    results["passed"] = passed_count

            except Exception as e:
                failed_count = cast(int, results["failed"]) + 1
                results["failed"] = failed_count
                failure_info = {
                    "test_name": test_name,
                    "error": str(e),
                    "exception_type": type(e).__name__,
                }
                failures_list = cast(List[Dict[str, Any]], results["failures"])
                failures_list.append(failure_info)

                if fail_on_first_error:
                    break

        return results

    def generate_missing_baselines(self, screen_buffer: ScreenBuffer) -> List[str]:
        """Generate baseline snapshots for tests that don't have them."""
        missing_baselines = []

        for test_name, test_case in self.test_cases.items():
            if test_case.baseline_path and not os.path.exists(test_case.baseline_path):
                logger.info(f"Generating baseline for {test_name}")
                actual_snapshot = test_case.run(screen_buffer)
                test_case.save_as_baseline(actual_snapshot)
                missing_baselines.append(test_name)

        return missing_baselines

    def get_test_report(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable test report."""
        report = []
        report.append(f"=== Regression Test Suite: {results['suite_name']} ===")
        report.append(f"Total Tests: {results['total_tests']}")
        report.append(f"Passed: {results['passed']}")
        report.append(f"Failed: {results['failed']}")
        success_rate = (
            (results["passed"] / results["total_tests"] * 100)
            if results["total_tests"] > 0
            else 0
        )
        report.append(f"Success Rate: {success_rate:.1f}%")

        if results["failures"]:
            report.append("")
            report.append("=== FAILURES ===")
            for failure in results["failures"]:
                report.append(f"Test: {failure['test_name']}")
                report.append(f"Error: {failure['error']}")
                if "differences" in failure:
                    report.append(f"Differences: {failure['differences']}")
                report.append("")

        return "\n".join(report)


class RegressionTestRunner:
    """High-level interface for running regression tests."""

    def __init__(self, baseline_dir: str = "test_baselines"):
        """Initialize the test runner.

        Args:
            baseline_dir: Base directory for storing baseline snapshots
        """
        self.baseline_dir = baseline_dir
        self.suites: Dict[str, RegressionTestSuite] = {}

    def create_suite(self, name: str) -> RegressionTestSuite:
        """Create a new test suite."""
        suite = RegressionTestSuite(name, f"{self.baseline_dir}/{name}")
        self.suites[name] = suite
        return suite

    def run_suite(
        self,
        suite_name: str,
        screen_buffer: ScreenBuffer,
        fail_on_first_error: bool = True,
    ) -> Dict[str, Any]:
        """Run a specific test suite."""
        if suite_name not in self.suites:
            raise ValueError(f"Suite {suite_name} not found")

        suite = self.suites[suite_name]
        return suite.run_all_tests(screen_buffer, fail_on_first_error)

    def run_all_suites(
        self, screen_buffer: ScreenBuffer, fail_on_first_error: bool = True
    ) -> Dict[str, Any]:
        """Run all test suites."""
        all_results = {"total_suites": len(self.suites), "suite_results": {}}

        for suite_name, suite in self.suites.items():
            logger.info(f"Running suite: {suite_name}")
            results = suite.run_all_tests(screen_buffer, fail_on_first_error)
            suite_results = cast(
                Dict[str, Dict[str, Any]], all_results["suite_results"]
            )
            suite_results[suite_name] = results

        return all_results

    def generate_all_baselines(
        self, screen_buffer: ScreenBuffer
    ) -> Dict[str, List[str]]:
        """Generate baselines for all suites."""
        baselines_generated = {}

        for suite_name, suite in self.suites.items():
            logger.info(f"Generating baselines for suite: {suite_name}")
            missing = suite.generate_missing_baselines(screen_buffer)
            baselines_generated[suite_name] = missing

        return baselines_generated


# Convenience functions for common use cases
def create_simple_test_case(
    name: str, setup_function: Callable[[ScreenBuffer], None]
) -> RegressionTestCase:
    """Create a simple test case with a setup function."""
    return RegressionTestCase(name, setup_function)


def run_single_test(
    test_case: RegressionTestCase, screen_buffer: ScreenBuffer
) -> SnapshotComparison:
    """Run a single test case and return comparison with baseline."""
    actual_snapshot = test_case.run(screen_buffer)
    return test_case.compare_with_baseline(actual_snapshot)
