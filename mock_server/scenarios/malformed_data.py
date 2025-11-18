"""
Scenario: Malformed Data
Simulates client sending invalid or corrupted protocol bytes to the TN3270 mock server.
"""

import asyncio

from mock_server.tn3270_mock_server import TN3270MockServer


async def run() -> None:
    server = TN3270MockServer()
    await server.start()
    print("Malformed data scenario started.")
    # Simulate client sending malformed data
    await asyncio.sleep(1)
    await server.stop()
    print("Malformed data scenario completed.")


if __name__ == "__main__":
    asyncio.run(run())
