#!/usr/bin/env python3
"""
Parameterized tests for all 13 IBM 3270 terminal models.

This test suite validates that pure3270 correctly handles all supported
terminal model configurations, including screen dimensions, capabilities,
and negotiation behavior.
"""

# Import terminal model definitions
import sys
from pathlib import Path
from typing import Dict, Tuple

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.utils import TERMINAL_MODELS, TerminalCapabilities


class TestTerminalModels:
    """Test all 13 IBM 3270 terminal models."""

    @pytest.mark.parametrize("model_name,capabilities", TERMINAL_MODELS.items())
    def test_model_screen_dimensions(
        self, model_name: str, capabilities: TerminalCapabilities
    ):
        """Test that each model has correct screen dimensions."""
        rows, cols = capabilities.screen_size

        # Validate reasonable dimension ranges
        assert 20 <= rows <= 50, f"Invalid rows for {model_name}: {rows}"
        assert 80 <= cols <= 132, f"Invalid cols for {model_name}: {cols}"

        # Test that we can create a screen buffer with these dimensions
        screen = ScreenBuffer(rows=rows, cols=cols)
        assert screen.rows == rows
        assert screen.cols == cols
        assert len(screen.buffer) == rows * cols

    @pytest.mark.parametrize("model_name,capabilities", TERMINAL_MODELS.items())
    def test_model_capabilities_structure(
        self, model_name: str, capabilities: TerminalCapabilities
    ):
        """Test that each model has properly defined capabilities."""
        # All models should have screen_size as a tuple
        assert isinstance(capabilities.screen_size, tuple)
        assert len(capabilities.screen_size) == 2

        # All models should have boolean capability flags
        assert isinstance(capabilities.color_support, bool)
        assert isinstance(capabilities.extended_attributes, bool)
        assert isinstance(capabilities.programmed_symbols, bool)
        assert isinstance(capabilities.extended_highlighting, bool)
        assert isinstance(capabilities.light_pen_support, bool)
        assert isinstance(capabilities.magnetic_slot_reader, bool)
        assert isinstance(capabilities.operator_information_area, bool)

        # All models should have character sets
        assert isinstance(capabilities.character_sets, list)
        assert "EBCDIC" in capabilities.character_sets

    @pytest.mark.parametrize("model_name,capabilities", TERMINAL_MODELS.items())
    def test_model_expected_capabilities(
        self, model_name: str, capabilities: TerminalCapabilities
    ):
        """Test that models have expected capabilities based on IBM specifications."""
        rows, cols = capabilities.screen_size

        # 3278 models should not have color support
        if "3278" in model_name:
            assert (
                not capabilities.color_support
            ), f"3278 model {model_name} should not have color support"

        # 3279 models should have color support
        if "3279" in model_name:
            assert (
                capabilities.color_support
            ), f"3279 model {model_name} should have color support"

        # 3179 models should have color support
        if "3179" in model_name:
            assert (
                capabilities.color_support
            ), f"3179 model {model_name} should have color support"

        # PC models should have color support
        if "3270PC" in model_name:
            assert (
                capabilities.color_support
            ), f"PC model {model_name} should have color support"

        # All models should have extended attributes
        assert (
            capabilities.extended_attributes
        ), f"Model {model_name} should have extended attributes"

        # All models should have extended highlighting
        assert (
            capabilities.extended_highlighting
        ), f"Model {model_name} should have extended highlighting"

    @pytest.mark.parametrize("model_name,capabilities", TERMINAL_MODELS.items())
    def test_model_screen_buffer_operations(
        self, model_name: str, capabilities: TerminalCapabilities
    ):
        """Test that screen buffer operations work correctly for each model."""
        rows, cols = capabilities.screen_size
        screen = ScreenBuffer(rows=rows, cols=cols)

        # Test cursor positioning
        screen.cursor_row = rows // 2
        screen.cursor_col = cols // 2
        assert screen.cursor_row == rows // 2
        assert screen.cursor_col == cols // 2

        # Test boundary conditions
        screen.cursor_row = -1
        screen.cursor_col = -1
        # Cursor should be clamped to valid range (implementation dependent)

        # Test writing to buffer
        test_char = 0xC1  # EBCDIC 'A'
        screen.buffer[0] = test_char
        assert screen.buffer[0] == test_char

        # Test ASCII buffer access
        ascii_content = screen.ascii_buffer
        assert isinstance(ascii_content, str)
        assert len(ascii_content.split("\n")) == rows

    @pytest.mark.parametrize("model_name,capabilities", TERMINAL_MODELS.items())
    def test_model_negotiation_compatibility(
        self, model_name: str, capabilities: TerminalCapabilities
    ):
        """Test that model names are compatible with TN3270E negotiation."""
        # Model names should follow IBM naming conventions
        assert model_name.startswith("IBM-"), f"Invalid model name format: {model_name}"

        # Should not contain spaces or special characters that break negotiation
        assert " " not in model_name, f"Model name contains space: {model_name}"
        assert all(
            c.isalnum() or c in "-." for c in model_name
        ), f"Invalid characters in model name: {model_name}"

    def test_all_models_accounted_for(self):
        """Test that we have exactly 13 models as documented."""
        expected_models = [
            "IBM-3278-2",
            "IBM-3278-3",
            "IBM-3278-4",
            "IBM-3278-5",
            "IBM-3279-2",
            "IBM-3279-3",
            "IBM-3279-4",
            "IBM-3279-5",
            "IBM-3179-2",
            "IBM-3270PC-G",
            "IBM-3270PC-GA",
            "IBM-3270PC-GX",
            "IBM-DYNAMIC",
        ]

        actual_models = list(TERMINAL_MODELS.keys())

        # Check that we have all expected models
        for expected in expected_models:
            assert expected in actual_models, f"Missing expected model: {expected}"

        # Check that we don't have extra models
        for actual in actual_models:
            assert actual in expected_models, f"Unexpected model: {actual}"

        # Check total count
        assert (
            len(TERMINAL_MODELS) == 13
        ), f"Expected 13 models, got {len(TERMINAL_MODELS)}"

    def test_model_screen_size_validation(self):
        """Test that screen sizes match IBM specifications."""
        expected_sizes = {
            "IBM-3278-2": (24, 80),
            "IBM-3278-3": (32, 80),
            "IBM-3278-4": (43, 80),
            "IBM-3278-5": (27, 132),
            "IBM-3279-2": (24, 80),
            "IBM-3279-3": (32, 80),
            "IBM-3279-4": (43, 80),
            "IBM-3279-5": (27, 132),
            "IBM-3179-2": (24, 80),
            "IBM-3270PC-G": (24, 80),
            "IBM-3270PC-GA": (24, 80),
            "IBM-3270PC-GX": (24, 80),
            "IBM-DYNAMIC": (24, 80),
        }

        for model_name, expected_size in expected_sizes.items():
            capabilities = TERMINAL_MODELS[model_name]
            assert (
                capabilities.screen_size == expected_size
            ), f"Wrong screen size for {model_name}: expected {expected_size}, got {capabilities.screen_size}"

    def test_model_capability_consistency(self):
        """Test that similar models have consistent capabilities."""
        # All 3278 models should have identical capability flags (except screen size)
        model_3278_2 = TERMINAL_MODELS["IBM-3278-2"]
        model_3278_3 = TERMINAL_MODELS["IBM-3278-3"]

        # These should be identical for 3278 models
        assert model_3278_2.color_support == model_3278_3.color_support
        assert model_3278_2.extended_attributes == model_3278_3.extended_attributes
        assert model_3278_2.programmed_symbols == model_3278_3.programmed_symbols
        assert model_3278_2.extended_highlighting == model_3278_3.extended_highlighting
        assert model_3278_2.light_pen_support == model_3278_3.light_pen_support

        # All 3279 models should have color support
        for model_name in ["IBM-3279-2", "IBM-3279-3", "IBM-3279-4", "IBM-3279-5"]:
            assert TERMINAL_MODELS[
                model_name
            ].color_support, f"{model_name} should have color support"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
