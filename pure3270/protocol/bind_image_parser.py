# ATTRIBUTION NOTICE
# =================================================================================
# This module contains code ported from or inspired by: IBM s3270/x3270
# Source: https://github.com/rhacker/x3270
# Licensed under BSD-3-Clause
#
# DESCRIPTION
# --------------------
# BIND-IMAGE structured field parser for TN3270E addressing mode detection
#
# COMPATIBILITY
# --------------------
# Compatible with TN3270E BIND-IMAGE structured field format and addressing mode negotiation
#
# MODIFICATIONS
# --------------------
# Extended to parse addressing mode information from BIND-IMAGE for 14-bit addressing support
#
# INTEGRATION POINTS
# --------------------
# - TN3270E protocol negotiation
# - Addressing mode negotiation
# - Extended screen buffer initialization
#
# ATTRIBUTION REQUIREMENTS
# ------------------------------
# This attribution must be maintained when this code is modified or
# redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
# Last updated: 2025-10-13
# =================================================================================

"""BIND-IMAGE structured field parser for TN3270E addressing mode detection."""

import logging
from typing import Any, Dict, Optional, Tuple

from ..emulation.addressing import AddressingMode

logger = logging.getLogger(__name__)


class BindImageParseError(Exception):
    """Raised when BIND-IMAGE parsing fails."""

    pass


class BindImageParser:
    """
    Parser for TN3270E BIND-IMAGE structured fields.

    The BIND-IMAGE structured field contains session parameters including
    addressing mode information used for 14-bit addressing negotiation.
    """

    # BIND-IMAGE structured field constants
    SF_BIND_IMAGE = 0x81
    SF_CHARACTERISTICS = 0x81  # Same as BIND-IMAGE in some contexts

    # Addressing mode flags in BIND-IMAGE
    ADDRESSING_12_BIT = 0x00
    ADDRESSING_14_BIT = 0x01

    # BIND-IMAGE parameter offsets
    BIND_IMAGE_HEADER_LEN = 3  # SF ID (1) + Length (2)
    ADDRESSING_MODE_OFFSET = 2  # Offset to addressing mode byte in parameters

    @staticmethod
    def parse_addressing_mode(bind_image_data: bytes) -> Optional[AddressingMode]:
        """
        Parse addressing mode from BIND-IMAGE structured field data.

        Args:
            bind_image_data: Raw BIND-IMAGE structured field bytes

        Returns:
            Detected addressing mode, or None if not determinable

        Raises:
            BindImageParseError: If BIND-IMAGE format is invalid
        """
        try:
            if len(bind_image_data) < BindImageParser.BIND_IMAGE_HEADER_LEN:
                logger.warning("BIND-IMAGE data too short for header")
                return None

            # Check structured field identifier
            sf_id = bind_image_data[0]
            if sf_id != BindImageParser.SF_BIND_IMAGE:
                logger.warning(f"Invalid BIND-IMAGE SF ID: 0x{sf_id:02x}")
                return None

            # Parse length field (big-endian)
            if len(bind_image_data) < 3:
                logger.warning("BIND-IMAGE data too short for length field")
                return None

            sf_length = (bind_image_data[1] << 8) | bind_image_data[2]
            if sf_length < 3 or sf_length > len(bind_image_data):
                logger.warning(f"Invalid BIND-IMAGE length: {sf_length}")
                return None

            # Extract parameters
            parameters = bind_image_data[
                BindImageParser.BIND_IMAGE_HEADER_LEN : sf_length
            ]

            if len(parameters) < 1:
                logger.warning("BIND-IMAGE has no parameters")
                return None

            # Parse addressing mode from parameters
            addressing_mode = BindImageParser._parse_addressing_mode_from_parameters(
                parameters
            )

            logger.debug(f"Parsed addressing mode from BIND-IMAGE: {addressing_mode}")
            return addressing_mode

        except Exception as e:
            logger.error(f"Failed to parse BIND-IMAGE addressing mode: {e}")
            raise BindImageParseError(f"BIND-IMAGE parsing failed: {e}")

    @staticmethod
    def _parse_addressing_mode_from_parameters(
        parameters: bytes,
    ) -> Optional[AddressingMode]:
        """
        Parse addressing mode from BIND-IMAGE parameters.

        Args:
            parameters: BIND-IMAGE parameter bytes

        Returns:
            Addressing mode, or None if not specified
        """
        # BIND-IMAGE parameter format (simplified):
        # Byte 0: Reserved/Flags
        # Byte 1: Addressing mode indicator
        # Byte 2+: Additional parameters

        if len(parameters) < BindImageParser.ADDRESSING_MODE_OFFSET + 1:
            logger.debug("BIND-IMAGE parameters too short for addressing mode")
            return None

        addressing_flag = parameters[BindImageParser.ADDRESSING_MODE_OFFSET]

        # Check addressing mode flag
        if addressing_flag & BindImageParser.ADDRESSING_14_BIT:
            return AddressingMode.MODE_14_BIT
        else:
            return AddressingMode.MODE_12_BIT

    @staticmethod
    def parse_bind_parameters(bind_image_data: bytes) -> Dict[str, Any]:
        """
        Parse complete BIND-IMAGE parameters for session configuration.

        Args:
            bind_image_data: Raw BIND-IMAGE structured field bytes

        Returns:
            Dictionary of parsed parameters

        Raises:
            BindImageParseError: If parsing fails
        """
        try:
            parameters = {}

            if len(bind_image_data) < BindImageParser.BIND_IMAGE_HEADER_LEN:
                raise BindImageParseError("BIND-IMAGE data too short")

            # Validate SF ID
            sf_id = bind_image_data[0]
            if sf_id != BindImageParser.SF_BIND_IMAGE:
                raise BindImageParseError(f"Invalid SF ID: 0x{sf_id:02x}")

            # Parse length
            sf_length = (bind_image_data[1] << 8) | bind_image_data[2]
            if sf_length > len(bind_image_data):
                raise BindImageParseError("SF length exceeds data length")

            # Extract and parse parameters
            param_data = bind_image_data[
                BindImageParser.BIND_IMAGE_HEADER_LEN : sf_length
            ]

            if len(param_data) >= 1:
                parameters["flags"] = param_data[0]

            if len(param_data) >= 2:
                parameters["addressing_mode"] = param_data[1]

            if len(param_data) >= 4:
                parameters["screen_rows"] = param_data[2]
                parameters["screen_cols"] = param_data[3]

            # Additional parameters as needed
            if len(param_data) > 4:
                parameters["extended_params"] = param_data[4:]

            return parameters

        except Exception as e:
            raise BindImageParseError(f"BIND parameter parsing failed: {e}")

    @staticmethod
    def create_bind_image_response(
        addressing_mode: AddressingMode, screen_rows: int = 24, screen_cols: int = 80
    ) -> bytes:
        """
        Create a BIND-IMAGE response structured field.

        Args:
            addressing_mode: The addressing mode to advertise
            screen_rows: Screen rows
            screen_cols: Screen columns

        Returns:
            BIND-IMAGE structured field bytes
        """
        # Addressing mode flag
        addressing_flag = (
            BindImageParser.ADDRESSING_14_BIT
            if addressing_mode == AddressingMode.MODE_14_BIT
            else BindImageParser.ADDRESSING_12_BIT
        )

        # Build parameters
        parameters = bytes(
            [
                0x00,  # Flags (reserved)
                addressing_flag,  # Addressing mode
                screen_rows,  # Screen rows
                screen_cols,  # Screen columns
            ]
        )

        # Calculate total length
        total_length = BindImageParser.BIND_IMAGE_HEADER_LEN + len(parameters)

        # Build structured field
        sf_data = (
            bytes(
                [
                    BindImageParser.SF_BIND_IMAGE,  # SF ID
                    (total_length >> 8) & 0xFF,  # Length high byte
                    total_length & 0xFF,  # Length low byte
                ]
            )
            + parameters
        )

        return sf_data

    @staticmethod
    def validate_bind_image_format(data: bytes) -> bool:
        """
        Validate that data represents a valid BIND-IMAGE structured field.

        Args:
            data: Data to validate

        Returns:
            True if valid BIND-IMAGE format, False otherwise
        """
        try:
            if len(data) < BindImageParser.BIND_IMAGE_HEADER_LEN:
                return False

            # Check SF ID
            if data[0] != BindImageParser.SF_BIND_IMAGE:
                return False

            # Check length
            sf_length = (data[1] << 8) | data[2]
            if sf_length < BindImageParser.BIND_IMAGE_HEADER_LEN or sf_length > len(
                data
            ):
                return False

            return True

        except Exception:
            return False
