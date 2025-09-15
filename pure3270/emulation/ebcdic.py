"""
EBCDIC to ASCII translation utilities for 3270 emulation.
Based on IBM Code Page 037.
"""

import logging
from typing import Dict, Any
import codecs
import ebcdic

logger = logging.getLogger(__name__)



class EmulationEncoder:
    """Utility class for EBCDIC encoding/decoding in 3270 emulation."""

    @staticmethod
    def decode(data: bytes) -> str:
        """
        Decode EBCDIC bytes to ASCII string.
        
        Args:
            data: EBCDIC encoded bytes.
            
        Returns:
            ASCII string (unmapped chars default to space).
        """
        return ebcdic.decode('cp037', data)

    @staticmethod
    def encode(text: str) -> bytes:
        """
        Encode ASCII string to EBCDIC bytes.
        
        Args:
            text: ASCII string.
            
        Returns:
            EBCDIC bytes (unmapped chars default to space 0x40).
        """
        return ebcdic.encode('cp037', text)


def get_p3270_version():
    """Get p3270 version for patching.
    
    Returns the actual version of the installed p3270 package,
    or None if it cannot be determined.
    """
    try:
        import importlib.metadata

        return importlib.metadata.version("p3270")
    except (ImportError, Exception):
        # Fallback for older Python versions or if metadata is not available
        try:
            import p3270

            return getattr(p3270, "__version__", None)
        except ImportError:
            return None


def encode_field_attribute(attr: int) -> int:
    """
    Encode 3270 field attribute to EBCDIC.

    Args:
        attr: Attribute code (e.g., 0xF1 for unprotected).

    Returns:
        EBCDIC encoded attribute.
    """
    return attr  # In this implementation, attributes are direct; extend for specifics


