import asyncio

from integration_test import BindImageMockServer
from pure3270.protocol.utils import (IAC, SB, SE, TELOPT_TN3270E,
                                     TN3270E_DEVICE_TYPE, TN3270E_SEND)


async def run():
    server = BindImageMockServer()
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.1)  # Give server time to bind

    reader, writer = await asyncio.open_connection("localhost", server.port)
    try:
        # Build subnegotiation: IAC SB TELOPT_TN3270E DEVICE_TYPE SEND IAC SE
        msg = bytes(
            [IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_SEND, IAC, SE]
        )
        writer.write(msg)
        await writer.drain()
        print("Client sent device-type SEND subnegotiation:", msg.hex())

        collected = bytearray()
        # Read incoming bytes for up to 3s
        try:
            while True:
                data = await asyncio.wait_for(reader.read(4096), timeout=0.5)
                if not data:
                    break
                print("Client received chunk:", data.hex())
                collected.extend(data)
        except asyncio.TimeoutError:
            pass

        print("\n--- Final collected bytes (hex) ---")
        print(collected.hex())
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        await server.stop()
        server_task.cancel()


if __name__ == "__main__":
    asyncio.run(run())
