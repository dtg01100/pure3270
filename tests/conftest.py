import asyncio
import logging
import platform
import resource
from logging import NullHandler
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock
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
    """Fixture providing a DataStreamParser with mocked screen buffer."""
    return DataStreamParser(screen_buffer)


@pytest.fixture
def data_stream_sender():
    """Fixture providing a DataStreamSender."""
    return DataStreamSender()


@pytest.fixture
def negotiator(screen_buffer):
    """Fixture providing a Negotiator with mocked dependencies."""
    parser = Mock(spec=DataStreamParser)
    return Negotiator(None, parser, screen_buffer)


@pytest.fixture
def ebcdic_codec():
    """Fixture providing an EBCDICCodec."""
    return EBCDICCodec()


@pytest.fixture
def async_session():
    """Fixture providing an AsyncSession."""
    session = AsyncSession()
    # Mock the screen buffer
    session.screen = Mock(spec=ScreenBuffer)
    session.screen.buffer = bytearray(b"\x40" * (24 * 80))
    session.screen.fields = []
    return session


@pytest.fixture
def screen_buffer():
    mock = Mock(spec=ScreenBuffer, rows=24, cols=80)
    handler = Mock()
    type(mock).handler = PropertyMock(return_value=handler)
    type(handler).negotiator = PropertyMock(return_value=Mock(spec=Negotiator))
    handler.send_data = AsyncMock()
    handler.receive_data = AsyncMock(return_value=b"")
    type(mock).connected = PropertyMock(return_value=True)
    
    # Fix get_position to return a proper tuple
    mock.get_position = Mock(return_value=(0, 0))
    mock.set_position = Mock()
    
    mock.buffer = bytearray(b"\x40" * (24 * 80))
    mock.fields = []
    mock.connected = True
    return mock


def pytest_configure(config):
    config.option.log_cli_level = "INFO"


@pytest.fixture
def tn3270_handler():
    from unittest.mock import AsyncMock

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    try:
        handler = TN3270Handler(mock_reader, mock_writer)
        handler.negotiator = Mock()
        handler.negotiator._ascii_mode = False
        # Mock the SNA session state properly
        from pure3270.protocol.negotiator import SnaSessionState
        handler.negotiator._sna_session_state = SnaSessionState.NORMAL
        # Mock current_sna_session_state as a property that returns the _sna_session_state
        type(handler.negotiator).current_sna_session_state = PropertyMock(
            return_value=SnaSessionState.NORMAL
        )
        handler.connected = True
        inner_handler = Mock()
        type(handler).handler = PropertyMock(return_value=inner_handler)
        type(inner_handler).negotiator = PropertyMock(
            return_value=Mock(spec=Negotiator)
        )
        inner_handler.send_data = AsyncMock()
        inner_handler.receive_data = AsyncMock(return_value=b"")
        type(handler).connected = PropertyMock(return_value=True)
    except ValueError:
        handler = Mock(spec=TN3270Handler)
        handler.negotiator = Mock()
        handler.negotiator._ascii_mode = False
        # Mock the SNA session state properly for fallback case
        from pure3270.protocol.negotiator import SnaSessionState
        mock_sna_state = Mock()
        mock_sna_state.value = SnaSessionState.NORMAL.value
        handler.negotiator.current_sna_session_state = mock_sna_state
        handler.connected = True
        inner_handler = Mock()
        type(handler).handler = PropertyMock(return_value=inner_handler)
        type(inner_handler).negotiator = PropertyMock(
            return_value=Mock(spec=Negotiator)
        )
        inner_handler.send_data = AsyncMock()
        inner_handler.receive_data = AsyncMock(return_value=b"")
        type(handler).connected = PropertyMock(return_value=True)
    return handler


@pytest.fixture(autouse=True)
def suppress_logging():
    logger = logging.getLogger()
    old_handlers = logger.handlers[:]
    logger.addHandler(NullHandler())
    yield
    for h in logger.handlers:
        if isinstance(h, NullHandler):
            logger.removeHandler(h)
    logger.handlers = old_handlers


@pytest.fixture
def memory_limit_500mb():
    """Fixture to limit memory to 500MB for the duration of the test."""
    if platform.system() == 'Linux':
        try:
            # Set memory limit to 500MB (in bytes)
            resource.setrlimit(resource.RLIMIT_AS, (500 * 1024 * 1024, 500 * 1024 * 1024))
        except (ValueError, OSError):
            # If we can't set the limit, just continue
            pass
    yield
    if platform.system() == 'Linux':
        try:
            # Reset to unlimited
            resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        except (ValueError, OSError):
            pass


@pytest.fixture
def memory_limit_100mb():
    """Fixture to limit memory to 100MB for the duration of the test."""
    if platform.system() == 'Linux':
        try:
            # Set memory limit to 100MB (in bytes)
            resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))
        except (ValueError, OSError):
            # If we can't set the limit, just continue
            pass
    yield
    if platform.system() == 'Linux':
        try:
            # Reset to unlimited
            resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        except (ValueError, OSError):
            pass
