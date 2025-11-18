import base64

from pure3270.emulation.ebcdic import EBCDICCodec


def test_ebcdic_codec_p3270_compat_fallback():
    codec_default = EBCDICCodec()
    codec_p = EBCDICCodec(compat="p3270")

    # Choose a character outside CP037 (e.g., EURO SIGN)
    char = "\u20AC"
    b_default, _ = codec_default.encode(char)
    b_compat, _ = codec_p.encode(char)

    assert b_default == b"@"  # default fallback is EBCDIC space (0x40)
    assert b_compat == b"z"  # p3270 compat falls back to EBCDIC 'z' (0x7A)
