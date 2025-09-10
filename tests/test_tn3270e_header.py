import pytest
from pure3270.protocol.tn3270e_header import TN3270EHeader
from pure3270.protocol.utils import (
    TN3270_DATA,
    SCS_DATA,
    TN3270E_RSF_NO_RESPONSE,
    TN3270E_RSF_ERROR_RESPONSE,
)


class TestTN3270EHeader:
    def test_init_default(self):
        """Test default initialization."""
        header = TN3270EHeader()
        assert header.data_type == TN3270_DATA
        assert header.request_flag == 0
        assert header.response_flag == TN3270E_RSF_NO_RESPONSE
        assert header.seq_number == 0

    def test_init_custom(self):
        """Test custom initialization."""
        header = TN3270EHeader(
            data_type=SCS_DATA,
            request_flag=0x01,
            response_flag=TN3270E_RSF_ERROR_RESPONSE,
            seq_number=1234,
        )
        assert header.data_type == SCS_DATA
        assert header.request_flag == 0x01
        assert header.response_flag == TN3270E_RSF_ERROR_RESPONSE
        assert header.seq_number == 1234

    def test_to_bytes(self):
        """Test conversion to bytes."""
        header = TN3270EHeader(
            data_type=SCS_DATA,
            request_flag=0x01,
            response_flag=TN3270E_RSF_ERROR_RESPONSE,
            seq_number=1234,
        )
        bytes_data = header.to_bytes()
        assert len(bytes_data) == 5
        assert bytes_data == b"\x01\x01\x01\x04\xd2"

    def test_from_bytes(self):
        """Test parsing from bytes."""
        bytes_data = b"\x01\x01\x01\x04\xd2"
        header = TN3270EHeader.from_bytes(bytes_data)
        assert header is not None
        assert header.data_type == SCS_DATA
        assert header.request_flag == 0x01
        assert header.response_flag == TN3270E_RSF_ERROR_RESPONSE
        assert header.seq_number == 1234

    def test_from_bytes_invalid(self):
        """Test parsing invalid bytes."""
        # Too short
        header = TN3270EHeader.from_bytes(b"\x01\x01")
        assert header is None

        # Invalid struct
        header = TN3270EHeader.from_bytes(b"\x01\x01\x01\x01\xff")
        assert header is not None  # This should still work

    def test_repr(self):
        """Test string representation."""
        header = TN3270EHeader(
            data_type=SCS_DATA,
            request_flag=0x01,
            response_flag=TN3270E_RSF_ERROR_RESPONSE,
            seq_number=1234,
        )
        repr_str = repr(header)
        assert "SCS_DATA" in repr_str
        assert "ERROR_RESPONSE" in repr_str  # Should show ERROR_RESPONSE now
        assert "seq_number=1234" in repr_str

    def test_type_checks(self):
        """Test type checking methods."""
        # TN3270_DATA header
        tn3270_header = TN3270EHeader(data_type=TN3270_DATA)
        assert tn3270_header.is_tn3270_data()
        assert not tn3270_header.is_scs_data()
        assert not tn3270_header.is_response()

        # SCS_DATA header
        scs_header = TN3270EHeader(data_type=SCS_DATA)
        assert not scs_header.is_tn3270_data()
        assert scs_header.is_scs_data()
        assert not scs_header.is_response()

        # RESPONSE header with error
        response_header = TN3270EHeader(
            data_type=0x02, response_flag=TN3270E_RSF_ERROR_RESPONSE  # RESPONSE
        )
        assert not response_header.is_tn3270_data()
        assert not response_header.is_scs_data()
        assert response_header.is_response()
        assert response_header.is_error_response()

    def test_get_data_type_name(self):
        """Test getting data type names."""
        header = TN3270EHeader(data_type=TN3270_DATA)
        assert header.get_data_type_name() == "TN3270_DATA"

        header = TN3270EHeader(data_type=SCS_DATA)
        assert header.get_data_type_name() == "SCS_DATA"

        # Unknown type
        header = TN3270EHeader(data_type=0xFF)
        assert header.get_data_type_name() == "UNKNOWN(0xff)"
