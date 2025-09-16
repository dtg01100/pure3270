import platform
from unittest.mock import AsyncMock, MagicMock

import pytest

from pure3270.protocol.utils import (send_iac, send_subnegotiation,
                                     strip_telnet_iac)


def test_send_iac(mock_sync_writer, memory_limit_500mb):
    data = b"\xfb\x01"  # WILL ECHO
    send_iac(mock_sync_writer, data)
    mock_sync_writer.write.assert_called_once_with(b"\xff" + data)
    # drain() is not called automatically, caller should await it if needed


def test_send_subnegotiation(mock_sync_writer, memory_limit_500mb):
    opt = b"\x27"
    data = b"\x00\x01\xff\xff"
    send_subnegotiation(mock_sync_writer, opt, data)
    expected = b"\xff\xfa" + opt + data + b"\xff\xf0"
    mock_sync_writer.write.assert_called_once_with(expected)
    # drain() is not called automatically, caller should await it if needed


def test_strip_telnet_iac_basic(memory_limit_500mb):
    data = b"Hello\xff\xfb\x01World"
    cleaned = strip_telnet_iac(data)
    assert cleaned == b"HelloWorld"


def test_strip_telnet_iac_subnegotiation(memory_limit_500mb):
    data = b"Test\xff\xfa\x27\x00\x01\xff\xff\xf0End"
    cleaned = strip_telnet_iac(data)
    assert cleaned == b"TestEnd"


def test_strip_telnet_iac_eor_ga(memory_limit_500mb):
    data = b"Data\xff\x19More\xff\xf9Final"
    cleaned = strip_telnet_iac(data, handle_eor_ga=True)
    assert cleaned == b"DataMoreFinal"


def test_strip_telnet_iac_no_iac(memory_limit_500mb):
    data = b"Plain text without IAC"
    cleaned = strip_telnet_iac(data)
    assert cleaned == data


def test_strip_telnet_iac_incomplete(memory_limit_500mb):
    data = b"Incomplete\xff"
    cleaned = strip_telnet_iac(data)
    assert cleaned == b"Incomplete"  # Truncates incomplete IAC
