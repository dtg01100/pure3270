#!/usr/bin/env python3
"""
Synthetic TN3270 Data Stream Generator for Offline Validation.

This tool generates synthetic TN3270 protocol data streams with various
commands, orders, and edge cases for testing the parser robustness.

Usage:
    python tools/synthetic_data_generator.py generate <output_dir> [count]
    python tools/synthetic_data_generator.py test <data_file>
"""

import json
import random
import struct

# Add pure3270 to path
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270.protocol.data_stream import (
    EOA,
    EXT_ATTR_CHARACTER_SET,
    EXT_ATTR_COLOR,
    EXT_ATTR_HIGHLIGHT,
    IC,
    RA,
    SBA,
    SF,
    SFE,
    WCC,
    WRITE,
)


class TN3270DataStreamGenerator:
    """Generates synthetic TN3270 data streams for testing."""

    def __init__(self, seed: int = 42):
        self.random = random.Random(seed)
        self.ebcdic_chars = list(range(0x40, 0xFF))  # EBCDIC character range

    def generate_test_cases(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate test cases with synthetic data streams."""
        test_cases = []

        for i in range(count):
            test_case = {
                "id": f"synthetic_{i:03d}",
                "description": f"Synthetic test case {i}",
                "data_stream": self._generate_data_stream(),
                "expected_behavior": self._generate_expected_behavior(),
            }
            test_cases.append(test_case)

        return test_cases

    def _generate_data_stream(self) -> bytes:
        """Generate a synthetic TN3270 data stream."""
        stream = bytearray()

        # Start with WCC (Write Control Character)
        wcc = self._generate_wcc()
        stream.append(WCC)
        stream.append(wcc)

        # Add orders and data
        orders_count = self.random.randint(5, 20)
        for _ in range(orders_count):
            order_data = self._generate_order()
            stream.extend(order_data)

        # End with EOA (End of Area) if not already present
        if stream and stream[-1] != EOA:
            stream.append(EOA)

        return bytes(stream)

    def _generate_wcc(self) -> int:
        """Generate a Write Control Character."""
        # WCC format: 0xC0 + control bits
        # Bit 7: Start Printer (0)
        # Bit 6: Sound Alarm (0)
        # Bit 5: Keyboard Restore (0)
        # Bit 4: Reset Modified (1)
        # Bit 3-2: Reserved (0)
        # Bit 1: Reset MDT (0)
        # Bit 0: Reserved (0)
        return 0xC0 | self.random.randint(0, 0x3F)

    def _generate_order(self) -> bytes:
        """Generate a random TN3270 order with data."""
        order_type = self.random.choice(["sba", "sf", "ra", "ic", "sfe", "text", "eoa"])

        if order_type == "sba":
            return self._generate_sba()
        elif order_type == "sf":
            return self._generate_sf()
        elif order_type == "ra":
            return self._generate_ra()
        elif order_type == "ic":
            return self._generate_ic()
        elif order_type == "sfe":
            return self._generate_sfe()
        elif order_type == "text":
            return self._generate_text()
        elif order_type == "eoa":
            return bytes([EOA])
        else:
            return self._generate_text()  # Default to text

    def _generate_sba(self) -> bytes:
        """Generate Set Buffer Address order."""
        # SBA + 2-byte address (12-bit buffer address)
        address = self.random.randint(0, 1920)  # 24x80 screen
        addr_high = (address >> 6) & 0x3F
        addr_low = address & 0x3F
        return bytes([SBA, addr_high, addr_low])

    def _generate_sf(self) -> bytes:
        """Generate Start Field order."""
        # SF + attribute byte
        attr = self.random.randint(0, 255)
        return bytes([SF, attr])

    def _generate_ra(self) -> bytes:
        """Generate Repeat to Address order."""
        # RA + addr_high + addr_low + char
        address = self.random.randint(0, 1920)
        addr_high = (address >> 6) & 0x3F
        addr_low = address & 0x3F
        char = self.random.choice(self.ebcdic_chars)
        return bytes([RA, addr_high, addr_low, char])

    def _generate_ic(self) -> bytes:
        """Generate Insert Cursor order."""
        return bytes([IC])

    def _generate_sfe(self) -> bytes:
        """Generate Start Field Extended order."""
        # SFE + count + attribute pairs
        count = self.random.randint(1, 4)
        data = bytearray([SFE, count])

        for _ in range(count):
            attr_type = self.random.choice(
                [EXT_ATTR_HIGHLIGHT, EXT_ATTR_COLOR, EXT_ATTR_CHARACTER_SET]
            )
            attr_value = self.random.randint(0, 255)
            data.extend([attr_type, attr_value])

        return bytes(data)

    def _generate_text(self) -> bytes:
        """Generate text data."""
        length = self.random.randint(1, 20)
        text = bytearray()
        for _ in range(length):
            char = self.random.choice(self.ebcdic_chars)
            text.append(char)
        return bytes(text)

    def _generate_expected_behavior(self) -> Dict[str, Any]:
        """Generate expected behavior description."""
        return {
            "should_parse": True,
            "may_have_validation_errors": False,
            "tests_cursor_positioning": self.random.choice([True, False]),
            "tests_field_attributes": self.random.choice([True, False]),
            "tests_extended_attributes": self.random.choice([True, False]),
        }

    def generate_edge_cases(self) -> List[Dict[str, Any]]:
        """Generate edge case test streams."""
        edge_cases = []

        # Empty stream
        edge_cases.append(
            {
                "id": "edge_empty",
                "description": "Empty data stream",
                "data_stream": b"",
                "expected_behavior": {"should_parse": False, "error_type": "empty"},
            }
        )

        # Only WCC
        edge_cases.append(
            {
                "id": "edge_wcc_only",
                "description": "Only WCC, no orders",
                "data_stream": bytes([WCC, 0xC1]),
                "expected_behavior": {"should_parse": True, "minimal": True},
            }
        )

        # Invalid WCC
        edge_cases.append(
            {
                "id": "edge_invalid_wcc",
                "description": "Invalid WCC value",
                "data_stream": bytes([WCC, 0xFF, EOA]),
                "expected_behavior": {
                    "should_parse": True,
                    "may_have_validation_errors": True,
                },
            }
        )

        # Truncated SBA
        edge_cases.append(
            {
                "id": "edge_truncated_sba",
                "description": "Truncated SBA order",
                "data_stream": bytes([WCC, 0xC1, SBA]),
                "expected_behavior": {"should_parse": False, "error_type": "truncated"},
            }
        )

        # Oversized address
        edge_cases.append(
            {
                "id": "edge_oversized_address",
                "description": "Address beyond screen bounds",
                "data_stream": bytes([WCC, 0xC1, SBA, 0xFF, 0xFF, EOA]),
                "expected_behavior": {"should_parse": True, "boundary_test": True},
            }
        )

        # Nested SFE
        sfe_data = bytes(
            [WCC, 0xC1, SFE, 2, EXT_ATTR_HIGHLIGHT, 0xF0, EXT_ATTR_COLOR, 0x0F, EOA]
        )
        edge_cases.append(
            {
                "id": "edge_nested_sfe",
                "description": "SFE with multiple attributes",
                "data_stream": sfe_data,
                "expected_behavior": {"should_parse": True, "extended_attrs": True},
            }
        )

        # Very long text
        long_text = bytes([WCC, 0xC1]) + bytes(self.ebcdic_chars * 10) + bytes([EOA])
        edge_cases.append(
            {
                "id": "edge_long_text",
                "description": "Very long text data",
                "data_stream": long_text,
                "expected_behavior": {"should_parse": True, "large_data": True},
            }
        )

        # Malformed RA
        edge_cases.append(
            {
                "id": "edge_malformed_ra",
                "description": "Malformed RA order",
                "data_stream": bytes([WCC, 0xC1, RA, 0x00, EOA]),  # Missing char
                "expected_behavior": {"should_parse": False, "error_type": "malformed"},
            }
        )

        return edge_cases


class DataStreamTester:
    """Tests synthetic data streams against the parser."""

    def __init__(self):
        from pure3270.emulation.screen_buffer import ScreenBuffer
        from pure3270.protocol.data_stream import DataStreamParser

        self.screen = ScreenBuffer(rows=24, cols=80)
        self.parser = DataStreamParser(self.screen)

    def test_stream(self, data_stream: bytes) -> Dict[str, Any]:
        """Test a data stream and return results."""
        results = {
            "parsed_successfully": False,
            "validation_errors": [],
            "screen_modified": False,
            "cursor_moved": False,
            "error_message": None,
        }

        try:
            # Reset parser state
            self.parser.clear_validation_errors()

            # Parse the stream
            self.parser.parse(data_stream)

            results["parsed_successfully"] = True
            results["validation_errors"] = self.parser.get_validation_errors()

            # Check if screen was modified
            # This is a simple check - in real implementation we'd compare snapshots
            results["screen_modified"] = True  # Assume modification for now

            # Check cursor position
            initial_cursor = (0, 0)  # Assume initial position
            current_cursor = (self.screen.cursor_row, self.screen.cursor_col)
            results["cursor_moved"] = current_cursor != initial_cursor

        except Exception as e:
            results["error_message"] = str(e)
            results["validation_errors"] = self.parser.get_validation_errors()

        return results


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage:")
        print(
            "  python tools/synthetic_data_generator.py generate <output_dir> [count]"
        )
        print("  python tools/synthetic_data_generator.py test <data_file>")
        print("  python tools/synthetic_data_generator.py edge_cases <output_dir>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "generate":
        output_dir = sys.argv[2]
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 20

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        generator = TN3270DataStreamGenerator()
        test_cases = generator.generate_test_cases(count)

        output_file = Path(output_dir) / "synthetic_test_cases.json"
        with open(output_file, "w") as f:
            json.dump(
                test_cases,
                f,
                indent=2,
                default=lambda x: x.hex() if isinstance(x, bytes) else str(x),
            )

        print(f"✓ Generated {count} synthetic test cases in {output_file}")

    elif command == "edge_cases":
        output_dir = sys.argv[2]
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        generator = TN3270DataStreamGenerator()
        edge_cases = generator.generate_edge_cases()

        output_file = Path(output_dir) / "edge_cases.json"
        with open(output_file, "w") as f:
            json.dump(
                edge_cases,
                f,
                indent=2,
                default=lambda x: x.hex() if isinstance(x, bytes) else str(x),
            )

        print(f"✓ Generated {len(edge_cases)} edge cases in {output_file}")

    elif command == "test":
        data_file = sys.argv[2]

        with open(data_file, "r") as f:
            test_cases = json.load(f)

        tester = DataStreamTester()
        results = []

        for test_case in test_cases:
            data_stream = bytes.fromhex(test_case["data_stream"])
            result = tester.test_stream(data_stream)
            result["test_case"] = test_case["id"]
            results.append(result)

        # Print summary
        successful = sum(1 for r in results if r["parsed_successfully"])
        total = len(results)

        print(f"Test Results: {successful}/{total} streams parsed successfully")

        for result in results:
            status = "✓" if result["parsed_successfully"] else "✗"
            print(
                f"  {status} {result['test_case']}: {len(result.get('validation_errors', []))} errors"
            )

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
