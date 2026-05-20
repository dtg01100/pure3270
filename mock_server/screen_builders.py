"""3270 data stream builders for mock server scenarios."""

from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from pure3270.protocol.data_stream import SBA, SF

EW = 0x0F


def build_sba(row: int, col: int, width: int = 80) -> bytes:
    """Build SBA (Set Buffer Address) order for 12-bit addressing."""
    addr = (row * width) + col
    high = (addr >> 6) & 0x3F
    low = addr & 0x3F
    return bytes([SBA, high | 0x40, low | 0x40])


def build_erase_write() -> bytes:
    """Build EW order for full screen erase."""
    return bytes([EW])


def build_menu_screen(
    title: str,
    options: list[tuple[str, str]],
    width: int = 80,
) -> bytes:
    """Build a formatted 3270 menu screen.

    Args:
        title: Screen title (ASCII)
        options: List of (label, description) tuples

    Returns:
        Complete 3270 data stream bytes (WCC + orders + text + IAC EOR)
    """
    wcc_byte = bytes([0x00])

    buffer = bytearray(wcc_byte)

    buffer.extend(build_sba(0, 0, width))
    buffer.extend(translate_ascii_to_ebcdic(title))

    for i, (label, desc) in enumerate(options):
        row = 2 + i
        buffer.extend(build_sba(row, 0, width))
        buffer.extend(bytes([SF, 0xF0]))
        buffer.extend(translate_ascii_to_ebcdic(f"{label}: {desc}"))

    return bytes(buffer)