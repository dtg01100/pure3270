import asyncio
import time

import pytest

from mock_server.tn3270_mock_server import EnhancedTN3270MockServer
from pure3270 import Session
from pure3270.utils.common import decode_ebcdic_string


@pytest.mark.timeout(8)
def test_3270_extended_payload_writes_to_screen():
    server = EnhancedTN3270MockServer()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.start())
    try:
        s = Session()
        s.open(server.host, server.port)
        deadline = time.time() + 5
        while time.time() < deadline and not s.tn3270e_mode:
            time.sleep(0.05)
        assert s.tn3270e_mode, "TN3270E mode not established"
        # Access screen buffer
        handler = getattr(s, "_handler", None)
        if handler is None:
            async_session = getattr(s, "_async_session", None)
            handler = getattr(async_session, "_handler", None)
        screen = getattr(handler, "screen_buffer", None)
        assert screen is not None, "ScreenBuffer not available"
        # Decode head of screen buffer to ASCII and look for HELLO and WORLD
        raw = bytes(screen.buffer[:160])
        decoded = decode_ebcdic_string(raw)
        assert "HELLO" in decoded, f"HELLO not found in screen: '{decoded}'"
        assert "WORLD" in decoded, f"WORLD not found in screen: '{decoded}'"
        s.close()
    finally:
        loop.run_until_complete(server.stop())
        loop.close()
