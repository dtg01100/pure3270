"""Example: Using the negotiation trace recorder.

Run with:
    python examples/example_trace.py HOST [PORT]

If HOST is omitted it will attempt a mock / unreachable host and still show
that initial negotiation events may be recorded (depending on availability).
"""

import asyncio
import sys

from pure3270 import AsyncSession


def print_events(events):
    if not events:
        print(
            "No events recorded (enable_trace may be False or negotiation not started)."
        )
        return
    print("Recorded negotiation events:")
    for e in events:
        print(f"  {e.ts:7.3f}s  {e.kind:9}  {e.details}")


async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "mock-tn3270-host.example.com"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 23

    async with AsyncSession(enable_trace=True) as session:
        try:
            await session.connect(host, port)
        except Exception as exc:  # Connection may fail in offline environments
            print(f"Connection attempt failed: {exc}")
        finally:
            events = session.get_trace_events()
            print_events(events)


if __name__ == "__main__":
    asyncio.run(main())
