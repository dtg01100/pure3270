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
