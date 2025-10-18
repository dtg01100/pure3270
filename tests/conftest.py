import asyncio
import logging
import platform
import resource

# Patching support removed or unavailable; provide lightweight no-op
# stubs for tests that referenced MonkeyPatchManager/PatchContext.
from contextlib import contextmanager
from logging import NullHandler
from unittest.mock import AsyncMock, MagicMock, Mock
from unittest.mock import patch as mock_patch  # noqa: F401

import pytest
import pytest_asyncio

from pure3270.emulation.ebcdic import EBCDICCodec
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.session import AsyncSession


class MonkeyPatchManager:
    """No-op monkey patch manager used when patching is disabled.

    Tests only require a manager object to exist; this minimal
    implementation avoids importing the full patching module.
    """

    def _apply_module_patch(self, module_name, replacement):
        return None

    def _apply_method_patch(self, target, method_name, new_method):
        return None

    def revert_all(self):
        return None


@contextmanager
def PatchContext():
    mgr = MonkeyPatchManager()
    try:
        yield mgr
    finally:
        mgr.revert_all()


from pure3270.protocol.data_stream import DataStreamParser, DataStreamSender
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.ssl_wrapper import SSLWrapper
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.session import Session


@pytest.fixture
def data_stream_parser(screen_buffer):
    """Fixture providing a real DataStreamParser with real screen buffer."""
    return DataStreamParser(screen_buffer)


@pytest.fixture
def data_stream_sender():
    """Fixture providing a DataStreamSender."""
    return DataStreamSender()


@pytest.fixture
def negotiator(screen_buffer):
    """Fixture providing a real Negotiator with mocked writer only."""
    # Use real Negotiator with real parser and screen buffer for better testing
    # Only mock the writer for network I/O operations
    mock_writer = AsyncMock()
    parser = DataStreamParser(screen_buffer)
    negotiator = Negotiator(
        writer=mock_writer,
        parser=parser,
        screen_buffer=screen_buffer,
        handler=None,  # Will be set by tests that need it
        is_printer_session=False,
    )
    return negotiator


@pytest.fixture
def ebcdic_codec():
    """Fixture providing an EBCDICCodec."""
    return EBCDICCodec()


@pytest.fixture
def ssl_wrapper():
    """Fixture providing an SSLWrapper."""
    return SSLWrapper()


@pytest_asyncio.fixture
async def real_async_session():
    """Fixture providing a real AsyncSession with real TN3270Handler for better test coverage."""
    from pure3270.emulation.screen_buffer import ScreenBuffer
    from pure3270.protocol.data_stream import DataStreamParser
    from pure3270.protocol.negotiator import Negotiator
    from pure3270.protocol.tn3270_handler import TN3270Handler

    # Create real components
    screen_buffer = ScreenBuffer(rows=24, cols=80)
    session = AsyncSession("localhost", 23)

    # Create real handler with real components but mocked I/O
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()

    # Set up minimal mock responses for basic operation
    mock_reader.readexactly.return_value = b"\xff\xfb\x27"  # IAC WILL TN3270E
    mock_reader.read.return_value = b"\x28\x00\x01\x00"  # Basic response

    parser = DataStreamParser(screen_buffer)
    negotiator = Negotiator(
        writer=mock_writer,
        parser=parser,
        screen_buffer=screen_buffer,
        handler=None,  # Will be set below
        is_printer_session=False,
    )

    handler = TN3270Handler(
        reader=mock_reader,
        writer=mock_writer,
        screen_buffer=screen_buffer,
        is_printer_session=False,
    )
    handler.negotiator = negotiator
    negotiator.handler = handler

    # Set up session with real handler
    session._handler = handler

    return session


@pytest.fixture
def screen_buffer():
    """Fixture providing a real ScreenBuffer for more accurate testing."""
    # Use real ScreenBuffer instead of mock for better test coverage
    screen_buffer = ScreenBuffer(rows=24, cols=80)
    return screen_buffer


def pytest_configure(config):
    config.option.log_cli_level = "INFO"


@pytest.fixture
def tn3270_handler():
    """Fixture providing a TN3270Handler with mocked dependencies."""
    from unittest.mock import AsyncMock

    # Mock the reader and writer
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()

    # Create a real TN3270Handler instance with mocked reader/writer
    screen_buffer = ScreenBuffer(rows=24, cols=80)
    handler = TN3270Handler(
        reader=mock_reader,
        writer=mock_writer,
        screen_buffer=screen_buffer,
        host="test-host",
        port=23,
    )

    return handler


@pytest.fixture(autouse=True)
def suppress_logging():
    logger = logging.getLogger()
    old_handlers = logger.handlers[:]
    null_handler = NullHandler()
    logger.addHandler(null_handler)
    yield
    # Remove only the NullHandler we added
    try:
        logger.removeHandler(null_handler)
    except ValueError:
        pass
    # Restore any handlers that were removed during the test
    current_handlers = logger.handlers[:]
    for h in old_handlers:
        if h not in current_handlers:
            logger.addHandler(h)
    # Optionally, remove any handlers that were not present before
    for h in logger.handlers[:]:
        if h not in old_handlers:
            logger.removeHandler(h)


@pytest.fixture
def memory_limit_500mb():
    """Fixture to limit memory to 500MB for the duration of the test."""
    if platform.system() == "Linux":
        try:
            # Set memory limit to 500MB (in bytes)
            resource.setrlimit(
                resource.RLIMIT_AS, (500 * 1024 * 1024, 500 * 1024 * 1024)
            )
        except (ValueError, OSError):
            # If we can't set the limit, just continue
            pass
    yield
    if platform.system() == "Linux":
        try:
            # Reset to unlimited
            resource.setrlimit(
                resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
            )
        except (ValueError, OSError):
            pass


@pytest.fixture
def memory_limit_100mb():
    """Fixture to limit memory to 100MB for the duration of the test."""
    if platform.system() == "Linux":
        try:
            # Set memory limit to 100MB (in bytes)
            resource.setrlimit(
                resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024)
            )
        except (ValueError, OSError):
            # If we can't set the limit, just continue
            pass
    yield
    if platform.system() == "Linux":
        try:
            # Reset to unlimited
            resource.setrlimit(
                resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
            )
        except (ValueError, OSError):
            pass


async def mock_tn3270e_handle_success(reader, writer):
    try:
        # Send IAC DO TN3270E
        writer.write(b"\xff\xfd\x1b")
        await writer.drain()

        # Wait for client's IAC WILL TN3270E
        data = await reader.readexactly(3)

        # Send SB TN3270E DEVICE-TYPE REQUEST
        request_sb = b"\xff\xfa\x1b\x00\x01\xff\xf0"
        writer.write(request_sb)
        await writer.drain()

        # Wait for client's SB TN3270E DEVICE-TYPE RESPONSE (IBM-3278-2-E)
        # Full SB: \xff\xfa\x1b \x00 \x02 IBM-3278-2-E \xff\xf0 ~ 18 bytes
        sb_data = await reader.read(20)  # Read up to 20 bytes for SB

        # Send SB TN3270E FUNCTIONS (BIND-IMAGE EOR)
        functions_sb = b"\xff\xfa\x1b\x02\x00\x01\x00\x07\x01\xff\xf0"
        writer.write(functions_sb)
        await writer.drain()

        # Send sample TN3270E data: header + Write + full screen spaces + EOR
        header = b"\x00\x00\x00\x00"  # Type 0, flags 0, seq 0, hlen 0
        screen_size = 24 * 80  # 1920
        simple_data = (
            b"\xf5" + b"\x40" * screen_size + b"\x19"
        )  # Write + spaces + EOR (0x19 for EOR)
        writer.write(header + simple_data)
        await writer.drain()

        # Keep open for test to read
        await asyncio.sleep(5)

    except Exception as e:
        logging.getLogger(__name__).error(f"Mock server error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def mock_tn3270e_handle_fallback(reader, writer):
    try:
        # Send IAC DONT TN3270E
        writer.write(b"\xff\xfe\x1b")
        await writer.drain()

        # Optionally send some basic Telnet or VT100, but for fallback, just wait
        await asyncio.sleep(5)

    except Exception as e:
        logging.getLogger(__name__).error(f"Mock server error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


@pytest_asyncio.fixture
async def mock_tn3270e_server():
    """Async fixture for successful TN3270E mock server."""
    server = await asyncio.start_server(mock_tn3270e_handle_success, "127.0.0.1", 2323)
    serve_task = asyncio.create_task(server.serve_forever())
    try:
        yield server
    finally:
        serve_task.cancel()
        server.close()
        await server.wait_closed()
        await serve_task


@pytest_asyncio.fixture
async def mock_tn3270e_server_fallback():
    """Async fixture for fallback TN3270E mock server (sends DONT)."""
    server = await asyncio.start_server(mock_tn3270e_handle_fallback, "127.0.0.1", 2324)
    serve_task = asyncio.create_task(server.serve_forever())
    try:
        yield server
    finally:
        serve_task.cancel()
        server.close()
        await server.wait_closed()
        await serve_task


@pytest.fixture
def mock_async_writer():
    """Fixture providing a mock async writer for tests."""
    from unittest.mock import AsyncMock

    return AsyncMock()


@pytest.fixture
def mock_negotiator_handler():
    """Fixture providing a mock handler for negotiator tests."""
    from unittest.mock import MagicMock

    handler = MagicMock()
    handler._update_session_state_from_sna_response = MagicMock()
    return handler
