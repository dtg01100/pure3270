import pytest

from pure3270.protocol.tn3270_handler import TN3270Handler


@pytest.mark.asyncio
async def test_negotiator_set_propagates_to_handler():
    handler = TN3270Handler(None, None, None)
    # Initially unset
    assert handler.negotiator.negotiated_tn3270e is False
    assert handler.negotiated_tn3270e is False

    # Set via negotiator
    handler.negotiator.set_negotiated_tn3270e(True)
    assert handler.negotiator.negotiated_tn3270e is True
    assert handler.negotiated_tn3270e is True

    # Unset via negotiator
    handler.negotiator.set_negotiated_tn3270e(False)
    assert handler.negotiator.negotiated_tn3270e is False
    assert handler.negotiated_tn3270e is False


@pytest.mark.asyncio
async def test_handler_set_propagates_to_negotiator():
    handler = TN3270Handler(None, None, None)
    # Initially unset
    assert handler.negotiator.negotiated_tn3270e is False
    assert handler.negotiated_tn3270e is False

    # Set via handler
    handler.set_negotiated_tn3270e(True)
    assert handler.negotiator.negotiated_tn3270e is True
    assert handler.negotiated_tn3270e is True

    # Unset via handler
    handler.set_negotiated_tn3270e(False)
    assert handler.negotiator.negotiated_tn3270e is False
    assert handler.negotiated_tn3270e is False
