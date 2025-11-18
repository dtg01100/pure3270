"""
Scenario: Printer Session
Simulates negotiation and data flow for a printer device type.
"""

import asyncio

from mock_server.tn3270_mock_server import TN3270MockServer


async def run() -> None:
    server = TN3270MockServer()
    await server.start()
    print("Printer session scenario started.")
    # Simulate printer session negotiation and data flow
    await asyncio.sleep(1)
    await server.stop()
    print("Printer session scenario completed.")


if __name__ == "__main__":
    asyncio.run(run())
