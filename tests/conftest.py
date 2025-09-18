import asyncio
import logging
import platform
import resource
from logging import NullHandler
from unittest.mock import AsyncMock, MagicMock, Mock
from unittest.mock import patch as mock_patch  # noqa: F401

import pytest

from pure3270.emulation.ebcdic import EBCDICCodec
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.patching.patching import MonkeyPatchManager, PatchContext
from pure3270.protocol.data_stream import DataStreamParser, DataStreamSender
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.ssl_wrapper import SSLWrapper
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.session import AsyncSession, Session


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


@pytest.fixture
def async_session():
    """Fixture providing an AsyncSession with mocked components."""
    from unittest.mock import AsyncMock, PropertyMock

    from pure3270.emulation.screen_buffer import ScreenBuffer
    from pure3270.protocol.tn3270_handler import TN3270Handler

    # Create session
    session = AsyncSession("localhost", 23)

    # Create mock handler with proper properties
    mock_handler = AsyncMock(spec=TN3270Handler)
    mock_handler.screen_buffer = PropertyMock(return_value=ScreenBuffer())
    mock_handler.is_connected = PropertyMock(return_value=True)
    mock_handler.connected = True
    mock_handler.receive_data.return_value = b"test data"

    # Set internal state
    session._handler = mock_handler
    session.connected = True
    session._transport = Mock()
    session._transport.perform_telnet_negotiation.return_value = None
    session._transport.perform_tn3270_negotiation.return_value = None

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
