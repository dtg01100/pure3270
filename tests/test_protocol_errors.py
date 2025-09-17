import asyncio
import platform
import ssl
from unittest.mock import patch

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser, ParseError
from pure3270.protocol.ssl_wrapper import SSLError, SSLWrapper
from pure3270.protocol.tn3270_handler import TN3270Handler


def test_parse_error(caplog, memory_limit_500mb):
    parser = DataStreamParser(ScreenBuffer())
    # Critical parse errors like "Incomplete WCC order" are re-raised immediately without logging
    with pytest.raises(ParseError) as exc_info:
        parser.parse(b"\xf5")  # Incomplete
    assert "Incomplete WCC order" in str(exc_info.value)


def test_protocol_error(caplog, memory_limit_500mb):
    handler = TN3270Handler(None, None, None, host="host", port=23)
    handler.writer = None
    with caplog.at_level("ERROR"):
        with pytest.raises(Exception):  # Catch ProtocolError
            asyncio.run(handler.send_data(b""))
    assert "Not connected" in caplog.text


def test_ssl_error(caplog, memory_limit_500mb):
    wrapper = SSLWrapper()
    with patch("ssl.SSLContext", side_effect=ssl.SSLError("Test")):
        with caplog.at_level("ERROR"):
            with pytest.raises(SSLError):
                wrapper.create_context()
    assert "SSL context creation failed" in caplog.text
