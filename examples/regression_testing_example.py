#!/usr/bin/env python3
"""
Screen Buffer Regression Testing Example

This example demonstrates how to use the screen buffer snapshot and comparison
system for regression testing of 3270 emulation functionality.

The system provides:
1. Snapshot capture of screen buffer state
2. Comparison utilities for detecting differences
3. Test harness infrastructure for automated regression testing
4. Support for both EBCDIC and ASCII modes
5. Integration with existing test frameworks

Usage:
    python regression_testing_example.py

This will run a series of example tests and demonstrate the functionality.
"""

import logging
import sys
from pathlib import Path

# Add the pure3270 package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270.emulation.regression_harness import (
    RegressionTestCase,
    RegressionTestRunner,
    RegressionTestSuite,
    create_simple_test_case,
    run_single_test,
)
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.emulation.snapshot import (
    ScreenSnapshot,
    SnapshotComparison,
    compare_snapshots,
    create_ascii_mode_snapshot,
    create_ebcdic_mode_snapshot,
    take_snapshot,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def example_basic_snapshot_usage() -> None:
    """Example 1: Basic snapshot capture and comparison."""
    print("\n=== Example 1: Basic Snapshot Usage ===")

    # Create a screen buffer
    screen = ScreenBuffer(rows=10, cols=40)

    # Write some content
    screen.write_char(0xC1, 0, 0)  # 'A' in EBCDIC
    screen.write_char(0xC2, 0, 1)  # 'B' in EBCDIC
    screen.write_char(0xC3, 0, 2)  # 'C' in EBCDIC

    # Take a snapshot
    snapshot1 = take_snapshot(screen)
    print(f"Snapshot 1 captured at {snapshot1.metadata['timestamp']}")
    print(f"Buffer content: {snapshot1.to_screen_buffer().to_text()}")

    # Modify the buffer
    screen.write_char(0xC4, 0, 3)  # 'D' in EBCDIC

    # Take another snapshot
    snapshot2 = take_snapshot(screen)
    print(f"Snapshot 2 captured at {snapshot2.metadata['timestamp']}")
    print(f"Buffer content: {snapshot2.to_screen_buffer().to_text()}")

    # Compare snapshots
    comparison = compare_snapshots(snapshot1, snapshot2)
    print(f"Snapshots identical: {comparison.is_identical}")

    if not comparison.is_identical:
        print("Differences found:")
        for diff_type, diff_data in comparison.differences.items():
            print(f"  - {diff_type}: {diff_data}")


def example_mode_aware_comparison() -> None:
    """Example 2: Basic snapshot comparison."""
    print("\n=== Example 2: Basic Snapshot Comparison ===")

    # Create screen buffer
    screen1 = ScreenBuffer(rows=24, cols=80)
    snapshot1 = take_snapshot(screen1)
    print(f"Snapshot 1 created with ascii_mode: {snapshot1.metadata['ascii_mode']}")

    # Create another screen buffer
    screen2 = ScreenBuffer(rows=24, cols=80)
    snapshot2 = take_snapshot(screen2)
    print(f"Snapshot 2 created with ascii_mode: {snapshot2.metadata['ascii_mode']}")

    # Compare snapshots
    comparison = compare_snapshots(snapshot1, snapshot2)
    print(f"Snapshots identical: {comparison.is_identical}")
    if comparison.differences:
        print(f"Found {len(comparison.differences)} differences")


def example_advanced_comparator() -> None:
    """Example 3: Advanced snapshot comparison."""
    print("\n=== Example 3: Advanced Snapshot Comparison ===")

    # Create test snapshots
    screen1 = ScreenBuffer(rows=24, cols=80)
    snapshot1 = take_snapshot(screen1)

    screen2 = ScreenBuffer(rows=24, cols=80)
    # Write some data to make them different
    screen2.write_char(0x48, row=0, col=0)  # 'H' in EBCDIC
    snapshot2 = take_snapshot(screen2)

    # Use basic comparison
    result = compare_snapshots(snapshot1, snapshot2)

    print(f"Snapshots identical: {result.is_identical}")
    if result.differences:
        print(f"Found differences in: {list(result.differences.keys())}")
    else:
        print("No differences found")


def example_regression_test_harness() -> None:
    """Example 4: Using the regression test harness."""
    print("\n=== Example 4: Regression Test Harness ===")

    # Create test suite
    suite = RegressionTestSuite("example_tests", "test_baselines/example")

    # Define test functions
    def test_hello_world(screen: ScreenBuffer) -> None:
        """Test that writes 'HELLO' to the screen."""
        screen.write_char(0xC8, 0, 0)  # H
        screen.write_char(0xC5, 0, 1)  # E
        screen.write_char(0xD3, 0, 2)  # L
        screen.write_char(0xD3, 0, 3)  # L
        screen.write_char(0xD6, 0, 4)  # O

    def test_cursor_position(screen: ScreenBuffer) -> None:
        """Test cursor positioning."""
        screen.set_position(2, 5)
        screen.write_char(0xC1, 2, 5)  # A

    def test_field_creation(screen: ScreenBuffer) -> None:
        """Test field creation and attributes."""
        # Create a protected field
        screen.write_char(0xC8, 0, 0)  # H
        screen.set_attribute(0x40, 0, 0)  # Set protected attribute

    # Add test cases
    suite.add_test_case_from_function("hello_world", test_hello_world)
    suite.add_test_case_from_function("cursor_position", test_cursor_position)
    suite.add_test_case_from_function("field_creation", test_field_creation)

    # Create screen buffer for testing
    screen = ScreenBuffer(rows=10, cols=40)

    # Run the test suite
    print("Running regression test suite...")
    results = suite.run_all_tests(screen, fail_on_first_error=False)

    # Print results
    print(f"Total tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")

    if results["failures"]:
        print("Failures:")
        for failure in results["failures"]:
            print(f"  - {failure['test_name']}: {failure['error']}")

    # Generate missing baselines
    print("\nGenerating missing baselines...")
    missing = suite.generate_missing_baselines(screen)
    print(f"Generated baselines for: {missing}")


def example_file_operations() -> None:
    """Example 5: File save/load operations."""
    print("\n=== Example 5: File Operations ===")

    # Create a screen buffer with some content
    screen = ScreenBuffer(rows=5, cols=20)
    screen.write_char(0xC1, 0, 0)  # A
    screen.write_char(0xC2, 0, 1)  # B
    screen.write_char(0xC3, 0, 2)  # C

    # Take snapshot
    snapshot = take_snapshot(screen)

    # Save to file
    snapshot.save_to_file("example_snapshot.json")
    print("Snapshot saved to example_snapshot.json")

    # Load from file
    loaded_snapshot = ScreenSnapshot.load_from_file("example_snapshot.json")
    print("Snapshot loaded from file")

    # Compare original and loaded
    comparison = compare_snapshots(snapshot, loaded_snapshot)
    print(f"Original and loaded snapshots identical: {comparison.is_identical}")


def example_pytest_integration() -> None:
    """Example 6: Integration with pytest framework."""
    print("\n=== Example 6: Pytest Integration ===")

    # This example shows how the snapshot system can be integrated
    # with pytest for automated testing

    def test_screen_buffer_regression() -> bool:
        """Example pytest test function using snapshots."""
        screen = ScreenBuffer(rows=24, cols=80)

        # Set up initial state
        screen.write_char(0xC8, 0, 0)  # H
        screen.write_char(0xC5, 0, 1)  # E
        screen.write_char(0xD3, 0, 2)  # L
        screen.write_char(0xD3, 0, 3)  # L
        screen.write_char(0xD6, 0, 4)  # O

        # Take snapshot
        actual_snapshot = take_snapshot(screen)

        # Load expected snapshot (would be stored in test fixtures)
        try:
            expected_snapshot = ScreenSnapshot.load_from_file(
                "test_fixtures/hello_world.json"
            )
            comparison = compare_snapshots(expected_snapshot, actual_snapshot)

            if not comparison.is_identical:
                # In pytest, you would use assert or pytest.fail()
                print(
                    "REGRESSION DETECTED: Screen buffer output differs from expected!"
                )
                comparison.print_report()
                return False
            else:
                print("✓ Test passed: Screen buffer matches expected output")
                return True

        except FileNotFoundError:
            print("No baseline found, creating new baseline...")
            actual_snapshot.save_to_file("test_fixtures/hello_world.json")
            return True

    # Run the example test
    test_screen_buffer_regression()


def main() -> int:
    """Run all examples."""
    print("Screen Buffer Regression Testing Examples")
    print("=" * 50)

    try:
        example_basic_snapshot_usage()
        example_mode_aware_comparison()
        example_advanced_comparator()
        example_regression_test_harness()
        example_file_operations()
        example_pytest_integration()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("\nKey Features Demonstrated:")
        print("• Snapshot capture and serialization")
        print("• Cross-mode comparison (EBCDIC/ASCII)")
        print("• Regression test harness")
        print("• File I/O operations")
        print("• Pytest integration patterns")
        print("• Advanced comparison utilities")

    except Exception as e:
        logger.error(f"Example failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
