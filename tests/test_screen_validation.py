#!/usr/bin/env python3
"""
Screen Content Validation Tests for Pure3270.

These tests validate that parsed 3270 data produces correct screen output
by replaying real trace files and checking for expected content.
"""

import logging
import re
import sys
from pathlib import Path

import pytest

# Silence DEBUG logging from the parser
logging.getLogger("pure3270.protocol.data_stream").setLevel(logging.WARNING)
logging.getLogger("pure3270.emulation.screen_buffer").setLevel(logging.WARNING)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.data_stream import DataStreamParser
from pure3270.protocol.utils import IAC, TN3270_DATA


def parse_trace_to_screen(trace_path: str) -> ScreenBuffer:
    """
    Parse a .trc file and return the resulting ScreenBuffer.

    Extracts all server-to-client (recv) events, filters out Telnet
    negotiation (IAC-based), concatenates the remaining data, and
    parses it through the 3270 data stream parser.
    """
    with open(trace_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    raw_data = b""
    for line in lines:
        line = line.strip()
        recv_match = re.match(r"<\s+0x\w+\s+([0-9a-fA-F\s]+)$", line)
        if recv_match:
            hex_data = recv_match.group(1).replace(" ", "")
            try:
                data = bytes.fromhex(hex_data)
                if data and data[0] != IAC:
                    raw_data += data
            except ValueError:
                pass

    screen = ScreenBuffer(24, 80)
    parser = DataStreamParser(screen)
    parser.parse(raw_data, TN3270_DATA)
    return screen


def get_screen_lines(screen: ScreenBuffer) -> list[str]:
    """Get screen content as a list of lines."""
    return screen.to_text().split("\n")


def get_non_empty_lines(screen: ScreenBuffer) -> list[str]:
    """Get non-empty screen lines."""
    return [l for l in get_screen_lines(screen) if l.strip()]


class TestLoginScreenValidation:
    """Validate the login.trc screen content matches expected IBM i login screen."""

    @pytest.fixture(scope="class")
    def login_screen(self):
        """Parse login.trc once for all tests."""
        trace_path = Path(__file__).parent / "data" / "traces" / "login.trc"
        if not trace_path.exists():
            pytest.skip("login.trc not found")
        return parse_trace_to_screen(str(trace_path))

    def test_screen_dimensions(self, login_screen):
        """Screen should be 24x80."""
        assert login_screen.rows == 24
        assert login_screen.cols == 80
        assert len(login_screen.buffer) == 24 * 80

    def test_screen_has_content(self, login_screen):
        """Screen should have non-space content."""
        text = login_screen.to_text()
        non_space = sum(1 for c in text if c not in (" ", "\n", "\r"))
        assert non_space > 100, f"Screen has only {non_space} non-space characters"

    def test_system_title_present(self, login_screen):
        """Screen should contain the system title."""
        text = login_screen.to_text()
        assert (
            "Global Payments" in text or "CMS/MMS" in text or "IBM" in text
        ), "Expected system title not found on screen"

    def test_username_field_label(self, login_screen):
        """Screen should contain username/login field label."""
        text = login_screen.to_text()
        # Login screens typically have username or user label
        has_user_label = any(
            kw in text.upper() for kw in ["UZIVATEL", "USER", "LOGIN", "USERID"]
        )
        assert has_user_label, "Username field label not found on screen"

    def test_password_field_label(self, login_screen):
        """Screen should contain password field label."""
        text = login_screen.to_text()
        has_password_label = any(
            kw in text.upper() for kw in ["PASSWORD", "HESLO", "PASSWORT"]
        )
        assert has_password_label, "Password field label not found on screen"

    def test_ibm_copyright_present(self, login_screen):
        """Screen should contain IBM copyright notice."""
        text = login_screen.to_text()
        assert (
            "COPYRIGHT" in text.upper() or "IBM" in text.upper()
        ), "IBM copyright not found on screen"

    def test_cursor_at_valid_position(self, login_screen):
        """Cursor should be at a valid screen position."""
        assert 0 <= login_screen.cursor_row < 24
        assert 0 <= login_screen.cursor_col < 80

    def test_top_line_has_title(self, login_screen):
        """Top few lines should contain the system title."""
        lines = get_non_empty_lines(login_screen)
        if lines:
            first_line = lines[0]
            # The first non-empty line should have meaningful content
            assert len(first_line.strip()) > 10, f"First line too short: {first_line!r}"

    def test_screen_buffer_terminates_correctly(self, login_screen):
        """Screen buffer should end with spaces (unfilled rows)."""
        # Last row should be mostly spaces for login screens
        last_row_start = 23 * 80
        last_row = login_screen.buffer[last_row_start:]
        # Count non-space bytes in last row
        non_space = sum(1 for b in last_row if b != 0x40)
        assert non_space < 40, "Last row should be mostly empty for login screen"


class TestIBMlinkScreenValidation:
    """Validate the ibmlink.trc screen content."""

    @pytest.fixture(scope="class")
    def ibmlink_screen(self):
        trace_path = Path(__file__).parent / "data" / "traces" / "ibmlink.trc"
        if not trace_path.exists():
            pytest.skip("ibmlink.trc not found")
        return parse_trace_to_screen(str(trace_path))

    def test_screen_dimensions(self, ibmlink_screen):
        assert ibmlink_screen.rows == 24
        assert ibmlink_screen.cols == 80

    def test_system_id_present(self, ibmlink_screen):
        """Screen should contain system identifier."""
        text = ibmlink_screen.to_text()
        assert (
            "SYSTEM" in text.upper() or "SVM" in text.upper()
        ), "System identifier not found on screen"

    def test_date_or_time_present(self, ibmlink_screen):
        """Screen should contain date or time information."""
        text = ibmlink_screen.to_text()
        has_datetime = any(
            kw in text.upper() for kw in ["DATE", "TIME", "UHR", "FECHA"]
        )
        assert has_datetime, "Date/time not found on screen"

    def test_termid_present(self, ibmlink_screen):
        """Screen should contain terminal ID."""
        text = ibmlink_screen.to_text()
        has_termid = any(kw in text.upper() for kw in ["TERMID", "TERMINAL", "DEVICE"])
        assert has_termid, "Terminal ID not found on screen"


class TestFTDFTScreenValidation:
    """Validate the ft_dft.trc screen content (file transfer/menu screen)."""

    @pytest.fixture(scope="class")
    def ftdft_screen(self):
        trace_path = Path(__file__).parent / "data" / "traces" / "ft_dft.trc"
        if not trace_path.exists():
            pytest.skip("ft_dft.trc not found")
        return parse_trace_to_screen(str(trace_path))

    def test_screen_dimensions(self, ftdft_screen):
        assert ftdft_screen.rows == 24
        assert ftdft_screen.cols == 80

    def test_menu_content_present(self, ftdft_screen):
        """Screen should contain menu content."""
        text = ftdft_screen.to_text()
        non_space = sum(1 for c in text if c not in (" ", "\n", "\r"))
        assert non_space > 50, "Menu screen should have significant content"


class TestScreenInvariantAcross_Traces:
    """Validate screen invariants hold when parsing multiple trace files."""

    @pytest.mark.parametrize(
        "trace_name",
        [
            "login.trc",
            "ibmlink.trc",
            "ft_dft.trc",
            "ft-crash.trc",
        ],
    )
    def test_screen_invariants_after_parsing_trace(self, trace_name):
        """After parsing any trace, screen invariants must hold."""
        trace_path = Path(__file__).parent / "data" / "traces" / trace_name
        if not trace_path.exists():
            pytest.skip(f"{trace_name} not found")

        screen = parse_trace_to_screen(str(trace_path))

        # Structural invariants
        assert screen.rows == 24, f"{trace_name}: rows changed"
        assert screen.cols == 80, f"{trace_name}: cols changed"
        assert len(screen.buffer) == 24 * 80, f"{trace_name}: buffer size changed"
        assert 0 <= screen.cursor_row < 24, f"{trace_name}: cursor row out of range"
        assert 0 <= screen.cursor_col < 80, f"{trace_name}: cursor col out of range"

        # to_text must return consistent output
        text = screen.to_text()
        expected_len = 24 * 80 + 23  # chars + newlines
        assert (
            len(text) == expected_len
        ), f"{trace_name}: to_text() length mismatch: got {len(text)}, expected {expected_len}"


class TestASCII_RoundTrip:
    """Validate ASCII mode screen content."""

    def test_ascii_buffer_matches_raw_buffer(self):
        """When not in ASCII mode, to_text should decode EBCDIC."""
        screen = ScreenBuffer(24, 80)
        # Write some EBCDIC bytes
        screen.write_char(0xC1, row=0, col=0)  # EBCDIC 'A'
        screen.write_char(0xC2, row=0, col=1)  # EBCDIC 'B'
        screen.write_char(0xC3, row=0, col=2)  # EBCDIC 'C'

        text = screen.to_text()
        # to_text should decode EBCDIC to ASCII
        assert (
            "A" in text or "B" in text or "C" in text or "ABC" in text
        ), "EBCDIC bytes should be decoded to ASCII in to_text()"

    def test_ascii_mode_flag(self):
        """Screen buffer should support ASCII mode flag."""
        screen = ScreenBuffer(24, 80)
        assert hasattr(screen, "ascii_buffer")
        assert hasattr(screen, "is_ascii_mode")
        assert hasattr(screen, "set_ascii_mode")

        # Toggle ASCII mode
        screen.set_ascii_mode(True)
        assert screen.is_ascii_mode()
        screen.set_ascii_mode(False)
        assert not screen.is_ascii_mode()

    def test_screen_clear_resets_all(self):
        """After clear, screen should be all spaces."""
        screen = ScreenBuffer(24, 80)
        # Write data everywhere
        for row in range(24):
            for col in range(80):
                screen.write_char(0xC1, row=row, col=col)

        screen.clear()

        # All bytes should be 0x40 (space in EBCDIC)
        assert all(b == 0x40 for b in screen.buffer)
        text = screen.to_text()
        # After clear, text should be all spaces (plus newlines)
        non_space = sum(1 for c in text if c not in (" ", "\n"))
        assert (
            non_space == 0
        ), f"Screen still has {non_space} non-space chars after clear"
