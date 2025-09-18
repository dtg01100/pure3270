"""Enhanced exceptions for pure3270 with contextual information."""

from typing import Any, Dict, Optional


class Pure3270Error(Exception):
    """Base error for pure3270 with contextual information."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        Initialize a pure3270 error.

        Args:
            message: Error message
            context: Optional context information (host, port, operation, stream_pos, order_byte, trace, etc.)
            original_exception: Original exception that caused this error
        """
        super().__init__(message)
        self.context = context or {}
        self.original_exception = original_exception

    def __str__(self) -> str:
        """Get string representation with context."""
        base_msg = super().__str__()
        if self.context:
            context_items = []
            for key, value in self.context.items():
                if isinstance(value, str) and len(value) > 50:
                    # Truncate long values
                    value = value[:47] + "..."
                context_items.append(f"{key}={value}")
            context_str = ", ".join(context_items)
            return f"{base_msg} (Context: {context_str})"
        return base_msg

    def __repr__(self) -> str:
        """Get repr with context details."""
        base_repr = super().__repr__()
        if self.context:
            context_repr = repr(self.context)
            return f"{base_repr} (context={context_repr})"
        return base_repr

    def add_context(self, key: str, value: Any) -> None:
        """
        Add context information to the exception.

        Args:
            key: Context key
            value: Context value
        """
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get context information from the exception.

        Args:
            key: Context key
            default: Default value if key not found

        Returns:
            Context value or default
        """
        return self.context.get(key, default)


class ConnectionError(Pure3270Error):
    """Connection error with connection-specific context."""

    pass


class NegotiationError(Pure3270Error):
    """Negotiation error with protocol-specific context."""

    pass


# MacroError removed along with macro DSL support


class ParseError(Pure3270Error):
    """Parsing error with data-specific context."""

    pass


class ProtocolError(Pure3270Error):
    """Protocol error with protocol-specific context."""

    pass


class TimeoutError(Pure3270Error):
    """Timeout error with operation-specific context."""

    pass


class NotConnectedError(Pure3270Error):
    """Error raised when operation is attempted on a not connected session."""

    pass


class EnhancedSessionError(Pure3270Error):
    """Enhanced session error with session-specific context."""

    pass
