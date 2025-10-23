#!/usr/bin/env python3
"""
Simple demonstration: How pure3270 and s3270 would handle the same data stream.

This parses an s3270 trace file and shows what commands/orders are being sent,
then compares with how pure3270 would interpret them.
"""

import re

# Import pure3270's protocol constants
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, "/workspaces/pure3270")

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser


class S3270TraceAnalyzer:
    """Analyze s3270 trace files and show what they do."""

    def __init__(self, trace_file: str):
        self.trace_file = Path(trace_file)

    def parse_and_analyze(self) -> Dict[str, Any]:
        """Parse trace file and analyze the data stream."""
        results = {"telnet_events": [], "data_stream_events": [], "raw_data": []}

        with open(self.trace_file, "r") as f:
            for line in f:
                line = line.strip()

                # Skip comments
                if not line or line.startswith("//"):
                    continue

                # Parse output lines (data sent from client/s3270)
                if line.startswith("<"):
                    match = re.match(r"<\s+0x\w+\s+([0-9a-fA-F]+)", line)
                    if match:
                        hex_data = match.group(1)
                        data = bytes.fromhex(hex_data)

                        # Analyze what this data contains
                        analysis = self._analyze_data(data)

                        results["raw_data"].append(
                            {
                                "direction": "send",
                                "hex": hex_data,
                                "bytes": data,
                                "analysis": analysis,
                            }
                        )

        return results

    def _analyze_data(self, data: bytes) -> Dict[str, Any]:
        """Analyze what a data packet contains."""
        result = {"type": "unknown", "details": []}

        # Check for Telnet IAC sequences
        if data and data[0] == 0xFF:
            result["type"] = "telnet"
            result["details"] = self._parse_telnet(data)
            return result

        # Check for TN3270E header
        if len(data) >= 5 and data[0] in [0x00, 0x01, 0x02, 0x03, 0x04, 0x05]:
            result["type"] = "tn3270e"
            result["details"] = self._parse_tn3270e(data)
            return result

        # Check for 3270 data stream
        if data and data[0] in [0x01, 0x02, 0x05, 0x7E, 0xF1, 0xF5]:
            result["type"] = "3270_data_stream"
            result["details"] = self._parse_3270_stream(data)
            return result

        result["details"] = [f"Unknown data: {data.hex()}"]
        return result

    def _parse_telnet(self, data: bytes) -> List[str]:
        """Parse Telnet IAC sequences."""
        details = []
        i = 0
        while i < len(data):
            if data[i] == 0xFF and i + 1 < len(data):
                cmd = data[i + 1]
                cmd_names = {
                    0xFB: "WILL",
                    0xFC: "WONT",
                    0xFD: "DO",
                    0xFE: "DONT",
                    0xFA: "SB",
                    0xF0: "SE",
                    0xEF: "EOR",
                }
                cmd_name = cmd_names.get(cmd, f"0x{cmd:02x}")

                if cmd in [0xFB, 0xFC, 0xFD, 0xFE] and i + 2 < len(data):
                    option = data[i + 2]
                    option_names = {
                        0x18: "TERMINAL-TYPE",
                        0x19: "EOR",
                        0x28: "TN3270E",
                        0x27: "NEW-ENVIRON",
                    }
                    opt_name = option_names.get(option, f"0x{option:02x}")
                    details.append(f"IAC {cmd_name} {opt_name}")
                    i += 3
                else:
                    details.append(f"IAC {cmd_name}")
                    i += 2
            else:
                i += 1
        return details

    def _parse_tn3270e(self, data: bytes) -> List[str]:
        """Parse TN3270E header and data."""
        details = []
        if len(data) >= 5:
            data_type = data[0]
            request_flag = data[1]
            response_flag = data[2]
            seq_number = (data[3] << 8) | data[4]

            type_names = {
                0x00: "3270-DATA",
                0x01: "SCS-DATA",
                0x02: "RESPONSE",
                0x03: "BIND-IMAGE",
                0x04: "UNBIND",
                0x05: "NVT-DATA",
                0x06: "REQUEST",
                0x07: "SSCP-LU-DATA",
            }

            details.append(
                f"TN3270E Header: {type_names.get(data_type, f'0x{data_type:02x}')}"
            )
            details.append(
                f"  Seq: {seq_number}, Req: 0x{request_flag:02x}, Rsp: 0x{response_flag:02x}"
            )

            # Parse the 3270 data stream after header
            if len(data) > 5:
                stream_details = self._parse_3270_stream(data[5:])
                details.extend(["  " + d for d in stream_details])

        return details

    def _parse_3270_stream(self, data: bytes) -> List[str]:
        """Parse 3270 data stream commands and orders."""
        details = []
        i = 0

        while i < len(data):
            byte = data[i]

            # Check for commands
            if byte == 0x01:
                details.append("Command: WRITE")
                i += 1
                if i < len(data):
                    wcc = data[i]
                    details.append(f"  WCC: 0x{wcc:02x}")
                    i += 1
                continue

            elif byte == 0x05:
                details.append("Command: EW (Erase/Write)")
                i += 1
                if i < len(data):
                    wcc = data[i]
                    details.append(f"  WCC: 0x{wcc:02x}")
                    i += 1
                continue

            elif byte == 0x7E:
                details.append("Command: EWA (Erase/Write Alternate)")
                i += 1
                if i < len(data):
                    wcc = data[i]
                    details.append(f"  WCC: 0x{wcc:02x}")
                    i += 1
                continue

            # Check for orders
            elif byte == 0x11:  # SBA
                details.append("Order: SBA (Set Buffer Address)")
                if i + 2 < len(data):
                    addr_hi = data[i + 1]
                    addr_low = data[i + 2]
                    # Decode 12-bit address
                    address = ((addr_hi & 0x3F) << 6) | (addr_low & 0x3F)
                    row = address // 80
                    col = address % 80
                    details.append(f"  Address: {address} (row={row}, col={col})")
                    i += 3
                else:
                    i += 1
                continue

            elif byte == 0x3C:  # RA
                details.append("Order: RA (Repeat to Address)")
                if i + 3 < len(data):
                    addr_hi = data[i + 1]
                    addr_low = data[i + 2]
                    char = data[i + 3]
                    address = ((addr_hi & 0x3F) << 6) | (addr_low & 0x3F)
                    row = address // 80
                    col = address % 80
                    details.append(
                        f"  To: {address} (row={row}, col={col}), Char: 0x{char:02x}"
                    )
                    i += 4
                else:
                    i += 1
                continue

            elif byte == 0x1D:  # SF
                details.append("Order: SF (Start Field)")
                if i + 1 < len(data):
                    attr = data[i + 1]
                    details.append(f"  Attribute: 0x{attr:02x}")
                    i += 2
                else:
                    i += 1
                continue

            elif byte == 0x13:  # IC
                details.append("Order: IC (Insert Cursor)")
                i += 1
                continue

            elif byte == 0x29:  # SFE
                details.append("Order: SFE (Start Field Extended)")
                i += 1
                # SFE has count byte
                if i < len(data):
                    count = data[i]
                    details.append(f"  Pairs: {count}")
                    i += 1 + (count * 2)  # Skip attribute pairs
                continue

            # Otherwise it's data
            else:
                # Find run of data bytes (not orders)
                start = i
                while i < len(data) and data[i] not in [
                    0x01,
                    0x05,
                    0x7E,
                    0x11,
                    0x1D,
                    0x13,
                    0x29,
                    0x3C,
                ]:
                    i += 1
                if i > start:
                    data_bytes = data[start:i]
                    preview = " ".join(f"{b:02x}" for b in data_bytes[:8])
                    if len(data_bytes) > 8:
                        preview += "..."
                    details.append(f"Data ({len(data_bytes)} bytes): {preview}")
                continue

        return details


def main():
    """Demonstrate trace analysis."""

    trace_file = "/workspaces/pure3270/tests/data/traces/ra_test.trc"

    print("=" * 80)
    print(f"S3270 TRACE ANALYSIS: {Path(trace_file).name}")
    print("=" * 80)

    analyzer = S3270TraceAnalyzer(trace_file)
    results = analyzer.parse_and_analyze()

    print(f"\nFound {len(results['raw_data'])} data packets\n")

    for i, packet in enumerate(results["raw_data"], 1):
        print(f"\nPacket #{i} ({packet['direction']}):")
        print(f"  Hex: {packet['hex'][:60]}{'...' if len(packet['hex']) > 60 else ''}")
        print(f"  Type: {packet['analysis']['type']}")
        print(f"  Details:")
        for detail in packet["analysis"]["details"]:
            print(f"    {detail}")

    print("\n" + "=" * 80)
    print("KEY OBSERVATIONS:")
    print("=" * 80)
    print("1. s3270 trace shows EXACTLY what bytes are sent/received")
    print("2. TN3270E header format: data_type | request | response | seq_hi | seq_low")
    print("3. RA order format: 0x3C | addr_hi | addr_low | char_to_repeat")
    print("4. This is the ground truth we fixed pure3270 to match!")
    print("=" * 80)


if __name__ == "__main__":
    main()
