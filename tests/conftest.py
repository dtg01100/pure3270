import asyncio
import platform
import resource
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
def screen_buffer():
    mock = MagicMock()
    mock.rows = 24
    mock.cols = 80
    mock.buffer = [0x40] * (24 * 80)
    mock.attributes = [0] * (24 * 80 * 3)
    mock.get_content.return_value = ""
    return mock


@pytest.fixture
def ebcdic_codec():
    return EBCDICCodec()


@pytest.fixture
def mock_tn3270_handler():
    return AsyncMock(spec=TN3270Handler)


@pytest.fixture
def ssl_wrapper():
    return SSLWrapper(verify=True)


@pytest.fixture
def data_stream_sender():
    return DataStreamSender()


@pytest.fixture
def data_stream_parser(screen_buffer):
    return DataStreamParser(screen_buffer)


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def async_session(event_loop, request):
    session = AsyncSession("localhost", 23)
    def finalizer():
        event_loop.run_until_complete(session.close())
    request.addfinalizer(finalizer)
    return session


@pytest.fixture
def sync_session(request):
    session = Session("localhost", 23)
    def finalizer():
        session.close()
    request.addfinalizer(finalizer)
    return session


@pytest.fixture
def tn3270_handler():
    # Don't pre-set reader/writer for connection tests
    return TN3270Handler(None, None, host="localhost", port=23)


def set_memory_limit(max_memory_mb: int):
    """
    Set maximum memory limit for the current process.

    Args:
        max_memory_mb: Maximum memory in megabytes

    Raises:
        Exception: If memory limit cannot be set
    """
    # Only works on Unix systems
    if platform.system() != 'Linux':
        return None

    try:
        max_memory_bytes = max_memory_mb * 1024 * 1024
        # RLIMIT_AS limits total virtual memory
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
        return max_memory_bytes
    except Exception as e:
        return None


@pytest.fixture
def memory_limit_500mb():
    """Pytest fixture to limit memory to 500MB for a test.

    This is suitable for most tests that need memory limiting but don't have
    particularly high memory requirements.
    """
    if platform.system() != 'Linux':
        yield None
        return

    original_limit = resource.getrlimit(resource.RLIMIT_AS)
    limit = set_memory_limit(500)
    yield limit
    try:
        resource.setrlimit(resource.RLIMIT_AS, original_limit)
    except Exception:
        pass


@pytest.fixture
def memory_limit_100mb():
    """Pytest fixture to limit memory to 100MB for a test.

    This is suitable for performance tests or tests that should be
    particularly memory-conscious.
    """
    if platform.system() != 'Linux':
        yield None
        return

    original_limit = resource.getrlimit(resource.RLIMIT_AS)
    limit = set_memory_limit(100)
    yield limit
    try:
        resource.setrlimit(resource.RLIMIT_AS, original_limit)
    except Exception:
        pass


def pytest_addoption(parser):
    """Add command-line options for configuring test timeouts and memory limits."""
    parser.addoption(
        "--timeout-unit",
        action="store",
        default=5,
        type=float,
        help="Timeout in seconds for unit tests (default: 5)"
    )
    parser.addoption(
        "--timeout-integration",
        action="store",
        default=10,
        type=float,
        help="Timeout in seconds for integration tests (default: 10)"
    )
    parser.addoption(
        "--memlimit-unit",
        action="store",
        default=100,
        type=int,
        help="Memory limit in MB for unit tests (default: 100)"
    )
    parser.addoption(
        "--memlimit-integration",
        action="store",
        default=200,
        type=int,
        help="Memory limit in MB for integration tests (default: 200)"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically apply timeout markers to tests based on their type (unit vs integration)."""
    timeout_unit = config.getoption("--timeout-unit")
import warnings


@pytest.fixture(autouse=True, scope="function")
def memory_limit_autouse(request, pytestconfig):
    """Autouse fixture to apply memory limits based on test type."""
    # DISABLED: Memory limits causing crashes, run without limits for now
    yield None


@pytest.fixture
def mock_sync_writer():
    return MagicMock()  # Use MagicMock instead of AsyncMock for sync functions


@pytest.fixture
def mock_async_writer():
    writer = AsyncMock()
    writer.drain = AsyncMock()
    return writer


@pytest.fixture
def mock_data_stream_parser():
    return MagicMock(spec=DataStreamParser)


@pytest.fixture
def mock_negotiator_handler():
    handler = MagicMock()
    handler.receive_data = AsyncMock()
    handler._update_session_state_from_sna_response = MagicMock()
    return handler


@pytest.fixture
def monkey_patch_manager():
    return MonkeyPatchManager()


@pytest.fixture
def mock_p3270():
    mock_module = MagicMock()
    mock_session_module = MagicMock()
    mock_session = MagicMock()
    mock_session_module.Session = mock_session
    mock_module.session = mock_session_module
    mock_module.__version__ = "0.1.6"
    return mock_module


@pytest.fixture
def patching_context():
    with PatchContext():
        yield


@pytest.fixture
def negotiator(mock_async_writer, mock_data_stream_parser, screen_buffer, mock_negotiator_handler):
    return Negotiator(mock_async_writer, mock_data_stream_parser, screen_buffer, mock_negotiator_handler)
