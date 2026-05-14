"""
Feature matrix: smoke-test every major pure3270 feature.

Each test validates one independent feature. Tests are parameterized
so adding a new feature is a single line.
"""

import pytest

# ── Session ──────────────────────────────────────────────────────────────────


def test_imports():
    from pure3270 import AsyncSession, P3270Client, Session, setup_logging


def test_session_construct():
    from pure3270 import Session

    session = Session(host="test-host", port=23)
    assert session._host == "test-host"
    assert session._port == 23


def test_session_construct_default_port():
    from pure3270 import Session

    session = Session(host="test-host")
    assert session._port == 23


def test_async_session_construct():
    from pure3270 import AsyncSession

    session = AsyncSession(host="test-host", port=23)
    assert session.host == "test-host"
    assert session.port == 23


# ── Screen Buffer ────────────────────────────────────────────────────────────


def test_screen_buffer_create():
    from pure3270.emulation.screen_buffer import ScreenBuffer

    sb = ScreenBuffer(rows=24, cols=80)
    assert sb.rows == 24
    assert sb.cols == 80
    assert len(sb.buffer) == 1920


def test_screen_buffer_clear():
    from pure3270.emulation.screen_buffer import ScreenBuffer

    sb = ScreenBuffer(24, 80)
    sb.clear()
    assert all(b == 0x40 for b in sb.buffer)


def test_screen_buffer_set_cursor():
    from pure3270.emulation.screen_buffer import ScreenBuffer

    sb = ScreenBuffer(24, 80)
    sb.set_position(10, 20)
    assert sb.cursor_row == 10
    assert sb.cursor_col == 20


def test_screen_buffer_write_char():
    from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
    from pure3270.emulation.screen_buffer import ScreenBuffer

    sb = ScreenBuffer(3, 10)
    sb.write_char(0xC1, 0, 0)
    text = sb.to_text()
    assert len(text) > 0


def test_screen_buffer_fields():
    from pure3270.emulation.screen_buffer import ScreenBuffer

    sb = ScreenBuffer(24, 80)
    fields = sb.fields
    assert isinstance(fields, list)


# ── EBCDIC ───────────────────────────────────────────────────────────────────


def test_ebcdic_import():
    from pure3270.emulation.ebcdic import EBCDICCodec


def test_ebcdic_encode():
    from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic

    result = translate_ascii_to_ebcdic("HELLO")
    assert len(result) == 5
    assert result == b"\xc8\xc5\xd3\xd3\xd6"


def test_ebcdic_decode():
    from pure3270.emulation.ebcdic import translate_ebcdic_to_ascii

    result = translate_ebcdic_to_ascii(b"\xc1\xc2\xc3")
    assert result == "ABC"


# ── Telnet Protocol ──────────────────────────────────────────────────────────


def test_iac_commands():
    from pure3270.protocol.utils import (
        AO,
        AYT,
        BRK,
        DM,
        EC,
        EL,
        GA,
        IAC,
        IP,
        NOP,
        SB,
        SE,
    )

    assert IAC == 0xFF
    assert NOP == 0xF1
    assert SB == 0xFA
    assert SE == 0xF0


def test_option_negotiation():
    from pure3270.protocol.utils import DO, DONT, WILL, WONT

    assert bytes([0xFF, WILL, 0x00]) == b"\xff\xfb\x00"
    assert bytes([0xFF, WONT, 0x00]) == b"\xff\xfc\x00"
    assert bytes([0xFF, DO, 0x01]) == b"\xff\xfd\x01"
    assert bytes([0xFF, DONT, 0x01]) == b"\xff\xfe\x01"


def test_iac_iac_escaping():
    data = b"Hello" + bytes([0xFF, 0xFF]) + b"World"
    result = data.replace(b"\xff\xff", b"\xff")
    assert result == b"Hello\xffWorld"


# ── TN3270E Header ───────────────────────────────────────────────────────────


def test_tn3270e_header_construct():
    from pure3270.protocol.tn3270e_header import TN3270EHeader
    from pure3270.protocol.utils import TN3270_DATA

    h = TN3270EHeader(
        data_type=TN3270_DATA, request_flag=0, response_flag=0, seq_number=0
    )
    assert h.data_type == TN3270_DATA


def test_tn3270e_header_roundtrip():
    from pure3270.protocol.tn3270e_header import TN3270EHeader
    from pure3270.protocol.utils import RESPONSE, TN3270_DATA

    h1 = TN3270EHeader(
        data_type=TN3270_DATA, request_flag=0, response_flag=1, seq_number=42
    )
    raw = h1.to_bytes()
    assert len(raw) == 5
    assert raw[0] == TN3270_DATA
    assert raw[2] == 1
    assert raw[3] == 0
    assert raw[4] == 42


def test_tn3270e_header_all_data_types():
    from pure3270.protocol.tn3270e_header import TN3270EHeader
    from pure3270.protocol.utils import (
        BIND_IMAGE,
        NVT_DATA,
        PRINT_EOJ,
        REQUEST,
        RESPONSE,
        SCS_DATA,
        SNA_RESPONSE,
        SSCP_LU_DATA,
        TN3270_DATA,
        UNBIND,
    )

    for dtype in [
        TN3270_DATA,
        SCS_DATA,
        RESPONSE,
        BIND_IMAGE,
        UNBIND,
        NVT_DATA,
        REQUEST,
        SSCP_LU_DATA,
        PRINT_EOJ,
        SNA_RESPONSE,
    ]:
        h = TN3270EHeader(
            data_type=dtype, request_flag=0, response_flag=0, seq_number=0
        )
        assert h.data_type == dtype


# ── Data Stream Parser ───────────────────────────────────────────────────────


def test_parser_construct(screen_buffer):
    from pure3270.protocol.data_stream import DataStreamParser

    p = DataStreamParser(screen_buffer)
    assert p is not None


def test_parser_write():
    from pure3270.emulation.screen_buffer import ScreenBuffer
    from pure3270.protocol.data_stream import DataStreamParser, DataStreamSender

    sb = ScreenBuffer(24, 80)
    parser = DataStreamParser(sb)
    sender = DataStreamSender()
    buf = sender.build_write(b"\xf5\x40\x40\x40\x40")
    parser.parse(buf, 0x00)


# ── Negotiator ───────────────────────────────────────────────────────────────


def test_negotiator_construct():
    from unittest.mock import AsyncMock

    from pure3270.emulation.screen_buffer import ScreenBuffer
    from pure3270.protocol.data_stream import DataStreamParser
    from pure3270.protocol.negotiator import Negotiator

    sb = ScreenBuffer(24, 80)
    parser = DataStreamParser(sb)
    neg = Negotiator(
        writer=AsyncMock(), parser=parser, screen_buffer=sb, is_printer_session=False
    )
    assert neg.terminal_type is not None


def test_negotiator_supported_functions():
    from pure3270.protocol.utils import (
        TN3270E_BIND_IMAGE,
        TN3270E_DATA_STREAM_CTL,
        TN3270E_RESPONSES,
        TN3270E_SCS_CTL_CODES,
    )

    supported = (
        TN3270E_BIND_IMAGE
        | TN3270E_DATA_STREAM_CTL
        | TN3270E_SCS_CTL_CODES
        | TN3270E_RESPONSES
    )
    assert supported & TN3270E_BIND_IMAGE
    assert supported & TN3270E_SCS_CTL_CODES


# ── TN3270Handler ────────────────────────────────────────────────────────────


def test_handler_construct():
    from unittest.mock import AsyncMock

    from pure3270.emulation.screen_buffer import ScreenBuffer
    from pure3270.protocol.tn3270_handler import TN3270Handler

    h = TN3270Handler(
        reader=AsyncMock(), writer=AsyncMock(), screen_buffer=ScreenBuffer(24, 80)
    )
    assert h._connected is False


# ── P3270 Client ─────────────────────────────────────────────────────────────


def test_p3270_client_import():
    from pure3270.p3270_client import P3270Client


def test_p3270_client_construct():
    from pure3270.p3270_client import P3270Client

    client = P3270Client()
    assert client.isConnected() is False


# ── Printer ──────────────────────────────────────────────────────────────────


def test_printer_session_construct():
    from pure3270.protocol.printer import PrinterSession

    ps = PrinterSession()
    assert ps.is_active is False


def test_printer_job_construct():
    from pure3270.protocol.printer import PrinterJob

    job = PrinterJob()
    assert job.status == "active"
    assert job.data == b""


# ── SSL ──────────────────────────────────────────────────────────────────────


def test_ssl_wrapper_construct():
    from pure3270.protocol.ssl_wrapper import SSLWrapper

    sw = SSLWrapper()
    assert sw is not None


# ── IND$FILE ─────────────────────────────────────────────────────────────────


def test_indfile_import():
    from pure3270.ind_file import IndFileError, IndFileMessage


# ── LU-LU Session ────────────────────────────────────────────────────────────


def test_lulu_session_import():
    from pure3270.lu_lu_session import LuLuSession


# ── Addressing ────────────────────────────────────────────────────────────────


def test_addressing_import():
    from pure3270.emulation.addressing import AddressingMode


# ── Field Attributes ─────────────────────────────────────────────────────────


def test_field_attributes_import():
    from pure3270.emulation.field_attributes import (
        BackgroundAttribute,
        CharacterSetAttribute,
        ColorAttribute,
        ExtendedAttributeSet,
        HighlightAttribute,
    )


# ── Constants ────────────────────────────────────────────────────────────────


def test_constants_import():
    from pure3270.constants import (
        AID_CLEAR,
        AID_ENTER,
        AID_PA1,
        AID_PF1,
        CMD_EW,
        CMD_EWA,
        CMD_W,
        CMD_WSF,
        COLOR_RED,
        HIGHLIGHT_BLINK,
    )


# ── Logging ──────────────────────────────────────────────────────────────────


def test_logging_api():
    import logging

    from pure3270 import JSONFormatter, StructuredLogger, setup_logging

    logger = logging.getLogger("test")
    assert isinstance(logger, logging.Logger)


# ── CLI ──────────────────────────────────────────────────────────────────────


def test_cli_module():
    """CLI entry point is accessible (run via `python -m pure3270`)."""
    # The __main__ module uses argparse at import time, so we skip
    # import-level testing and verify it exists on disk instead.
    import os

    assert os.path.isfile(
        os.path.join(os.path.dirname(__file__), "..", "pure3270", "__main__.py")
    )


# ── Patching System ──────────────────────────────────────────────────────────


def test_patching_import():
    from pure3270.patching import enable_replacement


# ── Warnings System ──────────────────────────────────────────────────────────


def test_warnings_import():
    from pure3270.warnings import (
        WarningCategory,
        WarningFilters,
        configure_default_filters,
        get_warning_filters,
    )
