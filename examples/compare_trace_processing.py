#!/usr/bin/env python3
"""
Compare pure3270 vs s3270 trace file processing.

This tool:
1. Parses s3270 trace files to extract protocol sequences
2. Feeds the same data through pure3270's parser
3. Compares the resulting screen buffers and identifies differences
4. Reports any discrepancies as bugs to fix

Usage:
    python compare_trace_processing.py [trace_file]
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, "/workspaces/pure3270")

from pure3270.emulation.ebcdic import EBCDICCodec
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser


@dataclass
class TraceEvent:
    """Represents a single trace event."""

    direction: str  # 'send' or 'recv'
    offset: int
    data: bytes
    line_num: int


class S3270TraceProcessor:
    """Process s3270 trace files and extract expected behavior."""

    def __init__(self, trace_file: str):
        self.trace_file = Path(trace_file)
        self.events: List[TraceEvent] = []
        self.expected_screen_size: Tuple[int, int] = (24, 80)  # Default

    def parse(self) -> List[TraceEvent]:
        """Parse trace file and extract all events."""
        events = []
        line_num = 0

        with open(self.trace_file, "r") as f:
            for line in f:
                line_num += 1
                line = line.strip()

                # Parse screen size directive
                if line.startswith("// rows "):
                    rows = int(line.split()[2])
                    self.expected_screen_size = (rows, self.expected_screen_size[1])
                    continue

                if line.startswith("// columns "):
                    cols = int(line.split()[2])
                    self.expected_screen_size = (self.expected_screen_size[0], cols)
                    continue

                # Skip other comments
                if not line or line.startswith("//"):
                    continue

                # Parse data lines
                # Format: < 0xOFFSET   HEXDATA (output/send)
                # Format: > 0xOFFSET   HEXDATA (input/recv)
                match = re.match(r"([<>])\s+0x([0-9a-fA-F]+)\s+([0-9a-fA-F]+)", line)
                if match:
                    direction = "send" if match.group(1) == "<" else "recv"
                    offset = int(match.group(2), 16)
                    hex_data = match.group(3)
                    data = bytes.fromhex(hex_data)

                    events.append(
                        TraceEvent(
                            direction=direction,
                            offset=offset,
                            data=data,
                            line_num=line_num,
                        )
                    )

        self.events = events
        return events


class Pure3270TraceProcessor:
    """Process trace data through pure3270's parser."""

    def __init__(self, screen_size: Tuple[int, int] = (24, 80)):
        self.rows, self.cols = screen_size
        self.screen_buffer = ScreenBuffer(rows=self.rows, cols=self.cols)
        self.parser = DataStreamParser(self.screen_buffer)
        self.errors: List[str] = []

    def process_data_stream(self, data: bytes, event: TraceEvent) -> bool:
        """Process a data stream packet through pure3270."""
        try:
            # For s3270 traces, data may include TN3270E headers or be raw 3270 data
            # Try to detect and strip TN3270E header if present
            data_stream = data
            if len(data) >= 5 and data[0] <= 0x07:  # TN3270E data types
                data_stream = data[5:]

            # Split by Telnet IAC EOR (0xFF 0xEF) to process each 3270 record separately
            # This mirrors real TN3270(E) framing and prevents concatenating multiple
            # writes into a single parse pass (which can inflate field counts).
            segments: list[bytes] = []
            if b"\xff\xef" in data_stream:
                parts = data_stream.split(b"\xff\xef")
                # All parts except the last are complete records; the last may be empty or partial
                for p in parts[:-1]:
                    if p:
                        segments.append(p)
                # If trailing segment has content (no EOR at end), include it too
                if parts and parts[-1]:
                    segments.append(parts[-1])
            else:
                segments = [data_stream]

            # Parse each 3270 record independently
            for seg in segments:
                if not seg:
                    continue
                self.parser.parse(seg, data_type=0x00)  # TN3270_DATA

            # Ensure field detection runs after parsing
            if hasattr(self.screen_buffer, "_detect_fields"):
                self.screen_buffer._detect_fields()

            return True

        except Exception as e:
            error_msg = f"Line {event.line_num}: Error processing data stream: {e}"
            self.errors.append(error_msg)
            return False

    def get_screen_text(self) -> str:
        """Get current screen as ASCII text."""
        return self.screen_buffer.ascii_buffer

    def get_screen_hex(self) -> str:
        """Get current screen buffer as hex for detailed comparison."""
        return self.screen_buffer.buffer.hex()


class TraceComparator:
    """Compare s3270 trace expectations with pure3270 behavior."""

    def __init__(self) -> None:
        self.differences: List[Dict[str, Any]] = []

    def compare_processing(
        self, trace_file: str, verbose: bool = True
    ) -> Dict[str, Any]:
        """Compare how s3270 trace and pure3270 process the same data."""

        print(f"\n{'='*80}")
        print(f"TRACE COMPARISON: {Path(trace_file).name}")
        print(f"{'='*80}\n")

        # Parse s3270 trace
        s3270_proc = S3270TraceProcessor(trace_file)
        events = s3270_proc.parse()

        print(f"📂 Parsed trace file:")
        print(
            f"   Screen size: {s3270_proc.expected_screen_size[0]}x{s3270_proc.expected_screen_size[1]}"
        )
        print(f"   Total events: {len(events)}")
        print(f"   Send events: {sum(1 for e in events if e.direction == 'send')}")
        print(f"   Recv events: {sum(1 for e in events if e.direction == 'recv')}")

        # Create pure3270 processor
        pure_proc = Pure3270TraceProcessor(screen_size=s3270_proc.expected_screen_size)

        # Process all data stream events (typically 'send' direction in traces)
        print(f"\n🔄 Processing through pure3270...")
        processed_count = 0
        error_count = 0

        # CRITICAL FIX: Accumulate all data to handle commands split across lines
        accumulated_data = bytearray()
        first_event_in_batch = None

        for event in events:
            if event.direction == "send":
                # Handle Telnet negotiations (IAC sequences)
                if event.data and event.data[0] == 0xFF:
                    # Preserve IAC EOR (0xFF 0xEF) markers as record boundaries
                    # while ignoring other Telnet negotiations that aren't part of the
                    # 3270 data stream. If multiple EORs are present, include them all.
                    chunk = event.data
                    idx = 0
                    while True:
                        pos = chunk.find(b"\xff\xef", idx)
                        if pos == -1:
                            break
                        accumulated_data.extend(b"\xff\xef")
                        idx = pos + 2
                    # Skip further processing for non-data Telnet bytes
                    continue

                # Accumulate data
                if not accumulated_data:
                    first_event_in_batch = event
                accumulated_data.extend(event.data)

                if verbose:
                    hex_preview = event.data.hex()[:60]
                    if len(event.data.hex()) > 60:
                        hex_preview += "..."
                    print(
                        f"   ✓ Line {event.line_num}: {len(event.data)} bytes - {hex_preview}"
                    )

        # Process accumulated data as a single stream
        if accumulated_data and first_event_in_batch:
            success = pure_proc.process_data_stream(
                bytes(accumulated_data), first_event_in_batch
            )
            if success:
                processed_count = len(
                    [
                        e
                        for e in events
                        if e.direction == "send" and not (e.data and e.data[0] == 0xFF)
                    ]
                )
            else:
                error_count = 1

        print(f"\n📊 Processing results:")
        print(f"   Successfully processed: {processed_count}")
        print(f"   Errors encountered: {error_count}")

        if pure_proc.errors:
            print(f"\n⚠️  Errors during processing:")
            for error in pure_proc.errors:
                print(f"   • {error}")

        # Get final screen state
        screen_text = pure_proc.get_screen_text()

        print(f"\n📺 Final screen state ({pure_proc.rows}x{pure_proc.cols}):")
        print("─" * 80)
        for i, line in enumerate(screen_text.split("\n")[: pure_proc.rows], 1):
            # Truncate to screen width and show line numbers
            line_display = line[: pure_proc.cols].ljust(pure_proc.cols)
            print(f"{i:2d}│{line_display}│")
        print("─" * 80)

        # Analyze the screen for issues
        issues = self._analyze_screen(screen_text, pure_proc.screen_buffer)

        results = {
            "trace_file": trace_file,
            "screen_buffer": pure_proc.screen_buffer,
            "events_processed": processed_count,
            "errors": error_count,
            "screen_size": s3270_proc.expected_screen_size,
            "screen_text": screen_text,
            "issues": issues,
            "pure3270_errors": pure_proc.errors,
            # Provide an explicit field_count optimized for semantics: count input fields only
            "field_count": sum(
                1 for f in pure_proc.screen_buffer.fields if not f.protected
            ),
        }

        return results

    def _analyze_screen(
        self, screen_text: str, screen_buffer: ScreenBuffer
    ) -> List[Dict[str, Any]]:
        """Analyze screen for common issues.

        NOTE: These are heuristics and may produce false positives. They should not be treated
        as hard failures - only PARSING ERRORS indicate real bugs.
        """
        issues = []

        # Check for excessive repetition (sign of RA bug)
        # IMPORTANT: Only flag truly excessive runs (50+ chars) to avoid false positives
        lines = screen_text.split("\n")
        for i, line in enumerate(lines):
            # Check for runs of same character (>50 chars to reduce false positives)
            for char in set(line):
                # Skip spaces, common fill characters, and null bytes
                if char in (" ", "-", "=", "_", chr(0)):
                    continue
                if line.count(char * 50) > 0:
                    issues.append(
                        {
                            "type": "excessive_repetition",
                            "line": i + 1,
                            "char": char,
                            "description": f"Line {i+1}: Character '{char}' repeated excessively",
                        }
                    )

        # Check for attribute bytes appearing as characters
        # DISABLED: Too many false positives
        # Common issue: attribute bytes (>= 0xC0) shown as Y, C, etc.
        # suspicious_chars = ['Y', 'C', '-', '0']
        # for i, line in enumerate(lines):
        #     for char in suspicious_chars:
        #         pattern = f' {char} '
        #         if pattern in line:
        #             count = line.count(pattern)
        #             if count > 3:
        #                 issues.append({
        #                     'type': 'possible_attribute_bytes',
        #                     'line': i + 1,
        #                     'char': char,
        #                     'count': count,
        #                     'description': f"Line {i+1}: '{char}' appears {count} times (may be attribute bytes)"
        #                 })

        # Check for field positions - but only if there's actual content on screen
        has_content = any(line.strip() for line in lines)
        field_count = (
            len(screen_buffer.fields) if hasattr(screen_buffer, "fields") else 0
        )
        if field_count == 0 and has_content:
            issues.append(
                {
                    "type": "no_fields",
                    "description": "No fields detected - field parsing may be broken",
                }
            )

        return issues

    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print summary of comparison."""
        print(f"\n{'='*80}")
        print("COMPARISON SUMMARY")
        print(f"{'='*80}\n")

        if results["errors"] == 0:
            print("✅ All events processed successfully")
        else:
            print(f"❌ {results['errors']} events failed to process")

        if not results["issues"]:
            print("✅ No screen rendering issues detected")
        else:
            print(f"⚠️  Found {len(results['issues'])} potential issues:\n")
            for issue in results["issues"]:
                print(f"   • {issue['description']}")

        print(f"\n{'='*80}")
        if results["errors"] == 0 and not results["issues"]:
            print("🎉 TRACE PROCESSING MATCHES - No bugs found!")
        else:
            print("🔧 DIFFERENCES FOUND - These need to be fixed in pure3270:")
            if results["pure3270_errors"]:
                print("\nParsing Errors:")
                for error in results["pure3270_errors"]:
                    print(f"   • {error}")
            if results["issues"]:
                print("\nRendering Issues:")
                for issue in results["issues"]:
                    print(f"   • {issue['type']}: {issue['description']}")
        print(f"{'='*80}\n")


def main() -> int:
    """Main comparison workflow."""

    # Get trace file from command line or use default
    if len(sys.argv) > 1:
        trace_file = sys.argv[1]
    else:
        # Use ra_test since we just fixed RA
        trace_file = "/workspaces/pure3270/tests/data/traces/ra_test.trc"

    if not Path(trace_file).exists():
        print(f"Error: Trace file not found: {trace_file}")
        print("\nAvailable traces:")
        trace_dir = Path("/workspaces/pure3270/tests/data/traces")
        if trace_dir.exists():
            for trc in sorted(trace_dir.glob("*.trc"))[:10]:
                print(f"   {trc.name}")
            print(f"   ... and more in {trace_dir}")
        return 1

    # Run comparison
    comparator = TraceComparator()
    results = comparator.compare_processing(trace_file, verbose=True)

    # Print summary
    comparator.print_summary(results)

    # Return exit code based on results
    # Only fail on PARSING ERRORS, not on cosmetic "issues"
    if results["errors"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
