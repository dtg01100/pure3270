import pytest
import platform
from pure3270.emulation.ebcdic import (
    EBCDICCodec,
    translate_ebcdic_to_ascii,
    translate_ascii_to_ebcdic,
)


@pytest.mark.skipif(platform.system() != 'Linux', reason="Memory limiting only supported on Linux")
def test_ebcdic_codec_decode(memory_limit_500mb):
    codec = EBCDICCodec()
    result, _ = codec.decode(b"\xc1\xc2\xc3")  # A B C in EBCDIC
    assert result == "ABC"


@pytest.mark.skipif(platform.system() != 'Linux', reason="Memory limiting only supported on Linux")
def test_ebcdic_codec_encode(memory_limit_500mb):
    codec = EBCDICCodec()
    result, _ = codec.encode("ABC")
    assert result == b"\xc1\xc2\xc3"


@pytest.mark.skipif(platform.system() != 'Linux', reason="Memory limiting only supported on Linux")
def test_translate_ebcdic_to_ascii(memory_limit_500mb):
    ebcdic_bytes = b"\xc1\xc2\xc3\x40\xd1"  # A B C space J
    ascii_str = translate_ebcdic_to_ascii(ebcdic_bytes)
    assert ascii_str == "ABC J"


@pytest.mark.skipif(platform.system() != 'Linux', reason="Memory limiting only supported on Linux")
def test_translate_ascii_to_ebcdic(memory_limit_500mb):
    ascii_str = "ABC J"
    ebcdic_bytes = translate_ascii_to_ebcdic(ascii_str)
    assert ebcdic_bytes == b"\xc1\xc2\xc3\x40\xd1"


@pytest.mark.skipif(platform.system() != 'Linux', reason="Memory limiting only supported on Linux")
def test_ebcdic_edge_cases(memory_limit_500mb):
    # Invalid EBCDIC
    result = translate_ebcdic_to_ascii(b"\xff\x00")
    assert len(result) > 0  # Handles invalid chars

    # Empty
    assert translate_ebcdic_to_ascii(b"") == ""
    assert translate_ascii_to_ebcdic("") == b""


@pytest.mark.skipif(platform.system() != 'Linux', reason="Memory limiting only supported on Linux")
def test_codec_errors(memory_limit_500mb):
    codec = EBCDICCodec()
    # Our implementation uses 'z' for unknown values instead of raising errors
    result, _ = codec.decode(b"\xff" * 10)
    assert result == "z" * 10  # Should handle invalid chars gracefully
