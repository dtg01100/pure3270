"""RFC 1576 TN3270 Current Practices validation checks.

Each test maps to a specific section of RFC 1576.
"""

from pure3270.protocol.utils import DO, IAC, TELOPT_BINARY, TELOPT_EOR, WILL


def test_section_2_binary_and_eor() -> None:
    """RFC 1576 §2.1: TN3270 uses BINARY and EOR telnet options."""
    assert TELOPT_BINARY == 0x00
    assert TELOPT_EOR == 0x19
    assert bytes([IAC, WILL, TELOPT_BINARY]) == b"\xff\xfb\x00"
    assert bytes([IAC, WILL, TELOPT_EOR]) == b"\xff\xfb\x19"


def test_section_2_will_eor_negotiation() -> None:
    """RFC 1576 §2.2: Server sends IAC WILL EOR to indicate TN3270 support."""
    assert bytes([IAC, WILL, TELOPT_EOR]) == b"\xff\xfb\x19"
    # Client responds with IAC DO EOR to accept
    assert DO == 0xFD
    assert bytes([IAC, DO, TELOPT_EOR]) == b"\xff\xfd\x19"
