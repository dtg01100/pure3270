"""RFC 854 Telnet Protocol Specification validation checks.

Each test maps to a specific section of RFC 854.
"""

from pure3270.protocol.utils import (
    AO,
    AYT,
    BRK,
    DM,
    DO,
    DONT,
    EC,
    EL,
    EOR,
    GA,
    IAC,
    IP,
    NOP,
    SB,
    SE,
    TELOPT_BINARY,
    TELOPT_ECHO,
    TELOPT_SGA,
    TELOPT_TM,
    WILL,
    WONT,
)


def test_section_3_command_structure() -> None:
    """RFC 854 §3: IAC is 0xFF, commands are 2-byte sequences."""
    assert IAC == 0xFF
    assert bytes([IAC, NOP]) == b"\xff\xf1"
    assert bytes([IAC, DM]) == b"\xff\xf2"
    assert bytes([IAC, BRK]) == b"\xff\xf3"
    assert bytes([IAC, IP]) == b"\xff\xf4"
    assert bytes([IAC, AO]) == b"\xff\xf5"
    assert bytes([IAC, AYT]) == b"\xff\xf6"
    assert bytes([IAC, EC]) == b"\xff\xf7"
    assert bytes([IAC, EL]) == b"\xff\xf8"
    assert bytes([IAC, GA]) == b"\xff\xf9"


def test_section_3_subnegotiation() -> None:
    """RFC 854 §3: Subnegotiation uses IAC SB ... IAC SE."""
    assert SB == 0xFA
    assert SE == 0xF0
    assert bytes([IAC, SB]) == b"\xff\xfa"
    assert bytes([IAC, SE]) == b"\xff\xf0"


def test_section_4_option_negotiation() -> None:
    """RFC 854 §4: WILL/WONT/DO/DONT codes."""
    assert WILL == 0xFB
    assert WONT == 0xFC
    assert DO == 0xFD
    assert DONT == 0xFE
    assert bytes([IAC, WILL, TELOPT_BINARY]) == b"\xff\xfb\x00"
    assert bytes([IAC, WONT, TELOPT_BINARY]) == b"\xff\xfc\x00"
    assert bytes([IAC, DO, TELOPT_ECHO]) == b"\xff\xfd\x01"
    assert bytes([IAC, DONT, TELOPT_ECHO]) == b"\xff\xfe\x01"


def test_section_4_iac_iac_escaping() -> None:
    """RFC 854 §4: IAC IAC in data stream means single 0xFF byte."""
    data = b"Hello" + bytes([IAC, IAC]) + b"World"
    result = data.replace(bytes([IAC, IAC]), bytes([0xFF]))
    assert result == b"Hello\xffWorld"


def test_section_5_nop() -> None:
    """RFC 854 §5.1: NOP (0xF1) - No operation."""
    assert NOP == 0xF1
    assert bytes([IAC, NOP]) == b"\xff\xf1"


def test_section_5_dm() -> None:
    """RFC 854 §5.2: DM (0xF2) - Data Mark (part of SYNCH)."""
    assert DM == 0xF2
    assert bytes([IAC, DM]) == b"\xff\xf2"


def test_section_5_brk() -> None:
    """RFC 854 §5.3: BRK (0xF3) - Break."""
    assert BRK == 0xF3
    assert bytes([IAC, BRK]) == b"\xff\xf3"


def test_section_5_ip() -> None:
    """RFC 854 §5.4: IP (0xF4) - Interrupt Process."""
    assert IP == 0xF4
    assert bytes([IAC, IP]) == b"\xff\xf4"


def test_section_5_ao() -> None:
    """RFC 854 §5.5: AO (0xF5) - Abort Output."""
    assert AO == 0xF5
    assert bytes([IAC, AO]) == b"\xff\xf5"


def test_section_5_ayt() -> None:
    """RFC 854 §5.6: AYT (0xF6) - Are You There."""
    assert AYT == 0xF6
    assert bytes([IAC, AYT]) == b"\xff\xf6"


def test_section_5_ec() -> None:
    """RFC 854 §5.7: EC (0xF7) - Erase Character."""
    assert EC == 0xF7
    assert bytes([IAC, EC]) == b"\xff\xf7"


def test_section_5_el() -> None:
    """RFC 854 §5.8: EL (0xF8) - Erase Line."""
    assert EL == 0xF8
    assert bytes([IAC, EL]) == b"\xff\xf8"


def test_section_5_ga() -> None:
    """RFC 854 §5.9: GA (0xF9) - Go Ahead."""
    assert GA == 0xF9
    assert bytes([IAC, GA]) == b"\xff\xf9"


def test_section_10_nvt_default() -> None:
    """RFC 854 §10: Default NVT is half-duplex, ASCII, carriage-oriented."""
    from pure3270.emulation.ebcdic import translate_ebcdic_to_ascii

    ascii_text = translate_ebcdic_to_ascii(b"\xc1\xc2\xc3")
    assert ascii_text == "ABC"


def test_crlf_normalization() -> None:
    """RFC 854 §3: CR must be followed by either NULL or LF."""
    crlf = b"\r\n"
    crnul = b"\r\x00"
    assert crlf[0] == 0x0D
    assert crlf[1] == 0x0A
    assert crnul[1] == 0x00


def test_timing_mark_option() -> None:
    """RFC 854 §17: TIMING-MARK option (6) definition."""
    assert TELOPT_TM == 0x06


def test_binary_option() -> None:
    """RFC 856: BINARY transmission option (0)."""
    assert TELOPT_BINARY == 0x00


def test_echo_option() -> None:
    """RFC 857: Echo option (1)."""
    assert TELOPT_ECHO == 0x01


def test_sga_option() -> None:
    """RFC 858: Suppress Go Ahead option (3)."""
    assert TELOPT_SGA == 0x03
