import pytest
import asyncio
from unittest.mock import patch
from pure3270.protocol.data_stream import DataStreamParser, ParseError
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.ssl_wrapper import SSLWrapper, SSLError
import ssl


def test_parse_error(caplog):
    parser = DataStreamParser(ScreenBuffer())
    with caplog.at_level("ERROR"):
        with pytest.raises(ParseError):
            parser.parse(b"\xf5")  # Incomplete
    assert "Unexpected end" in caplog.text


def test_protocol_error(caplog):
    handler = TN3270Handler("host", 23)
    handler.writer = None
    with caplog.at_level("ERROR"):
        with pytest.raises(Exception):  # Catch ProtocolError
            asyncio.run(handler.send_data(b""))
    assert "Not connected" in caplog.text


def test_ssl_error(caplog):
    wrapper = SSLWrapper()
    with patch("ssl.SSLContext", side_effect=ssl.SSLError("Test")):
        with caplog.at_level("ERROR"):
            with pytest.raises(SSLError):
                wrapper.create_context()
    assert "SSL context creation failed" in caplog.text
