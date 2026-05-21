"""Echo server scenario - echoes received data."""

import asyncio

from mock_server.tn3270_mock_server import TN3270MockServer
from pure3270.protocol.utils import IAC, TELOPT_EOR, WILL


class EchoServer(TN3270MockServer):
    """Simple echo server for protocol debugging."""

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        writer.write(bytes([IAC, WILL, TELOPT_EOR]))
        await writer.drain()

        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
