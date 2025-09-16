import asyncio
import time

from integration_test import BindImageMockServer


async def capture(timeout=6.0):
    server = BindImageMockServer()
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.1)  # give server time to start

    from pure3270.protocol.utils import (IAC, SB, SE, TELOPT_TN3270E,
                                         TN3270E_DEVICE_TYPE, TN3270E_SEND)

    reader = writer = None
    collected = bytearray()
    try:
        reader, writer = await asyncio.open_connection('localhost', server.port)

        # Send DEVICE-TYPE SEND subnegotiation
        msg = bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_SEND, IAC, SE])
        writer.write(msg)
        await writer.drain()

        # Read until timeout, collecting data. Exit early if we see expected markers.
        start = time.time()
        while time.time() - start < timeout:
            try:
                chunk = await asyncio.wait_for(reader.read(4096), timeout=0.5)
            except asyncio.TimeoutError:
                # no data in this slice, continue until overall timeout
                continue
            if not chunk:
                break
            collected.extend(chunk)
            # If we see IAC SB TELOPT_TN3270E or a Structured Field (0x3C) or TN3270E header (0x00 0x00), exit early
            if b'\xff\xfa' in collected or b'\x3c' in collected or collected.find(b'\x00\x00') != -1:
                break
        return collected
    finally:
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        # Stop server
        try:
            await server.stop()
        except Exception:
            pass
        server_task.cancel()

if __name__ == '__main__':
    data = asyncio.run(capture())
    print('\nCollected (hex):')
    print(data.hex())
