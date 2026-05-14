"""Shared fixtures for validation suite."""

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer


@pytest.fixture
def screen_buffer() -> ScreenBuffer:
    return ScreenBuffer(rows=24, cols=80)
