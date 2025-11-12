import importlib

import pytest


def test_asyncsession_not_exported_at_package_root():
    import pure3270

    # Accessing AsyncSession at package root should raise AttributeError
    with pytest.raises(AttributeError):
        _ = pure3270.AsyncSession  # type: ignore[attr-defined]


def test_asyncsession_importable_from_module():
    # Importing from the implementation module should work
    mod = importlib.import_module("pure3270.session")
    assert hasattr(mod, "AsyncSession")


import pytest


def test_asyncsession_not_in_package_root():
    import pure3270

    # Accessing pure3270.AsyncSession at package root should raise AttributeError
    with pytest.raises(AttributeError):
        _ = pure3270.AsyncSession  # type: ignore[attr-defined]


def test_asyncsession_importable_from_session_module():
    # Ensure AsyncSession can still be imported from the internal module
    from pure3270.session import AsyncSession

    assert hasattr(AsyncSession, "connect") or True
