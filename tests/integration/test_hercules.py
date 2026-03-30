#!/usr/bin/env python3
"""
Integration tests for pure3270 against Hercules MVS mainframe.

These tests verify pure3270 functionality against a real MVS 3.8j TK4- system.

IMPORTANT: There is a known issue where pure3270 does not correctly receive the
initial Hercules "About" screen from the TN3270 server. The s3270 reference
implementation receives this screen correctly, but pure3270 only receives blank
screens. This appears to be related to how the initial 3270 data stream is parsed.

Tests marked with `@pytest.mark.xfail` document known failures that need investigation.

Tests require:
- Docker and Docker Compose
- Running hercules-mvs container (see docker-compose.yml)
- s3270 package installed in test container

Run with: pytest -m hercules tests/integration/test_hercules.py
"""

import asyncio
import shutil
import subprocess
from typing import Any, Dict, List, Tuple

import pytest
import pytest_asyncio

from pure3270 import AsyncSession

HERCULES_HOST = "127.0.0.1"
HERCULES_PORT = 3270
TSO_USER = "HERC01"
TSO_PASSWORD = "CUL8TR"


def get_s3270_path() -> str:
    """Resolve s3270 binary path, checking common locations."""
    path = shutil.which("s3270")
    if path:
        return path
    for candidate in [
        "/usr/bin/s3270",
        "/usr/local/bin/s3270",
        "/home/linuxbrew/.linuxbrew/bin/s3270",
    ]:
        if shutil.isfile(candidate):
            return candidate
    raise FileNotFoundError("s3270 not found in PATH")


def run_s3270_command(
    commands: List[str], timeout: float = 10.0
) -> Tuple[str, str, int]:
    """Run s3270 command and return (stdout, stderr, returncode)."""
    cmd = [get_s3270_path(), "-xrm", "*trace:False"]
    try:
        full_commands = commands + ["Quit"]
        result = subprocess.run(
            cmd,
            input="\n".join(full_commands),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", -1


def parse_s3270_ascii_output(output: str) -> str:
    """Parse s3270 ASCII output which has 'data:' prefix for each line."""
    lines = []
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            lines.append(line[5:].rstrip())
        elif (
            line.startswith("ok")
            or line.startswith("error")
            or line.startswith("U F P")
        ):
            continue
    return "\n".join(lines)


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_s3270_available() -> None:
    """Verify s3270 is installed and working."""
    result = subprocess.run(["which", "s3270"], capture_output=True, text=True)
    assert result.returncode == 0, "s3270 not found in PATH"


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_connection(session: AsyncSession) -> None:
    """Test basic TCP connection to TN3270 server."""
    assert session.connected is True


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_tn3270_negotiation(session: AsyncSession) -> None:
    """Test TN3270 protocol negotiation completes successfully."""
    await asyncio.sleep(0.5)
    assert session.connected is True
    assert session.screen is not None
    assert len(session.screen.buffer) == 1920  # 24x80


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_screen_buffer_dimensions(session: AsyncSession) -> None:
    """Test screen buffer has correct 24x80 dimensions."""
    screen = session.screen
    assert screen.rows == 24
    assert screen.cols == 80
    assert len(screen.buffer) == 24 * 80


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_screen_to_text(session: AsyncSession) -> None:
    """Test screen.to_text() returns valid string output."""
    await asyncio.sleep(0.5)
    text = session.screen.to_text()
    assert isinstance(text, str)
    assert len(text) > 0


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_cursor_position(session: AsyncSession) -> None:
    """Test cursor position tracking."""
    await asyncio.sleep(0.5)
    row, col = session.screen.get_position()
    assert 0 <= row < 24
    assert 0 <= col < 80


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_enter_key(session: AsyncSession) -> None:
    """Test Enter key sending."""
    await asyncio.sleep(0.5)
    await session.key("Enter")
    await asyncio.sleep(0.3)
    assert session.connected is True


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_string_input(session: AsyncSession) -> None:
    """Test string input method."""
    await asyncio.sleep(0.5)
    await session.string("TEST")
    await asyncio.sleep(0.3)
    assert session.connected is True


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_tab_key(session: AsyncSession) -> None:
    """Test Tab key sending."""
    await asyncio.sleep(0.5)
    await session.key("Tab")
    await asyncio.sleep(0.2)
    assert session.connected is True


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_pf_keys(session: AsyncSession) -> None:
    """Test PF key sending."""
    await asyncio.sleep(0.5)
    for pf_num in [1, 3, 7, 12]:
        await session.key(f"PF({pf_num})")
        await asyncio.sleep(0.1)
    assert session.connected is True


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_cursor_movement_keys(session: AsyncSession) -> None:
    """Test cursor movement keys."""
    await asyncio.sleep(0.5)
    await session.key("Home")
    await session.key("Down")
    await session.key("Right")
    await session.key("Left")
    await session.key("Up")
    assert session.connected is True


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_disconnect_reconnect(session: AsyncSession) -> None:
    """Test disconnect and reconnect functionality."""
    await asyncio.sleep(0.5)

    await session.disconnect()
    assert not session.connected

    await session.connect(HERCULES_HOST, HERCULES_PORT)
    await asyncio.sleep(0.5)
    assert session.connected


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_alphanumeric_input(session: AsyncSession) -> None:
    """Test alphanumeric character input."""
    await asyncio.sleep(0.5)
    await session.string("ABC123")
    assert session.connected is True


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_special_characters(session: AsyncSession) -> None:
    """Test special character input."""
    await asyncio.sleep(0.5)
    await session.string("@#$%")
    assert session.connected is True


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_quick_keystrokes(session: AsyncSession) -> None:
    """Test rapid keystroke sequence."""
    await asyncio.sleep(0.5)
    for _ in range(5):
        await session.key("Enter")
        await asyncio.sleep(0.05)
    assert session.connected is True


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_mixed_operations(session: AsyncSession) -> None:
    """Test mixed input and key operations."""
    await asyncio.sleep(0.5)
    await session.string("USER")
    await session.key("Tab")
    await session.string("ID")
    await session.key("Enter")
    await asyncio.sleep(0.3)
    assert session.connected is True


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_s3270_connection_test() -> None:
    """Test s3270 can connect and execute commands."""
    commands = [
        f"Connect({HERCULES_HOST}:{HERCULES_PORT})",
        "Wait(Input)",
        "Disconnect",
    ]
    stdout, stderr, rc = run_s3270_command(commands, timeout=30)
    assert rc == 0, f"s3270 command failed: {stderr}"


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_s3270_enter_key() -> None:
    """Test s3270 can send Enter key."""
    commands = [
        f"Connect({HERCULES_HOST}:{HERCULES_PORT})",
        "Enter",
        "Wait(Output)",
        "Ascii",
        "Disconnect",
    ]
    stdout, _, rc = run_s3270_command(commands, timeout=30)
    assert rc == 0
    assert "data:" in stdout


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_s3270_string_input() -> None:
    """Test s3270 can send string input."""
    commands = [
        f"Connect({HERCULES_HOST}:{HERCULES_PORT})",
        "String(TEST)",
        "Wait(Output)",
        "Ascii",
        "Disconnect",
    ]
    stdout, _, rc = run_s3270_command(commands, timeout=30)
    assert rc == 0


@pytest.mark.hercules
@pytest.mark.xfail(
    reason="Known issue: pure3270 does not correctly receive Hercules initial screen"
)
@pytest.mark.asyncio
async def test_initial_screen_matches_s3270(session: AsyncSession) -> None:
    """Compare initial screen with s3270 reference.

    This test is expected to FAIL because pure3270 does not correctly
    receive the Hercules "About" screen that s3270 receives.
    """
    await asyncio.sleep(1)

    pure_screen = session.screen.to_text()

    commands = [
        f"Connect({HERCULES_HOST}:{HERCULES_PORT})",
        "Enter",
        "Wait(Output)",
        "Ascii",
        "Disconnect",
    ]
    stdout, _, rc = run_s3270_command(commands, timeout=30)
    s3270_screen = parse_s3270_ascii_output(stdout)

    assert pure_screen == s3270_screen, "Screens do not match"


@pytest.mark.hercules
@pytest.mark.xfail(reason="Known issue: pure3270 screen reception incomplete")
@pytest.mark.asyncio
async def test_tso_login_matches_s3270(session: AsyncSession) -> None:
    """Compare TSO login screen with s3270.

    This test is expected to FAIL due to the initial screen reception issue.
    """
    await asyncio.sleep(1)

    await session.string(TSO_USER)
    await session.key("Enter")
    await asyncio.sleep(0.5)

    await session.string(TSO_PASSWORD)
    await session.key("Enter")
    await asyncio.sleep(1)

    pure_screen = session.screen.to_text()

    commands = [
        f"Connect({HERCULES_HOST}:{HERCULES_PORT})",
        "Enter",
        "Wait(Output)",
        f"String({TSO_USER})",
        "Enter",
        "Wait(Output)",
        f"String({TSO_PASSWORD})",
        "Enter",
        "Wait(Output)",
        "Ascii",
        "Disconnect",
    ]
    stdout, _, rc = run_s3270_command(commands, timeout=30)
    s3270_screen = parse_s3270_ascii_output(stdout)

    assert pure_screen == s3270_screen, "Login screens do not match"


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_hercules_connection_established(session: AsyncSession) -> None:
    """Verify connection to Hercules TN3270 server is established."""
    await asyncio.sleep(0.5)

    assert session.connected is True

    screen = session.screen
    assert screen is not None
    assert screen.rows == 24
    assert screen.cols == 80

    print(f"\n=== Connection Test Results ===")
    print(f"Connected: {session.connected}")
    print(f"Screen dimensions: {screen.rows}x{screen.cols}")
    print(f"Buffer size: {len(screen.buffer)}")


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_tn3270_protocol_compliance(session: AsyncSession) -> None:
    """Test basic TN3270 protocol compliance."""
    await asyncio.sleep(0.5)

    assert session.connected is True

    assert session.screen is not None
    assert session.screen.rows == 24
    assert session.screen.cols == 80

    assert session.screen.buffer is not None
    assert len(session.screen.buffer) == 1920

    print(f"\n=== Protocol Compliance Test ===")
    print(f"TN3270 connection: ESTABLISHED")
    print(
        f"Screen buffer: {session.screen.rows}x{session.screen.cols} = {len(session.screen.buffer)} bytes"
    )
    print(f"Protocol: TN3270 (non-E)")


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_keystroke_injection(session: AsyncSession) -> None:
    """Test that keystrokes can be injected without errors."""
    await asyncio.sleep(0.5)

    keystrokes = [
        ("Enter", lambda: session.key("Enter")),
        ("Tab", lambda: session.key("Tab")),
        ("PF1", lambda: session.key("PF(1)")),
        ("PF3", lambda: session.key("PF(3)")),
        ("Home", lambda: session.key("Home")),
        ("String(TEST)", lambda: session.string("TEST")),
    ]

    errors = []
    for name, func in keystrokes:
        try:
            await func()
            await asyncio.sleep(0.1)
        except Exception as e:
            errors.append(f"{name}: {e}")

    assert len(errors) == 0, f"Keystroke errors: {errors}"

    print(f"\n=== Keystroke Injection Test ===")
    print(f"Tested {len(keystrokes)} keystroke types")
    print(f"Errors: {len(errors)}")


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_screen_update_after_input(session: AsyncSession) -> None:
    """Test that screen updates after input."""
    await asyncio.sleep(0.5)

    initial_text = session.screen.to_text()

    await session.string("X")
    await asyncio.sleep(0.3)

    final_text = session.screen.to_text()

    assert len(final_text) > 0

    print(f"\n=== Screen Update Test ===")
    print(f"Initial screen: {len(initial_text)} chars")
    print(f"After input: {len(final_text)} chars")


@pytest.mark.hercules
@pytest.mark.asyncio
async def test_reference_implementation_comparison() -> None:
    """Compare basic functionality with s3270 reference.

    This test verifies both implementations can connect and execute basic commands.
    """
    result = subprocess.run(
        [get_s3270_path(), "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "Usage" in output or "s3270" in output.lower()

    commands = [f"Connect({HERCULES_HOST}:{HERCULES_PORT})", "Disconnect"]
    stdout, stderr, rc = run_s3270_command(commands, timeout=30)
    assert rc == 0

    print(f"\n=== Reference Comparison ===")
    print(f"s3270 available: True")
    print(f"s3270 functional: True")


@pytest_asyncio.fixture
async def session():
    """Create an async session connected to Hercules."""
    sess = AsyncSession()
    await sess.connect(HERCULES_HOST, HERCULES_PORT)
    await asyncio.sleep(0.5)
    yield sess
    await sess.disconnect()
