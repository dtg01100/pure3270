import pytest

from pure3270.emulation.ebcdic import EmulationEncoder
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.session import AsyncSession


@pytest.mark.asyncio
async def test_insert_text_no_leading_space_async():
    session = AsyncSession()
    # Use a small screen for faster assertion
    session.screen_buffer = ScreenBuffer(rows=4, cols=24)
    session.screen_buffer.set_position(0, 0)
    await session.insert_text("TEST123")
    # Verify buffer content
    first_line = session.screen_buffer.ascii_buffer.split("\n")[0]
    assert first_line.startswith("TEST123")


@pytest.mark.asyncio
async def test_insert_text_matches_write_char():
    session = AsyncSession()
    sb_direct = ScreenBuffer(rows=4, cols=24)
    session.screen_buffer = ScreenBuffer(rows=4, cols=24)
    # Write direct via write_char
    row, col = 0, 0
    for ch in "TEST123":
        eb = EmulationEncoder.encode(ch)[0]
        sb_direct.write_char(eb, row=row, col=col)
        col += 1
    # Now use insert_text and compare the first line
    session.screen_buffer.set_position(0, 0)
    await session.insert_text("TEST123")
    assert (
        session.screen_buffer.ascii_buffer.split("\n")[0]
        == sb_direct.ascii_buffer.split("\n")[0]
    )
