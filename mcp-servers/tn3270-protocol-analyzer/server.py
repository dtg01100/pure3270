#!/usr/bin/env python3
"""
TN3270 Protocol Analyzer MCP Server

This server provides tools for analyzing and debugging TN3270/TN3270E protocol flows,
including telnet negotiations, subnegotiations, and data stream parsing.
"""

import asyncio
import base64
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NegotiationEvent:
    """Represents a TN3270 negotiation event"""

    kind: str
    direction: str
    command: str
    option: str
    details: Dict[str, Any]
    timestamp: float


@dataclass
class SubnegotiationEvent:
    """Represents a TN3270 subnegotiation event"""

    kind: str
    option: str
    length: int
    preview: str
    details: Dict[str, Any]
    timestamp: float


@dataclass
class DataStreamEvent:
    """Represents a data stream parsing event"""

    kind: str
    data_type: str
    content: str
    details: Dict[str, Any]
    timestamp: float


class TN3270ProtocolAnalyzer:
    """Analyzer for TN3270 protocol flows"""

    def __init__(self):
        self.negotiation_events: List[NegotiationEvent] = []
        self.subnegotiation_events: List[SubnegotiationEvent] = []
        self.data_stream_events: List[DataStreamEvent] = []
        self.telnet_commands = {
            0xFF: "IAC",
            0xFB: "WILL",
            0xFC: "WONT",
            0xFD: "DO",
            0xFE: "DONT",
            0xF0: "SE",
            0xF1: "NOP",
            0xF2: "DM",
            0xF3: "BRK",
            0xF4: "IP",
            0xF5: "AO",
            0xF6: "AYT",
            0xF7: "EC",
            0xF8: "EL",
            0xF9: "GA",
            0xFA: "SB",
            0xFB: "WILL",
            0xFC: "WONT",
            0xFD: "DO",
            0xFE: "DONT",
        }

        self.telnet_options = {
            0x00: "BINARY",
            0x01: "ECHO",
            0x03: "SGA",
            0x05: "STATUS",
            0x06: "TIMING-MARK",
            0x08: "SEND-LOCATION",
            0x18: "TTYPE",
            0x19: "EOR",
            0x1C: "TUID",
            0x1D: "OUTMRK",
            0x1E: "TTYLOC",
            0x20: "3270REGIME",
            0x28: "TN3270E",
            0x2A: "X.3PAD",
            0x2B: "NAWS",
            0x2C: "TSPEED",
            0x2D: "LFLOW",
            0x2E: "LINEMODE",
            0x2F: "XDISPLOC",
            0x31: "OLD-ENVIRON",
            0x39: "AUTHENTICATION",
            0x3A: "ENCRYPT",
            0x3B: "NEW-ENVIRON",
            0x3C: "TN3270E-RESP-MODE",
            0x3D: "TN3270E-DS-HNDLR",
            0x3E: "TN3270E-ENVIRON",
            0x3F: "EXOPL",
        }

        self.tn3270e_functions = {
            0x01: "BIND-IMAGE",
            0x02: "DATA-STREAM-CTL",
            0x03: "RESPONSES",
            0x04: "SCS-CTL-CODES",
            0x05: "SYSREQ",
        }

    def analyze_negotiation_trace(self, trace_bytes: bytes) -> Dict[str, Any]:
        """Analyze a TN3270 negotiation trace and extract events"""
        events = []
        i = 0

        while i < len(trace_bytes):
            if trace_bytes[i] == 0xFF:  # IAC
                if i + 1 < len(trace_bytes):
                    command = trace_bytes[i + 1]
                    if command in [0xFB, 0xFC, 0xFD, 0xFE]:  # WILL, WONT, DO, DONT
                        if i + 2 < len(trace_bytes):
                            option = trace_bytes[i + 2]
                            cmd_name = self.telnet_commands.get(
                                command, f"0x{command:02X}"
                            )
                            opt_name = self.telnet_options.get(
                                option, f"0x{option:02X}"
                            )

                            event = NegotiationEvent(
                                kind="telnet",
                                direction="unknown",
                                command=cmd_name,
                                option=opt_name,
                                details={
                                    "command_code": command,
                                    "option_code": option,
                                },
                                timestamp=0.0,
                            )
                            self.negotiation_events.append(event)
                            events.append(asdict(event))
                            i += 3
                            continue
                    elif command == 0xFA:  # SB (Subnegotiation)
                        # Find the end of subnegotiation (IAC SE)
                        sb_start = i
                        j = i + 2
                        while j < len(trace_bytes) - 1:
                            if (
                                trace_bytes[j] == 0xFF and trace_bytes[j + 1] == 0xF0
                            ):  # IAC SE
                                option = trace_bytes[i + 1]
                                opt_name = self.telnet_options.get(
                                    option, f"0x{option:02X}"
                                )
                                sub_data = trace_bytes[i + 2 : j]

                                event = SubnegotiationEvent(
                                    kind="subneg",
                                    option=opt_name,
                                    length=len(sub_data),
                                    preview=sub_data.hex()[:32],
                                    details={
                                        "option_code": option,
                                        "raw_data": sub_data.hex(),
                                    },
                                    timestamp=0.0,
                                )
                                self.subnegotiation_events.append(event)
                                events.append(asdict(event))
                                i = j + 2
                                break
                            j += 1
                        else:
                            i += 1
                        continue
            i += 1

        return {
            "events": events,
            "summary": {
                "total_events": len(events),
                "telnet_events": len([e for e in events if e["kind"] == "telnet"]),
                "subnegotiation_events": len(
                    [e for e in events if e["kind"] == "subneg"]
                ),
            },
        }

    def decode_ebcdic_to_ascii(self, ebcdic_bytes: bytes) -> str:
        """Decode EBCDIC bytes to ASCII text"""
        try:
            # Use Python's built-in EBCDIC codec
            return ebcdic_bytes.decode("cp037")  # US-Canada variant
        except UnicodeDecodeError:
            # Fallback to basic mapping for common characters
            ebcdic_to_ascii_map = {
                0x40: " ",
                0x4B: ".",
                0x5B: "<",
                0x5C: "(",
                0x5D: "+",
                0x5E: "|",
                0x5F: "&",
                0x61: "!",
                0x6C: "$",
                0x6D: "*",
                0x6E: ")",
                0x6F: ";",
                0x79: ">",
                0x7A: "?",
                0x7B: ":",
                0x7C: "#",
                0x7D: "@",
                0x7E: "'",
                0x7F: "=",
                # Numbers
                0xF0: "0",
                0xF1: "1",
                0xF2: "2",
                0xF3: "3",
                0xF4: "4",
                0xF5: "5",
                0xF6: "6",
                0xF7: "7",
                0xF8: "8",
                0xF9: "9",
                # Uppercase letters
                0xC1: "A",
                0xC2: "B",
                0xC3: "C",
                0xC4: "D",
                0xC5: "E",
                0xC6: "F",
                0xC7: "G",
                0xC8: "H",
                0xC9: "I",
                0xD1: "J",
                0xD2: "K",
                0xD3: "L",
                0xD4: "M",
                0xD5: "N",
                0xD6: "O",
                0xD7: "P",
                0xD8: "Q",
                0xD9: "R",
                0xE2: "S",
                0xE3: "T",
                0xE4: "U",
                0xE5: "V",
                0xE6: "W",
                0xE7: "X",
                0xE8: "Y",
                0xE9: "Z",
            }

            result = []
            for byte in ebcdic_bytes:
                if byte in ebcdic_to_ascii_map:
                    result.append(ebcdic_to_ascii_map[byte])
                elif 0x81 <= byte <= 0x89:  # Lowercase a-i
                    result.append(chr(ord("a") + (byte - 0x81)))
                elif 0x91 <= byte <= 0x99:  # Lowercase j-r
                    result.append(chr(ord("j") + (byte - 0x91)))
                elif 0xA2 <= byte <= 0xA9:  # Lowercase s-z
                    result.append(chr(ord("s") + (byte - 0xA2)))
                else:
                    result.append("?")
            return "".join(result)

    def parse_data_stream(self, data: bytes) -> Dict[str, Any]:
        """Parse TN3270 data stream and identify orders and commands"""
        if not data:
            return {"orders": [], "summary": {"total_orders": 0}}

        orders = []
        i = 0

        # TN3270 orders
        orders_map = {
            0x05: "SET-ATTRIBUTE",
            0x11: "ERASE-UNPROTECTED",
            0x12: "READ-UNPROTECTED",
            0x13: "READ-UNPROTECTED-ALL",
            0x25: "SET-ATTRIBUTE",
            0x28: "OUTBOUND-3270-DATA",
            0x29: "START-OF-HEADER",
            0x2F: "TRANSFER-ASCII",
            0x40: "INSERT-CURSOR",
            0x41: "SBA",
            0x42: "EUA",
            0x45: "MCU",
            0x4D: "BI",
            0x4E: "NOP",
            0x51: "GE",
            0x5A: "ED",
            0x61: "SF",
            0x6C: "SA",
            0x78: "EA",
            0x79: "WCC",
            0x7B: "MDT",
            0x7E: "SFE",
            0x7F: "W",
            0xF1: "RA",
            0xF5: "EWA",
            0xF6: "EWR",
            0xF7: "EWF",
        }

        while i < len(data):
            byte = data[i]
            if byte in orders_map:
                order_name = orders_map[byte]
                order_info = {
                    "order": order_name,
                    "code": f"0x{byte:02X}",
                    "position": i,
                    "data": [],
                }

                # Some orders have parameters
                if byte in [0x41, 0x42]:  # SBA, EUA - take 2 parameter bytes
                    if i + 1 < len(data):
                        order_info["data"].append(data[i + 1])
                    if i + 2 < len(data):
                        order_info["data"].append(data[i + 2])
                    i += 3
                elif byte in [0x61, 0x6C]:  # SF, SA - take attribute byte
                    if i + 1 < len(data):
                        order_info["data"].append(data[i + 1])
                    i += 2
                else:
                    i += 1

                orders.append(order_info)
            else:
                # Regular character data
                char_info = {
                    "type": "character",
                    "position": i,
                    "byte": f"0x{byte:02X}",
                    "ascii": chr(byte) if 32 <= byte <= 126 else "?",
                    "ebcdic_decoded": self.decode_ebcdic_to_ascii(bytes([byte])),
                }
                orders.append(char_info)
                i += 1

        return {
            "orders": orders,
            "summary": {
                "total_orders": len(orders),
                "has_screen_data": any(o.get("type") == "character" for o in orders),
            },
        }

    def analyze_tn3270e_negotiation(self, negotiation_bytes: bytes) -> Dict[str, Any]:
        """Analyze TN3270E specific negotiation sequences"""
        analysis = {
            "tn3270e_supported": False,
            "device_types": [],
            "functions": [],
            "response_modes": [],
            "sequence": [],
        }

        i = 0
        while i < len(negotiation_bytes):
            if i + 1 < len(negotiation_bytes) and negotiation_bytes[i] == 0xFF:
                # IAC command
                command = negotiation_bytes[i + 1]
                if command == 0xFA and i + 2 < len(negotiation_bytes):  # SB
                    option = negotiation_bytes[i + 2]
                    if option == 0x28:  # TN3270E
                        analysis["tn3270e_supported"] = True
                        # Parse TN3270E subnegotiation
                        j = i + 3
                        while j < len(negotiation_bytes) - 1:
                            if (
                                negotiation_bytes[j] == 0xFF
                                and j + 1 < len(negotiation_bytes)
                                and negotiation_bytes[j + 1] == 0xF0
                            ):
                                break
                            j += 1
                        if j < len(negotiation_bytes):
                            sub_data = negotiation_bytes[i + 3 : j]
                            self._parse_tn3270e_subneg(sub_data, analysis)
                i += 1
            else:
                i += 1

        return analysis

    def _parse_tn3270e_subneg(self, sub_data: bytes, analysis: Dict[str, Any]) -> None:
        """Parse TN3270E subnegotiation data"""
        if not sub_data:
            return

        command = sub_data[0]

        if command == 0x01:  # DEVICE-TYPE
            analysis["sequence"].append("DEVICE-TYPE negotiation")
            if len(sub_data) > 1:
                device_type_bytes = sub_data[1:]
                # Look for null-terminated string
                null_pos = device_type_bytes.find(0x00)
                if null_pos != -1:
                    device_type = device_type_bytes[:null_pos].decode(
                        "ascii", errors="ignore"
                    )
                    analysis["device_types"].append(device_type)
                else:
                    device_type = device_type_bytes.decode("ascii", errors="ignore")
                    analysis["device_types"].append(device_type)

        elif command == 0x02:  # FUNCTIONS
            analysis["sequence"].append("FUNCTIONS negotiation")
            if len(sub_data) > 1:
                # Parse function bits
                for byte in sub_data[1:]:
                    for bit_pos in range(8):
                        if byte & (1 << bit_pos):
                            func_name = self.tn3270e_functions.get(
                                bit_pos + 1, f"UNKNOWN_FUNC_{bit_pos + 1}"
                            )
                            analysis["functions"].append(func_name)

        elif command == 0x03:  # RESPONSE-MODE
            analysis["sequence"].append("RESPONSE-MODE negotiation")
            analysis["response_modes"].append("BIND-IMAGE")


async def create_server() -> Server:
    """Create and configure the TN3270 Protocol Analyzer MCP server"""
    server = Server("tn3270-protocol-analyzer", "1.0.0")
    analyzer = TN3270ProtocolAnalyzer()

    # Tool implementations (no @server.tool decorator; register via list_tools/call_tool compatibility layer)
    async def analyze_negotiation_trace(trace_data: str) -> TextContent:
        """
        Analyze a TN3270 negotiation trace and extract events.

        Args:
            trace_data: Base64 encoded trace data as a string
        """
        try:
            trace_bytes = base64.b64decode(trace_data)
            result = analyzer.analyze_negotiation_trace(trace_bytes)
            return TextContent(type="text", text=json.dumps(result, indent=2))
        except Exception as e:
            return TextContent(type="text", text=f"Error analyzing trace: {str(e)}")

    async def decode_ebcdic(ebcdic_data: str) -> TextContent:
        """
        Decode EBCDIC bytes to ASCII text.

        Args:
            ebcdic_data: Base64 encoded EBCDIC data as a string
        """
        try:
            ebcdic_bytes = base64.b64decode(ebcdic_data)
            decoded = analyzer.decode_ebcdic_to_ascii(ebcdic_bytes)
            return TextContent(
                type="text",
                text=f"Decoded text: {decoded}\nHex: {ebcdic_bytes.hex()}\nOriginal bytes: {list(ebcdic_bytes)}",
            )
        except Exception as e:
            return TextContent(type="text", text=f"Error decoding EBCDIC: {str(e)}")

    async def parse_data_stream(data: str) -> TextContent:
        """
        Parse TN3270 data stream and identify orders and commands.

        Args:
            data: Base64 encoded data stream as a string
        """
        try:
            data_bytes = base64.b64decode(data)
            result = analyzer.parse_data_stream(data_bytes)
            return TextContent(type="text", text=json.dumps(result, indent=2))
        except Exception as e:
            return TextContent(type="text", text=f"Error parsing data stream: {str(e)}")

    async def analyze_tn3270e_negotiation(negotiation_data: str) -> TextContent:
        """
        Analyze TN3270E specific negotiation sequences.

        Args:
            negotiation_data: Base64 encoded negotiation data as a string
        """
        try:
            negotiation_bytes = base64.b64decode(negotiation_data)
            result = analyzer.analyze_tn3270e_negotiation(negotiation_bytes)
            return TextContent(type="text", text=json.dumps(result, indent=2))
        except Exception as e:
            return TextContent(
                type="text", text=f"Error analyzing TN3270E negotiation: {str(e)}"
            )

    async def get_protocol_constants() -> TextContent:
        """Get TN3270 protocol constants and mappings."""
        constants = {
            "telnet_commands": analyzer.telnet_commands,
            "telnet_options": analyzer.telnet_options,
            "tn3270e_functions": analyzer.tn3270e_functions,
            "tn3270_orders": {
                0x05: "SET-ATTRIBUTE",
                0x11: "ERASE-UNPROTECTED",
                0x12: "READ-UNPROTECTED",
                0x13: "READ-UNPROTECTED-ALL",
                0x25: "SET-ATTRIBUTE",
                0x28: "OUTBOUND-3270-DATA",
                0x29: "START-OF-HEADER",
                0x2F: "TRANSFER-ASCII",
                0x40: "INSERT-CURSOR",
                0x41: "SBA",
                0x42: "EUA",
                0x45: "MCU",
                0x4D: "BI",
                0x4E: "NOP",
                0x51: "GE",
                0x5A: "ED",
                0x61: "SF",
                0x6C: "SA",
                0x78: "EA",
                0x79: "WCC",
                0x7B: "MDT",
                0x7E: "SFE",
                0x7F: "W",
                0xF1: "RA",
                0xF5: "EWA",
                0xF6: "EWR",
                0xF7: "EWF",
            },
        }
        return TextContent(type="text", text=json.dumps(constants, indent=2))

    # Compatibility layer: advertise individual tools via list_tools and dispatch via call_tool
    _tool_map = {
        "analyze_negotiation_trace": analyze_negotiation_trace,
        "decode_ebcdic": decode_ebcdic,
        "parse_data_stream": parse_data_stream,
        "analyze_tn3270e_negotiation": analyze_tn3270e_negotiation,
        "get_protocol_constants": get_protocol_constants,
    }

    import mcp.types as types
    from mcp.types import ListToolsResult, Tool

    @server.list_tools()
    async def _list_tools(_: types.ListToolsRequest | None = None) -> ListToolsResult:
        tools = []
        for name in _tool_map.keys():
            tools.append(
                Tool(
                    name=name,
                    description=f"{name} (registered by tn3270-protocol-analyzer)",
                    inputSchema={},
                    outputSchema=None,
                )
            )
        # Return ListToolsResult so the server will cache tool definitions
        return types.ListToolsResult(tools=tools, total=len(tools))

    @server.call_tool()
    async def _dispatch_call_tool(name: str, arguments: dict | None):
        """
        Dispatch incoming tools/calls to the internal tool implementations.
        The internal functions return mcp.types.Result; convert to content blocks expected by call_tool.
        """
        func = _tool_map.get(name)
        if func is None:
            # Let the lowlevel handling produce a method not found error
            raise RuntimeError(f"Tool '{name}' not found")

        # Normalize argument to a single value (many tools expect a single base64 string)
        arg = None
        if isinstance(arguments, dict):
            # Prefer commonly named parameters, fallback to first value
            for k in ("trace_data", "ebcdic_data", "data", "negotiation_data"):
                if k in arguments:
                    arg = arguments[k]
                    break
            if arg is None and len(arguments) > 0:
                # pick first value
                arg = next(iter(arguments.values()))
        else:
            arg = arguments

        # Call the tool implementation
        if arg is None:
            result = await func()
        else:
            result = await func(arg)

        # The implementation returns TextContent objects directly
        # call_tool expects an iterable of content blocks
        return [result]

    return server


if __name__ == "__main__":
    import mcp.server.stdio as stdio_mod
    import mcp.types as types
    from mcp.server.models import InitializationOptions

    async def main() -> None:
        server = await create_server()
        async with stdio_mod.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="tn3270-protocol-analyzer",
                    server_version="1.0.0",
                    capabilities=types.ServerCapabilities(),
                ),
            )

    asyncio.run(main())
