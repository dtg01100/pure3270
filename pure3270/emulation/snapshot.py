"""Screen buffer snapshot and comparison system for regression testing."""

import base64
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from .screen_buffer import Field, ScreenBuffer

logger = logging.getLogger(__name__)


class ScreenSnapshot:
    """Represents a snapshot of a ScreenBuffer state for regression testing."""

    def __init__(self, screen_buffer: ScreenBuffer):
        """Create a snapshot from a ScreenBuffer instance."""
        self.metadata = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "ascii_mode": screen_buffer.is_ascii_mode(),
            "rows": screen_buffer.rows,
            "cols": screen_buffer.cols,
        }

        # Capture buffer and attributes as base64 for JSON serialization
        self.buffer = base64.b64encode(screen_buffer.buffer).decode("ascii")
        self.attributes = base64.b64encode(screen_buffer.attributes).decode("ascii")

        # Capture cursor position
        self.cursor = {"row": screen_buffer.cursor_row, "col": screen_buffer.cursor_col}

        # Capture extended attributes
        self.extended_attributes = {}
        for (row, col), attrs in screen_buffer._extended_attributes.items():
            self.extended_attributes[f"({row},{col})"] = dict(attrs)

        # Capture fields
        self.fields = []
        for field in screen_buffer.fields:
            field_dict = {
                "start": list(field.start),
                "end": list(field.end),
                "protected": field.protected,
                "numeric": field.numeric,
                "modified": field.modified,
                "selected": field.selected,
                "intensity": field.intensity,
                "color": field.color,
                "background": field.background,
                "validation": field.validation,
                "outlining": field.outlining,
                "character_set": field.character_set,
                "sfe_highlight": field.sfe_highlight,
                "content": base64.b64encode(field.content).decode("ascii"),
            }
            self.fields.append(field_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for JSON serialization."""
        return {
            "metadata": self.metadata,
            "buffer": self.buffer,
            "attributes": self.attributes,
            "cursor": self.cursor,
            "extended_attributes": self.extended_attributes,
            "fields": self.fields,
        }

    def to_json(self) -> str:
        """Convert snapshot to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScreenSnapshot":
        """Create snapshot from dictionary data."""
        snapshot = cls.__new__(cls)  # Create without calling __init__

        # Restore metadata
        snapshot.metadata = data["metadata"]

        # Restore binary data
        snapshot.buffer = data["buffer"]
        snapshot.attributes = data["attributes"]
        snapshot.cursor = data["cursor"]
        snapshot.extended_attributes = data.get("extended_attributes", {})
        snapshot.fields = data.get("fields", [])

        return snapshot

    @classmethod
    def from_json(cls, json_str: str) -> "ScreenSnapshot":
        """Create snapshot from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def to_screen_buffer(self) -> ScreenBuffer:
        """Reconstruct a ScreenBuffer from this snapshot."""
        # Create new screen buffer with snapshot dimensions
        rows = cast(int, self.metadata["rows"])
        cols = cast(int, self.metadata["cols"])
        ascii_mode = cast(bool, self.metadata["ascii_mode"])

        screen_buffer = ScreenBuffer(rows=rows, cols=cols)

        # Set ASCII mode
        screen_buffer.set_ascii_mode(ascii_mode)

        # Restore buffer and attributes
        screen_buffer.buffer = bytearray(base64.b64decode(self.buffer))
        screen_buffer.attributes = bytearray(base64.b64decode(self.attributes))

        # Restore cursor position
        screen_buffer.cursor_row = self.cursor["row"]
        screen_buffer.cursor_col = self.cursor["col"]

        # Restore extended attributes
        for pos_str, attrs in self.extended_attributes.items():
            row, col = map(int, pos_str.strip("()").split(","))
            for attr_type, value in attrs.items():
                screen_buffer.set_extended_attribute(row, col, attr_type, value)

        # Restore fields
        screen_buffer.fields = []
        for field_dict in self.fields:
            start_list = cast(List[int], field_dict["start"])
            end_list = cast(List[int], field_dict["end"])

            field = Field(
                start=(start_list[0], start_list[1]),
                end=(end_list[0], end_list[1]),
                protected=cast(bool, field_dict["protected"]),
                numeric=cast(bool, field_dict["numeric"]),
                modified=cast(bool, field_dict["modified"]),
                selected=cast(bool, field_dict["selected"]),
                intensity=cast(int, field_dict["intensity"]),
                color=cast(int, field_dict["color"]),
                background=cast(int, field_dict["background"]),
                validation=cast(int, field_dict["validation"]),
                outlining=cast(int, field_dict["outlining"]),
                character_set=cast(int, field_dict["character_set"]),
                sfe_highlight=cast(int, field_dict["sfe_highlight"]),
                content=base64.b64decode(cast(str, field_dict["content"])),
            )
            screen_buffer.fields.append(field)

        return screen_buffer

    def save_to_file(self, filepath: str) -> None:
        """Save snapshot to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        logger.info(f"Snapshot saved to {filepath}")

    @classmethod
    def load_from_file(cls, filepath: str) -> "ScreenSnapshot":
        """Load snapshot from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            snapshot = cls.from_json(f.read())
        logger.info(f"Snapshot loaded from {filepath}")
        return snapshot


def take_snapshot(screen_buffer: ScreenBuffer) -> ScreenSnapshot:
    """Convenience function to take a snapshot of a ScreenBuffer."""
    return ScreenSnapshot(screen_buffer)


def create_ascii_mode_snapshot(screen_buffer: ScreenBuffer) -> ScreenSnapshot:
    """Create a snapshot with the screen buffer in ASCII mode."""
    original_mode = screen_buffer.is_ascii_mode()
    screen_buffer.set_ascii_mode(True)

    try:
        snapshot = ScreenSnapshot(screen_buffer)
        return snapshot
    finally:
        # Always restore original mode
        screen_buffer.set_ascii_mode(original_mode)


def create_ebcdic_mode_snapshot(screen_buffer: ScreenBuffer) -> ScreenSnapshot:
    """Create a snapshot with the screen buffer in EBCDIC mode."""
    original_mode = screen_buffer.is_ascii_mode()
    screen_buffer.set_ascii_mode(False)

    try:
        snapshot = ScreenSnapshot(screen_buffer)
        return snapshot
    finally:
        # Always restore original mode
        screen_buffer.set_ascii_mode(original_mode)


def compare_snapshots_cross_mode(
    snapshot1: ScreenSnapshot, snapshot2: ScreenSnapshot
) -> "SnapshotComparison":
    """Compare two snapshots that may be in different modes.

    This function handles the complexity of comparing snapshots that might be
    in different character modes (ASCII vs EBCDIC) by normalizing them for comparison.
    """
    # If both snapshots are in the same mode, use regular comparison
    if snapshot1.metadata["ascii_mode"] == snapshot2.metadata["ascii_mode"]:
        return compare_snapshots(snapshot1, snapshot2)

    # For cross-mode comparison, we need to compare the semantic content
    # rather than the raw bytes. This is a simplified approach that compares
    # the decoded text content.

    # Create temporary screen buffers from snapshots
    buffer1 = snapshot1.to_screen_buffer()
    buffer2 = snapshot2.to_screen_buffer()

    # Get the text representation for comparison
    text1 = buffer1.to_text()
    text2 = buffer2.to_text()

    # Create a simplified comparison result
    comparison = SnapshotComparison(snapshot1, snapshot2)
    comparison.is_identical = text1 == text2

    if not comparison.is_identical:
        comparison.differences["cross_mode_text"] = {
            "text1": text1,
            "text2": text2,
            "ascii_mode1": snapshot1.metadata["ascii_mode"],
            "ascii_mode2": snapshot2.metadata["ascii_mode"],
        }

    return comparison


class ModeAwareSnapshotComparator:
    """Advanced comparator that handles both ASCII and EBCDIC modes intelligently."""

    def __init__(self, mode_handling: str = "strict"):
        """Initialize comparator with mode handling strategy.

        Args:
            mode_handling: How to handle mode differences
                - "strict": Only compare snapshots in same mode
                - "convert": Convert to common mode for comparison
                - "semantic": Compare semantic content across modes
        """
        self.mode_handling = mode_handling

    def compare(
        self, snapshot1: ScreenSnapshot, snapshot2: ScreenSnapshot
    ) -> SnapshotComparison:
        """Compare two snapshots using the configured mode handling strategy."""
        if self.mode_handling == "strict":
            return compare_snapshots(snapshot1, snapshot2)
        elif self.mode_handling == "convert":
            return self._compare_with_conversion(snapshot1, snapshot2)
        elif self.mode_handling == "semantic":
            return compare_snapshots_cross_mode(snapshot1, snapshot2)
        else:
            raise ValueError(f"Unknown mode handling strategy: {self.mode_handling}")

    def _compare_with_conversion(
        self, snapshot1: ScreenSnapshot, snapshot2: ScreenSnapshot
    ) -> SnapshotComparison:
        """Compare snapshots by converting to a common mode."""
        # Determine target mode (prefer ASCII if either is ASCII)
        target_mode = (
            snapshot1.metadata["ascii_mode"] or snapshot2.metadata["ascii_mode"]
        )

        # Convert snapshots to target mode
        buffer1 = snapshot1.to_screen_buffer()
        buffer2 = snapshot2.to_screen_buffer()

        original_mode1 = buffer1.is_ascii_mode()
        original_mode2 = buffer2.is_ascii_mode()

        try:
            buffer1.set_ascii_mode(bool(target_mode))
            buffer2.set_ascii_mode(bool(target_mode))

            # Create new snapshots in target mode
            converted_snapshot1 = ScreenSnapshot(buffer1)
            converted_snapshot2 = ScreenSnapshot(buffer2)

            return compare_snapshots(converted_snapshot1, converted_snapshot2)

        finally:
            # Restore original modes
            buffer1.set_ascii_mode(original_mode1)
            buffer2.set_ascii_mode(original_mode2)


class SnapshotComparison:
    """Represents the result of comparing two snapshots."""

    def __init__(self, snapshot1: ScreenSnapshot, snapshot2: ScreenSnapshot):
        """Compare two snapshots and identify differences."""
        self.snapshot1 = snapshot1
        self.snapshot2 = snapshot2
        self.is_identical = True
        self.differences: Dict[str, Any] = {}

        # Compare metadata
        if snapshot1.metadata != snapshot2.metadata:
            self.is_identical = False
            self.differences["metadata"] = {
                "before": snapshot1.metadata,
                "after": snapshot2.metadata,
            }

        # Compare buffer
        if snapshot1.buffer != snapshot2.buffer:
            self.is_identical = False
            self.differences["buffer"] = {
                "before": snapshot1.buffer,
                "after": snapshot2.buffer,
            }

        # Compare attributes
        if snapshot1.attributes != snapshot2.attributes:
            self.is_identical = False
            self.differences["attributes"] = {
                "before": snapshot1.attributes,
                "after": snapshot2.attributes,
            }

        # Compare cursor
        if snapshot1.cursor != snapshot2.cursor:
            self.is_identical = False
            self.differences["cursor"] = {
                "before": snapshot1.cursor,
                "after": snapshot2.cursor,
            }

        # Compare extended attributes
        if snapshot1.extended_attributes != snapshot2.extended_attributes:
            self.is_identical = False
            self.differences["extended_attributes"] = {
                "before": snapshot1.extended_attributes,
                "after": snapshot2.extended_attributes,
            }

        # Compare fields
        if len(snapshot1.fields) != len(snapshot2.fields):
            self.is_identical = False
            self.differences["fields_count"] = {
                "before": len(snapshot1.fields),
                "after": len(snapshot2.fields),
            }
        else:
            for i, (field1, field2) in enumerate(
                zip(snapshot1.fields, snapshot2.fields)
            ):
                if field1 != field2:
                    self.is_identical = False
                    if "fields" not in self.differences:
                        self.differences["fields"] = {}
                    self.differences["fields"][f"field_{i}"] = {
                        "before": field1,
                        "after": field2,
                    }

    def has_differences(self) -> bool:
        """Return True if there are any differences between snapshots."""
        return not self.is_identical

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the comparison results."""
        return {
            "is_identical": self.is_identical,
            "differences_count": len(self.differences),
            "differences": list(self.differences.keys()),
        }

    def print_report(self) -> None:
        """Print a human-readable comparison report."""
        print("=== Snapshot Comparison Report ===")
        print(f"Overall: {'IDENTICAL' if self.is_identical else 'DIFFERENCES FOUND'}")

        if self.is_identical:
            return

        print(f"\nDifferences found in {len(self.differences)} areas:")
        for diff_type, diff_data in self.differences.items():
            print(f"\n- {diff_type.upper()}:")
            if (
                isinstance(diff_data, dict)
                and "before" in diff_data
                and "after" in diff_data
            ):
                print(f"  Before: {diff_data['before']}")
                print(f"  After:  {diff_data['after']}")
            else:
                print(f"  {diff_data}")


def compare_snapshots(
    snapshot1: ScreenSnapshot, snapshot2: ScreenSnapshot
) -> SnapshotComparison:
    """Convenience function to compare two snapshots."""
    return SnapshotComparison(snapshot1, snapshot2)


class SnapshotDiffer:
    """Advanced snapshot comparison with detailed diff analysis."""

    def __init__(self, snapshot1: ScreenSnapshot, snapshot2: ScreenSnapshot):
        """Initialize differ with two snapshots."""
        self.snapshot1 = snapshot1
        self.snapshot2 = snapshot2
        self.comparison = SnapshotComparison(snapshot1, snapshot2)

    def get_buffer_diff_positions(self) -> List[Tuple[int, int, int, int]]:
        """Get positions where buffer bytes differ."""
        if self.comparison.is_identical or "buffer" not in self.comparison.differences:
            return []

        buffer1 = base64.b64decode(self.snapshot1.buffer)
        buffer2 = base64.b64decode(self.snapshot2.buffer)

        cols = cast(int, self.snapshot1.metadata["cols"])
        positions = []
        for i, (b1, b2) in enumerate(zip(buffer1, buffer2)):
            if b1 != b2:
                row = i // cols
                col = i % cols
                positions.append((row, col, b1, b2))

        return positions

    def get_attribute_diff_positions(self) -> List[Tuple[int, int, int, int]]:
        """Get positions where attributes differ."""
        if (
            self.comparison.is_identical
            or "attributes" not in self.comparison.differences
        ):
            return []

        attrs1 = base64.b64decode(self.snapshot1.attributes)
        attrs2 = base64.b64decode(self.snapshot2.attributes)

        cols = cast(int, self.snapshot1.metadata["cols"])
        positions = []
        for i in range(0, len(attrs1), 3):
            if attrs1[i : i + 3] != attrs2[i : i + 3]:
                row = i // (cols * 3)
                col = (i % (cols * 3)) // 3
                positions.append((row, col, attrs1[i], attrs2[i]))

        return positions

    def get_field_differences(self) -> Dict[str, Any]:
        """Get detailed field differences."""
        if self.comparison.is_identical or "fields" not in self.comparison.differences:
            return {}

        field_diffs = {}
        fields1 = self.snapshot1.fields
        fields2 = self.snapshot2.fields

        # Find added/removed fields
        for i, field in enumerate(fields2):
            if i >= len(fields1) or field != fields1[i]:
                field_diffs[f"field_{i}"] = {
                    "type": "modified_or_added",
                    "field": field,
                }

        for i, field in enumerate(fields1):
            if i >= len(fields2) or field != fields2[i]:
                field_diffs[f"field_{i}"] = {
                    "type": "modified_or_removed",
                    "field": field,
                }

        return field_diffs
