import asyncio

async def safe_read(reader, n, timeout=1.0):
    """Read up to n bytes from reader with a timeout. Returns b'' on EOF, None on timeout."""
    try:
        data = await asyncio.wait_for(reader.read(n), timeout=timeout)
        return data
    except asyncio.TimeoutError:
        return None
