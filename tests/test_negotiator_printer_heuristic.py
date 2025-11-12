import pytest

from pure3270.protocol.negotiator import Negotiator
from pure3270.protocol.utils import TTYPE_SEND


class DummyHandler:
    def __init__(self):
        self.printer_buffer = object()


class DummyWriter:
    async def drain(self):
        return


@pytest.mark.asyncio
async def test_ttype_reply_printer_via_handler(monkeypatch):
    capture = {}
    # Provide a writer with drain so negotiator attempts to send without error
    negotiator = Negotiator(
        writer=DummyWriter(),
        parser=None,
        screen_buffer=None,
        handler=DummyHandler(),
        is_printer_session=False,
        terminal_type="IBM-3278-4",
    )

    def fake_send(option, payload, writer=None):
        capture["payload"] = payload

    negotiator._send_subneg = fake_send
    await negotiator._handle_terminal_type_subnegotiation(bytes([TTYPE_SEND]))
    assert b"IBM-3287-1" in capture.get("payload", b"")


@pytest.mark.asyncio
async def test_ttype_reply_printer_via_terminal_type(monkeypatch):
    capture = {}
    # Create negotiator with valid terminal_type then override to simulate a 3287 model
    negotiator = Negotiator(
        writer=DummyWriter(),
        parser=None,
        screen_buffer=None,
        handler=None,
        is_printer_session=False,
        terminal_type="IBM-3278-4",
    )

    # Force terminal_type to a 3287 model to exercise the heuristic
    negotiator.terminal_type = "IBM-3287-2"

    def fake_send(option, payload, writer=None):
        capture["payload"] = payload

    negotiator._send_subneg = fake_send
    await negotiator._handle_terminal_type_subnegotiation(bytes([TTYPE_SEND]))
    assert b"IBM-3287-1" in capture.get("payload", b"")
