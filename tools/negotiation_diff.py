#!/usr/bin/env python3
"""
Compare negotiation dump files produced by TraceReplayServer.

Usage:
    python tools/negotiation_diff.py --dir /tmp/pure3270_trace_dumps --trace smoke
    python tools/negotiation_diff.py --file-pure /tmp/.../smoke_*_send.hex --file-s3270 /tmp/.../smoke_*_send.hex

This tool loads hex-dump files (one hex string per line), converts to bytes,
then prints unified diffs of their hex representations for quick inspection.
"""

from __future__ import annotations

import argparse
import difflib
import os
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


def read_hex_dump(path: Path) -> bytes:
    data = bytearray()
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            # Remove non-hex whitespace
            hexstr = "".join(ln.split())
            try:
                data.extend(bytes.fromhex(hexstr))
            except Exception:
                # Try to strip non-hex characters
                filtered = "".join(c for c in hexstr if c in "0123456789abcdefABCDEF")
                if filtered:
                    try:
                        data.extend(bytes.fromhex(filtered))
                    except Exception:
                        pass
    return bytes(data)


def bytes_to_hex_lines(data: bytes, width: int = 16) -> List[str]:
    out = []
    for i in range(0, len(data), width):
        chunk = data[i : i + width]
        out.append(" ".join(f"{b:02x}" for b in chunk))
    return out


def find_dump_files(directory: Path, trace_stem: Optional[str] = None) -> List[Path]:
    files = list(directory.glob("*.hex"))
    if trace_stem:
        files = [p for p in files if trace_stem in p.name]
    return sorted(files)


def parse_dump_basename(p: Path) -> Tuple[str, Optional[int]]:
    """Parse file stem to extract timestamp (ms) and trace prefix.

    Expected format: <trace>_<host>_<port>_<timestamp>_<counter>_(send|recv)
    Returns: (prefix_without_timestamp_counter, timestamp_ms)
    """
    stem = p.stem
    parts = stem.split("_")
    if len(parts) >= 6:
        # prefix = parts[0] (trace stem)
        prefix = parts[0]
        try:
            ts = int(parts[-2])
        except Exception:
            ts = None
        return prefix, ts
    # Fallback: return full stem as prefix
    return stem, None


def pair_files(files: List[Path]) -> List[Tuple[Path, Path]]:
    # Pair send files by sorting them by timestamp and pairing sequentially
    send_files = [p for p in files if p.name.endswith("_send.hex")]
    # Group by trace prefix
    groups = {}
    for p in send_files:
        prefix, ts = parse_dump_basename(p)
        groups.setdefault(prefix, []).append((p, ts))

    pairs: List[Tuple[Path, Path]] = []
    for prefix, items in groups.items():
        # Sort items by timestamp if available, else by filename
        items_sorted = sorted(
            items, key=lambda pt: (pt[1] is None, pt[1] or 0, str(pt[0]))
        )
        # Pair sequentially
        for i in range(0, len(items_sorted) - 1, 2):
            a = items_sorted[i][0]
            b = items_sorted[i + 1][0]
            pairs.append((a, b))
    return pairs


def diff_hex_files(a: Path, b: Path) -> str:
    a_bytes = read_hex_dump(a)
    b_bytes = read_hex_dump(b)
    a_lines = bytes_to_hex_lines(a_bytes)
    b_lines = bytes_to_hex_lines(b_bytes)
    diff = difflib.unified_diff(
        a_lines, b_lines, fromfile=str(a), tofile=str(b), lineterm=""
    )
    return "\n".join(diff)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Compare negotiation hex dumps")
    ap.add_argument(
        "--dir",
        type=str,
        default=tempfile.gettempdir() + "/pure3270_trace_dumps",
        help="Directory with negotiation hex dumps",
    )  # nosec B108
    ap.add_argument("--trace", type=str, default=None, help="Filter by trace stem")
    ap.add_argument("--file-a", type=str, default=None)
    ap.add_argument("--file-b", type=str, default=None)
    ap.add_argument("--width", type=int, default=16)
    return ap.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    ns = parse_args(argv)
    d = Path(ns.dir)
    if not d.exists():
        print(f"Dump directory not found: {d}")
        return 2

    if ns.file_a and ns.file_b:
        a = Path(ns.file_a)
        b = Path(ns.file_b)
        if not a.exists() or not b.exists():
            print("File not found")
            return 2
        print(diff_hex_files(a, b))
        return 0

    files = find_dump_files(d, ns.trace)
    pairs = pair_files(files)
    if not pairs:
        print("No file pairs found to compare")
        # Print list of files for debugging
        for p in files:
            print(p)
        return 1

    for a, b in pairs:
        print(f"Comparing {a} <-> {b}")
        print(diff_hex_files(a, b))
        print("\n---\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
