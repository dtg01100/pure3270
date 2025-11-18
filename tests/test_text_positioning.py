from pure3270.emulation.ebcdic import EmulationEncoder
from pure3270.emulation.screen_buffer import ScreenBuffer


def test_write_chars_no_leading_space():
    sb = ScreenBuffer(rows=4, cols=24, init_value=0x40)
    sb.set_position(0, 0)
    text = "TEST123"
    # Write each char as if typed using explicit position
    row, col = sb.get_position()
    for ch in text:
        eb = EmulationEncoder.encode(ch)[0]
        sb.write_char(eb, row=row, col=col)
        col += 1
        if col >= sb.cols:
            col = 0
            row += 1
    # The ascii_buffer should start with TEST123 at row 0
    ascii_lines = sb.ascii_buffer.split("\n")
    assert ascii_lines[0].startswith(text)
