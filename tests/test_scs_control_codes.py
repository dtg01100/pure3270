"""
Unit tests for SCS (SNA Character String) control code processing in DataStreamParser.

Tests verify proper handling of SCS control codes like CR, LF, FF, HT, etc.
in printer sessions as implemented in data_stream.py.
"""

import pytest

from pure3270.emulation.printer_buffer import PrinterBuffer
from pure3270.protocol.data_stream import SCS_DATA, DataStreamParser


class TestSCSControlCodes:
    """Test SCS control code processing in DataStreamParser."""

    def test_scs_cr_control_code(self):
        """Test SCS Carriage Return (0x0D) resets cursor column."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        printer.cursor_col = 5
        assert printer.cursor_col == 5

        scs_data = bytes([0x0D])
        parser.parse(scs_data, data_type=SCS_DATA)

        assert printer.cursor_col == 0, "CR should reset cursor column to 0"

    def test_scs_lf_control_code(self):
        """Test SCS Line Feed (0x0A) advances to next line."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        initial_row = printer.cursor_row
        scs_data = bytes([0x0A])
        parser.parse(scs_data, data_type=SCS_DATA)

        assert printer.cursor_row > initial_row, "LF should advance cursor row"

    def test_scs_ff_control_code(self):
        """Test SCS Form Feed (0x0C) adds form feed character."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        scs_data = bytes([0x0C])
        parser.parse(scs_data, data_type=SCS_DATA)

        output = printer.get_content()
        assert "\f" in output, "FF should add form feed to output"

    def test_scs_ht_control_code(self):
        """Test SCS Horizontal Tab (0x09) adds tab character."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        scs_data = bytes([0x09])
        parser.parse(scs_data, data_type=SCS_DATA)

        output = printer.get_content()
        assert "\t" in output, "HT should add tab to output"

    def test_scs_bs_control_code(self):
        """Test SCS Backspace (0x08) handling - not explicitly handled."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        scs_data = bytes([0x08])
        parser.parse(scs_data, data_type=SCS_DATA)

        output = printer.get_content()
        assert output == "", "BS should not add printable content"

    def test_scs_so_si_control_codes(self):
        """Test SCS Shift Out/In (0x0E, 0x0F) - not explicitly handled."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        scs_data = bytes([0x0E, 0x0F])
        parser.parse(scs_data, data_type=SCS_DATA)

        output = printer.get_content()
        assert output == "", "SO/SI should not add printable content"

    def test_scs_vt_control_codes(self):
        """Test SCS Vertical Tab (0x0B) - treated as unhandled control."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        scs_data = bytes([0x0B])
        parser.parse(scs_data, data_type=SCS_DATA)

        output = printer.get_content()
        assert output == "", "VT should not add printable content"

    def test_scs_bel_control_code(self):
        """Test SCS Bell (0x07) - should be ignored."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        scs_data = bytes([0x07])
        parser.parse(scs_data, data_type=SCS_DATA)

        output = printer.get_content()
        assert output == "", "BEL should be ignored and produce no output"

    def test_scs_enq_ack_control_codes(self):
        """Test SCS Enquiry (0x05) and Acknowledge (0x06) - not explicitly handled."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        scs_data = bytes([0x05, 0x06])
        parser.parse(scs_data, data_type=SCS_DATA)

        output = printer.get_content()
        assert output == "", "ENQ/ACK should produce no printable output"

    def test_scs_unknown_control_code(self):
        """Test SCS unknown control code handling - should not raise."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        scs_data = bytes([0xFF])
        parser.parse(scs_data, data_type=SCS_DATA)

        output = printer.get_content()
        assert output == "", "Unknown control code should produce no output"

    def test_scs_soh_control_code(self):
        """Test SCS SOH (Start of Header) - updates printer status."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        scs_data = bytes([0x01, 0x40])
        parser.parse(scs_data, data_type=SCS_DATA)

        assert printer.get_status() == 0x40, "SOH should update printer status"

    def test_scs_cr_resets_column(self):
        """Test CR followed by text resets column before text."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        printer.cursor_col = 10
        scs_data = bytes([0x0D, 0x41])
        parser.parse(scs_data, data_type=SCS_DATA)

        assert printer.cursor_col == 0, (
            "CR should reset column before writing next char"
        )

    def test_scs_text_with_lf(self):
        """Test text followed by LF creates output with line advancement."""
        printer = PrinterBuffer()
        parser = DataStreamParser(None, printer_buffer=printer)

        from pure3270.emulation.ebcdic import EBCDICCodec

        codec = EBCDICCodec()
        ebcdic_text, _ = codec.encode("HELLO")
        scs_data = ebcdic_text + bytes([0x0A])

        parser.parse(scs_data, data_type=SCS_DATA)

        output = printer.get_content()
        assert "HELLO" in output, "Text data should be in output"
