import pytest
from unittest.mock import patch  # noqa: F401
from pure3270.protocol.data_stream import ParseError

class TestDataStreamParser:
    def test_init(self, data_stream_parser):
        assert data_stream_parser.screen is not None
        assert data_stream_parser._data == b""
        assert data_stream_parser._pos == 0
        assert data_stream_parser.wcc is None
        assert data_stream_parser.aid is None

    def test_parse_wcc(self, data_stream_parser):
        sample_data = b'\xF5\xC1'  # WCC 0xC1
        data_stream_parser.parse(sample_data)
        assert data_stream_parser.wcc == 0xC1
        # Check if clear was called if bit set
        assert data_stream_parser.screen.buffer == bytearray(1920)  # cleared if bit 0

    def test_parse_aid(self, data_stream_parser):
        sample_data = b'\xF6\x7D'  # AID Enter 0x7D
        data_stream_parser.parse(sample_data)
        assert data_stream_parser.aid == 0x7D

    def test_parse_sba(self, data_stream_parser):
        sample_data = b'\x10\x00\x00'  # SBA to 0,0
        with patch.object(data_stream_parser.screen, 'set_position'):
            data_stream_parser.parse(sample_data)
            data_stream_parser.screen.set_position.assert_called_with(0, 0)

    def test_parse_sf(self, data_stream_parser):
        sample_data = b'\x1D\x40'  # SF protected
        with patch.object(data_stream_parser.screen, 'write_char'):
            data_stream_parser.parse(sample_data)
            data_stream_parser.screen.write_char.assert_called_once()

    def test_parse_ra(self, data_stream_parser):
        sample_data = b'\xF3\x40\x00\x05'  # RA space 5 times
        data_stream_parser.parse(sample_data)
        # Assert logging or basic handling

    def test_parse_ge(self, data_stream_parser):
        sample_data = b'\x29'  # GE
        data_stream_parser.parse(sample_data)
        # Assert debug log for unsupported

    def test_parse_write(self, data_stream_parser):
        sample_data = b'\x05'  # Write
        with patch.object(data_stream_parser.screen, 'clear'):
            data_stream_parser.parse(sample_data)
            data_stream_parser.screen.clear.assert_called_once()

    def test_parse_data(self, data_stream_parser):
        sample_data = b'\xC1\xC2'  # Data ABC
        data_stream_parser.parse(sample_data)
        # Check buffer updated
        assert data_stream_parser.screen.buffer[0:2] == b'\xC1\xC2'

    def test_parse_bind(self, data_stream_parser):
        sample_data = b'\x28' + b'\x00' * 10  # BIND stub
        data_stream_parser.parse(sample_data)
        # Assert debug log

    def test_parse_incomplete(self, data_stream_parser):
        sample_data = b'\xF5'  # Incomplete WCC
        with pytest.raises(ParseError):
            data_stream_parser.parse(sample_data)

    def test_get_aid(self, data_stream_parser):
        data_stream_parser.aid = 0x7D
        assert data_stream_parser.get_aid() == 0x7D

class TestDataStreamSender:
    def test_build_read_modified_all(self, data_stream_sender):
        stream = data_stream_sender.build_read_modified_all()
        assert stream == b'\x7D\xF1'  # AID + Read Partition

    def test_build_read_modified_fields(self, data_stream_sender):
        stream = data_stream_sender.build_read_modified_fields()
        assert stream == b'\x7D\xF6\xF0'

    def test_build_key_press(self, data_stream_sender):
        stream = data_stream_sender.build_key_press(0x7D)
        assert stream == b'\x7D'

    def test_build_write(self, data_stream_sender):
        data = b'\xC1\xC2'
        stream = data_stream_sender.build_write(data)
        assert stream.startswith(b'\xF5\xC1\x05')
        assert b'\xC1\xC2' in stream
        assert stream.endswith(b'\x0D')

    def test_build_sba(self, data_stream_sender):
        # Note: sender has no screen, but assume default
        with patch('pure3270.protocol.data_stream.ScreenBuffer', rows=24, cols=80):
            stream = data_stream_sender.build_sba(0, 0)
            assert stream == b'\x10\x00\x00'

# Sample data streams fixtures
@pytest.fixture
def sample_wcc_stream():
    return b'\xF5\xC1'  # WCC reset modified

@pytest.fixture
def sample_sba_stream():
    return b'\x10\x00\x14'  # SBA to row 0 col 20

@pytest.fixture
def sample_write_stream():
    return b'\x05\xC1\xC2\xC3'  # Write ABC

def test_parse_sample_wcc(data_stream_parser, sample_wcc_stream):
    data_stream_parser.parse(sample_wcc_stream)
    assert data_stream_parser.wcc == 0xC1

def test_parse_sample_sba(data_stream_parser, sample_sba_stream):
    with patch.object(data_stream_parser.screen, 'set_position'):
        data_stream_parser.parse(sample_sba_stream)
        data_stream_parser.screen.set_position.assert_called_with(0, 20)

def test_parse_sample_write(data_stream_parser, sample_write_stream):
    with patch.object(data_stream_parser.screen, 'clear'):
        data_stream_parser.parse(sample_write_stream)
        data_stream_parser.screen.clear.assert_called_once()
    assert data_stream_parser.screen.buffer[0:3] == b'\xC1\xC2\xC3'
