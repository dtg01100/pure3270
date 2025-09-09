import pytest
import asyncio
from unittest.mock import AsyncMock  # noqa: F401

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.emulation.ebcdic import EBCDICCodec
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.ssl_wrapper import SSLWrapper
from pure3270.protocol.data_stream import DataStreamParser, DataStreamSender
from pure3270.session import AsyncSession, Session


@pytest.fixture
def screen_buffer():
    return ScreenBuffer(rows=24, cols=80)


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


@pytest.fixture
def async_session():
    return AsyncSession("localhost", 23)


@pytest.fixture
def sync_session():
    return Session("localhost", 23)


@pytest.fixture
def tn3270_handler():
    # Don't pre-set reader/writer for connection tests
    return TN3270Handler(None, None, host="localhost", port=23)
