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
        sample_data = b"\xf5\xc1"  # WCC 0xC1
        data_stream_parser.parse(sample_data)
        assert data_stream_parser.wcc == 0xC1
        # Check if clear was called if bit set (bit 0 means reset modified flags)
        # Our implementation clears buffer to spaces (0x40) when cleared
        assert data_stream_parser.screen.buffer == bytearray([0x40] * 1920)

    def test_parse_aid(self, data_stream_parser):
        sample_data = b"\xf6\x7d"  # AID Enter 0x7D
        data_stream_parser.parse(sample_data)
        assert data_stream_parser.aid == 0x7D

    def test_parse_sba(self, data_stream_parser):
        sample_data = b"\x10\x00\x00"  # SBA to 0,0
        with patch.object(data_stream_parser.screen, "set_position"):
            data_stream_parser.parse(sample_data)
            data_stream_parser.screen.set_position.assert_called_with(0, 0)

    def test_parse_sf(self, data_stream_parser):
        sample_data = b"\x1d\x40"  # SF protected
        with patch.object(data_stream_parser.screen, "write_char"):
            data_stream_parser.parse(sample_data)
            data_stream_parser.screen.write_char.assert_called_once()

    def test_parse_ra(self, data_stream_parser):
        sample_data = b"\xf3\x40\x00\x05"  # RA space 5 times
        data_stream_parser.parse(sample_data)
        # Assert logging or basic handling

    def test_parse_ge(self, data_stream_parser):
        sample_data = b"\x29"  # GE
        data_stream_parser.parse(sample_data)
        # Assert debug log for unsupported

    def test_parse_write(self, data_stream_parser):
        sample_data = b"\x05"  # Write
        with patch.object(data_stream_parser.screen, "clear"):
            data_stream_parser.parse(sample_data)
            data_stream_parser.screen.clear.assert_called_once()

    def test_parse_data(self, data_stream_parser):
        sample_data = b"\xc1\xc2"  # Data ABC
        data_stream_parser.parse(sample_data)
        # Check buffer updated
        assert data_stream_parser.screen.buffer[0:2] == b"\xc1\xc2"

    def test_parse_bind(self, data_stream_parser):
        sample_data = b"\x28" + b"\x00" * 10  # BIND stub
        data_stream_parser.parse(sample_data)
        # Assert debug log

    def test_parse_incomplete(self, data_stream_parser):
        sample_data = b"\xf5"  # Incomplete WCC
        with pytest.raises(ParseError):
            data_stream_parser.parse(sample_data)

    def test_get_aid(self, data_stream_parser):
        data_stream_parser.aid = 0x7D
        assert data_stream_parser.get_aid() == 0x7D

    def test_parse_scs_ctl_codes(self, data_stream_parser):
        sample_data = b"\x04\x01"  # SCS-CTL-CODES with PRINT-EOJ
        # This should not crash and should be handled
        data_stream_parser.parse(sample_data)

    def test_parse_data_stream_ctl(self, data_stream_parser):
        sample_data = b"\x40\x01"  # DATA-STREAM-CTL with some code
        # This should not crash and should be handled
        data_stream_parser.parse(sample_data)


class TestDataStreamSender:
    def test_build_read_modified_all(self, data_stream_sender):
        stream = data_stream_sender.build_read_modified_all()
        assert stream == b"\x7d\xf1"  # AID + Read Partition

    def test_build_read_modified_fields(self, data_stream_sender):
        stream = data_stream_sender.build_read_modified_fields()
        assert stream == b"\x7d\xf6\xf0"

    def test_build_key_press(self, data_stream_sender):
        stream = data_stream_sender.build_key_press(0x7D)
        assert stream == b"\x7d"

    def test_build_write(self, data_stream_sender):
        data = b"\xc1\xc2"
        stream = data_stream_sender.build_write(data)
        assert stream.startswith(b"\xf5\xc1\x05")
        assert b"\xc1\xc2" in stream
        assert stream.endswith(b"\x0d")

    def test_build_sba(self, data_stream_sender):
        # Note: sender has no screen, but assume default
        with patch("pure3270.protocol.data_stream.ScreenBuffer", rows=24, cols=80):
            stream = data_stream_sender.build_sba(0, 0)
            assert stream == b"\x10\x00\x00"

    def test_build_scs_ctl_codes(self, data_stream_sender):
        stream = data_stream_sender.build_scs_ctl_codes(0x01)  # PRINT-EOJ
        assert stream == b"\x04\x01"

    def test_build_data_stream_ctl(self, data_stream_sender):
        stream = data_stream_sender.build_data_stream_ctl(0x01)
        assert stream == b"\x40\x01"


# Sample data streams fixtures
@pytest.fixture
def sample_wcc_stream():
    return b"\xf5\xc1"  # WCC reset modified


@pytest.fixture
def sample_sba_stream():
    return b"\x10\x00\x14"  # SBA to row 0 col 20


@pytest.fixture
def sample_write_stream():
    return b"\x05\xc1\xc2\xc3"  # Write ABC


def test_parse_sample_wcc(data_stream_parser, sample_wcc_stream):
    data_stream_parser.parse(sample_wcc_stream)
    assert data_stream_parser.wcc == 0xC1


def test_parse_sample_sba(data_stream_parser, sample_sba_stream):
    with patch.object(data_stream_parser.screen, "set_position"):
        data_stream_parser.parse(sample_sba_stream)
        data_stream_parser.screen.set_position.assert_called_with(0, 20)


def test_parse_sample_write(data_stream_parser, sample_write_stream):
    with patch.object(data_stream_parser.screen, "clear"):
        data_stream_parser.parse(sample_write_stream)
        data_stream_parser.screen.clear.assert_called_once()
    assert data_stream_parser.screen.buffer[0:3] == b"\xc1\xc2\xc3"
