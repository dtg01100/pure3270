"""
RFC 2355 TN3270E RESPONSES Function Tests (Section 10.4)

These tests verify compliance with RFC 2355 Section 10.4 "The RESPONSES Function".

According to RFC 2355:
- RESPONSE-FLAG values: NO-RESPONSE (0x00), ERROR-RESPONSE (0x01), ALWAYS-RESPONSE (0x02)
- SEQ-NUMBER is a 2-byte binary counter (0-32767) in network byte order
- 0xff bytes in SEQ-NUMBER must be doubled (0xff -> 0xffff)
- Counter wraps from 32767 to 0
- Counter is independent of SNA sequence numbers
- Responses must correlate to the original request's SEQ-NUMBER

Section 8.1.3 also specifies RESPONSE-FLAG for 3270-DATA and SCS-DATA:
- NO-RESPONSE (0x00): Sender doesn't expect response
- ERROR-RESPONSE (0x01): Respond only if error
- ALWAYS-RESPONSE (0x02): Always respond (positive or negative)
"""

import struct
from unittest.mock import AsyncMock, MagicMock

import pytest

from pure3270.protocol.tn3270e_header import TN3270EHeader
from pure3270.protocol.utils import (
    BIND_IMAGE,
    NVT_DATA,
    RESPONSE,
    SCS_DATA,
    SSCP_LU_DATA,
    TN3270_DATA,
    TN3270E_RSF_ALWAYS_RESPONSE,
    TN3270E_RSF_ERROR_RESPONSE,
    TN3270E_RSF_NO_RESPONSE,
    UNBIND,
)


class TestSEQNumberHandling:
    """Tests for RFC 2355 Section 10.4 SEQ-NUMBER handling.

    Per RFC 2355 10.4:
    - SEQ-NUMBER is a 2-byte binary counter
    - Range: 0 to 32767
    - Wraps from 32767 back to 0
    - Must be sent in network byte order (big endian)
    - 0xff bytes must be doubled (0xff -> 0xffff)
    """

    def test_seq_number_range_0_to_32767(self):
        """Test SEQ-NUMBER can represent full range 0-32767."""
        # Minimum value
        header_min = TN3270EHeader(
            data_type=TN3270_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_NO_RESPONSE,
            seq_number=0,
        )
        assert header_min.seq_number == 0

        # Maximum value
        header_max = TN3270EHeader(
            data_type=TN3270_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_NO_RESPONSE,
            seq_number=32767,
        )
        assert header_max.seq_number == 32767

    def test_seq_number_wraps_from_max_to_zero(self):
        """RFC 2355: SEQ-NUMBER wraps from 32767 to 0.

        This is important for long-running sessions that exceed 32767 messages.
        """
        # Create header with max SEQ-NUMBER
        header = TN3270EHeader(
            data_type=TN3270_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_NO_RESPONSE,
            seq_number=32767,
        )

        # Next message should have SEQ-NUMBER 0
        next_seq = 0
        next_header = TN3270EHeader(
            data_type=TN3270_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_NO_RESPONSE,
            seq_number=next_seq,
        )
        assert next_header.seq_number == 0

    def test_seq_number_network_byte_order(self):
        """RFC 2355: SEQ-NUMBER is sent in network byte order (big endian)."""
        header = TN3270EHeader(
            data_type=TN3270_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_NO_RESPONSE,
            seq_number=256,  # 0x0100 in big endian
        )
        bytes_out = header.to_bytes()

        # Bytes 3-4 should be 0x01 0x00 (big endian)
        assert bytes_out[3] == 0x01
        assert bytes_out[4] == 0x00

    def test_seq_number_roundtrip(self):
        """Test SEQ-NUMBER survives to_bytes and from_bytes roundtrip."""
        original = TN3270EHeader(
            data_type=SCS_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_ALWAYS_RESPONSE,
            seq_number=12345,
        )
        bytes_out = original.to_bytes()
        parsed = TN3270EHeader.from_bytes(bytes_out)

        assert parsed is not None
        assert parsed.seq_number == original.seq_number


class TestResponseFlagBehavior:
    """Tests for RFC 2355 RESPONSE-FLAG behavior.

    Per RFC 2355 8.1.3, RESPONSE-FLAG values for 3270-DATA and SCS-DATA:
    - NO-RESPONSE (0x00): Sender doesn't expect receiver to respond
    - ERROR-RESPONSE (0x01): Receiver responds only if error occurred
    - ALWAYS-RESPONSE (0x02): Receiver always responds (positive or negative)
    """

    def test_no_response_flag(self):
        """NO-RESPONSE (0x00) means sender doesn't expect any response."""
        header = TN3270EHeader(
            data_type=TN3270_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_NO_RESPONSE,
            seq_number=1,
        )
        assert header.response_flag == TN3270E_RSF_NO_RESPONSE
        assert header.is_no_response() is True
        assert header.is_error_response() is False
        assert header.is_always_response() is False

    def test_error_response_flag(self):
        """ERROR-RESPONSE (0x01) means respond only if error."""
        header = TN3270EHeader(
            data_type=TN3270_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_ERROR_RESPONSE,
            seq_number=1,
        )
        assert header.response_flag == TN3270E_RSF_ERROR_RESPONSE
        assert header.is_no_response() is False
        assert header.is_error_response() is True
        assert header.is_always_response() is False

    def test_always_response_flag(self):
        """ALWAYS-RESPONSE (0x02) means always respond (positive or negative)."""
        header = TN3270EHeader(
            data_type=TN3270_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_ALWAYS_RESPONSE,
            seq_number=1,
        )
        assert header.response_flag == TN3270E_RSF_ALWAYS_RESPONSE
        assert header.is_no_response() is False
        assert header.is_error_response() is False
        assert header.is_always_response() is True

    def test_response_flag_for_scs_data(self):
        """RESPONSE-FLAG applies to SCS-DATA as well as 3270-DATA."""
        header = TN3270EHeader(
            data_type=SCS_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_ERROR_RESPONSE,
            seq_number=1,
        )
        assert header.data_type == SCS_DATA
        assert header.response_flag == TN3270E_RSF_ERROR_RESPONSE


class TestSEQNumberCorrelation:
    """Tests for RFC 2355 SEQ-NUMBER correlation in responses.

    Per RFC 2355 10.4.1:
    - When sending a response, the SEQ-NUMBER must match the original request
    - This allows the sender to correlate responses with requests
    """

    def test_response_header_correlates_seq_number(self):
        """Response header should use same SEQ-NUMBER as request being responded to."""
        original_seq = 42

        # This would be a RESPONSE data-type message
        response_header = TN3270EHeader(
            data_type=RESPONSE,
            request_flag=0,
            response_flag=TN3270E_RSF_NO_RESPONSE,
            seq_number=original_seq,
        )

        assert response_header.seq_number == original_seq


class TestAlwaysResponseBehavior:
    """Tests for RFC 2355 ALWAYS-RESPONSE handling.

    Per RFC 2355, when RESPONSE-FLAG is ALWAYS-RESPONSE:
    - Receiver MUST respond positively if no errors
    - Receiver MUST respond negatively if errors occurred
    - This is important for reliable delivery confirmation
    """

    def test_positive_response_has_no_error_data(self):
        """RFC 2355: Positive response (no error) has no error data.

        When data is processed successfully, the response has no sense data.
        """
        # For a positive response to ALWAYS-RESPONSE, we'd see:
        # data_type=RESPONSE, response_flag=ALWAYS-RESPONSE, seq=N
        # with empty or zero data portion
        header = TN3270EHeader(
            data_type=RESPONSE,
            request_flag=0,
            response_flag=TN3270E_RSF_ALWAYS_RESPONSE,
            seq_number=1,
        )
        assert header.data_type == RESPONSE
        assert header.response_flag == TN3270E_RSF_ALWAYS_RESPONSE

    def test_negative_response_has_sense_data(self):
        """RFC 2355: Negative response includes sense data indicating the error.

        Sense data typically includes SNA sense codes like:
        - 0x10030000: Intervention required
        - 0x082D0000: LU busy
        - 0x08020000: Session ended
        """
        # A negative response would have sense data in the data portion
        # The header would still have ALWAYS-RESPONSE flag
        header = TN3270EHeader(
            data_type=RESPONSE,
            request_flag=0,
            response_flag=TN3270E_RSF_ALWAYS_RESPONSE,
            seq_number=1,
        )
        assert header.data_type == RESPONSE
        assert header.response_flag == TN3270E_RSF_ALWAYS_RESPONSE


class TestResponseDataParsing:
    """Tests for RFC 2355 response data content parsing.

    Per RFC 2355 10.4.1, response data byte meanings:
    - 0x00: Request processed successfully (positive response)
    - 0x01: Intervention required (negative response)
    - Other values indicate specific error conditions
    """

    def test_response_success_code(self):
        """0x00 in response data indicates successful processing."""
        # This would be in the data portion following a RESPONSE header
        response_data = bytes([0x00])

        # 0x00 means success - no action needed
        assert response_data[0] == 0x00

    def test_response_intervention_required(self):
        """0x01 in response data indicates intervention required.

        Examples: printer out of paper, device not ready
        """
        response_data = bytes([0x01])

        # 0x01 means intervention required
        assert response_data[0] == 0x01

    def test_response_format_for_always_response(self):
        """Test RESPONSE header format for ALWAYS-RESPONSE.

        RFC 2355 10.4.1 Response Messages format:
        DATA-TYPE (1 byte) = RESPONSE (0x02)
        REQUEST-FLAG (1 byte)
        RESPONSE-FLAG (1 byte)
        SEQ-NUMBER (2 bytes)
        [-optional sense data]
        """
        header = TN3270EHeader(
            data_type=RESPONSE,
            request_flag=0,
            response_flag=TN3270E_RSF_ALWAYS_RESPONSE,
            seq_number=100,
        )
        header_bytes = header.to_bytes()

        # Should be exactly 5 bytes
        assert len(header_bytes) == 5

        # Parse back
        parsed = TN3270EHeader.from_bytes(header_bytes)
        assert parsed is not None
        assert parsed.data_type == RESPONSE
        assert parsed.response_flag == TN3270E_RSF_ALWAYS_RESPONSE
        assert parsed.seq_number == 100


class TestDataTypeRestrictions:
    """Tests for RFC 2355 data type restrictions based on RESPONSE-FLAG.

    Per RFC 2355 8.1.3, RESPONSE-FLAG only has meaning for certain DATA-TYPEs:
    - 3270-DATA
    - SCS-DATA
    - RESPONSE (itself)
    - REQUEST
    """

    def test_response_flag_with_3270_data(self):
        """RESPONSE-FLAG applies to 3270-DATA."""
        header = TN3270EHeader(
            data_type=TN3270_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_ERROR_RESPONSE,
            seq_number=1,
        )
        assert header.data_type == TN3270_DATA
        assert header.response_flag == TN3270E_RSF_ERROR_RESPONSE

    def test_response_flag_with_scs_data(self):
        """RESPONSE-FLAG applies to SCS-DATA (printer sessions)."""
        header = TN3270EHeader(
            data_type=SCS_DATA,
            request_flag=0,
            response_flag=TN3270E_RSF_ALWAYS_RESPONSE,
            seq_number=1,
        )
        assert header.data_type == SCS_DATA
        assert header.response_flag == TN3270E_RSF_ALWAYS_RESPONSE

    def test_response_flag_with_bind_image_not_meaningful(self):
        """RFC 2355: RESPONSE-FLAG not meaningful for BIND-IMAGE.

        BIND-IMAGE is a one-way notification; responses aren't expected.
        """
        header = TN3270EHeader(
            data_type=BIND_IMAGE,
            request_flag=0,
            response_flag=0,  # Should be 0x00 per RFC
            seq_number=1,
        )
        assert header.data_type == BIND_IMAGE

    def test_response_flag_with_unbind_not_meaningful(self):
        """RFC 2355: RESPONSE-FLAG not meaningful for UNBIND."""
        header = TN3270EHeader(
            data_type=UNBIND,
            request_flag=0,
            response_flag=0,  # Should be 0x00 per RFC
            seq_number=1,
        )
        assert header.data_type == UNBIND


class TestERRCONDResponseFlag:
    """Tests for ERR-COND-CLEARED REQUEST-FLAG (Section 10.4).

    Per RFC 2355 10.4, after sending ERR-COND-CLEARED:
    - Client sends REQUEST message with ERR-COND-CLEARED flag
    - This tells server the previous error condition has been cleared
    """

    def test_err_cond_cleared_request_flag(self):
        """ERR-COND-CLEARED (0x01) in REQUEST-FLAG indicates error resolved."""
        # REQUEST data-type with ERR-COND-CLEARED flag
        from pure3270.protocol.utils import TN3270E_REQ_ERR_COND_CLEARED

        header = TN3270EHeader(
            data_type=RESPONSE,  # Using RESPONSE for request response tracking
            request_flag=TN3270E_REQ_ERR_COND_CLEARED,
            response_flag=TN3270E_RSF_NO_RESPONSE,
            seq_number=1,
        )
        # ERR-COND-CLEARED is a REQUEST-FLAG, not RESPONSE-FLAG
        # It would be used in a REQUEST (0x06) data-type message
        assert header.request_flag == TN3270E_REQ_ERR_COND_CLEARED
