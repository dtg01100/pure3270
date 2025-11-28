#!/usr/bin/env python3
import difflib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P1 = ROOT / "pure3270_script_results.json"
P2 = ROOT / "p3270_script_results.json"
OUT = ROOT / "drop_in_char_diff.txt"


def get_step_content(data, step):
    for s in data.get("screenshots", []):
        if s.get("step") == step:
            return s.get("content", "")
    return ""


def main():
    a = json.loads(open(P1).read())
    b = json.loads(open(P2).read())

    lines = []
    lines.append("Character-level diff report")
    lines.append("=========================")

    # Final screen diff
    fa = a.get("final_screen", "")
    fb = b.get("final_screen", "")
    lines.append("\n--- FINAL SCREEN DIFF ---\n")
    da = fa.splitlines(keepends=True)
    db = fb.splitlines(keepends=True)
    diff = difflib.unified_diff(da, db, fromfile="pure3270_final", tofile="p3270_final")
    lines.extend(diff)

    # Step 11 diff
    sa = get_step_content(a, 11).splitlines(keepends=True)
    sb = get_step_content(b, 11).splitlines(keepends=True)
    lines.append("\n--- STEP 11 (get_screen) DIFF ---\n")
    diff2 = difflib.unified_diff(
        sa, sb, fromfile="pure3270_step11", tofile="p3270_step11"
    )
    lines.extend(diff2)

    OUT.write_text("\n".join(lines))
    print(f"Wrote character diff to {OUT}")


if __name__ == "__main__":
    main()
