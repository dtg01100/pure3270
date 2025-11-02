"""
Error Handling Tests for Trace Replay

Validate that the trace replay framework and parser gracefully detect and report:
- Truncated / malformed hex records
- Non-hex characters in hex records
- Incomplete negotiation sequences (missing WILL/DO)
- Completely missing trace file handling
- Records that trigger parser exceptions

Tests use the existing EnhancedTraceReplay implementation from tools/enhanced_trace_replay.py
by importing it dynamically so tests remain fast and self-contained.
"""

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest


def load_enhanced_replay():
    """Dynamically import EnhancedTraceReplay class from tools/enhanced_trace_replay.py."""
    spec = importlib.util.spec_from_file_location(
        "enhanced_trace_replay",
        Path(__file__).parent.parent / "tools" / "enhanced_trace_replay.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module.EnhancedTraceReplay


@pytest.fixture
def EnhancedReplay():
    return load_enhanced_replay()


def read_lines(path: Path):
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def write_temp_trace(tmp_path: Path, name: str, lines):
    p = tmp_path / name
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_missing_trace_file(EnhancedReplay):
    """Replayer should report an error when trace file does not exist."""
    replay = EnhancedReplay(str(Path("nonexistent.trc")))
    result = replay.replay_and_validate()
    assert not result.success
    assert any(
        "Trace file not found" in e for e in result.errors
    ), "Missing trace file not reported"


def test_truncated_hex_record_detection(tmp_path: Path, EnhancedReplay):
    """Inject a truncated hex record and expect a parse warning/error."""
    src = Path(__file__).parent / "data" / "traces" / "login.trc"
    assert src.exists()
    lines = read_lines(src)
    # Find first '< 0x' hex data line and truncate the hex payload
    modified = []
    truncated = False
    for ln in lines:
        if not truncated and ln.strip().startswith("<") and "0x" in ln:
            # keep header but shorten hex (remove last nibble)
            parts = ln.split()
            # last token typically hex payload
            if len(parts) >= 3:
                hex_payload = parts[-1]
                if len(hex_payload) > 8:
                    hex_payload = hex_payload[
                        :-3
                    ]  # chop off bytes to make it truncated
                    parts[-1] = hex_payload
                    ln = " ".join(parts)
                    truncated = True
        modified.append(ln)
    tmp = write_temp_trace(tmp_path, "truncated_login.trc", modified)
    replay = EnhancedReplay(str(tmp))
    result = replay.replay_and_validate()
    # Either a warning about parsing hex or records_failed > 0
    assert (
        (result.records_failed > 0)
        or any("Could not parse hex data" in w for w in result.warnings)
        or any("parse" in e.lower() for e in result.errors)
    ), "Truncated record not detected as error/warning"


def test_non_hex_characters_in_record(tmp_path: Path, EnhancedReplay):
    """Inject non-hex characters into a hex record to ensure parser warns."""
    src = Path(__file__).parent / "data" / "traces" / "login.trc"
    lines = read_lines(src)
    modified = []
    injected = False
    for ln in lines:
        if not injected and ln.strip().startswith("<") and "0x" in ln:
            parts = ln.split()
            if len(parts) >= 3:
                hex_payload = parts[-1]
                # inject invalid characters into payload
                hex_payload = hex_payload[:10] + "GGHH" + hex_payload[10:]
                parts[-1] = hex_payload
                ln = " ".join(parts)
                injected = True
        modified.append(ln)
    tmp = write_temp_trace(tmp_path, "badhex_login.trc", modified)
    replay = EnhancedReplay(str(tmp))
    result = replay.replay_and_validate()
    # Expect a warning about non-hex data or failed records
    assert (
        (result.records_failed > 0)
        or any("Could not parse hex data" in w for w in result.warnings)
        or any("hex" in e.lower() for e in result.errors)
    ), "Non-hex payload not reported"


def test_incomplete_negotiation_detected(tmp_path: Path, EnhancedReplay):
    """Remove telnet negotiation lines and ensure analyzer notes missing negotiation."""
    src = Path(__file__).parent / "data" / "traces" / "login.trc"
    lines = read_lines(src)
    modified = []
    for ln in lines:
        # drop lines that indicate DO/WILL negotiation to simulate incomplete negotiation
        if any(
            x in ln
            for x in [
                "RCVD DO",
                "SENT WILL",
                "RCVD WILL",
                "SENT DO",
                "Now operating in",
            ]
        ):
            continue
        modified.append(ln)
    tmp = write_temp_trace(tmp_path, "no_negotiation.trc", modified)
    replay = EnhancedReplay(str(tmp))
    result = replay.replay_and_validate()
    # The features detector should mark telnet_negotiation as False
    features = result.features.to_dict()
    assert features.get("telnet_negotiation") in (
        False,
        None,
    ), "Incomplete negotiation not detected"


def test_parser_exception_propagation(tmp_path: Path, EnhancedReplay, monkeypatch):
    """Force DataStreamParser.parse to raise to ensure replay records failure."""
    # Create a minimal valid trace copy
    src = Path(__file__).parent / "data" / "traces" / "login.trc"
    lines = read_lines(src)[:200]  # smaller chunk
    tmp = write_temp_trace(tmp_path, "small_login.trc", lines)
    # Load the module and monkeypatch the DataStreamParser.parse to raise
    spec = importlib.util.spec_from_file_location(
        "enhanced_trace_replay",
        Path(__file__).parent.parent / "tools" / "enhanced_trace_replay.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    Enhanced = mod.EnhancedTraceReplay
    # Monkeypatch DataStreamParser.parse by creating a fake module attribute
    original_import = mod.__dict__.get("DataStreamParser", None)

    class FakeParser:
        def __init__(self, screen):
            pass

        def parse(self, _):
            raise RuntimeError("forced parser failure")

    # Inject FakeParser into the enhanced replay module before instantiation
    mod.DataStreamParser = FakeParser  # type: ignore
    replay = Enhanced(str(tmp))
    result = replay.replay_and_validate()
    # Expect records_failed > 0 and an error message referencing forced parser failure
    assert result.records_failed > 0 or any(
        "forced parser failure" in e.lower() for e in result.errors
    ), "Parser exception not surfaced in replay result"


def test_replay_reports_warnings_and_errors_for_corrupted_trace(
    tmp_path: Path, EnhancedReplay
):
    """Combine multiple corruptions and verify replay reports both warnings and errors."""
    src = Path(__file__).parent / "data" / "traces" / "smoke.trc"
    lines = read_lines(src)
    # Corrupt a couple of hex lines
    for i, ln in enumerate(lines):
        if ln.strip().startswith("<") and "0x" in ln:
            parts = ln.split()
            if len(parts) >= 3:
                parts[-1] = parts[-1][:8] + "ZZ" + parts[-1][8:]
                lines[i] = " ".join(parts)
                break
    # Remove TN3270E marker lines
    lines = [ln for ln in lines if "TN3270E" not in ln]
    tmp = write_temp_trace(tmp_path, "corrupt_smoke.trc", lines)
    replay = EnhancedReplay(str(tmp))
    result = replay.replay_and_validate()
    # Expect mixture of warnings and errors; at minimum, success should be False
    assert not result.success
    assert (
        result.warnings or result.errors
    ), "No warnings/errors reported for corrupted trace"
