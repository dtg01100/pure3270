import asyncio
from unittest.mock import MagicMock, patch

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import (
    CMD_EW,
    WCC_BIT_KEYBOARD_RESTORE,
    DataStreamParser,
)
from pure3270.session import AsyncSession, Session


class TestC3270Compatibility:
    @pytest.mark.asyncio
    async def test_input_inhibited_lifecycle(self):
        """Test the lifecycle of Input Inhibited state."""
        # Setup session with mocked handler
        session = AsyncSession()
        session._handler = MagicMock()
        session._handler.send_data = MagicMock(return_value=asyncio.Future())
        session._handler.send_data.return_value.set_result(None)

        # Verify initial state (unlocked)
        assert session.screen_buffer.input_inhibited is False
        assert session.input_inhibited is False

        # 1. Simulate sending an AID (e.g. Enter)
        # This should lock the keyboard (Input Inhibited)
        enter_aid = AsyncSession.AID_MAP["Enter"]
        await session.submit(enter_aid)

        assert session.screen_buffer.input_inhibited is True
        assert session.input_inhibited is True

        # 2. Simulate receiving a Write command with Keyboard Restore (WCC bit 6)
        # This should unlock the keyboard

        # Create a parser attached to the session's screen buffer
        # We need to simulate the parser processing data that unlocks the keyboard
        parser = DataStreamParser(session.screen_buffer)

        # Verify manual unlock
        session.screen_buffer.set_keyboard_lock(False)
        assert session.input_inhibited is False

        # Re-lock
        await session.submit(enter_aid)
        assert session.input_inhibited is True

        # Verify parser unlocking
        # Command Erase Write (0x05)
        # WCC with Restore bit (0x40)
        cmd = CMD_EW
        wcc_byte = WCC_BIT_KEYBOARD_RESTORE
        data = bytes([cmd, wcc_byte])

        parser.parse(data)

        assert session.input_inhibited is False

        # 1. Simulate sending an AID (e.g. Enter)
        # This should lock the keyboard (Input Inhibited)
        await session.submit(0x7D)  # Enter AID

        assert session.screen_buffer.input_inhibited is True
        assert session.input_inhibited is True

        # 2. Simulate receiving a Write command with Keyboard Restore (WCC bit 6)
        # This should unlock the keyboard

        # Create a parser attached to the session's screen buffer
        # We need to simulate the parser processing data that unlocks the keyboard
        parser = DataStreamParser(session.screen_buffer)

        # Construct a 3270 data stream: Command (Write) + WCC (Restore)
        # Command 0x01 (Write) or 0x05 (Erase/Write)
        # WCC: 0xC2 (1100 0010) -> Reset MDT (bit 7) + Restore (bit 6) + ...
        # Actually simpler: 0x40 is just restore bit.
        # WCC_BIT_KEYBOARD_RESTORE = 0x40
        wcc = WCC_BIT_KEYBOARD_RESTORE

        # Parse data stream.
        # Note: DataStreamParser.parse expects data starting with command if it's TN3270_DATA
        # But wait, DataStreamParser.parse takes bytes.
        # If we pass raw bytes, the first byte is usually the command if we are simulating the handler feeding it.
        # But wait, DataStreamParser handles data types.

        # Let's look at DataStreamParser again. It processes WCC at the start of Write commands.
        # The parser is typically invoked with `parse(data, data_type)`.

        # We'll rely on the existing parser logic which we verified calls screen.set_keyboard_lock(False)

        # Just manually invoke the method on screen buffer to verify it works,
        # and then verify the parser calls it (mocking if necessary).

        # Verify manual unlock
        session.screen_buffer.set_keyboard_lock(False)
        assert session.input_inhibited is False

        # Re-lock
        await session.submit(0x7D)
        assert session.input_inhibited is True

        # Verify parser unlocking
        # Command 0xF1 (Write) is SNA? No, 0x01 is Write.
        # Let's use Erase Write (0x05)
        # WCC with Restore bit (0x40)
        cmd = 0x05
        wcc_byte = WCC_BIT_KEYBOARD_RESTORE
        data = bytes([cmd, wcc_byte])

        parser.parse(data)

        assert session.input_inhibited is False

    def test_sync_session_input_inhibited(self):
        """Test synchronous session exposes input_inhibited."""
        session = Session()
        # Mock the async session and its screen buffer
        session._async_session = MagicMock()
        session._async_session.input_inhibited = True

        assert session.input_inhibited is True

        session._async_session.input_inhibited = False
        assert session.input_inhibited is False
