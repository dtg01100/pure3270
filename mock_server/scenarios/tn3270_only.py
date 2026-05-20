"""TN3270-only server - refuses TN3270E, forces non-E negotiation."""

import asyncio

from mock_server.scenarios.menu_3270 import Menu3270Server
from mock_server.tn3270_mock_server import TN3270MockServer


class TN3270OnlyServer(Menu3270Server):
    """Server that only supports TN3270, not TN3270E.

    This server explicitly does NOT offer WILL TN3270E,
    testing the client's fallback behavior.
    """

    pass
