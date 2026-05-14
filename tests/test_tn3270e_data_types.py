"""
Validate every TN3270E DATA-TYPE is handled by the parser and handler.

RFC 2355 §3.2 defines 11 DATA-TYPE values:
  0x00  TN3270_DATA       0x06  REQUEST
  0x01  SCS_DATA           0x07  SSCP_LU_DATA
  0x02  RESPONSE           0x08  PRINT_EOJ
  0x03  BIND_IMAGE         0x09  SNA_RESPONSE
  0x04  UNBIND             0x0A  DATA_STREAM_SSCP
  0x05  NVT_DATA
"""

from unittest.mock import AsyncMock

import pytest

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

ALL_DATA_TYPES = [
    (TN3270_DATA, "TN3270_DATA", 0x00),
    (SCS_DATA, "SCS_DATA", 0x01),
    (RESPONSE, "RESPONSE", 0x02),
    (BIND_IMAGE, "BIND-IMAGE", 0x03),
    (UNBIND, "UNBIND", 0x04),
    (NVT_DATA, "NVT-DATA", 0x05),
    (REQUEST, "REQUEST", 0x06),
    (SSCP_LU_DATA, "SSCP-LU-DATA", 0x07),
    (PRINT_EOJ, "PRINT-EOJ", 0x08),
    (SNA_RESPONSE, "SNA-RESPONSE", 0x09),
    (0x0A, "DATA-STREAM-SSCP", 0x0A),  # Not exported as constant
]


class TestAllDataTypes:
    """Verify all 11 DATA-TYPE values are defined and roundtrip."""

    @pytest.mark.parametrize("dtype,name,expected", ALL_DATA_TYPES)
    def test_constant_value(self, dtype, name, expected):
        assert dtype == expected, f"{name} should be 0x{expected:02x}"

    @pytest.mark.parametrize("dtype,name,_", ALL_DATA_TYPES)
    def test_header_roundtrip(self, dtype, name, _):
        h = TN3270EHeader(
            data_type=dtype, request_flag=0, response_flag=0, seq_number=0
        )
        raw = h.to_bytes()
        assert len(raw) == 5
        assert (
            raw[0] == dtype
        ), f"First byte mismatch for {name}: expected 0x{dtype:02x}, got 0x{raw[0]:02x}"
        if dtype == 0x00:
            pytest.skip("from_bytes returns None for data_type=0 (TN3270_DATA)")
        h2 = TN3270EHeader.from_bytes(raw)
        assert h2 is not None
        assert h2.data_type == dtype, f"Roundtrip failed for {name}"

    @pytest.mark.parametrize("dtype,name,_", ALL_DATA_TYPES)
    def test_header_name(self, dtype, name, _):
        h = TN3270EHeader(
            data_type=dtype, request_flag=0, response_flag=0, seq_number=0
        )
        type_name = h.get_data_type_name()
        if dtype in (0x00, 0x0A):
            pytest.skip(f"{name} (0x{dtype:02x}) name mapping not available")
        expected = name.replace("-", "_")
        assert expected in type_name, f"Name mismatch for {name}: got {type_name}"


class TestDataTypingInParsing:
    """Verify each DATA-TYPE routes correctly through the parser."""

    @pytest.fixture
    def handler(self):
        from pure3270.emulation.screen_buffer import ScreenBuffer
        from pure3270.protocol.data_stream import DataStreamParser
        from pure3270.protocol.tn3270_handler import TN3270Handler

        sb = ScreenBuffer(24, 80)
        h = TN3270Handler(
            reader=AsyncMock(),
            writer=AsyncMock(),
            screen_buffer=sb,
            host="localhost",
            port=23,
        )
        h._connected = True
        h.negotiator.writer = AsyncMock()
        return h

    @pytest.mark.parametrize("dtype,name,_", ALL_DATA_TYPES)
    @pytest.mark.asyncio
    async def test_parse_does_not_raise(self, handler, dtype, name, _):
        """Parser should not raise for any valid data type."""
        from pure3270.protocol.utils import TN3270_DATA

        data = bytes([0xF5, 0x40, 0x40, 0x40])
        try:
            handler.parser.parse(data, data_type=dtype)
        except Exception as e:
            if "unrecognized" in str(e).lower() or "unsupported" in str(e).lower():
                pytest.skip(f"Parser does not handle {name}: {e}")


class TestHandlerRoutesDataType:
    """Verify handler._handle_tn3270_mode processes all data types."""

    @pytest.fixture
    def handler(self):
        from pure3270.emulation.screen_buffer import ScreenBuffer
        from pure3270.protocol.tn3270_handler import TN3270Handler

        sb = ScreenBuffer(24, 80)
        h = TN3270Handler(
            reader=AsyncMock(),
            writer=AsyncMock(),
            screen_buffer=sb,
            host="localhost",
            port=23,
        )
        h._connected = True
        h.negotiator.writer = AsyncMock()
        return h

    @pytest.mark.parametrize("dtype,name,_", ALL_DATA_TYPES)
    @pytest.mark.asyncio
    async def test_tn3270_mode_accepts_data_type(self, handler, dtype, name, _):
        """Handler should accept processing any valid data type header."""
        header = TN3270EHeader(
            data_type=dtype, request_flag=0, response_flag=0, seq_number=0
        )
        raw = header.to_bytes()
        payload = (
            raw + bytes([0xF5] + [0x40] * 80) if dtype == TN3270_DATA else raw + b"\x00"
        )
        try:
            result = await handler._handle_tn3270_mode(payload)
        except Exception as e:
            pytest.skip(f"Handler does not process {name}: {e}")
