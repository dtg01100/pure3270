"""
Comprehensive tests for TN3270E negotiation inference.

This file consolidates all TN3270E inference tests from across the test suite
to eliminate redundancy and provide comprehensive coverage.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from pure3270.protocol.negotiator import Negotiator


class TestTN3270ENegotiationInference:
    """Comprehensive tests for TN3270E negotiation inference from traces."""

    @pytest.mark.parametrize(
        "trace,expected,description",
        [
            # Basic test cases
            (b"", False, "Empty trace should not infer TN3270E"),
            (b"\xff\xfb\x19", True, "IAC WILL EOR should infer TN3270E support"),
            (
                b"\xff\xfc\x24",
                False,
                "IAC WONT TN3270E should not infer TN3270E support",
            ),
            (
                b"\xff\xfb\x19\xff\xfc\x24",
                False,
                "Conflicting signals should not infer TN3270E",
            ),
            # Additional edge cases
            (b"\xff\xfd\x24", False, "IAC DO TN3270E alone should not infer support"),
            (
                b"\xff\xfe\xe0\x00\x00\x00\x00",
                False,
                "IAC SUBNEG with TN3270E device type might be valid",
            ),
            # Complex traces
            (
                b"\xff\xfb\x19\xff\xfd\x03\xff\xfe\x24",
                False,
                "Complex trace with EOR, SUPPRESS_GO_AHEAD, and TN3270E rejection",
            ),
            # Malformed data
            (b"\xff\xfa\x19\x00", False, "Malformed IAC SB sequence"),
            (b"\xff\xfb", False, "Incomplete IAC WILL sequence"),
            (b"\xff\xfc", False, "Incomplete IAC WONT sequence"),
            # Valid single options
            (b"\xff\xfb\x19", True, "IAC WILL EOR only (should support TN3270E)"),
            (
                b"\xff\xfc\x24",
                False,
                "IAC WONT TN3270E only (should not support TN3270E)",
            ),
            # Multiple conflicting options
            (
                b"\xff\xfb\x19\xff\xfc\x24\xff\xfb\x19",
                False,
                "Multiple conflicts with final rejection",
            ),
            (
                b"\xff\xfc\x24\xff\xfb\x19\xff\xfc\x24",
                False,
                "Rejection before and after acceptance",
            ),
        ],
    )
    def test_infer_tn3270e_from_trace_comprehensive(self, trace, expected, description):
        """Comprehensive parametrized test for TN3270E inference from traces."""
        # Create a minimal negotiator (screen_buffer not needed for inference)
        negotiator = Negotiator(None, None, screen_buffer=type("SB", (), {})())  # type: ignore[arg-type]

        result = negotiator.infer_tn3270e_from_trace(trace)

        assert (
            result is expected
        ), f"Failed for: {description}\n  Trace: {trace!r}\n  Expected: {expected}\n  Got: {result}"

    def test_infer_tn3270e_from_trace_with_real_negotiator(self):
        """Test inference using a real negotiator instance with proper mocks."""
        # Create a proper screen buffer mock
        screen_buffer = Mock()

        # Create negotiator instance with real mocks
        reader = AsyncMock()
        writer = AsyncMock()
        negotiator = Negotiator(reader, writer, screen_buffer=screen_buffer)

        # Test the basic cases with a real negotiator
        test_cases = [
            (b"", False, "Empty trace"),
            (b"\xff\xfb\x19", True, "EOR only"),
            (b"\xff\xfc\x24", False, "TN3270E rejection"),
        ]

        for trace, expected, description in test_cases:
            result = negotiator.infer_tn3270e_from_trace(trace)
            assert result is expected, f"Failed for {description}"

    def test_infer_tn3270e_edge_cases_with_state_isolation(self):
        """Test edge cases with proper state isolation between tests."""
        test_cases = [
            # Test with various malformed sequences
            (b"\xff", False, "Single IAC byte"),
            (b"\xff\x00", False, "IAC followed by null"),
            (b"\xff\xff", False, "Double IAC"),
            # Test with valid but unusual sequences
            (b"\xff\xfb\x00", False, "WILL BINARY (not EOR)"),
            (b"\xff\xfb\x01", False, "WILL ECHO (not EOR)"),
            (b"\xff\xfb\x03", False, "WILL SUPPRESS_GO_AHEAD (not EOR)"),
            # Test with EOR in different positions
            (b"\x00\xff\xfb\x19\x00", True, "EOR in middle of data"),
            (b"\xff\xfb\x19\x00\x00", True, "EOR at start with trailing data"),
        ]

        for trace, expected, description in test_cases:
            # Create fresh negotiator for each test to ensure state isolation
            negotiator = Negotiator(None, None, screen_buffer=type("SB", (), {})())  # type: ignore[arg-type]

            result = negotiator.infer_tn3270e_from_trace(trace)
            assert (
                result is expected
            ), f"Failed for {description}: got {result}, expected {expected}"
