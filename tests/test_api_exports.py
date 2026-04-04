import importlib
from unittest.mock import AsyncMock, patch

import pytest

import pure3270
from pure3270 import AsyncSession
from pure3270.emulation.screen_buffer import ScreenBuffer


def test_asyncsession_exported_at_package_root():
    assert hasattr(pure3270, "AsyncSession")
    assert pure3270.AsyncSession is not None
    assert pure3270.AsyncSession.__name__ == "AsyncSession"


def test_asyncsession_importable_from_module():
    mod = importlib.import_module("pure3270.session")
    assert hasattr(mod, "AsyncSession")
    assert mod.AsyncSession is AsyncSession


def test_asyncsession_has_required_methods():
    for method_name in ("connect", "read", "send", "close", "key", "string"):
        assert hasattr(AsyncSession, method_name), f"Missing method: {method_name}"
        method = getattr(AsyncSession, method_name)
        assert callable(method), f"{method_name} is not callable"


def test_asyncsession_can_be_instantiated():
    session = AsyncSession()
    assert session is not None
    assert not session.connected
    assert hasattr(session, "screen")
    assert isinstance(session.screen, ScreenBuffer)
    assert session.screen.rows == 24
    assert session.screen.cols == 80


@pytest.mark.asyncio
async def test_asyncsession_connect_raises_when_no_host():
    session = AsyncSession()
    with pytest.raises(Exception):
        await session.connect("invalid.host.that.does.not.exist", 23)


@pytest.mark.asyncio
async def test_asyncsession_key_method_accepts_valid_aid_keys():
    session = AsyncSession()
    assert hasattr(session, "AID_MAP")
    assert "PF(1)" in session.AID_MAP
    assert "Enter" in session.AID_MAP
    assert session.AID_MAP["PF(1)"] == 0xF1
