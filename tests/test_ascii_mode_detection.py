import asyncio

import pytest

from pure3270.protocol.tn3270_handler import TN3270Handler


@pytest.mark.asyncio
async def test_ascii_detection_sets_negotiator_flag():
    """VT100 sequences should trigger negotiator.set_ascii_mode via receive_data path."""
    vt100_payload = b"\x1b[2JHello, VT100!\n"

    class OneShotReader:
        def __init__(self, data: bytes):
            self._data = data
            self._done = False

        async def read(self, n: int = 4096) -> bytes:  # pragma: no cover - helper
            if not self._done:
                self._done = True
                return self._data
            return b""

        async def readexactly(self, n: int) -> bytes:  # pragma: no cover - helper
            return await self.read(n)

        def at_eof(self) -> bool:  # pragma: no cover - helper
            return self._done

    reader = OneShotReader(vt100_payload)
    handler = TN3270Handler(reader=reader, writer=None)

    # Sanity: starts not in ASCII
    assert getattr(handler.negotiator, "_ascii_mode", False) is False

    # Exercise full receive path which performs detection and sets negotiator flag
    received = await handler.receive_data(timeout=0.2)
    assert received == vt100_payload.rstrip(b"\x19")  # cleaned of any EOR if present

    # After detection, negotiator and handler should reflect ASCII mode
    assert getattr(handler.negotiator, "_ascii_mode", False) is True
    assert handler._ascii_mode is True

    # Idempotent explicit API call
    handler.set_ascii_mode()
    assert handler._ascii_mode is True


@pytest.mark.asyncio
async def test_ascii_api_sets_flags_and_propagates():
    """Direct API call should set flags on both negotiator and handler consistently."""
    handler = TN3270Handler(reader=None, writer=None)
    assert getattr(handler.negotiator, "_ascii_mode", False) is False
    assert handler._ascii_mode is False

    handler.set_ascii_mode()

    assert getattr(handler.negotiator, "_ascii_mode", False) is True
    assert handler._ascii_mode is True
