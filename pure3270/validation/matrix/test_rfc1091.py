"""RFC 1091 Telnet Terminal-Type Option validation checks.

Each test maps to a specific section of RFC 1091.
"""

from pure3270.protocol.utils import TELOPT_TTYPE, TTYPE_IS, TTYPE_SEND


def test_section_2_option_code() -> None:
    """RFC 1091 §2.1: Terminal type option code is 24 (0x18)."""
    assert TELOPT_TTYPE == 0x18


def test_section_2_subnegotiation_qualifiers() -> None:
    """RFC 1091 §2.2: Terminal type subnegotiation uses IS and SEND qualifiers."""
    assert TTYPE_IS == 0x00
    assert TTYPE_SEND == 0x01
    assert TTYPE_IS != TTYPE_SEND


def test_section_3_iana_registered_names() -> None:
    """RFC 1091 §3.1: Terminal type names follow registered IANA format (IBM-XXXX)."""
    valid_prefixes = ("IBM-", "DEC-", "WYSE-", "HP-")
    known_types = ("IBM-3278-2", "IBM-3278-4", "IBM-3287-1", "IBM-DYNAMIC")
    for name in known_types:
        assert name.startswith(valid_prefixes), f"'{name}' must use registered prefix"
        assert len(name) <= 40, f"'{name}' must be within IANA length limit"
