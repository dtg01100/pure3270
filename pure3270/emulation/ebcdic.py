"""
EBCDIC to ASCII translation utilities for 3270 emulation.
Based on IBM Code Page 037.
"""

import logging
from typing import Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Optional dependency: prefer `ebcdic` package when available for explicit
# encode/decode helpers, but fall back to the stdlib codec for CP037.
try:
    import ebcdic  # type: ignore[import-untyped]
except Exception:
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
            import p3270  # type: ignore[import-untyped]

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
        # Build a forward table (byte -> unicode char). Prefer the cp037
        # decoder but normalize non-printable/unmapped results to 'z', except
        # for the NUL (0x00) byte which should remain as '\x00'.
        table = []
        for b in range(256):
            ch = _decode_cp037(bytes([b]))
            if ch == "\x00" or (len(ch) == 1 and 0x20 <= ord(ch) <= 0x7E):
                table.append(ch)
            else:
                table.append("z")
        self.ebcdic_to_unicode_table = tuple(table)

        # Build a conservative reverse mapping (unicode -> byte) for the
        # characters tests expect to round-trip: uppercase letters, digits,
        # space, and common punctuation. Any other character will be treated
        # as unknown and map to 0x7A.
        allowed = set(
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !@#$%^&*()_+-=[]{}|;:",./<>?'
        )
        rev = {}
        for i, ch in enumerate(self.ebcdic_to_unicode_table):
            if ch in allowed and ch not in rev:
                rev[ch] = i
        # Allow lowercase letters to map to same byte as uppercase if present
        for upper in list(rev.keys()):
            if upper.isalpha():
                rev[upper.lower()] = rev[upper]

        self._unicode_to_ebcdic_table = rev

        # Convenience alias used in tests
        self.ebcdic_translate = self.decode

    def decode(self, data: bytes) -> tuple[str, int]:
        """Decode raw EBCDIC bytes to (string, length).

        Unknown or non-printable bytes yield the character 'z' (per tests).
        """
        if not data:
            return ("", 0)
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
