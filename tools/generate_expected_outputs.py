#!/usr/bin/env python3
"""
Generate expected output files for trace semantic validation.

This tool:
1. Processes traces using TraceComparator to get actual outputs
2. Generates JSON expected files with appropriate validation checks
3. Focuses on traces that provide good semantic coverage
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, "/workspaces/pure3270")
sys.path.insert(0, "/workspaces/pure3270/examples")

from compare_trace_processing import TraceComparator

from pure3270.emulation.screen_buffer import ScreenBuffer


class ExpectedOutputGenerator:
    """Generate expected outputs for trace semantic validation."""

    def __init__(self, traces_dir: Path, expected_dir: Path):
        self.traces_dir = traces_dir
        self.expected_dir = expected_dir
        self.comparator = TraceComparator()

    def generate_for_trace(
        self, trace_name: str, description: str, validation_checks: List[Dict]
    ) -> Dict[str, Any]:
        """Generate expected output for a single trace."""
        trace_file = self.traces_dir / f"{trace_name}.trc"

        if not trace_file.exists():
            print(f"⚠️  Trace file not found: {trace_file}")
            return None

        print(f"🔄 Processing {trace_name}.trc...")

        try:
            # Process trace using TraceComparator
            result = self.comparator.compare_processing(str(trace_file), verbose=False)

            # Extract key information
            screen_buffer = result.get("screen_buffer")
            if not isinstance(screen_buffer, ScreenBuffer):
                print(f"❌ No screen buffer for {trace_name}")
                return None

            # Build expected output
            expected = {
                "trace_file": f"{trace_name}.trc",
                "description": description,
                "validation_checks": validation_checks,
                "protocol": {
                    "tn3270e": True,  # Most traces are TN3270E
                    "primary_features": ["screen_operations", "field_processing"],
                    "expected_screen_size": f"{screen_buffer.rows}x{screen_buffer.cols}",
                    "field_count_range": [1, 10],  # Conservative range
                },
            }

            # Customize validation checks based on actual results
            self._customize_checks(expected, result)

            return expected

        except Exception as e:
            print(f"❌ Error processing {trace_name}: {e}")
            return None

    def _customize_checks(self, expected: Dict, result: Dict):
        """Customize validation checks based on actual trace processing results."""
        screen_buffer = result.get("screen_buffer")
        if not isinstance(screen_buffer, ScreenBuffer):
            return

        # Extract actual screen size and customize checks
        actual_rows, actual_cols = screen_buffer.rows, screen_buffer.cols
        actual_field_count = (
            len(screen_buffer.fields) if hasattr(screen_buffer, "fields") else 0
        )

        # Update screen size check
        for check in expected["validation_checks"]:
            if check.get("type") == "screen_size":
                check["expected"] = f"{actual_rows}x{actual_cols}"
                break
        else:
            # Add screen size check if not present
            expected["validation_checks"].append(
                {
                    "type": "screen_size",
                    "expected": f"{actual_rows}x{actual_cols}",
                    "description": f"Expected screen size {actual_rows}x{actual_cols}",
                }
            )

        # Update field count check
        for check in expected["validation_checks"]:
            if check.get("type") == "field_count":
                check["min"] = max(0, actual_field_count - 2)  # Allow some flexibility
                check["max"] = actual_field_count + 5
                break

        # Add parsing errors check if not present
        has_parsing_errors = result.get("errors", 0) > 0
        for check in expected["validation_checks"]:
            if check.get("type") == "parsing_errors":
                check["expected_errors"] = has_parsing_errors
                break
        else:
            expected["validation_checks"].append(
                {
                    "type": "parsing_errors",
                    "expected_errors": has_parsing_errors,
                    "description": "Basic parsing error check",
                }
            )

        # Update protocol info
        if actual_rows > 24 or actual_cols > 80:
            expected["protocol"]["primary_features"].append("large_screen_support")

    def generate_key_expected_files(self):
        """Generate expected outputs for important trace files."""

        # Define key traces with their descriptions and validation priorities
        key_traces = [
            (
                "smoke",
                "Basic smoke test trace",
                [
                    {
                        "type": "screen_size",
                        "expected": "24x80",
                        "description": "Standard 3270 screen size",
                    },
                    {
                        "type": "field_count",
                        "min": 0,
                        "max": 5,
                        "description": "Basic field count check",
                    },
                    {
                        "type": "parsing_errors",
                        "expected_errors": False,
                        "description": "Should process without errors",
                    },
                ],
            ),
            (
                "login",
                "User login screen operations",
                [
                    {
                        "type": "screen_size",
                        "expected": "24x80",
                        "description": "Standard login screen size",
                    },
                    {
                        "type": "field_count",
                        "min": 1,
                        "max": 10,
                        "description": "Login form fields expected",
                    },
                    {
                        "type": "input_fields",
                        "count": 0,
                        "description": "Check for input capable fields",
                    },
                    {
                        "type": "parsing_errors",
                        "expected_errors": False,
                        "description": "Login processing should work",
                    },
                ],
            ),
            (
                "bid",
                "BIND image display operations",
                [
                    {
                        "type": "screen_size",
                        "expected": "24x80",
                        "description": "BIND image processing",
                    },
                    {
                        "type": "field_count",
                        "min": 0,
                        "max": 15,
                        "description": "BIND screens can have few fields",
                    },
                    {
                        "type": "parsing_errors",
                        "expected_errors": False,
                        "description": "BIND processing should work",
                    },
                ],
            ),
            (
                "invalid_ra",
                "Invalid Repeat-to-Address test",
                [
                    {
                        "type": "screen_size",
                        "expected": "24x80",
                        "description": "Invalid RA handling",
                    },
                    {
                        "type": "field_count",
                        "min": 0,
                        "max": 5,
                        "description": "Should handle invalid RA gracefully",
                    },
                    {
                        "type": "parsing_errors",
                        "expected_errors": True,
                        "description": "Invalid RA should trigger parsing errors",
                    },
                ],
            ),
            (
                "numeric",
                "Numeric field operations",
                [
                    {
                        "type": "screen_size",
                        "expected": "24x80",
                        "description": "Numeric field test",
                    },
                    {
                        "type": "field_count",
                        "min": 1,
                        "max": 8,
                        "description": "Numeric tests need input fields",
                    },
                    {
                        "type": "parsing_errors",
                        "expected_errors": False,
                        "description": "Numeric processing should work",
                    },
                ],
            ),
            (
                "wrap",
                "Line wrapping operations",
                [
                    {
                        "type": "screen_size",
                        "expected": "24x80",
                        "description": "Text wrapping test",
                    },
                    {
                        "type": "field_count",
                        "min": 0,
                        "max": 10,
                        "description": "Wrapping can affect field layout",
                    },
                    {
                        "type": "parsing_errors",
                        "expected_errors": False,
                        "description": "Wrapping should work correctly",
                    },
                ],
            ),
        ]

        generated_count = 0
        for trace_name, description, checks in key_traces:
            expected = self.generate_for_trace(trace_name, description, checks)
            if expected:
                # Write expected file
                expected_file = self.expected_dir / f"{trace_name}_expected.json"
                with open(expected_file, "w") as f:
                    json.dump(expected, f, indent=2)

                print(f"✅ Generated {expected_file.name}")
                generated_count += 1

        return generated_count


def main():
    """Main generation workflow."""
    traces_dir = Path("/workspaces/pure3270/tests/data/traces")
    expected_dir = Path("/workspaces/pure3270/tests/data/expected")

    expected_dir.mkdir(parents=True, exist_ok=True)

    generator = ExpectedOutputGenerator(traces_dir, expected_dir)

    print("🎯 Generating expected outputs for key traces...")
    count = generator.generate_key_expected_files()

    print(f"\n✅ Generated {count} expected output files")

    # Show all available expected files
    all_expected = list(expected_dir.glob("*_expected.json"))
    print(f"\n📋 Total expected files now available: {len(all_expected)}")
    for expected_file in sorted(all_expected):
        print(f"  ✓ {expected_file.name}")


if __name__ == "__main__":
    main()
