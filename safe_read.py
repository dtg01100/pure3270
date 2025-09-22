"""
Safe read utility for asyncio streams with timeout support.
"""

import asyncio
from typing import Optional


async def safe_read(
    reader: asyncio.StreamReader,
    n: int,
    timeout: float = 5.0
) -> bytes:
    """
    Safely read data from an asyncio StreamReader with timeout.

    Args:
        reader: The asyncio StreamReader to read from
        n: Maximum number of bytes to read
        timeout: Timeout in seconds (default 5.0)

    Returns:
        The bytes read from the stream

    Raises:
        asyncio.TimeoutError: If the read operation times out
        ConnectionError: If the connection is lost during read
    """
    try:
        data = await asyncio.wait_for(reader.read(n), timeout=timeout)
        return data
    except asyncio.TimeoutError:
        raise asyncio.TimeoutError(f"Read timeout after {timeout} seconds")
    except ConnectionResetError:
        raise ConnectionError("Connection reset during read")
    except Exception as e:
        raise ConnectionError(f"Read error: {e}")
