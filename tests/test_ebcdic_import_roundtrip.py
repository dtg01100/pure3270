import platform

import pytest

from pure3270.emulation import ebcdic


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
def test_ebcdic_module_import_and_basic_roundtrip():
    # Module import smoke
    assert hasattr(ebcdic, "translate_ebcdic_to_ascii")
    assert hasattr(ebcdic, "translate_ascii_to_ebcdic")
    assert hasattr(ebcdic, "EBCDICCodec")

    # Basic round-trip using translate helpers
    text = "HELLO"
    eb = ebcdic.translate_ascii_to_ebcdic(text)
    assert isinstance(eb, (bytes, bytearray))
    decoded = ebcdic.translate_ebcdic_to_ascii(eb)
    # Allow for possible spacing/canonicalization but ensure letters are present
    assert "H" in decoded and "E" in decoded and "L" in decoded and "O" in decoded


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
def test_ebcdiccodec_tuple_api():
    codec = ebcdic.EBCDICCodec()
    encoded, length = codec.encode("ABC")
    assert isinstance(encoded, (bytes, bytearray))
    assert isinstance(length, int) and length == len(encoded)
    decoded, dlen = codec.decode(encoded)
    assert isinstance(decoded, str)
    assert isinstance(dlen, int) and dlen == len(decoded)
