import pytest
from pure3270.emulation.ebcdic import (
    EBCDICCodec,
    translate_ebcdic_to_ascii,
    translate_ascii_to_ebcdic,
)


def test_ebcdic_codec_decode():
    codec = EBCDICCodec()
    result, _ = codec.decode(b"\xc1\xc2\xc3")  # A B C in EBCDIC
    assert result == "ABC"


def test_ebcdic_codec_encode():
    codec = EBCDICCodec()
    result, _ = codec.encode("ABC")
    assert result == b"\xc1\xc2\xc3"


def test_translate_ebcdic_to_ascii():
    ebcdic_bytes = b"\xc1\xc2\xc3\x40\xd1"  # A B C space J
    ascii_str = translate_ebcdic_to_ascii(ebcdic_bytes)
    assert ascii_str == "ABC J"


def test_translate_ascii_to_ebcdic():
    ascii_str = "ABC J"
    ebcdic_bytes = translate_ascii_to_ebcdic(ascii_str)
    assert ebcdic_bytes == b"\xc1\xc2\xc3\x40\xd1"


def test_ebcdic_edge_cases():
    # Invalid EBCDIC
    result = translate_ebcdic_to_ascii(b"\xff\x00")
    assert len(result) > 0  # Handles invalid chars

    # Empty
    assert translate_ebcdic_to_ascii(b"") == ""
    assert translate_ascii_to_ebcdic("") == b""


def test_codec_errors():
    codec = EBCDICCodec()
    # Our implementation uses 'z' for unknown values instead of raising errors
    result, _ = codec.decode(b"\xff" * 10)
    assert result == "z" * 10  # Should handle invalid chars gracefully
