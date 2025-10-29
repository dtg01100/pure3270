#!/usr/bin/env python3
# Replay smoke.trc using DataStreamParser and PrinterBuffer, then dump buffer lines.
from pathlib import Path

from pure3270.emulation.printer_buffer import PrinterBuffer
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.tn3270e_header import TN3270EHeader
from pure3270.protocol.utils import SCS_DATA

TRACE = Path("tests/data/traces/smoke.trc")


def replay_and_dump():
    printer_buffer = PrinterBuffer()
    parser = DataStreamParser(None, printer_buffer=printer_buffer)

    with TRACE.open("r", encoding="utf-8", errors="ignore") as f:
        current_packet = b""
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(("<", ">")) and len(line.split()) >= 3:
                parts = line.split(maxsplit=2)
                direction = parts[0]
                offset_str = parts[1]
                hex_payload = parts[2]
                try:
                    offset = int(offset_str, 16)
                except Exception:
                    continue
                if direction == "<":
                    if offset == 0 and current_packet:
                        # process packet
                        data_type = SCS_DATA
                        payload = current_packet
                        if len(current_packet) >= 5:
                            header = TN3270EHeader.from_bytes(current_packet[:5])
                            if header:
                                data_type = header.data_type
                                payload = current_packet[5:]
                        try:
                            parser.parse(payload, data_type=data_type)
                        except Exception:
                            pass
                        current_packet = b""
                    try:
                        data = bytes.fromhex(hex_payload)
                        current_packet += data
                    except Exception:
                        continue
            else:
                if current_packet:
                    data_type = SCS_DATA
                    payload = current_packet
                    if len(current_packet) >= 5:
                        header = TN3270EHeader.from_bytes(current_packet[:5])
                        if header:
                            data_type = header.data_type
                            payload = current_packet[5:]
                    try:
                        parser.parse(payload, data_type=data_type)
                    except Exception:
                        pass
                    current_packet = b""
        if current_packet:
            data_type = SCS_DATA
            payload = current_packet
            if len(current_packet) >= 5:
                header = TN3270EHeader.from_bytes(current_packet[:5])
                if header:
                    data_type = header.data_type
                    payload = current_packet[5:]
            try:
                parser.parse(payload, data_type=data_type)
            except Exception:
                pass

    # Dump buffer content
    lines = printer_buffer.get_buffer_content()
    print(f"Total lines: {len(lines)}")
    for idx, ln in enumerate(lines):
        print(f"{idx:04d}: {repr(ln)}")


if __name__ == "__main__":
    replay_and_dump()
