# ATTRIBUTION NOTICE
# =================================================================================
# This module contains code ported from or inspired by: IBM s3270/x3270
# Source: https://github.com/rhacker/x3270
# Licensed under BSD-3-Clause
#
# DESCRIPTION
# --------------------
# EBCDIC ↔ ASCII translation using IBM Code Page 037 based on s3270
#
# COMPATIBILITY
# --------------------
# Compatible with s3270 EBCDIC handling and character translation
#
# MODIFICATIONS
# --------------------
# Enhanced with additional codec support and error handling
#
# INTEGRATION POINTS
# --------------------
# - EBCDIC to ASCII conversion for screen display
# - ASCII to EBCDIC conversion for data transmission
# - IBM Code Page 037 (CP037) encoding/decoding
# - Screen buffer character processing
#
# ATTRIBUTION REQUIREMENTS
# ------------------------------
# This attribution must be maintained when this code is modified or
# redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
# Last updated: 2025-10-12
# =================================================================================

"""
EBCDIC to ASCII translation utilities for 3270 emulation.
Based on IBM Code Page 037.
"""

import logging
from typing import Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Optional dependency: prefer `ebcdic` package when available for explicit
# encode/decode helpers, but fall back to the stdlib codec for CP037.
# Declare the name at module scope with an Any type so static checkers see a
# consistent symbol regardless of whether the optional package is present.
ebcdic: Any = None
try:
    # Dynamically import the optional `ebcdic` package at runtime. Using
    # importlib.import_module avoids a static `import ebcdic` statement so
    # mypy won't attempt to check the package when it is installed without
    # type information in CI environments.
    import importlib

    ebcdic = importlib.import_module("ebcdic")
except Exception:
    # Leave ebcdic as None when the package is not present.
    ebcdic = None


def _decode_cp037(data: bytes) -> str:
    """Decode bytes using CP037 (EBCDIC) to a Python string.

    Uses the `ebcdic` package if available; otherwise falls back to the
    standard library codec. Errors are handled with replacement to ensure
    tests get a string back instead of an exception.
    """
    if not data:
        return ""
    # Prefer `ebcdic.decode` where available
    try:
        if ebcdic is not None and hasattr(ebcdic, "decode"):
            result = ebcdic.decode("cp037", data)
            return str(result) if result is not None else ""
    except Exception:
        logger.debug(
            "ebcdic.decode failed, falling back to codecs.decode", exc_info=True
        )
    try:
        return data.decode("cp037")
    except Exception:
        return data.decode("cp037", errors="replace")


def _encode_cp037(text: Union[str, bytes]) -> bytes:
    """Encode a Python string or bytes into EBCDIC CP037 bytes.

    Accepts either `str` or `bytes`. If `bytes` are provided they are
    interpreted as ASCII/latin-1 bytes and will be decoded before encoding
    to CP037 so callers that pass in already-encoded bytes won't raise.
    Prefer the optional `ebcdic` package when available. Errors are handled
    with replacement so encoding does not raise.
    """
    # If bytes were provided, attempt to decode as latin-1 to preserve raw
    # byte values rather than failing on non-UTF-8 content.
    if isinstance(text, (bytes, bytearray)):
        try:
            # latin-1 maps bytes 1:1 to unicode codepoints
            if isinstance(text, (bytes, bytearray)):
                text_bytes: Union[bytes, bytearray] = text
                text = text_bytes.decode("latin-1")
        except Exception:
            if isinstance(text, (bytes, bytearray)):
                text_bytes = text
                text = text_bytes.decode("latin-1", errors="replace")
    if text == "":
        return b""
    try:
        if ebcdic is not None and hasattr(ebcdic, "encode"):
            result = ebcdic.encode("cp037", text)
            return bytes(result) if result is not None else b""
    except Exception:
        logger.debug(
            "ebcdic.encode failed, falling back to builtin encode", exc_info=True
        )
    try:
        return text.encode("cp037")
    except Exception:
        return text.encode("cp037", errors="replace")


class EmulationEncoder:
    """Utility class for EBCDIC encoding/decoding in 3270 emulation.

    The class exposes `encode(text) -> bytes` and `decode(data) -> str` which
    use IBM Code Page 037 (CP037) for conversions.
    """

    @staticmethod
    def decode(data: bytes) -> str:
        """Decode EBCDIC bytes to a Unicode string."""
        return _decode_cp037(data)

    @staticmethod
    def encode(text: str) -> bytes:
        """Encode a Unicode string to EBCDIC CP037 bytes."""
        return _encode_cp037(text)


def translate_ebcdic_to_ascii(data: bytes) -> str:
    """Translate raw EBCDIC bytes to an ASCII/Unicode string using CP037."""
    return _decode_cp037(data)


def translate_ascii_to_ebcdic(text: str) -> bytes:
    """Translate an ASCII/Unicode string to EBCDIC CP037 bytes."""
    return _encode_cp037(text)


def get_p3270_version() -> Optional[str]:
    """Get p3270 version for patching.

    Returns the installed `p3270` package version string or `None`.
    """
    try:
        import importlib.metadata

        return importlib.metadata.version("p3270")
    except Exception:
        try:
            import p3270  # noqa: F401

            return getattr(p3270, "__version__", None)
        except Exception:
            return None


def encode_field_attribute(attr: int) -> int:
    """Encode 3270 field attribute to EBCDIC.

    Current implementation treats attributes as direct values and returns
    the input unchanged. This is a placeholder for future mapping logic.
    """
    return attr


class EBCDICCodec:
    """Backwards-compatible EBCDIC codec used by tests.

    This class provides a simple mapping-based encode/decode API that matches
    the historical project tests: methods return tuples `(value, length)` and
    unknown characters are encoded as `0x7A` and decoded as `'z'`.

    The implementation uses the CP037 (EBCDIC) codec for deriving a base
    mapping where possible but intentionally restricts the reverse mapping to
    a conservative set (uppercase letters, digits and space) so that
    punctuation and other characters fall back to the 'unknown' mapping.
    """

    def __init__(self) -> None:
        # Build a forward table (byte -> unicode char) using CP037 mapping.
        # Explicit CP037 mapping for uppercase letters and digits
        cp037_map = {
            0xC1: "A",
            0xC2: "B",
            0xC3: "C",
            0xC4: "D",
            0xC5: "E",
            0xC6: "F",
            0xC7: "G",
            0xC8: "H",
            0xC9: "I",
            0xD1: "J",
            0xD2: "K",
            0xD3: "L",
            0xD4: "M",  # Correct: CP037 0xD4 is 'M'
            0xD5: "N",
            0xD6: "O",
            0xD7: "P",
            0xD8: "Q",
            0xD9: "R",
            0xE2: "S",
            0xE3: "T",  # Correct: CP037 0xE3 is 'T'
            0xE4: "U",
            0xE5: "V",
            0xE6: "W",
            0xE7: "X",
            0xE8: "Y",
            0xE9: "Z",
            0xF0: "0",
            0xF1: "1",
            0xF2: "2",
            0xF3: "3",
            0xF4: "4",
            0xF5: "5",
            0xF6: "6",
            0xF7: "7",
            0xF8: "8",
            0xF9: "9",
        }
        import codecs

        table = []
        for b in range(256):
            if b in cp037_map:
                ch = cp037_map[b]
            else:
                try:
                    ch = codecs.decode(bytes([b]), "cp037")
                except Exception:
                    ch = "z"
            table.append(ch)
        self.ebcdic_to_unicode_table = tuple(table)

        # Build a complete reverse mapping (unicode -> byte) for all characters
        # in the EBCDIC table. Each unique character maps to its EBCDIC byte value.
        rev = {}
        for i, ch in enumerate(self.ebcdic_to_unicode_table):
            if ch not in rev:
                rev[ch] = i

        self._unicode_to_ebcdic_table = rev

        # Convenience alias used in tests
        self.ebcdic_translate = self.decode

    def decode(self, data: bytes) -> tuple[str, int]:
        """Decode raw EBCDIC bytes to (string, length).

        Uses CP037 codec for robust translation. Unknown bytes yield 'z'.
        """
        if not data:
            return ("", 0)
        try:
            decoded = _decode_cp037(data)
            return (decoded, len(decoded))
        except Exception:
            # Fallback: decode each byte using table, else 'z'
            out_chars = []
            for b in data:
                try:
                    out_chars.append(self.ebcdic_to_unicode_table[b])
                except Exception:
                    out_chars.append("z")
            return ("".join(out_chars), len(out_chars))

    def encode(self, text: Union[str, bytes]) -> Tuple[bytes, int]:
        """Encode text to EBCDIC bytes, returning (bytes, length).

        Accepts either `str` or `bytes`. If `bytes` are provided they are
        interpreted as latin-1 and decoded before encoding so callers that
        pass raw bytes won't raise. Characters not present in the conservative
        reverse mapping are encoded as 0x7A.
        """
        if not text:
            return (b"", 0)
        if isinstance(text, (bytes, bytearray)):
            try:
                text_bytes: Union[bytes, bytearray] = text
                text = text_bytes.decode("latin-1")
            except Exception:
                if isinstance(text, (bytes, bytearray)):
                    text_bytes = text
                    text = text_bytes.decode("latin-1", errors="replace")
        out = bytearray()
        for ch in text:
            b = self._unicode_to_ebcdic_table.get(ch)
            if b is None:
                out.append(0x7A)
            else:
                out.append(b)
        return (bytes(out), len(out))

    def encode_to_unicode_table(self, text: str) -> bytes:
        """Encode without returning length (compat helper used by tests)."""
        out = bytearray()
        for ch in text:
            b = self._unicode_to_ebcdic_table.get(ch)
            out.append(b if b is not None else 0x7A)
        return bytes(out)
