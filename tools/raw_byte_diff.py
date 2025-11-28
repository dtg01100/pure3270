#!/usr/bin/env python3
import base64
import binascii
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P1 = ROOT / "pure3270_script_results.json"
P2 = ROOT / "p3270_script_results.json"
OUT = ROOT / "drop_in_raw_byte_diff.txt"

steps_to_check = [9, 11]


def find_raw_for_step(data, step):
    for s in data.get("screenshots", []):
        if s.get("step") == step:
            return s.get("raw_base64")
    return None


def hexdump(b: bytes, width=16):
    lines = []
    for i in range(0, len(b), width):
        chunk = b[i : i + width]
        hexbytes = " ".join(f"{x:02x}" for x in chunk)
        text = "".join((chr(x) if 32 <= x <= 126 else ".") for x in chunk)
        lines.append(f"{i:08x}  {hexbytes:<{width*3}}  |{text}|")
    return "\n".join(lines)


def compare_bytes(b1: bytes, b2: bytes):
    if b1 == b2:
        return True, "identical", None
    # find first diff
    n = min(len(b1), len(b2))
    i = 0
    while i < n and b1[i] == b2[i]:
        i += 1
    # find last common suffix
    j1 = len(b1) - 1
    j2 = len(b2) - 1
    suffix = 0
    while j1 >= 0 and j2 >= 0 and b1[j1] == b2[j2] and (j1 > i and j2 > i):
        j1 -= 1
        j2 -= 1
        suffix += 1
    return False, (i, suffix), (b1, b2)


def main():
    a = json.loads(open(P1).read())
    b = json.loads(open(P2).read())
    report_lines = []
    report_lines.append("Raw byte-level comparison report")
    report_lines.append("=\n")
    for step in steps_to_check:
        report_lines.append(f"\nSTEP {step}:")
        r1 = find_raw_for_step(a, step)
        r2 = find_raw_for_step(b, step)
        if not r1:
            report_lines.append("  - pure3270: raw bytes not captured")
        if not r2:
            report_lines.append("  - p3270: raw bytes not captured")
        if not r1 or not r2:
            continue
        try:
            ba = base64.b64decode(r1)
            bb = base64.b64decode(r2)
        except Exception as e:
            report_lines.append(f"  - failed to decode base64: {e}")
            continue
        report_lines.append(f"  - pure3270 raw length: {len(ba)} bytes")
        report_lines.append(f"  - p3270 raw length: {len(bb)} bytes")
        same, info, _ = compare_bytes(ba, bb)
        if same:
            report_lines.append("  - raw bytes IDENTICAL")
        else:
            first_diff, suffix = info
            report_lines.append(
                f"  - raw bytes DIFFER (first differing offset: {first_diff}, common-suffix-bytes: {suffix})"
            )
            # add small hexdump windows around first diff
            start = max(0, first_diff - 32)
            end = min(max(len(ba), len(bb)), first_diff + 128)
            report_lines.append("\n  --- pure3270 hexdump window ---")
            report_lines.append(hexdump(ba[start:end]))
            report_lines.append("\n  --- p3270 hexdump window ---")
            report_lines.append(hexdump(bb[start:end]))
            # write full hexdumps to files
            (ROOT / f"pure3270_step{step}_raw_hexdump.txt").write_text(hexdump(ba))
            (ROOT / f"p3270_step{step}_raw_hexdump.txt").write_text(hexdump(bb))
            report_lines.append(
                f"\n  Full hexdumps written to: pure3270_step{step}_raw_hexdump.txt, p3270_step{step}_raw_hexdump.txt"
            )
    OUT.write_text("\n".join(report_lines))
    print(f"Wrote byte-diff report to {OUT}")


if __name__ == "__main__":
    main()
