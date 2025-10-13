# ATTRIBUTION NOTICE
# =================================================================================
# This module contains code ported from or inspired by: IBM s3270/x3270
# Source: https://github.com/rhacker/x3270
# Licensed under BSD-3-Clause
#
# DESCRIPTION
# --------------------
# Extended position class with 14-bit addressing support for large screen emulation
#
# COMPATIBILITY
# --------------------
# Compatible with TN3270E extended addressing and large screen formats
#
# MODIFICATIONS
# --------------------
# Extended to support 14-bit addressing with coordinate conversion utilities
#
# INTEGRATION POINTS
# --------------------
# - Screen buffer position management
# - Field positioning and addressing
# - Cursor positioning with extended coordinates
#
# ATTRIBUTION REQUIREMENTS
# ------------------------------
# This attribution must be maintained when this code is modified or
# redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
# Last updated: 2025-10-13
# =================================================================================

"""Extended position class with 14-bit addressing support for large screen emulation."""

import logging
from typing import Optional, Tuple, Union

from .addressing import AddressCalculator, AddressingMode

logger = logging.getLogger(__name__)


class ExtendedPosition:
    """
    Represents a position in a 3270 screen buffer with support for extended 14-bit addressing.

    This class provides coordinate-based positioning with automatic conversion to/from
    linear addresses, supporting both traditional 12-bit and extended 14-bit addressing modes.
    """

    def __init__(
        self,
        row: int = 0,
        col: int = 0,
        cols: int = 80,
        addressing_mode: AddressingMode = AddressingMode.MODE_12_BIT,
    ) -> None:
        """
        Initialize an ExtendedPosition.

        Args:
            row: Row coordinate (0-based)
            col: Column coordinate (0-based)
            cols: Number of columns in the screen (default 80)
            addressing_mode: Addressing mode for validation and conversion

        Raises:
            ValueError: If coordinates are invalid for the addressing mode
        """
        self._row = int(row)
        self._col = int(col)
        self._cols = int(cols)
        self._addressing_mode = addressing_mode

        # Validate coordinates
        self._validate_coordinates()

    def _validate_coordinates(self) -> None:
        """Validate that coordinates are within valid ranges for the addressing mode."""
        if self._row < 0 or self._col < 0:
            raise ValueError(
                f"Coordinates must be non-negative: row={self._row}, col={self._col}"
            )

        if self._cols <= 0:
            raise ValueError(f"Columns must be positive: {self._cols}")

        # Check if the linear address would exceed mode limits
        address = self._row * self._cols + self._col
        if not AddressCalculator.validate_address(address, self._addressing_mode):
            max_positions = AddressCalculator.get_max_positions(self._addressing_mode)
            raise ValueError(
                f"Position ({self._row}, {self._col}) with {self._cols} columns "
                f"exceeds {self._addressing_mode.value} addressing limits "
                f"(address {address} >= {max_positions})"
            )

    @property
    def row(self) -> int:
        """Get the row coordinate."""
        return self._row

    @property
    def col(self) -> int:
        """Get the column coordinate."""
        return self._col

    @property
    def cols(self) -> int:
        """Get the number of columns."""
        return self._cols

    @property
    def addressing_mode(self) -> AddressingMode:
        """Get the addressing mode."""
        return self._addressing_mode

    @property
    def linear_address(self) -> int:
        """Get the linear address for this position."""
        address = AddressCalculator.coords_to_address(
            self._row, self._col, self._cols, self._addressing_mode
        )
        return address if address is not None else 0

    @property
    def coordinates(self) -> Tuple[int, int]:
        """Get the (row, col) coordinates as a tuple."""
        return (self._row, self._col)

    def set_coordinates(self, row: int, col: int) -> None:
        """
        Set new coordinates for this position.

        Args:
            row: New row coordinate
            col: New column coordinate

        Raises:
            ValueError: If new coordinates are invalid
        """
        self._row = int(row)
        self._col = int(col)
        self._validate_coordinates()

    def set_from_address(self, address: int) -> None:
        """
        Set coordinates from a linear address.

        Args:
            address: Linear address to convert from

        Raises:
            ValueError: If address is invalid for the addressing mode
        """
        coords = AddressCalculator.address_to_coords(
            address, self._cols, self._addressing_mode
        )
        if coords is None:
            raise ValueError(
                f"Invalid address {address} for {self._addressing_mode.value} mode"
            )
        self._row, self._col = coords

    def convert_addressing_mode(self, new_mode: AddressingMode) -> "ExtendedPosition":
        """
        Create a new ExtendedPosition with the same coordinates but different addressing mode.

        Args:
            new_mode: New addressing mode

        Returns:
            New ExtendedPosition instance with converted addressing mode

        Raises:
            ValueError: If coordinates are invalid in the new mode
        """
        # Create new instance with same coordinates but different mode
        new_pos = ExtendedPosition(
            row=self._row, col=self._col, cols=self._cols, addressing_mode=new_mode
        )
        return new_pos

    def is_valid_for_mode(self, mode: AddressingMode) -> bool:
        """
        Check if this position is valid for a given addressing mode.

        Args:
            mode: Addressing mode to check against

        Returns:
            True if position is valid for the mode, False otherwise
        """
        address = self._row * self._cols + self._col
        return AddressCalculator.validate_address(address, mode)

    def move_relative(self, row_delta: int = 0, col_delta: int = 0) -> None:
        """
        Move the position by relative offsets.

        Args:
            row_delta: Rows to move (positive for down, negative for up)
            col_delta: Columns to move (positive for right, negative for left)

        Raises:
            ValueError: If new position is invalid
        """
        new_row = self._row + row_delta
        new_col = self._col + col_delta
        self.set_coordinates(new_row, new_col)

    def move_to_next_line(self) -> None:
        """Move to the beginning of the next line."""
        self.set_coordinates(self._row + 1, 0)

    def move_to_previous_line(self) -> None:
        """Move to the beginning of the previous line."""
        if self._row > 0:
            self.set_coordinates(self._row - 1, 0)

    def clamp_to_bounds(self, max_row: int, max_col: int) -> None:
        """
        Clamp coordinates to specified maximum bounds.

        Args:
            max_row: Maximum row (exclusive, 0-based)
            max_col: Maximum column (exclusive, 0-based)
        """
        self._row = max(0, min(self._row, max_row - 1))
        self._col = max(0, min(self._col, max_col - 1))

    def __eq__(self, other: object) -> bool:
        """Check equality with another ExtendedPosition."""
        if not isinstance(other, ExtendedPosition):
            return NotImplemented
        return (
            self._row == other._row
            and self._col == other._col
            and self._cols == other._cols
            and self._addressing_mode == other._addressing_mode
        )

    def __hash__(self) -> int:
        """Hash function for use in sets and dictionaries."""
        return hash((self._row, self._col, self._cols, self._addressing_mode))

    def __repr__(self) -> str:
        """String representation of the position."""
        return (
            f"ExtendedPosition(row={self._row}, col={self._col}, "
            f"cols={self._cols}, mode={self._addressing_mode.value}, "
            f"address={self.linear_address})"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"({self._row}, {self._col}) [{self._addressing_mode.value}]"
