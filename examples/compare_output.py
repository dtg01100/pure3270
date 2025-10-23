#!/usr/bin/env python3
"""
Compare pure3270 vs p3270 screen output side-by-side
"""

import subprocess
import sys


def run_script(script_name):
    """Run a test script and capture output"""
    try:
        result = subprocess.run(
            ["timeout", "30", "python", script_name],
            capture_output=True,
            text=True,
            timeout=35,
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT"


def extract_screen(output, marker="Screen after sending Enter:"):
    """Extract screen content after marker"""
    lines = output.split("\n")
    try:
        idx = next(i for i, line in enumerate(lines) if marker in line)
        # Get next 24 lines (standard 3270 screen)
        screen_lines = lines[idx + 1 : idx + 25]
        return screen_lines
    except StopIteration:
        return []


def compare_screens():
    """Compare pure3270 vs p3270 output"""
    print("Running pure3270 test...")
    pure_output = run_script("testing.py")
    pure_screen = extract_screen(pure_output)

    print("Running p3270 test...")
    p3270_output = run_script("testing copy.py")
    p3270_screen = extract_screen(p3270_output)

    print("\n" + "=" * 160)
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 160)
    print(f"{'PURE3270 (left)':79s} | {'P3270 (right)':79s}")
    print("-" * 160)

    max_lines = max(len(pure_screen), len(p3270_screen))
    differences = 0

    for i in range(max_lines):
        pure_line = pure_screen[i] if i < len(pure_screen) else ""
        p3270_line = p3270_screen[i] if i < len(p3270_screen) else ""

        # Truncate/pad to exactly 79 chars for clean display
        pure_line = pure_line[:79].ljust(79)
        p3270_line = p3270_line[:79].ljust(79)

        marker = "✓" if pure_line == p3270_line else "✗"
        if marker == "✗":
            differences += 1

        print(f"{pure_line} {marker} {p3270_line}")

    print("=" * 160)
    print(f"\nMatching lines: {max_lines - differences}/{max_lines}")
    print(f"Different lines: {differences}/{max_lines}")
    print(f"Match percentage: {100*(max_lines-differences)/max_lines:.1f}%")

    if differences == 0:
        print("\n🎉 PERFECT MATCH! Both implementations produce identical screens!")
        return 0
    else:
        print(f"\n⚠️  Found {differences} differences to investigate")
        return 1


if __name__ == "__main__":
    sys.exit(compare_screens())
