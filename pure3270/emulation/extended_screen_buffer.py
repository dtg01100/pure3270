# ATTRIBUTION NOTICE
# =================================================================================
# This module contains code ported from or inspired by: IBM s3270/x3270
# Source: https://github.com/rhacker/x3270
# Licensed under BSD-3-Clause
#
# DESCRIPTION
# --------------------
# Extended screen buffer with 14-bit addressing support for large screen emulation
#
# COMPATIBILITY
# --------------------
# Compatible with TN3270E extended addressing and large screen formats
#
# MODIFICATIONS
# --------------------
# Extended ScreenBuffer to support 14-bit addressing with backward compatibility
#
# INTEGRATION POINTS
# --------------------
# - Extends existing ScreenBuffer API
# - Maintains field management compatibility
# - Supports extended position handling
#
# ATTRIBUTION REQUIREMENTS
# ------------------------------
# This attribution must be maintained when this code is modified or
# redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
# Last updated: 2025-10-13
# =================================================================================

"""Extended screen buffer with 14-bit addressing support for large screen emulation."""

import logging
from typing import List, Optional, Tuple

from .addressing import AddressCalculator, AddressingMode
from .extended_position import ExtendedPosition
from .screen_buffer import Field, ScreenBuffer

logger = logging.getLogger(__name__)


class ExtendedScreenBuffer(ScreenBuffer):
    """
    Extended screen buffer supporting 14-bit addressing for large screens.

    This class extends the traditional ScreenBuffer to support larger screen sizes
    through 14-bit addressing while maintaining full backward compatibility with
    existing ScreenBuffer API.
    """

    def __init__(
        self,
        rows: int = 24,
        cols: int = 80,
        init_value: int = 0x40,
        addressing_mode: AddressingMode = AddressingMode.MODE_12_BIT,
    ):
        """
        Initialize the ExtendedScreenBuffer.

        Args:
            rows: Number of rows (default 24)
            cols: Number of columns (default 80)
            init_value: Initial value for buffer positions (default 0x40 for EBCDIC space)
            addressing_mode: Addressing mode for the buffer

        Raises:
            ValueError: If dimensions exceed addressing mode limits
        """
        # Validate dimensions against addressing mode
        total_positions = rows * cols
        if not AddressCalculator.validate_address(total_positions - 1, addressing_mode):
            max_positions = AddressCalculator.get_max_positions(addressing_mode)
            raise ValueError(
                f"Screen size {rows}x{cols} ({total_positions} positions) exceeds "
                f"{addressing_mode.value} addressing limits ({max_positions} positions)"
            )

        # Initialize parent ScreenBuffer
        super().__init__(rows=rows, cols=cols, init_value=init_value)

        # Extended properties
        self._addressing_mode = addressing_mode
        self._extended_cursor = ExtendedPosition(
            row=0, col=0, cols=cols, addressing_mode=addressing_mode
        )

        logger.debug(
            f"ExtendedScreenBuffer initialized: {rows}x{cols}, "
            f"mode={addressing_mode.value}, positions={total_positions}"
        )

    @property
    def addressing_mode(self) -> AddressingMode:
        """Get the addressing mode for this buffer."""
        return self._addressing_mode

    @property
    def extended_cursor(self) -> ExtendedPosition:
        """Get the extended cursor position."""
        return self._extended_cursor

    def set_position(self, row: int, col: int, wrap: bool = False) -> None:
        """
        Set cursor position with extended addressing validation.

        Args:
            row: Row coordinate
            col: Column coordinate
            wrap: Whether to wrap coordinates to valid range

        Raises:
            ValueError: If position is invalid for the addressing mode
        """
        # Validate position first
        temp_pos = ExtendedPosition(
            row=row, col=col, cols=self.cols, addressing_mode=self._addressing_mode
        )

        # Update extended cursor
        self._extended_cursor = temp_pos

        # Call parent method for backward compatibility
        super().set_position(row, col, wrap)

    def set_position_from_address(self, address: int) -> None:
        """
        Set cursor position from a linear address.

        Args:
            address: Linear address to set cursor to

        Raises:
            ValueError: If address is invalid for the addressing mode
        """
        self._extended_cursor.set_from_address(address)
        row, col = self._extended_cursor.coordinates
        super().set_position(row, col)

    def get_position_address(self) -> int:
        """
        Get the current cursor position as a linear address.

        Returns:
            Linear address of current cursor position
        """
        return self._extended_cursor.linear_address

    def write_char_at_address(
        self,
        ebcdic_byte: int,
        address: int,
        protected: bool = False,
        circumvent_protection: bool = False,
    ) -> None:
        """
        Write a character at a specific linear address.

        Args:
            ebcdic_byte: EBCDIC byte value to write
            address: Linear address to write to
            protected: Whether to set protection attribute
            circumvent_protection: Whether to write even to protected fields

        Raises:
            ValueError: If address is invalid for the addressing mode
        """
        coords = AddressCalculator.address_to_coords(
            address, self.cols, self._addressing_mode
        )
        if coords is None:
            raise ValueError(
                f"Invalid address {address} for {self._addressing_mode.value} mode"
            )

        row, col = coords
        self.write_char(ebcdic_byte, row, col, protected, circumvent_protection)

    def read_char_at_address(self, address: int) -> Optional[int]:
        """
        Read a character from a specific linear address.

        Args:
            address: Linear address to read from

        Returns:
            EBCDIC byte value at the address, or None if address is invalid
        """
        coords = AddressCalculator.address_to_coords(
            address, self.cols, self._addressing_mode
        )
        if coords is None:
            return None

        row, col = coords
        if 0 <= row < self.rows and 0 <= col < self.cols:
            pos = row * self.cols + col
            return self.buffer[pos]
        return None

    def is_address_valid(self, address: int) -> bool:
        """
        Check if an address is valid for this buffer's addressing mode.

        Args:
            address: Address to validate

        Returns:
            True if address is valid, False otherwise
        """
        return AddressCalculator.validate_address(address, self._addressing_mode)

    def get_address_range(self) -> Tuple[int, int]:
        """
        Get the valid address range for this buffer.

        Returns:
            Tuple of (min_address, max_address) inclusive
        """
        max_positions = AddressCalculator.get_max_positions(self._addressing_mode)
        buffer_size = self.rows * self.cols
        max_address = min(buffer_size - 1, max_positions - 1)
        return (0, max_address)

    def convert_addressing_mode(
        self, new_mode: AddressingMode
    ) -> Optional["ExtendedScreenBuffer"]:
        """
        Create a new ExtendedScreenBuffer with the same content but different addressing mode.

        Args:
            new_mode: New addressing mode

        Returns:
            New ExtendedScreenBuffer instance, or None if conversion fails

        Raises:
            ValueError: If current buffer size exceeds new mode limits
        """
        total_positions = self.rows * self.cols
        if not AddressCalculator.validate_address(total_positions - 1, new_mode):
            raise ValueError(
                f"Cannot convert to {new_mode.value} mode: "
                f"buffer size {total_positions} exceeds limits"
            )

        # Create new buffer with same dimensions but different mode
        new_buffer = ExtendedScreenBuffer(
            rows=self.rows, cols=self.cols, addressing_mode=new_mode
        )

        # Copy buffer content
        new_buffer.buffer = self.buffer.copy()
        new_buffer.attributes = self.attributes.copy()
        new_buffer._extended_attributes = self._extended_attributes.copy()
        new_buffer.fields = (
            self.fields.copy()
        )  # Note: fields contain position references

        # Update cursor position
        new_buffer._extended_cursor = self._extended_cursor.convert_addressing_mode(
            new_mode
        )
        new_buffer.cursor_row = new_buffer._extended_cursor.row
        new_buffer.cursor_col = new_buffer._extended_cursor.col

        return new_buffer

    def get_field_at_address(self, address: int) -> Optional[Field]:
        """
        Get the field containing a specific linear address.

        Args:
            address: Linear address to check

        Returns:
            Field containing the address, or None if no field or invalid address
        """
        coords = AddressCalculator.address_to_coords(
            address, self.cols, self._addressing_mode
        )
        if coords is None:
            return None

        row, col = coords
        return self.get_field_at_position(row, col)

    def move_cursor_to_address(self, address: int) -> None:
        """
        Move cursor to a specific linear address.

        Args:
            address: Linear address to move cursor to

        Raises:
            ValueError: If address is invalid
        """
        self.set_position_from_address(address)

    def __repr__(self) -> str:
        """String representation including addressing mode."""
        return (
            f"ExtendedScreenBuffer({self.rows}x{self.cols}, "
            f"mode={self._addressing_mode.value}, "
            f"fields={len(self.fields)})"
        )
