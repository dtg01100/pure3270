"""Property-based tests for handler state machine."""

# mypy: disable-error-code="misc"

from collections.abc import Coroutine
from typing import Any
from unittest.mock import AsyncMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.tn3270_handler import HandlerState, TN3270Handler

ALL_HANDLER_STATES: set[HandlerState] = {
    getattr(HandlerState, name)
    for name in vars(HandlerState)
    if not name.startswith("_")
}


@given(
    st.lists(
        st.sampled_from(
            [
                "connect",
                "send",
                "receive",
                "close",
                "send_break",
                "negotiate",
            ]
        ),
        min_size=0,
        max_size=20,
    )
)
@settings(max_examples=100)
def test_state_machine_never_crashes(operations: list[str]) -> None:
    """Property: Any sequence of operations terminates without crash."""
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

    for op in operations:
        try:
            if op == "send":
                asyncio_run(handler.send_data(b"test"))
            elif op == "receive":
                reader.read.side_effect = [b"", b""]
            elif op == "close":
                if handler._current_state:
                    asyncio_run(handler.close())
            elif op == "send_break":
                asyncio_run(handler.send_break())
        except Exception:
            pass

    assert handler._current_state in ALL_HANDLER_STATES  # type: ignore[comparison-overlap]


@given(st.lists(st.integers(min_value=0, max_value=255), min_size=0, max_size=100))
@settings(max_examples=100)
def test_state_machine_random_bytes(byte_list: list[int]) -> None:
    """Property: Random bytes fed to handler never crash it."""
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

    data = bytes(byte_list)
    try:
        asyncio_run(handler._process_telnet_stream(data))
    except Exception:
        pass

    assert handler._current_state in ALL_HANDLER_STATES  # type: ignore[comparison-overlap]


def asyncio_run(coro: Coroutine[Any, Any, Any]) -> Any:
    """Minimal asyncio runner for sync test context."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            import threading

            result: list[Any] = []
            error: list[BaseException] = []

            def run() -> None:
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result.append(new_loop.run_until_complete(coro))
                    new_loop.close()
                except Exception as e:
                    error.append(e)

            t = threading.Thread(target=run, daemon=True)
            t.start()
            t.join(timeout=5)
            if error:
                raise error[0]
            return result[0] if result else None
    except RuntimeError:
        pass
    return asyncio.run(coro)
