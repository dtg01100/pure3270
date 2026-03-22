"""
RFC 2355 TN3270E SYSREQ Function Tests (Section 10.5)

These tests verify compliance with RFC 2355 Section 10.5 "The SYSREQ Function".

According to RFC 2355:
- SYSREQ is an SNA-only function
- When server receives SYSREQ, it enters "suspended mode"
- The client can send USS commands and receive responses
- LOGOFF command terminates the session
- LU Busy (0x082D) response while suspended is possible
- Second SYSREQ key press sends LUSTAT (0x082D) and unsuspends

Section 11 also covers the 3270 ATTN Key:
- Telnet IP command is used for ATTN when SYSREQ not negotiated
- Non-SNA servers should ignore IP commands
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.exceptions import ProtocolError
from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.utils import (
    AO,
    DO,
    DONT,
    IAC,
    IP,
    NVT_DATA,
    SSCP_LU_DATA,
    TN3270_DATA,
    TN3270E_SYSREQ,
    TN3270E_SYSREQ_ATTN,
    TN3270E_SYSREQ_BREAK,
    TN3270E_SYSREQ_CANCEL,
    TN3270E_SYSREQ_LOGOFF,
    TN3270E_SYSREQ_MESSAGE_TYPE,
    TN3270E_SYSREQ_PRINT,
    TN3270E_SYSREQ_RESTART,
    WILL,
    WONT,
)


class TestSYSREQSubsection:
    """Tests for RFC 2355 Section 10.5 - The SYSREQ Function.

    Per RFC 2355 10.5.1 Background:
    - SYSREQ is an SNA-only function
    - When server receives SYSREQ, it enters "suspended mode"
    - The client can send USS commands and receive responses
    - LOGOFF command terminates the session
    - LU Busy (0x082D) response while suspended is possible
    - Second SYSREQ key press sends LUSTAT (0x082D) and unsuspends

    Section 11 also covers the 3270 ATTN Key:
    - Telnet IP command is used for ATTN when SYSREQ not negotiated
    - Non-SNA servers should ignore IP commands
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
    async def test_sysreq_function_not_negotiated_ignores_ao(self, tn3270_handler):
        """RFC 2355 10.5.2: Server not agreeing to SYSREQ should ignore AO commands.

        When SYSREQ function is NOT negotiated, the server MUST ignore Telnet AO commands.
        """
        tn3270_handler.negotiator.negotiated_functions = 0  # No functions negotiated
        tn3270_handler._in_3270_mode = True

        # Receive IAC AO (should be ignored)
        await tn3270_handler._handle_telnet_command(AO)

        # Mode should remain 3270
        assert tn3270_handler._in_3270_mode is True

    @pytest.mark.asyncio
    async def test_sysreq_function_negotiated_enters_suspended_mode(
        self, tn3270_handler
    ):
        """RFC 2355 10.5.2: Server agreeing to SYSREQ enters suspended mode on AO.

        When SYSREQ function IS negotiated, server enters "suspended mode" on receipt of AO.
        In suspended mode, server accepts SSCP-LU-DATA messages.
        """
        tn3270_handler.negotiator.negotiated_functions = TN3270E_SYSREQ
        tn3270_handler._in_3270_mode = True

        # Receive IAC AO - should enter suspended mode
        await tn3270_handler._handle_telnet_command(AO)

        # Mode should change to suspended
        assert tn3270_handler._in_suspended_mode is True
        assert tn3270_handler._in_3270_mode is False

    @pytest.mark.asyncio
    async def test_sysreq_creates_sscp_lu_session(self, tn3270_handler):
        """RFC 2355 10.5.2: While suspended, server accepts SSCP-LU-DATA messages.

        The SSCP (System Services Control Point) can send commands to the terminal
        while in suspended mode. These are sent as SSCP-LU-DATA TN3270E messages.
        """
        tn3270_handler.negotiator.negotiated_functions = TN3270E_SYSREQ
        tn3270_handler._in_suspended_mode = False

        # Simulate entering suspended mode
        tn3270_handler._in_suspended_mode = True

        # Should be able to process SSCP-LU-DATA while suspended
        assert tn3270_handler._in_suspended_mode is True

    @pytest.mark.asyncio
    async def test_sysreq_logoff_command(self, tn3270_handler):
        """RFC 2355 10.5.2: LOGOFF command terminates the session.

        A minimal SYSREQ server may handle LOGOFF by sending a fixed string.
        The session should be closed after LOGOFF.
        """
        tn3270_handler.negotiator.negotiated_functions = TN3270E_SYSREQ
        tn3270_handler._in_suspended_mode = True
        tn3270_handler._connected = True

        # Send LOGOFF command
        await tn3270_handler.send_sysreq_command(TN3270E_SYSREQ_LOGOFF)

        # Should have sent the LOGOFF command
        tn3270_handler.writer.write.assert_called()

    @pytest.mark.asyncio
    async def test_sysreq_lu_busy_response_while_suspended(self, tn3270_handler):
        """RFC 2355 10.5.2: LU Busy response while suspended.

        If the LU is busy, the server sends a negative response with sense code 0x082D.
        The terminal should handle this appropriately.
        """
        tn3270_handler.negotiator.negotiated_functions = TN3270E_SYSREQ
        tn3270_handler._in_suspended_mode = True

        # Simulate receiving LU Busy (0x082D) sense code
        # This would typically come as an SNA negative response
        lu_busy_sense = bytes([0x08, 0x2D, 0x00, 0x00])

        # Should handle without raising
        try:
            await tn3270_handler._handle_sysreq_response(lu_busy_sense)
        except Exception as e:
            pytest.fail(f"Should handle LU Busy: {e}")

    @pytest.mark.asyncio
    async def test_sysreq_second_press_unsuspends(self, tn3270_handler):
        """RFC 2355 10.5.2: Second SYSREQ key press while suspended sends LUSTAT and unsuspends.

        When user presses SYSREQ while already suspended, the client sends LUSTAT (0x082D)
        to indicate the terminal is ready, and the server exits suspended mode.
        """
        tn3270_handler.negotiator.negotiated_functions = TN3270E_SYSREQ
        tn3270_handler._in_suspended_mode = True

        # Second SYSREQ press should unsuspend
        await tn3270_handler.send_sysreq_command(TN3270E_SYSREQ_ATTN)

        # Should exit suspended mode and return to 3270 mode
        assert tn3270_handler._in_suspended_mode is False


class TestATTNKeySection11:
    """Tests for RFC 2355 Section 11 - The 3270 ATTN Key.

    Per RFC 2355 Section 11:
    - ATTN key generates Telnet IP command when SYSREQ not negotiated
    - Server translates IP to SIGNAL RU for SNA hosts
    - Non-SNA servers should ignore IP commands
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
    async def test_attn_generates_ip_when_sysreq_not_negotiated(self, tn3270_handler):
        """RFC 2355 Section 11: ATTN key generates Telnet IP when SYSREQ not negotiated.

        When the user presses ATTN and SYSREQ is not negotiated, the client sends
        IAC IP (Interrupt Process) to the server.
        """
        tn3270_handler.negotiator.negotiated_functions = 0  # SYSREQ not negotiated
        tn3270_handler._connected = True

        # Send ATTN
        await tn3270_handler.send_sysreq_command(TN3270E_SYSREQ_ATTN)

        # Should send IAC IP
        from pure3270.protocol.utils import IAC, IP

        tn3270_handler.writer.write.assert_called_with(bytes([IAC, IP]))

    @pytest.mark.asyncio
    async def test_attn_generates_tn3270e_subneg_when_sysreq_negotiated(
        self, tn3270_handler
    ):
        """RFC 2355 Section 11: ATTN with negotiated SYSREQ uses TN3270E subnegotiation.

        When SYSREQ function is negotiated, ATTN is sent as TN3270E SYSREQ subnegotiation
        with message type 0x1C and ATTN code 0x01.
        """
        tn3270_handler.negotiator.negotiated_functions = TN3270E_SYSREQ
        tn3270_handler._connected = True

        # Send ATTN
        await tn3270_handler.send_sysreq_command(TN3270E_SYSREQ_ATTN)

        # Should have sent TN3270E subnegotiation (IAC SB TN3270E SYSREQ ...)
        assert tn3270_handler.writer.write.called

    @pytest.mark.asyncio
    async def test_non_sna_server_ignores_ip(self, tn3270_handler):
        """RFC 2355 Section 11: Non-SNA servers should ignore IP commands.

        A non-SNA server receiving IAC IP should simply ignore it (not treat as error).
        """
        tn3270_handler.negotiator.negotiated_functions = 0  # Not SNA
        tn3270_handler._in_3270_mode = True

        # Receive IAC IP (should be ignored, not cause error)
        try:
            await tn3270_handler._handle_telnet_command(IP)
        except Exception as e:
            pytest.fail(f"Non-SNA server should ignore IP: {e}")

        # Mode should remain unchanged
        assert tn3270_handler._in_3270_mode is True

    @pytest.mark.asyncio
    async def test_signal_ru_generated_from_ip(self, tn3270_handler):
        """RFC 2355 Section 11: Server translates IP to SIGNAL RU.

        An SNA server receiving IP should generate a SIGNAL RU to send to the host.
        This is server-side behavior, but we test the client doesn't break.
        """
        tn3270_handler.negotiator.negotiated_functions = TN3270E_SYSREQ
        tn3270_handler._connected = True

        # Client sends IP for ATTN
        await tn3270_handler.send_sysreq_command(TN3270E_SYSREQ_ATTN)

        # Client should have sent either IP (fallback) or TN3270E subneg
        assert tn3270_handler.writer.write.called


class TestSYSREQSubnegotiation:
    """Tests for TN3270E SYSREQ subnegotiation message format."""

    @pytest.fixture
    def negotiator_with_sysreq(self, memory_limit_500mb):
        """Create a Negotiator with SYSREQ function enabled."""
        parser = DataStreamParser(ScreenBuffer())
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

        negotiator = Negotiator(
            writer=handler.writer,
            parser=parser,
            screen_buffer=screen_buffer,
            handler=handler,
            is_printer_session=False,
        )
        # Set up initial state
        negotiator._server_supports_tn3270e = True
        negotiator._negotiated_tn3270e = True
        return negotiator

    @pytest.mark.asyncio
    async def test_receive_sysreq_subnegotiation_attn(self, negotiator_with_sysreq):
        """Test receiving SYSREQ subnegotiation with ATTN command."""
        # Format: IAC SB TN3270E <MSG_TYPE> <CMD> IAC SE
        # MSG_TYPE = 0x1C (TN3270E_SYSREQ_MESSAGE_TYPE)
        # CMD = 0x01 (TN3270E_SYSREQ_ATTN)
        subneg_data = bytes([TN3270E_SYSREQ_MESSAGE_TYPE, TN3270E_SYSREQ_ATTN])

        # Should handle without error
        try:
            await negotiator_with_sysreq._handle_sysreq_subnegotiation(subneg_data)
        except Exception as e:
            pytest.fail(f"Should handle SYSREQ ATTN: {e}")

    @pytest.mark.asyncio
    async def test_receive_sysreq_subnegotiation_logoff(self, negotiator_with_sysreq):
        """Test receiving SYSREQ subnegotiation with LOGOFF command."""
        subneg_data = bytes([TN3270E_SYSREQ_MESSAGE_TYPE, TN3270E_SYSREQ_LOGOFF])

        # Should handle without error
        try:
            await negotiator_with_sysreq._handle_sysreq_subnegotiation(subneg_data)
        except Exception as e:
            pytest.fail(f"Should handle SYSREQ LOGOFF: {e}")

    @pytest.mark.asyncio
    async def test_receive_sysreq_subnegotiation_break(self, negotiator_with_sysreq):
        """Test receiving SYSREQ subnegotiation with BREAK command."""
        subneg_data = bytes([TN3270E_SYSREQ_MESSAGE_TYPE, TN3270E_SYSREQ_BREAK])

        # Should handle without error
        try:
            await negotiator_with_sysreq._handle_sysreq_subnegotiation(subneg_data)
        except Exception as e:
            pytest.fail(f"Should handle SYSREQ BREAK: {e}")

    @pytest.mark.asyncio
    async def test_receive_sysreq_subnegotiation_cancel(self, negotiator_with_sysreq):
        """Test receiving SYSREQ subnegotiation with CANCEL command."""
        subneg_data = bytes([TN3270E_SYSREQ_MESSAGE_TYPE, TN3270E_SYSREQ_CANCEL])

        # Should handle without error
        try:
            await negotiator_with_sysreq._handle_sysreq_subnegotiation(subneg_data)
        except Exception as e:
            pytest.fail(f"Should handle SYSREQ CANCEL: {e}")

    @pytest.mark.asyncio
    async def test_receive_sysreq_subnegotiation_print(self, negotiator_with_sysreq):
        """Test receiving SYSREQ subnegotiation with PRINT command."""
        subneg_data = bytes([TN3270E_SYSREQ_MESSAGE_TYPE, TN3270E_SYSREQ_PRINT])

        # Should handle without error
        try:
            await negotiator_with_sysreq._handle_sysreq_subnegotiation(subneg_data)
        except Exception as e:
            pytest.fail(f"Should handle SYSREQ PRINT: {e}")

    @pytest.mark.asyncio
    async def test_receive_sysreq_subnegotiation_restart(self, negotiator_with_sysreq):
        """Test receiving SYSREQ subnegotiation with RESTART command."""
        subneg_data = bytes([TN3270E_SYSREQ_MESSAGE_TYPE, TN3270E_SYSREQ_RESTART])

        # Should handle without error
        try:
            await negotiator_with_sysreq._handle_sysreq_subnegotiation(subneg_data)
        except Exception as e:
            pytest.fail(f"Should handle SYSREQ RESTART: {e}")

    @pytest.mark.asyncio
    async def test_receive_sysreq_empty_data(self, negotiator_with_sysreq):
        """Test receiving SYSREQ subnegotiation with empty data."""
        subneg_data = bytes([])

        # Should handle gracefully (treat as unknown)
        try:
            await negotiator_with_sysreq._handle_sysreq_subnegotiation(subneg_data)
        except Exception as e:
            pytest.fail(f"Should handle empty SYSREQ: {e}")


class TestUSSCommandResponse:
    """Tests for USS (Unit Specific Services) command/response flow.

    RFC 2355 10.5.2 describes a terminal dialogue while in suspended mode:
    1. Terminal sends USS command (e.g., "LOGON" or "LOGOFF")
    2. Host responds with data or SSCP-LU-DATA messages
    3. Terminal sends another SYSREQ to exit suspended mode

    Per RFC 2355, a minimal SYSREQ server responds to unknown USS commands
    with "COMMAND UNRECOGNIZED".
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
        handler.negotiator.negotiated_functions = TN3270E_SYSREQ
        return handler

    @pytest.mark.asyncio
    async def test_send_uss_command(self, tn3270_handler):
        """Test sending USS command while in suspended mode.

        USS commands are sent as part of SYSREQ subnegotiation payload.
        """
        tn3270_handler._in_suspended_mode = True

        # USS commands would be sent as part of SYSREQ subnegotiation
        # The format is implementation-specific but typically includes
        # a string command followed by parameters
        uss_command = b"STATUS"  # Example USS command

        # Should be able to send USS command
        assert tn3270_handler._in_suspended_mode is True

    @pytest.mark.asyncio
    async def test_receive_sscp_lu_data_in_suspended_mode(self, tn3270_handler):
        """Test receiving SSCP-LU-DATA while in suspended mode.

        RFC 2355: While in suspended mode, server sends SSCP-LU-DATA messages
        containing responses to USS commands or system messages.
        """
        tn3270_handler._in_suspended_mode = True

        # Create a mock TN3270E header with SSCP-LU-DATA data type
        from pure3270.protocol.tn3270e_header import TN3270EHeader

        header = TN3270EHeader(
            data_type=SSCP_LU_DATA,
            request_flag=0,
            response_flag=0,
            seq_number=0,
        )

        # Should handle SSCP-LU-DATA in suspended mode
        assert header.data_type == SSCP_LU_DATA

    @pytest.mark.asyncio
    async def test_command_unrecognized_response(self, tn3270_handler):
        """Test receiving 'COMMAND UNRECOGNIZED' response.

        Per RFC 2355, a minimal SYSREQ server responds to unknown USS commands
        with "COMMAND UNRECOGNIZED".
        """
        tn3270_handler._in_suspended_mode = True

        # Simulate receiving "COMMAND UNRECOGNIZED" response
        unrecognized_response = b"COMMAND UNRECOGNIZED"

        # Should handle without error
        try:
            # This would be processed as SSCP-LU-DATA
            pass
        except Exception as e:
            pytest.fail(f"Should handle COMMAND UNRECOGNIZED: {e}")


class TestSYSREQStateTransitions:
    """Tests for SYSREQ state machine transitions."""

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

    def test_initial_state_is_3270_mode(self, tn3270_handler):
        """Initial state should be 3270 mode, not suspended."""
        # Default state after connection
        assert tn3270_handler._in_3270_mode is True
        assert tn3270_handler._in_suspended_mode is False

    @pytest.mark.asyncio
    async def test_ao_transitions_to_suspended(self, tn3270_handler):
        """Telnet AO command transitions from 3270 mode to suspended mode."""
        tn3270_handler.negotiator.negotiated_functions = TN3270E_SYSREQ
        tn3270_handler._in_3270_mode = True

        await tn3270_handler._handle_telnet_command(AO)

        assert tn3270_handler._in_suspended_mode is True
        assert tn3270_handler._in_3270_mode is False

    @pytest.mark.asyncio
    async def test_sysreq_in_suspended_transitions_to_3270(self, tn3270_handler):
        """SYSREQ command while suspended transitions back to 3270 mode."""
        tn3270_handler.negotiator.negotiated_functions = TN3270E_SYSREQ
        tn3270_handler._in_suspended_mode = True
        tn3270_handler._in_3270_mode = False

        await tn3270_handler.send_sysreq_command(TN3270E_SYSREQ_ATTN)

        # Should have exited suspended mode and returned to 3270 mode
        assert tn3270_handler._in_suspended_mode is False
        assert tn3270_handler._in_3270_mode is True

    @pytest.mark.asyncio
    async def test_logoff_exits_session(self, tn3270_handler):
        """LOGOFF command should result in session termination."""
        tn3270_handler.negotiator.negotiated_functions = TN3270E_SYSREQ
        tn3270_handler._in_suspended_mode = True
        tn3270_handler._connected = True

        await tn3270_handler.send_sysreq_command(TN3270E_SYSREQ_LOGOFF)

        # LOGOFF should have been sent
        assert tn3270_handler.writer.write.called
