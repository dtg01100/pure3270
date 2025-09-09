"""Exceptions for protocol handling."""


class NegotiationError(Exception):
    """Raised on negotiation failure."""

    pass


class ProtocolError(Exception):
    """Raised on protocol errors."""

    pass


class ParseError(Exception):
    """Raised on parsing errors."""

    pass
