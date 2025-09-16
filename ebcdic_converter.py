"""Simple EBCDIC converter for demonstration purposes."""

# Note: This is a simplified implementation for demonstration
# In practice, you would use a library like codecs or py3270

# Simple mapping for demonstration (not complete EBCDIC)
ASCII_TO_EBCDIC = {
    "A": 0xC1,
    "B": 0xC2,
    "C": 0xC3,
    "D": 0xC4,
    "E": 0xC5,
    "F": 0xC6,
    "G": 0xC7,
    "H": 0xC8,
    "I": 0xC9,
    "J": 0xD1,
    "K": 0xD2,
    "L": 0xD3,
    "M": 0xD4,
    "N": 0xD5,
    "O": 0xD6,
    "P": 0xD7,
    "Q": 0xD8,
    "R": 0xD9,
    "S": 0xE2,
    "T": 0xE3,
    "U": 0xE4,
    "V": 0xE5,
    "W": 0xE6,
    "X": 0xE7,
    "Y": 0xE8,
    "Z": 0xE9,
    "0": 0xF0,
    "1": 0xF1,
    "2": 0xF2,
    "3": 0xF3,
    "4": 0xF4,
    "5": 0xF5,
    "6": 0xF6,
    "7": 0xF7,
    "8": 0xF8,
    "9": 0xF9,
    " ": 0x40,
    ".": 0x4B,
    ",": 0x6B,
    "!": 0x5A,
}

EBCDIC_TO_ASCII = {v: k for k, v in ASCII_TO_EBCDIC.items()}


def encode_to_ebcdic(text):
    """Convert ASCII text to EBCDIC byte array."""
    result = bytearray()
    for char in text.upper():
        if char in ASCII_TO_EBCDIC:
            result.append(ASCII_TO_EBCDIC[char])
        else:
            # For unsupported characters, use space as fallback
            result.append(ASCII_TO_EBCDIC[" "])
    return result


def decode_from_ebcdic(ebcdic_bytes):
    """Convert EBCDIC byte array to ASCII text."""
    result = ""
    for byte in ebcdic_bytes:
        if byte in EBCDIC_TO_ASCII:
            result += EBCDIC_TO_ASCII[byte]
        else:
            # For unsupported bytes, use space as fallback
            result += " "
    return result
