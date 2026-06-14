"""Negotiation failure scenario - refuses EOR."""

import asyncio

from mock_server.tn3270_mock_server import TN3270MockServer
from pure3270.protocol.utils import IAC, TELOPT_EOR, WONT


class NegotiationFailureServer(TN3270MockServer):
    """Server that refuses EOR - tests error handling."""

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        writer.write(bytes([IAC, WONT, TELOPT_EOR]))
        await writer.drain()
        await asyncio.sleep(0.1)
        writer.close()


async def run() -> None:
    """Exercise the NegotiationFailureServer end-to-end.

    The test harness in ``mock_server/test_scenarios.py`` imports
    each scenario module and calls its ``run()`` coroutine. The class
    above is the canonical implementation; this wrapper spins up an
    instance so the test does not need to special-case class-based
    scenarios.
    """
    server = NegotiationFailureServer()
    await server.start()
    try:
        await asyncio.sleep(0.5)
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(run())
