import asyncio
import telnetlib3

async def test():
    try:
        reader, writer = await asyncio.open_connection('localhost', 23)
        client = telnetlib3.TelnetClient(reader, writer)
        print('Client created:', type(client))
        print('Has write?', hasattr(client, 'write'))
        print('Has read_until?', hasattr(client, 'read_until'))
        # Send something
        await client.write(b'\xff\xfd\x27')  # DO TN3270
        print('Wrote data')
        # Read
        data = await client.read_until(b'\xff', timeout=1.0)
        print('Read data length:', len(data))
        # Close
        client.close()
        await client.wait_closed()
        print('Closed')
    except Exception as e:
        print('Error:', e)

asyncio.run(test())