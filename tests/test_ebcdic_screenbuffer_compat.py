import base64

from pure3270.emulation.ebcdic import EBCDICCodec
from pure3270.emulation.screen_buffer import ScreenBuffer


def test_ebcdic_codec_p3270_encode_decode():
    codec_default = EBCDICCodec()
    codec_p = EBCDICCodec(compat="p3270")

    # Choose a character outside CP037 (e.g., EURO SIGN) -- likely to be treated
    # differently by the default codec vs the p3270 compat mapping.
    char = "\u20AC"  # EURO SIGN
    # When encoding an unknown or control character, p3270 compat should
    # return a different fallback byte value than default.
    b_default, _ = codec_default.encode(char)
    b_compat, _ = codec_p.encode(char)

    assert isinstance(b_default, bytes)
    assert isinstance(b_compat, bytes)
    # They should not be identical when the compat behavior is enabled
    assert b_default != b_compat


def test_screen_buffer_uses_p3270_compat_mode():
    # Create a minimal screen buffer with a known pattern, using values
    # that map to visible characters in EBCDIC CP037.
    sb = ScreenBuffer(rows=1, cols=4, init_value=0x40)  # default spaces
    # Write a couple of bytes that are in CP037 but then an unknown byte 0xFF
    sb.buffer[0:4] = bytes([0xC1, 0x81, 0x7A, 0x40])
    # Without compat, decode normally
    decoded_default = sb.ascii_buffer
    # Now with compat mode (p3270), set the flag and decode again
    sb.compat_mode = "p3270"
    decoded_p = sb.ascii_buffer
    # Ensure both decodes are strings and same length
    assert isinstance(decoded_default, str)
    assert isinstance(decoded_p, str)
    assert len(decoded_default) == len(decoded_p)
    # The compatibility mode may alter mapping for certain characters.
    # Ensure the text is stable and no exceptions are thrown during decode.
    assert all((32 <= ord(ch) or ch in "\n\t\r") for ch in decoded_p)
