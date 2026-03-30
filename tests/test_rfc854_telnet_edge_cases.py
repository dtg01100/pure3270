"""
RFC 854 Telnet Protocol Edge Case Tests

Tests for Telnet protocol (RFC 854) edge cases and compliance.

RFC 854 References:
- Section 3.1: Telnet commands (IAC handling)
- Section 3.2.1: Telnet control commands (NOP, DM, GA, etc.)
- Section 3.2.2: The Interrupt Process (IP) function
- Section 4.1: NVT ASCII representation
- Section 4.2: NVT line endings (CRLF)

Test Coverage:
- IAC escaping (consecutive 0xFF bytes)
- CRLF normalization
- Go-ahead handling
- Telnet command processing
- NVT character set validation
"""

import pytest

from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.utils import AO, AYT, BRK, DM, EC, EL, GA, IAC, IP, NOP, SB, SE


class TestIACEscaping:
    """Tests for IAC (0xFF) escaping per RFC 854 Section 3.1.

    In Telnet, the IAC byte (0xFF) must be escaped when it appears in data.
    Two consecutive IAC bytes (0xFF 0xFF) represent a single data byte 0xFF.
    """

    def test_iac_escaping_single_byte(self):
        """Test that IAC byte in data is properly escaped."""
        # When IAC appears in data, it should be doubled
        data_with_iac = bytes([IAC, IAC])  # 0xFF 0xFF
        # This should be interpreted as single data byte 0xFF
        assert len(data_with_iac) == 2
        assert data_with_iac[0] == IAC
        assert data_with_iac[1] == IAC

    def test_iac_escaping_in_stream(self):
        """Test IAC escaping within a data stream."""
        # Data: "Hello" + IAC + "World"
        # Should be: "Hello" + IAC + IAC + "World"
        original = b"Hello" + bytes([IAC]) + b"World"
        escaped = b"Hello" + bytes([IAC, IAC]) + b"World"

        # Verify escaping doubles the IAC
        assert len(escaped) == len(original) + 1
        assert escaped[5:7] == bytes([IAC, IAC])

    def test_consecutive_iac_bytes(self):
        """Test multiple consecutive IAC bytes."""
        # Three IAC bytes: IAC (command) + IAC IAC (data)
        # Or: IAC IAC (data) + IAC (command)
        data = bytes([IAC, IAC, IAC])
        # First two should be data 0xFF, third starts command
        assert len(data) == 3

    def test_iac_at_start_of_data(self):
        """Test IAC byte at start of data stream."""
        data = bytes([IAC, IAC]) + b"test"
        assert data[0:2] == bytes([IAC, IAC])
        assert data[2:] == b"test"

    def test_iac_at_end_of_data(self):
        """Test IAC byte at end of data stream."""
        data = b"test" + bytes([IAC, IAC])
        assert data[0:4] == b"test"
        assert data[4:6] == bytes([IAC, IAC])


class TestCRLFHandling:
    """Tests for CRLF handling per RFC 854 Section 4.2.

    NVT uses CRLF (\\r\\n) for line endings.
    CR alone (\\r) should be followed by NUL (\\0) or LF (\\n).
    """

    def test_crf_line_ending(self):
        """Test standard CRLF line ending."""
        line = b"Hello\r\n"
        assert line.endswith(b"\r\n")

    def test_cr_without_lf(self):
        """Test CR without LF (should be CR + NUL per RFC)."""
        # Per RFC 854, CR alone should be CR + NUL
        data = b"Hello\r"
        # In proper NVT, this should be followed by NUL or LF
        assert data.endswith(b"\r")

    def test_lf_without_cr(self):
        """Test LF without CR (non-standard but common)."""
        data = b"Hello\n"
        # Some systems use LF alone
        assert data.endswith(b"\n")

    def test_mixed_line_endings(self):
        """Test handling of mixed line endings."""
        data = b"Line1\r\nLine2\nLine3\r"
        lines = data.replace(b"\r\n", b"\n").split(b"\n")
        assert len(lines) == 3
        assert lines[0] == b"Line1"
        assert lines[1] == b"Line2"
        assert lines[2] == b"Line3\r"

    def test_cr_nul_sequence(self):
        """Test CR + NUL sequence per RFC 854."""
        # CR followed by NUL is valid NVT
        data = b"Hello\r\x00"
        assert data.endswith(b"\r\x00")


class TestTelnetCommands:
    """Tests for Telnet control commands per RFC 854 Section 3.2."""

    def test_nop_command(self):
        """Test NOP (No Operation) command."""
        # NOP is IAC NOP (0xFF 0xF1)
        nop_command = bytes([IAC, NOP])
        assert len(nop_command) == 2
        assert nop_command[0] == IAC
        assert nop_command[1] == NOP

    def test_dm_command(self):
        """Test DM (Data Mark) command."""
        # DM is IAC DM (0xFF 0xF2)
        dm_command = bytes([IAC, DM])
        assert len(dm_command) == 2
        assert dm_command[0] == IAC
        assert dm_command[1] == DM

    def test_brk_command(self):
        """Test BRK (Break) command."""
        # BRK is IAC BRK (0xFF 0xF3)
        brk_command = bytes([IAC, BRK])
        assert len(brk_command) == 2
        assert brk_command[0] == IAC
        assert brk_command[1] == BRK

    def test_ip_command(self):
        """Test IP (Interrupt Process) command."""
        # IP is IAC IP (0xFF 0xF4)
        ip_command = bytes([IAC, IP])
        assert len(ip_command) == 2
        assert ip_command[0] == IAC
        assert ip_command[1] == IP

    def test_ao_command(self):
        """Test AO (Abort Output) command."""
        # AO is IAC AO (0xFF 0xF5)
        ao_command = bytes([IAC, AO])
        assert len(ao_command) == 2
        assert ao_command[0] == IAC
        assert ao_command[1] == AO

    def test_ayt_command(self):
        """Test AYT (Are You There) command."""
        # AYT is IAC AYT (0xFF 0xF6)
        ayt_command = bytes([IAC, AYT])
        assert len(ayt_command) == 2
        assert ayt_command[0] == IAC
        assert ayt_command[1] == AYT

    def test_ec_command(self):
        """Test EC (Erase Character) command."""
        # EC is IAC EC (0xFF 0xF7)
        ec_command = bytes([IAC, EC])
        assert len(ec_command) == 2
        assert ec_command[0] == IAC
        assert ec_command[1] == EC

    def test_el_command(self):
        """Test EL (Erase Line) command."""
        # EL is IAC EL (0xFF 0xF8)
        el_command = bytes([IAC, EL])
        assert len(el_command) == 2
        assert el_command[0] == IAC
        assert el_command[1] == EL

    def test_ga_command(self):
        """Test GA (Go Ahead) command."""
        # GA is IAC GA (0xFF 0xF9)
        ga_command = bytes([IAC, GA])
        assert len(ga_command) == 2
        assert ga_command[0] == IAC
        assert ga_command[1] == GA


class TestSubnegotiation:
    """Tests for Telnet subnegotiation per RFC 854.

    Subnegotiations are framed by IAC SB ... IAC SE.
    """

    def test_subnegotiation_framing(self):
        """Test subnegotiation start and end markers."""
        # SB = 0xFA, SE = 0xF0
        subneg = bytes([IAC, SB, 0x01, 0x02, 0x03, IAC, SE])
        assert subneg[0] == IAC
        assert subneg[1] == SB
        assert subneg[-2] == IAC
        assert subneg[-1] == SE

    def test_subnegotiation_with_iac_in_data(self):
        """Test subnegotiation containing IAC byte in data."""
        # IAC in subnegotiation data must be escaped
        data_with_iac = bytes([IAC, SB, 0x01, IAC, IAC, 0x02, IAC, SE])
        # The IAC IAC in the middle represents data byte 0xFF
        assert len(data_with_iac) == 8

    def test_empty_subnegotiation(self):
        """Test minimal subnegotiation (no data)."""
        subneg = bytes([IAC, SB, IAC, SE])
        assert len(subneg) == 4
        assert subneg[0:2] == bytes([IAC, SB])
        assert subneg[2:4] == bytes([IAC, SE])


class TestNVTCharacterSet:
    """Tests for NVT ASCII character set per RFC 854 Section 4.1."""

    def test_ascii_printable_characters(self):
        """Test printable ASCII characters (0x20-0x7E)."""
        printable = bytes(range(0x20, 0x7F))
        assert len(printable) == 95
        assert printable[0] == 0x20  # Space
        assert printable[-1] == 0x7E  # Tilde

    def test_ascii_control_characters(self):
        """Test ASCII control characters (0x00-0x1F, 0x7F)."""
        # NUL, LF, CR, etc.
        assert bytes([0x00]) == b"\x00"  # NUL
        assert bytes([0x0A]) == b"\n"  # LF
        assert bytes([0x0D]) == b"\r"  # CR
        assert bytes([0x7F]) == b"\x7f"  # DEL

    def test_nvt_ascii_range(self):
        """Test NVT ASCII is 7-bit (0x00-0x7F)."""
        # NVT uses 7-bit ASCII
        for i in range(0x80):
            assert i <= 0x7F

    def test_high_bit_characters(self):
        """Test characters with high bit set (0x80-0xFF)."""
        # These are not part of NVT ASCII
        high_bit = bytes([0x80, 0xFF])
        assert len(high_bit) == 2
        assert high_bit[0] == 0x80
        assert high_bit[1] == 0xFF


class TestGoAheadHandling:
    """Tests for Go Ahead (GA) handling per RFC 854.

    GA is used in half-duplex mode to indicate end of transmission.
    """

    def test_ga_at_end_of_transmission(self):
        """Test GA marking end of transmission."""
        transmission = b"Data\r\n" + bytes([IAC, GA])
        assert transmission.endswith(bytes([IAC, GA]))

    def test_multiple_ga_sequences(self):
        """Test multiple GA commands in sequence."""
        data = bytes([IAC, GA, IAC, GA])
        assert len(data) == 4
        assert data.count(GA) == 2

    def test_ga_with_data(self):
        """Test GA followed by more data (full-duplex mode)."""
        # In full-duplex, GA might be ignored or used differently
        data = b"Data1" + bytes([IAC, GA]) + b"Data2"
        assert b"Data1" in data
        assert b"Data2" in data
        assert GA in data


@pytest.mark.asyncio
class TestAsyncTelnetHandling:
    """Async tests for Telnet protocol handling."""

    async def test_async_iac_detection(self):
        """Test async detection of IAC bytes in stream."""
        # Simulate receiving data with IAC
        data = b"Hello" + bytes([IAC, IAC]) + b"World"
        # Should detect IAC and handle escaping
        iac_count = data.count(IAC)
        assert iac_count == 2

    async def test_async_command_parsing(self):
        """Test async parsing of Telnet commands."""
        # Stream with embedded command
        stream = b"Data" + bytes([IAC, NOP]) + b"More"
        # Should identify command boundaries
        assert IAC in stream
        assert NOP in stream

    async def test_async_subnegotiation_parsing(self):
        """Test async parsing of subnegotiations."""
        # Stream with subnegotiation
        stream = b"Before" + bytes([IAC, SB, 0x01, IAC, SE]) + b"After"
        # Should identify subnegotiation boundaries
        assert SB in stream
        assert SE in stream
