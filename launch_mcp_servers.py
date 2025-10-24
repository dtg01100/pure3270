#!/usr/bin/env python3
"""
Launch script for all MCP servers in the pure3270 project.

This script starts all 4 MCP servers as background processes for development and testing.
Each server runs on stdio and can be connected to by MCP-compatible clients.
"""

import asyncio
import signal
import subprocess
import sys
from typing import Any, Dict, List


class MCPServerManager:
    """Manages launching and monitoring MCP servers."""

    def __init__(self):
        self.servers = [
            {
                "name": "TN3270 Protocol Analyzer",
                "path": "mcp-servers/tn3270-protocol-analyzer/server.py",
                "process": None,
            },
            {
                "name": "EBCDIC/ASCII Converter",
                "path": "mcp-servers/ebcdic-ascii-converter/server.py",
                "process": None,
            },
            {
                "name": "Terminal Debugger",
                "path": "mcp-servers/terminal-debugger/server.py",
                "process": None,
            },
            {
                "name": "Connection Tester",
                "path": "mcp-servers/connection-tester/server.py",
                "process": None,
            },
        ]
        self.running = False

    async def start_servers(self) -> None:
        """Start all MCP servers."""
        print("🚀 Starting MCP servers for pure3270 project...")
        print("=" * 50)

        for server in self.servers:
            print(f"Starting {server['name']}...")
            try:
                # Launch server as subprocess
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    server["path"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=".",
                )
                server["process"] = process
                print(f"✅ {server['name']} started (PID: {process.pid})")
            except Exception as e:
                print(f"❌ Failed to start {server['name']}: {e}")

        self.running = True
        print("\n" + "=" * 50)
        print("🎉 All MCP servers started successfully!")
        print(
            "Servers are running in the background and ready to accept MCP connections."
        )
        print("Press Ctrl+C to stop all servers.")
        print("=" * 50)

    async def stop_servers(self) -> None:
        """Stop all running MCP servers."""
        if not self.running:
            return

        print("\n🛑 Stopping MCP servers...")
        for server in self.servers:
            if server["process"]:
                try:
                    server["process"].terminate()
                    await asyncio.wait_for(server["process"].wait(), timeout=5.0)
                    print(f"✅ {server['name']} stopped")
                except asyncio.TimeoutError:
                    print(f"⚠️  {server['name']} didn't stop gracefully, killing...")
                    server["process"].kill()
                    await server["process"].wait()
                except Exception as e:
                    print(f"❌ Error stopping {server['name']}: {e}")

        self.running = False
        print("🎯 All MCP servers stopped.")

    async def monitor_servers(self) -> None:
        """Monitor server processes and restart if they crash."""
        while self.running:
            for server in self.servers:
                if server["process"] and server["process"].returncode is not None:
                    print(
                        f"⚠️  {server['name']} crashed (exit code: {server['process'].returncode})"
                    )
                    # Could implement auto-restart here if desired
            await asyncio.sleep(1)

    async def run(self) -> None:
        """Main run loop."""

        # Set up signal handlers
        def signal_handler(signum, frame):
            print(f"\nReceived signal {signum}, shutting down...")
            asyncio.create_task(self.stop_servers())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            await self.start_servers()
            await self.monitor_servers()
        except KeyboardInterrupt:
            pass
        finally:
            await self.stop_servers()


def print_usage():
    """Print usage information."""
    print("MCP Server Launcher for pure3270")
    print("=" * 40)
    print("This script launches all 4 MCP servers for the pure3270 project:")
    print("• TN3270 Protocol Analyzer")
    print("• EBCDIC/ASCII Converter")
    print("• Terminal Debugger")
    print("• Connection Tester")
    print()
    print("Usage:")
    print("  python launch_mcp_servers.py    # Start all servers")
    print("  python launch_mcp_servers.py --help  # Show this help")
    print()
    print("The servers will run in the background until you press Ctrl+C.")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print_usage()
        return

    manager = MCPServerManager()
    asyncio.run(manager.run())


if __name__ == "__main__":
    main()
