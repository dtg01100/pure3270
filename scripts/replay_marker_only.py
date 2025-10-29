#!/usr/bin/env python3
# Replay only packets containing the known marker and show PrinterBuffer state after each.
import re
from pathlib import Path

from pure3270.emulation.printer_buffer import PrinterBuffer
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.tn3270e_header import TN3270EHeader
from pure3270.protocol.utils import SCS_DATA

TRACE = Path("tests/data/traces/smoke.trc")
MARKER_HEX = "e4e2c5d97a40"


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


def main():
    lines = TRACE.read_text(encoding="utf-8", errors="ignore").splitlines()
    packets = find_packets(lines)
    print(f"Found {len(packets)} packets; scanning for marker...")
    marker_packets = [i for i, p in enumerate(packets) if MARKER_HEX in p.lower()]
    print("Marker found in packet indices:", marker_packets)

    printer_buffer = PrinterBuffer()
    # Provide a minimal ScreenBuffer for the parser to avoid None checks when
    # the parse path exercises TN3270/TN3270E handling. Use default dimensions.
    from pure3270.emulation.screen_buffer import ScreenBuffer

    screen = ScreenBuffer()
    parser = DataStreamParser(screen, printer_buffer=printer_buffer)

    for idx in marker_packets:
        hexstr = packets[idx]
        b = bytes.fromhex(hexstr)
        print(f"--- Processing packet {idx} (bytes={len(b)}) ---")
        # emulate header parsing like replay
        data_type = SCS_DATA
        payload = b
        if len(b) >= 5:
            header = TN3270EHeader.from_bytes(b[:5])
            if header:
                data_type = header.data_type
                payload = b[5:]
        try:
            # Direct diagnostic path: bypass the full DataStreamParser and feed the
            # raw payload directly into the PrinterBuffer.write_scs_data method so
            # we can observe the instrumentation added there. This helps confirm
            # whether the decoded marker survives the printer path independent of
            # screen parsing semantics.
            printer_buffer.write_scs_data(payload)
        except Exception as e:
            print("printer.write_scs_data exception:", e)
        # dump buffer content after processing this packet
        lines = printer_buffer.get_buffer_content()
        print(f"Buffer lines after packet {idx}: total={len(lines)}")
        for li, ln in enumerate(lines[-10:]):  # show last 10 lines
            print(f"{li:02d}: {repr(ln)[:300]}")
        print()


if __name__ == "__main__":
    main()
