"""Small parser utilities extracted from utils.py for clearer typing and reuse.

This module provides ParseError and BaseParser used by data stream parsers.
"""

import struct
from typing import Optional


class ParseError(Exception):
    """Error during parsing."""


class BaseParser:
    def __init__(self, data: bytes) -> None:
        self._data: bytes = data
        self._pos: int = 0

    def has_more(self) -> bool:
        return self._pos < len(self._data)

    def remaining(self) -> int:
        return len(self._data) - self._pos

    def peek_byte(self) -> int:
        if not self.has_more():
            raise ParseError("Peek at EOF")
        return self._data[self._pos]

    def read_byte(self) -> int:
        if not self.has_more():
            raise ParseError("Unexpected end of data stream")
        byte = self._data[self._pos]
        self._pos += 1
        return byte

    def read_u16(self) -> int:
        # Read two bytes big-endian
        high = self.read_byte()
        low = self.read_byte()
        result = struct.unpack(">H", bytes([high, low]))[0]
        return int(result)

    def read_fixed(self, length: int) -> bytes:
        if self.remaining() < length:
            raise ParseError("Insufficient data for fixed length read")
        start = self._pos
        self._pos += length
        return self._data[start : self._pos]

    def seek(self, pos: int) -> None:
        """Set the current read position within the buffer.

        Allows caller to rewind or advance the internal cursor for
        multi-pass parsing algorithms.
        """
        if pos < 0 or pos > len(self._data):
            raise ParseError("Seek position out of range")
        self._pos = int(pos)
