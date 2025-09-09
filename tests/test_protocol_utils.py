import pytest
from unittest.mock import AsyncMock, MagicMock
from pure3270.protocol.utils import send_iac, send_subnegotiation, strip_telnet_iac


@pytest.fixture
def mock_writer():
    return MagicMock()  # Use MagicMock instead of AsyncMock for sync functions


def test_send_iac(mock_writer):
    data = b"\xfb\x01"  # WILL ECHO
    send_iac(mock_writer, data)
    mock_writer.write.assert_called_once_with(b"\xff" + data)
    # drain() is not called automatically, caller should await it if needed


def test_send_subnegotiation(mock_writer):
    opt = b"\x27"
    data = b"\x00\x01\xff\xff"
    send_subnegotiation(mock_writer, opt, data)
    expected = b"\xff\xfa" + opt + data + b"\xff\xf0"
    mock_writer.write.assert_called_once_with(expected)
    # drain() is not called automatically, caller should await it if needed


def test_strip_telnet_iac_basic():
    data = b"Hello\xff\xfb\x01World"
    cleaned = strip_telnet_iac(data)
    assert cleaned == b"HelloWorld"


def test_strip_telnet_iac_subnegotiation():
    data = b"Test\xff\xfa\x27\x00\x01\xff\xff\xf0End"
    cleaned = strip_telnet_iac(data)
    assert cleaned == b"TestEnd"


def test_strip_telnet_iac_eor_ga():
    data = b"Data\xff\x19More\xff\xf9Final"
    cleaned = strip_telnet_iac(data, handle_eor_ga=True)
    assert cleaned == b"DataMoreFinal"


def test_strip_telnet_iac_no_iac():
    data = b"Plain text without IAC"
    cleaned = strip_telnet_iac(data)
    assert cleaned == data


def test_strip_telnet_iac_incomplete():
    data = b"Incomplete\xff"
    cleaned = strip_telnet_iac(data)
    assert cleaned == b"Incomplete"  # Truncates incomplete IAC
