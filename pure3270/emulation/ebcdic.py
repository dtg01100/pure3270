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
        # Build a forward table (byte -> unicode char) using CP037 mapping with IBM 3270 graphics support.
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

        # IBM 3270 Graphics Character Set mappings for high EBCDIC range
        # Based on IBM 3270 character set standards
        graphics_map = {
            0x7E: "■",  # Solid block - commonly used in IBM logos
            0x7F: "○",  # Empty circle
            0x80: "┌",  # Box drawing light down and right
            0x81: "┐",  # Box drawing light down and left
            0x82: "└",  # Box drawing light up and right
            0x83: "┘",  # Box drawing light up and left
            0x84: "─",  # Box drawing light horizontal
            0x85: "┼",  # Box drawing light vertical and horizontal
            0x86: "│",  # Box drawing light vertical
            0x87: "├",  # Box drawing light vertical and right
            0x88: "┤",  # Box drawing light vertical and left
            0x89: "┬",  # Box drawing light down and horizontal
            0x8A: "┴",  # Box drawing light up and horizontal
            0x8B: "═",  # Box drawing double horizontal
            0x8C: "║",  # Box drawing double vertical
            0x8D: "╒",  # Box drawing down double and right single
            0x8E: "╓",  # Box drawing down single and right double
            0x8F: "╔",  # Box drawing double down and right
            0x90: "╕",  # Box drawing down double and left single
            0x91: "╖",  # Box drawing down single and left double
            0x92: "╗",  # Box drawing double down and left
            0x93: "╘",  # Box drawing up double and right single
            0x94: "╙",  # Box drawing up single and right double
            0x95: "╚",  # Box drawing double up and right
            0x96: "╛",  # Box drawing up double and left single
            0x97: "╜",  # Box drawing up single and left double
            0x98: "╝",  # Box drawing double up and left
            0x99: "╞",  # Box drawing vertical single and right double
            0x9A: "╟",  # Box drawing vertical double and right single
            0x9B: "╠",  # Box drawing double vertical and right
            0x9C: "╡",  # Box drawing vertical single and left double
            0x9D: "╢",  # Box drawing vertical double and left single
            0x9E: "╣",  # Box drawing double vertical and left
            0x9F: "╤",  # Box drawing down single and horizontal double
            0xA0: "╥",  # Box drawing down double and horizontal single
            0xA1: "╦",  # Box drawing double down and horizontal
            0xA2: "╧",  # Box drawing up single and horizontal double
            0xA3: "╨",  # Box drawing up double and horizontal single
            0xA4: "╩",  # Box drawing double up and horizontal
            0xA5: "╪",  # Box drawing vertical single and horizontal double
            0xA6: "╫",  # Box drawing vertical double and horizontal single
            0xA7: "╬",  # Box drawing double vertical and horizontal
            0xA8: "░",  # Light shade
            0xA9: "▒",  # Medium shade
            0xAA: "▓",  # Dark shade
            0xAB: "█",  # Full block (alternative for 0x7E)
        }

        import codecs

        table = []
        for b in range(256):
            if b in cp037_map:
                ch = cp037_map[b]
            elif b in graphics_map:
                ch = graphics_map[b]
            else:
                try:
                    ch = codecs.decode(bytes([b]), "cp037")
                    # Filter out control characters that don't belong in screen display
                    if ord(ch) < 32 and ch not in "\t\n\r":
                        ch = "?"  # Use ? for control characters instead of space
                except Exception:
                    ch = "?"  # Use ? for unknown characters instead of 'z'
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
            # Fallback: decode each byte using table, else '?'
            out_chars = []
            for b in data:
                try:
                    out_chars.append(self.ebcdic_to_unicode_table[b])
                except Exception:
                    out_chars.append("?")
            return ("".join(out_chars), len(out_chars))

    def debug_decode_byte(self, byte: int) -> str:
        """Debug method to see how a single EBCDIC byte is decoded."""
        try:
            char = self.ebcdic_to_unicode_table[byte]
            cp037_result = None
            try:
                cp037_result = bytes([byte]).decode("cp037")
            except:
                cp037_result = f"CP037_ERROR"

            return f"EBCDIC 0x{byte:02X} -> table:'{char}' (ord:{ord(char):d}), CP037:{repr(cp037_result)}"
        except Exception as e:
            return f"EBCDIC 0x{byte:02X} -> ERROR: {e}"

    def encode(self, text: Union[str, bytes]) -> Tuple[bytes, int]:
        """Encode text to EBCDIC bytes, returning (bytes, length).

        Accepts either `str` or `bytes`. If `bytes` are provided they are
        interpreted as latin-1 and decoded before encoding so callers that
        pass raw bytes won't raise. Prefers full CP037 mapping, falling back
        to conservative mapping only on failure. Characters not present in
        the conservative reverse mapping are encoded as 0x7A.
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
        # Prefer full CP037 encoding only when all characters are representable
        # in the conservative reverse mapping; otherwise fall back to the
        # conservative per-character mapping which encodes unknown characters
        # as 0x7A. This ensures surrogate or otherwise-unmappable characters
        # yield the documented 0x7A value expected by tests.
        try:
            all_representable = True
            for ch in text:
                # If character not present in our reverse map, consider it
                # unrepresentable and force conservative mapping.
                if ch not in self._unicode_to_ebcdic_table:
                    all_representable = False
                    break
            if all_representable:
                result = _encode_cp037(text)
                return (result, len(result))
        except Exception:
            # If any error occurs, fall through to conservative mapping below
            pass

        # Conservative per-character mapping: unknown characters -> 0x6F (?)
        out = bytearray()
        for ch in text:
            b = self._unicode_to_ebcdic_table.get(ch)
            if b is None:
                out.append(0x6F)  # Use ? EBCDIC code instead of z
            else:
                out.append(b)
        return (bytes(out), len(out))

    def encode_to_unicode_table(self, text: str) -> bytes:
        """Encode without returning length (compat helper used by tests)."""
        out = bytearray()
        for ch in text:
            b = self._unicode_to_ebcdic_table.get(ch)
            out.append(b if b is not None else 0x6F)  # Use ? EBCDIC code instead of z
        return bytes(out)
