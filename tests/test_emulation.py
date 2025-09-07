import pytest
from unittest.mock import patch
import time

from pure3270.emulation.screen_buffer import ScreenBuffer, Field
from pure3270.emulation.ebcdic import EBCDICCodec


@pytest.fixture
def screen_buffer():
    return ScreenBuffer(rows=24, cols=80)


@pytest.fixture
def ebcdic_codec():
    return EBCDICCodec()


class TestField:
    def test_field_init(self):
        field = Field(start=(0, 0), end=(0, 5), protected=True, numeric=True, modified=False, content=b'\xC1\xC2\xC3')
        assert field.start == (0, 0)
        assert field.end == (0, 5)
        assert field.protected is True
        assert field.numeric is True
        assert field.modified is False
        assert field.content == b'\xC1\xC2\xC3'

    def test_field_get_content(self, ebcdic_codec):
        with patch.object(ebcdic_codec, 'decode', return_value='ABC'):
            field = Field(start=(0, 0), end=(0, 3), content=b'\xC1\xC2\xC3')
            assert field.get_content() == 'ABC'

    def test_field_set_content(self, ebcdic_codec):
        with patch.object(ebcdic_codec, 'encode', return_value=b'\xC4\xC5\xC6'):
            field = Field(start=(0, 0), end=(0, 3))
            field.set_content('DEF')
            assert field.content == b'\xC4\xC5\xC6'
            assert field.modified is True

    def test_field_repr(self):
        field = Field(start=(0, 0), end=(0, 5), protected=False)
        assert repr(field) == "Field(start=(0, 0), end=(0, 5), protected=False)"


class TestScreenBuffer:
    def test_init(self, screen_buffer):
        assert screen_buffer.rows == 24
        assert screen_buffer.cols == 80
        assert len(screen_buffer.buffer) == 1920
        assert len(screen_buffer.attributes) == 5760
        assert len(screen_buffer.fields) == 0
        assert screen_buffer.cursor_row == 0
        assert screen_buffer.cursor_col == 0

    def test_clear(self, screen_buffer):
        screen_buffer.buffer = bytearray([1] * 1920)
        screen_buffer.attributes = bytearray([2] * 5760)
        screen_buffer.fields = [Field((0,0),(0,1))]
        screen_buffer.cursor_row = 5
        screen_buffer.cursor_col = 10
        screen_buffer.clear()
        assert len(screen_buffer.buffer) == 1920 and all(b == 0 for b in screen_buffer.buffer)
        assert len(screen_buffer.attributes) == 5760 and all(b == 0 for b in screen_buffer.attributes)
        assert len(screen_buffer.fields) == 0
        assert screen_buffer.cursor_row == 0
        assert screen_buffer.cursor_col == 0

    def test_set_position_and_get_position(self, screen_buffer):
        screen_buffer.set_position(10, 20)
        assert screen_buffer.get_position() == (10, 20)

    def test_write_char(self, screen_buffer):
        screen_buffer.write_char(0xC1, 0, 0, protected=True)
        pos = 0
        assert screen_buffer.buffer[pos] == 0xC1
        attr_offset = pos * 3
        assert screen_buffer.attributes[attr_offset] == 0x02  # protected bit

    def test_write_char_out_of_bounds(self, screen_buffer):
        screen_buffer.write_char(0xC1, 25, 81)  # out of bounds
        assert screen_buffer.buffer[0] == 0  # no change

    @patch('pure3270.emulation.screen_buffer.EBCDICCodec')
    def test_to_text(self, mock_codec, screen_buffer):
        mock_codec.return_value.decode.return_value = 'Test Line'
        screen_buffer.buffer = bytearray([0xC1] * 80)  # A repeated
        with patch.object(mock_codec.return_value, 'decode', return_value='A' * 80):
            text = screen_buffer.to_text()
            lines = text.split('\n')
            assert len(lines) == 24
            assert lines[0] == 'A' * 80

    def test_update_from_stream(self, screen_buffer):
        sample_stream = b'\xC1\xC2\xC3' * 10  # Sample EBCDIC
        with patch.object(screen_buffer, '_detect_fields'):
            screen_buffer.update_from_stream(sample_stream)
        pos = 0
        for i in range(30):
            assert screen_buffer.buffer[pos + i] == sample_stream[i % 3]

    def test_get_field_content(self, screen_buffer):
        screen_buffer.fields = [Field((0,0),(0,3), content=b'\xC1\xC2\xC3')]
        with patch('pure3270.emulation.screen_buffer.EBCDICCodec') as mock_codec:
            mock_codec.return_value.decode.return_value = 'ABC'
            assert screen_buffer.get_field_content(0) == 'ABC'
        assert screen_buffer.get_field_content(1) == ''  # out of range

    def test_read_modified_fields(self, screen_buffer):
        field1 = Field((0,0),(0,3), modified=True)
        field2 = Field((1,0),(1,3), modified=False)
        screen_buffer.fields = [field1, field2]
        with patch.object(field1, 'get_content', return_value='MOD'), \
             patch.object(field2, 'get_content', return_value='NOT'):
            modified = screen_buffer.read_modified_fields()
            assert len(modified) == 1
            assert modified[0][0] == (0, 0)
            assert modified[0][1] == 'MOD'

    def test_repr(self, screen_buffer):
        assert repr(screen_buffer) == "ScreenBuffer(24x80, fields=0)"


class TestEBCDICCodec:
    def test_init(self, ebcdic_codec):
        assert hasattr(ebcdic_codec, 'ebcdic_to_unicode_table')
        assert len(ebcdic_codec.ebcdic_to_unicode_table) > 50  # partial mapping
        assert hasattr(ebcdic_codec, 'ebcdic_translate')

    def test_encode(self, ebcdic_codec):
        encoded = ebcdic_codec.encode('A')
        assert encoded == b'\xC1'  # From mapping
        encoded = ebcdic_codec.encode('ABC123')
        assert encoded == b'\xC1\xC2\xC3\xF1\xF2\xF3'  # A B C 1 2 3

    def test_encode_unknown_char(self, ebcdic_codec):
        encoded = ebcdic_codec.encode('?')  # Unknown, should default to space 0x40
        assert encoded == b'\x40'

    def test_decode(self, ebcdic_codec):
        decoded = ebcdic_codec.decode(b'\xC1\xC2\xC3')
        assert decoded == 'ABC'
        decoded = ebcdic_codec.decode(b'\xF0\xF1\xF2')
        assert decoded == '012'

    @patch('builtins.bytes.translate')
    def test_decode_translate(self, mock_translate, ebcdic_codec):
        mock_bytes = MagicMock()
        mock_bytes.translate.return_value = b'ABC'
        mock_bytes.decode.return_value = 'ABC'
        with patch('builtins.bytes', return_value=mock_bytes):
            decoded = ebcdic_codec.decode(b'\xC1')
            assert decoded == 'ABC'

    def test_encode_to_unicode_table(self, ebcdic_codec):
        encoded = ebcdic_codec.encode_to_unicode_table('A')
        assert encoded == b'\xC1'

# General tests for exceptions and logging (emulation specific)
def test_emulation_exception(caplog):
    with pytest.raises(AttributeError):  # Example, as no specific exceptions in emulation
        ScreenBuffer(rows=-1)
    assert 'error' not in caplog.text  # No logging in init

# Performance basic test: time to fill buffer
def test_performance_buffer_fill(benchmark, screen_buffer):
    def fill_buffer():
        for i in range(1920):
            screen_buffer.write_char(0x40, i // 80, i % 80)
    benchmark(fill_buffer)
    # Assert under threshold, but benchmark handles timing

# Sample 3270 data stream test
SAMPLE_3270_STREAM = b'\x05\xF5\xC1\x10\x00\x00\xC1\xC2\xC3\x0D'  # Write, WCC, SBA(0,0), ABC, EOA

def test_update_from_sample_stream(screen_buffer):
    with patch.object(screen_buffer, '_detect_fields'):
        screen_buffer.update_from_stream(SAMPLE_3270_STREAM)
    assert screen_buffer.buffer[0:3] == b'\xC1\xC2\xC3'