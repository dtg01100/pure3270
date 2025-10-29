#!/usr/bin/env python3
"""
Compare Pure3270 behavior against the real s3270 by replaying a trace.

This harness:
- Starts the local TraceReplayServer on 127.0.0.1:<port>
- Connects using pure3270.Session, captures screen text
- Connects using the real s3270 binary (NOT our bin/s3270 wrapper), captures ASCII screen
- Produces a unified diff and basic stats

Usage:
    python tools/compare_replay_with_s3270.py --trace tests/data/traces/smoke.trc --port 23240
    python tools/compare_replay_with_s3270.py --trace tests/data/traces/login.trc --port 23241

Notes:
- If the real s3270 binary is not available (e.g., /usr/bin/s3270), the comparison will
  skip that side and report availability status. You can specify a path explicitly with
  --s3270-path.
- This script never invokes the repo's bin/s3270 wrapper.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import difflib
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pure3270 import AsyncSession, Session  # noqa: E402
from tools.trace_replay_server import TraceReplayServer  # noqa: E402

logger = logging.getLogger("compare_replay")


def _is_wrapper_script(path: Path) -> bool:
    """Heuristic: detect our repo's Python wrapper script masquerading as s3270.

    We consider it a wrapper if:
      - It exists and is a text file starting with a python shebang, and
      - Contains 'from pure3270.session import Session'
    """
    try:
        if not path.exists() or not path.is_file():
            return False
        # Small files are text; read a bit
        text = path.read_text(errors="ignore")
        if "from pure3270.session import Session" in text:
            return True
        # Also consider any file under the repo's bin/ as a wrapper
        try:
            return str(path).startswith(str(ROOT / "bin"))
        except Exception:
            return False
    except Exception:
        return False


def find_real_s3270(user_path: Optional[str]) -> Optional[Path]:
    """Locate a real s3270 binary, avoiding the repo's wrapper.

    Search order:
      1) --s3270-path if provided (must not be the wrapper)
      2) $S3270_PATH environment variable
      3) shutil.which('s3270')
      4) Common locations: /usr/bin/s3270, /usr/local/bin/s3270
    """
    candidates = []
    if user_path:
        candidates.append(Path(user_path))
    env_path = os.environ.get("S3270_PATH")
    if env_path:
        candidates.append(Path(env_path))
    which = shutil.which("s3270")
    if which:
        candidates.append(Path(which))
    candidates.extend([Path("/usr/bin/s3270"), Path("/usr/local/bin/s3270")])

    for c in candidates:
        if c and c.exists() and c.is_file() and not _is_wrapper_script(c):
            return c
    return None


async def run_pure3270_capture(
    host: str, port: int, delay: float = 1.0, is_printer: bool = False
) -> str:
    """Connect with pure3270.AsyncSession and return screen text after delay.

    Using AsyncSession ensures cooperative cancellation and clean shutdown
    when a timeout occurs.
    """
    # Use appropriate terminal type based on session type
    terminal_type = "IBM-3278-4"
    if is_printer:
        terminal_type = "IBM-3278-2"  # Printer sessions use different default

    async with AsyncSession(terminal_type=terminal_type) as session:
        await session.connect(host, port)
        await asyncio.sleep(delay)
        # Access the screen buffer via async session
        text = session.screen_buffer.to_text()
        return text


async def run_real_s3270_capture(
    s3270_path: Path,
    host: str,
    port: int,
    delay: float = 1.0,
    model: str = "3278-4-E",
) -> Tuple[str, str]:
    """Connect with the real s3270 and return (stdout, stderr) content from Ascii().

    We drive the program in -script mode and send well-known actions. We avoid any commands
    specific to our wrapper script; these are x3270/s3270 standard actions.
    """
    # Prefer action syntax with parentheses, which s3270 supports.
    # We include a Wait() to give the replay time to deliver the first screen.
    commands = [
        f"Connect({host}:{port})",
        f"Wait({max(0.1, delay):.2f},Output)",
        "Ascii()",
        "Quit()",
    ]
    proc = await asyncio.create_subprocess_exec(
        str(s3270_path),
        "-model",
        model,
        "-script",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        assert proc.stdin is not None
        stdin_bytes = ("\n".join(commands) + "\n").encode("utf-8")
        out, err = await proc.communicate(input=stdin_bytes)
        # Decode as UTF-8, replacing errors to keep comparison robust
        stdout_text = out.decode("utf-8", errors="replace")
        stderr_text = err.decode("utf-8", errors="replace")
        return stdout_text, stderr_text
    except asyncio.CancelledError:
        # Ensure the child process is terminated if our caller cancels (timeout)
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        raise


def normalize_screen_text(text: str) -> str:
    """Normalize whitespace for fair comparisons."""
    # Replace Windows newlines, trim trailing spaces per line
    lines = [
        ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    # Drop leading/trailing empty lines
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


async def compare_trace(
    trace_path: Path,
    port: int,
    s3270_path: Optional[Path],
    delay: float = 1.0,
    s3270_model: str = "3278-4-E",
    compat_handshake: bool = False,
    capture_timeout: float = 180.0,
) -> int:
    """Run comparison for a single trace. Returns 0 if identical (or if s3270 missing), 1 if differs."""
    logger.info("Starting TraceReplayServer for %s on port %d", trace_path, port)
    server = TraceReplayServer(
        str(trace_path), loop_mode=False, compat_handshake=compat_handshake
    )

    # Start server as a background task
    server_task = asyncio.create_task(server.start_server(host="127.0.0.1", port=port))
    await asyncio.sleep(0.15)

    try:
        # Capture from pure3270 with timeout
        # Detect printer sessions from trace name (smoke.trc is a known printer session)
        is_printer_session = trace_path.name == "smoke.trc"
        logger.info(
            "Capturing screen from pure3270... (printer=%s)", is_printer_session
        )
        try:
            p_screen = await asyncio.wait_for(
                run_pure3270_capture(
                    "127.0.0.1", port, delay=delay, is_printer=is_printer_session
                ),
                timeout=capture_timeout,
            )
        except asyncio.TimeoutError:
            logger.error("pure3270 capture timed out")
            return 1
        p_norm = normalize_screen_text(p_screen)

        # Capture from real s3270 if available
        if s3270_path is None:
            logger.warning("Real s3270 not found; skipping reference comparison.")
            print("[INFO] pure3270 screen (normalized):\n" + p_norm)
            return 0

        logger.info(
            "Capturing screen from real s3270 at %s (model %s)...",
            s3270_path,
            s3270_model,
        )
        try:
            s_out, s_err = await asyncio.wait_for(
                run_real_s3270_capture(
                    s3270_path, "127.0.0.1", port, delay=delay, model=s3270_model
                ),
                timeout=capture_timeout,
            )
        except asyncio.TimeoutError:
            logger.error("s3270 capture timed out")
            return 1

        # Extract only screen lines from s3270 output. In script mode, ASCII() typically
        # emits lines prefixed with 'data:'. Ignore status lines like 'U F U C(...)' and 'ok'.
        s_lines = []
        for ln in s_out.splitlines():
            if ln.startswith("data:"):
                # Keep text after the prefix (strip single leading space if present)
                payload = ln[len("data:") :]
                if payload.startswith(" "):
                    payload = payload[1:]
                s_lines.append(payload)
        s_text = "\n".join(s_lines) if s_lines else s_out
        s_norm = normalize_screen_text(s_text)

        # Compare
        if p_norm == s_norm:
            print(f"[OK] Screens match for {trace_path.name}")
            return 0

        print(f"[DIFF] Screens differ for {trace_path.name}")
        diff = difflib.unified_diff(
            s_norm.splitlines(),
            p_norm.splitlines(),
            fromfile="s3270",
            tofile="pure3270",
            lineterm="",
        )
        for line in diff:
            print(line)
        return 1
    finally:
        # Stop server
        try:
            server_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await server_task
        except Exception:
            pass


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Compare pure3270 vs s3270 under trace replay"
    )
    ap.add_argument("--trace", required=True, help="Path to .trc file")
    ap.add_argument(
        "--port", type=int, default=23230, help="Port for local replay server"
    )
    ap.add_argument(
        "--delay", type=float, default=1.0, help="Seconds to wait before capture"
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Seconds to allow for each capture step before timing out (default: 180)",
    )
    ap.add_argument(
        "--s3270-path",
        default=None,
        help="Path to real s3270 binary (not repo wrapper)",
    )
    ap.add_argument(
        "--s3270-model",
        default="3278-4-E",
        help="Model to pass to s3270 via -model (default: 3278-4-E)",
    )
    ap.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    ap.add_argument(
        "--compat-handshake",
        action="store_true",
        help="Enable RFC-aligned compatibility handshake in replay server",
    )
    ap.add_argument(
        "--overall-timeout",
        type=float,
        default=240.0,
        help="Hard timeout (seconds) for the entire comparison, including server startup and both captures (default: 240)",
    )
    return ap.parse_args(argv)


async def amain(ns: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.DEBUG if ns.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    trace_path = Path(ns.trace).resolve()
    if not trace_path.exists():
        print(f"Trace not found: {trace_path}", file=sys.stderr)
        return 2

    real = find_real_s3270(ns.s3270_path)
    if real is None:
        logger.warning(
            "Real s3270 binary not found. Set --s3270-path or S3270_PATH if installed."
        )
    else:
        logger.info("Using real s3270 at: %s", real)

    try:
        rc = await asyncio.wait_for(
            compare_trace(
                trace_path,
                ns.port,
                real,
                delay=ns.delay,
                s3270_model=ns.s3270_model,
                compat_handshake=ns.compat_handshake,
                capture_timeout=ns.timeout,
            ),
            timeout=ns.overall_timeout,
        )
    except asyncio.TimeoutError:
        logger.error("Overall comparison timed out after %.1fs", ns.overall_timeout)
        return 3
    return rc


def main(argv: Optional[list[str]] = None) -> int:
    ns = parse_args(argv)
    return asyncio.run(amain(ns))


if __name__ == "__main__":
    sys.exit(main())
