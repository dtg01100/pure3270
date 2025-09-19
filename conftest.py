import asyncio
import sys
import pytest
import pytest_asyncio
from pure3270.protocol.utils import (
    IAC, SB, SE, WILL, DO, DONT, TELOPT_EOR, TELOPT_TN3270E
)

# Removed broken fixtures that reference non-existent TN3270ENegotiatingMockServer

# We now require Python >= 3.10; pytest-asyncio provides proper event loop handling
# so the manual event_loop fixture for older Python versions is no longer necessary.

class MockTN3270EServer:
    def __init__(self, success: bool = True):
        self.success = success
        self.server = None
        self.task = None

    async def __aenter__(self):
        self.server = await asyncio.start_server(self.handle_client, '127.0.0.1', 2323)
        self.task = asyncio.create_task(self.server.serve_forever())
        await asyncio.sleep(0.1)  # Give time to start
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def handle_client(self, reader, writer):
        try:
            # Expect client to send WILL TN3270E first
            data = await reader.readexactly(3)
            if data != bytes([IAC, WILL, TELOPT_TN3270E]):
                writer.close()
                await writer.wait_closed()
                return

            # Send WILL EOR (common in both modes)
            writer.write(bytes([IAC, WILL, TELOPT_EOR]))
            await writer.drain()

            if self.success:
                # Send DO TN3270E
                writer.write(bytes([IAC, DO, TELOPT_TN3270E]))
                await writer.drain()

                # Wait for SB DEVICE-TYPE REQUEST
                # Expect IAC SB TN3270E DEVICE_TYPE REQUEST "IBM-..." IAC SE
                data = await reader.readuntil(bytes([SE]))
                if b'\xff\xfa' + bytes([TELOPT_TN3270E, TN3270E_DEVICE_TYPE, 1]) not in data:
                    # If not matching, close
                    writer.close()
                    await writer.wait_closed()
                    return

                # Send SB FUNCTIONS IS (BIND-IMAGE and EOR)
                functions_sb = bytes([IAC, SB, TELOPT_TN3270E, TN3270E_IS, 0, 1, 0, 7, 1, IAC, SE])
                writer.write(functions_sb)
                await writer.drain()

                # Send SB REQUEST (no response flag)
                request_sb = bytes([IAC, SB, TELOPT_TN3270E, TN3270E_REQUEST, 0, 0, 0, 0, IAC, SE])
                await asyncio.sleep(0.1)
                writer.write(request_sb)
                await writer.drain()

                # Optionally send NVT_DATA or keep open
                await asyncio.sleep(0.5)  # Allow client to process

            else:
                # Fallback: Send DONT TN3270E
                writer.write(bytes([IAC, DONT, TELOPT_TN3270E]))
                await writer.drain()

            # Keep connection open for session.close()
            while True:
                data = await reader.read(1024)
                if len(data) == 0:
                    break
                # Echo or handle further, but for test, no need
        except asyncio.IncompleteReadError:
            pass  # Client closed
        except Exception as e:
            print(f"Mock server error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def mock_tn3270e_server():
    server = MockTN3270EServer(success=True)
    async with server:
        yield server

@pytest_asyncio.fixture(scope="session")
async def mock_tn3270e_server_fallback():
    server = MockTN3270EServer(success=False)
    async with server:
        yield server
