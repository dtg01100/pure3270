"""Exceptions for protocol handling."""

from ..exceptions import (MacroError, NegotiationError, NotConnectedError,
                          ParseError, ProtocolError)

__all__ = [
    "NegotiationError",
    "ProtocolError",
    "ParseError",
    "MacroError",
    "NotConnectedError",
]
