"""Scenario registry for mock TN3270 servers."""

from typing import Type

from mock_server.tn3270_mock_server import TN3270MockServer

SCENARIOS: dict[str, Type[TN3270MockServer]] = {}
