#!/usr/bin/env python3
"""
TN3270 Packet Analyzer Utility

A debugging tool for analyzing TN3270 and TN3270E protocol packets.
Provides human-readable output for protocol debugging and development.

Usage:
    python tn3270_packet_analyzer.py <hex_data>
    python tn3270_packet_analyzer.py --file <trace_file>
    python tn3270_packet_analyzer.py --interactive
"""

import argparse
import sys
from typing import Dict, List, Optional

# Import pure3270 components
try:
    from pure3270.protocol.tn3270e_header import TN3270EHeader
    from pure3270.protocol.utils import (
        DO,
        DONT,
        IAC,
        SB,
        SE,
        TELOPT_BINARY,
        TELOPT_ECHO,
        TELOPT_TN3270E,
        WILL,
        WONT,
    )
except ImportError:
    print("Error: pure3270 package not found. Please install it first.")
    sys.exit(1)


class TN3270PacketAnalyzer:
    """TN3270 protocol packet analyzer."""

    def __init__(self):
        pass

    def analyze_packet(self, data: bytes) -> Dict:
        """Analyze a TN3270 packet and return structured information."""
        result = {
            "raw_hex": data.hex(),
            "length": len(data),
            "telnet_commands": [],
            "tn3270e_headers": [],
            "data_segments": [],
            "analysis": [],
        }

        pos = 0
        while pos < len(data):
            # Check for Telnet IAC sequences
            if data[pos] == IAC:
                if pos + 1 < len(data):
                    cmd_info = self._analyze_telnet_command(data, pos)
                    result["telnet_commands"].append(cmd_info)
                    pos += cmd_info["length"]
                    continue

            # Check for TN3270E headers (5 bytes starting with data type)
            if pos + 4 < len(data):
                header_info = self._analyze_tn3270e_header(data[pos : pos + 5])
                if header_info:
                    result["tn3270e_headers"].append({**header_info, "offset": pos})
                    pos += 5
                    continue

            # Regular data
            data_end = self._find_next_control_sequence(data, pos)
            if data_end > pos:
                result["data_segments"].append(
                    {
                        "offset": pos,
                        "length": data_end - pos,
                        "data": data[pos:data_end],
                    }
                )
                pos = data_end
            else:
                pos += 1

        result["analysis"] = self._generate_analysis(result)
        return result

    def _analyze_telnet_command(self, data: bytes, pos: int) -> Dict:
        """Analyze a Telnet command sequence."""
        if pos + 1 >= len(data):
            return {"type": "incomplete", "length": 1}

        cmd = data[pos + 1]
        length = 2

        # Handle subnegotiation
        if cmd == SB:
            end_pos = data.find(SE, pos + 2)
            if end_pos != -1:
                length = end_pos - pos + 1
                return {
                    "type": "subnegotiation",
                    "command": "SB",
                    "option": data[pos + 2] if pos + 2 < len(data) else "unknown",
                    "data": data[pos + 3 : end_pos].hex() if end_pos > pos + 3 else "",
                    "length": length,
                }

        # Handle option negotiation
        cmd_names = {WILL: "WILL", WONT: "WONT", DO: "DO", DONT: "DONT"}

        if cmd in cmd_names:
            option = data[pos + 2] if pos + 2 < len(data) else "unknown"
            length = 3
            return {
                "type": "option_negotiation",
                "command": cmd_names[cmd],
                "option": option,
                "option_name": self._get_option_name(option),
                "length": length,
            }

        return {"type": "command", "command": f"0x{cmd:02x}", "length": length}

    def _analyze_tn3270e_header(self, header_bytes: bytes) -> Optional[Dict]:
        """Analyze TN3270E header bytes."""
        if len(header_bytes) != 5:
            return None

        try:
            header = TN3270EHeader.from_bytes(header_bytes)
            if header:
                return {
                    "data_type": header.get_data_type_name(),
                    "request_flag": f"0x{header.request_flag:02x}",
                    "response_flag": header.get_response_flag_name(),
                    "sequence_number": header.seq_number,
                    "raw_bytes": header_bytes.hex(),
                }
        except Exception:
            pass
        return None

    def _find_next_control_sequence(self, data: bytes, start: int) -> int:
        """Find the next control sequence in the data."""
        for i in range(start, len(data)):
            if data[i] == IAC:
                return i
        return len(data)

    def _get_option_name(self, option) -> str:
        """Get human-readable name for Telnet option."""
        if not isinstance(option, int):
            return str(option)

        options = {
            TELOPT_BINARY: "BINARY",
            TELOPT_ECHO: "ECHO",
            TELOPT_TN3270E: "TN3270E",
        }
        return options.get(option, f"0x{option:02x}")

    def _generate_analysis(self, result: Dict) -> List[str]:
        """Generate analysis insights."""
        analysis = []

        if result["tn3270e_headers"]:
            analysis.append(f"Found {len(result['tn3270e_headers'])} TN3270E header(s)")
            seq_nums = [h["sequence_number"] for h in result["tn3270e_headers"]]
            if len(seq_nums) > 1:
                if seq_nums == list(range(min(seq_nums), max(seq_nums) + 1)):
                    analysis.append("Sequence numbers are consecutive")
                else:
                    analysis.append("Sequence numbers have gaps")

        if result["telnet_commands"]:
            analysis.append(f"Found {len(result['telnet_commands'])} Telnet command(s)")

        if result["data_segments"]:
            total_data = sum(s["length"] for s in result["data_segments"])
            analysis.append(
                f"Found {total_data} bytes of data in {len(result['data_segments'])} segment(s)"
            )

        return analysis

    def display_analysis(self, result: Dict):
        """Display the analysis results in a human-readable format."""
        self._display_plain(result)

    def _display_plain(self, result: Dict):
        """Display results in plain text."""
        print("TN3270 Packet Analysis")
        print(f"Length: {result['length']} bytes")
        print(
            f"Raw: {result['raw_hex'][:100]}{'...' if len(result['raw_hex']) > 100 else ''}"
        )
        print()

        if result["telnet_commands"]:
            print("Telnet Commands:")
            for cmd in result["telnet_commands"]:
                print(f"  {cmd}")

        if result["tn3270e_headers"]:
            print("TN3270E Headers:")
            for header in result["tn3270e_headers"]:
                print(f"  {header}")

        if result["analysis"]:
            print("Analysis:")
            for insight in result["analysis"]:
                print(f"  • {insight}")


def main():
    parser = argparse.ArgumentParser(description="TN3270 Packet Analyzer")
    parser.add_argument("data", nargs="?", help="Hex data to analyze")
    parser.add_argument("--file", "-f", help="Read data from file")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive mode"
    )

    args = parser.parse_args()

    analyzer = TN3270PacketAnalyzer()

    if args.interactive:
        print("TN3270 Packet Analyzer - Interactive Mode")
        print("Enter hex data (or 'quit' to exit):")
        while True:
            try:
                data = input("> ").strip()
                if data.lower() in ("quit", "exit"):
                    break
                if data:
                    packet_data = bytes.fromhex(data)
                    result = analyzer.analyze_packet(packet_data)
                    analyzer.display_analysis(result)
                    print()
            except ValueError as e:
                print(f"Invalid hex data: {e}")
            except KeyboardInterrupt:
                break

    elif args.file:
        try:
            with open(args.file, "rb") as f:
                data = f.read()
            result = analyzer.analyze_packet(data)
            analyzer.display_analysis(result)
        except FileNotFoundError:
            print(f"File not found: {args.file}")
            sys.exit(1)

    elif args.data:
        try:
            packet_data = bytes.fromhex(args.data)
            result = analyzer.analyze_packet(packet_data)
            analyzer.display_analysis(result)
        except ValueError as e:
            print(f"Invalid hex data: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
