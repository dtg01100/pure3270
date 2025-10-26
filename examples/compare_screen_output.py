#!/usr/bin/env python3
"""
Screen Output Comparison Tool for Pure3270 vs s3270.

This tool provides side-by-side visual comparison of screen output between:
1. Pure3270 processing of trace data
2. Expected output inferred from s3270 trace analysis

Usage:
    python compare_screen_output.py [trace_file] [--diff-only] [--hex-view]
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add pure3270 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270.emulation.ebcdic import EBCDICCodec
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser


@dataclass
class ScreenComparison:
    """Result of screen comparison between implementations."""

    trace_file: str
    screen_size: Tuple[int, int]
    pure3270_screen: List[str]
    expected_screen: List[str]
    differences: List[Dict[str, Any]]
    match_percentage: float


class ScreenOutputComparator:
    """Compare screen output between pure3270 and expected s3270 behavior."""

    def __init__(self):
        self.ebcdic_codec = EBCDICCodec()

    def parse_trace_file(self, trace_file: str) -> List[bytes]:
        """Parse s3270 trace file and extract data streams."""
        data_streams = []

        with open(trace_file, "r") as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("//"):
                    continue

                # Parse data lines: > 0xOFFSET   HEXDATA (recv/server to client)
                # Parse data lines: < 0xOFFSET   HEXDATA (send/client to server)
                match = re.match(r"[<>]\s+0x[0-9a-fA-F]+\s+([0-9a-fA-F]+)", line)
                if match:
                    hex_data = match.group(1)
                    try:
                        data = bytes.fromhex(hex_data)
                        # Only collect data sent TO the client (from server)
                        if line.startswith(">"):
                            data_streams.append(data)
                            print(
                                f"   📥 Found {len(data)} bytes: {data.hex()[:40]}..."
                            )
                    except ValueError:
                        continue

        return data_streams

    def extract_screen_size(self, trace_file: str) -> Tuple[int, int]:
        """Extract screen size from trace file comments or model line."""
        rows, cols = 24, 80  # Default

        with open(trace_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("// rows "):
                    rows = int(line.split()[2])
                elif line.startswith("// columns "):
                    cols = int(line.split()[2])
                elif line.startswith("Model ") and "rows x" in line:
                    # Extract from "Model 3279-4-E, 43 rows x 80 cols, ..."
                    parts = line.split(",")
                    for part in parts:
                        part = part.strip()
                        if "rows x" in part:
                            size_part = part.split("rows x")[0].strip().split()[-1]
                            rows = int(size_part)
                        elif "cols" in part:
                            cols_part = part.split("cols")[0].strip().split()[-1]
                            cols = int(cols_part)

        return rows, cols

    def process_with_pure3270(
        self, data_streams: List[bytes], screen_size: Tuple[int, int]
    ) -> List[str]:
        """Process trace data through pure3270 and return screen lines."""
        rows, cols = screen_size
        screen_buffer = ScreenBuffer(rows=rows, cols=cols)
        parser = DataStreamParser(screen_buffer)

        # Accumulate all data streams into one (like compare_trace_processing.py does)
        # Skip telnet negotiations (IAC sequences)
        accumulated_data = bytearray()
        tn3270_data_streams = []

        for data_stream in data_streams:
            # Skip pure telnet negotiations (IAC sequences)
            if data_stream and data_stream[0] == 0xFF:
                print(f"   🚫 Skipping telnet negotiation: {data_stream.hex()[:20]}...")
                continue

            tn3270_data_streams.append(data_stream)
            accumulated_data.extend(data_stream)

        print(
            f"   📊 After filtering: {len(tn3270_data_streams)} TN3270 data streams, {len(accumulated_data)} bytes"
        )

        print(f"   📦 Accumulated {len(accumulated_data)} bytes of data")

        if accumulated_data:
            try:
                # Strip TN3270E header if present
                data = bytes(accumulated_data)
                print(f"   🔍 First 20 bytes: {data[:20].hex()}")

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
                    print("   📋 Stripping TN3270E header")
                    data = data[5:]

                print(f"   ⚙️  Parsing {len(data)} bytes of TN3270 data")
                print(f"   📄 Data: {data.hex()}")

                # Try to decode some orders for debugging
                pos = 0
                while pos < len(data):
                    if pos < len(data):
                        order = data[pos]
                        print(f"   🔍 Order at {pos}: 0x{order:02x}")
                        if order == 0x11:  # SBA - Set Buffer Address
                            if pos + 2 < len(data):
                                addr = (data[pos + 1] << 8) | data[pos + 2]
                                print(f"      SBA to address 0x{addr:04x}")
                                pos += 3
                            else:
                                break
                        elif order == 0x1D:  # SF - Start Field
                            if pos + 1 < len(data):
                                attr = data[pos + 1]
                                print(f"      SF with attribute 0x{attr:02x}")
                                pos += 2
                            else:
                                break
                        elif order in [
                            0xC1,
                            0xC2,
                            0xC3,
                            0xC4,
                            0xC5,
                            0xC6,
                            0xC7,
                            0xC8,
                            0xC9,
                            0xCA,
                            0xCB,
                            0xCC,
                            0xCD,
                            0xCE,
                            0xCF,
                        ]:  # Character data
                            print(f"      Character data: 0x{order:02x}")
                            pos += 1
                        else:
                            print(f"      Unknown order: 0x{order:02x}")
                            pos += 1
                    else:
                        break

                parser.parse(data, data_type=0x00)
                print("   ✅ Parsing completed successfully")
            except Exception as e:
                print(f"Parse error during data stream processing: {e}")
                # Continue anyway to show partial results

        # Get screen content
        screen_text = screen_buffer.ascii_buffer
        return screen_text.split("\n")[:rows]

    def get_expected_screen_for_trace(
        self, trace_file: str, screen_size: Tuple[int, int]
    ) -> List[str]:
        """Get the expected screen content for known trace files."""
        rows, cols = screen_size
        trace_name = Path(trace_file).name

        # Define expected outputs for specific traces
        expected_outputs = {
            "ra_test.trc": [""]
            * rows,  # Empty screen - RA test validates protocol, not screen content
            "ibmlink.trc": [
                "CUSTOMER ASSISTANCE: CALL 800-727-2222",
                "-------------------------------------------------------------------------------",
                "",
                "              W E L C O M E   T O",
                "",
                "  ===     ===============         ===============",
                "=======   ===============    ==   ===============",
                "====   ===        ===        ==  ==       ===",
                "===========       ===       ===   =       ===",
                "=============      ===        ====         ===",
                "===       ===      ===       == === =      ===",
                "===       ===      ===       ==   ==       ===",
                "===       ===      ===        ==== ==      ===",
                "",
                "   Provided by AT&T Global Network Services",
                "WARNING: Restricted System. Authori ed Access Only. Security Monitoring Active.",
                "-------------------------------------------------------------------------------",
                "ACCOUNT... ________ USERID... ________ PASSWORD...",
                "Enter desired product or service, or press the HELP key (PF) for assistance.",
                "",
                "===>",
            ],
            "empty.trc": [""] * rows,  # Truly empty screen
            "all_chars.trc": [""]
            * rows,  # No server responses - tests client sending, not screen content
        }

        if trace_name in expected_outputs:
            expected = expected_outputs[trace_name]
            # Pad or truncate to match screen size
            if len(expected) < rows:
                expected.extend([""] * (rows - len(expected)))
            return expected[:rows]

        # For unknown traces, show a generic message
        expected_screen = [""] * rows
        expected_screen[0] = f"Trace: {trace_name}"
        expected_screen[1] = f"Screen size: {rows}x{cols}"
        expected_screen[2] = "Expected output not defined for this trace"
        expected_screen[3] = "Compare with pure3270 output manually"
        return expected_screen

    def compare_screens(
        self, pure3270_screen: List[str], expected_screen: List[str]
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Compare two screen representations and return differences."""
        differences = []
        total_chars = 0
        matching_chars = 0

        max_lines = max(len(pure3270_screen), len(expected_screen))

        for i in range(max_lines):
            pure_line = pure3270_screen[i] if i < len(pure3270_screen) else ""
            expected_line = expected_screen[i] if i < len(expected_screen) else ""

            # Pad lines to same length for comparison
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
                            "position": (i + 1, j + 1),  # 1-based indexing
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

    def compare_trace(
        self, trace_file: str, diff_only: bool = False, hex_view: bool = False
    ) -> ScreenComparison:
        """Compare screen output for a trace file."""
        print(f"🔍 Analyzing trace file: {Path(trace_file).name}")

        # Parse trace data
        data_streams = self.parse_trace_file(trace_file)
        screen_size = self.extract_screen_size(trace_file)

        print(f"   📊 Found {len(data_streams)} data streams")
        print(f"   📺 Screen size: {screen_size[0]}x{screen_size[1]}")

        # For traces with no server responses, we can't process them through pure3270
        # as pure3270 expects server data. Instead, show what pure3270 would produce
        # if it received typical data, and compare against expected behavior.
        if not data_streams:
            print(
                "   ⚠️  No server responses in trace - showing expected vs. empty screen comparison"
            )
            pure3270_screen = [""] * screen_size[0]  # Empty screen
        else:
            # Process with pure3270
            pure3270_screen = self.process_with_pure3270(data_streams, screen_size)

        # Get expected screen for this trace
        expected_screen = self.get_expected_screen_for_trace(trace_file, screen_size)

        # Compare screens
        differences, match_percentage = self.compare_screens(
            pure3270_screen, expected_screen
        )

        return ScreenComparison(
            trace_file=trace_file,
            screen_size=screen_size,
            pure3270_screen=pure3270_screen,
            expected_screen=expected_screen,
            differences=differences,
            match_percentage=match_percentage,
        )

    def display_comparison(
        self,
        comparison: ScreenComparison,
        diff_only: bool = False,
        hex_view: bool = False,
    ):
        """Display side-by-side screen comparison."""
        print(f"\n{'='*100}")
        print(f"SCREEN OUTPUT COMPARISON: {Path(comparison.trace_file).name}")
        print(f"{'='*100}")
        print(f"Screen Size: {comparison.screen_size[0]}x{comparison.screen_size[1]}")
        print(f"Match: {comparison.match_percentage:.1f}%")
        if comparison.differences:
            print(f"Differences found: {len(comparison.differences)} lines")
        else:
            print("✅ No differences found - screens match!")

        print(f"{'='*100}")

        # Display screens side by side
        rows = max(len(comparison.pure3270_screen), len(comparison.expected_screen))

        print(f"{'Pure3270 Output':<50} │ {'Expected (s3270) Output':<50}")
        print("─" * 50 + "─┼" + "─" * 50)

        for i in range(rows):
            pure_line = (
                comparison.pure3270_screen[i]
                if i < len(comparison.pure3270_screen)
                else ""
            )
            expected_line = (
                comparison.expected_screen[i]
                if i < len(comparison.expected_screen)
                else ""
            )

            # Truncate to 48 chars for display
            pure_display = pure_line[:48].ljust(48)
            expected_display = expected_line[:48].ljust(48)

            # Highlight differences if this line has them
            line_has_diff = any(d["line"] == i + 1 for d in comparison.differences)

            if line_has_diff and not diff_only:
                # Show differences in red (using ANSI codes)
                print(
                    f"\033[91m{pure_display}\033[0m │ \033[91m{expected_display}\033[0m"
                )
            elif not diff_only or line_has_diff:
                print(f"{pure_display} │ {expected_display}")

        print("─" * 50 + "─┴" + "─" * 50)

        # Show detailed differences
        if comparison.differences and not diff_only:
            print(f"\n🔍 DETAILED DIFFERENCES ({len(comparison.differences)} lines):")
            for diff in comparison.differences[:10]:  # Show first 10 differences
                print(f"\nLine {diff['line']}:")
                print(f"  Pure3270: {diff['pure3270_line']}")
                print(f"  Expected: {diff['expected_line']}")

                # Show character-by-character differences
                for char_diff in diff["differences"][:20]:  # Show first 20 per line
                    pos = char_diff["position"]
                    print(
                        f"    Position {pos[0]},{pos[1]}: '{char_diff['pure3270']}' vs '{char_diff['expected']}'"
                    )

            if len(comparison.differences) > 10:
                print(f"    ... and {len(comparison.differences) - 10} more lines")

        if hex_view:
            print(f"\n🔢 HEX VIEW:")
            print("Pure3270:")
            for i, line in enumerate(comparison.pure3270_screen[:5]):
                hex_data = " ".join(f"{ord(c):02x}" for c in line[:20])
                print(f"  Line {i+1}: {hex_data}")

            print("Expected:")
            for i, line in enumerate(comparison.expected_screen[:5]):
                hex_data = " ".join(f"{ord(c):02x}" for c in line[:20])
                print(f"  Line {i+1}: {hex_data}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare screen output between pure3270 and s3270"
    )
    parser.add_argument("trace_file", help="s3270 trace file to analyze")
    parser.add_argument(
        "--diff-only", action="store_true", help="Only show lines with differences"
    )
    parser.add_argument(
        "--hex-view", action="store_true", help="Show hex representation of screen data"
    )

    args = parser.parse_args()

    if not Path(args.trace_file).exists():
        print(f"Error: Trace file not found: {args.trace_file}")
        return 1

    # Perform comparison
    comparator = ScreenOutputComparator()
    comparison = comparator.compare_trace(
        args.trace_file, args.diff_only, args.hex_view
    )

    # Display results
    comparator.display_comparison(comparison, args.diff_only, args.hex_view)

    return 0


if __name__ == "__main__":
    sys.exit(main())
