#!/usr/bin/env python3
"""
3270 Terminal Debugger MCP Server

This server provides tools for debugging 3270 terminal emulation,
including screen buffer inspection, field analysis, cursor position,
and terminal state information.
"""

import asyncio
import base64
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from mcp.server import Server
from mcp.types import Result, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ScreenField:
    """Represents a field in the 3270 screen"""

    start_row: int
    start_col: int
    end_row: int
    end_col: int
    content: str
    protected: bool
    modified: bool
    attribute: int
    length: int


@dataclass
class TerminalState:
    """Represents the current state of the terminal"""

    cursor_row: int
    cursor_col: int
    screen_rows: int
    screen_cols: int
    connected: bool
    tn3270_mode: bool
    tn3270e_mode: bool
    screen_buffer: str
    fields: List[ScreenField]
    field_count: int
    input_field_count: int
    protected_field_count: int


class TerminalDebugger:
    """Debugger for 3270 terminal emulation"""

    def __init__(self):
        # Common 3270 terminal models and their dimensions
        self.terminal_models = {
            "IBM-3278-2": (24, 80),
            "IBM-3278-3": (32, 80),
            "IBM-3278-4": (43, 80),
            "IBM-3278-5": (27, 132),
            "IBM-3279-2": (24, 80),  # Color version
            "IBM-3279-3": (32, 80),
            "IBM-3279-4": (43, 80),
            "IBM-3279-5": (27, 132),
        }

        # Field attribute bits
        self.field_attributes = {
            0x00: "Unprotected, Numeric",
            0x10: "Protected, Numeric",
            0x20: "Unprotected, Alpha",
            0x30: "Protected, Alpha",
            0x40: "Unprotected, Intensity High",
            0x50: "Protected, Intensity High",
            0x60: "Unprotected, Intensity Low",
            0x70: "Protected, Intensity Low",
        }

    def parse_screen_buffer(
        self, buffer_data: bytes, rows: int = 24, cols: int = 80
    ) -> str:
        """Parse raw screen buffer bytes to readable text"""
        try:
            # Try to decode as EBCDIC first
            return buffer_data.decode("cp037")  # US-Canada EBCDIC
        except UnicodeDecodeError:
            # Fallback to interpreting as raw bytes with basic EBCDIC mapping
            result = []
            for i, byte in enumerate(buffer_data):
                if 0x40 <= byte <= 0x5A:  # Space to 'Z'
                    result.append(chr(byte - 0x40 + ord(" ")))
                elif 0x61 <= byte <= 0x79:  # 'a' to 'i'
                    result.append(chr(byte - 0x61 + ord("a")))
                elif 0x81 <= byte <= 0x89:  # 'j' to 'r'
                    result.append(chr(byte - 0x81 + ord("j")))
                elif 0x91 <= byte <= 0x99:  # 's' to 'z'
                    result.append(chr(byte - 0x91 + ord("s")))
                elif 0xA2 <= byte <= 0xA9:  # '0' to '9'
                    result.append(chr(byte - 0xA2 + ord("0")))
                elif byte == 0x00:
                    result.append(" ")
                else:
                    result.append("?")
            return "".join(result)

    def extract_fields(
        self, buffer_data: bytes, attr_data: bytes, rows: int = 24, cols: int = 80
    ) -> List[ScreenField]:
        """Extract fields from screen buffer and attributes"""
        fields = []
        buffer_str = self.parse_screen_buffer(buffer_data, rows, cols)

        # Simple field detection: look for field attributes in attribute data
        # In real 3270, field attributes are stored in attribute bytes
        field_start = None
        current_attr = 0

        for pos in range(len(buffer_data)):
            row = pos // cols
            col = pos % cols

            # Check if this position has a field attribute marker
            if pos < len(attr_data):
                attr_byte = attr_data[pos]

                # Check if this is a field attribute (starts a new field)
                if attr_byte & 0xF0 in [
                    0x10,
                    0x20,
                    0x30,
                    0x40,
                    0x50,
                    0x60,
                    0x70,
                ]:  # Field attributes
                    if field_start is not None:
                        # End previous field
                        prev_row, prev_col = field_start
                        content = self._extract_field_content(
                            buffer_str, prev_row, prev_col, row, col, cols
                        )
                        fields.append(
                            ScreenField(
                                start_row=prev_row,
                                start_col=prev_col,
                                end_row=row,
                                end_col=col,
                                content=content,
                                protected=(current_attr & 0x10) != 0,
                                modified=(current_attr & 0x01) != 0,
                                attribute=current_attr,
                                length=(row * cols + col)
                                - (prev_row * cols + prev_col)
                                + 1,
                            )
                        )

                    # Start new field
                    field_start = (row, col)
                    current_attr = attr_byte

        # Add the last field if it exists
        if field_start is not None:
            prev_row, prev_col = field_start
            content = self._extract_field_content(
                buffer_str, prev_row, prev_col, rows - 1, cols - 1, cols
            )
            fields.append(
                ScreenField(
                    start_row=prev_row,
                    start_col=prev_col,
                    end_row=rows - 1,
                    end_col=cols - 1,
                    content=content,
                    protected=(current_attr & 0x10) != 0,
                    modified=(current_attr & 0x01) != 0,
                    attribute=current_attr,
                    length=(rows * cols) - (prev_row * cols + prev_col) + 1,
                )
            )

        return fields

    def _extract_field_content(
        self,
        buffer_str: str,
        start_row: int,
        start_col: int,
        end_row: int,
        end_col: int,
        cols: int,
    ) -> str:
        """Extract content from a field range"""
        content = []
        for r in range(start_row, end_row + 1):
            c_start = start_col if r == start_row else 0
            c_end = end_col if r == end_row else cols - 1
            for c in range(c_start, c_end + 1):
                pos = r * cols + c
                if pos < len(buffer_str):
                    content.append(buffer_str[pos])
        return "".join(content).strip()

    def analyze_terminal_state(
        self,
        screen_buffer: bytes,
        attribute_buffer: bytes,
        cursor_pos: Tuple[int, int],
        is_connected: bool = True,
        tn3270_mode: bool = True,
        tn3270e_mode: bool = False,
        rows: int = 24,
        cols: int = 80,
    ) -> TerminalState:
        """Analyze the current terminal state"""
        fields = self.extract_fields(screen_buffer, attribute_buffer, rows, cols)

        input_fields = [f for f in fields if not f.protected]
        protected_fields = [f for f in fields if f.protected]

        return TerminalState(
            cursor_row=cursor_pos[0],
            cursor_col=cursor_pos[1],
            screen_rows=rows,
            screen_cols=cols,
            connected=is_connected,
            tn3270_mode=tn3270_mode,
            tn3270e_mode=tn3270e_mode,
            screen_buffer=self.parse_screen_buffer(screen_buffer, rows, cols),
            fields=fields,
            field_count=len(fields),
            input_field_count=len(input_fields),
            protected_field_count=len(protected_fields),
        )

    def get_field_at_position(
        self, fields: List[ScreenField], row: int, col: int
    ) -> Optional[ScreenField]:
        """Get the field at a specific position"""
        for field in fields:
            if (
                field.start_row <= row <= field.end_row
                and field.start_col <= col <= field.end_col
            ):
                return field
        return None

    def validate_screen_format(
        self, screen_data: str, rows: int = 24, cols: int = 80
    ) -> Dict[str, Any]:
        """Validate the format of screen data"""
        lines = screen_data.split("\n")
        validation = {
            "valid_format": True,
            "line_count": len(lines),
            "expected_lines": rows,
            "line_length_issues": [],
            "total_characters": len(screen_data),
            "expected_total": rows * cols,
            "issues": [],
        }

        for i, line in enumerate(lines):
            if len(line) > cols:
                validation["line_length_issues"].append(
                    f"Line {i}: {len(line)} chars (max {cols})"
                )
                validation["valid_format"] = False
            elif len(line) < cols and i < rows - 1:  # Don't check last line for padding
                validation["issues"].append(
                    f"Line {i}: {len(line)} chars (expected {cols})"
                )

        if len(lines) != rows:
            validation["issues"].append(f"Expected {rows} lines, got {len(lines)}")
            validation["valid_format"] = False

        return validation

    def format_screen_for_display(
        self, screen_data: str, rows: int = 24, cols: int = 80
    ) -> str:
        """Format screen data for better display"""
        lines = screen_data.split("\n")
        formatted_lines = []

        for i, line in enumerate(lines):
            if len(line) < cols:
                line = line.ljust(cols)  # Pad with spaces
            elif len(line) > cols:
                line = line[:cols]  # Truncate
            formatted_lines.append(f"{i+1:2d}: {line}")

        return "\n".join(formatted_lines)


async def create_server() -> Server:
    """Create and configure the 3270 Terminal Debugger MCP server"""
    server = Server("terminal-debugger", "1.0.0")
    debugger = TerminalDebugger()

    # Implementation functions return TextContent
    async def analyze_terminal_state_impl(
        screen_buffer: str,
        attribute_buffer: str,
        cursor_row: int = 0,
        cursor_col: int = 0,
        connected: bool = True,
        tn3270_mode: bool = True,
        tn3270e_mode: bool = False,
        rows: int = 24,
        cols: int = 80,
    ):
        try:
            screen_bytes = base64.b64decode(screen_buffer)
            attr_bytes = base64.b64decode(attribute_buffer)

            state = debugger.analyze_terminal_state(
                screen_bytes,
                attr_bytes,
                (cursor_row, cursor_col),
                connected,
                tn3270_mode,
                tn3270e_mode,
                rows,
                cols,
            )
            return TextContent(type="text", text=json.dumps(asdict(state), indent=2))
        except Exception as e:
            return TextContent(
                type="text", text=f"Error analyzing terminal state: {str(e)}"
            )

    async def extract_fields_impl(
        screen_buffer: str,
        attribute_buffer: str,
        rows: int = 24,
        cols: int = 80,
    ):
        try:
            screen_bytes = base64.b64decode(screen_buffer)
            attr_bytes = base64.b64decode(attribute_buffer)

            fields = debugger.extract_fields(screen_bytes, attr_bytes, rows, cols)
            fields_dict = [asdict(f) for f in fields]

            result = {
                "fields": fields_dict,
                "total_fields": len(fields),
                "input_fields": len([f for f in fields if not f.protected]),
                "protected_fields": len([f for f in fields if f.protected]),
            }
            return TextContent(type="text", text=json.dumps(result, indent=2))
        except Exception as e:
            return TextContent(type="text", text=f"Error extracting fields: {str(e)}")

    async def validate_screen_format_impl(
        screen_data: str, rows: int = 24, cols: int = 80
    ):
        try:
            validation = debugger.validate_screen_format(screen_data, rows, cols)
            return TextContent(type="text", text=json.dumps(validation, indent=2))
        except Exception as e:
            return TextContent(
                type="text", text=f"Error validating screen format: {str(e)}"
            )

    async def format_screen_display_impl(
        screen_data: str, rows: int = 24, cols: int = 80
    ):
        try:
            formatted = debugger.format_screen_for_display(screen_data, rows, cols)
            return TextContent(type="text", text=formatted)
        except Exception as e:
            return TextContent(
                type="text", text=f"Error formatting screen display: {str(e)}"
            )

    async def get_field_at_position_impl(
        screen_buffer: str,
        attribute_buffer: str,
        row: int,
        col: int,
        rows: int = 24,
        cols: int = 80,
    ):
        try:
            screen_bytes = base64.b64decode(screen_buffer)
            attr_bytes = base64.b64decode(attribute_buffer)

            fields = debugger.extract_fields(screen_bytes, attr_bytes, rows, cols)
            field = debugger.get_field_at_position(fields, row, col)

            if field:
                return TextContent(
                    type="text", text=json.dumps(asdict(field), indent=2)
                )
            else:
                return TextContent(
                    type="text", text=f"No field found at position ({row}, {col})"
                )
        except Exception as e:
            return TextContent(
                type="text", text=f"Error getting field at position: {str(e)}"
            )

    async def get_terminal_models_impl():
        try:
            models = {
                "models": list(debugger.terminal_models.keys()),
                "dimensions": {
                    k: {"rows": v[0], "cols": v[1]}
                    for k, v in debugger.terminal_models.items()
                },
            }
            return TextContent(type="text", text=json.dumps(models, indent=2))
        except Exception as e:
            return TextContent(
                type="text", text=f"Error getting terminal models: {str(e)}"
            )

    _tool_map = {
        "analyze_terminal_state": analyze_terminal_state_impl,
        "extract_fields": extract_fields_impl,
        "validate_screen_format": validate_screen_format_impl,
        "format_screen_display": format_screen_display_impl,
        "get_field_at_position": get_field_at_position_impl,
        "get_terminal_models": get_terminal_models_impl,
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
                    description=f"{name} (registered by terminal-debugger)",
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
            for k in ("screen_buffer", "attribute_buffer", "screen_data", "row", "col"):
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
            # If the arguments are a dict and the function expects multiple params,
            # pass them through as keyword arguments where possible.
            if isinstance(arguments, dict):
                try:
                    result = await func(**arguments)  # type: ignore[arg-type]
                except TypeError:
                    # fall back to single-arg
                    result = await func(arg)
            else:
                result = await func(arg)
        return [result] if result is not None else []

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
                    server_name="terminal-debugger",
                    server_version="1.0.0",
                    capabilities=types.ServerCapabilities(),
                ),
            )

    asyncio.run(main())
