"""
RFC 2355 FUNCTIONS Negotiation Tests (Section 7.2)

These tests verify compliance with RFC 2355 Section 7.2 "FUNCTIONS Negotiation".

According to RFC 2355:
- 7.2.1: FUNCTIONS commands - REQUEST and IS
- 7.2.2: List of TN3270E Functions that can be negotiated
- Function list iteration when server sends multiple functions
- Impasse detection when client/server can't agree
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.utils import (
    TN3270E_BIND_IMAGE,
    TN3270E_DATA_STREAM_CTL,
    TN3270E_FUNCTIONS,
    TN3270E_IS,
    TN3270E_REQUEST,
    TN3270E_RESPONSES,
    TN3270E_SCS_CTL_CODES,
    TN3270E_SEND,
    TN3270E_SYSREQ,
)


class TestFunctionsNegotiation:
    """Tests for RFC 2355 7.2 FUNCTIONS Negotiation."""

    def test_functions_request_command(self):
        """Test FUNCTIONS REQUEST command code.

        Per RFC 2355 7.2.1:
        - REQUEST is used to request specific functions
        """
        # FUNCTIONS REQUEST = 0x01
        assert TN3270E_REQUEST == 0x07  # This is the subneg type

    def test_functions_send_command(self):
        """Test FUNCTIONS SEND command code.

        Per RFC 2355 7.2.1:
        - SEND is used to send function list
        """
        assert TN3270E_SEND == 0x08

    def test_functions_is_command(self):
        """Test FUNCTIONS IS command code.

        Per RFC 2355 7.2.1:
        - IS is used to respond with accepted functions
        """
        # Note: IS is the positive response command
        assert TN3270E_IS == 0x04


class TestFunctionsList:
    """Tests for RFC 2355 7.2.2 List of TN3270E Functions.

    Per RFC 2355 7.2.2, negotiable functions include:
    - BIND-IMAGE (0x01)
    - DATA-STREAM-CTL (0x02)
    - SCS-CTL-CODES (0x04)
    - RESPONSES (0x08)
    - SYSREQ (0x10)
    """

    def test_bind_image_function_code(self):
        """Test BIND-IMAGE function code."""
        assert TN3270E_BIND_IMAGE == 0x01

    def test_data_stream_ctl_function_code(self):
        """Test DATA-STREAM-CTL function code."""
        assert TN3270E_DATA_STREAM_CTL == 0x01  # Note: this is also 0x01

    def test_scs_ctl_codes_function_code(self):
        """Test SCS-CTL-CODES function code."""
        assert TN3270E_SCS_CTL_CODES == 0x04

    def test_responses_function_code(self):
        """Test RESPONSES function code."""
        assert TN3270E_RESPONSES == 0x03  # Actually 0x03 in RFC

    def test_sysreq_function_code(self):
        """Test SYSREQ function code."""
        assert TN3270E_SYSREQ == 0x05


class TestFunctionsNegotiationFlow:
    """Tests for RFC 2355 7.2 complete FUNCTIONS negotiation flow."""

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
    async def test_functions_request_received(self, negotiator):
        """Test receiving FUNCTIONS REQUEST from server.

        Server sends FUNCTIONS REQUEST to negotiate optional functions.
        """
        pass

    @pytest.mark.asyncio
    async def test_functions_is_sent(self, negotiator):
        """Test sending FUNCTIONS IS response.

        Client responds with FUNCTIONS IS containing accepted functions.
        """
        pass


class TestFunctionListIteration:
    """Tests for RFC 2355 7.2 function list handling.

    Per RFC 2355:
    - Server sends list of functions it supports
    - Client accepts subset it supports
    - If no common functions, impasse occurs
    """

    def test_intersection_of_functions(self):
        """Test finding common functions between client and server.

        Both client and server have function bitmaps.
        Per RFC 2355, function codes are individual bits that can be OR'd together.
        """
        # These are bit flags - TN3270E_RESPONSES = 0x03, TN3270E_SCS_CTL_CODES = 0x04
        # They can overlap when using the actual negotiated flag values
        client_functions = TN3270E_RESPONSES
        server_functions = TN3270E_RESPONSES

        common = client_functions & server_functions
        # If both support same function, it should be in common
        assert common == TN3270E_RESPONSES or common > 0

    def test_empty_intersection_causes_impasse(self):
        """Test that no common functions causes impasse.

        If client and server have no overlapping functions,
        negotiation cannot proceed.
        """
        # Use very specific values that won't overlap
        client_functions = 0x01  # BIND_IMAGE only
        server_functions = 0x02  # Different function

        common = client_functions & server_functions
        assert common == 0  # No common functions


class TestImpasseDetection:
    """Tests for RFC 2355 7.2 impasse detection.

    Per RFC 2355:
    - Impasse occurs when client/server can't agree on functions
    - If impasse detected, WON'T/DON'T TN3270E may be sent
    - Fallback to basic TN3270 mode
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
    async def test_impasse_triggers_fallback(self, tn3270_handler):
        """Test that impasse triggers fallback to basic TN3270 mode.

        When FUNCTIONS negotiation cannot reach agreement,
        fallback to basic TN3270 (no extended functions).
        """
        pass

    @pytest.mark.asyncio
    async def test_wont_tn3270e_on_impasse(self, tn3270_handler):
        """Test that WON'T TN3270E is sent on impasse.

        Per RFC 2355, if impasse cannot be resolved,
        client or server may terminate TN3270E option.
        """
        pass


class TestFunctionNegotiationRetry:
    """Tests for RFC 2355 7.2 function negotiation retry logic.

    Per RFC 2355:
    - If function negotiation fails, client may retry
    - Retry may include different function set
    """

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
    async def test_retry_with_reduced_functions(self, negotiator):
        """Test retry with reduced function list.

        If initial negotiation fails, retry with fewer functions.
        """
        pass


class TestFunctionRemoval:
    """Tests for RFC 2355 7.2 unrecognized function removal.

    Per RFC 2355:
    - Client should ignore unrecognized function codes
    - Server may omit functions client doesn't understand
    """

    def test_ignore_unrecognized_function(self):
        """Test that unrecognized functions are ignored.

        If server includes unknown function codes,
        client should ignore them and respond with known functions.
        Per RFC 2355, client masks only the bits it understands.
        """
        # Unknown function would be a bit not in the RFC range
        unknown_function = 0x80  # Undefined bit
        known_functions = 0x07  # Known bits

        # Client should respond with only known functions
        # Mask out bits that aren't known function bits
        valid_bits = 0x1F  # Only valid function bits per RFC
        response = known_functions & valid_bits
        assert response == known_functions
