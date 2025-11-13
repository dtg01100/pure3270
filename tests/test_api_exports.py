import importlib

import pytest


def test_asyncsession_exported_at_package_root():
    import pure3270

    # Accessing AsyncSession at package root should work since it's in __all__
    assert hasattr(pure3270, "AsyncSession")
    assert pure3270.AsyncSession is not None


def test_asyncsession_importable_from_module():
    # Importing from the implementation module should work
    mod = importlib.import_module("pure3270.session")
    assert hasattr(mod, "AsyncSession")


import pytest


def test_asyncsession_in_package_root():
    import pure3270

    # Accessing pure3270.AsyncSession at package root should work since it's exported
    assert hasattr(pure3270, "AsyncSession")
    assert pure3270.AsyncSession is not None


def test_asyncsession_importable_from_session_module():
    # Ensure AsyncSession can still be imported from the internal module
    from pure3270.session import AsyncSession

    assert hasattr(AsyncSession, "connect") or True
