#!/usr/bin/env python3
"""
Comprehensive MCP Server Functionality Demonstration

This script exercises all 22 MCP tools across 4 servers to demonstrate
complete MCP functionality for the pure3270 TN3270 emulator project.
"""

import asyncio
import base64
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class MCPFunctionalityDemo:
    """Demonstrate all MCP server functionality"""

    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()

    async def call_mcp_tool(
        self, session, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an MCP tool through a server session"""
        request = {
            "jsonrpc": "2.0",
            "id": len(session["requests"]),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        session["requests"].append(request)

        print(f"Calling {session['server_name']}.{tool_name} with args: {arguments}")

        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            session["stdin"].write(request_json.encode())
            await session["stdin"].drain()

            # Read response
            response_line = await asyncio.wait_for(
                session["stdout"].readline(), timeout=10.0
            )

            if response_line:
                response = json.loads(response_line.decode().strip())
                is_success = "error" not in response and "result" in response

                result = {
                    "request": request,
                    "response": response,
                    "success": is_success,
                    "error": (
                        response.get("error", {}).get("message")
                        if not is_success
                        else None
                    ),
                }

                if is_success:
                    print(f"✅ {tool_name} succeeded")
                    if len(str(response.get("result", ""))) < 100:
                        print(f"  Result: {response.get('result', '')}")
                else:
                    print(f"❌ {tool_name} failed: {result['error']}")

                return result
            else:
                return {
                    "request": request,
                    "response": "NO_RESPONSE",
                    "success": False,
                    "error": "No response",
                }

        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"❌ {tool_name} exception: {error_msg}")
            return {
                "request": request,
                "response": "EXCEPTION",
                "success": False,
                "error": error_msg,
            }

    async def start_server(
        self, server_name: str, server_script: str
    ) -> Dict[str, Any]:
        """Start an MCP server process"""
        print(f"\n🚀 Starting {server_name}...")

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                server_script,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(server_script),
            )

            # Give server time to initialize
            await asyncio.sleep(0.5)

            session = {
                "server_name": server_name,
                "process": process,
                "stdin": process.stdin,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "requests": [],
            }

            # Test if server is responsive
            await self.call_mcp_tool(session, "list_tools", {})

            return session

        except Exception as e:
            print(f"❌ Failed to start {server_name}: {e}")
            return None

    async def stop_server(self, session: Dict[str, Any]):
        """Stop an MCP server process"""
        if session and "process" in session:
            try:
                session["stdin"].close()
                await session["process"].wait()
                print(f"🛑 Stopped {session['server_name']}")
            except:
                pass

    async def demonstrate_tn3270_protocol_analyzer(self) -> List[Dict[str, Any]]:
        """Demonstrate TN3270 Protocol Analyzer server functionality"""
        print("\n🔍 === TN3270 Protocol Analyzer Demonstration ===")
        server_script = "mcp-servers/tn3270-protocol-analyzer/server.py"
        session = await self.start_server("TN3270 Protocol Analyzer", server_script)
        if not session:
            return []

        results = []

        # 1. Get protocol constants
        result = await self.call_mcp_tool(session, "get_protocol_constants", {})
        results.append(result)

        # 2. Analyze negotiation trace (simple IAC DO ECHO)
        trace_data = base64.b64encode(b"\xff\xfd\x01").decode()
        result = await self.call_mcp_tool(
            session, "analyze_negotiation_trace", {"trace_data": trace_data}
        )
        results.append(result)

        # 3. Decode EBCDIC to ASCII (test with "Hello")
        ebcdic_data = base64.b64encode(b"\xc8\x85\x93\x93\x96").decode()
        result = await self.call_mcp_tool(
            session, "decode_ebcdic", {"ebcdic_data": ebcdic_data}
        )
        results.append(result)

        # 4. Parse data stream (simulate screen update)
        screen_data = base64.b64encode(b"\x40\x41\x42\x43HELLO\x00").decode()
        result = await self.call_mcp_tool(
            session, "parse_data_stream", {"data": screen_data}
        )
        results.append(result)

        # 5. Analyze TN3270E negotiation
        tn3270e_data = base64.b64encode(
            b"\xff\xfd\x28\xff\xfa\x28\x01\xff\xf0"
        ).decode()
        result = await self.call_mcp_tool(
            session, "analyze_tn3270e_negotiation", {"negotiation_data": tn3270e_data}
        )
        results.append(result)

        await self.stop_server(session)
        return results

    async def demonstrate_ebcdic_converter(self) -> List[Dict[str, Any]]:
        """Demonstrate EBCDIC/ASCII Converter server functionality"""
        print("\n🔄 === EBCDIC/ASCII Converter Demonstration ===")
        server_script = "mcp-servers/ebcdic-ascii-converter/server.py"
        session = await self.start_server("EBCDIC/ASCII Converter", server_script)
        if not session:
            return []

        results = []

        # 1. ASCII to EBCDIC conversion
        result = await self.call_mcp_tool(
            session, "ascii_to_ebcdic", {"ascii_data": "Hello World"}
        )
        results.append(result)

        # 2. EBCDIC to ASCII conversion
        # Use known EBCDIC bytes for "WORLD"
        ebcdic_world = base64.b64encode(b"\xe6\xd6\xd9\x93\xc4").decode()
        result = await self.call_mcp_tool(
            session, "ebcdic_to_ascii", {"ebcdic_data": ebcdic_world}
        )
        results.append(result)

        # 3. Analyze encoding
        test_data = base64.b64encode(b"Mixed ascii/data\x00\x01").decode()
        result = await self.call_mcp_tool(
            session, "analyze_encoding", {"data": test_data}
        )
        results.append(result)

        # 4. Hex EBCDIC to ASCII
        hex_data = "C8E2E3E240"  # "TEST" in EBCDIC hex
        result = await self.call_mcp_tool(
            session, "hex_to_ascii", {"hex_data": hex_data}
        )
        results.append(result)

        # 5. ASCII to hex EBCDIC
        result = await self.call_mcp_tool(
            session, "ascii_to_hex", {"ascii_data": "PURE3270"}
        )
        results.append(result)

        await self.stop_server(session)
        return results

    async def demonstrate_terminal_debugger(self) -> List[Dict[str, Any]]:
        """Demonstrate Terminal Debugger server functionality"""
        print("\n📺 === Terminal Debugger Demonstration ===")
        server_script = "mcp-servers/terminal-debugger/server.py"
        session = await self.start_server("Terminal Debugger", server_script)
        if not session:
            return []

        results = []

        # 1. Get terminal models
        result = await self.call_mcp_tool(session, "get_terminal_models", {})
        results.append(result)

        # 2. Analyze terminal state
        screen_buffer = base64.b64encode(b"Hello TN3270\x00\x00\x00").decode()
        attr_buffer = base64.b64encode(
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        ).decode()
        result = await self.call_mcp_tool(
            session,
            "analyze_terminal_state",
            {
                "screen_buffer": screen_buffer,
                "attribute_buffer": attr_buffer,
                "cursor_row": 0,
                "cursor_col": 5,
                "connected": True,
                "tn3270_mode": True,
                "tn3270e_mode": False,
            },
        )
        results.append(result)

        # 3. Extract fields
        result = await self.call_mcp_tool(
            session,
            "extract_fields",
            {"screen_buffer": screen_buffer, "attribute_buffer": attr_buffer},
        )
        results.append(result)

        # 4. Validate screen format
        screen_data = "Line 1\nLine 2\nLine 3"
        result = await self.call_mcp_tool(
            session,
            "validate_screen_format",
            {"screen_data": screen_data, "rows": 3, "cols": 6},
        )
        results.append(result)

        # 5. Format screen display
        result = await self.call_mcp_tool(
            session,
            "format_screen_display",
            {"screen_data": screen_data, "rows": 3, "cols": 6},
        )
        results.append(result)

        # 6. Get field at position (if screen has fields)
        result = await self.call_mcp_tool(
            session,
            "get_field_at_position",
            {
                "screen_buffer": screen_buffer,
                "attribute_buffer": attr_buffer,
                "row": 0,
                "col": 0,
            },
        )
        results.append(result)

        await self.stop_server(session)
        return results

    async def demonstrate_connection_tester(self) -> List[Dict[str, Any]]:
        """Demonstrate Connection Tester server functionality"""
        print("\n🌐 === Connection Tester Demonstration ===")
        server_script = "mcp-servers/connection-tester/server.py"
        session = await self.start_server("Connection Tester", server_script)
        if not session:
            return []

        results = []

        # 1. Test connectivity (to localhost)
        result = await self.call_mcp_tool(
            session,
            "test_connectivity",
            {"host": "127.0.0.1", "port": 80, "timeout": 2.0},
        )
        results.append(result)

        # 2. Test SSL connectivity (may fail)
        result = await self.call_mcp_tool(
            session,
            "test_ssl_connectivity",
            {"host": "127.0.0.1", "port": 443, "timeout": 2.0},
        )
        results.append(result)

        # 3. Test basic negotiation (may fail)
        result = await self.call_mcp_tool(
            session,
            "test_basic_negotiation",
            {"host": "127.0.0.1", "port": 23, "timeout": 1.0},
        )
        results.append(result)

        # 4. Test TN3270E negotiation (may fail)
        result = await self.call_mcp_tool(
            session,
            "test_tn3270e_negotiation",
            {"host": "127.0.0.1", "port": 23, "timeout": 1.0},
        )
        results.append(result)

        # 5. Test performance
        result = await self.call_mcp_tool(
            session,
            "test_performance",
            {"host": "127.0.0.1", "port": 80, "count": 2, "timeout": 1.0},
        )
        results.append(result)

        # 6. Test port range
        result = await self.call_mcp_tool(
            session,
            "test_port_range",
            {"host": "127.0.0.1", "start_port": 80, "end_port": 82, "timeout": 1.0},
        )
        results.append(result)

        await self.stop_server(session)
        return results

    def generate_report(self):
        """Generate comprehensive functionality report"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        report = []
        report.append("=" * 80)
        report.append("MCP SERVER FUNCTIONALITY DEMONSTRATION REPORT")
        report.append("=" * 80)
        report.append(
            f"Execution Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} - {end_time.strftime('%H:%M:%S')}"
        )
        report.append(f"Duration: {duration.total_seconds():.2f} seconds")
        report.append("")

        total_tests = 0
        total_success = 0

        for server_results in self.results.values():
            for result in server_results:
                if "server_name" in result:
                    continue
                total_tests += 1
                if result.get("success", False):
                    total_success += 1

        report.append(
            f"OVERALL RESULTS: {total_success}/{total_tests} tests passed ({total_success/total_tests*100:.1f}%)"
        )
        report.append("")

        for server_name, server_results in self.results.items():
            report.append(f"SERVER: {server_name}")
            report.append("-" * 40)

            server_success = sum(1 for r in server_results if r.get("success", False))
            server_total = len(server_results)

            report.append(f"Tests Passed: {server_success}/{server_total}")
            report.append("")

            for result in server_results:
                if "server_name" in result:
                    continue

                status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
                tool_name = result["request"]["params"]["name"]
                report.append(f"  {status} {tool_name}")

                if not result.get("success", False):
                    error = result.get("error", "Unknown error")
                    report.append(f"    Error: {error}")

            report.append("")

        report.append("=" * 80)
        report.append("DETAILED RESULTS JSON")
        report.append("=" * 80)
        report.append(json.dumps(self.results, indent=2, default=str))

        return "\n".join(report)

    async def run_demonstrations(self) -> str:
        """Run all functionality demonstrations"""
        print("🎯 MCP Server Functionality Demonstration")
        print("=" * 50)
        print("Exercising all 22 MCP tools across 4 servers")
        print("This may take a minute as servers start/stop...")

        # Run each server demonstration
        self.results["TN3270 Protocol Analyzer"] = (
            await self.demonstrate_tn3270_protocol_analyzer()
        )
        self.results["EBCDIC/ASCII Converter"] = (
            await self.demonstrate_ebcdic_converter()
        )
        self.results["Terminal Debugger"] = await self.demonstrate_terminal_debugger()
        self.results["Connection Tester"] = await self.demonstrate_connection_tester()

        # Generate final report
        report = self.generate_report()

        # Save report to file
        with open("MCP_FUNCTIONALITY_DEMO_REPORT.md", "w") as f:
            f.write(report)

        print("\n" + "=" * 50)
        print("DEMONSTRATION COMPLETE!")
        print("See MCP_FUNCTIONALITY_DEMO_REPORT.md for full results")
        print("=" * 50)

        return report


def main():
    """Run the functionality demonstration"""
    demo = MCPFunctionalityDemo()

    try:
        result = asyncio.run(demo.run_demonstrations())
        print("\nFinal Report Summary:")
        # Just print key summary lines
        lines = result.split("\n")
        for line in lines:
            if any(
                keyword in line
                for keyword in ["OVERALL RESULTS:", "SERVER:", "PASS", "FAIL"]
            ):
                print(line)
        return 0

    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
        return 1
    except Exception as e:
        print(f"\nDemo failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
