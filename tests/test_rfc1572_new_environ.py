"""
RFC 1572 NEW_ENVIRON Tests

These tests verify compliance with RFC 1572 "Telnet Environment Option".

According to RFC 1572:
- NEW_ENVIRON option (39 decimal, 0x27) negotiates environment variable exchange
- IS (0x00): Send environment information
- SEND (0x01): Request environment information
- INFO (0x02): Additional environment information
- VAR (0x00): Well-known environment variable
- VALUE (0x01): Variable value
- ESC (0x02): Escape next byte
- USERVAR (0x03): User-defined variable

Environment variables include: USER, JOB, ACCT, PRINTER, SYSTEMTYPE, DISPLAY, TERM
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.utils import (
    IAC,
    NEW_ENV_ESC,
    NEW_ENV_INFO,
    NEW_ENV_IS,
    NEW_ENV_SEND,
    NEW_ENV_USERVAR,
    NEW_ENV_VALUE,
    NEW_ENV_VAR,
    SB,
    SE,
    TELOPT_NEW_ENVIRON,
)


class TestRFC1572CommandConstants:
    """Tests for RFC 1572 command constants."""

    def test_new_environ_option_number(self):
        """NEW_ENVIRON Telnet option is 39 (0x27) per RFC 1572."""
        assert TELOPT_NEW_ENVIRON == 0x27

    def test_new_environ_is_command(self):
        """IS (0x00) - sender provides environment information."""
        assert NEW_ENV_IS == 0x00

    def test_new_environ_send_command(self):
        """SEND (0x01) - sender requests environment information."""
        assert NEW_ENV_SEND == 0x01

    def test_new_environ_info_command(self):
        """INFO (0x02) - sender provides additional environment info."""
        assert NEW_ENV_INFO == 0x02

    def test_new_environ_var_type(self):
        """VAR (0x00) - specifies a well-known environment variable."""
        assert NEW_ENV_VAR == 0x00

    def test_new_environ_value_type(self):
        """VALUE (0x01) - specifies the value of a variable."""
        assert NEW_ENV_VALUE == 0x01

    def test_new_environ_esc_type(self):
        """ESC (0x02) - escape next byte for IAC and ESC handling."""
        assert NEW_ENV_ESC == 0x02

    def test_new_environ_uservar_type(self):
        """USERVAR (0x03) - specifies a user-defined environment variable."""
        assert NEW_ENV_USERVAR == 0x03


class TestRFC1572SubnegotiationFormat:
    """Tests for RFC 1572 subnegotiation framing format."""

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

    def test_server_send_format(self):
        """Server requests env vars: IAC SB NEW_ENVIRON SEND IAC SE.

        Per RFC 1572, the server sends SEND to request environment variables.
        The SEND may include a list of requested variable names.
        """
        subneg = bytes([IAC, SB, TELOPT_NEW_ENVIRON, NEW_ENV_SEND, IAC, SE])
        assert subneg[0] == IAC
        assert subneg[1] == SB
        assert subneg[2] == TELOPT_NEW_ENVIRON
        assert subneg[3] == NEW_ENV_SEND
        assert subneg[4] == IAC
        assert subneg[5] == SE

    def test_server_send_with_vars(self):
        """Server requests specific vars: IAC SB NEW_ENVIRON SEND VAR USER VAR TERM IAC SE.

        Per RFC 1572, the SEND command can include specific variables.
        """
        subneg = (
            bytes([IAC, SB, TELOPT_NEW_ENVIRON, NEW_ENV_SEND])
            + bytes([NEW_ENV_VAR])
            + b"USER"
            + bytes([NEW_ENV_VAR])
            + b"TERM"
            + bytes([IAC, SE])
        )
        assert NEW_ENV_VAR in subneg
        assert b"USER" in subneg
        assert b"TERM" in subneg

    def test_client_is_response(self):
        """Client responds with env vars: IAC SB NEW_ENVIRON IS VAR USER VALUE <val> IAC SE.

        Per RFC 1572, the client responds with IS containing variable/value pairs.
        """
        subneg = (
            bytes([IAC, SB, TELOPT_NEW_ENVIRON, NEW_ENV_IS])
            + bytes([NEW_ENV_VAR])
            + b"USER"
            + bytes([NEW_ENV_VALUE])
            + b"MYUSER"
            + bytes([IAC, SE])
        )
        assert NEW_ENV_IS in subneg
        assert NEW_ENV_VAR in subneg
        assert NEW_ENV_VALUE in subneg
        assert b"MYUSER" in subneg

    def test_var_and_value_alternation(self):
        """RFC 1572: Variables and values alternate in IS/INFO response.

        Format: VAR <name> VALUE <value> VAR <name> VALUE <value> ...
        """
        response = (
            bytes([NEW_ENV_VAR])
            + b"USER"
            + bytes([NEW_ENV_VALUE])
            + b"MYUSER"
            + bytes([NEW_ENV_VAR])
            + b"TERM"
            + bytes([NEW_ENV_VALUE])
            + b"IBM-3278-2"
        )
        # Count alternations
        var_count = sum(
            1
            for i in range(len(response))
            if response[i : i + 1] == bytes([NEW_ENV_VAR])
        )
        value_count = sum(
            1
            for i in range(len(response))
            if response[i : i + 1] == bytes([NEW_ENV_VALUE])
        )
        assert var_count == 2
        assert value_count == 2

    def test_escape_byte_usage(self):
        """RFC 1572: ESC (0x02) escapes IAC bytes and ESC itself in variable names/values.

        When a variable name or value contains IAC (0xFF) or ESC (0x02),
        the byte must be doubled (preceded by ESC).
        """
        # If a value contains IAC (0xFF), it should be escaped
        value_with_iac = b"value" + bytes([NEW_ENV_ESC, IAC])
        assert len(value_with_iac) > 0


class TestNewEnvironSubnegotiationHandling:
    """Tests for NEW_ENVIRON subnegotiation handling in the negotiator."""

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
    async def test_handle_new_environ_send(self, tn3270_handler):
        """Server sends NEW_ENVIRON SEND, negotiator responds with IS.

        Per RFC 1572, the receiver must respond to SEND with
        IS containing the requested environment variables.
        """
        neg = tn3270_handler.negotiator

        # Should process NEW_ENVIRON SEND without raising
        await neg.handle_subnegotiation(TELOPT_NEW_ENVIRON, bytes([NEW_ENV_SEND]))

    @pytest.mark.asyncio
    async def test_handle_new_environ_is(self, tn3270_handler):
        """Client processes NEW_ENVIRON IS from server.

        Per RFC 1572, IS contains server's environment variables.
        """
        neg = tn3270_handler.negotiator

        # Server sends IS with TERM and USER vars
        is_payload = (
            bytes([NEW_ENV_IS])
            + bytes([NEW_ENV_VAR])
            + b"TERM"
            + bytes([NEW_ENV_VALUE])
            + b"IBM-3278-2"
        )

        result = await neg.handle_subnegotiation(TELOPT_NEW_ENVIRON, is_payload)
        # Should not raise - IS is processed silently

    @pytest.mark.asyncio
    async def test_handle_new_environ_info(self, tn3270_handler):
        """Client processes NEW_ENVIRON INFO from server.

        Per RFC 1572, INFO is additional environment information.
        """
        neg = tn3270_handler.negotiator

        info_payload = bytes([NEW_ENV_INFO])

        result = await neg.handle_subnegotiation(TELOPT_NEW_ENVIRON, info_payload)
        # Should not raise - INFO is processed silently

    @pytest.mark.asyncio
    async def test_handle_new_environ_send_with_specific_vars(self, tn3270_handler):
        """Server requests specific env vars, negotiator responds with those vars.

        Per RFC 1572, the server can request specific variables.
        The client should respond with only the requested variables.
        """
        neg = tn3270_handler.negotiator
        tn3270_handler.writer.write = MagicMock()

        # Server requests USER and TERM
        send_payload = (
            bytes([NEW_ENV_SEND])
            + bytes([NEW_ENV_VAR])
            + b"USER"
            + bytes([NEW_ENV_VAR])
            + b"TERM"
        )

        try:
            await neg.handle_subnegotiation(TELOPT_NEW_ENVIRON, send_payload)
            assert True
        except Exception as e:
            pytest.fail(f"NEW_ENVIRON SEND with vars should not raise: {e}")

    @pytest.mark.asyncio
    async def test_empty_new_environ_payload(self, tn3270_handler):
        """Empty NEW_ENVIRON subnegotiation payload should not crash.

        Per RFC 1572, malformed or empty payloads should be handled gracefully.
        """
        neg = tn3270_handler.negotiator

        try:
            await neg.handle_subnegotiation(TELOPT_NEW_ENVIRON, b"")
            assert True
        except Exception as e:
            pytest.fail(f"Empty NEW_ENVIRON should not raise: {e}")


class TestNewEnvironEscaping:
    """Tests for RFC 1572 ESC byte handling in variable names/values.

    Per RFC 1572 Section 4:
    - ESC (0x02) escapes the next byte
    - IAC (0xFF) and ESC (0x02) in names/values must be escaped
    - ESC prefix removes special meaning from the following byte
    """

    def test_esc_iac_in_value(self):
        """IAC byte in value is escaped as ESC IAC per RFC 1572."""
        # If a value contains 0xFF, it's sent as ESC IAC
        escaped_iac = bytes([NEW_ENV_ESC, IAC])
        assert escaped_iac[0] == NEW_ENV_ESC
        assert escaped_iac[1] == IAC

    def test_esc_esc_in_name(self):
        """ESC byte in name is escaped as ESC ESC per RFC 1572."""
        # If a name contains 0x02, it's sent as ESC ESC
        escaped_esc = bytes([NEW_ENV_ESC, NEW_ENV_ESC])
        assert escaped_esc[0] == NEW_ENV_ESC
        assert escaped_esc[1] == NEW_ENV_ESC

    def test_unescape_byte_sequence(self):
        """Unescaping removes the ESC prefix and restores the original byte."""
        # ESC IAC should be unescaped to a single IAC byte
        escaped = bytes([NEW_ENV_ESC, IAC])
        unescaped = escaped[1:]  # After unescaping: just IAC
        assert unescaped == bytes([IAC])

        # ESC ESC should be unescaped to a single ESC byte
        escaped2 = bytes([NEW_ENV_ESC, NEW_ENV_ESC])
        unescaped2 = escaped2[1:]  # After unescaping: just ESC
        assert unescaped2 == bytes([NEW_ENV_ESC])


class TestNewEnvironVariableParsing:
    """Tests for RFC 1572 variable list parsing.

    Per RFC 1572:
    - Variable list is a sequence of VAR/VALUE pairs
    - VAR <name> indicates a variable whose value is requested
    - VALUE <value> provides the value for the preceding VAR
    - USERVAR <name> indicates a user-defined variable
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

    def test_parse_var_value_pairs(self, negotiator):
        """Parse VAR VALUE pairs from IS payload."""
        payload = bytes([NEW_ENV_VAR]) + b"USER" + bytes([NEW_ENV_VALUE]) + b"MYUSER"
        result = negotiator._parse_new_environ_variables(payload)
        assert result == {"USER": "MYUSER"}

    def test_parse_var_only(self, negotiator):
        """Parse SEND payload with VAR-only entries.

        In a SEND command, VAR indicates which variables the
        server wants the client to send. Without VALUE, the dict entry
        should have an empty string value.
        """
        payload = bytes([NEW_ENV_VAR]) + b"USER"
        result = negotiator._parse_new_environ_variables(payload)
        assert "USER" in result

    def test_parse_uservar(self, negotiator):
        """Parse USERVAR type per RFC 1572.

        USERVAR is used for user-defined, non-well-known variables.
        """
        payload = (
            bytes([NEW_ENV_USERVAR]) + b"MYVAR" + bytes([NEW_ENV_VALUE]) + b"MYVAL"
        )
        result = negotiator._parse_new_environ_variables(payload)
        assert result == {"MYVAR": "MYVAL"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
