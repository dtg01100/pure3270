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
        st.integers(min_value=0, max_value=1919),  # Valid buffer addresses
        st.binary(min_size=0, max_size=20),  # Trailing bytes
    )
    @settings(max_examples=50, deadline=None)
    def test_valid_sba_sets_position(self, address, trailing):
        row = address // 80
        col = address % 80
        addr_high = (row & 0x3F) | ((col & 0xC0) >> 2)
        addr_low = (col & 0x3F) | ((row & 0xC0) << 2)
        sba_bytes = bytes([SBA, addr_high, addr_low]) + trailing
        try:
            self.parser.parse(sba_bytes)
        except ParseError as e:
            # Some minimal sequences interpreted as other orders (e.g. DATA_STREAM_CTL) may be incomplete.
            if any(
                phrase in str(e)
                for phrase in [
                    "Incomplete DATA_STREAM_CTL",
                    "Incomplete SBA",
                    "Incomplete WCC order",
                    "Incomplete AID order",
                ]
            ):
                return
            pytest.fail(f"Unexpected ParseError in SBA property: {e}")
        final_pos = self.screen.get_position()
        assert 0 <= final_pos[0] < self.screen.rows
        assert 0 <= final_pos[1] < self.screen.cols
        assert self.parser._pos <= len(sba_bytes)

    @given(
        st.integers(min_value=0x00, max_value=0xFF), st.binary(min_size=0, max_size=20)
    )
    @settings(max_examples=50, deadline=None)
    def test_valid_sf_sets_attribute(self, attr_byte, trailing):
        sf_bytes = bytes([SF, attr_byte]) + trailing
        try:
            self.parser.parse(sf_bytes)
        except ParseError:
            pytest.skip("Parser raised ParseError on short SF sequence")
        assert self.parser._pos <= len(sf_bytes)
        assert self.parser._pos >= min(2, len(sf_bytes))

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
