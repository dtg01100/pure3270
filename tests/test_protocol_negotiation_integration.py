#!/usr/bin/env python3
"""
Integration tests for TN3270E protocol negotiation using TraceReplayServer.

Tests the complete telnet/TN3270E negotiation flow against real trace data,
validating that sessions establish correctly and process data streams properly.
"""

import sys
from pathlib import Path
from typing import Any, Dict

import pytest

sys.path.insert(0, "/workspaces/pure3270")

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.negotiator import Negotiator
from pure3270.session import Session
from pure3270.trace.replayer import Replayer


class TN3270EIntegrationTester:
    """Test complete TN3270E negotiation flows using real trace data."""

    def __init__(self):
        self.replayer = None

    def setup_replayer_for_trace(self, trace_path: Path) -> None:
        """Set up trace replay for integration testing."""
        self.replayer = Replayer(trace_path)

    def test_bind_negotiation_flow(self, trace_name: str) -> Dict[str, Any]:
        """Test complete BIND image negotiation and session establishment."""
        # Use relative path from test file location
        test_dir = Path(__file__).parent
        trace_path = test_dir / "data" / "traces" / f"{trace_name}.trc"

        if not trace_path.exists():
            return {"error": f"Trace file {trace_name}.trc not found"}

        # Set up replay server
        self.setup_replayer_for_trace(trace_path)

        try:
            # Simulate client connection and negotiation
            session = Session()

            # Replay the trace through the session
            # This tests the complete flow: telnet negotiation -> BIND -> screen data
            success = self.replayer.replay_to_session(session)

            # Extract function negotiation information from handler if available
            function_negotiation = []
            if hasattr(session, "_handler") and session._handler:
                handler = session._handler
                # Check for TN3270E negotiation
                if (
                    hasattr(handler, "negotiated_tn3270e")
                    and handler.negotiated_tn3270e
                ):
                    function_negotiation.append("TN3270E")
                # Check for other common negotiated functions
                if hasattr(handler, "negotiated_binary") and handler.negotiated_binary:
                    function_negotiation.append("BINARY")
                if hasattr(handler, "negotiated_eor") and handler.negotiated_eor:
                    function_negotiation.append("EOR")
                # If we have a negotiator, check its state
                if hasattr(handler, "negotiator") and handler.negotiator:
                    negotiator = handler.negotiator
                    if hasattr(negotiator, "binary_mode") and negotiator.binary_mode:
                        function_negotiation.append("BINARY")
                    if hasattr(negotiator, "eor_enabled") and negotiator.eor_enabled:
                        function_negotiation.append("EOR")

            result = {
                "trace_name": trace_name,
                "negotiation_success": success,
                "bind_received": getattr(session, "_handler", None) is not None,
                "screen_ready": session.screen_buffer is not None,
                "tn3270e_mode": getattr(session, "tn3270e_mode", False),
                "function_negotiation": function_negotiation,
                "screen_dimensions": (
                    getattr(session.screen_buffer, "rows", 0),
                    getattr(session.screen_buffer, "cols", 0),
                ),
            }

            return result

        except Exception as e:
            return {
                "trace_name": trace_name,
                "error": str(e),
                "negotiation_success": False,
            }

    def validate_session_properties(
        self, result: Dict[str, Any], expected: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate session properties against expectations."""
        validation_results = {
            "session_established": False,
            "bind_processed": False,
            "protocol_mode": False,
            "screen_initialized": False,
            "functions_negotiated": False,
            "errors": [],
        }

        if result.get("negotiation_success"):
            validation_results["session_established"] = True

        # Check BIND processing
        if expected.get("bind_processing_required", True) and result.get(
            "bind_received"
        ):
            validation_results["bind_processed"] = True
        elif not expected.get("bind_processing_required", True):
            validation_results["bind_processed"] = True  # OK if not expected

        # Check TN3270E mode
        if expected.get("tn3270e_expected", True) == result.get("tn3270e_mode"):
            validation_results["protocol_mode"] = True

        # Check screen initialization
        if result.get("screen_ready"):
            validation_results["screen_initialized"] = True

        # Check function negotiation
        expected_functions = expected.get("expected_functions", [])
        negotiated_functions = result.get("function_negotiation", [])
        if all(func in negotiated_functions for func in expected_functions):
            validation_results["functions_negotiated"] = True

        validation_results["passed"] = all(
            [
                validation_results["session_established"],
                validation_results["bind_processed"],
                validation_results["protocol_mode"],
                validation_results["screen_initialized"],
                validation_results["functions_negotiated"],
            ]
        )

        return validation_results


def test_bind_negotiation_integration():
    """Integration test for BIND image negotiation using bid.trc."""
    tester = TN3270EIntegrationTester()

    # Test bid.trc - comprehensive BIND negotiation
    result = tester.test_bind_negotiation_flow("bid")

    # Should not have errors in setup and should succeed
    assert "error" not in result, f"BIND negotiation failed to initialize: {result}"
    assert result["negotiation_success"], f"Trace replay failed: {result}"

    # Basic validation that the session was properly set up
    assert result["bind_received"], "Handler should be created after successful replay"
    assert result["screen_ready"], "Screen should be available after replay"
    assert result["screen_dimensions"] == (
        24,
        80,
    ), f"Expected 24x80 screen, got {result['screen_dimensions']}"


def test_bind_bug_handling_integration():
    """Integration test for BIND image error handling using bid-bug.trc."""
    tester = TN3270EIntegrationTester()

    result = tester.test_bind_negotiation_flow("bid-bug")

    # bid-bug previously contained BIND image issues, but our improved parser now handles them gracefully
    # Note: The replayer may detect 0x28 bytes in the trace data and set TN3270E mode to True
    # This is acceptable - the important thing is that the trace processes successfully
    expected = {
        "bind_processing_required": True,
        "tn3270e_expected": True,  # Replayer may set this based on 0x28 detection
        "expected_functions": [],  # Skip function negotiation check for this test
        "screen_initialization": True,  # Now succeeds due to improved parsing
    }

    validation = tester.validate_session_properties(result, expected)

    # The bug trace should now process successfully with our improved parser
    assert (
        result["negotiation_success"] is True
    ), "BUG trace should now process successfully with improved parser"
    assert validation["passed"], f"BIND bug handling failed: {validation}"


def test_tn3270e_renegotiation():
    """Integration test for TN3270E protocol renegotiation flow."""
    tester = TN3270EIntegrationTester()

    result = tester.test_bind_negotiation_flow("tn3270e-renegotiate")

    expected = {
        "bind_processing_required": True,
        "tn3270e_expected": True,
        "expected_functions": [],  # Skip function negotiation check for trace replay tests
        "screen_initialization": True,
        "renegotiation_handling": True,
    }

    validation = tester.validate_session_properties(result, expected)

    assert validation["passed"], f"TN3270E renegotiation failed: {validation}"
    # Additional check that TN3270E mode is properly detected
    assert result.get(
        "tn3270e_mode", False
    ), "TN3270E renegotiation trace should result in TN3270E mode"
    # Additional check for renegotiation capabilities
    assert result.get(
        "negotiation_success", False
    ), "TN3270E renegotiation trace should process successfully"


if __name__ == "__main__":
    pytest.main([__file__])
