import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import (
    EOA,
    SBA,
    SF,
    STRUCTURED_FIELD,
    WCC,
    DataStreamParser,
    ParseError,
)


@pytest.mark.property
class TestDataStreamProperties:
    """Property-based tests for DataStreamParser edge cases and invariants."""

    def setup_method(self):
        self.screen = ScreenBuffer(rows=24, cols=80)
        self.parser = DataStreamParser(self.screen)

    @given(st.binary(min_size=1, max_size=200))
    @settings(max_examples=50, deadline=None)
    def test_no_unhandled_exception_on_any_input(self, data):
        """Property: Parser never raises unexpected exceptions; limited ParseError OK for clearly incomplete minimal orders."""
        try:
            self.parser.parse(data)
        except ParseError as e:
            # Allow specific incomplete / overflow conditions for short streams
            msg = str(e)
            if (len(data) <= 6 and ("Incomplete" in msg or "Overflow" in msg)) or any(
                phrase in msg
                for phrase in [
                    "Incomplete WCC order",
                    "Incomplete AID order",
                    "Incomplete DATA_STREAM_CTL order",
                    "Incomplete SBA order",
                    "Incomplete SF order",
                ]
            ):
                return
            pytest.fail(f"Unexpected ParseError: {e}")

    @given(st.binary(min_size=1, max_size=200))
    def test_position_advances_progressively(self, data):
        """Property: Parser position never exceeds input and advances >= one byte unless early ParseError on tiny inputs."""
        self.parser._data = data
        self.parser._pos = 0
        try:
            self.parser.parse(data)
        except ParseError:
            # Accept early termination for minimal incomplete sequences
            pass
        assert 0 <= self.parser._pos <= len(data)
        if len(data) > 2:  # For larger inputs expect some advancement
            assert self.parser._pos > 0

    @given(
        st.integers(
            min_value=0, max_value=1919
        ),  # Valid 12-bit buffer addresses for a 24x80 screen
    )
    @settings(max_examples=50, deadline=None)
    def test_valid_sba_sets_position(self, address):
        # Correctly encode a 12-bit address into two bytes, where the lower 6 bits of each byte are used.
        addr_high = (address >> 6) & 0x3F
        addr_low = address & 0x3F
        sba_bytes = bytes([SBA, addr_high, addr_low])
        try:
            self.parser.parse(sba_bytes)
        except ParseError as e:
            pytest.fail(f"Unexpected ParseError in SBA property: {e}")

        final_row, final_col = self.screen.get_position()

        expected_row = address // 80
        expected_col = address % 80

        assert final_row == expected_row
        assert final_col == expected_col

    @given(
        st.integers(
            min_value=0, max_value=1919
        ),  # Valid 14-bit buffer addresses for a 24x80 screen
    )
    @settings(max_examples=50, deadline=None)
    def test_valid_sba_14bit_sets_position(self, address):
        from pure3270.emulation.addressing import AddressingMode

        self.parser.addressing_mode = AddressingMode.MODE_14_BIT

        # 14-bit addressing uses a simple 2-byte big-endian integer.
        sba_bytes = bytes([SBA]) + address.to_bytes(2, "big")
        try:
            self.parser.parse(sba_bytes)
        except ParseError as e:
            pytest.fail(f"Unexpected ParseError in 14-bit SBA property: {e}")

        final_row, final_col = self.screen.get_position()
        expected_row = address // 80
        expected_col = address % 80

        assert final_row == expected_row
        assert final_col == expected_col

    @given(st.integers(min_value=0x00, max_value=0xFF))
    @settings(max_examples=50, deadline=None)
    def test_valid_sf_sets_attribute(self, attr_byte):
        sf_bytes = bytes([SF, attr_byte])
        self.screen.set_position(0, 0)  # Reset position
        self.parser.parse(sf_bytes)
        assert self.parser._pos == 2

    def test_extended_attributes_are_applied_to_fields(self):
        # This test bypasses the parser to test the screen buffer logic directly.

        # 1. Manually set a basic and an extended attribute at the same position.
        self.screen.set_attribute(0xC1, row=0, col=5)  # Basic attribute for a field
        self.screen.set_extended_attribute(
            row=0, col=5, attr_type="color", value=0xF2
        )  # Red

        # 2. Manually trigger field detection.
        self.screen._detect_fields()

        # 3. Assert that one field was created and has the correct attributes.
        assert len(self.screen.fields) == 1
        field = self.screen.fields[0]
        assert field.start == (0, 5)
        assert field.color == 0xF2

    @given(st.integers(min_value=0x00, max_value=0xFF), st.booleans())
    @settings(max_examples=50, deadline=None)
    def test_wcc_handling(self, wcc_byte, should_clear):
        if should_clear:
            wcc_byte |= 0x01
        wcc_bytes = bytes([WCC, wcc_byte]) + bytes([EOA])
        self.screen.buffer = bytearray(b"\x41" * len(self.screen.buffer))
        try:
            self.parser.parse(wcc_bytes)
        except ParseError:
            pytest.skip("Parser raised ParseError on minimal WCC")
        if wcc_byte & 0x01:
            assert all(b == 0x40 for b in self.screen.buffer)
        else:
            # At minimum, screen remains within size invariant
            assert len(self.screen.buffer) == self.screen.rows * self.screen.cols
        assert getattr(self.parser, "wcc", None) == wcc_byte

    @given(
        st.integers(min_value=1, max_value=10),  # SF length
        st.integers(min_value=0x00, max_value=0xFF),  # SF type
        st.binary(min_size=0, max_size=20),  # Payload
    )
    @settings(max_examples=50, deadline=None)
    def test_structured_field_skipped_on_unknown(self, length, sf_type, payload):
        """Property: Unknown structured fields are skipped, position advances fully."""
        # Build minimal SF: 0x3C (SF) + length (2 bytes, big-endian) + type + payload
        sf_length = 3 + len(payload)  # type + payload
        length_bytes = sf_length.to_bytes(2, "big")
        sf_bytes = bytes([STRUCTURED_FIELD]) + length_bytes + bytes([sf_type]) + payload
        pos_before = self.parser._pos
        self.parser._data = sf_bytes
        self.parser.parse(sf_bytes)
        # Should advance past entire SF
        assert self.parser._pos == len(sf_bytes)
        # For unknown type, no crash, just skipped

    @given(st.binary(min_size=10, max_size=50))  # Enough for malformed
    @settings(max_examples=50, deadline=None)
    def test_malformed_input_no_overflow(self, data):
        """Property: Malformed input (e.g., incomplete orders) does not cause infinite loop or pos overflow."""
        # Inject malformed SBA (only 1 address byte)
        malformed = data[:5] + bytes([SBA]) + data[5:]  # Insert incomplete SBA
        initial_pos = 0
        self.parser._data = malformed
        self.parser._pos = initial_pos
        try:
            self.parser.parse(malformed)
        except ParseError as e:
            # Accept early termination on any incomplete order or overflow encountered while parsing malformed input.
            if "Incomplete" in str(e) or "Overflow" in str(e):
                return
            pytest.fail(f"Unexpected ParseError in malformed property: {e}")
        # Position should not exceed length (no overflow) if parse completes
        assert self.parser._pos <= len(malformed)
        # And advanced at least some
        assert self.parser._pos > initial_pos
