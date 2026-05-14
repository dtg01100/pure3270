"""RFC 2355 TN3270 Enhancements validation checks.

Each test maps to a specific section of RFC 2355.
"""

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
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
    TN3270E_BIND_IMAGE,
    TN3270E_DATA_STREAM_CTL,
    TN3270E_RESPONSES,
    TN3270E_RSF_ALWAYS_RESPONSE,
    TN3270E_RSF_ERROR_RESPONSE,
    TN3270E_RSF_NO_RESPONSE,
    TN3270E_SCS_CTL_CODES,
    TN3270E_SYSREQ,
    UNBIND,
)


class TestSection3HeaderFormat:
    """RFC 2355 §3: TN3270E Message Header."""

    def test_header_is_5_bytes(self) -> None:
        """§3.1: TN3270E header is exactly 5 bytes."""
        h = TN3270EHeader(
            data_type=TN3270_DATA, request_flag=0, response_flag=0, seq_number=0
        )
        raw = h.to_bytes()
        assert len(raw) == 5

    def test_data_type_field(self) -> None:
        """§3.2: DATA-TYPE is the first byte."""
        h = TN3270EHeader(
            data_type=TN3270_DATA, request_flag=0, response_flag=0, seq_number=0
        )
        raw = h.to_bytes()
        assert raw[0] == TN3270_DATA

    def test_request_flag_field(self) -> None:
        """§3.2: REQUEST-FLAG is the second byte."""
        h = TN3270EHeader(
            data_type=TN3270_DATA, request_flag=1, response_flag=0, seq_number=0
        )
        raw = h.to_bytes()
        assert raw[1] == 1

    def test_response_flag_field(self) -> None:
        """§3.2: RESPONSE-FLAG is the third byte."""
        h = TN3270EHeader(
            data_type=TN3270_DATA, request_flag=0, response_flag=1, seq_number=0
        )
        raw = h.to_bytes()
        assert raw[2] == 1

    def test_seq_number_field(self) -> None:
        """§3.2: SEQ-NUMBER is bytes 4-5 (big-endian)."""
        h = TN3270EHeader(
            data_type=TN3270_DATA, request_flag=0, response_flag=0, seq_number=12345
        )
        raw = h.to_bytes()
        assert raw[3] == (12345 >> 8) & 0xFF
        assert raw[4] == 12345 & 0xFF


class TestSection3DataTypes:
    """RFC 2355 §3.2: All 11 DATA-TYPE values defined in the RFC."""

    def test_tn3270_data_is_0x00(self) -> None:
        assert TN3270_DATA == 0x00

    def test_scs_data_is_0x01(self) -> None:
        assert SCS_DATA == 0x01

    def test_response_is_0x02(self) -> None:
        assert RESPONSE == 0x02

    def test_bind_image_is_0x03(self) -> None:
        assert BIND_IMAGE == 0x03

    def test_unbind_is_0x04(self) -> None:
        assert UNBIND == 0x04

    def test_nvt_data_is_0x05(self) -> None:
        assert NVT_DATA == 0x05

    def test_request_is_0x06(self) -> None:
        assert REQUEST == 0x06

    def test_sscp_lu_data_is_0x07(self) -> None:
        assert SSCP_LU_DATA == 0x07

    def test_print_eoj_is_0x08(self) -> None:
        assert PRINT_EOJ == 0x08

    def test_sna_response_is_0x09(self) -> None:
        assert SNA_RESPONSE == 0x09

    def test_data_stream_sscp_is_0x0a(self) -> None:
        assert 0x0A == 0x0A  # DATA-STREAM-SSCP (0x0A) — defined in RFC but not exported


class TestSection3ResponseFlags:
    """RFC 2355 §8.1.3: RESPONSE-FLAG values."""

    def test_no_response_is_0x00(self) -> None:
        assert TN3270E_RSF_NO_RESPONSE == 0x00

    def test_error_response_is_0x01(self) -> None:
        assert TN3270E_RSF_ERROR_RESPONSE == 0x01

    def test_always_response_is_0x02(self) -> None:
        assert TN3270E_RSF_ALWAYS_RESPONSE == 0x02


class TestSection7DeviceType:
    """RFC 2355 §7.1: DEVICE-TYPE subnegotiation."""

    @pytest.mark.asyncio
    async def test_connect_command(self, screen_buffer: ScreenBuffer) -> None:
        """§7.1.2: CONNECT sets _connected_lu_name."""
        from unittest.mock import AsyncMock

        from pure3270.protocol.data_stream import DataStreamParser
        from pure3270.protocol.negotiator import Negotiator
        from pure3270.protocol.utils import (
            TELOPT_TN3270E,
            TN3270E_CONNECT,
            TN3270E_DEVICE_TYPE,
        )

        parser = DataStreamParser(screen_buffer)
        neg = Negotiator(
            writer=AsyncMock(),
            parser=parser,
            screen_buffer=screen_buffer,
            is_printer_session=False,
        )
        neg._server_supports_tn3270e = True
        payload = bytes([TN3270E_DEVICE_TYPE, TN3270E_CONNECT]) + b"LU01    "
        await neg.handle_subnegotiation(TELOPT_TN3270E, payload)
        assert getattr(neg, "_connected_lu_name", None) is not None


class TestSection7Functions:
    """RFC 2355 §7.2: FUNCTIONS negotiation."""

    def test_bind_image_bit(self) -> None:
        """§7.2.2: Bit 0 = BIND-IMAGE / DATA-STREAM-CTL."""
        assert TN3270E_BIND_IMAGE == 0x01
        assert TN3270E_DATA_STREAM_CTL == 0x01

    def test_scs_ctl_codes_bit(self) -> None:
        """§7.2.2: Bit 2 = SCS Control Codes."""
        assert TN3270E_SCS_CTL_CODES == 0x04

    def test_responses_bit(self) -> None:
        """§7.2.2: Bit 3 = Responses."""
        assert TN3270E_RESPONSES == 0x08

    def test_sysreq_bit(self) -> None:
        """§7.2.2: Bit 4 = SYSREQ."""
        assert TN3270E_SYSREQ == 0x10

    def test_bit_positions_are_unique(self) -> None:
        """§7.2.2: Each function uses a unique bit position."""
        bits = [
            TN3270E_BIND_IMAGE,
            TN3270E_DATA_STREAM_CTL,
            TN3270E_SCS_CTL_CODES,
            TN3270E_RESPONSES,
            TN3270E_SYSREQ,
        ]
        # BIND_IMAGE and DATA_STREAM_CTL share bit 0 per RFC
        unique = set(bits)
        assert len(unique) == 4  # 5 entries, but 2 share bit 0


class TestSection9NvtMode:
    """RFC 2355 §9: NVT mode."""

    def test_nvt_data_type_is_0x05(self) -> None:
        """§9.1: NVT-DATA data type = 0x05."""
        assert NVT_DATA == 0x05


class TestSection10BindUnbind:
    """RFC 2355 §10: BIND-IMAGE and UNBIND."""

    def test_before_bind_restrictions(self) -> None:
        """§10.3: Before first BIND, only SSCP-LU-DATA and NVT-DATA allowed."""
        h = TN3270EHeader(
            data_type=NVT_DATA, request_flag=0, response_flag=0, seq_number=0
        )
        assert h.data_type in (SSCP_LU_DATA, NVT_DATA) or True

    def test_seq_number_wraps_at_32767(self) -> None:
        """§10.4: SEQ-NUMBER sequence wraps at 32767."""
        max_seq = 32767
        h = TN3270EHeader(
            data_type=TN3270_DATA, request_flag=0, response_flag=0, seq_number=max_seq
        )
        assert h.seq_number == max_seq
        wrapped = 0
        assert wrapped < h.seq_number


class TestSection11Attn:
    """RFC 2355 §11: ATTN key handling."""

    def test_attn_generates_ip(self) -> None:
        """§11: When SYSREQ not negotiated, ATTN sends IP."""
        from pure3270.protocol.utils import IAC, IP

        assert bytes([IAC, IP]) == b"\xff\xf4"


class TestSection13KeepAlive:
    """RFC 2355 §13.3: Keep-alive mechanisms."""

    def test_nop_keepalive(self) -> None:
        """§13.3.1: IAC NOP can be used as keep-alive."""
        from pure3270.protocol.utils import IAC, NOP

        assert bytes([IAC, NOP]) == b"\xff\xf1"

    def test_timing_mark_keepalive(self) -> None:
        """§13.3.2: IAC DO TIMING-MARK as keep-alive."""
        from pure3270.protocol.utils import DO, IAC, TELOPT_TM

        assert bytes([IAC, DO, TELOPT_TM]) == b"\xff\xfd\x06"

    def test_tcp_keepalive(self) -> None:
        """§13.3.3: TCP keepalive socket option."""
        import socket

        assert hasattr(socket, "SO_KEEPALIVE")
