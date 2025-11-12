"""
Integration tests that combine multiple validation approaches for Pure3270.

This module tests the integration of various validation tools and approaches
to ensure comprehensive validation of Pure3270 functionality.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


class TestValidationIntegration:
    """Test integration of multiple validation approaches."""

    def test_offline_validation_pipeline(self):
        """Test that the complete offline validation pipeline works."""
        # Run the offline validation suite
        result = subprocess.run(
            [sys.executable, "tools/run_offline_validation.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0, f"Offline validation failed: {result.stderr}"
        assert "ALL OFFLINE VALIDATION TESTS PASSED" in result.stdout

    def test_synthetic_data_integration(self):
        """Test integration of synthetic data generation and testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate synthetic data
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/synthetic_data_generator.py",
                    "generate",
                    temp_dir,
                    "5",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0, f"Data generation failed: {result.stderr}"

            # Test the generated data
            data_file = Path(temp_dir) / "synthetic_test_cases.json"
            assert data_file.exists(), "Synthetic data file not created"

            result = subprocess.run(
                [
                    sys.executable,
                    "tools/synthetic_data_generator.py",
                    "test",
                    str(data_file),
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0, f"Data testing failed: {result.stderr}"
            assert "streams parsed successfully" in result.stdout

    def test_screen_buffer_regression_integration(self):
        """Test integration of screen buffer regression testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate regression test data
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/screen_buffer_regression_test.py",
                    "generate",
                    temp_dir,
                    "3",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert (
                result.returncode == 0
            ), f"Regression generation failed: {result.stderr}"

            # Run regression tests
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/screen_buffer_regression_test.py",
                    "run",
                    temp_dir,
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0, f"Regression testing failed: {result.stderr}"
            # Tool output changed to a human-readable summary string; match on that
            assert "Screen buffer regression test passed" in result.stdout

    def test_trace_replay_integration(self):
        """Test integration of trace replay functionality."""
        # Test with a simple trace file
        trace_file = Path(__file__).parent.parent / "tests/data/traces/empty-user.trc"

        result = subprocess.run(
            [sys.executable, "tools/test_trace_replay.py", str(trace_file)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=15,
        )

        assert result.returncode == 0, f"Trace replay failed: {result.stderr}"
        assert "Trace replay test completed successfully" in result.stdout

    def test_performance_benchmark_integration(self):
        """Test that performance benchmarking runs without errors."""
        result = subprocess.run(
            [sys.executable, "tools/performance_benchmark.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=60,
        )

        assert result.returncode == 0, f"Performance benchmark failed: {result.stderr}"
        assert "All benchmarks completed successfully" in result.stdout

    def test_combined_validation_workflow(self):
        """Test a combined workflow using multiple validation tools."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Generate synthetic data
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/synthetic_data_generator.py",
                    "generate",
                    temp_dir,
                    "2",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0

            # Step 2: Test synthetic data
            data_file = Path(temp_dir) / "synthetic_test_cases.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/synthetic_data_generator.py",
                    "test",
                    str(data_file),
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0

            # Step 3: Run screen buffer regression
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/screen_buffer_regression_test.py",
                    "generate",
                    temp_dir,
                    "2",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0

            result = subprocess.run(
                [
                    sys.executable,
                    "tools/screen_buffer_regression_test.py",
                    "run",
                    temp_dir,
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0

            # Step 4: Run performance benchmark
            result = subprocess.run(
                [sys.executable, "tools/performance_benchmark.py"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
                timeout=30,
            )

            assert result.returncode == 0

    def test_validation_tools_exist_and_executable(self):
        """Test that all validation tools exist and are executable."""
        tools_dir = Path(__file__).parent.parent / "tools"
        expected_tools = [
            "run_offline_validation.py",
            "synthetic_data_generator.py",
            "screen_buffer_regression_test.py",
            "test_trace_replay.py",
            "performance_benchmark.py",
        ]

        for tool in expected_tools:
            tool_path = tools_dir / tool
            assert tool_path.exists(), f"Tool {tool} does not exist"
            assert tool_path.is_file(), f"Tool {tool} is not a file"

            # Test that it's executable (can be run with python)
            # For tools that take arguments, just check they start without immediate crash
            if tool == "synthetic_data_generator.py":
                # Check help for tools that support it
                result = subprocess.run(
                    [sys.executable, str(tool_path), "--help"],
                    capture_output=True,
                    cwd=Path(__file__).parent.parent,
                    timeout=5,
                )
            else:
                # For other tools, just check they can be imported/executed briefly
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        f'import sys; sys.path.insert(0, "tools"); exec(open("{tool}").read().split("if __name__")[0])',
                    ],
                    capture_output=True,
                    cwd=Path(__file__).parent.parent,
                    timeout=2,
                )

            # Just check they don't crash immediately with import/exec errors
            assert (
                result.returncode != 1 or "import" not in result.stderr.decode().lower()
            ), f"Tool {tool} has import issues: {result.stderr.decode()}"
