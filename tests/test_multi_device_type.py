import asyncio
import shutil
import time

import pytest

from mock_server.tn3270_mock_server import EnhancedTN3270MockServer
from pure3270 import Session


@pytest.mark.timeout(8)
@pytest.mark.parametrize(
    "requested", ["IBM-3279-2-E", "IBM-3278-2-E"]
)  # exercise alt & default
def test_requested_device_type_negotiation(requested):
    server = EnhancedTN3270MockServer(requested_device_type=requested)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.start())
    try:
        s = Session()
        s.open(server.host, server.port)
        # wait for tn3270e mode
        deadline = time.time() + 5
        while time.time() < deadline and not s.tn3270e_mode:
            time.sleep(0.05)
        assert s.tn3270e_mode, "TN3270E mode not established"
        # Access negotiator via async session handler fallback
        handler = getattr(s, "_handler", None)
        if handler is None:
            async_session = getattr(s, "_async_session", None)
            handler = getattr(async_session, "_handler", None)
        negotiator = getattr(handler, "negotiator", None)
        negotiated_device = getattr(negotiator, "negotiated_device_type", None)
        supported = getattr(negotiator, "supported_device_types", [])
        assert negotiated_device is not None, "No device type negotiated"
        if requested:
            # If server requested a specific device type, negotiator should select that
            assert (
                negotiated_device == requested
            ), f"Negotiated device {negotiated_device} != requested {requested}"
        else:
            assert (
                negotiated_device in supported
            ), f"Negotiated device type {negotiated_device} not in supported list"
        s.close()
    finally:
        loop.run_until_complete(server.stop())
        loop.close()
