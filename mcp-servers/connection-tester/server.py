#!/usr/bin/env python3
"""
Connection Testing MCP Server

This server provides tools for testing TN3270 connections, including
connectivity checks, negotiation testing, SSL/TLS testing, and performance analysis.
"""

import asyncio
import base64
import json
import logging
import socket
import ssl
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from mcp.server import Server
from mcp.types import TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConnectionResult:
    """Result of a connection test"""

    host: str
    port: int
    connected: bool
    response_time: float
    error: Optional[str]
    details: Dict[str, Any]


@dataclass
class NegotiationResult:
    """Result of a negotiation test"""

    negotiation_type: str
    success: bool
    response_time: float
    steps: List[Dict[str, Any]]
    error: Optional[str]


class ConnectionTester:
    """Tester for TN3270 connections and network operations"""

    def __init__(self):
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
        }

        self.telnet_options = {
            0x00: "BINARY",
            0x01: "ECHO",
            0x03: "SGA",
            0x18: "TYPE",
            0x19: "EOR",
            0x28: "TN3270E",
            0x2B: "NAWS",
            0x2C: "TSPEED",
            0x2D: "LFLOW",
            0x2E: "LINEMODE",
            0x2F: "XDISPLOC",
            0x3B: "NEW-ENVIRON",
        }

    async def test_connectivity(
        self, host: str, port: int, timeout: float = 10.0
    ) -> ConnectionResult:
        """Test basic connectivity to a host/port"""
        start_time = time.time()

        try:
            # Create a TCP connection
            reader, writer = await asyncio.open_connection(host, port, timeout=timeout)

            connect_time = time.time() - start_time

            # Send a simple telnet command to test responsiveness
            writer.write(
                b"\xff\xf4\xff\xf2"
            )  # IP + AYT (Interrupt Process + Are You There)
            await writer.drain()

            # Try to read response with timeout
            try:
                response = await asyncio.wait_for(reader.read(1024), timeout=2.0)
                response_time = time.time() - start_time
            except asyncio.TimeoutError:
                response_time = time.time() - start_time
                response = b""

            writer.close()
            if hasattr(writer, "wait_closed"):
                await writer.wait_closed()

            return ConnectionResult(
                host=host,
                port=port,
                connected=True,
                response_time=response_time,
                error=None,
                details={
                    "connect_time": connect_time,
                    "response_bytes": len(response),
                    "response_hex": response.hex() if response else None,
                },
            )
        except Exception as e:
            response_time = time.time() - start_time
            return ConnectionResult(
                host=host,
                port=port,
                connected=False,
                response_time=response_time,
                error=str(e),
                details={},
            )

    async def test_ssl_connectivity(
        self, host: str, port: int, timeout: float = 10.0
    ) -> ConnectionResult:
        """Test SSL/TLS connectivity to a host/port"""
        start_time = time.time()

        try:
            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Create a TCP connection first, then upgrade to SSL
            reader, writer = await asyncio.open_connection(
                host, port, ssl=ssl_context, timeout=timeout
            )

            connect_time = time.time() - start_time

            # Send a simple test
            writer.write(b"\xff\xf4\xff\xf2")  # IP + AYT
            await writer.drain()

            try:
                response = await asyncio.wait_for(reader.read(1024), timeout=2.0)
                response_time = time.time() - start_time
            except asyncio.TimeoutError:
                response_time = time.time() - start_time
                response = b""

            writer.close()
            if hasattr(writer, "wait_closed"):
                await writer.wait_closed()

            return ConnectionResult(
                host=host,
                port=port,
                connected=True,
                response_time=response_time,
                error=None,
                details={
                    "connect_time": connect_time,
                    "response_bytes": len(response),
                    "response_hex": response.hex() if response else None,
                    "ssl_negotiated": True,
                },
            )
        except Exception as e:
            response_time = time.time() - start_time
            return ConnectionResult(
                host=host,
                port=port,
                connected=False,
                response_time=response_time,
                error=str(e),
                details={},
            )

    async def test_basic_negotiation(
        self, host: str, port: int, timeout: float = 10.0
    ) -> NegotiationResult:
        """Test basic TN3270 negotiation sequence"""
        start_time = time.time()
        steps = []

        try:
            reader, writer = await asyncio.open_connection(host, port, timeout=timeout)
            negotiation_start = time.time()

            # Step 1: Send initial negotiation request
            # WILL TERMINAL-TYPE
            negotiation_request = b"\xff\xfb\x18"  # IAC WILL TTYPE
            writer.write(negotiation_request)
            await writer.drain()
            steps.append(
                {
                    "step": 1,
                    "action": "send_will_ttype",
                    "data_sent": negotiation_request.hex(),
                    "timestamp": time.time(),
                }
            )

            # Step 2: Wait for response
            try:
                response = await asyncio.wait_for(reader.read(1024), timeout=3.0)
                steps.append(
                    {
                        "step": 2,
                        "action": "receive_response",
                        "data_received": response.hex(),
                        "timestamp": time.time(),
                    }
                )

                # Parse response for negotiation commands
                parsed = self._parse_telnet_response(response)
                steps.append(
                    {
                        "step": 3,
                        "action": "parse_response",
                        "parsed_commands": parsed,
                        "timestamp": time.time(),
                    }
                )
            except asyncio.TimeoutError:
                steps.append(
                    {"step": 2, "action": "receive_timeout", "timestamp": time.time()}
                )

            # Step 3: Send DO TERMINAL-TYPE if we received WILL
            if b"\xff\xfb\x18" in response or b"\xff\xfd\x18" in response:
                do_ttype = b"\xff\xfd\x18"  # IAC DO TTYPE
                writer.write(do_ttype)
                await writer.drain()
                steps.append(
                    {
                        "step": 4,
                        "action": "send_do_ttype",
                        "data_sent": do_ttype.hex(),
                        "timestamp": time.time(),
                    }
                )

            writer.close()
            if hasattr(writer, "wait_closed"):
                await writer.wait_closed()

            negotiation_time = time.time() - negotiation_start

            return NegotiationResult(
                negotiation_type="basic",
                success=True,
                response_time=negotiation_time,
                steps=steps,
                error=None,
            )
        except Exception as e:
            negotiation_time = time.time() - start_time
            return NegotiationResult(
                negotiation_type="basic",
                success=False,
                response_time=negotiation_time,
                steps=steps,
                error=str(e),
            )

    def _parse_telnet_response(self, response: bytes) -> List[Dict[str, Any]]:
        """Parse telnet response for commands and options"""
        commands = []
        i = 0

        while i < len(response):
            if response[i] == 0xFF:  # IAC
                if i + 1 < len(response):
                    command_code = response[i + 1]
                    command_name = self.telnet_commands.get(
                        command_code, f"UNKNOWN(0x{command_code:02X})"
                    )

                    if command_code in [0xFB, 0xFC, 0xFD, 0xFE]:  # WILL, WONT, DO, DONT
                        if i + 2 < len(response):
                            option_code = response[i + 2]
                            option_name = self.telnet_options.get(
                                option_code, f"UNKNOWN(0x{option_code:02X})"
                            )

                            commands.append(
                                {
                                    "command": command_name,
                                    "option": option_name,
                                    "command_code": command_code,
                                    "option_code": option_code,
                                    "raw_bytes": response[i : i + 3].hex(),
                                }
                            )
                            i += 3
                            continue

                    commands.append(
                        {
                            "command": command_name,
                            "command_code": command_code,
                            "raw_bytes": response[i : i + 2].hex(),
                        }
                    )
                    i += 2
                    continue

            i += 1

        return commands

    async def test_tn3270e_negotiation(
        self, host: str, port: int, timeout: float = 10.0
    ) -> NegotiationResult:
        """Test TN3270E negotiation sequence"""
        start_time = time.time()
        steps = []

        try:
            reader, writer = await asyncio.open_connection(host, port, timeout=timeout)
            negotiation_start = time.time()

            # Step 1: Send DO TN3270E
            do_tn3270e = b"\xff\xfd\x28"  # IAC DO TN3270E
            writer.write(do_tn3270e)
            await writer.drain()
            steps.append(
                {
                    "step": 1,
                    "action": "send_do_tn3270e",
                    "data_sent": do_tn3270e.hex(),
                    "timestamp": time.time(),
                }
            )

            # Step 2: Wait for response (WILL or WONT TN3270E)
            try:
                response = await asyncio.wait_for(reader.read(1024), timeout=3.0)
                steps.append(
                    {
                        "step": 2,
                        "action": "receive_response",
                        "data_received": response.hex(),
                        "timestamp": time.time(),
                    }
                )

                # Parse response
                parsed = self._parse_telnet_response(response)
                steps.append(
                    {
                        "step": 3,
                        "action": "parse_response",
                        "parsed_commands": parsed,
                        "timestamp": time.time(),
                    }
                )

                # Check if server accepted TN3270E
                if any(
                    cmd.get("command_code") == 0xFB and cmd.get("option_code") == 0x28
                    for cmd in parsed
                ):  # WILL TN3270E
                    # Step 3: Send subnegotiation for device type
                    # SB TN3270E DEVICE-TYPE SEND IAC SE
                    subneg = b"\xff\xfa\x28\x01\xff\xf0"  # IAC SB TN3270E DEVICE-TYPE SEND IAC SE
                    writer.write(subneg)
                    await writer.drain()
                    steps.append(
                        {
                            "step": 4,
                            "action": "send_device_type_request",
                            "data_sent": subneg.hex(),
                            "timestamp": time.time(),
                        }
                    )

                    # Step 4: Wait for device type response
                    try:
                        response2 = await asyncio.wait_for(
                            reader.read(1024), timeout=3.0
                        )
                        steps.append(
                            {
                                "step": 5,
                                "action": "receive_device_type_response",
                                "data_received": response2.hex(),
                                "timestamp": time.time(),
                            }
                        )
                    except asyncio.TimeoutError:
                        steps.append(
                            {
                                "step": 5,
                                "action": "device_type_response_timeout",
                                "timestamp": time.time(),
                            }
                        )

            except asyncio.TimeoutError:
                steps.append(
                    {"step": 2, "action": "receive_timeout", "timestamp": time.time()}
                )

            writer.close()
            if hasattr(writer, "wait_closed"):
                await writer.wait_closed()

            negotiation_time = time.time() - negotiation_start

            return NegotiationResult(
                negotiation_type="tn3270e",
                success=True,
                response_time=negotiation_time,
                steps=steps,
                error=None,
            )
        except Exception as e:
            negotiation_time = time.time() - start_time
            return NegotiationResult(
                negotiation_type="tn3270e",
                success=False,
                response_time=negotiation_time,
                steps=steps,
                error=str(e),
            )

    async def test_performance(
        self, host: str, port: int, count: int = 5, timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Test connection performance with multiple attempts"""
        results = []
        connect_times = []

        for i in range(count):
            result = await self.test_connectivity(host, port, timeout)
            results.append(result)
            if result.connected:
                connect_times.append(result.response_time)

        if connect_times:
            avg_time = sum(connect_times) / len(connect_times)
            min_time = min(connect_times)
            max_time = max(connect_times)
        else:
            avg_time = min_time = max_time = 0

        success_count = sum(1 for r in results if r.connected)
        success_rate = success_count / count if count > 0 else 0

        return {
            "test_count": count,
            "success_count": success_count,
            "success_rate": success_rate,
            "average_connect_time": avg_time,
            "min_connect_time": min_time,
            "max_connect_time": max_time,
            "results": [asdict(r) for r in results],
        }

    async def test_port_range(
        self, host: str, start_port: int, end_port: int, timeout: float = 2.0
    ) -> Dict[str, Any]:
        """Test connectivity across a range of ports"""
        open_ports = []
        closed_ports = []

        for port in range(start_port, end_port + 1):
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=timeout
                )
                writer.close()
                if hasattr(writer, "wait_closed"):
                    await writer.wait_closed()
                open_ports.append(port)
            except Exception:
                closed_ports.append(port)

        return {
            "host": host,
            "port_range": f"{start_port}-{end_port}",
            "open_ports": open_ports,
            "closed_ports": closed_ports,
            "open_count": len(open_ports),
            "closed_count": len(closed_ports),
        }


async def create_server() -> Server:
    """Create and configure the Connection Testing MCP server (compatibility layer)"""
    server = Server("connection-tester", "1.0.0")
    tester = ConnectionTester()

    # Internal implementations that return TextContent blocks
    async def test_connectivity_impl(host: str, port: int, timeout: float = 10.0):
        try:
            result = await tester.test_connectivity(host, port, timeout)
            return TextContent(type="text", text=json.dumps(asdict(result), indent=2))
        except Exception as e:
            return TextContent(
                type="text", text=f"Error testing connectivity: {str(e)}"
            )

    async def test_ssl_connectivity_impl(host: str, port: int, timeout: float = 10.0):
        try:
            result = await tester.test_ssl_connectivity(host, port, timeout)
            return TextContent(type="text", text=json.dumps(asdict(result), indent=2))
        except Exception as e:
            return TextContent(
                type="text", text=f"Error testing SSL connectivity: {str(e)}"
            )

    async def test_basic_negotiation_impl(host: str, port: int, timeout: float = 10.0):
        try:
            result = await tester.test_basic_negotiation(host, port, timeout)
            return TextContent(type="text", text=json.dumps(asdict(result), indent=2))
        except Exception as e:
            return TextContent(
                type="text", text=f"Error testing basic negotiation: {str(e)}"
            )

    async def test_tn3270e_negotiation_impl(
        host: str, port: int, timeout: float = 10.0
    ):
        try:
            result = await tester.test_tn3270e_negotiation(host, port, timeout)
            return TextContent(type="text", text=json.dumps(asdict(result), indent=2))
        except Exception as e:
            return TextContent(
                type="text", text=f"Error testing TN3270E negotiation: {str(e)}"
            )

    async def test_performance_impl(
        host: str, port: int, count: int = 5, timeout: float = 10.0
    ):
        try:
            result = await tester.test_performance(host, port, count, timeout)
            return TextContent(type="text", text=json.dumps(result, indent=2))
        except Exception as e:
            return TextContent(type="text", text=f"Error testing performance: {str(e)}")

    async def test_port_range_impl(
        host: str, start_port: int, end_port: int, timeout: float = 2.0
    ):
        try:
            result = await tester.test_port_range(host, start_port, end_port, timeout)
            return TextContent(type="text", text=json.dumps(result, indent=2))
        except Exception as e:
            return TextContent(type="text", text=f"Error testing port range: {str(e)}")

    # Map public tool names to implementations
    _tool_map = {
        "test_connectivity": test_connectivity_impl,
        "test_ssl_connectivity": test_ssl_connectivity_impl,
        "test_basic_negotiation": test_basic_negotiation_impl,
        "test_tn3270e_negotiation": test_tn3270e_negotiation_impl,
        "test_performance": test_performance_impl,
        "test_port_range": test_port_range_impl,
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
                    description=f"{name} (registered by connection-tester)",
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

        # Normalize arguments: prefer named parameters then fallback to first value
        arg = None
        if isinstance(arguments, dict):
            for k in (
                "host",
                "trace_data",
                "ebcdic_data",
                "data",
                "negotiation_data",
                "start_port",
                "end_port",
                "count",
                "timeout",
                "port",
            ):
                if k in arguments:
                    arg = arguments[k]
                    break
            if arg is None and len(arguments) > 0:
                arg = next(iter(arguments.values()))
        else:
            arg = arguments

        # Call implementation with either single arg or expanded args when dict contains multiple
        if isinstance(arg, dict) and not isinstance(arg, (str, bytes)):
            # If argument is a dict but the implementation expects multiple params, pass through dict values as needed.
            result = await func(**arg)
        else:
            # Many implementations expect (host, port, ...)
            if arg is None:
                result = await func()
            else:
                # If arg is a tuple/list, expand it
                if isinstance(arg, (list, tuple)):
                    result = await func(*arg)
                else:
                    # Single scalar argument -> pass as single param
                    result = await func(arg)

        # If result has content attribute (legacy Result), return its content; otherwise return the TextContent directly
        if hasattr(result, "content") and result.content is not None:
            return [result.content]

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
                    server_name="connection-tester",
                    server_version="1.0.0",
                    capabilities=types.ServerCapabilities(),
                ),
            )

    asyncio.run(main())
