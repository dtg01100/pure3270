"""Scenario registry for mock TN3270 servers."""

from typing import Type

from mock_server.scenarios.echo import EchoServer
from mock_server.scenarios.menu_3270 import Menu3270Server
from mock_server.scenarios.menu_nvt import MenuNVTServer
from mock_server.scenarios.menu_tn3270e import MenuTN3270EServer
from mock_server.scenarios.negotiation_failure import NegotiationFailureServer
from mock_server.tn3270_mock_server import TN3270MockServer

SCENARIOS: dict[str, Type[TN3270MockServer]] = {
    "echo": EchoServer,
    "menu_3270": Menu3270Server,
    "menu_nvt": MenuNVTServer,
    "negotiation_failure": NegotiationFailureServer,
    "menu_tn3270e": MenuTN3270EServer,
    "enhanced": MenuTN3270EServer,
}
