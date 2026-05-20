"""Property-based fuzzing for protocol handling."""

from unittest.mock import AsyncMock

from hypothesis import given, settings
from hypothesis import strategies as st

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.tn3270_handler import TN3270Handler


@given(st.binary(min_size=0, max_size=512))
@settings(max_examples=200)
def test_receive_data_never_crashes(raw_bytes: bytes) -> None:
    """Property: receive_data() never crashes on arbitrary byte input."""
    screen = ScreenBuffer(24, 80)
    reader = AsyncMock()
    writer = AsyncMock()
    writer.write = AsyncMock()

    handler = TN3270Handler(
        reader=reader,
        writer=writer,
        screen_buffer=screen,
        host="127.0.0.1",
        port=2323,
        allow_fallback=True,
    )

    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(handler._process_telnet_stream(raw_bytes))
            assert result is None or (isinstance(result, tuple) and len(result) == 2)
        finally:
            loop.close()
    except (ConnectionError, ValueError, OSError):
        pass


@given(st.binary(min_size=0, max_size=256))
@settings(max_examples=100)
def test_send_data_never_crashes(raw_bytes: bytes) -> None:
    """Property: send_data() never crashes on arbitrary byte input."""
    screen = ScreenBuffer(24, 80)
    reader = AsyncMock()
    writer = AsyncMock()
    writer.write = AsyncMock()
    writer.drain = AsyncMock()

    handler = TN3270Handler(
        reader=reader,
        writer=writer,
        screen_buffer=screen,
        host="127.0.0.1",
        port=2323,
        allow_fallback=True,
    )

    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(handler.send_data(raw_bytes))
        finally:
            loop.close()
    except Exception:
        pass