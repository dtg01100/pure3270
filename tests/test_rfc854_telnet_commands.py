"""
RFC 854 Telnet Command Tests

These tests verify compliance with RFC 854 (Telnet Protocol Specification)
for basic Telnet commands.

According to RFC 854, the following commands are defined:
- SE (Subnegotiation End) - 0xF0
- NOP (No Operation) - 0xF1
- DM (Data Mark) - 0xF2 - urgent data mark
- BRK (Break) - 0xF3
- IP (Interrupt Process) - 0xF4
- AO (Abort Output) - 0xF5
- AYT (Are You There) - 0xF6
- EC (Erase Character) - 0xF7
- EL (Erase Line) - 0xF8
- GA (Go Ahead) - 0xF9
- SB (Subnegotiation Begin) - 0xFA
- WILL (Option 250) - 0xFB
- WONT (Option 251) - 0xFC
- DO (Option 252) - 0xFD
- DONT (Option 253) - 0xFE
- IAC (Interpret As Command) - 0xFF

This test module covers:
- AYT (Are You There) - RFC 854 Section 3.2.2
- NOP (No Operation) - RFC 854 Section 3.2.1
- SYNCH/DM (Urgent Data) - RFC 854 Section 3.2.1
- GA (Go Ahead) - RFC 854 Section 3.2.1
- EC (Erase Character) - RFC 854 Section 3.2.1
- EL (Erase Line) - RFC 854 Section 3.2.1
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.utils import (
    AO,
    AYT,
    BRK,
    DM,
    DO,
    DONT,
    EC,
    EL,
    GA,
    IAC,
    IP,
    NOP,
    SB,
    SE,
    WILL,
    WONT,
)


class TestAYTCommand:
    """Tests for RFC 854 AYT (Are You There) command.

    Per RFC 854 Section 3.2.2:
    "The AYT command is used to determine if the remote site is still
    active. Upon receipt of AYT, the receiver may (depending on the
    implementation) return some visual evidence that the command was
    received and the system is 'up'."

    AYT is commonly used by clients to verify the connection is alive.
    The server should respond with some indication that it is alive.
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

    def test_ayt_command_format(self):
        """Telnet AYT format: IAC AYT (0xFF 0xF6).

        IAC AYT is the Are You There command.
        """
        ayt_command = bytes([IAC, AYT])
        assert ayt_command[0] == 0xFF  # IAC
        assert ayt_command[1] == 0xF6  # AYT

    @pytest.mark.asyncio
    async def test_ayt_received_logs_debug(self, tn3270_handler):
        """Receipt of AYT should be logged at debug level.

        The handler should log when AYT is received.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            # Directly call the internal handler
            await tn3270_handler._handle_telnet_command(AYT)
            # Should log the AYT receipt
            mock_logger.debug.assert_called()
            # Check that "AYT" or "Are You There" appears in logged messages
            log_calls = [str(call) for call in mock_logger.debug.call_args_list]
            ayt_logged = any(
                "AYT" in call or "Are You There" in call for call in log_calls
            )
            assert ayt_logged, f"AYT not found in log calls: {log_calls}"

    @pytest.mark.asyncio
    async def test_ayt_via_process_telnet_stream(self, tn3270_handler):
        """IAC AYT through _process_telnet_stream should be recognized.

        The AYT command should be processed without error.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            # Process IAC AYT
            data = bytes([IAC, AYT])
            cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
            # No cleaned data should remain (AYT is a command, not data)
            assert cleaned_data == b""
            # Should log the AYT
            assert mock_logger.debug.called

    @pytest.mark.asyncio
    async def test_ayt_does_not_enter_3270_mode(self, tn3270_handler):
        """AYT should not affect 3270 mode state.

        AYT is just a check for aliveness, it should not change
        the current mode of operation.
        """
        tn3270_handler._in_3270_mode = True
        await tn3270_handler._handle_telnet_command(AYT)
        assert tn3270_handler._in_3270_mode is True


class TestNOPCommand:
    """Tests for RFC 854 NOP (No Operation) command.

    Per RFC 854 Section 3.2.1:
    "The NOP command is used to send no special effect."
    It is commonly used as a keep-alive mechanism (RFC 2355 13.3).
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

    def test_nop_command_format(self):
        """Telnet NOP format: IAC NOP (0xFF 0xF1).

        IAC NOP is the No Operation command.
        """
        nop_command = bytes([IAC, NOP])
        assert nop_command[0] == 0xFF  # IAC
        assert nop_command[1] == 0xF1  # NOP

    @pytest.mark.asyncio
    async def test_nop_received_logs_debug(self, tn3270_handler):
        """Receipt of NOP should be logged at debug level.

        The handler should log when NOP is received.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            await tn3270_handler._handle_telnet_command(NOP)
            mock_logger.debug.assert_called()
            log_calls = [str(call) for call in mock_logger.debug.call_args_list]
            nop_logged = any(
                "NOP" in call or "No Operation" in call for call in log_calls
            )
            assert nop_logged, f"NOP not found in log calls: {log_calls}"

    @pytest.mark.asyncio
    async def test_nop_via_process_telnet_stream(self, tn3270_handler):
        """IAC NOP through _process_telnet_stream should be recognized.

        The NOP command should be processed without error.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            data = bytes([IAC, NOP])
            cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
            assert cleaned_data == b""
            assert mock_logger.debug.called

    @pytest.mark.asyncio
    async def test_nop_does_not_affect_mode(self, tn3270_handler):
        """NOP should not affect 3270 mode or suspended mode.

        NOP is just a no-op, it should not change any state.
        """
        tn3270_handler._in_3270_mode = True
        tn3270_handler._in_suspended_mode = False
        await tn3270_handler._handle_telnet_command(NOP)
        assert tn3270_handler._in_3270_mode is True
        assert tn3270_handler._in_suspended_mode is False


class TestDMCommand:
    """Tests for RFC 854 DM (Data Mark) command.

    Per RFC 854 Section 3.2.1:
    "The DATA MARK command is the data stream position of the
    'urgent' section of the data stream."

    DM is used for urgent data (SYNCH mechanism). It should:
    - Flush the data stream
    - Be processed immediately regardless of data stream position
    - The receiver should flush pending data and process the urgent data
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

    def test_dm_command_format(self):
        """Telnet DM format: IAC DM (0xFF 0xF2).

        IAC DM is the Data Mark command for urgent data.
        """
        dm_command = bytes([IAC, DM])
        assert dm_command[0] == 0xFF  # IAC
        assert dm_command[1] == 0xF2  # DM

    @pytest.mark.asyncio
    async def test_dm_received_logs_debug(self, tn3270_handler):
        """Receipt of DM (Data Mark) should be logged.

        DM indicates urgent data that should be processed immediately.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            await tn3270_handler._handle_telnet_command(DM)
            mock_logger.debug.assert_called()
            log_calls = [str(call) for call in mock_logger.debug.call_args_list]
            dm_logged = any(
                "DM" in call or "Data Mark" in call or "urgent" in call.lower()
                for call in log_calls
            )
            assert dm_logged, f"DM not found in log calls: {log_calls}"

    @pytest.mark.asyncio
    async def test_dm_via_process_telnet_stream(self, tn3270_handler):
        """IAC DM through _process_telnet_stream should be recognized.

        The DM command should be processed without error.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            data = bytes([IAC, DM])
            cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
            assert cleaned_data == b""
            assert mock_logger.debug.called


class TestGACommand:
    """Tests for RFC 854 GA (Go Ahead) command.

    Per RFC 854 Section 3.2.1:
    "The GO AHEAD command is used in some line-oriented protocols
    to indicate that the receiver should go ahead and start
    transmitting."

    Historically used in half-duplex communication, but in modern
    TN3270 implementations it's typically ignored.
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

    def test_ga_command_format(self):
        """Telnet GA format: IAC GA (0xFF 0xF9).

        IAC GA is the Go Ahead command.
        """
        ga_command = bytes([IAC, GA])
        assert ga_command[0] == 0xFF  # IAC
        assert ga_command[1] == 0xF9  # GA

    @pytest.mark.asyncio
    async def test_ga_received_logs_debug(self, tn3270_handler):
        """Receipt of GA (Go Ahead) should be logged.

        GA is typically ignored but should be acknowledged.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            await tn3270_handler._handle_telnet_command(GA)
            mock_logger.debug.assert_called()
            log_calls = [str(call) for call in mock_logger.debug.call_args_list]
            ga_logged = any("GA" in call or "Go Ahead" in call for call in log_calls)
            assert ga_logged, f"GA not found in log calls: {log_calls}"

    @pytest.mark.asyncio
    async def test_ga_via_process_telnet_stream(self, tn3270_handler):
        """IAC GA through _process_telnet_stream should be recognized.

        The GA command should be processed without error.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            data = bytes([IAC, GA])
            cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
            assert cleaned_data == b""
            assert mock_logger.debug.called


class TestECCommand:
    """Tests for RFC 854 EC (Erase Character) command.

    Per RFC 854 Section 3.2.1:
    "The ERASE CHARACTER command causes the receiver to delete
    the last undeleted character from the data stream."

    EC should erase the previous character in the input buffer.
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

    def test_ec_command_format(self):
        """Telnet EC format: IAC EC (0xFF 0xF7).

        IAC EC is the Erase Character command.
        """
        ec_command = bytes([IAC, EC])
        assert ec_command[0] == 0xFF  # IAC
        assert ec_command[1] == 0xF7  # EC

    @pytest.mark.asyncio
    async def test_ec_received_logs_debug(self, tn3270_handler):
        """Receipt of EC (Erase Character) should be logged.

        EC should cause deletion of the last undeleted character.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            await tn3270_handler._handle_telnet_command(EC)
            mock_logger.debug.assert_called()
            log_calls = [str(call) for call in mock_logger.debug.call_args_list]
            ec_logged = any(
                "EC" in call or "Erase Character" in call for call in log_calls
            )
            assert ec_logged, f"EC not found in log calls: {log_calls}"

    @pytest.mark.asyncio
    async def test_ec_via_process_telnet_stream(self, tn3270_handler):
        """IAC EC through _process_telnet_stream should be recognized.

        The EC command should be processed without error.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            data = bytes([IAC, EC])
            cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
            assert cleaned_data == b""
            assert mock_logger.debug.called


class TestELCommand:
    """Tests for RFC 854 EL (Erase Line) command.

    Per RFC 854 Section 3.2.1:
    "The ERASE LINE command causes the receiver to delete all
    undeleted characters from the data stream."

    EL should erase the entire current line in the input buffer.
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

    def test_el_command_format(self):
        """Telnet EL format: IAC EL (0xFF 0xF8).

        IAC EL is the Erase Line command.
        """
        el_command = bytes([IAC, EL])
        assert el_command[0] == 0xFF  # IAC
        assert el_command[1] == 0xF8  # EL

    @pytest.mark.asyncio
    async def test_el_received_logs_debug(self, tn3270_handler):
        """Receipt of EL (Erase Line) should be logged.

        EL should cause deletion of all undeleted characters on the line.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            await tn3270_handler._handle_telnet_command(EL)
            mock_logger.debug.assert_called()
            log_calls = [str(call) for call in mock_logger.debug.call_args_list]
            el_logged = any("EL" in call or "Erase Line" in call for call in log_calls)
            assert el_logged, f"EL not found in log calls: {log_calls}"

    @pytest.mark.asyncio
    async def test_el_via_process_telnet_stream(self, tn3270_handler):
        """IAC EL through _process_telnet_stream should be recognized.

        The EL command should be processed without error.
        """
        with patch("pure3270.protocol.tn3270_handler.logger") as mock_logger:
            data = bytes([IAC, EL])
            cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
            assert cleaned_data == b""
            assert mock_logger.debug.called


class TestTelnetCommandProcessing:
    """Tests for overall Telnet command processing behavior."""

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
    async def test_all_telnet_commands_recognized(self, tn3270_handler):
        """All defined RFC 854 commands should be recognized without error.

        Commands: NOP, DM, BRK, IP, AO, AYT, EC, EL, GA
        """
        commands = [
            (NOP, b"IAC NOP"),
            (DM, b"IAC DM"),
            (BRK, b"IAC BRK"),
            (IP, b"IAC IP"),
            (AO, b"IAC AO"),
            (AYT, b"IAC AYT"),
            (EC, b"IAC EC"),
            (EL, b"IAC EL"),
            (GA, b"IAC GA"),
        ]

        for cmd, name in commands:
            # Should not raise
            await tn3270_handler._handle_telnet_command(cmd)

    @pytest.mark.asyncio
    async def test_iac_iac_in_data_is_escaped_byte(self, tn3270_handler):
        """IAC IAC (0xFF 0xFF) in data represents a single 0xFF data byte.

        Per RFC 854 Section 3.2.1, within the data stream, 0xFF must be doubled
        (IAC IAC) to indicate a data byte of 0xFF. The TN3270Handler must properly
        handle IAC escaping at the telnet stream processing layer.

        IAC IAC in the telnet stream should produce a single 0xFF byte in the
        cleaned data, not be treated as two separate IAC commands.
        """
        # IAC IAC in telnet stream = single 0xFF data byte, followed by AB
        data = bytes([0xFF, 0xFF, 0x41, 0x42])  # IAC IAC AB = 0xFF AB
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        # IAC IAC should produce single 0xFF, leaving 0xFF AB
        assert cleaned_data == bytes([0xFF, 0x41, 0x42])

    @pytest.mark.asyncio
    async def test_lone_iac_at_end_buffered(self, tn3270_handler):
        """A lone IAC at the end of data should be buffered for next chunk.

        If we receive an incomplete IAC sequence, it should be buffered.
        """
        # Send just IAC without command
        data = bytes([IAC])
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        # Nothing processed yet
        assert cleaned_data == b""
        # IAC should be buffered
        assert tn3270_handler._telnet_buffer == bytes([IAC])

    @pytest.mark.asyncio
    async def test_iac_with_unknown_command_ignored(self, tn3270_handler):
        """IAC with an unknown command should be ignored.

        Commands not recognized should be silently ignored per RFC 854.
        """
        # 0xF0 (SE) is technically a valid byte but not a command we handle
        # directly in the else branch; it should be handled but we don't crash
        data = bytes([IAC, 0xF0])
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        assert cleaned_data == b""


class TestSYNCHMechanism:
    """Tests for RFC 854 SYNCH mechanism (urgent data).

    Per RFC 854:
    The SYNCH mechanism uses DM (Data Mark) sent with urgent data.
    The sequence is:
    - IAC DM (data mark)
    - Urgent data follows

    The receiver should:
    1. Immediately process the DM
    2. Discard any pending non-urgent data
    3. Process the urgent data
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
    async def test_synch_sequence(self, tn3270_handler):
        """SYNCH is IAC DM followed by urgent data.

        The DM marks the start of urgent data.
        """
        # IAC DM
        dm_command = bytes([IAC, DM])
        assert dm_command[0] == IAC
        assert dm_command[1] == DM

    @pytest.mark.asyncio
    async def test_urgent_data_following_dm(self, tn3270_handler):
        """Data following IAC DM is considered urgent.

        DM (Data Mark) indicates urgent data per RFC 854 SYNCH mechanism.
        In our implementation, DM is logged and consumed, but the actual
        urgent data handling (discarding pending data, processing urgently)
        is a more advanced feature that would require additional implementation.

        For now, DM is recognized and logged, but subsequent data passes
        through normally.
        """
        # Sequence: IAC DM followed by some data
        data = bytes([IAC, DM, 0x01, 0x02, 0x03])
        cleaned_data, ascii_mode = await tn3270_handler._process_telnet_stream(data)
        # DM is consumed (logged), data after DM passes through as normal data
        assert cleaned_data == bytes([0x01, 0x02, 0x03])


class TestCommandConstants:
    """Tests to verify RFC 854 command constants are correct."""

    def test_iac_constant(self):
        """IAC (Interpret As Command) must be 0xFF."""
        assert IAC == 0xFF

    def test_command_values(self):
        """Verify all command values match RFC 854."""
        assert SE == 0xF0
        assert NOP == 0xF1
        assert DM == 0xF2
        assert BRK == 0xF3
        assert IP == 0xF4
        assert AO == 0xF5
        assert AYT == 0xF6
        assert EC == 0xF7
        assert EL == 0xF8
        assert GA == 0xF9
        assert SB == 0xFA
        assert WILL == 0xFB
        assert WONT == 0xFC
        assert DO == 0xFD
        assert DONT == 0xFE
        # IAC is 0xFF (already verified above)
        assert IAC == 0xFF
