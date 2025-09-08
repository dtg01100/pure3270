import asyncio
import telnetlib3

async def test():
    try:
        reader, writer = await asyncio.open_connection('localhost', 23)
        client = telnetlib3.TelnetClient(reader, writer, encoding='latin1', force_binary=True)
        print('Has _transport?', hasattr(client, '_transport'))
        print('Transport type:', type(client._transport))
        print('Transport has write?', hasattr(client._transport, 'write'))
        # Send
        client._transport.write(b'\xff\xfd\x27')
        print('Wrote via transport')
        # Read
        data = await client._reader.readuntil(b'\xff', timeout=1.0)
        print('Read data length:', len(data))
        # Close
        client.close()
        await client.wait_closed()
        print('Closed')
    except Exception as e:
        print('Error:', e)

asyncio.run(test())