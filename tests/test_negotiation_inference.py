import pytest

from pure3270.protocol.negotiator import Negotiator


class DummyReader:
    async def read(self, n):
        return b""


class DummyWriter:
    def write(self, data):
        pass

    async def drain(self):
        pass


@pytest.mark.parametrize(
    "trace,expected",
    [
        (b"", False),  # Empty trace
        (b"\xff\xfb\x19", True),  # IAC WILL EOR only
        (b"\xff\xfc\x24", False),  # IAC WONT TN3270E only
        (b"\xff\xfb\x19\xff\xfc\x24", False),  # Both present -> refusal wins
    ],
)
def test_infer_tn3270e_from_trace(trace, expected):
    # Create a minimal negotiator (screen_buffer not needed for inference)
    negotiator = Negotiator(None, None, screen_buffer=type("SB", (), {})())  # type: ignore[arg-type]
    result = negotiator.infer_tn3270e_from_trace(trace)
    assert result is expected
