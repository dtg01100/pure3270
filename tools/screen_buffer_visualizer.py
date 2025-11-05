#!/usr/bin/env python3
"""
Screen Buffer Visualizer for Pure3270

Visualizes TN3270 screen buffer state for debugging complex screen operations.
Provides ASCII art representation of the screen with field attributes and cursor position.

Usage:
    python screen_buffer_visualizer.py --buffer-file buffer.json
    python screen_buffer_visualizer.py --live-session
    python screen_buffer_visualizer.py --from-trace trace_file.json --frame 10
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# EBCDIC to ASCII mapping for display
EBCDIC_TO_ASCII = {
    0x40: " ",  # Space
    0x4B: ".",  # Period
    0x5B: "$",  # Dollar sign
    0x6B: ",",  # Comma
    0x7B: "#",  # Hash
    # Add more mappings as needed
}


class ScreenBufferVisualizer:
    """Visualizes TN3270 screen buffer state."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None

    def load_buffer_from_file(self, filepath: str) -> Dict:
        """Load screen buffer data from JSON file."""
        with open(filepath, "r") as f:
            return json.load(f)

    def visualize_buffer(self, buffer_data: Dict, title: str = "Screen Buffer"):
        """Visualize the screen buffer."""
        if not buffer_data:
            print("No buffer data available")
            return

        # Extract buffer dimensions
        rows = buffer_data.get("rows", 24)
        cols = buffer_data.get("cols", 80)

        # Extract buffer content
        content = buffer_data.get("content", [])
        if isinstance(content, str):
            # Convert string to list if needed
            content = list(content)

        # Extract field attributes if available
        field_attrs = buffer_data.get("field_attributes", [])

        # Extract cursor position
        cursor_row = buffer_data.get("cursor_row", 0)
        cursor_col = buffer_data.get("cursor_col", 0)

        # Create visual representation
        screen_lines = []
        for row in range(rows):
            line = ""
            for col in range(cols):
                idx = row * cols + col
                if idx < len(content):
                    char_code = content[idx]
                    # Convert EBCDIC to ASCII for display
                    char = self._ebcdic_to_display_char(char_code)
                    line += char
                else:
                    line += " "

            # Add field attribute markers
            attr_markers = ""
            for attr in field_attrs:
                if attr.get("row") == row:
                    attr_markers += f"[{attr.get('type', 'field')}]"

            screen_lines.append(f"{row:2d}: {line}{attr_markers}")

        # Mark cursor position
        if cursor_row < len(screen_lines):
            cursor_line = screen_lines[cursor_row]
            # Insert cursor marker
            before_cursor = cursor_line[: 4 + cursor_col]
            after_cursor = cursor_line[4 + cursor_col :]
            screen_lines[cursor_row] = f"{before_cursor}[CURSOR]{after_cursor}"

        # Display
        screen_text = "\n".join(screen_lines)

        if self.console:
            panel = Panel(screen_text, title=title, border_style="blue")
            self.console.print(panel)
        else:
            print(f"=== {title} ===")
            print(screen_text)
            print("=" * (len(title) + 8))

    def _ebcdic_to_display_char(self, ebcdic_code: int) -> str:
        """Convert EBCDIC code to displayable character."""
        if ebcdic_code in EBCDIC_TO_ASCII:
            return EBCDIC_TO_ASCII[ebcdic_code]

        # Try to convert as ASCII if it's printable
        try:
            char = chr(ebcdic_code)
            if char.isprintable():
                return char
            else:
                return "."
        except:
            return "."

    def visualize_from_trace(self, trace_file: str, frame: int = 0):
        """Visualize screen buffer from trace file at specific frame."""
        with open(trace_file, "r") as f:
            trace_data = json.load(f)

        if "frames" in trace_data and frame < len(trace_data["frames"]):
            buffer_data = trace_data["frames"][frame].get("screen_buffer", {})
            title = f"Screen Buffer - Frame {frame}"
            self.visualize_buffer(buffer_data, title)
        else:
            print(f"Frame {frame} not found in trace")

    def compare_buffers(
        self,
        buffer1: Dict,
        buffer2: Dict,
        title1: str = "Buffer 1",
        title2: str = "Buffer 2",
    ):
        """Compare two screen buffers side by side."""
        if not self.console:
            print("Rich library required for side-by-side comparison")
            return

        # This would require more complex layout, for now just show sequentially
        self.visualize_buffer(buffer1, title1)
        print()
        self.visualize_buffer(buffer2, title2)


def main():
    parser = argparse.ArgumentParser(
        description="Screen Buffer Visualizer for Pure3270"
    )
    parser.add_argument("--buffer-file", help="JSON file containing screen buffer data")
    parser.add_argument("--trace-file", help="Trace file to visualize")
    parser.add_argument(
        "--frame", type=int, default=0, help="Frame number to visualize from trace"
    )
    parser.add_argument("--compare", nargs=2, help="Compare two buffer files")

    args = parser.parse_args()

    visualizer = ScreenBufferVisualizer()

    if args.compare:
        buffer1 = visualizer.load_buffer_from_file(args.compare[0])
        buffer2 = visualizer.load_buffer_from_file(args.compare[1])
        visualizer.compare_buffers(
            buffer1, buffer2, f"Buffer: {args.compare[0]}", f"Buffer: {args.compare[1]}"
        )
    elif args.trace_file:
        visualizer.visualize_from_trace(args.trace_file, args.frame)
    elif args.buffer_file:
        buffer_data = visualizer.load_buffer_from_file(args.buffer_file)
        visualizer.visualize_buffer(buffer_data)
    else:
        print("Please specify --buffer-file, --trace-file, or --compare")
        sys.exit(1)


if __name__ == "__main__":
    main()
