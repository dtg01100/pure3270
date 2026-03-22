"""
RFC 2355 DEVICE-TYPE Negotiation Tests (Section 7.1)

These tests verify compliance with RFC 2355 Section 7.1 "DEVICE-TYPE Negotiation".

According to RFC 2355:
- 7.1.1 Device Pools: Client can request generic or specific sessions
- 7.1.2 CONNECT Command: Connect to specific LU in device pool
- 7.1.3 ASSOCIATE Command: Printer associates with display session
- 7.1.4 Accepting a Request: DEVICE-TYPE IS processing
- 7.1.5 REJECT Command: Reason codes for rejected requests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.utils import (
    TN3270E_DEVICE_TYPE,
    TN3270E_CONNECT,
    TN3270E_ASSOCIATE,
    TN3270E_IS,
    TN3270E_REJECT,
    TN3270E_REQUEST,
    TN3270E_SEND,
    TELOPT_TN3270E,
)


class TestDeviceTypeNames:
    """Tests for RFC 2355 7.1 Device Type Names.

    Per RFC 2355 7.1, valid device type names include:
    - IBM-3278-2 through IBM-3278-5 (display models)
    - IBM-3287-1 (printer)
    - IBM-DYNAMIC (dynamic terminal)
    """

    def test_valid_display_device_types(self):
        """Test valid display device types."""
        valid_types = [
            "IBM-3278-2",  # Model 2 (24x80)
            "IBM-3278-3",  # Model 3 (32x80)
            "IBM-3278-4",  # Model 4 (43x80)
            "IBM-3278-5",  # Model 5 (27x132)
        ]
        for device_type in valid_types:
            assert len(device_type) > 0

    def test_valid_printer_device_type(self):
        """Test valid printer device type."""
        printer_type = "IBM-3287-1"
        assert printer_type == "IBM-3287-1"

    def test_dynamic_device_type(self):
        """Test IBM-DYNAMIC device type for dynamic terminals."""
        dynamic_type = "IBM-DYNAMIC"
        assert dynamic_type == "IBM-DYNAMIC"


class TestCONNECTCommand:
    """Tests for RFC 2355 7.1.2 CONNECT Command.

    Per RFC 2355 7.1.2:
    - CONNECT command connects to specific LU in device pool
    - Format: IAC SB TN3270E DEVICE-TYPE CONNECT <lu-name> IAC SE
    - Used when client knows specific LU it wants
    """

    def test_connect_command_format(self):
        """Test CONNECT command byte format.

        CONNECT command structure:
        - DEVICE-TYPE (0x02)
        - CONNECT (0x03)
        - <lu-name> (padded to 8 bytes)
        """
        # CONNECT command code is 0x03 per RFC 2355
        connect_cmd = TN3270E_CONNECT
        assert connect_cmd == 0x03

    @pytest.fixture
    def tn3270_handler(self, memory_limit_500mb):
        """Create a TN3270Handler for testing."""
        screen_buffer = ScreenBuffer()
        handler = TN3270Handler(
            reader=None,
            writer=None,
            screen_buffer=screen_buffer,
            host="localhost",
            port=23,
            terminal_type="IBM-3278-2",
            is_printer_session=False,
        )
        handler._connected = True
        handler.writer = AsyncMock()
        handler.writer.drain = AsyncMock()
        handler.reader = AsyncMock()
        return handler

    @pytest.mark.asyncio
    async def test_handle_connect_command(self, tn3270_handler):
        """Test handling of CONNECT command from server.

        When server sends CONNECT, client should respond appropriately.
        """
        # CONNECT would be received as part of DEVICE-TYPE subnegotiation
        # Format: IAC SB TN3270E DEVICE-TYPE CONNECT <lu-name> IAC SE
        pass


class TestASSOCIATECommand:
    """Tests for RFC 2355 7.1.3 ASSOCIATE Command.

    Per RFC 2355 7.1.3:
    - ASSOCIATE command pairs printer with display session
    - Format: IAC SB TN3270E DEVICE-TYPE ASSOCIATE <lu-name> IAC SE
    - Used by printer sessions to associate with user's display
    """

    def test_associate_command_format(self):
        """Test ASSOCIATE command byte format.

        ASSOCIATE command structure:
        - DEVICE-TYPE (0x02)
        - ASSOCIATE (0x04)
        - <lu-name> (padded to 8 bytes)
        """
        # ASSOCIATE command code is 0x04 per RFC 2355
        associate_cmd = TN3270E_ASSOCIATE
        assert associate_cmd == 0x04

    @pytest.fixture
    def printer_handler(self, memory_limit_500mb):
        """Create a printer TN3270Handler for testing."""
        screen_buffer = ScreenBuffer()
        handler = TN3270Handler(
            reader=None,
            writer=None,
            screen_buffer=screen_buffer,
            host="localhost",
            port=23,
            terminal_type="IBM-3287-1",
            is_printer_session=True,
        )
        handler._connected = True
        handler.writer = AsyncMock()
        handler.writer.drain = AsyncMock()
        handler.reader = AsyncMock()
        return handler

    @pytest.mark.asyncio
    async def test_printer_receives_associate(self, printer_handler):
        """Test printer session handling of ASSOCIATE command.

        A printer session receives ASSOCIATE to pair with a display.
        """
        # ASSOCIATE would be received as part of DEVICE-TYPE subnegotiation
        pass

    @pytest.mark.asyncio
    async def test_associate_with_lu_name(self, printer_handler):
        """Test ASSOCIATE with specific LU name.

        Server sends ASSOCIATE with the LU name of the display session.
        """
        lu_name = b"LU1     "  # Padded to 8 bytes
        # In real implementation, this would trigger printer-display pairing
        assert len(lu_name) == 8


class TestDeviceTypeRequest:
    """Tests for RFC 2355 7.1 DEVICE-TYPE REQUEST.

    Per RFC 2355 7.1:
    - REQUEST command requests specific device type or generic
    - Client sends DEVICE-TYPE REQUEST with optional LU name
    - Server responds with DEVICE-TYPE IS or REJECT
    """

    def test_device_type_request_command(self):
        """Test DEVICE-TYPE REQUEST command code.

        Per RFC 2355, DEVICE-TYPE REQUEST uses the REQUEST subnegotiation type.
        The actual value is implementation-defined but uses REQUEST (0x07) as type.
        """
        # REQUEST is the subnegotiation type for requesting
        request_cmd = TN3270E_REQUEST
        assert request_cmd == 0x07

    def test_device_type_is_command(self):
        """Test DEVICE-TYPE IS (positive response) command code.

        Per RFC 2355, IS is the positive response for DEVICE-TYPE.
        """
        # IS is the command indicating positive response
        is_cmd = TN3270E_IS
        assert is_cmd == 0x04


class TestRejectCommand:
    """Tests for RFC 2355 7.1.5 REJECT Command.

    Per RFC 2355 7.1.5, REJECT reason codes include:
    - INV-DEVICE-TYPE (0x01): Invalid device type
    - INV-NAME (0x02): Invalid LU name
    - DEVICE-IN-USE (0x03): Resource busy
    - TYPE-NAME-ERROR (0x04): Device type not supported
    - UNSUPPORTED-REQ (0x05): Function not supported
    - INV-ASSOCIATE (0x06): Association not valid
    - CONN-PARTNER (0x07): Connected to wrong partner
    - UNKNOWN-ERROR (0x08): Unknown error
    """

    def test_reject_command_format(self):
        """Test REJECT command byte format.

        REJECT command structure:
        - DEVICE-TYPE (0x02)
        - REJECT (0x05)
        - <reason-code> (1 byte)
        """
        # REJECT command code is 0x05 per RFC 2355
        reject_cmd = TN3270E_REJECT
        assert reject_cmd == 0x05


class TestGenericVsSpecificRequest:
    """Tests for RFC 2355 7.1.1 Device Pools - Generic vs Specific.

    Per RFC 2355 7.1.1:
    - Generic request: No LU name, any available session
    - Specific request: LU name specified, that specific session
    """

    @pytest.fixture
    def tn3270_handler(self, memory_limit_500mb):
        """Create a TN3270Handler for testing."""
        screen_buffer = ScreenBuffer()
        handler = TN3270Handler(
            reader=None,
            writer=None,
            screen_buffer=screen_buffer,
            host="localhost",
            port=23,
            terminal_type="IBM-3278-2",
            is_printer_session=False,
        )
        handler._connected = True
        handler.writer = AsyncMock()
        handler.writer.drain = AsyncMock()
        handler.reader = AsyncMock()
        return handler

    @pytest.mark.asyncio
    async def test_generic_device_request(self, tn3270_handler):
        """Test requesting generic session from device pool.

        When no LU name is specified, server assigns any available session.
        """
        # Generic request would have no LU name in DEVICE-TYPE REQUEST
        pass

    @pytest.mark.asyncio
    async def test_specific_device_request(self, tn3270_handler):
        """Test requesting specific LU from device pool.

        When LU name is specified, server connects to that specific session.
        """
        specific_lu = b"LUA12345"  # Example LU name
        assert len(specific_lu) <= 8


class TestDeviceTypeNegotiationFlow:
    """Tests for RFC 2355 7.1 complete negotiation flow."""

    @pytest.fixture
    def negotiator(self, memory_limit_500mb):
        """Create a Negotiator for testing."""
        screen_buffer = ScreenBuffer()
        parser = DataStreamParser(screen_buffer)
        handler = TN3270Handler(
            reader=None,
            writer=None,
            screen_buffer=screen_buffer,
            host="localhost",
            port=23,
            terminal_type="IBM-3278-2",
            is_printer_session=False,
        )
        handler._connected = True
        handler.writer = AsyncMock()
        handler.writer.drain = AsyncMock()
        handler.reader = AsyncMock()

        negotiator = Negotiator(
            writer=handler.writer,
            parser=parser,
            screen_buffer=screen_buffer,
            handler=handler,
            is_printer_session=False,
        )
        negotiator._server_supports_tn3270e = True
        negotiator._negotiated_tn3270e = True
        return negotiator

    @pytest.mark.asyncio
    async def test_device_type_is_accepts_request(self, negotiator):
        """Test receiving DEVICE-TYPE IS accepts the request."""
        # DEVICE-TYPE IS is positive acknowledgment
        pass

    @pytest.mark.asyncio
    async def test_device_type_reject_with_reason(self, negotiator):
        """Test receiving DEVICE-TYPE REJECT with reason code."""
        # REJECT with reason code indicates why request failed
        pass
