import pytest
from unittest.mock import AsyncMock, MagicMock
from pure3270.protocol.utils import send_iac, send_subnegotiation, strip_telnet_iac

@pytest.fixture
def mock_writer():
    return AsyncMock()

def test_send_iac(mock_writer):
    data = b'\xFB\x01'  # WILL ECHO
    send_iac(mock_writer, data)
    mock_writer.write.assert_called_once_with(b'\xFF' + data)
    mock_writer.drain.assert_called_once()

def test_send_subnegotiation(mock_writer):
    opt = b'\x27'
    data = b'\x00\x01\xFF\xFF'
    send_subnegotiation(mock_writer, opt, data)
    expected = b'\xFF\xFA' + opt + data + b'\xFF\xF0'
    mock_writer.write.assert_called_once_with(expected)
    mock_writer.drain.assert_called_once()

def test_strip_telnet_iac_basic():
    data = b'Hello\xFF\xFB\x01World'
    cleaned = strip_telnet_iac(data)
    assert cleaned == b'HelloWorld'

def test_strip_telnet_iac_subnegotiation():
    data = b'Test\xFF\xFA\x27\x00\x01\xFF\xFF\xF0End'
    cleaned = strip_telnet_iac(data)
    assert cleaned == b'TestEnd'

def test_strip_telnet_iac_eor_ga():
    data = b'Data\xFF\x19More\xFF\xF9Final'
    cleaned = strip_telnet_iac(data, handle_eor_ga=True)
    assert cleaned == b'DataMoreFinal'

def test_strip_telnet_iac_no_iac():
    data = b'Plain text without IAC'
    cleaned = strip_telnet_iac(data)
    assert cleaned == data

def test_strip_telnet_iac_incomplete():
    data = b'Incomplete\xFF'
    cleaned = strip_telnet_iac(data)
    assert cleaned == b'Incomplete'  # Truncates incomplete IAC
