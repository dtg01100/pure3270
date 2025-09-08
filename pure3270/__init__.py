"""Pure3270 library: Pure Python 3270 terminal emulator and p3270 integration."""

from .session import Session, setup_logging
from .patching.patching import enable_replacement

# Initialize logging by default
setup_logging()

__version__ = "0.1.0b1"

__all__ = [
    "Session",
    "enable_replacement",
    "setup_logging",
    "Pure3270Error",
    "SessionError",
    "ProtocolError",
    "NegotiationError",
    "ParseError",
    "Pure3270PatchError",
]
