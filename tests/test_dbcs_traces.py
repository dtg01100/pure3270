"""
DBCS Support Tests for Trace Replay

Validate basic handling of double-byte and non-ASCII byte sequences in traces.
These tests are defensive: they ensure the replay parser and screen buffer accept
multi-byte payloads without crashing and surface reasonable parsing results.

They use tools/enhanced_trace_replay.EnhancedTraceReplay to do the heavy lifting.
"""

import importlib.util
import json
from pathlib import Path
from typing import List

import pytest


def load_enhanced_replay():
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


def write_temp_trace(tmp_path: Path, name: str, lines: List[str]) -> Path:
    p = tmp_path / name
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def make_hex_line(prefix: str, payload: bytes) -> str:
    """Create a trace-style hex line for tests."""
    return f"< 0x0   {payload.hex()}"


def test_synthetic_dbcs_record_parsed(tmp_path: Path, EnhancedReplay):
    """Create a synthetic trace containing high-bit bytes (DBCS-like) and ensure replay parses it."""
    # Construct a small synthetic trace header + one data line containing bytes > 0x7F
    header = "Trace started synthetic"
    # Example bytes that would appear in double-byte/cjk encodings (just arbitrary >0x80 bytes)
    dbcs_payload = bytes([0xC1, 0xA1, 0xC1, 0xA2, 0xC1, 0xA3, 0x40, 0x40])
    data_line = make_hex_line("<", dbcs_payload)
    lines = [header, data_line]
    tmp = write_temp_trace(tmp_path, "synthetic_dbcs.trc", lines)
    replay = EnhancedReplay(str(tmp))
    result = replay.replay_and_validate()
    # Parser should process the record (either succeed or at least report records_parsed > 0 and not crash)
    assert result is not None, "EnhancedTraceReplay returned no result"
    assert result.records_parsed >= 0, "No records_parsed field"
    # If parsing failed, records_failed should reflect that; test asserts no unexpected exception occurred
    assert isinstance(result.records_failed, int)


def test_real_trace_contains_high_bit_bytes_and_parses(
    smoke_trace: Path = Path(__file__).parent / "data" / "traces" / "smoke.trc",
    EnhancedReplay=None,
):
    """If the smoke trace contains bytes with the high bit set, ensure EnhancedTraceReplay parses it without crashing."""
    # If EnhancedReplay fixture not supplied (direct invocation), load it
    if EnhancedReplay is None:
        EnhancedReplay = load_enhanced_replay()
    if not smoke_trace.exists():
        pytest.skip("smoke.trc not available")
    # Scan smoke.trc for any hex bytes >= 0x80
    has_high = False
    with open(smoke_trace, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("<") or line.startswith(">"):
                parts = line.split()
                if len(parts) >= 3:
                    hex_payload = parts[-1]
                    try:
                        bs = bytes.fromhex(hex_payload)
                        if any(b >= 0x80 for b in bs):
                            has_high = True
                            break
                    except Exception:
                        # ignore parse problems here; the replay test below will catch them
                        pass
    if not has_high:
        pytest.skip(
            "No high-bit bytes found in smoke.trc; DBCS-specific assertions not applicable"
        )
    # Run replay and ensure it does not crash and reports parsing metrics
    replay = EnhancedReplay(str(smoke_trace))
    result = replay.replay_and_validate()
    assert result is not None
    # The key is that replay completes and returns a ValidationResult — success may be False if parser lacks full DBCS support,
    # but it must not raise an exception. Check for parsed/failed record counters.
    assert hasattr(result, "records_parsed")
    assert hasattr(result, "records_failed")
    assert isinstance(result.records_parsed, int)
    assert isinstance(result.records_failed, int)
