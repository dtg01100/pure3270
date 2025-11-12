"""Tests for transactional Write/EW behavior: incomplete orders abort entire write.

These tests ensure s3270-compatible semantics: when a write contains an
incomplete order (e.g., SA/SBA truncated), the entire write is rolled back
and the screen state remains unchanged.
"""

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser


def test_abort_write_on_incomplete_sa():
    """Incomplete SA (missing value) must abort the entire write and rollback."""
    screen = ScreenBuffer(rows=2, cols=5)
    parser = DataStreamParser(screen)

    # Write (0x01), WCC (0x40), data 'A'(0xC1), 'B'(0xC2), then SA (0x28) with
    # only the attribute type (0x41) and missing the value byte -> incomplete.
    stream = bytes([0x01, 0x40, 0xC1, 0xC2, 0x28, 0x41])

    before = bytes(screen.buffer)
    parser.parse(stream)
    after = bytes(screen.buffer)

    # Expect no change due to rollback
    assert before == after, "Screen buffer changed despite incomplete SA rollback"


def test_abort_write_on_incomplete_sba():
    """Incomplete SBA (missing one address byte) must abort the entire write and rollback."""
    screen = ScreenBuffer(rows=2, cols=5)
    parser = DataStreamParser(screen)

    # Write (0x01), WCC (0x40), data 'X'(0xE7), then SBA (0x11) with only one
    # address byte (0x00) -> incomplete (needs two bytes in our handler).
    stream = bytes([0x01, 0x40, 0xE7, 0x11, 0x00])

    before = bytes(screen.buffer)
    parser.parse(stream)
    after = bytes(screen.buffer)

    # Expect no change due to rollback
    assert before == after, "Screen buffer changed despite incomplete SBA rollback"


def test_complete_write_applies_bytes():
    """A complete write without incomplete orders should update the buffer."""
    screen = ScreenBuffer(rows=2, cols=5)
    parser = DataStreamParser(screen)

    # Write (0x01), WCC (0x40), data 'A'(0xC1), 'B'(0xC2) -> should be applied.
    stream = bytes([0x01, 0x40, 0xC1, 0xC2])

    before = bytes(screen.buffer)
    parser.parse(stream)
    after = bytes(screen.buffer)

    # Expect changes at first two positions
    assert before != after, "Screen buffer did not change on complete write"
    assert (
        after[0] == 0xC1 and after[1] == 0xC2
    ), "Written bytes not applied at start of buffer"
