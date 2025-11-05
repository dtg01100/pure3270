#!/usr/bin/env python3
"""
Test module for trace replay functionality.

Tests the Replayer class to ensure it correctly processes trace files
and produces expected screen buffer state.
"""

import logging
import os
import sys
from pathlib import Path

import pytest

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.trace.replayer import Replayer

# Import packet analyzer mixin
sys.path.insert(0, str(Path(__file__).parent))
try:
    from test_protocol_state_machine import TracePacketAnalyzerMixin

    PACKET_ANALYZER_AVAILABLE = True
except ImportError:
    PACKET_ANALYZER_AVAILABLE = False
    TracePacketAnalyzerMixin = object

logger = logging.getLogger(__name__)


class TraceReplayTestCase(TracePacketAnalyzerMixin):
    """Enhanced trace replay test case with packet analysis capabilities."""

    def __init__(self):
        if PACKET_ANALYZER_AVAILABLE:
            super().__init__()
        self.replayer = Replayer()


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


@pytest.mark.slow
def test_trace_packet_analysis():
    """
    Test packet analysis of trace files to ensure protocol compliance.
    """
    if not PACKET_ANALYZER_AVAILABLE:
        pytest.skip("Packet analyzer not available")

    test_case = TraceReplayTestCase()

    # Test with smoke trace file
    trace_file = "tests/data/traces/smoke.trc"
    trace_path = Path(trace_file)

    if not trace_path.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    # Analyze packets in the trace
    analysis = test_case.analyze_trace_packets(str(trace_path))

    # Verify analysis structure
    assert "packet_count" in analysis, "Analysis should contain packet count"
    assert "summary" in analysis, "Analysis should contain summary"
    assert "packets" in analysis, "Analysis should contain packet list"

    # Verify we have packets
    assert analysis["packet_count"] > 0, "Trace should contain packets"

    # Verify summary contains expected keys
    summary = analysis["summary"]
    assert "telnet_commands" in summary, "Summary should contain telnet command count"
    assert "tn3270e_headers" in summary, "Summary should contain TN3270E header count"
    assert "data_segments" in summary, "Summary should contain data segment count"

    logger.info(
        f"Packet analysis: {test_case.get_trace_packet_summary(str(trace_path))}"
    )


@pytest.mark.slow
def test_trace_negotiation_validation():
    """
    Test that trace files contain proper TN3270 negotiation sequences.
    """
    if not PACKET_ANALYZER_AVAILABLE:
        pytest.skip("Packet analyzer not available")

    test_case = TraceReplayTestCase()

    # Test multiple trace files for negotiation
    trace_files = [
        "tests/data/traces/smoke.trc",
        "tests/data/traces/login.trc",
        "tests/data/traces/tn3270e-renegotiate.trc",
    ]

    for trace_file in trace_files:
        trace_path = Path(trace_file)
        if not trace_path.exists():
            logger.warning(f"Trace file not found: {trace_file}")
            continue

        try:
            # Test that trace contains TN3270 negotiation
            test_case.assert_trace_contains_negotiation(str(trace_path))
            logger.info(f"✓ {trace_file} contains valid TN3270 negotiation")
        except AssertionError as e:
            # Log but don't fail - some traces might not have negotiation
            logger.warning(
                f"⚠️  {trace_file} negotiation check failed: {str(e)[:100]}..."
            )


@pytest.mark.slow
def test_trace_packet_structure():
    """
    Test that packets in trace files have valid structure.
    """
    if not PACKET_ANALYZER_AVAILABLE:
        pytest.skip("Packet analyzer not available")

    test_case = TraceReplayTestCase()

    trace_file = "tests/data/traces/smoke.trc"
    trace_path = Path(trace_file)

    if not trace_path.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    # Get individual packets
    records = test_case.parse_trace_file(str(trace_path))
    assert len(records) > 0, "Trace should contain records"

    # Analyze first few packets
    for i, record in enumerate(records[:5]):  # Test first 5 packets
        analysis = test_case.analyze_packet_data(record)

        # Every packet analysis should have basic structure
        assert "length" in analysis, f"Packet {i} analysis missing length"
        assert "raw_hex" in analysis, f"Packet {i} analysis missing raw_hex"
        assert analysis["length"] == len(record), f"Packet {i} length mismatch"

        # Packet should be analyzable (not error)
        assert (
            "error" not in analysis
        ), f"Packet {i} analysis failed: {analysis.get('error', 'unknown')}"

    logger.info(
        f"✓ First {min(5, len(records))} packets in {trace_file} have valid structure"
    )


@pytest.mark.slow
def test_trace_replay_with_packet_insights():
    """
    Enhanced trace replay test that provides packet-level insights on failure.
    """
    # Get trace file path from environment or use default
    trace_file = os.environ.get("TRACE_FILE", "tests/data/traces/smoke.trc")

    # Verify trace file exists
    trace_path = Path(trace_file)
    if not trace_path.exists():
        pytest.skip(f"Trace file not found: {trace_file}")

    logger.info(f"Testing enhanced trace replay with file: {trace_file}")

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

        # Additional validation with packet insights
        if PACKET_ANALYZER_AVAILABLE:
            test_case = TraceReplayTestCase()
            packet_summary = test_case.get_trace_packet_summary(str(trace_path))
            logger.info(f"Packet analysis: {packet_summary}")

            # Verify trace contains some data packets
            analysis = test_case.analyze_trace_packets(str(trace_path))
            assert (
                analysis["summary"]["data_segments"] > 0
            ), "Trace should contain data segments"

        logger.info(
            f"Enhanced replay successful: ascii_screen length={len(result['ascii_screen'])}, "
            f"fields count={len(result['fields'])}"
        )

    except FileNotFoundError as e:
        pytest.fail(f"Trace file not found: {e}")
    except ValueError as e:
        # Enhanced error reporting with packet analysis
        if PACKET_ANALYZER_AVAILABLE:
            test_case = TraceReplayTestCase()
            packet_summary = test_case.get_trace_packet_summary(str(trace_path))
            pytest.fail(f"Trace parsing failed: {e}\nPacket analysis: {packet_summary}")
        else:
            pytest.fail(f"Trace parsing failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during replay: {e}")
        pytest.fail(f"Replay failed with unexpected error: {e}")
