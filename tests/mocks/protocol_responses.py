"""
Mock Protocol Negotiation Responses.

Provides comprehensive mocking of TN3270 and Telnet protocol negotiations
for testing protocol-dependent functionality without requiring actual servers.
"""

import asyncio
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock

from pure3270.emulation.ebcdic import EBCDICCodec


class MockNegotiationHandler:
    """Mock handler for protocol negotiation scenarios."""

    def __init__(
        self,
        enable_tn3270e: bool = True,
        device_type: str = "IBM-3278-2-E",
        functions: Optional[List[str]] = None,
        lu_name: Optional[str] = None,
    ):
        """
        Initialize mock negotiation handler.

        Args:
            enable_tn3270e: Whether to enable TN3270E
            device_type: Device type to advertise
            functions: List of supported functions
            lu_name: Logical Unit name
        """
        self.enable_tn3270e = enable_tn3270e
        self.device_type = device_type
        self.functions = functions or ["BIND-IMAGE", "EOR"]
        self.lu_name = lu_name
        self.negotiation_sequence = []
        self.ebcdic_codec = EBCDICCodec()

    async def handle_telnet_negotiation(
        self, reader: Any, writer: Any
    ) -> Dict[str, Any]:
        """Handle Telnet negotiation (WILL/WONT DO/DONT)."""
        negotiation_result = {
            "will_tn3270e": False,
            "negotiated_options": {},
            "tn3270e_enabled": False,
        }

        # Send IAC WILL TN3270E
        _res = writer.write(b"\xff\xfb\x1b")
        if asyncio.iscoroutine(_res):
            await _res
        await writer.drain()
        self.negotiation_sequence.append("SENT_WILL_TN3270E")

        # Read client response
        try:
            data = await reader.readexactly(3)

            if data == b"\xff\xfd\x1b":  # Client agrees to TN3270E
                negotiation_result["will_tn3270e"] = True
                negotiation_result["tn3270e_enabled"] = self.enable_tn3270e
                self.negotiation_sequence.append("RECEIVED_DO_TN3270E")

            elif data == b"\xff\xfc\x1b":  # Client refuses TN3270E
                negotiation_result["will_tn3270e"] = False
                negotiation_result["tn3270e_enabled"] = False
                self.negotiation_sequence.append("RECEIVED_DONT_TN3270E")

            else:
                # Send IAC DONT TN3270E
                _res = writer.write(b"\xff\xfe\x1b")
                if asyncio.iscoroutine(_res):
                    await _res
                await writer.drain()
                negotiation_result["will_tn3270e"] = False
                negotiation_result["tn3270e_enabled"] = False
                self.negotiation_sequence.append("SENT_DONT_TN3270E")

        except asyncio.IncompleteReadError:
            # Client closed connection during negotiation
            negotiation_result["connection_closed"] = True
            self.negotiation_sequence.append("INCOMPLETE_READ")

        return negotiation_result

    async def handle_tn3270e_negotiation(
        self, reader: Any, writer: Any
    ) -> Dict[str, Any]:
        """Handle TN3270E specific negotiation."""
        negotiation_result = {
            "device_type_accepted": False,
            "functions_negotiated": [],
            "lu_name_accepted": False,
        }

        # Send device type request or response
        device_type_request = (
            b"\xff\xfa\x1b"  # SB TN3270E
            b"\x00"  # REQUEST
            b"\x01"  # DEVICE-TYPE
            b"\xff\xf0"  # SE
        )
        _res = writer.write(device_type_request)
        if asyncio.iscoroutine(_res):
            await _res
        await writer.drain()
        self.negotiation_sequence.append("SENT_DEVICE_TYPE_REQUEST")

        # Read device type response
        try:
            response = await reader.read(50)  # Read up to 50 bytes

            if b"IBM-3278-2" in response or b"IBM-3278-4" in response:
                negotiation_result["device_type_accepted"] = True
                self.negotiation_sequence.append("RECEIVED_DEVICE_TYPE_RESPONSE")

                # Check for LU name
                if self.lu_name and self.lu_name.encode() in response:
                    negotiation_result["lu_name_accepted"] = True
                    self.negotiation_sequence.append("RECEIVED_LU_NAME")

        except asyncio.IncompleteReadError:
            self.negotiation_sequence.append("INCOMPLETE_DEVICE_TYPE_READ")
            return negotiation_result

        # Send functions request
        functions_sb = self._create_functions_sb()
        _res = writer.write(functions_sb)
        if asyncio.iscoroutine(_res):
            await _res
        await writer.drain()
        self.negotiation_sequence.append("SENT_FUNCTIONS_REQUEST")

        # Read functions response
        try:
            response = await reader.read(30)

            # Fix: the original implementation erroneously looked for the ASCII
            # bytes "0" "0" rather than the binary sequence 0x00 0x07 0x01 that
            # appears in the mocked TN3270E functions support response. Using the
            # proper binary pattern ensures the negotiated function list (which
            # includes "BIND-IMAGE") is populated so integration tests can
            # validate negotiation success.
            if b"\x00\x07\x01" in response:  # Standard functions response marker
                negotiation_result["functions_negotiated"] = self.functions
                self.negotiation_sequence.append("RECEIVED_FUNCTIONS_RESPONSE")

        except asyncio.IncompleteReadError:
            self.negotiation_sequence.append("INCOMPLETE_FUNCTIONS_READ")

        return negotiation_result

    def _create_functions_sb(self) -> bytes:
        """Create TN3270E Functions SB message."""
        # Simplified functions SB for testing
        return (
            b"\xff\xfa\x1b"  # SB TN3270E
            b"\x02"  # FUNCTIONS
            b"\x00"  # REQUEST
            b"\x01"  # REJECTED
            b"\x00\x07"  # Number of functions
            b"\x01"  # First function code (BIND-IMAGE)
            b"\xff\xf0"  # SE
        )

    def get_negotiation_sequence(self) -> List[str]:
        """Get the sequence of negotiation steps."""
        return self.negotiation_sequence.copy()

    def reset_negotiation(self) -> None:
        """Reset negotiation state."""
        self.negotiation_sequence.clear()


class MockProtocolResponseGenerator:
    """Generates predefined protocol responses for testing scenarios."""

    @staticmethod
    def create_tn3270e_responses() -> List[bytes]:
        """Create a sequence of standard TN3270E responses."""
        return [
            b"\xff\xfd\x1b",  # Client IAC DO TN3270E
            b"\xff\xfa\x1b\x00\x02"
            + b"IBM-3278-2-E"
            + b"\xff\xf0",  # Device type response
            b"\xff\xfa\x1b\x02\x00\x01\x00\x07\x01\xff\xf0",  # Functions response
        ]

    @staticmethod
    def create_tn3270_responses() -> List[bytes]:
        """Create a sequence of basic TN3270 responses."""
        return [
            b"\xff\xfc\x1b",  # Client IAC DONT TN3270E
            b"\xff\xfb\x18",  # Client IAC WILL BINARY
        ]

    @staticmethod
    def create_error_responses() -> List[bytes]:
        """Create responses that simulate protocol errors."""
        return [
            b"\xff\xfc\x1b",  # Client IAC DONT TN3270E
            b"\xff\xfe\x18",  # Client IAC WONT BINARY
            b"\xff\xfd\x00",  # Client IAC DO ECHO
        ]

    @staticmethod
    def create_custom_responses(responses: List[Union[str, bytes]]) -> List[bytes]:
        """Create responses from custom input."""
        result = []
        ebcdic = EBCDICCodec()

        for response in responses:
            if isinstance(response, str):
                # Convert string to screen data
                ebcdic_data = ebcdic.encode(response)
                screen_with_header = (
                    b"\x00\x00\x00\x00" + b"\xf5" + ebcdic_data + b"\x19"
                )
                result.append(screen_with_header)
            else:
                # Assume bytes
                result.append(response)

        return result


class MockScreenUpdateGenerator:
    """Generates mock screen updates for testing screen buffer parsing."""

    def __init__(self, screen_buffer):
        self.screen_buffer = screen_buffer
        self.ebcdic_codec = EBCDICCodec()

    def create_empty_screen_update(self) -> bytes:
        """Create a screen update with all spaces."""
        screen_size = self.screen_buffer.rows * self.screen_buffer.cols
        return b"\x00\x00\x00\x00" + b"\xf5" + b"\x40" * screen_size + b"\x19"

    def create_text_screen_update(
        self, text: str, start_row: int = 0, start_col: int = 0
    ) -> bytes:
        """Create a screen update with specific text."""
        screen_data = b"\xf5"  # Write command

        # Add SBA (Set Buffer Address) to start position using 12-bit encoding
        addr = start_row * 80 + start_col
        sba_hi = 0x40 | ((addr >> 6) & 0x3F)
        sba_lo = 0x40 | (addr & 0x3F)
        screen_data += bytes([0x11, sba_hi, sba_lo])

        # Add text in EBCDIC
        try:
            text_ebcdic = self.ebcdic_codec.encode(text)
            if isinstance(text_ebcdic, tuple):
                text_ebcdic = bytes(text_ebcdic)
            # If it's already bytes, use as-is
            if not isinstance(text_ebcdic, bytes):
                text_ebcdic = bytes(text_ebcdic)
            screen_data += text_ebcdic
        except:
            # Fallback to ASCII encoding if EBCDIC fails
            screen_data += text.encode("ascii")

        # Add EOR
        screen_data += b"\x19"

        return b"\x00\x00\x00\x00" + screen_data

    def create_field_screen_update(self, fields: List[Dict[str, Any]]) -> bytes:
        """Create a screen update with specific field layout."""
        screen_data = b"\xf5"  # Write command

        for field in fields:
            # Add field attribute if specified
            if "attr" in field:
                screen_data += bytes([0x1D, field["attr"]])

            # Add SBA to field position
            row, col = field.get("pos", (0, 0))
            addr = row * 80 + col
            sba_hi = 0x40 | ((addr >> 6) & 0x3F)
            sba_lo = 0x40 | (addr & 0x3F)
            screen_data += bytes([0x11, sba_hi, sba_lo])

            # Add field content
            if "content" in field:
                content_ebcdic = self.ebcdic_codec.encode(field["content"])
                # Handle both tuple and non-tuple results from encode
                if isinstance(content_ebcdic, tuple):
                    content_ebcdic = content_ebcdic[0]
                screen_data += content_ebcdic

        # Add EOR
        screen_data += b"\x19"

        return b"\x00\x00\x00\x00" + screen_data

    def create_cursor_position_update(self, row: int, col: int) -> bytes:
        """Create a screen update that positions cursor without changing content."""
        addr = row * 80 + col
        # 12-bit SBA encoding for 24x80: two 6-bit values with 0x40 offset
        sba_hi = 0x40 | ((addr >> 6) & 0x3F)
        sba_lo = 0x40 | (addr & 0x3F)

        screen_data = (
            b"\xf5"  # Write command
            + b"\x00"  # WCC (normal)
            + b"\x11"
            + bytes([sba_hi, sba_lo])  # SBA to position
            + b"\x19"  # EOR
        )

        return b"\x00\x00\x00\x00" + screen_data


def create_mock_negotiation_handler(
    scenario: str = "standard",
) -> MockNegotiationHandler:
    """Factory function to create negotiation handler for different scenarios."""
    if scenario == "standard":
        return MockNegotiationHandler(enable_tn3270e=True, device_type="IBM-3278-2-E")
    elif scenario == "fallback":
        return MockNegotiationHandler(enable_tn3270e=False)
    elif scenario == "lu_session":
        return MockNegotiationHandler(enable_tn3270e=True, lu_name="LUA1")
    elif scenario == "error":
        return MockNegotiationHandler(enable_tn3270e=True, device_type="INVALID")
    else:
        return MockNegotiationHandler(enable_tn3270e=True)


def create_mock_protocol_responses(scenario: str = "standard") -> List[bytes]:
    """Factory function to create protocol responses for different scenarios."""
    generator = MockProtocolResponseGenerator()

    if scenario == "standard":
        return generator.create_tn3270e_responses()
    elif scenario == "fallback":
        return generator.create_tn3270_responses()
    elif scenario == "error":
        return generator.create_error_responses()
    else:
        return generator.create_tn3270e_responses()
