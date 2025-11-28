import asyncio
from typing import Any, cast

from pure3270.protocol.negotiator import Negotiator


class HandlerStub:
    def __init__(self):
        self._negotiated_tn3270e = False
        # Expose property expected by tests

    @property
    def negotiated_tn3270e(self) -> bool:
        return getattr(self, "_negotiated_tn3270e", False)

    def set_negotiated_tn3270e(self, value: bool, propagate: bool = True) -> None:
        self._negotiated_tn3270e = bool(value)


def test_signal_device_and_functions_finalizes_negotiation():
    handler = HandlerStub()
    negotiator = Negotiator(
        writer=None, parser=None, screen_buffer=None, handler=handler
    )

    # Initially not negotiated and no server support
    assert not negotiator._server_supports_tn3270e
    assert not negotiator._get_or_create_device_type_event().is_set()
    assert not negotiator._get_or_create_functions_event().is_set()
    assert not negotiator._get_or_create_negotiation_complete().is_set()

    # Signal device event as a send; should mark server support
    negotiator._signal_device_event(on_send=True)
    assert negotiator._get_or_create_device_type_event().is_set()
    assert negotiator._server_supports_tn3270e is True
    assert not negotiator._get_or_create_negotiation_complete().is_set()

    # Signal functions event as a send; should finalize negotiation
    negotiator._signal_functions_event(on_send=True)
    assert negotiator._get_or_create_functions_event().is_set()
    assert negotiator._get_or_create_negotiation_complete().is_set()
    assert negotiator.negotiated_tn3270e
    assert handler.negotiated_tn3270e


def test_force_negotiated_event_sets_flags_and_handler():
    handler = HandlerStub()
    negotiator = Negotiator(
        writer=None, parser=None, screen_buffer=None, handler=handler
    )

    # Force negotiated via functions event even if device not set
    negotiator._signal_functions_event(force_negotiated=True)
    assert negotiator.negotiated_tn3270e is True
    assert handler.negotiated_tn3270e is True

    negotiator._signal_negotiation_complete(success=False)
    # Negotiation complete event must be set and negotiated flag cleared
    assert negotiator._get_or_create_negotiation_complete().is_set()
    assert negotiator.negotiated_tn3270e is False
    assert handler.negotiated_tn3270e is False


def test_set_negotiated_flag_propagates_to_handler():
    handler = HandlerStub()
    negotiator = Negotiator(
        writer=None, parser=None, screen_buffer=None, handler=handler
    )

    # Verify initial state
    assert negotiator.negotiated_tn3270e is False
    assert handler.negotiated_tn3270e is False

    # Set negotiated via public API and verify propagation
    negotiator.set_negotiated_tn3270e(True)
    assert negotiator.negotiated_tn3270e is True
    assert handler.negotiated_tn3270e is True

    # Unset via public API and verify propagation
    negotiator.set_negotiated_tn3270e(False)
    assert negotiator.negotiated_tn3270e is False
    assert handler.negotiated_tn3270e is False
