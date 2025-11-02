#!/usr/bin/env python3
"""
Test module for trace replay functionality.

Tests the Replayer class to ensure it correctly processes trace files
and produces expected screen buffer state.
"""

import logging
import os
from pathlib import Path

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.trace.replayer import Replayer

logger = logging.getLogger(__name__)


@pytest.mark.slow
def test_replay_trace():
    """
    Test replaying a trace file using the Replayer class.

    Uses the TRACE_FILE environment variable or defaults to ra_test.trc.
    Validates that replay() returns a dict with expected keys and types.
    """
    # Get trace file path from environment or use default
    trace_file = os.environ.get("TRACE_FILE", "tests/data/traces/ra_test.trc")

    # Verify trace file exists
    trace_path = Path(trace_file)
    if not trace_path.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    logger.info(f"Testing trace replay with file: {trace_file}")

    try:
        # Create replayer instance
        replayer = Replayer()

        # Replay the trace file
        result = replayer.replay(str(trace_path))

        # Validate result structure
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "screen_buffer" in result, "Result should contain 'screen_buffer' key"
        assert "ascii_screen" in result, "Result should contain 'ascii_screen' key"
        assert "fields" in result, "Result should contain 'fields' key"

        # Validate screen_buffer
        screen_buffer = result["screen_buffer"]
        assert isinstance(
            screen_buffer, ScreenBuffer
        ), "screen_buffer should be a ScreenBuffer instance"

        # Validate ascii_screen
        ascii_screen = result["ascii_screen"]
        assert isinstance(ascii_screen, str), "ascii_screen should be a string"
        assert len(ascii_screen) > 0, "ascii_screen should be non-empty"

        # Validate fields
        fields = result["fields"]
        assert isinstance(fields, list), "fields should be a list"

        logger.info(
            f"Replay successful: ascii_screen length={len(ascii_screen)}, fields count={len(fields)}"
        )

    except FileNotFoundError as e:
        pytest.fail(f"Trace file not found: {e}")
    except ValueError as e:
        pytest.fail(f"Trace parsing failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during replay: {e}")
        pytest.fail(f"Replay failed with unexpected error: {e}")
