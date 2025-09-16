"""Common base class for buffer writers in pure3270 emulation."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple


class BufferWriter(ABC):
    """
    Abstract base class consolidating write operations, cursor management,
    and content retrieval for screen, printer, and session buffers.
    """

    def __init__(self):
        self.cursor_row = 0
        self.cursor_col = 0

    def set_position(self, row: int, col: int) -> None:
        """Set cursor position."""
        self.cursor_row = row
        self.cursor_col = col

    def get_position(self) -> Tuple[int, int]:
        """Get current cursor position."""
        return (self.cursor_row, self.cursor_col)

    @abstractmethod
    def write_char(
        self,
        ebcdic_byte: int,
        row: Optional[int] = None,
        col: Optional[int] = None,
        protected: bool = False,
        circumvent_protection: bool = False,
    ) -> None:
        """
        Write an EBCDIC character to the buffer at specified or current position.
        Handles insertion, protection checks, and overflow where applicable.
        """
        if row is None or col is None:
            row, col = self.get_position()
        raise NotImplementedError("Subclasses must implement write_char")

    @abstractmethod
    def set_attribute(
        self,
        attr: int,
        row: Optional[int] = None,
        col: Optional[int] = None,
    ) -> None:
        """
        Set attribute (e.g., protection, intensity) at specified or current position.
        """
        if row is None or col is None:
            row, col = self.get_position()
        raise NotImplementedError("Subclasses must implement set_attribute")

    @abstractmethod
    def get_content(self) -> str:
        """Retrieve the buffer content as a string."""
        raise NotImplementedError("Subclasses must implement get_content")
