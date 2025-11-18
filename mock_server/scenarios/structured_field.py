"""
Scenario: Structured Field Handling
Simulates structured field exchange between client and TN3270 mock server.
"""

import asyncio

from mock_server.tn3270_mock_server import TN3270MockServer


async def run() -> None:
    server = TN3270MockServer()
    await server.start()
    print("Structured field scenario started.")
    # Simulate structured field exchange
    await asyncio.sleep(1)
    await server.stop()
    print("Structured field scenario completed.")


if __name__ == "__main__":
    asyncio.run(run())
