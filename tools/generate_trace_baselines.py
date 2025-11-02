#!/usr/bin/env python3
"""
Generate baseline expected outputs for trace files.

This tool processes traces and saves their actual screen outputs as JSON baselines
that can be used for regression testing.
"""

import json
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser


def parse_trace_file(trace_file: Path) -> List[bytes]:
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


def extract_screen_size(trace_file: Path) -> tuple[int, int]:
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


def process_trace(trace_file: Path) -> List[str]:
    """Process trace and return screen lines."""
    data_streams = parse_trace_file(trace_file)
    rows, cols = extract_screen_size(trace_file)

    screen_buffer = ScreenBuffer(rows=rows, cols=cols)
    parser = DataStreamParser(screen_buffer)

    # Accumulate all data streams
    accumulated_data = bytearray()
    for data_stream in data_streams:
        # Skip telnet negotiations
        if data_stream and data_stream[0] == 0xFF:
            continue
        accumulated_data.extend(data_stream)

    if accumulated_data:
        try:
            data = bytes(accumulated_data)
            # Strip TN3270E header if present
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
            print(f"  Warning: Parse error for {trace_file.name}: {e}")

    # Get screen content
    screen_text = screen_buffer.ascii_buffer
    return screen_text.split("\n")[:rows]


def generate_baseline(trace_file: Path, output_dir: Path) -> None:
    """Generate baseline for a single trace file."""
    print(f"Processing {trace_file.name}...")

    screen_lines = process_trace(trace_file)

    baseline = {
        "trace_file": trace_file.name,
        "rows": len(screen_lines),
        "cols": len(screen_lines[0]) if screen_lines else 0,
        "screen_lines": screen_lines,
    }

    # Save baseline
    output_file = output_dir / f"{trace_file.stem}.json"
    with open(output_file, "w") as f:
        json.dump(baseline, f, indent=2)

    print(f"  ✓ Saved baseline to {output_file}")


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate trace baselines")
    parser.add_argument(
        "trace_files", nargs="+", type=Path, help="Trace files to process"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tests/data/baselines"),
        help="Output directory for baselines",
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Process each trace
    for trace_file in args.trace_files:
        if not trace_file.exists():
            print(f"Warning: {trace_file} not found, skipping")
            continue

        try:
            generate_baseline(trace_file, args.output_dir)
        except Exception as e:
            print(f"Error processing {trace_file}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
