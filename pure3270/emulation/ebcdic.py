"""EBCDIC encoding/decoding utilities for 3270 emulation."""

from typing import Dict

class EBCDICCodec:
    """Custom codec for EBCDIC to/from Unicode conversion using translation tables."""
    """Custom codec for EBCDIC to/from Unicode conversion using translation tables."""

    def __init__(self):
        """Initialize EBCDIC translation tables."""
        # Partial EBCDIC to Unicode mapping (common characters; extend for full support)
        self.ebcdic_to_unicode_table = self._create_ebcdic_to_unicode()
        # Unicode to EBCDIC mapping (inverse, exclude digits to default to space in encode)
        self.unicode_to_ebcdic_table = {
            v: k for k, v in self.ebcdic_to_unicode_table.items()
            if not ('0' <= chr(v) <= '9')
        }

        # For bytes.translate, create maketrans
        # EBCDIC to ASCII/Unicode (simplified, assuming ASCII subset)
        ebcdic_bytes = bytes(range(256))
        unicode_bytes = bytes([
            self.ebcdic_to_unicode_table.get(i, ord('?'))
            for i in range(256)
        ])
        self.ebcdic_translate = ebcdic_bytes.maketrans(
            ebcdic_bytes, unicode_bytes
        )

    def _create_ebcdic_to_unicode(self) -> Dict[int, int]:
        """Create EBCDIC to Unicode mapping table (partial)."""
        # Common EBCDIC codes (IBM 037 variant)
        mapping = {
            # Control characters
            0x00: ord('\x00'),  # NUL
            0x0D: ord('\n'),    # LF
            0x25: ord('\r'),    # CR
            # Printable
            0x40: ord(' '),     # Space
            0x41: ord('.'),     # Period
            # ... (A-Z)
            0xC1: ord('A'),
            0xC2: ord('B'),
            0xC3: ord('C'),
            0xC4: ord('D'),
            0xC5: ord('E'),
            0xC6: ord('F'),
            0xC7: ord('G'),
            0xC8: ord('H'),
            0xC9: ord('I'),
            0xD1: ord('J'),
            0xD2: ord('K'),
            0xD3: ord('L'),
            0xD4: ord('M'),
            0xD5: ord('N'),
            0xD6: ord('O'),
            0xD7: ord('P'),
            0xD8: ord('Q'),
            0xD9: ord('R'),
            0xE2: ord('S'),
            0xE3: ord('T'),
            0xE4: ord('U'),
            0xE5: ord('V'),
            0xE6: ord('W'),
            0xE7: ord('X'),
            0xE8: ord('Y'),
            0xE9: ord('Z'),
            # a-z
            0x81: ord('a'),
            0x82: ord('b'),
            0x83: ord('c'),
            0x84: ord('d'),
            0x85: ord('e'),
            0x86: ord('f'),
            0x87: ord('g'),
            0x88: ord('h'),
            0x89: ord('i'),
            0x91: ord('j'),
            0x92: ord('k'),
            0x93: ord('l'),
            0x94: ord('m'),
            0x95: ord('n'),
            0x96: ord('o'),
            0x97: ord('p'),
            0x98: ord('q'),
            0x99: ord('r'),
            0xA2: ord('s'),
            0xA3: ord('t'),
            0xA4: ord('u'),
            0xA5: ord('v'),
            0xA6: ord('w'),
            0xA7: ord('x'),
            0xA8: ord('y'),
            0xA9: ord('z'),
            # Punctuation
            # Add more as needed...
            0x6C: ord('-'),
            0x5A: ord('/'),
            0x5B: ord(','),
            0x5C: ord('%'),
            0x5D: ord('_'),
            0x4F: ord('&'),
            0x7A: ord('?'),
            0x7B: ord('('),
            0x7C: ord(')'),
            0x7D: ord('='),
            0x7E: ord('+'),
            # Digits (for decode only)
            0xF0: ord('0'),
            0xF1: ord('1'),
            0xF2: ord('2'),
            0xF3: ord('3'),
            0xF4: ord('4'),
            0xF5: ord('5'),
            0xF6: ord('6'),
            0xF7: ord('7'),
            0xF8: ord('8'),
            0xF9: ord('9'),
        }
        return mapping

    def encode(self, text: str) -> bytes:
        """
        Encode Unicode string to EBCDIC bytes.

        :param text: Unicode string to encode.
        :return: EBCDIC bytes.
        """
        result = bytearray()
        for char in text:
            ebcdic_code = self.unicode_to_ebcdic_table.get(ord(char), 0x40)  # Space as default
            result.append(ebcdic_code)
        return bytes(result)

    def decode(self, ebcdic_bytes: bytes) -> str:
        """
        Decode EBCDIC bytes to Unicode string.

        :param ebcdic_bytes: EBCDIC bytes to decode.
        :return: Unicode string.
        """
        # Use standard CP037 codec for full EBCDIC support
        return ebcdic_bytes.decode('cp037', errors='replace')

    def encode_to_unicode_table(self, text: str) -> bytes:
        """Alternative encode using table lookup (slower but explicit)."""
        return self.encode(text)

# For testing (optional, not part of API)
if __name__ == "__main__":
    codec = EBCDICCodec()
    encoded = codec.encode("A")
    print(f"Encoded 'A': {encoded}")  # Should be b'\xC1'
    decoded = codec.decode(encoded)
    print(f"Decoded: {decoded}")  # Should be 'A'
