"""
Centralized error handling utilities for protocol operations.

Provides decorators, context managers, and functions to handle common
socket/SSL/protocol errors, reducing duplication in negotiator.py,
tn3270_handler.py, and ssl_wrapper.py.
"""

import asyncio
import functools
import logging
import ssl
from typing import Any, Callable, Dict, Optional, TypeVar

from .exceptions import NegotiationError, ProtocolError

logger = logging.getLogger(__name__)

# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])


def handle_drain(func: F) -> F:
    """
    Decorator to handle exceptions during writer.drain() calls.

    Wraps the function and adds a try-except around the final drain,
    logging warnings on failure without raising (to preserve behavior).
    Assumes the function is async and ends with await writer.drain().
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = await func(*args, **kwargs)
        # Assume last operation is drain; catch and log
        try:
            if hasattr(args[0], "writer") and args[0].writer is not None:
                await args[0].writer.drain()
        except Exception as e:
            logger.warning(f"Failed to drain writer in {func.__name__}: {e}")
        return result

    return wrapper  # type: ignore[return-value]


class safe_socket_operation:
    """
    Async context manager for safe socket/SSL operations.

    Catches OSError, ssl.SSLError, asyncio.TimeoutError; logs and raises
    ProtocolError with original message. Use for connect, read/write ops.
    """

    def __enter__(self) -> "safe_socket_operation":
        return self

    async def __aenter__(self) -> "safe_socket_operation":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type in (OSError, ssl.SSLError, asyncio.TimeoutError):
            logger.error(f"Socket/SSL operation failed: {exc_val}", exc_info=True)
            raise ProtocolError(f"Protocol operation failed: {exc_val}")
        return None

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type in (OSError, ssl.SSLError, asyncio.TimeoutError):
            logger.error(f"Socket/SSL operation failed: {exc_val}", exc_info=True)
            raise ProtocolError(f"Protocol operation failed: {exc_val}")
        return None


def raise_protocol_error(message: str, exc: Optional[Exception] = None) -> None:
    """Raise a ProtocolError with optional wrapped exception."""
    if exc:
        logger.error(f"{message}: {exc}", exc_info=True)
        raise ProtocolError(message) from exc
    else:
        logger.error(message)
        raise ProtocolError(message)


def raise_negotiation_error(
    message: str,
    exc: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Raise a NegotiationError with optional wrapped exception and context."""
    if context:
        if exc:
            logger.error(
                f"Negotiation failed: {message}: {exc} (Context: {context})",
                exc_info=True,
            )
            raise NegotiationError(f"{message}: {exc}", context=context) from exc
        else:
            logger.error(f"Negotiation failed: {message} (Context: {context})")
            raise NegotiationError(message, context=context)
    else:
        if exc:
            logger.error(f"Negotiation failed: {message}: {exc}", exc_info=True)
            raise NegotiationError(f"{message}: {exc}") from exc
        else:
            logger.error(f"Negotiation failed: {message}")
            raise NegotiationError(message)
