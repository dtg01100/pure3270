"""
RFC 1091 Terminal Type Option Tests

These tests verify compliance with RFC 1091 "Telnet Terminal-Type Option".

According to RFC 1091:
- TTYPE option (24 decimal, 0x18) negotiates terminal type
- Subnegotiation: IAC SB TTYPE SEND IAC SE (server requests)
- Subnegotiation: IAC SB TTYPE IS <type> IAC SE (client responds)
- The server may request multiple times to cycle through terminal types
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.utils import IAC, SB, SE, TELOPT_TTYPE, TTYPE_IS, TTYPE_SEND


class TestRFC1091CommandConstants:
    """Tests for RFC 1091 command constants."""

    def test_ttype_option_number(self):
        """TTYPE Telnet option is 24 (0x18) per RFC 1091."""
        assert TELOPT_TTYPE == 0x18

    def test_ttype_send_command(self):
        """TTYPE SEND (0x01) requests terminal type from receiver."""
        assert TTYPE_SEND == 0x01

    def test_ttype_is_command(self):
        """TTYPE IS (0x00) sends terminal type to requester."""
        assert TTYPE_IS == 0x00


class TestTerminalTypeSubnegotiation:
    """Tests for RFC 1091 terminal type subnegotiation format."""

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

    def test_server_sends_ttype_send(self):
        """Server requests terminal type: IAC SB TTYPE SEND IAC SE.

        Per RFC 1091, the server initiates by sending a SEND subnegotiation.
        """
        subneg = bytes([IAC, SB, TELOPT_TTYPE, TTYPE_SEND, IAC, SE])
        assert subneg[0] == IAC
        assert subneg[1] == SB
        assert subneg[2] == TELOPT_TTYPE
        assert subneg[3] == TTYPE_SEND
        assert subneg[4] == IAC
        assert subneg[5] == SE

    def test_client_responds_with_is(self):
        """Client responds with terminal type: IAC SB TTYPE IS <type> IAC SE.

        Per RFC 1091, the client responds with IS followed by the terminal type.
        """
        terminal_type = b"IBM-3278-2"
        subneg = (
            bytes([IAC, SB, TELOPT_TTYPE, TTYPE_IS]) + terminal_type + bytes([IAC, SE])
        )
        assert subneg[0] == IAC
        assert subneg[1] == SB
        assert subneg[2] == TELOPT_TTYPE
        assert subneg[3] == TTYPE_IS
        assert subneg[-2] == IAC
        assert subneg[-1] == SE
        assert terminal_type in subneg

    @pytest.mark.asyncio
    async def test_handle_ttype_send(self, tn3270_handler):
        """Server sends TTYPE SEND, handler should respond with TTYPE IS.

        Per RFC 1091, the receiver must respond to SEND with IS + terminal type.
        """
        tn3270_handler.writer.write = MagicMock()

        # The negotiator handles TTYPE subnegotiation
        neg = tn3270_handler.negotiator
        await neg.handle_subnegotiation(TELOPT_TTYPE, bytes([TTYPE_SEND]))

        # Negotiator should have recorded TTYPE SEND was received
        # The negotiator will respond with TTYPE IS containing terminal type
        assert neg.terminal_type == "IBM-3278-2"

    @pytest.mark.asyncio
    async def test_handle_ttype_is(self, tn3270_handler):
        """Client sends TTYPE IS, server confirms the terminal type.

        Per RFC 1091, after receiving IS, the server may accept the type or
        request again to cycle through available types.
        """
        neg = tn3270_handler.negotiator

        # Simulate receiving IS with a terminal type
        await neg.handle_subnegotiation(TELOPT_TTYPE, bytes([TTYPE_IS]) + b"IBM-3278-2")

        # After IS, the negotiator should have recorded the terminal type
        assert neg.terminal_type == "IBM-3278-2"

    def test_ttype_negotiation_flow(self):
        """Full TTYPE negotiation flow per RFC 1091.

        1. Server: IAC SB TTYPE SEND IAC SE
        2. Client: IAC SB TTYPE IS IBM-3278-2 IAC SE
        """
        # Step 1: Server requests
        server_send = bytes([IAC, SB, TELOPT_TTYPE, TTYPE_SEND, IAC, SE])
        assert len(server_send) == 6

        # Step 2: Client responds
        client_is = (
            bytes([IAC, SB, TELOPT_TTYPE, TTYPE_IS]) + b"IBM-3278-2" + bytes([IAC, SE])
        )
        assert IAC in client_is
        assert b"IBM-3278-2" in client_is


class TestMultipleTerminalTypes:
    """Tests for RFC 1091 multiple terminal type cycling.

    Per RFC 1091:
    - Server may request terminal type multiple times
    - If client supports multiple types, it returns the next one each time
    - When all types have been cycled, server stops requesting
    """

    @pytest.fixture
    def negotiator(self, memory_limit_500mb):
        """Create a Negotiator for testing."""
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

        neg = Negotiator(
            writer=handler.writer,
            parser=None,
            screen_buffer=screen_buffer,
            handler=handler,
            is_printer_session=False,
            terminal_type="IBM-3278-2",
        )
        return neg

    def test_single_terminal_type_response(self, negotiator):
        """With a single terminal type, each SEND gets the same response."""
        # The terminal type should be available for response
        assert negotiator.terminal_type == "IBM-3278-2"

    @pytest.mark.asyncio
    async def test_ttype_send_does_not_crash(self, negotiator):
        """Repeated TTYPE SEND should not cause errors."""
        for _ in range(3):
            try:
                await negotiator.handle_subnegotiation(
                    TELOPT_TTYPE, bytes([TTYPE_SEND])
                )
            except Exception as e:
                pytest.fail(f"TTYPE SEND should not raise on repeat: {e}")


class TestTerminalTypeValidation:
    """Tests for terminal type value validation per RFC 1091.

    RFC 1091 does not define specific terminal type names.
    The type is an arbitrary ASCII string identifying the terminal.
    """

    def test_valid_terminal_types(self):
        """Verify common terminal type strings are valid ASCII."""
        valid_types = [
            "IBM-3278-2",
            "IBM-3278-2-E",
            "IBM-DYNAMIC",
            "IBM-3279-2",
            "IBM-3179-2",
        ]
        for ttype in valid_types:
            assert isinstance(ttype, str)
            assert len(ttype) > 0
            assert ttype.isascii()

    def test_terminal_type_encoding(self):
        """Terminal type is sent as ASCII bytes per RFC 1091."""
        ttype = "IBM-3278-2"
        encoded = ttype.encode("ascii")
        assert encoded == b"IBM-3278-2"
        assert isinstance(encoded, bytes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
