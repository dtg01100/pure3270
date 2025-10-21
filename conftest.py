import asyncio
import logging
import os
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch as _patch

import pytest
import pytest_asyncio

# Test configuration - allow override via environment variables
TEST_HOST = os.environ.get("PURE3270_TEST_HOST", "127.0.0.1")
TEST_PORT = int(os.environ.get("PURE3270_TEST_PORT", "2323"))
TEST_ALT_PORT = int(os.environ.get("PURE3270_TEST_ALT_PORT", "2324"))

from pure3270.protocol.utils import (
    DO,
    DONT,
    IAC,
    SB,
    SE,
    TELOPT_EOR,
    TELOPT_TN3270E,
    TELOPT_TTYPE,
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IS,
    TN3270E_REQUEST,
    TN3270E_SEND,
    WILL,
)

logger = logging.getLogger(__name__)

# Removed broken fixtures that reference non-existent TN3270ENegotiatingMockServer

# We now require Python >= 3.10; pytest-asyncio provides proper event loop handling
# so the manual event_loop fixture for older Python versions is no longer necessary.


class MockTN3270EServer:
    def __init__(self, success: bool = True):
        self.success = success
        self.server = None
        self.task = None

    async def __aenter__(self):
        self.server = await asyncio.start_server(
            self.handle_client, TEST_HOST, TEST_PORT
        )
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
            print("Mock server started handling client")
            print(
                f"TN3270E_DEVICE_TYPE = 0x{TN3270E_DEVICE_TYPE:02x}, TN3270E_SEND = 0x{TN3270E_SEND:02x}"
            )
            # First, handle telnet negotiation - expect WILL TTYPE
            data = await reader.readexactly(3)
            print(f"Mock server received telnet negotiation: {data.hex()}")
            if data == bytes([IAC, WILL, TELOPT_TTYPE]):
                # Send DO TTYPE
                writer.write(bytes([IAC, DO, TELOPT_TTYPE]))
                await writer.drain()
                print("Mock server sent DO TTYPE")

                # Wait for SB TTYPE IS response
                data = await reader.readuntil(bytes([SE]))
                print(f"Mock server received TTYPE response: {data.hex()}")

            # Send DO TN3270E to initiate TN3270E negotiation
            writer.write(bytes([IAC, DO, TELOPT_TN3270E]))
            await writer.drain()
            print("Mock server sent DO TN3270E")

            # Wait for client to respond with WILL TN3270E
            data = await reader.readexactly(3)
            print(f"Mock server received after DO TN3270E: {data.hex()}")
            if data != bytes([IAC, WILL, TELOPT_TN3270E]):
                print(f"Expected WILL TN3270E, got {data.hex()}")
                writer.close()
                await writer.wait_closed()
                return

            if self.success:
                # Wait a bit for client to complete telnet negotiation
                await asyncio.sleep(0.1)

                # Send DEVICE-TYPE SEND (RFC 2355: server initiates device type negotiation)
                device_type_send = bytes(
                    [
                        IAC,
                        SB,
                        TELOPT_TN3270E,
                        TN3270E_DEVICE_TYPE,
                        TN3270E_SEND,
                        IAC,
                        SE,
                    ]
                )
                print(f"About to send DEVICE-TYPE SEND: {device_type_send.hex()}")
                writer.write(device_type_send)
                await writer.drain()
                print(f"Mock server sent DEVICE-TYPE SEND: {device_type_send.hex()}")

                # Wait for DEVICE-TYPE IS response
                data = await reader.readuntil(bytes([SE]))
                print(f"Mock server received DEVICE-TYPE response: {data.hex()}")
                if (
                    b"\xff\xfa"
                    + bytes([TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_IS])
                    not in data
                ):
                    print(f"Unexpected DEVICE-TYPE response")
                    writer.close()
                    await writer.wait_closed()
                    return

                # Send SB FUNCTIONS IS (BIND-IMAGE and EOR)
                functions_sb = bytes(
                    [
                        IAC,
                        SB,
                        TELOPT_TN3270E,
                        TN3270E_FUNCTIONS,
                        TN3270E_IS,
                        0,
                        1,
                        0,
                        7,
                        1,
                        IAC,
                        SE,
                    ]
                )
                print(f"About to send FUNCTIONS IS: {functions_sb.hex()}")
                writer.write(functions_sb)
                await writer.drain()
                print(f"Mock server sent FUNCTIONS IS: {functions_sb.hex()}")

                # Send SB REQUEST (no response flag)
                request_sb = bytes(
                    [IAC, SB, TELOPT_TN3270E, TN3270E_REQUEST, 0, 0, 0, 0, IAC, SE]
                )
                await asyncio.sleep(0.1)
                print(f"About to send REQUEST: {request_sb.hex()}")
                writer.write(request_sb)
                await writer.drain()
                print(f"Mock server sent REQUEST: {request_sb.hex()}")

                # Optionally send NVT_DATA or keep open
                await asyncio.sleep(0.5)  # Allow client to process

            else:
                # Fallback: Send DONT TN3270E
                writer.write(bytes([IAC, DONT, TELOPT_TN3270E]))
                await writer.drain()

            # Keep connection open for session.close()
            max_iterations = 100  # Prevent infinite loops
            iteration_count = 0
            while iteration_count < max_iterations:
                iteration_count += 1
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=5.0)
                    if len(data) == 0:
                        break
                    # Echo or handle further, but for test, no need
                except asyncio.TimeoutError:
                    break  # Exit on timeout to prevent hanging
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
    logger.info("Starting mock TN3270E server fixture")
    server = MockTN3270EServer(success=True)
    async with server:
        logger.info("Mock TN3270E server started and ready")
        yield server
    logger.info("Mock TN3270E server fixture ended")


@pytest_asyncio.fixture(scope="session")
async def mock_tn3270e_server_fallback():
    server = MockTN3270EServer(success=False)
    async with server:
        yield server


# Minimal fallback for pytest-mock's 'mocker' fixture to avoid adding a dependency.
# Supports the subset used in tests: mocker.patch.object(obj, "attr").
@pytest.fixture()
def mocker():
    class _Mocker:
        def __init__(self):
            self._patchers = []

        def patch_object(self, target, attribute, new=None, **kwargs):
            # For async methods/coroutines, default to AsyncMock; otherwise MagicMock
            if new is None:
                # Attempt to detect if the target attribute is async
                try:
                    import inspect

                    target_attr = getattr(target, attribute, None)
                    if target_attr and inspect.iscoroutinefunction(target_attr):
                        new = AsyncMock()
                    else:
                        new = MagicMock()
                except Exception:
                    # Fallback to MagicMock if detection fails
                    new = MagicMock()

            patcher = _patch.object(target, attribute, new, **kwargs)
            mocked = patcher.start()
            self._patchers.append(patcher)
            return mocked

        @property
        def patch(self):
            outer = self

            class _PatchNamespace:
                def object(self, target, attribute, new=None, **kwargs):
                    return outer.patch_object(target, attribute, new=new, **kwargs)

            return _PatchNamespace()

        def stopall(self):
            for p in reversed(self._patchers):
                try:
                    p.stop()
                except Exception:
                    pass
            self._patchers.clear()

    m = _Mocker()
    try:
        yield m
    finally:
        m.stopall()
