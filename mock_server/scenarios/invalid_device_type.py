"""
Scenario: Invalid Device Type
Simulates a client requesting an unknown device type from the TN3270 mock server.
"""

import asyncio

from mock_server.tn3270_mock_server import TN3270MockServer


async def run() -> None:
    server = TN3270MockServer()
    await server.start()
    print("Invalid device type scenario started.")
    # Simulate client requesting unknown device type
    await asyncio.sleep(1)
    await server.stop()
    print("Invalid device type scenario completed.")


if __name__ == "__main__":
    asyncio.run(run())
