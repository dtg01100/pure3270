"""Test all mock server scenarios."""

import asyncio
import socket
import pytest
from mock_server.scenarios import SCENARIOS
from mock_server import TN3270MockServer


@pytest.mark.parametrize("scenario_name", list(SCENARIOS.keys()))
@pytest.mark.timeout(10)
def test_scenario_negotiates(scenario_name):
    """Verify each scenario starts and accepts connections."""
    server_class = SCENARIOS[scenario_name]
    server = server_class()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.start())

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((server.host, server.port))
        data = s.recv(1024)
        assert data is not None
        s.close()
    finally:
        loop.run_until_complete(server.stop())
        loop.close()