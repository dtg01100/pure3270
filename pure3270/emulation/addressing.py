# ATTRIBUTION NOTICE
# =================================================================================
# This module contains code ported from or inspired by: IBM s3270/x3270
# Source: https://github.com/rhacker/x3270
# Licensed under BSD-3-Clause
#
# DESCRIPTION
# --------------------
# Addressing mode enumeration and utilities for 3270 emulation
#
# COMPATIBILITY
# --------------------
# Compatible with TN3270E addressing mode negotiation
#
# MODIFICATIONS
# --------------------
# Extended to support 14-bit addressing for large screen emulation
#
# INTEGRATION POINTS
# --------------------
# - TN3270E protocol negotiation
# - Screen buffer addressing calculations
# - Extended position handling
#
# ATTRIBUTION REQUIREMENTS
# ------------------------------
# This attribution must be maintained when this code is modified or
# redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
# Last updated: 2025-10-13
# =================================================================================

"""Addressing mode enumeration and utilities for 3270 emulation."""

import logging
from enum import Enum
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class AddressingMode(Enum):
    """Enumeration of supported 3270 addressing modes."""

    MODE_12_BIT = "12-bit"
    """Traditional 12-bit addressing mode supporting up to 4096 positions (24x80, 32x80, etc.)."""

    MODE_14_BIT = "14-bit"
    """Extended 14-bit addressing mode supporting up to 16384 positions for large screens."""


class AddressCalculator:
    """Utility class for address calculations and conversions between addressing modes."""

    @staticmethod
    def validate_address(address: int, mode: AddressingMode) -> bool:
        """
        Validate if an address is valid for the given addressing mode.

        Args:
            address: The address to validate (0-based linear position)
            mode: The addressing mode to validate against

        Returns:
            True if address is valid for the mode, False otherwise
        """
        if mode == AddressingMode.MODE_12_BIT:
            return 0 <= address <= 0xFFF  # 12-bit: 0-4095
        elif mode == AddressingMode.MODE_14_BIT:
            return 0 <= address <= 0x3FFF  # 14-bit: 0-16383
        else:
            logger.warning(f"Unknown addressing mode: {mode}")  # type: ignore[unreachable]
            return False

    @staticmethod
    def address_to_coords(
        address: int, cols: int, mode: AddressingMode
    ) -> Optional[Tuple[int, int]]:
        """
        Convert a linear address to row/column coordinates.

        Args:
            address: Linear address (0-based)
            cols: Number of columns in the screen
            mode: Addressing mode

        Returns:
            Tuple of (row, col) coordinates, or None if address is invalid
        """
        if not AddressCalculator.validate_address(address, mode):
            logger.warning(f"Invalid address {address} for mode {mode}")
            return None

        row = address // cols
        col = address % cols
        return (row, col)

    @staticmethod
    def coords_to_address(
        row: int, col: int, cols: int, mode: AddressingMode
    ) -> Optional[int]:
        """
        Convert row/column coordinates to a linear address.

        Args:
            row: Row coordinate (0-based)
            col: Column coordinate (0-based)
            cols: Number of columns in the screen
            mode: Addressing mode

        Returns:
            Linear address, or None if coordinates would exceed mode limits
        """
        address = row * cols + col

        if not AddressCalculator.validate_address(address, mode):
            logger.warning(
                f"Coordinates ({row}, {col}) exceed address limits for mode {mode}"
            )
            return None

        return address

    @staticmethod
    def get_max_positions(mode: AddressingMode) -> int:
        """
        Get the maximum number of positions supported by the addressing mode.

        Args:
            mode: The addressing mode

        Returns:
            Maximum number of positions (1-based, so max address + 1)
        """
        if mode == AddressingMode.MODE_12_BIT:
            return 4096  # 0x1000
        elif mode == AddressingMode.MODE_14_BIT:
            return 16384  # 0x4000
        else:
            logger.warning(f"Unknown addressing mode: {mode}")  # type: ignore[unreachable]
            return 4096  # Default to 12-bit

    @staticmethod
    def convert_address_mode(
        address: int, from_mode: AddressingMode, to_mode: AddressingMode, cols: int
    ) -> Optional[int]:
        """
        Convert an address from one addressing mode to another.

        This is primarily useful for converting between 12-bit and 14-bit addressing
        when the same row/column coordinates are used but different linear addressing.

        Args:
            address: The address to convert
            from_mode: Source addressing mode
            to_mode: Target addressing mode
            cols: Number of columns (needed for coordinate conversion)

        Returns:
            Converted address, or None if conversion is not possible
        """
        # Convert to coordinates first
        coords = AddressCalculator.address_to_coords(address, cols, from_mode)
        if coords is None:
            return None

        # Convert back to address in target mode
        return AddressCalculator.coords_to_address(coords[0], coords[1], cols, to_mode)
