"""Minimal patching stub to satisfy tests.

The test suite sometimes patches pure3270.patching.enable_replacement; provide a
no-op implementation here to avoid AttributeError during tests that import it.
"""

from __future__ import annotations

from typing import Any


def enable_replacement() -> None:  # pragma: no cover - trivial stub
    """No-op replacement enabler for compatibility with p3270 patching tests.

    Real patching is out of scope for these unit tests; this function simply
    exists so unittest.mock.patch can reference it without raising errors.
    """
    return None
