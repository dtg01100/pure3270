import base64
import json
from pathlib import Path

from pure3270.emulation.ebcdic import translate_ebcdic_to_ascii


def _load_archive_json(name: str) -> dict:
    p = Path("archives/test-artifacts-20251109") / name
    return json.loads(p.read_text())


def test_translate_pure3270_archived_raw_bytes():
    """Decode pure3270 archived raw bytes and ensure translation contains expected phrases."""
    data = _load_archive_json("pure3270_script_results.json")
    # Find any screenshot with raw_base64
    raw_entry = None
    for s in data.get("screenshots", []):
        if "raw_base64" in s:
            raw_entry = s
            break
    assert raw_entry is not None, "No raw_base64 entry in archived pure3270 data"
    raw = base64.b64decode(raw_entry["raw_base64"])
    text = translate_ebcdic_to_ascii(raw)
    # Ensure we decoded some content and preserved the typed username
    assert len(text) > 0
    assert "testuser" in text
    # The raw file contains initial ASCII header; verify via latin-1/ascii decode
    ascii_decoded = raw.decode("latin-1", errors="replace")
    assert "Connected" in ascii_decoded or "connected" in ascii_decoded
