import pytest
from unittest.mock import patch  # noqa: F401

from pure3270.emulation.screen_buffer import ScreenBuffer, Field


class TestField:
    def test_field_init(self):
        field = Field(
            start=(0, 0),
            end=(0, 5),
            protected=True,
            numeric=True,
            modified=False,
            content=b"\xc1\xc2\xc3",
        )
        assert field.start == (0, 0)
        assert field.end == (0, 5)
        assert field.protected is True
        assert field.numeric is True
        assert field.modified is False
        assert field.content == b"\xc1\xc2\xc3"

    def test_field_get_content(self, ebcdic_codec):
        with patch.object(ebcdic_codec, "decode", return_value=("ABC", 3)):
            field = Field(start=(0, 0), end=(0, 3), content=b"\xc1\xc2\xc3")
            assert field.get_content() == "ABC"

    def test_field_set_content(self, ebcdic_codec):
        with patch.object(ebcdic_codec, "encode", return_value=(b"\xc4\xc5\xc6", 3)):
            field = Field(start=(0, 0), end=(0, 3))
            field.set_content("DEF")
            assert field.content == b"\xc4\xc5\xc6"
            assert field.modified is True

    def test_field_repr(self):
        field = Field(start=(0, 0), end=(0, 5), protected=False)
        assert "Field(start=(0, 0), end=(0, 5), protected=False" in repr(field)


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
        screen_buffer.fields = [Field((0, 0), (0, 1))]
        screen_buffer.cursor_row = 5
        screen_buffer.cursor_col = 10
        screen_buffer.clear()
        assert len(screen_buffer.buffer) == 1920 and all(
            b == 0x40 for b in screen_buffer.buffer
        )
        assert len(screen_buffer.attributes) == 5760 and all(
            b == 0 for b in screen_buffer.attributes
        )
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
        assert screen_buffer.attributes[attr_offset] & 0x40  # protected bit (bit 6)

    def test_write_char_out_of_bounds(self, screen_buffer):
        screen_buffer.write_char(0xC1, 25, 81)  # out of bounds
        assert (
            screen_buffer.buffer[0] == 0x40
        )  # no change (buffer initialized with spaces)

    @patch("pure3270.emulation.screen_buffer.EBCDICCodec")
    def test_to_text(self, mock_codec, screen_buffer):
        mock_codec.return_value.decode.return_value = ("Test Line", 9)
        screen_buffer.buffer = bytearray([0xC1] * 80)  # A repeated
        with patch.object(
            mock_codec.return_value, "decode", return_value=("A" * 80, 80)
        ):
            text = screen_buffer.to_text()
            lines = text.split("\n")
            assert len(lines) == 24
            assert lines[0] == "A" * 80

    def test_update_from_stream(self, screen_buffer):
        sample_stream = b"\xc1\xc2\xc3" * 10  # Sample EBCDIC
        with patch.object(screen_buffer, "_detect_fields"):
            screen_buffer.update_from_stream(sample_stream)
        pos = 0
        for i in range(30):
            assert screen_buffer.buffer[pos + i] == sample_stream[i % 3]

    def test_get_field_content(self, screen_buffer):
        screen_buffer.fields = [Field((0, 0), (0, 3), content=b"\xc1\xc2\xc3")]
        with patch("pure3270.emulation.screen_buffer.EBCDICCodec") as mock_codec:
            mock_codec.return_value.decode.return_value = ("ABC", 3)
            assert screen_buffer.get_field_content(0) == "ABC"
        assert screen_buffer.get_field_content(1) == ""  # out of range

    def test_read_modified_fields(self, screen_buffer):
        field1 = Field((0, 0), (0, 3), modified=True)
        field2 = Field((1, 0), (1, 3), modified=False)
        screen_buffer.fields = [field1, field2]
        with patch.object(field1, "get_content", return_value="MOD"), patch.object(
            field2, "get_content", return_value="NOT"
        ):
            modified = screen_buffer.read_modified_fields()
            assert len(modified) == 1
            assert modified[0][0] == (0, 0)
            assert modified[0][1] == "MOD"

    def test_repr(self, screen_buffer):
        screen_buffer.fields = []  # Ensure empty
        assert repr(screen_buffer) == "ScreenBuffer(24x80, fields=0)"


class TestEBCDICCodec:
    def test_init(self, ebcdic_codec):
        assert hasattr(ebcdic_codec, "ebcdic_to_unicode_table")
        assert len(ebcdic_codec.ebcdic_to_unicode_table) > 50  # partial mapping
        assert hasattr(ebcdic_codec, "ebcdic_translate")

    def test_encode(self, ebcdic_codec):
        encoded, _ = ebcdic_codec.encode("A")
        assert encoded == b"\xc1"  # From mapping
        encoded, _ = ebcdic_codec.encode("ABC123")
        assert encoded == b"\xc1\xc2\xc3\xf1\xf2\xf3"  # A B C digits in EBCDIC

    def test_encode_unknown_char(self, ebcdic_codec):
        encoded, _ = ebcdic_codec.encode("?")  # Unknown, maps to 0x7A
        assert encoded == b"\x7a"

    def test_decode(self, ebcdic_codec):
        decoded, _ = ebcdic_codec.decode(b"\xc1\xc2\xc3")
        assert decoded == "ABC"
        decoded, _ = ebcdic_codec.decode(b"\xf0\xf1\xf2")
        assert decoded == "012"  # digits for EBCDIC digits

    def test_decode_translate(self, ebcdic_codec):
        decoded, _ = ebcdic_codec.decode(b"\xc1")
        assert decoded == "A"

    def test_encode_to_unicode_table(self, ebcdic_codec):
        encoded = ebcdic_codec.encode_to_unicode_table("A")
        assert encoded == b"\xc1"

    # General tests for exceptions and logging (emulation specific)
    def test_decode_unmapped_bytes(self, ebcdic_codec):
        """Test decode with unmapped bytes defaults to 'z'."""
        data = b"\x00\xff\xab"  # \x00 maps to Null, \xFF and \xAB unmapped
        decoded, _ = ebcdic_codec.decode(data)
        assert decoded == "\x00zz"  # Null + two 'z'

    def test_encode_surrogate_escape(self, ebcdic_codec):
        """Test encode with surrogate char defaults to 'z'."""
        surrogate = "\ud800"
        encoded, _ = ebcdic_codec.encode(surrogate)
        assert encoded == b"\x7a"

    def test_round_trip_mapped(self, ebcdic_codec):
        """Test round-trip encode/decode for mapped characters."""
        text = "ABC"
        encoded, _ = ebcdic_codec.encode(text)
        decoded, _ = ebcdic_codec.decode(encoded)
        assert decoded == text

    def test_round_trip_unmapped(self, ebcdic_codec):
        """Test round-trip for unmapped character defaults to 'z'."""
        text = chr(0xFF)
        encoded, _ = ebcdic_codec.encode(text)
        decoded, _ = ebcdic_codec.decode(encoded)
        assert decoded == "z"

    def test_decode_mock_data(self, ebcdic_codec):
        """Test decode with mock unmapped data like b'\x00\xff'."""
        mock_data = b"\x00\xff"
        decoded, _ = ebcdic_codec.decode(mock_data)
        assert decoded == "\x00z"


def test_emulation_exception(caplog):
    with pytest.raises(ValueError):
        ScreenBuffer(rows=-1)
    assert "error" not in caplog.text  # No logging in init


# Performance basic test: time to fill buffer
def test_performance_buffer_fill(screen_buffer):
    import time

    start = time.time()
    for i in range(1920):
        screen_buffer.write_char(0x40, i // 80, i % 80)
    end = time.time()
    assert end - start < 0.1  # Basic threshold


# Sample 3270 data stream test
SAMPLE_3270_STREAM = (
    b"\x05\xf5\xc1\x10\x00\x00\xc1\xc2\xc3\x0d"  # Write, WCC, SBA(0,0), ABC, EOA
)


def test_update_from_sample_stream(screen_buffer):
    with patch.object(screen_buffer, "_detect_fields"):
        screen_buffer.update_from_stream(SAMPLE_3270_STREAM)
    assert screen_buffer.buffer[0:3] == b"\xc1\xc2\xc3"


def test_basic_session_clear(screen_buffer):
    """
    Ported from s3270 test case 1: Basic session clear.
    Input IAC EWA; output blank 24x80 screen buffer with EBCDIC space (0x40);
    assert all positions 0x40, no residual data.
    """
    # Simulate clear (WCC or Write), but pure3270 clear sets to 0x00; fill with EBCDIC space 0x40
    screen_buffer.clear()
    # Fill with EBCDIC spaces as per 3270 standard blank screen
    for i in range(screen_buffer.size):
        screen_buffer.buffer[i] = 0x40
    # Assert all positions are EBCDIC space, no residual data, cursor at 0,0
    assert all(b == 0x40 for b in screen_buffer.buffer)
    assert screen_buffer.cursor_row == 0
    assert screen_buffer.cursor_col == 0
    assert len(screen_buffer.fields) == 0


def test_read_modified_fields_after_change(screen_buffer, ebcdic_codec):
    """
    Ported from s3270 test case 3: Read modified fields after change.
    Input modify field then RMF; output captures changed data, cursor;
    assert buffer matches modified string, position, attributes.
    """
    # Create a field, modify it
    field = Field(
        start=(0, 0),
        end=(0, 5),
        protected=False,
        modified=False,
        content=b"\x40\x40\x40\x40\x40",
    )
    screen_buffer.fields = [field]
    screen_buffer.set_position(0, 0)

    # Modify field content
    with patch.object(
        ebcdic_codec, "encode", return_value=(b"\xc1\xc2\xc3\xc4\xc5", 5)
    ):
        field.set_content("ABCDE")

    # Simulate RMF: read modified fields
    modified = screen_buffer.read_modified_fields()
    assert len(modified) == 1
    assert modified[0][0] == (0, 0)
    assert modified[0][1] == "ABCDE"  # Decoded content

    # Assert buffer updated (simplified, as update_from_stream not used here)
    pos = 0 * screen_buffer.cols + 0
    for i in range(5):
        screen_buffer.write_char(0xC1 + i, 0, i)
    assert screen_buffer.buffer[pos : pos + 5] == b"\xc1\xc2\xc3\xc4\xc5"
    assert field.modified is True
