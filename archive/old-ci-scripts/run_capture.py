import asyncio
import time

from integration_test import BindImageMockServer


async def capture():
    server = BindImageMockServer()
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.1)

    # Import telnet/tn3270 constants from package
    from pure3270.protocol.utils import (DO, IAC, TELOPT_BINARY, TELOPT_EOR,
                                         TELOPT_TN3270E, TELOPT_TTYPE, WILL)

    reader, writer = await asyncio.open_connection("localhost", server.port)
    try:
        # Send several WILL options to trigger server behavior
        opts = [TELOPT_TN3270E, TELOPT_TTYPE, TELOPT_BINARY, TELOPT_EOR]
        for opt in opts:
            msg = bytes([IAC, WILL, opt])
            writer.write(msg)
            await writer.drain()
            print(f"Client: sent {msg.hex()}")
            await asyncio.sleep(0.05)

        # Also send a DO for TN3270E to simulate client acceptance
        writer.write(bytes([IAC, DO, TELOPT_TN3270E]))
        await writer.drain()
        print(f"Client: sent DO tn3270e")

        # Read incoming bytes for a short period
        start = time.time()
        collected = bytearray()
        while time.time() - start < 5.0:
            await asyncio.sleep(0.05)
            try:
                data = await asyncio.wait_for(reader.read(4096), timeout=0.2)
            except asyncio.TimeoutError:
                continue
            if not data:
                break
            collected.extend(data)
            print(f"Client: received: {data.hex()}")

        print("\n--- Final collected bytes (hex) ---")
        print(collected.hex())

    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        server_task.cancel()
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(capture())
