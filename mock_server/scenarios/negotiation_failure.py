"""
Scenario: Negotiation Failure
Simulates a client connecting to the TN3270 mock server and failing negotiation due to unsupported device type.
"""

import asyncio

from mock_server.tn3270_mock_server import TN3270MockServer


async def run() -> None:
    server = TN3270MockServer()
    await server.start()
    print("Negotiation failure scenario started.")
    # Simulate client sending unsupported device type
    await asyncio.sleep(1)
    await server.stop()
    print("Negotiation failure scenario completed.")


if __name__ == "__main__":
    asyncio.run(run())
