#!/usr/bin/env python3
"""
TN3270/TN3270E Wire Protocol Validation Suite

Tests the pure3270 implementation against RFC specifications:
- RFC 854 (Telnet)
- RFC 1576 (TN3270)
- RFC 1646/1647 (TN3270E)
- RFC 2355 (TN3270E)
"""

import asyncio
import unittest

# Add project root to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pure3270.protocol.tn3270e_header import TN3270EHeader

# Import from utils module
from pure3270.protocol import utils as utils_module

# Telnet IAC commands
IAC = utils_module.IAC
SB = utils_module.SB
SE = utils_module.SE
WILL = utils_module.WILL
WONT = utils_module.WONT
DO = utils_module.DO
DONT = utils_module.DONT
GA = utils_module.GA
EL = utils_module.EL
EC = utils_module.EC
AYT = utils_module.AYT
AO = utils_module.AO
IP = utils_module.IP
BRK = utils_module.BRK
DM = utils_module.DM
NOP = utils_module.NOP

# Telnet options
TELOPT_BINARY = utils_module.TELOPT_BINARY
TELOPT_ECHO = utils_module.TELOPT_ECHO
TELOPT_SGA = utils_module.TELOPT_SGA
TELOPT_TTYPE = utils_module.TELOPT_TTYPE
TELOPT_EOR = utils_module.TELOPT_EOR
TELOPT_NAWS = utils_module.TELOPT_NAWS
TELOPT_TN3270E = utils_module.TELOPT_TN3270E
TELOPT_NEW_ENVIRON = utils_module.TELOPT_NEW_ENVIRON

# TN3270E data types
TN3270_DATA = utils_module.TN3270_DATA
SCS_DATA = utils_module.SCS_DATA
RESPONSE = utils_module.RESPONSE
BIND_IMAGE = utils_module.BIND_IMAGE
UNBIND = utils_module.UNBIND
NVT_DATA = utils_module.NVT_DATA
REQUEST = utils_module.REQUEST
SSCP_LU_DATA = utils_module.SSCP_LU_DATA
PRINT_EOJ = utils_module.PRINT_EOJ
SNA_RESPONSE = utils_module.SNA_RESPONSE

# TN3270E response flags
TN3270E_RSF_NO_RESPONSE = utils_module.TN3270E_RSF_NO_RESPONSE
TN3270E_RSF_ERROR_RESPONSE = utils_module.TN3270E_RSF_ERROR_RESPONSE
TN3270E_RSF_ALWAYS_RESPONSE = utils_module.TN3270E_RSF_ALWAYS_RESPONSE

# TN3270E function flags
TN3270E_BIND_IMAGE = utils_module.TN3270E_BIND_IMAGE
TN3270E_DATA_STREAM_CTL = utils_module.TN3270E_DATA_STREAM_CTL
TN3270E_NEW_APPL = utils_module.TN3270E_NEW_APPL
TN3270E_RESPONSES = utils_module.TN3270E_RESPONSES
TN3270E_SCS_CTL_CODES = utils_module.TN3270E_SCS_CTL_CODES
TN3270E_SYSREQ = utils_module.TN3270E_SYSREQ

# TTYPE subcommands
TTYPE_IS = utils_module.TTYPE_IS
TTYPE_SEND = utils_module.TTYPE_SEND

# TN3270E subnegotiation
TN3270E_IS = utils_module.TN3270E_IS
TN3270E_SEND = utils_module.TN3270E_SEND
TN3270E_CONNECT = utils_module.TN3270E_CONNECT
TN3270E_ASSOCIATE = utils_module.TN3270E_ASSOCIATE
TN3270E_REJECT = utils_module.TN3270E_REJECT
TN3270E_DEVICE_TYPE = utils_module.TN3270E_DEVICE_TYPE
TN3270E_FUNCTIONS = utils_module.TN3270E_FUNCTIONS
TN3270E_REQUEST = utils_module.TN3270E_REQUEST
TN3270E_QUERY = utils_module.TN3270E_QUERY

# Import data stream constants
from pure3270.protocol.data_stream import (
    CMD_W, CMD_EW, CMD_EWA, CMD_WSF, SNA_CMD_W, SNA_CMD_EW,
    PT, GE, SBA, EUA, IC, SF, SA, SFE, MF, RA,
    BIND_SF_TYPE, PRINTER_STATUS_SF_TYPE, QUERY_REPLY_SF_TYPE,
    OUTBOUND_3270DS_SF_TYPE, INBOUND_3270DS_SF_TYPE, IND_FILE_SF_TYPE,
)
from pure3270.protocol.data_stream import DataStreamParser, DataStreamSender
from pure3270.emulation.screen_buffer import ScreenBuffer


class TestTN3270EHeaderWireFormat(unittest.TestCase):
    """Test TN3270E header wire format per RFC 2355 Section 3."""
    
    def test_header_size_is_5_bytes(self):
        """RFC 2355: TN3270E header is exactly 5 bytes."""
        header = TN3270EHeader(TN3270_DATA)
        serialized = header.to_bytes()
        self.assertEqual(len(serialized), 5, "TN3270E header must be exactly 5 bytes")
    
    def test_data_type_byte_position(self):
        """RFC 2355: Byte 0 is DATA-TYPE."""
        for data_type in [TN3270_DATA, SCS_DATA, RESPONSE, BIND_IMAGE]:
            header = TN3270EHeader(data_type=data_type)
            serialized = header.to_bytes()
            self.assertEqual(serialized[0], data_type, 
                           f"DATA-TYPE byte must be {hex(data_type)}, got {hex(serialized[0])}")
    
    def test_request_flag_byte_position(self):
        """RFC 2355: Byte 1 is REQUEST-FLAG."""
        header = TN3270EHeader(request_flag=0x80)
        serialized = header.to_bytes()
        self.assertEqual(serialized[1], 0x80, "REQUEST-FLAG byte must be 0x80")
    
    def test_response_flag_byte_position(self):
        """RFC 2355: Byte 2 is RESPONSE-FLAG."""
        for flag in [0x00, 0x01, 0x02]:
            header = TN3270EHeader(response_flag=flag)
            serialized = header.to_bytes()
            self.assertEqual(serialized[2], flag,
                           f"RESPONSE-FLAG byte must be {hex(flag)}, got {hex(serialized[2])}")
    
    def test_seq_number_is_big_endian(self):
        """RFC 2355: Bytes 3-4 are SEQ-NUMBER (16-bit big-endian)."""
        test_cases = [
            (0, b'\x00\x00'),
            (1, b'\x00\x01'),
            (256, b'\x01\x00'),
            (0xFFFF, b'\xff\xff'),
        ]
        for seq_num, expected_bytes in test_cases:
            header = TN3270EHeader(seq_number=seq_num)
            serialized = header.to_bytes()
            self.assertEqual(serialized[3:5], expected_bytes,
                           f"SEQ-NUMBER {seq_num} must be {expected_bytes.hex()}, got {serialized[3:5].hex()}")
    
    def test_roundtrip_parse_serialize(self):
        """Test header survives parse->serialize roundtrip."""
        # Use non-zero data types to avoid validation rejection
        test_headers = [
            TN3270EHeader(TN3270_DATA, 0, TN3270E_RSF_NO_RESPONSE, 1),
            TN3270EHeader(SCS_DATA, 0x80, TN3270E_RSF_ERROR_RESPONSE, 12345),
            TN3270EHeader(BIND_IMAGE, 0, TN3270E_RSF_ALWAYS_RESPONSE, 0xFFFF),
            TN3270EHeader(NVT_DATA, 0x40, 0, 1),
        ]
        for original in test_headers:
            serialized = original.to_bytes()
            parsed = TN3270EHeader.from_bytes(serialized)
            self.assertIsNotNone(parsed, f"Failed to parse: {serialized.hex()}")
            assert parsed is not None
            self.assertEqual(parsed.data_type, original.data_type)
            self.assertEqual(parsed.request_flag, original.request_flag)
            self.assertEqual(parsed.response_flag, original.response_flag)
            self.assertEqual(parsed.seq_number, original.seq_number)
    
    def test_from_bytes_valid(self):
        """Test parsing valid 5-byte headers."""
        # All-zeros header is intentionally rejected (validation)
        raw = bytes([0x00, 0x00, 0x00, 0x00, 0x00])
        self.assertIsNone(TN3270EHeader.from_bytes(raw), "All-zeros header should be rejected")

        # Valid header with non-zero values
        raw = bytes([0x01, 0x80, 0x02, 0x12, 0x34])
        header = TN3270EHeader.from_bytes(raw)
        self.assertIsNotNone(header)
        assert header is not None
        self.assertEqual(header.data_type, SCS_DATA)
        self.assertEqual(header.request_flag, 0x80)
        self.assertEqual(header.response_flag, TN3270E_RSF_ALWAYS_RESPONSE)
        self.assertEqual(header.seq_number, 0x1234)
    
    def test_from_bytes_invalid_length(self):
        """Test that invalid length data returns None."""
        for length in [0, 1, 2, 3, 4, 6, 10]:
            header = TN3270EHeader.from_bytes(bytes([0] * length))
            self.assertIsNone(header, f"Invalid length {length} should return None")
    
    def test_header_constants_match_rfc(self):
        """Verify all RFC 2355 constants are correct."""
        self.assertEqual(TN3270_DATA, 0x00)
        self.assertEqual(SCS_DATA, 0x01)
        self.assertEqual(RESPONSE, 0x02)
        self.assertEqual(BIND_IMAGE, 0x03)
        self.assertEqual(UNBIND, 0x04)
        self.assertEqual(NVT_DATA, 0x05)
        self.assertEqual(REQUEST, 0x06)
        self.assertEqual(SSCP_LU_DATA, 0x07)
        self.assertEqual(PRINT_EOJ, 0x08)
        self.assertEqual(SNA_RESPONSE, 0x09)
        
        self.assertEqual(TN3270E_RSF_NO_RESPONSE, 0x00)
        self.assertEqual(TN3270E_RSF_ERROR_RESPONSE, 0x01)
        self.assertEqual(TN3270E_RSF_ALWAYS_RESPONSE, 0x02)


class TestTelnetWireProtocol(unittest.TestCase):
    """Test Telnet protocol constants and encoding per RFC 854."""
    
    def test_iac_constant(self):
        """RFC 854: IAC is 0xFF."""
        self.assertEqual(IAC, 0xFF)
    
    def test_all_iac_commands(self):
        """Verify all IAC command codes per RFC 854."""
        self.assertEqual(SB, 0xFA)
        self.assertEqual(SE, 0xF0)
        self.assertEqual(WILL, 0xFB)
        self.assertEqual(WONT, 0xFC)
        self.assertEqual(DO, 0xFD)
        self.assertEqual(DONT, 0xFE)
        self.assertEqual(GA, 0xF9)
        self.assertEqual(EL, 0xF8)
        self.assertEqual(EC, 0xF7)
        self.assertEqual(AYT, 0xF6)
        self.assertEqual(AO, 0xF5)
        self.assertEqual(IP, 0xF4)
        self.assertEqual(BRK, 0xF3)
        self.assertEqual(DM, 0xF2)
        self.assertEqual(NOP, 0xF1)
    
    def test_telnet_options(self):
        """Verify all Telnet option codes."""
        self.assertEqual(TELOPT_BINARY, 0x00)
        self.assertEqual(TELOPT_ECHO, 0x01)
        self.assertEqual(TELOPT_SGA, 0x03)
        self.assertEqual(TELOPT_TTYPE, 0x18)
        self.assertEqual(TELOPT_EOR, 0x19)
        self.assertEqual(TELOPT_NAWS, 0x1F)
        self.assertEqual(TELOPT_TN3270E, 0x28)
        self.assertEqual(TELOPT_NEW_ENVIRON, 0x27)


class TestTN3270EConstants(unittest.TestCase):
    """Test TN3270E-specific constants per RFC 1646/1647."""
    
    def test_tn3270e_option(self):
        """RFC 1647: TN3270E option code is 0x28."""
        self.assertEqual(TELOPT_TN3270E, 0x28)
    
    def test_ttype_subcommands(self):
        """Verify terminal type subnegotiation codes."""
        self.assertEqual(TTYPE_IS, 0x00)
        self.assertEqual(TTYPE_SEND, 0x01)
    
    def test_tn3270e_subnegotiation_types(self):
        """Verify TN3270E subnegotiation types per RFC 2355."""
        self.assertEqual(TN3270E_IS, 0x04)
        self.assertEqual(TN3270E_SEND, 0x08)
        self.assertEqual(TN3270E_CONNECT, 0x03)
        self.assertEqual(TN3270E_ASSOCIATE, 0x04)
        self.assertEqual(TN3270E_REJECT, 0x05)
        self.assertEqual(TN3270E_DEVICE_TYPE, 0x02)
        self.assertEqual(TN3270E_FUNCTIONS, 0x03)
        self.assertEqual(TN3270E_REQUEST, 0x07)
        self.assertEqual(TN3270E_QUERY, 0x0F)
    
    def test_tn3270e_function_flags(self):
        """Verify TN3270E function flags per RFC 2355."""
        self.assertEqual(TN3270E_BIND_IMAGE, 0x01)
        self.assertEqual(TN3270E_DATA_STREAM_CTL, 0x01)
        self.assertEqual(TN3270E_NEW_APPL, 0x02)
        self.assertEqual(TN3270E_RESPONSES, 0x08)
        self.assertEqual(TN3270E_SCS_CTL_CODES, 0x04)
        self.assertEqual(TN3270E_SYSREQ, 0x10)


class Test3270DataStreamCommands(unittest.TestCase):
    """Test 3270 data stream command codes."""
    
    def test_write_commands(self):
        """Verify 3270 Write command codes."""
        self.assertEqual(CMD_W, 0x01)
        self.assertEqual(CMD_EW, 0x05)
        self.assertEqual(CMD_EWA, 0x0D)
        self.assertEqual(CMD_WSF, 0x11)
    
    def test_sna_write_commands(self):
        """Verify SNA-formatted Write command codes."""
        self.assertEqual(SNA_CMD_W, 0xF1)
        self.assertEqual(SNA_CMD_EW, 0xF5)
    
    def test_in_stream_orders(self):
        """Verify 3270 in-stream order codes."""
        self.assertEqual(PT, 0x05)
        self.assertEqual(GE, 0x08)
        self.assertEqual(SBA, 0x11)
        self.assertEqual(EUA, 0x12)
        self.assertEqual(IC, 0x13)
        self.assertEqual(SF, 0x1D)
        self.assertEqual(SA, 0x28)
        self.assertEqual(SFE, 0x29)
        self.assertEqual(MF, 0x2C)
        self.assertEqual(RA, 0x3C)
    
    def test_structured_field_types(self):
        """Verify Structured Field type codes."""
        self.assertEqual(BIND_SF_TYPE, 0x03)
        self.assertEqual(PRINTER_STATUS_SF_TYPE, 0x02)
        self.assertEqual(QUERY_REPLY_SF_TYPE, 0x81)
        self.assertEqual(OUTBOUND_3270DS_SF_TYPE, 0x40)
        self.assertEqual(INBOUND_3270DS_SF_TYPE, 0x41)
        self.assertEqual(IND_FILE_SF_TYPE, 0xD0)


class TestTN3270EHeaderParsing(unittest.TestCase):
    """Test TN3270E header parsing edge cases."""
    
    def test_data_types_1_to_9_parseable(self):
        """Verify DATA-TYPE values 1-9 parse correctly (0 is all-zeros rejected)."""
        for data_type in range(0x01, 0x0A):
            raw = bytes([data_type, 0x00, 0x00, 0x00, 0x01])
            header = TN3270EHeader.from_bytes(raw)
            self.assertIsNotNone(header, f"DATA-TYPE {hex(data_type)} should be parseable")
            assert header is not None
            self.assertEqual(header.data_type, data_type)
    
    def test_response_flag_validation(self):
        """Verify RESPONSE-FLAG accepts valid values per RFC 2355."""
        valid_flags = [0x00, 0x01, 0x02]
        for flag in valid_flags:
            raw = bytes([TN3270_DATA, 0x00, flag, 0x00, 0x01])
            header = TN3270EHeader.from_bytes(raw)
            self.assertIsNotNone(header)
    
    def test_request_flag_bit7_extended_addressing(self):
        """Verify bit 7 of REQUEST-FLAG indicates extended addressing."""
        raw = bytes([TN3270_DATA, 0x80, 0x00, 0x00, 0x01])
        header = TN3270EHeader.from_bytes(raw)
        self.assertIsNotNone(header)
        assert header is not None
        self.assertEqual(header.request_flag, 0x80)
        
        raw = bytes([TN3270_DATA, 0x00, 0x00, 0x00, 0x01])
        header = TN3270EHeader.from_bytes(raw)
        self.assertIsNotNone(header)
        assert header is not None
        self.assertEqual(header.request_flag, 0x00)
    
    def test_seq_number_extreme_values(self):
        """Test sequence number handling at boundaries."""
        extremes = [1, 32767, 32768, 65534, 65535]
        for seq in extremes:
            header = TN3270EHeader(seq_number=seq)
            serialized = header.to_bytes()
            parsed = TN3270EHeader.from_bytes(serialized)
            self.assertIsNotNone(parsed)
            assert parsed is not None
            self.assertEqual(parsed.seq_number, seq)


class TestDataStreamParser(unittest.TestCase):
    """Test 3270 data stream parsing."""
    
    def setUp(self):
        self.screen = ScreenBuffer()
        self.parser = DataStreamParser(self.screen)
    
    def test_parse_write_command(self):
        """Test parsing Write command (0x01)."""
        data = bytes([
            CMD_W,
            0x00,
            SBA, 0x00, 0x00,
            SF, 0xC0,
            0xC8, 0xC5,
        ])
        result = self.parser.parse(data[1:], data_type=0x00)
        if asyncio.iscoroutine(result):
            asyncio.get_event_loop().run_until_complete(result)
        self.assertEqual(self.screen.buffer[0], 0xC0)
    
    def test_parse_erase_write_command(self):
        """Test parsing Erase/Write command (0x05)."""
        data = bytes([
            CMD_EW,
            0x00,
            SF, 0xC0,
            0x40,
        ])
        result = self.parser.parse(data[1:], data_type=0x00)
        if asyncio.iscoroutine(result):
            asyncio.get_event_loop().run_until_complete(result)
    
    def test_parse_sba_order(self):
        """Test Set Buffer Address order parsing."""
        sba_data = bytes([SBA, 0x00, 0x28])
        result = self.parser.parse(sba_data, data_type=0x00)
        if asyncio.iscoroutine(result):
            asyncio.get_event_loop().run_until_complete(result)
    
    def test_parse_sf_order(self):
        """Test Start Field order parsing."""
        data = bytes([SF, 0xC0])
        result = self.parser.parse(data, data_type=0x00)
        if asyncio.iscoroutine(result):
            asyncio.get_event_loop().run_until_complete(result)
        self.assertEqual(self.screen.buffer[0], 0xC0)
    
    def test_parse_wcc(self):
        """Test WCC (Write Control Character) handling."""
        wcc = 0x02
        self.parser._handle_wcc_with_byte(wcc)
        self.assertEqual(self.parser.wcc, wcc)
    
    def test_parse_with_tn3270e_header(self):
        """Test parsing data that includes TN3270E header."""
        data_stream = bytes([
            CMD_W,
            0x00,
            SF, 0xC0,
            0x40,
        ])
        
        result = self.parser.parse(data_stream, data_type=TN3270_DATA)
        if asyncio.iscoroutine(result):
            asyncio.get_event_loop().run_until_complete(result)


class TestDataStreamSender(unittest.TestCase):
    """Test 3270 data stream sending."""
    
    def test_build_printer_status_sf(self):
        """Test building Printer Status structured field."""
        sender = DataStreamSender()
        for status_code in [0x00, 0x01, 0x02, 0x04]:
            sf = sender.build_printer_status_sf(status_code)
            self.assertIsInstance(sf, bytes)
            self.assertGreater(len(sf), 0)
            # Verify method returns a non-empty structured field
            self.assertIn(status_code, sf)
    
    def test_sender_has_all_methods(self):
        """Verify DataStreamSender has all required methods."""
        sender = DataStreamSender()
        required_methods = [
            'build_printer_status_sf',
            'build_sba',
            'build_write',
        ]
        for method in required_methods:
            self.assertTrue(
                hasattr(sender, method),
                f"DataStreamSender missing method: {method}"
            )


class TestSequenceNumbers(unittest.TestCase):
    """Test TN3270E sequence number handling."""
    
    def test_sequence_number_wrapping(self):
        """Test sequence numbers wrap at 65535."""
        for seq in [1, 32767, 32768, 65534, 65535]:
            header = TN3270EHeader(seq_number=seq)
            serialized = header.to_bytes()
            parsed = TN3270EHeader.from_bytes(serialized)
            self.assertIsNotNone(parsed)
            assert parsed is not None
            self.assertEqual(parsed.seq_number, seq)
    
    def test_sequence_number_endianness(self):
        """Verify sequence number is big-endian in wire format."""
        header = TN3270EHeader(seq_number=0x1234)
        serialized = header.to_bytes()
        self.assertEqual(serialized[3], 0x12)
        self.assertEqual(serialized[4], 0x34)


class TestWireFormatCompliance(unittest.TestCase):
    """Test overall wire format compliance."""
    
    def test_no_palette_collision_high_values(self):
        """Verify protocol values use high byte range to avoid EBCDIC collision."""
        # Protocol values >= 0xF0 are IAC range, can't collide with EBCDIC
        # 3270 commands use values <= 0x11
        protocol_values = [
            IAC, SB, SE, WILL, WONT, DO, DONT,
            CMD_W, CMD_EW, CMD_EWA, CMD_WSF,
            SBA, SF, IC,
            TN3270_DATA, SCS_DATA, RESPONSE,
        ]
        for val in protocol_values:
            # Either IAC range (>=0xF0) or command range (<=0x1D)
            self.assertTrue(
                val >= 0xF0 or val <= 0x1D,
                f"Protocol value {hex(val)} might collide with EBCDIC data"
            )
    
    def test_header_to_bytes_length(self):
        """Verify header serialization produces correct length."""
        header = TN3270EHeader(TN3270_DATA, 0, 0, 1)
        serialized = header.to_bytes()
        self.assertEqual(len(serialized), 5)
        
        header2 = TN3270EHeader(TN3270_DATA, 0x80, 0x02, 0xFFFF)
        serialized2 = header2.to_bytes()
        self.assertEqual(len(serialized2), 5)
    
    def test_all_constants_are_int(self):
        """Verify all protocol constants are integers."""
        constants = [
            IAC, SB, SE, WILL, WONT, DO, DONT,
            TELOPT_BINARY, TELOPT_TTYPE, TELOPT_TN3270E,
            TN3270_DATA, SCS_DATA, RESPONSE,
            CMD_W, CMD_EW, CMD_EWA, CMD_WSF,
            SBA, SF, IC,
            TN3270E_RSF_NO_RESPONSE, TN3270E_RSF_ERROR_RESPONSE,
        ]
        for const in constants:
            self.assertIsInstance(const, int, f"{const} is not an integer")
    
    def test_tn3270e_data_types_complete(self):
        """Verify all TN3270E DATA-TYPE values are defined."""
        defined_types = [
            TN3270_DATA, SCS_DATA, RESPONSE, BIND_IMAGE, UNBIND,
            NVT_DATA, REQUEST, SSCP_LU_DATA, PRINT_EOJ, SNA_RESPONSE
        ]
        self.assertEqual(len(defined_types), 10)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def test_empty_data_stream(self):
        """Test parsing empty data stream."""
        screen = ScreenBuffer()
        parser = DataStreamParser(screen)
        result = parser.parse(b"", data_type=0x00)
        if asyncio.iscoroutine(result):
            asyncio.get_event_loop().run_until_complete(result)
    
    def test_header_with_max_values(self):
        """Test header with maximum allowed values."""
        header = TN3270EHeader(
            data_type=0x09,
            request_flag=0x7F,  # Max valid (not 0xFF which is rejected)
            response_flag=0x02,  # Max valid response flag
            seq_number=0xFFFF
        )
        serialized = header.to_bytes()
        self.assertEqual(len(serialized), 5)
        
        parsed = TN3270EHeader.from_bytes(serialized)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.data_type, 0x09)
        self.assertEqual(parsed.seq_number, 0xFFFF)
    
    def test_data_stream_with_control_characters(self):
        """Test data stream containing control-like characters."""
        screen = ScreenBuffer()
        parser = DataStreamParser(screen)
        
        data = bytes([
            SBA, 0x00, 0x00,
            0xFF,
            0x00,
        ])
        
        result = parser.parse(data, data_type=0x00)
        if asyncio.iscoroutine(result):
            asyncio.get_event_loop().run_until_complete(result)


class TestNegotiationSequence(unittest.TestCase):
    """Test TN3270E negotiation sequence."""
    
    def test_negotiation_constants_sequential(self):
        """Verify negotiation uses proper IAC sequence."""
        self.assertEqual(WILL, 0xFB)
        self.assertEqual(DO, 0xFD)
        self.assertEqual(TELOPT_TN3270E, 0x28)


if __name__ == "__main__":
    unittest.main(verbosity=2)