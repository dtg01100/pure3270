"""
pure3270 package init.
Exports core classes and functions for 3270 terminal emulation.
"""

import logging
from .session import Session, AsyncSession
from .patching import enable_replacement

def setup_logging(level='INFO'):
    """
    Setup basic logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(level=getattr(logging, level.upper()))

__all__ = [
    'Session',
    'AsyncSession',
    'enable_replacement',
    'setup_logging'
]
