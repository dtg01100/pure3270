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
def screen_buffer():
    mock = Mock(spec=ScreenBuffer, rows=24, cols=80)
    handler = Mock()
    type(mock).handler = PropertyMock(return_value=handler)
    type(handler).negotiator = PropertyMock(return_value=Mock(spec=Negotiator))
    handler.send_data = AsyncMock()
    handler.receive_data = AsyncMock(return_value=b"")
    type(mock).connected = PropertyMock(return_value=True)
    type(mock).set_position = Mock()
    mock.buffer = bytearray(b"\x40" * (24 * 80))
    mock.fields = []
    mock.connected = True
    mock.set_position = Mock()
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


@pytest.fixture
async def port():
    """Get an available port for testing."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture
async def mock_server(port):
    """Create a mock TN3270 server for testing."""
    from integration_test import TN3270ENegotiatingMockServer

    server = TN3270ENegotiatingMockServer(port=port)
    server.rows = 24
    server.cols = 80
    server.bind_image_sent = asyncio.Event()

    # Start server properly
    await server.start()

    yield server

    # Cleanup
    try:
        await server.stop()
    except Exception:
        pass


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
