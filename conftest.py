import asyncio
import socket
import pytest
import pytest_asyncio

from integration_test import TN3270ENegotiatingMockServer


@pytest_asyncio.fixture
async def port():
    """Get an available port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest_asyncio.fixture
async def mock_server(port):
    """Create a mock TN3270 server for testing."""
    server = TN3270ENegotiatingMockServer(port=port)
    server.rows = 24
    server.cols = 80
    server.bind_image_sent = asyncio.Event()

    task = asyncio.create_task(server.start())
    await asyncio.sleep(0.1)  # Give server time to start

    yield server

    # Cleanup
    try:
        await server.stop()
    except Exception:
        pass
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass