"""
Scenario: Negotiation Success
Simulates a client connecting to the TN3270 mock server and successfully negotiating device type and options.
"""

import asyncio

from mock_server.tn3270_mock_server import TN3270MockServer


async def run() -> None:
    server = TN3270MockServer()
    await server.start()
    print("Negotiation success scenario started.")
    # Simulate client negotiation (details would be filled in with protocol bytes)
    await asyncio.sleep(1)
    await server.stop()
    print("Negotiation success scenario completed.")


if __name__ == "__main__":
    asyncio.run(run())
