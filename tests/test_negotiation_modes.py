import asyncio

import pytest

from pure3270.protocol.negotiator import Negotiator


class _MockWriter:
    def write(self, data: bytes) -> None:
        return None

    async def drain(self) -> None:
        return None


@pytest.mark.asyncio
async def test_negotiation_strict_mode_requires_both_events():
    writer = _MockWriter()
    negotiator = Negotiator(
        writer, None, None, None, force_mode=None, negotiation_mode="strict"
    )
    negotiator._configure_x3270_timing_profile("ultra_fast")

    # Run negotiation in background
    task = asyncio.create_task(negotiator._negotiate_tn3270(timeout=1.0))

    # Allow a bit of time for negotiation to start
    await asyncio.sleep(0.02)

    # Set only functions event; strict mode should not finalize
    negotiator._signal_functions_event(on_send=True)
    await asyncio.sleep(0.02)
    assert not negotiator._get_or_create_negotiation_complete().is_set()

    # Now set device event, negotiation should complete
    negotiator._signal_device_event(on_send=True)
    await asyncio.wait_for(task, timeout=1.0)

    assert negotiator.negotiated_tn3270e is True
    assert negotiator._get_or_create_negotiation_complete().is_set()


@pytest.mark.asyncio
async def test_negotiation_flexible_mode_accepts_either_event():
    writer = _MockWriter()
    negotiator = Negotiator(
        writer, None, None, None, force_mode=None, negotiation_mode="flexible"
    )
    negotiator._configure_x3270_timing_profile("ultra_fast")

    task = asyncio.create_task(negotiator._negotiate_tn3270(timeout=1.0))
    await asyncio.sleep(0.02)

    # Signal only functions event; flexible mode should finalize
    negotiator._signal_functions_event(on_send=True)
    await asyncio.wait_for(task, timeout=1.0)

    assert negotiator.negotiated_tn3270e is True
    assert negotiator._get_or_create_negotiation_complete().is_set()
