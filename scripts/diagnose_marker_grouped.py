#!/usr/bin/env python3
# Diagnose marker presence using the same grouping logic as the test replay loop.
import re
from pathlib import Path

TRACE = Path("tests/data/traces/smoke.trc")
MARKER_HEX = "e4e2c5d97a40"


def main():
    lines = TRACE.read_text(encoding="utf-8", errors="ignore").splitlines()
    current_packet = b""
    packets = []
    for line in lines:
        ln = line.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith(("<", ">")) and len(ln.split()) >= 3:
            parts = ln.split(maxsplit=2)
            direction = parts[0]
            offset_str = parts[1]
            hex_payload = parts[2]
            try:
                offset = int(offset_str, 16)
            except Exception:
                continue
            if direction == "<":
                if offset == 0 and current_packet:
                    packets.append(current_packet)
                    current_packet = b""
                try:
                    data = bytes.fromhex(hex_payload)
                    current_packet += data
                except Exception:
                    continue
        else:
            if current_packet:
                packets.append(current_packet)
                current_packet = b""
    if current_packet:
        packets.append(current_packet)

    found = 0
    for idx, p in enumerate(packets):
        hx = p.hex()
        if MARKER_HEX in hx:
            print(f"Grouped packet #{idx} contains marker (bytes={len(p)})")
            pos = hx.find(MARKER_HEX)
            print(
                "  hex around marker:",
                hx[max(0, pos - 64) : pos + len(MARKER_HEX) + 64],
            )
            print("  marker byte offset:", pos // 2)
            found += 1
    print("Total grouped packets:", len(packets))
    print("Found in grouped packets:", found)


if __name__ == "__main__":
    main()
