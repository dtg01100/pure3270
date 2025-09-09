import pytest
from pure3270.emulation.ebcdic import EBCDICCodec, translate_ebcdic_to_ascii, translate_ascii_to_ebcdic

def test_ebcdic_codec_decode():
    codec = EBCDICCodec()
    result, _ = codec.decode(b'\x81\x82\x83')  # A B C in EBCDIC
    assert result == 'ABC'

def test_ebcdic_codec_encode():
    codec = EBCDICCodec()
    result, _ = codec.encode('ABC')
    assert result == b'\x81\x82\x83'

def test_translate_ebcdic_to_ascii():
    ebcdic_bytes = b'\x81\x82\x83\x40\x4B'  # A B C space J
    ascii_str = translate_ebcdic_to_ascii(ebcdic_bytes)
    assert ascii_str == 'ABC J'

def test_translate_ascii_to_ebcdic():
    ascii_str = 'ABC J'
    ebcdic_bytes = translate_ascii_to_ebcdic(ascii_str)
    assert ebcdic_bytes == b'\x81\x82\x83\x40\x4B'

def test_ebcdic_edge_cases():
    # Invalid EBCDIC
    result = translate_ebcdic_to_ascii(b'\xFF\x00')
    assert len(result) > 0  # Handles invalid chars

    # Empty
    assert translate_ebcdic_to_ascii(b'') == ''
    assert translate_ascii_to_ebcdic('') == b''

def test_codec_errors():
    codec = EBCDICCodec()
    with pytest.raises(ValueError):
        codec.decode(b'\xFF' * 1000)  # Too long or invalid