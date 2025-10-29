#!/usr/bin/env python3
# Diagnostic script: locate marker hex in a trace and show bulk decode vs per-byte mapping
# Usage: python scripts/diagnose_marker.py

import re
import sys
from pathlib import Path

TRACE = Path("tests/data/traces/smoke.trc")
MARKER_HEX = "e4e2c5d97a40"  # marker to search for (lowercase)


def load_trace(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def find_packets(lines):
    packets = []
    current = []
    hex_line_re = re.compile(r"<\s*0x[0-9a-fA-F]+\s+([0-9a-fA-F]+)")
    for ln in lines:
        m = hex_line_re.search(ln)
        if m:
            current.append(m.group(1))
        else:
            if current:
                packets.append("".join(current))
                current = []
    if current:
        packets.append("".join(current))
    return packets


def try_import_codec():
    try:
        from pure3270.emulation import ebcdic as _ebc

        # EBCDICCodec may be a class or module-level helpers.
        # prefer class if available
        Codec = getattr(_ebc, "EBCDICCodec", None)
        if Codec:
            codec = Codec()
        else:
            # fallback: module may expose decode function
            class _C:
                def decode(self, data: bytes):
                    # keep compatibility: return (decoded, length) or str
                    dec = (
                        _ebc.decode(data)
                        if hasattr(_ebc, "decode")
                        else data.decode("cp037", errors="replace")
                    )
                    return (dec, len(data)) if isinstance(dec, str) else dec

                @property
                def ebcdic_to_unicode_table(self):
                    return getattr(_ebc, "ebcdic_to_unicode_table", None)

            codec = _C()
        return codec
    except Exception:
        # minimal fallback using stdlib cp037
        class StdCodec:
            def decode(self, data: bytes):
                return (data.decode("cp037", errors="replace"), len(data))

            @property
            def ebcdic_to_unicode_table(self):
                # single-char decoding per byte using cp037
                table = []
                for b in range(256):
                    table.append(bytes([b]).decode("cp037", errors="replace"))
                return tuple(table)

        return StdCodec()


def printable_filter(s: str):
    return "".join(
        ch for ch in s if ch in ("\n", "\f", "\t") or 0x20 <= ord(ch) <= 0x7E
    )


def per_byte_map(table, data: bytes):
    if table is None:
        # fallback: decode single bytes with cp037
        return "".join(bytes([b]).decode("cp037", errors="replace") for b in data)
    return "".join(table[b] for b in data)


def diag_packet(idx, hexstr, codec):
    lower = hexstr.lower()
    print("=" * 80)
    print(f"Packet #{idx}: len(hex)={len(hexstr)} chars, len(bytes)={len(hexstr)//2}")
    # show whether marker present
    if MARKER_HEX not in lower:
        print("  marker not present in this packet")
        return
    print("  marker FOUND in packet hex")
    b = bytes.fromhex(lower)
    # find all occurrences
    marker_bytes = bytes.fromhex(MARKER_HEX)
    occ = []
    start = 0
    while True:
        i = lower.find(MARKER_HEX, start)
        if i == -1:
            break
        occ.append(i // 2)
        start = i + 1
    print(f"  marker byte offsets (in packet bytes): {occ}")

    # bulk decode
    decoded = None
    try:
        r = codec.decode(b)
        if isinstance(r, tuple):
            decoded = r[0]
        else:
            decoded = r
    except Exception as e:
        decoded = f"<bulk decode error: {e}>"
    print("\n-- Bulk decoded (first 400 chars) --")
    print(repr(decoded[:400]))

    # per-byte mapping
    table = getattr(codec, "ebcdic_to_unicode_table", None)
    try:
        pb = per_byte_map(table, b)
    except Exception as e:
        pb = f"<per-byte mapping error: {e}>"
    print("\n-- Per-byte mapped (first 400 chars) --")
    print(repr(pb[:400]))

    # safe decoded via printable filter on per-byte mapping
    safe_decoded = printable_filter(pb) if isinstance(pb, str) else "<non-string>"
    print("\n-- Safe decoded (filtered printable) --")
    print(repr(safe_decoded[:400]))

    # relaxed fallback from bulk decode (non-printable -> space)
    if isinstance(decoded, str):
        relaxed = "".join(
            ch if (ch in ("\n", "\f", "\t") or 0x20 <= ord(ch) <= 0x7E) else " "
            for ch in decoded
        )
    else:
        relaxed = "<no-bulk-decoded-string>"
    print("\n-- Relaxed fallback (from bulk decode) --")
    print(repr(relaxed[:400]))

    # show hex bytes around first occurence
    first = occ[0]
    start = max(0, first - 16)
    end = min(len(b), first + 32)
    print("\n-- Raw bytes around first marker (hex) --")
    print(b[start:end].hex())
    print("\n-- Bulk decoded around first marker (slice) --")
    if isinstance(decoded, str):
        print(repr(decoded[start:end]))
    else:
        print("<bulk decode not a string>")
    print("\n-- Per-byte mapped around first marker (slice) --")
    if isinstance(pb, str):
        print(repr(pb[start:end]))
    print("=" * 80)
    print()


def main():
    if not TRACE.exists():
        print(f"Trace file not found: {TRACE}", file=sys.stderr)
        sys.exit(2)
    lines = load_trace(TRACE)
    packets = find_packets(lines)
    print(f"Found {len(packets)} packets with hex blocks")
    codec = try_import_codec()
    found = 0
    for i, p in enumerate(packets):
        if MARKER_HEX in p.lower():
            found += 1
            diag_packet(i, p, codec)
    if found == 0:
        print("No packets containing the marker were located.")
    else:
        print(f"Diagnostics completed for {found} packet(s).")


if __name__ == "__main__":
    main()
