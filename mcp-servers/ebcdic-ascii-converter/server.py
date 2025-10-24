#!/usr/bin/env python3
"""
EBCDIC/ASCII Converter MCP Server

This server provides tools for converting between EBCDIC and ASCII encodings,
which is essential for working with mainframe systems and 3270 terminal emulation.
"""

import asyncio
import base64
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from mcp.server import Server
from mcp.types import TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of an EBCDIC/ASCII conversion"""

    original_data: str
    converted_data: str
    conversion_type: str
    encoding_details: Dict[str, Any]


class EBCDICASCIIConverter:
    """Converter for EBCDIC/ASCII encoding operations"""

    def __init__(self):
        # EBCDIC to ASCII conversion table (US-Canada variant - CP037)
        self.ebcdic_to_ascii = {
            0x00: "\x00",
            0x01: "\x01",
            0x02: "\x02",
            0x03: "\x03",
            0x37: "\x04",
            0x2D: "\x05",
            0x2E: "\x06",
            0x2F: "\x07",
            0x16: "\x08",
            0x05: "\t",
            0x15: "\n",
            0x0B: "\x0b",
            0x0C: "\x0c",
            0x0D: "\r",
            0x0E: "\x0e",
            0x0F: "\x0f",
            0x10: "\x10",
            0x11: "\x11",
            0x12: "\x12",
            0x13: "\x13",
            0x3C: "\x14",
            0x3D: "\x15",
            0x32: "\x16",
            0x26: "\x17",
            0x18: "\x18",
            0x19: "\x19",
            0x3F: "\x1a",
            0x27: "\x1b",
            0x1C: "\x1c",
            0x1D: "\x1d",
            0x1E: "\x1e",
            0x1F: "\x1f",
            0x40: " ",
            0x5A: "\x21",
            0x7F: '"',
            0x7B: "#",
            0x5B: "$",
            0x6C: "%",
            0x50: "&",
            0x7D: "'",
            0x4D: "(",
            0x5D: ")",
            0x5C: "*",
            0x4E: "+",
            0x6B: ",",
            0x60: "-",
            0x4B: ".",
            0x61: "/",
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
            0x7A: ":",
            0x5E: ";",
            0x4C: "<",
            0x7E: "=",
            0x6E: ">",
            0x6F: "?",
            0x7C: "@",
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
            0x4A: "[",
            0xE0: "\\",
            0x5A: "]",
            0x5F: "^",
            0x6D: "_",
            0x79: "`",
            0x81: "a",
            0x82: "b",
            0x83: "c",
            0x84: "d",
            0x85: "e",
            0x86: "f",
            0x87: "g",
            0x88: "h",
            0x89: "i",
            0x91: "j",
            0x92: "k",
            0x93: "l",
            0x94: "m",
            0x95: "n",
            0x96: "o",
            0x97: "p",
            0x98: "q",
            0x99: "r",
            0xA2: "s",
            0xA3: "t",
            0xA4: "u",
            0xA5: "v",
            0xA6: "w",
            0xA7: "x",
            0xA8: "y",
            0xA9: "z",
            0x4A: "{",
            0xE0: "|",
            0x5A: "}",
            0x5F: "~",
            0xFF: "\x7f",
        }

        # ASCII to EBCDIC conversion table (reverse of above)
        self.ascii_to_ebcdic = {v: k for k, v in self.ebcdic_to_ascii.items()}

        # Extended EBCDIC table for more characters
        self.extended_ebcdic = {
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
            # Lowercase letters
            0x81: "a",
            0x82: "b",
            0x83: "c",
            0x84: "d",
            0x85: "e",
            0x86: "f",
            0x87: "g",
            0x88: "h",
            0x89: "i",
            0x91: "j",
            0x92: "k",
            0x93: "l",
            0x94: "m",
            0x95: "n",
            0x96: "o",
            0x97: "p",
            0x98: "q",
            0x99: "r",
            0xA2: "s",
            0xA3: "t",
            0xA4: "u",
            0xA5: "v",
            0xA6: "w",
            0xA7: "x",
            0xA8: "y",
            0xA9: "z",
        }

    def ebcdic_to_ascii_str(self, ebcdic_bytes: bytes) -> str:
        """Convert EBCDIC bytes to ASCII string"""
        result = []
        for byte in ebcdic_bytes:
            if byte in self.ebcdic_to_ascii:
                result.append(self.ebcdic_to_ascii[byte])
            elif byte in self.extended_ebcdic:
                result.append(self.extended_ebcdic[byte])
            else:
                result.append("?")  # Unknown character
        return "".join(result)

    def ascii_to_ebcdic_str(self, ascii_str: str) -> bytes:
        """Convert ASCII string to EBCDIC bytes"""
        result = bytearray()
        for char in ascii_str:
            if char in self.ascii_to_ebcdic:
                result.append(self.ascii_to_ebcdic[char])
            else:
                # Use a reasonable default for unknown characters
                result.append(0x40)  # Space character
        return bytes(result)

    def ebcdic_to_ascii_hex(self, hex_str: str) -> str:
        """Convert EBCDIC hex string to ASCII string"""
        try:
            ebcdic_bytes = bytes.fromhex(hex_str)
            return self.ebcdic_to_ascii_str(ebcdic_bytes)
        except ValueError:
            raise ValueError(f"Invalid hex string: {hex_str}")

    def ascii_to_ebcdic_hex(self, ascii_str: str) -> str:
        """Convert ASCII string to EBCDIC hex string"""
        ebcdic_bytes = self.ascii_to_ebcdic_str(ascii_str)
        return ebcdic_bytes.hex().upper()

    def analyze_encoding(self, data: bytes) -> Dict[str, Any]:
        """Analyze the encoding characteristics of data"""
        analysis = {
            "length": len(data),
            "hex_values": [f"0x{b:02X}" for b in data],
            "ascii_decoded": self.ebcdic_to_ascii_str(data),
            "readable_chars": 0,
            "control_chars": 0,
            "printable_chars": 0,
            "likely_encoding": "unknown",
        }

        readable_count = 0
        control_count = 0
        printable_count = 0

        for byte in data:
            if 0x20 <= byte <= 0x7E:  # Printable ASCII range when converted
                printable_count += 1
                readable_count += 1
            elif byte in [0x00, 0x0A, 0x0D]:  # Common control chars
                control_count += 1
            elif byte < 0x20:  # Other control chars
                control_count += 1
            else:
                readable_count += 1

        analysis["readable_chars"] = readable_count
        analysis["control_chars"] = control_count
        analysis["printable_chars"] = printable_count

        # Determine likely encoding based on character distribution
        if readable_count / len(data) > 0.7:
            analysis["likely_encoding"] = "ebcdic"
        elif control_count / len(data) > 0.3:
            analysis["likely_encoding"] = "ebcdic_with_controls"
        else:
            analysis["likely_encoding"] = "mixed_or_binary"

        return analysis


async def create_server() -> Server:
    """Create and configure the EBCDIC/ASCII Converter MCP server"""
    server = Server("ebcdic-ascii-converter", "1.0.0")
    converter = EBCDICASCIIConverter()

    # Implementation functions return TextContent to be returned by call_tool
    async def ebcdic_to_ascii(ebcdic_data: str):
        try:
            try:
                data_bytes = base64.b64decode(ebcdic_data)
            except Exception:
                data_bytes = bytes.fromhex(ebcdic_data)
            ascii_result = converter.ebcdic_to_ascii_str(data_bytes)
            analysis = converter.analyze_encoding(data_bytes)
            result = ConversionResult(
                original_data=data_bytes.hex().upper(),
                converted_data=ascii_result,
                conversion_type="EBCDIC to ASCII",
                encoding_details=analysis,
            )
            return TextContent(type="text", text=json.dumps(asdict(result), indent=2))
        except Exception as e:
            return TextContent(
                type="text", text=f"Error in EBCDIC to ASCII conversion: {str(e)}"
            )

    async def ascii_to_ebcdic(ascii_data: str):
        try:
            ebcdic_bytes = converter.ascii_to_ebcdic_str(ascii_data)
            hex_result = ebcdic_bytes.hex().upper()
            result = ConversionResult(
                original_data=ascii_data,
                converted_data=hex_result,
                conversion_type="ASCII to EBCDIC",
                encoding_details={
                    "length": len(ascii_data),
                    "hex_values": [f"0x{b:02X}" for b in ebcdic_bytes],
                },
            )
            return TextContent(type="text", text=json.dumps(asdict(result), indent=2))
        except Exception as e:
            return TextContent(
                type="text", text=f"Error in ASCII to EBCDIC conversion: {str(e)}"
            )

    async def analyze_encoding_func(data: str):
        try:
            try:
                data_bytes = base64.b64decode(data)
            except Exception:
                data_bytes = bytes.fromhex(data)
            analysis = converter.analyze_encoding(data_bytes)
            return TextContent(type="text", text=json.dumps(analysis, indent=2))
        except Exception as e:
            return TextContent(type="text", text=f"Error analyzing encoding: {str(e)}")

    async def hex_to_ascii(hex_data: str):
        try:
            ascii_result = converter.ebcdic_to_ascii_hex(hex_data)
            return TextContent(
                type="text",
                text=json.dumps(
                    {
                        "input_hex": hex_data.upper(),
                        "output_ascii": ascii_result,
                        "conversion_type": "Hex (EBCDIC) to ASCII",
                    },
                    indent=2,
                ),
            )
        except Exception as e:
            return TextContent(
                type="text", text=f"Error in hex to ASCII conversion: {str(e)}"
            )

    async def ascii_to_hex(ascii_data: str):
        try:
            hex_result = converter.ascii_to_ebcdic_hex(ascii_data)
            return TextContent(
                type="text",
                text=json.dumps(
                    {
                        "input_ascii": ascii_data,
                        "output_hex": hex_result,
                        "conversion_type": "ASCII to Hex (EBCDIC)",
                    },
                    indent=2,
                ),
            )
        except Exception as e:
            return TextContent(
                type="text", text=f"Error in ASCII to hex conversion: {str(e)}"
            )

    _tool_map = {
        "ebcdic_to_ascii": ebcdic_to_ascii,
        "ascii_to_ebcdic": ascii_to_ebcdic,
        "analyze_encoding": analyze_encoding_func,
        "hex_to_ascii": hex_to_ascii,
        "ascii_to_hex": ascii_to_hex,
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
                    description=f"{name} (registered by ebcdic-ascii-converter)",
                    inputSchema={},
                    outputSchema=None,
                )
            )
        return types.ListToolsResult(tools=tools, total=len(tools))

    @server.call_tool()
    async def _dispatch_call_tool(name: str, arguments: dict | None):
        func = _tool_map.get(name)
        if func is None:
            raise RuntimeError(f"Tool '{name}' not found")
        arg = None
        if isinstance(arguments, dict):
            # prefer common keys
            for k in ("ebcdic_data", "ascii_data", "data", "hex_data"):
                if k in arguments:
                    arg = arguments[k]
                    break
            if arg is None and len(arguments) > 0:
                arg = next(iter(arguments.values()))
        else:
            arg = arguments
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

    async def main():
        server = await create_server()
        async with stdio_mod.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="ebcdic-ascii-converter",
                    server_version="1.0.0",
                    capabilities=types.ServerCapabilities(),
                ),
            )

    asyncio.run(main())
