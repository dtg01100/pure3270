#!/usr/bin/env python3
"""
Compare pure3270 and s3270 trace handling.

This script:
1. Runs a pure3270 session with tracing enabled
2. Captures the data stream orders/commands
3. Compares with s3270 trace file format
4. Shows differences in how each handles the protocol

Usage:
    python trace_comparison.py [host] [port] [--trace-file TRACEFILE]
"""

import asyncio
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from pure3270 import AsyncSession


class S3270TraceParser:
    """Parse s3270 trace files (.trc format)."""

    def __init__(self, trace_file: str):
        self.trace_file = Path(trace_file)
        self.events = []

    def parse(self) -> List[Dict[str, Any]]:
        """Parse s3270 trace file and extract events."""
        events = []

        with open(self.trace_file, "r") as f:
            for line in f:
                line = line.strip()

                # Skip comments
                if line.startswith("//"):
                    continue

                # Parse output lines (< direction)
                if line.startswith("<"):
                    # Format: < 0x0   hexdata
                    match = re.match(r"<\s+0x\w+\s+([0-9a-fA-F]+)", line)
                    if match:
                        hex_data = match.group(1)
                        data = bytes.fromhex(hex_data)
                        events.append(
                            {
                                "direction": "send",
                                "data": data,
                                "hex": hex_data,
                                "size": len(data),
                            }
                        )

                # Parse input lines (> direction)
                elif line.startswith(">"):
                    match = re.match(r">\s+0x\w+\s+([0-9a-fA-F]+)", line)
                    if match:
                        hex_data = match.group(1)
                        data = bytes.fromhex(hex_data)
                        events.append(
                            {
                                "direction": "recv",
                                "data": data,
                                "hex": hex_data,
                                "size": len(data),
                            }
                        )

        self.events = events
        return events


class Pure3270TraceCapture:
    """Capture pure3270 data stream processing."""

    def __init__(self):
        self.data_stream_events = []
        self.telnet_events = []

    async def connect_and_capture(self, host: str, port: int) -> Dict[str, Any]:
        """Connect to host and capture all trace events."""
        async with AsyncSession(enable_trace=True) as session:
            try:
                await session.connect(host, port)

                # Wait a bit for data
                await asyncio.sleep(2.0)

                # Try to read screen
                try:
                    screen_data = await session.read()
                except:
                    screen_data = None

                # Get trace events - try multiple methods
                trace_events = []

                # Method 1: get_trace_events() if available
                if hasattr(session, "get_trace_events"):
                    trace_events = session.get_trace_events()

                # Method 2: Check handler's negotiator's recorder
                if not trace_events and hasattr(session, "handler"):
                    handler = session.handler
                    if hasattr(handler, "negotiator"):
                        negotiator = handler.negotiator
                        if hasattr(negotiator, "recorder") and negotiator.recorder:
                            trace_events = negotiator.recorder.events()

                # Method 3: Check _trace_events directly
                if not trace_events and hasattr(session, "_trace_events"):
                    trace_events = session._trace_events

                # Get screen buffer if available
                screen_buffer = getattr(session, "screen_buffer", None)

                # Check connection status
                handler = getattr(session, "handler", None)
                connected = handler is not None and hasattr(handler, "state")

                return {
                    "trace_events": trace_events,
                    "screen_data": screen_data,
                    "screen_buffer": screen_buffer,
                    "connected": connected,
                }

            except Exception as e:
                print(f"Error during capture: {e}")
                import traceback

                traceback.print_exc()
                return {
                    "trace_events": [],
                    "screen_data": None,
                    "screen_buffer": None,
                    "connected": False,
                    "error": str(e),
                }


class TraceComparator:
    """Compare pure3270 and s3270 trace handling."""

    def __init__(self):
        self.pure3270_events = []
        self.s3270_events = []

    def compare_protocol_handling(
        self, pure3270_data: Dict[str, Any], s3270_events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compare how pure3270 and s3270 handle the protocol."""

        results = {
            "pure3270_trace_count": len(pure3270_data.get("trace_events", [])),
            "s3270_event_count": len(s3270_events),
            "differences": [],
            "similarities": [],
        }

        # Analyze trace events
        pure_events = pure3270_data.get("trace_events", [])

        # Count event types in pure3270
        pure_event_types = {}
        for event in pure_events:
            kind = event.kind if hasattr(event, "kind") else "unknown"
            pure_event_types[kind] = pure_event_types.get(kind, 0) + 1

        results["pure3270_event_types"] = pure_event_types

        # Count directions in s3270
        s3270_directions = {}
        s3270_total_bytes_sent = 0
        s3270_total_bytes_recv = 0

        for event in s3270_events:
            direction = event["direction"]
            s3270_directions[direction] = s3270_directions.get(direction, 0) + 1

            if direction == "send":
                s3270_total_bytes_sent += event["size"]
            else:
                s3270_total_bytes_recv += event["size"]

        results["s3270_directions"] = s3270_directions
        results["s3270_bytes"] = {
            "sent": s3270_total_bytes_sent,
            "received": s3270_total_bytes_recv,
            "total": s3270_total_bytes_sent + s3270_total_bytes_recv,
        }

        return results

    def print_comparison(
        self,
        results: Dict[str, Any],
        pure3270_data: Dict[str, Any],
        s3270_events: List[Dict[str, Any]],
    ):
        """Print detailed comparison."""

        print("\n" + "=" * 80)
        print("TRACE COMPARISON: pure3270 vs s3270")
        print("=" * 80)

        print("\n📊 PURE3270 TRACE EVENTS")
        print("-" * 80)
        print(f"Total events captured: {results['pure3270_trace_count']}")
        print(f"Event types: {results['pure3270_event_types']}")

        # Show first few pure3270 events
        pure_events = pure3270_data.get("trace_events", [])
        if pure_events:
            print(f"\nFirst {min(5, len(pure_events))} events:")
            for i, event in enumerate(pure_events[:5]):
                ts = event.ts if hasattr(event, "ts") else 0
                kind = event.kind if hasattr(event, "kind") else "unknown"
                details = event.details if hasattr(event, "details") else {}
                print(f"  {i+1}. [{ts:7.3f}s] {kind:12} {details}")

        print("\n📊 S3270 TRACE EVENTS")
        print("-" * 80)
        print(f"Total events parsed: {results['s3270_event_count']}")
        print(f"Directions: {results['s3270_directions']}")
        print(f"Bytes: {results['s3270_bytes']}")

        # Show first few s3270 events
        if s3270_events:
            print(f"\nFirst {min(5, len(s3270_events))} events:")
            for i, event in enumerate(s3270_events[:5]):
                direction = event["direction"]
                size = event["size"]
                hex_preview = event["hex"][:40] + (
                    "..." if len(event["hex"]) > 40 else ""
                )
                print(f"  {i+1}. {direction:6} {size:4} bytes: {hex_preview}")

        print("\n🔍 COMPARISON ANALYSIS")
        print("-" * 80)

        # Connection status
        if pure3270_data.get("connected"):
            print("✓ pure3270 connected successfully")
        else:
            print("✗ pure3270 connection failed")
            if "error" in pure3270_data:
                print(f"  Error: {pure3270_data['error']}")

        # Screen data comparison
        if pure3270_data.get("screen_data"):
            print(f"✓ pure3270 received screen data")
        else:
            print("✗ pure3270 did not receive screen data")

        # Event count comparison
        pure_count = results["pure3270_trace_count"]
        s3270_count = results["s3270_event_count"]

        if pure_count > 0 and s3270_count > 0:
            ratio = pure_count / s3270_count
            print(f"\nEvent count ratio (pure3270/s3270): {ratio:.2f}")
            if ratio < 0.5:
                print("  ⚠️  pure3270 captured significantly fewer events")
            elif ratio > 2.0:
                print("  ⚠️  pure3270 captured significantly more events")
            else:
                print("  ✓ Event counts are comparable")


async def main():
    """Main comparison workflow."""

    # Parse command line
    host = sys.argv[1] if len(sys.argv) > 1 else "66.189.134.90"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 2323

    # Check for trace file argument
    trace_file = None
    for i, arg in enumerate(sys.argv):
        if arg == "--trace-file" and i + 1 < len(sys.argv):
            trace_file = sys.argv[i + 1]

    if not trace_file:
        # Default to ra_test trace since we just fixed RA
        trace_file = "/workspaces/pure3270/tests/data/traces/ra_test.trc"

    print(f"Comparing pure3270 and s3270 trace handling")
    print(f"Host: {host}:{port}")
    print(f"S3270 trace file: {trace_file}")

    # Parse s3270 trace
    print("\n📂 Parsing s3270 trace file...")
    s3270_parser = S3270TraceParser(trace_file)
    s3270_events = s3270_parser.parse()
    print(f"   Parsed {len(s3270_events)} events from s3270 trace")

    # Capture pure3270 trace
    print("\n🔌 Connecting with pure3270 and capturing trace...")
    capture = Pure3270TraceCapture()
    pure3270_data = await capture.connect_and_capture(host, port)
    print(
        f"   Captured {len(pure3270_data.get('trace_events', []))} events from pure3270"
    )

    # Compare
    print("\n🔬 Analyzing differences...")
    comparator = TraceComparator()
    results = comparator.compare_protocol_handling(pure3270_data, s3270_events)

    # Print results
    comparator.print_comparison(results, pure3270_data, s3270_events)

    print("\n" + "=" * 80)
    print("Comparison complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
