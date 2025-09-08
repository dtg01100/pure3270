import asyncio
import telnetlib3

async def test():
    try:
        result = await telnetlib3.open_connection('localhost', 23)
        print('Type of result:', type(result))
        print('Is tuple?', isinstance(result, tuple))
        if isinstance(result, tuple):
            print('Len:', len(result))
            print('Type of first:', type(result[0]))
            print('Has write?', hasattr(result[0], 'write'))
        else:
            print('Has write?', hasattr(result, 'write'))
        # Close
        if isinstance(result, tuple):
            result[1].close()
            await result[1].wait_closed()
        else:
            result.close()
            await result.wait_closed()
    except Exception as e:
        print('Error:', e)

asyncio.run(test())