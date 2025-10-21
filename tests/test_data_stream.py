import platform
from unittest.mock import MagicMock, patch

import pytest

from pure3270.protocol.data_stream import SnaResponse  # Import SnaResponse class
from pure3270.protocol.data_stream import (
    BIND_SF_TYPE,
    PRINTER_STATUS_SF_TYPE,
    SNA_COMMAND_RESPONSE,
    SNA_DATA_RESPONSE,
    SNA_RESPONSE_DATA_TYPE,
    SNA_RESPONSE_SF_TYPE,
    SNA_SENSE_CODE_INVALID_FORMAT,
    SNA_SENSE_CODE_NOT_SUPPORTED,
    SNA_SENSE_CODE_SESSION_FAILURE,
    SNA_SENSE_CODE_SUCCESS,
    SOH,
    SOH_DEVICE_END,
    SOH_INTERVENTION_REQUIRED,
    SOH_SUCCESS,
    ParseError,
)
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.utils import SNA_RESPONSE  # Import SNA_RESPONSE
from pure3270.protocol.utils import (
    BIND_IMAGE,
    NVT_DATA,
    PRINT_EOJ,
    PRINTER_STATUS_DATA_TYPE,
    REQUEST,
    RESPONSE,
    SCS_DATA,
    SSCP_LU_DATA,
    TN3270_DATA,
    UNBIND,
)


@pytest.mark.skipif(
    platform.system() != "Linux", reason="Memory limiting only supported on Linux"
)
class TestDataStreamParser:
    def test_init(self, data_stream_parser, memory_limit_500mb):
        assert data_stream_parser.screen is not None
        assert data_stream_parser._data == b""
        assert data_stream_parser._pos == 0
        assert data_stream_parser.wcc is None
        assert data_stream_parser.aid is None

    def test_parse_wcc(self, data_stream_parser, memory_limit_500mb):
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
        with (
            patch.object(data_stream_parser.screen, "set_attribute") as mock_set_attr,
            patch.object(data_stream_parser.screen, "set_position") as mock_set_pos,
            patch.object(
                data_stream_parser.screen, "get_position", return_value=(0, 0)
            ),
        ):
            data_stream_parser.parse(sample_data)
            mock_set_attr.assert_called_once_with(0x40)  # Test actual behavior
            # Parse method calls set_position(0,0) initially, then SF handler calls set_position(0,1)
            assert mock_set_pos.call_count == 2
            mock_set_pos.assert_any_call(0, 0)  # Initial position reset
            mock_set_pos.assert_any_call(0, 1)  # SF position advance

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
        sample_data = b"\xc1\xc2"  # Data characters A and B in EBCDIC
        with (
            patch.object(data_stream_parser.screen, "write_char") as mock_write_char,
            patch.object(
                data_stream_parser.screen, "get_position", return_value=(0, 0)
            ) as mock_get_pos,
            patch.object(data_stream_parser.screen, "set_position") as mock_set_pos,
        ):
            data_stream_parser.parse(sample_data)
            # Should write each character and advance position
            assert mock_write_char.call_count == 2
            mock_write_char.assert_any_call(0xC1, 0, 0)  # First character at (0,0)
            mock_write_char.assert_any_call(0xC2, 0, 0)  # Second character at (0,0)
            # Position should be set initially and advanced after each character
            assert mock_set_pos.call_count >= 3  # Initial + after each char

    def test_parse_bind_structured_field(self, data_stream_parser):
        # Structured field: 0x3C (SF_ID), Length (2 bytes), SF_Type (1 byte), Data
        # BIND_SF_TYPE = 0x28
        bind_data_payload = b"\x01\x02\x03\x04"  # Example BIND data
        sf_length = 1 + len(bind_data_payload)  # SF_Type + payload length
        sample_data = (
            b"\x3c"
            + sf_length.to_bytes(2, "big")
            + BIND_SF_TYPE.to_bytes(1, "big")
            + bind_data_payload
        )

        with patch.object(data_stream_parser, "_handle_bind_sf") as mock_handle_bind_sf:
            data_stream_parser.parse(sample_data)
            mock_handle_bind_sf.assert_called_once_with(bind_data_payload)

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

    def test_parse_structured_field(self, data_stream_parser):
        sample_data = (
            b"\x3c\x00\x03\x01\x02\x03"  # STRUCTURED_FIELD with length 3 and some data
        )
        data_stream_parser.parse(sample_data)
        # Assert that it doesn't raise an error and skips the structured field
        assert data_stream_parser._pos == len(sample_data)

    def test_parse_unknown_order_treated_as_text_data(self, data_stream_parser):
        sample_data = b"\xff"  # Unknown byte treated as text data
        with (
            patch.object(data_stream_parser.screen, "write_char") as mock_write_char,
            patch.object(
                data_stream_parser.screen, "get_position", return_value=(0, 0)
            ),
            patch.object(data_stream_parser.screen, "set_position"),
        ):
            data_stream_parser.parse(sample_data)
            # Unknown bytes are treated as text data, not as errors
            mock_write_char.assert_called_once_with(0xFF, 0, 0)

    def test_parse_ic_order(self, data_stream_parser):
        # Assuming IC is 0x0F
        sample_data = b"\x0f"
        with patch.object(
            data_stream_parser.screen, "move_cursor_to_first_input_field"
        ) as mock_move:
            data_stream_parser.parse(sample_data)
            mock_move.assert_called_once()

    def test_parse_pt_order(self, data_stream_parser):
        # Assuming PT is 0x0E
        sample_data = b"\x0e"
        with patch.object(data_stream_parser.screen, "program_tab") as mock_program_tab:
            data_stream_parser.parse(sample_data)
            mock_program_tab.assert_called_once()

    def test_parse_scs_data_type(self, data_stream_parser):
        sample_data = b"Some SCS data"
        mock_printer = MagicMock()
        data_stream_parser.printer = mock_printer  # Set printer for test
        with patch.object(
            data_stream_parser, "_handle_scs_data"
        ) as mock_handle_scs_data:
            data_stream_parser.parse(sample_data, data_type=SCS_DATA)
            mock_handle_scs_data.assert_called_once_with(sample_data)

    def test_parse_nvt_data_type(self, data_stream_parser):
        sample_data = b"Some NVT data"
        with patch("pure3270.protocol.data_stream.logger.info") as mock_logger_info:
            with patch.object(data_stream_parser.screen, "clear", new=MagicMock()):
                data_stream_parser.parse(sample_data, data_type=NVT_DATA)
                mock_logger_info.assert_called_once()
                assert "Received NVT_DATA" in mock_logger_info.call_args[0][0]
                data_stream_parser.screen.clear.assert_not_called()

    def test_parse_response_data_type(self, data_stream_parser):
        sample_data = b"Some RESPONSE data"
        with patch("pure3270.protocol.data_stream.logger.info") as mock_logger_info:
            data_stream_parser.parse(sample_data, data_type=RESPONSE)
            mock_logger_info.assert_called_once()
            assert "Received RESPONSE data type" in mock_logger_info.call_args[0][0]

    def test_parse_request_data_type(self, data_stream_parser):
        sample_data = b"Some REQUEST data"
        with patch("pure3270.protocol.data_stream.logger.info") as mock_logger_info:
            data_stream_parser.parse(sample_data, data_type=REQUEST)
            mock_logger_info.assert_called_once()
            assert "Received REQUEST data type" in mock_logger_info.call_args[0][0]

    def test_parse_sscp_lu_data_type(self, data_stream_parser):
        sample_data = b"Some SSCP_LU_DATA"
        with patch("pure3270.protocol.data_stream.logger.info") as mock_logger_info:
            data_stream_parser.parse(sample_data, data_type=SSCP_LU_DATA)
            mock_logger_info.assert_called_once()
            assert "Received SSCP_LU_DATA" in mock_logger_info.call_args[0][0]

    def test_parse_print_eoj_data_type(self, data_stream_parser):
        sample_data = b"Some PRINT_EOJ data"
        with patch("pure3270.protocol.data_stream.logger.info") as mock_logger_info:
            if data_stream_parser.printer is None:
                mock_printer = MagicMock()
                data_stream_parser.printer = mock_printer
            with patch.object(data_stream_parser.printer, "end_job") as mock_end_job:
                data_stream_parser.parse(sample_data, data_type=PRINT_EOJ)
                mock_logger_info.assert_called_once()
                mock_end_job.assert_called_once()

    def test_parse_bind_image_data_type(self, data_stream_parser):
        # BIND_IMAGE data type means the following data should be parsed as 3270 data,
        # specifically looking for a BIND Structured Field.
        # This test ensures it doesn't short-circuit and proceeds with 3270 parsing.
        # Structured field: 0x3C (SF_ID), Length (2 bytes), SF_Type (1 byte), Data
        bind_data_payload = b"\x01\x02\x03\x04"  # Example BIND data
        sf_length = 1 + len(bind_data_payload)  # SF_Type + payload length
        sample_data = (
            b"\x3c"
            + sf_length.to_bytes(2, "big")
            + BIND_SF_TYPE.to_bytes(1, "big")
            + bind_data_payload
        )

        with patch.object(data_stream_parser, "_handle_bind_sf") as mock_handle_bind_sf:
            data_stream_parser.parse(sample_data, data_type=BIND_IMAGE)
            mock_handle_bind_sf.assert_called_once_with(bind_data_payload)

    def test_parse_bind_image_structured_field_detailed(self, data_stream_parser):
        from pure3270.protocol.data_stream import (
            BIND_SF_SUBFIELD_PSC,
            BIND_SF_SUBFIELD_QUERY_REPLY_IDS,
            BindImage,
        )

        # BIND-IMAGE with PSC (rows=24, cols=80) and Query Reply IDs (0x02)
        # PSC subfield: Length (6), ID (0x01), Rows (0x0018), Cols (0x0050)
        psc_subfield = bytes(
            [0x06, BIND_SF_SUBFIELD_PSC, 0x00, 0x18, 0x00, 0x50]
        )  # 24 rows, 80 cols
        # Query Reply IDs subfield: Length (3), ID (0x02), Query ID (0x02)
        query_reply_ids_subfield = bytes([0x03, BIND_SF_SUBFIELD_QUERY_REPLY_IDS, 0x02])

        bind_data_payload = psc_subfield + query_reply_ids_subfield
        sf_length = 1 + len(bind_data_payload)  # SF_Type + payload length
        sample_data = (
            b"\x3c"
            + sf_length.to_bytes(2, "big")
            + BIND_SF_TYPE.to_bytes(1, "big")
            + bind_data_payload
        )

        # Mock negotiator if not present
        if data_stream_parser.negotiator is None:
            mock_negotiator = MagicMock()
            data_stream_parser.negotiator = mock_negotiator

        with patch.object(
            data_stream_parser.negotiator, "handle_bind_image"
        ) as mock_handle_bind_image:
            data_stream_parser.parse(sample_data, data_type=BIND_IMAGE)
            mock_handle_bind_image.assert_called_once()

    def test_parse_unhandled_data_type_defaults_to_tn3270_data(
        self, data_stream_parser
    ):
        sample_data = b"\x05\xc1"  # A simple write command
        unhandled_data_type = 0xFF  # An arbitrary unhandled data type

        # Create a mock that wraps the original method
        from unittest.mock import MagicMock

        from pure3270.protocol.data_stream import WRITE

        mock_handle_write = MagicMock(wraps=data_stream_parser._handle_write)
        # Store original handler and replace it in the dictionary
        original_handler = data_stream_parser._order_handlers[WRITE]
        data_stream_parser._order_handlers[WRITE] = mock_handle_write

        try:
            with patch(
                "pure3270.protocol.data_stream.logger.warning"
            ) as mock_logger_warning:
                data_stream_parser.parse(sample_data, data_type=unhandled_data_type)
                mock_logger_warning.assert_called_once()
                assert (
                    "Unhandled TN3270E data type: 0x{:02x}. Processing as TN3270_DATA.".format(
                        unhandled_data_type
                    )
                    in mock_logger_warning.call_args[0][0]
                )
                mock_handle_write.assert_called_once()
        finally:
            # Restore original handler
            data_stream_parser._order_handlers[WRITE] = original_handler

    def test_parse_tn3270_data_type(self, data_stream_parser):
        from unittest.mock import MagicMock

        from pure3270.protocol.data_stream import TN3270_DATA, WRITE

        sample_data = b"\x05\xc1"  # A simple write command

        # Create a mock that wraps the original method
        mock_handle_write = MagicMock(wraps=data_stream_parser._handle_write)
        # Store original handler and replace it in the dictionary
        original_handler = data_stream_parser._order_handlers[WRITE]
        data_stream_parser._order_handlers[WRITE] = mock_handle_write

        try:
            data_stream_parser.parse(sample_data, data_type=TN3270_DATA)
            mock_handle_write.assert_called_once()
        finally:
            # Restore original handler
            data_stream_parser._order_handlers[WRITE] = original_handler

        assert not data_stream_parser._is_scs_data_stream  # Should be reset after parse


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

    def test_build_query_sf(self, data_stream_sender):
        from pure3270.protocol.data_stream import (
            QUERY_REPLY_CHARACTERISTICS,
            STRUCTURED_FIELD,
        )

        query_type = QUERY_REPLY_CHARACTERISTICS
        expected_sf = bytes(
            [
                STRUCTURED_FIELD,  # SF identifier
                0x00,  # Length high byte (length is 1)
                0x01,  # Length low byte
                query_type,  # Query Type
            ]
        )
        stream = data_stream_sender.build_query_sf(query_type)
        assert stream == expected_sf


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
    with (
        patch.object(data_stream_parser.screen, "clear"),
        patch.object(data_stream_parser.screen, "write_char") as mock_write_char,
        patch.object(
            data_stream_parser.screen,
            "get_position",
            side_effect=[(0, 0), (0, 1), (0, 2)],
        ) as mock_get_pos,
        patch.object(data_stream_parser.screen, "set_position") as mock_set_pos,
    ):
        data_stream_parser.parse(sample_write_stream)
        data_stream_parser.screen.clear.assert_called_once()
        # Verify that the ABC characters were written to the screen
        assert mock_write_char.call_count == 3
        mock_write_char.assert_any_call(0xC1, 0, 0)  # A at (0,0)
        mock_write_char.assert_any_call(0xC2, 0, 1)  # B at (0,1)
        mock_write_char.assert_any_call(0xC3, 0, 2)  # C at (0,2)

    def test_parse_sna_response_data_type_positive(self, data_stream_parser):
        from pure3270.protocol.data_stream import SNA_FLAGS_NONE, SNA_FLAGS_RSP

        # SNA Response: Type (1 byte), Flags (1 byte), Sense Code (2 bytes), Data (optional)
        # Positive response: Sense Code 0x0000, Flags 0x08 (RSP)
        sna_payload = bytes(
            [
                SNA_COMMAND_RESPONSE,
                SNA_FLAGS_RSP,
                (SNA_SENSE_CODE_SUCCESS >> 8) & 0xFF,
                SNA_SENSE_CODE_SUCCESS & 0xFF,
                0xDE,
                0xAD,
            ]
        )
        with patch.object(
            data_stream_parser.negotiator, "_handle_sna_response"
        ) as mock_handle_sna_response:
            data_stream_parser.parse(sna_payload, data_type=SNA_RESPONSE_DATA_TYPE)
            mock_handle_sna_response.assert_called_once()
            args, _ = mock_handle_sna_response.call_args
            sna_response = args[0]
            assert isinstance(sna_response, SnaResponse)
            assert sna_response.response_type == SNA_COMMAND_RESPONSE
            assert sna_response.flags == SNA_FLAGS_RSP
            assert sna_response.sense_code == SNA_SENSE_CODE_SUCCESS
            assert sna_response.data == b"\xde\xad"
            assert sna_response.is_positive()
            assert not sna_response.is_negative()

    def test_parse_sna_response_data_type_negative_first(self, data_stream_parser):
        from pure3270.protocol.data_stream import (
            SNA_FLAGS_EXCEPTION_RESPONSE,
            SNA_FLAGS_RSP,
        )

        # Negative response: Sense Code 0x1002 (Not Supported), Flags 0x88 (RSP | ER)
        sna_payload = bytes(
            [
                SNA_COMMAND_RESPONSE,
                SNA_FLAGS_RSP | SNA_FLAGS_EXCEPTION_RESPONSE,
                (SNA_SENSE_CODE_NOT_SUPPORTED >> 8) & 0xFF,
                SNA_SENSE_CODE_NOT_SUPPORTED & 0xFF,
            ]
        )
        with patch.object(
            data_stream_parser.negotiator, "_handle_sna_response"
        ) as mock_handle_sna_response:
            data_stream_parser.parse(sna_payload, data_type=SNA_RESPONSE_DATA_TYPE)
            mock_handle_sna_response.assert_called_once()
            args, _ = mock_handle_sna_response.call_args
            sna_response = args[0]
            assert isinstance(sna_response, SnaResponse)
            assert sna_response.response_type == SNA_COMMAND_RESPONSE
            assert sna_response.flags == (SNA_FLAGS_RSP | SNA_FLAGS_EXCEPTION_RESPONSE)
            assert sna_response.sense_code == SNA_SENSE_CODE_NOT_SUPPORTED
            assert sna_response.is_negative()
            assert not sna_response.is_positive()

    def test_parse_sna_response_data_type_incomplete_first(self, data_stream_parser):
        from pure3270.protocol.data_stream import SNA_FLAGS_NONE

        # Incomplete SNA response (only type byte)
        sna_payload = bytes([SNA_COMMAND_RESPONSE])
        with patch.object(
            data_stream_parser.negotiator, "_handle_sna_response"
        ) as mock_handle_sna_response:
            data_stream_parser.parse(sna_payload, data_type=SNA_RESPONSE_DATA_TYPE)
            mock_handle_sna_response.assert_called_once()
            args, _ = mock_handle_sna_response.call_args
            sna_response = args[0]
            assert isinstance(sna_response, SnaResponse)
            assert sna_response.response_type == SNA_COMMAND_RESPONSE
            assert sna_response.flags == SNA_FLAGS_NONE
            assert sna_response.sense_code is None  # No sense code provided
            assert sna_response.data == b""

    def test_parse_sna_response_data_type_only_type_and_flags(self, data_stream_parser):
        from pure3270.protocol.data_stream import SNA_FLAGS_RSP

        # SNA Response with only type and flags, no sense code
        sna_payload = bytes([SNA_DATA_RESPONSE, SNA_FLAGS_RSP])
        with patch.object(
            data_stream_parser.negotiator, "_handle_sna_response"
        ) as mock_handle_sna_response:
            data_stream_parser.parse(sna_payload, data_type=SNA_RESPONSE_DATA_TYPE)
            mock_handle_sna_response.assert_called_once()
            args, _ = mock_handle_sna_response.call_args
            sna_response = args[0]
            assert isinstance(sna_response, SnaResponse)
            assert sna_response.response_type == SNA_DATA_RESPONSE
            assert sna_response.flags == SNA_FLAGS_RSP
            assert sna_response.sense_code is None
            assert sna_response.data == b""

    def test_parse_sna_response_structured_field_first(self, data_stream_parser):
        from pure3270.protocol.data_stream import SNA_FLAGS_RSP, SNA_RESPONSE_SF_TYPE

        # Structured field: 0x3C (SF_ID), Length (2 bytes), SF_Type (1 byte), Data
        # SNA_RESPONSE_SF_TYPE is 0x01
        sna_response_payload = bytes(
            [
                SNA_COMMAND_RESPONSE,
                SNA_FLAGS_RSP,
                (SNA_SENSE_CODE_SUCCESS >> 8) & 0xFF,
                SNA_SENSE_CODE_SUCCESS & 0xFF,
            ]
        )
        sf_length = 1 + len(sna_response_payload)  # SF_Type + payload length
        sample_data = (
            b"\x3c"
            + sf_length.to_bytes(2, "big")
            + SNA_RESPONSE_SF_TYPE.to_bytes(1, "big")
            + sna_response_payload
        )

        with patch.object(
            data_stream_parser.negotiator, "_handle_sna_response"
        ) as mock_handle_sna_response:
            data_stream_parser.parse(
                sample_data, data_type=TN3270_DATA
            )  # Parse as regular TN3270 data stream
            mock_handle_sna_response.assert_called_once()
            args, _ = mock_handle_sna_response.call_args
            sna_response = args[0]
            assert isinstance(sna_response, SnaResponse)
            assert sna_response.response_type == SNA_COMMAND_RESPONSE
            assert sna_response.flags == SNA_FLAGS_RSP
            assert sna_response.sense_code == SNA_SENSE_CODE_SUCCESS
            assert sna_response.data == b""

    def test_parse_printer_status_data_type(self, data_stream_parser):
        printer_status_payload = bytes([0x01])  # Example status code
        with patch.object(
            data_stream_parser.negotiator, "update_printer_status"
        ) as mock_update_printer_status:
            data_stream_parser.parse(
                printer_status_payload, data_type=PRINTER_STATUS_DATA_TYPE
            )
            mock_update_printer_status.assert_called_once_with(0x01)

    def test_parse_soh_message(self, data_stream_parser):
        soh_message_data = bytes([SOH, SOH_DEVICE_END])
        with patch.object(
            data_stream_parser.negotiator, "update_printer_status"
        ) as mock_update_printer_status:
            data_stream_parser.parse(
                soh_message_data, data_type=TN3270_DATA
            )  # SOH is a 3270 order
            mock_update_printer_status.assert_called_once_with(SOH_DEVICE_END)
            assert data_stream_parser._pos == 2  # SOH byte + status byte

    def test_parse_printer_status_structured_field(self, data_stream_parser):
        # SF format: 0x3C (SF_ID), Length (2 bytes), SF_Type (1 byte), Data
        printer_sf_payload = bytes([PRINTER_STATUS_SF_TYPE, 0x02])  # Type + status
        sf_length = 1 + len(printer_sf_payload)
        sample_data = b"\x3c" + sf_length.to_bytes(2, "big") + printer_sf_payload

        with patch.object(
            data_stream_parser.negotiator, "update_printer_status"
        ) as mock_update_printer_status:
            data_stream_parser.parse(sample_data, data_type=TN3270_DATA)
            mock_update_printer_status.assert_called_once_with(0x02)
            assert data_stream_parser._pos == len(sample_data)

    def test_parse_sna_response_data_type_negative_second(self, data_stream_parser):
        # Negative response: Sense Code 0x1002 (Not Supported)
        sna_payload = bytes(
            [
                SNA_COMMAND_RESPONSE,
                (SNA_SENSE_CODE_NOT_SUPPORTED >> 8) & 0xFF,
                SNA_SENSE_CODE_NOT_SUPPORTED & 0xFF,
            ]
        )
        with patch.object(
            data_stream_parser.negotiator, "_handle_sna_response"
        ) as mock_handle_sna_response:
            data_stream_parser.parse(sna_payload, data_type=SNA_RESPONSE_DATA_TYPE)
            mock_handle_sna_response.assert_called_once()
            args, _ = mock_handle_sna_response.call_args
            sna_response = args[0]
            assert isinstance(sna_response, SnaResponse)
            assert sna_response.response_type == SNA_COMMAND_RESPONSE
            assert sna_response.sense_code == SNA_SENSE_CODE_NOT_SUPPORTED
            assert sna_response.is_negative()
            assert not sna_response.is_positive()

    def test_parse_sna_response_data_type_incomplete_second(self, data_stream_parser):
        # Incomplete SNA response (only type byte)
        sna_payload = bytes([SNA_COMMAND_RESPONSE])
        with patch.object(
            data_stream_parser.negotiator, "_handle_sna_response"
        ) as mock_handle_sna_response:
            data_stream_parser.parse(sna_payload, data_type=SNA_RESPONSE_DATA_TYPE)
            mock_handle_sna_response.assert_called_once()
            args, _ = mock_handle_sna_response.call_args
            sna_response = args[0]
            assert isinstance(sna_response, SnaResponse)
            assert sna_response.response_type == SNA_COMMAND_RESPONSE
            assert sna_response.sense_code is None  # No sense code provided
            assert sna_response.data == b""

    def test_parse_sna_response_structured_field_second(self, data_stream_parser):
        # Structured field: 0x3C (SF_ID), Length (2 bytes), SF_Type (1 byte), Data
        # SNA_RESPONSE_SF_TYPE is 0x01
        sna_response_payload = bytes(
            [
                SNA_COMMAND_RESPONSE,
                (SNA_SENSE_CODE_SUCCESS >> 8) & 0xFF,
                SNA_SENSE_CODE_SUCCESS & 0xFF,
            ]
        )
        sf_length = 1 + len(sna_response_payload)  # SF_Type + payload length
        sample_data = (
            b"\x3c"
            + sf_length.to_bytes(2, "big")
            + SNA_RESPONSE_SF_TYPE.to_bytes(1, "big")
            + sna_response_payload
        )

        with patch.object(
            data_stream_parser.negotiator, "_handle_sna_response"
        ) as mock_handle_sna_response:
            data_stream_parser.parse(
                sample_data, data_type=TN3270_DATA
            )  # Parse as regular TN3270 data stream
            mock_handle_sna_response.assert_called_once()
            args, _ = mock_handle_sna_response.call_args
            sna_response = args[0]
            assert isinstance(sna_response, SnaResponse)
            assert sna_response.response_type == SNA_COMMAND_RESPONSE
            assert sna_response.sense_code == SNA_SENSE_CODE_SUCCESS
            assert sna_response.data == b""
