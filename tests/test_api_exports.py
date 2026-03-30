import importlib
from unittest.mock import AsyncMock, patch

import pytest

import pure3270
from pure3270 import AsyncSession


def test_asyncsession_exported_at_package_root():
    assert hasattr(pure3270, "AsyncSession")
    assert pure3270.AsyncSession is not None


def test_asyncsession_importable_from_module():
    mod = importlib.import_module("pure3270.session")
    assert hasattr(mod, "AsyncSession")


def test_asyncsession_has_required_methods():
    assert hasattr(AsyncSession, "connect")
    assert hasattr(AsyncSession, "read")
    assert hasattr(AsyncSession, "send")
    assert hasattr(AsyncSession, "close")


def test_asyncsession_can_be_instantiated():
    session = AsyncSession()
    assert session is not None
    assert not session.connected


@pytest.mark.asyncio
async def test_asyncsession_connect_raises_when_no_host():
    session = AsyncSession()
    with pytest.raises(Exception):
        await session.connect("invalid.host.that.does.not.exist", 23)
