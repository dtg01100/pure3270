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
def ssl_wrapper():
    """Fixture providing an SSLWrapper."""
    return SSLWrapper()


@pytest.fixture
def async_session():
    """Fixture providing an AsyncSession."""
    session = AsyncSession()
    # Mock the screen buffer using property setter
    mock_screen = Mock(spec=ScreenBuffer)
    session.screen = mock_screen
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
    def mock_get_position():
        return (mock.cursor_row, mock.cursor_col)

    mock.get_position = Mock(side_effect=mock_get_position)

    # Configure set_position to actually update cursor position
    def mock_set_position(row, col):
        mock.cursor_row = row
        mock.cursor_col = col

    mock.set_position = Mock(side_effect=mock_set_position)

    mock.buffer = bytearray(b"\x40" * (24 * 80))
    mock.fields = []
    mock.connected = True
    mock.size = 24 * 80
    mock.cursor_row = 0
    mock.cursor_col = 0

    # Configure read_modified_fields to return a list for tests that need it
    mock.read_modified_fields = Mock(return_value=[])

    # Configure write_char to actually update the buffer
    def mock_write_char(char, row, col):
        if 0 <= row < mock.rows and 0 <= col < mock.cols:
            pos = row * mock.cols + col
            if pos < len(mock.buffer):
                mock.buffer[pos] = char

    mock.write_char = Mock(side_effect=mock_write_char)

    # Configure move_cursor_to_first_input_field to actually move the cursor
    def mock_move_cursor_to_first_input_field():
        first_input_field = None
        for field in mock.fields:
            if not field.protected:
                first_input_field = field
                break
        if first_input_field:
            mock.cursor_row, mock.cursor_col = first_input_field.start

    mock.move_cursor_to_first_input_field = Mock(
        side_effect=mock_move_cursor_to_first_input_field
    )

    # Configure move_cursor_to_next_input_field to actually move the cursor
    def mock_move_cursor_to_next_input_field():
        current_pos_linear = mock.cursor_row * mock.cols + mock.cursor_col
        next_input_field = None

        # Sort fields by their linear start position to ensure correct traversal
        sorted_fields = sorted(
            mock.fields, key=lambda f: f.start[0] * mock.cols + f.start[1]
        )

        # Find the next input field after the current cursor position
        for field in sorted_fields:
            field_start_linear = field.start[0] * mock.cols + field.start[1]
            if field_start_linear > current_pos_linear and not field.protected:
                next_input_field = field
                break

        if next_input_field:
            mock.cursor_row, mock.cursor_col = next_input_field.start
        else:
            # If no next input field is found, wrap around to the first input field
            for field in sorted_fields:
                if not field.protected:
                    next_input_field = field
                    break

            if next_input_field:
                mock.cursor_row, mock.cursor_col = next_input_field.start

    mock.move_cursor_to_next_input_field = Mock(
        side_effect=mock_move_cursor_to_next_input_field
    )

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
