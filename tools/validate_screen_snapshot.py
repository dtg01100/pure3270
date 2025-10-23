#!/usr/bin/env python3
"""
Screen snapshot validation tool for Pure3270.

This tool captures, compares, and validates screen buffer snapshots to prevent
regressions in screen rendering. It supports both ASCII and EBCDIC modes.

Usage:
    python tools/validate_screen_snapshot.py capture <output_file>
    python tools/validate_screen_snapshot.py compare <expected_file> <actual_file>
    python tools/validate_screen_snapshot.py validate <snapshot_file>
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add pure3270 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270.emulation.screen_buffer import ScreenBuffer


class ScreenSnapshot:
    """Represents a normalized screen snapshot for comparison."""

    def __init__(self, screen_buffer: ScreenBuffer):
        self.rows = screen_buffer.rows
        self.cols = screen_buffer.cols
        self.ascii_mode = screen_buffer._ascii_mode
        self.cursor_row = screen_buffer.cursor_row
        self.cursor_col = screen_buffer.cursor_col

        # Normalize the screen content
        self.content = self._normalize_content(screen_buffer.ascii_buffer)

    def _normalize_content(self, ascii_buffer: str) -> str:
        """Normalize screen content for consistent comparison.

        - Strip trailing whitespace from each line
        - Ensure consistent line endings (LF)
        - Preserve empty lines but normalize them
        """
        lines = ascii_buffer.split("\n")

        # Normalize each line: strip trailing whitespace, ensure consistent representation
        normalized_lines = []
        for line in lines:
            # Strip trailing whitespace but preserve the line
            normalized_line = line.rstrip()
            normalized_lines.append(normalized_line)

        # Rejoin with consistent line endings
        return "\n".join(normalized_lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for JSON serialization."""
        return {
            "version": "1.0",
            "metadata": {
                "rows": self.rows,
                "cols": self.cols,
                "ascii_mode": self.ascii_mode,
                "cursor_row": self.cursor_row,
                "cursor_col": self.cursor_col,
            },
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScreenSnapshot":
        """Create snapshot from dictionary (deserialized JSON)."""
        if data.get("version") != "1.0":
            raise ValueError(f"Unsupported snapshot version: {data.get('version')}")

        metadata = data.get("metadata", {})
        content = data.get("content", "")

        # Create a temporary screen buffer to hold the data
        screen = ScreenBuffer(
            rows=metadata.get("rows", 24), cols=metadata.get("cols", 80)
        )

        # Set ASCII mode if specified
        if metadata.get("ascii_mode", False):
            screen._ascii_mode = True

        # Set cursor position
        screen.cursor_row = metadata.get("cursor_row", 0)
        screen.cursor_col = metadata.get("cursor_col", 0)

        # Populate buffer from normalized content
        lines = content.split("\n")
        for row, line in enumerate(lines):
            if row >= screen.rows:
                break
            # Pad or truncate line to fit screen width
            padded_line = line.ljust(screen.cols)[: screen.cols]
            for col, char in enumerate(padded_line):
                if screen._ascii_mode:
                    # In ASCII mode, store ASCII bytes directly
                    screen.buffer[row * screen.cols + col] = ord(char)
                else:
                    # In EBCDIC mode, convert ASCII to EBCDIC
                    from pure3270.emulation.ebcdic import EBCDICCodec

                    ebcdic_result = EBCDICCodec().encode(char)
                    ebcdic_bytes, _ = ebcdic_result if ebcdic_result else (b"", 0)
                    if ebcdic_bytes:
                        screen.buffer[row * screen.cols + col] = ebcdic_bytes[0]
                    else:
                        screen.buffer[row * screen.cols + col] = 0x40

        # Create snapshot from the populated buffer
        snapshot = cls(screen)
        return snapshot

    def save(self, filepath: str) -> None:
        """Save snapshot to JSON file."""
        data = self.to_dict()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> "ScreenSnapshot":
        """Load snapshot from JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def compare(self, other: "ScreenSnapshot") -> Dict[str, Any]:
        """Compare this snapshot with another.

        Returns a dictionary with comparison results and any differences.
        """
        differences = []

        # Check metadata differences
        if self.rows != other.rows:
            differences.append(f"Rows mismatch: {self.rows} vs {other.rows}")
        if self.cols != other.cols:
            differences.append(f"Columns mismatch: {self.cols} vs {other.cols}")
        if self.ascii_mode != other.ascii_mode:
            differences.append(
                f"ASCII mode mismatch: {self.ascii_mode} vs {other.ascii_mode}"
            )
        if self.cursor_row != other.cursor_row:
            differences.append(
                f"Cursor row mismatch: {self.cursor_row} vs {other.cursor_row}"
            )
        if self.cursor_col != other.cursor_col:
            differences.append(
                f"Cursor col mismatch: {self.cursor_col} vs {other.cursor_col}"
            )

        # Check content differences
        if self.content != other.content:
            differences.append("Screen content differs")

            # Provide detailed diff
            self_lines = self.content.split("\n")
            other_lines = other.content.split("\n")

            max_lines = max(len(self_lines), len(other_lines))
            for i in range(max_lines):
                self_line = self_lines[i] if i < len(self_lines) else ""
                other_line = other_lines[i] if i < len(other_lines) else ""

                if self_line != other_line:
                    differences.append(f"Line {i+1}: '{self_line}' vs '{other_line}'")

        return {
            "match": len(differences) == 0,
            "differences": differences,
            "expected_lines": len(self.content.split("\n")),
            "actual_lines": len(other.content.split("\n")),
        }


def capture_snapshot(screen_buffer: ScreenBuffer, output_file: str) -> None:
    """Capture a snapshot from the current screen buffer."""
    snapshot = ScreenSnapshot(screen_buffer)
    snapshot.save(output_file)
    print(f"✓ Snapshot captured to {output_file}")
    print(f"  Dimensions: {snapshot.rows}x{snapshot.cols}")
    print(f"  ASCII mode: {snapshot.ascii_mode}")
    print(f"  Cursor: ({snapshot.cursor_row}, {snapshot.cursor_col})")


def compare_snapshots(expected_file: str, actual_file: str) -> bool:
    """Compare two snapshot files. Returns True if they match."""
    try:
        expected = ScreenSnapshot.load(expected_file)
        actual = ScreenSnapshot.load(actual_file)

        result = expected.compare(actual)

        if result["match"]:
            print("✓ Snapshots match")
            return True
        else:
            print("✗ Snapshots differ:")
            for diff in result["differences"]:
                print(f"  {diff}")
            return False

    except Exception as e:
        print(f"✗ Error comparing snapshots: {e}")
        return False


def validate_snapshot(snapshot_file: str) -> bool:
    """Validate that a snapshot file can be loaded and is well-formed."""
    try:
        snapshot = ScreenSnapshot.load(snapshot_file)
        print(
            f"✓ Snapshot is valid: {snapshot.rows}x{snapshot.cols}, ASCII mode: {snapshot.ascii_mode}"
        )
        return True
    except Exception as e:
        print(f"✗ Invalid snapshot: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Screen snapshot validation tool for Pure3270"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Capture command
    capture_parser = subparsers.add_parser("capture", help="Capture screen snapshot")
    capture_parser.add_argument("output_file", help="Output snapshot file path")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two snapshots")
    compare_parser.add_argument("expected_file", help="Expected snapshot file")
    compare_parser.add_argument("actual_file", help="Actual snapshot file")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate snapshot file")
    validate_parser.add_argument("snapshot_file", help="Snapshot file to validate")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # For now, create a dummy screen buffer for testing
    # In real usage, this would be passed from the session
    screen = ScreenBuffer(rows=24, cols=80)

    # Don't add test content for baseline captures - keep it truly empty
    # Add some test content
    # test_content = "Hello, World!\nThis is a test screen.\nLine 3"
    # for i, char in enumerate(test_content):
    #     if i < len(screen.buffer):
    #         screen.buffer[i] = ord(char) if ord(char) < 128 else 0x40

    if args.command == "capture":
        capture_snapshot(screen, args.output_file)
        return 0
    elif args.command == "compare":
        success = compare_snapshots(args.expected_file, args.actual_file)
        return 0 if success else 1
    elif args.command == "validate":
        success = validate_snapshot(args.snapshot_file)
        return 0 if success else 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
