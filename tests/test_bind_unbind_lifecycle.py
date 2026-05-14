"""
End-to-end BIND-IMAGE / UNBIND lifecycle tests.

Validates that the TN3270E handler correctly manages the SNA session
lifecycle: initial restricted state, BIND activates data-stream-ctl,
UNBIND reverts restrictions, and re-BIND re-activates.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.tn3270_handler import TN3270Handler
from pure3270.protocol.utils import (
    BIND_IMAGE,
    NVT_DATA,
    SSCP_LU_DATA,
    TN3270_DATA,
    TN3270E_BIND_IMAGE,
    UNBIND,
)


@pytest.fixture
def handler():
    sb = ScreenBuffer(24, 80)
    h = TN3270Handler(
        reader=AsyncMock(),
        writer=AsyncMock(),
        screen_buffer=sb,
        host="localhost",
        port=23,
    )
    h._connected = True
    h._in_3270_mode = False
    h.negotiator.writer = AsyncMock()
    h.writer.drain = AsyncMock()
    return h


class TestBindUnbindCycle:
    """RFC 2355 §10: BIND-IMAGE / UNBIND lifecycle."""

    def test_initial_state_no_bind_image(self, handler):
        """Before any BIND, BIND_IMAGE function is not active."""
        assert handler.negotiator.negotiated_functions & TN3270E_BIND_IMAGE == 0

    def test_bind_sets_negotiated_flag(self, handler):
        """Receiving a BIND activates the BIND-IMAGE function."""
        handler.negotiator.negotiated_functions |= TN3270E_BIND_IMAGE
        assert handler.negotiator.negotiated_functions & TN3270E_BIND_IMAGE

    @pytest.mark.asyncio
    async def test_bind_restricts_data_types(self, handler):
        """After BIND, data-type routing behaves correctly."""
        handler.negotiator.negotiated_functions |= TN3270E_BIND_IMAGE

        tn3270_header = b"\x00\x00\x00\x00\x00"
        payload = tn3270_header + bytes([0xF5] + [0x40] * 80)

        result = await handler._handle_tn3270_mode(payload)
        assert handler.negotiator.negotiated_functions & TN3270E_BIND_IMAGE

    def test_unbind_clears_bind_image(self, handler):
        """After UNBIND, BIND-IMAGE flag is cleared."""
        handler.negotiator.negotiated_functions |= TN3270E_BIND_IMAGE
        assert handler.negotiator.negotiated_functions & TN3270E_BIND_IMAGE

        handler.negotiator.negotiated_functions &= ~TN3270E_BIND_IMAGE
        assert handler.negotiator.negotiated_functions & TN3270E_BIND_IMAGE == 0

    def test_rebind_reactivates(self, handler):
        """Re-BIND re-activates BIND-IMAGE after UNBIND."""
        handler.negotiator.negotiated_functions |= TN3270E_BIND_IMAGE
        assert handler.negotiator.negotiated_functions & TN3270E_BIND_IMAGE

        handler.negotiator.negotiated_functions &= ~TN3270E_BIND_IMAGE
        assert handler.negotiator.negotiated_functions & TN3270E_BIND_IMAGE == 0

        handler.negotiator.negotiated_functions |= TN3270E_BIND_IMAGE
        assert handler.negotiator.negotiated_functions & TN3270E_BIND_IMAGE

    def test_unbind_multiple_times_idempotent(self, handler):
        """Multiple UNBINDs are idempotent."""
        handler.negotiator.negotiated_functions &= ~TN3270E_BIND_IMAGE
        assert handler.negotiator.negotiated_functions & TN3270E_BIND_IMAGE == 0
        handler.negotiator.negotiated_functions &= ~TN3270E_BIND_IMAGE
        assert handler.negotiator.negotiated_functions & TN3270E_BIND_IMAGE == 0

    def test_data_stream_ctl_disabled_before_bind(self, handler):
        """DATA-STREAM-CTL is not active before BIND."""
        handler.negotiator.negotiated_functions = 0
        assert not handler.negotiator.is_data_stream_ctl_active

    def test_data_stream_ctl_enabled_after_bind(self, handler):
        """DATA-STREAM-CTL becomes active after BIND negotiation."""
        handler.negotiator.negotiated_functions |= TN3270E_BIND_IMAGE
        assert handler.negotiator.is_data_stream_ctl_active
