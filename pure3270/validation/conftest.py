"""Shared fixtures for validation tests."""

from collections.abc import Generator

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer


@pytest.fixture
def screen_buffer() -> Generator[ScreenBuffer, None, None]:
    yield ScreenBuffer(rows=24, cols=80)
