# Tests for negotiation dump collection via TraceReplayServer

import asyncio
import contextlib
import logging
import shutil
import sys
from pathlib import Path
from typing import Optional

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270 import Session
from tools.trace_replay_server import TraceReplayServer

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_negotiation_dump_files_created(tmp_path: Path) -> None:
    trace_file = Path(__file__).parent / "data" / "traces" / "login.trc"
    if not trace_file.exists():
        pytest.skip("Trace file not found: login.trc")

    port = 2339
    dump_dir = tmp_path

    server = TraceReplayServer(
        str(trace_file),
        loop_mode=False,
        trace_replay_mode=True,
        compat_handshake=True,
        dump_negotiation=True,
        dump_dir=str(dump_dir),
    )

    server_task = asyncio.create_task(server.start_server(host="127.0.0.1", port=port))
    await asyncio.sleep(0.05)

    session = Session()
    try:
        await asyncio.wait_for(
            asyncio.to_thread(session.connect, "127.0.0.1", port), timeout=5
        )
        await asyncio.sleep(0.2)
    finally:
        try:
            # Ensure closure of the session
            await asyncio.to_thread(session.close)
        except Exception:
            pass
        server_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await server_task

    # Check dump files
    dumps = list(dump_dir.glob("login_*_send.hex")) + list(
        dump_dir.glob("login_*_recv.hex")
    )
    assert dumps, "Expected negotiation dump files to be present"

    # Ensure at least one send and one recv
    send_files = list(dump_dir.glob("login_*_send.hex"))
    recv_files = list(dump_dir.glob("login_*_recv.hex"))
    assert send_files, "Expected at least one send negotiation dump"
    assert recv_files, "Expected at least one recv negotiation dump"


@pytest.mark.asyncio
async def test_negotiation_dump_contains_iac_tokens(tmp_path: Path) -> None:
    trace_file = Path(__file__).parent / "data" / "traces" / "login.trc"
    if not trace_file.exists():
        pytest.skip("Trace file not found: login.trc")

    port = 2340
    dump_dir = tmp_path

    server = TraceReplayServer(
        str(trace_file),
        loop_mode=False,
        trace_replay_mode=True,
        compat_handshake=True,
        dump_negotiation=True,
        dump_dir=str(dump_dir),
    )

    server_task = asyncio.create_task(server.start_server(host="127.0.0.1", port=port))
    await asyncio.sleep(0.05)

    session = Session()
    try:
        await asyncio.wait_for(
            asyncio.to_thread(session.connect, "127.0.0.1", port), timeout=5
        )
        await asyncio.sleep(0.2)
    finally:
        try:
            await asyncio.to_thread(session.close)
        except Exception:
            pass
        server_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await server_task

    send_files = list(dump_dir.glob("login_*_send.hex"))
    recv_files = list(dump_dir.glob("login_*_recv.hex"))
    assert send_files and recv_files

    # Check for common IAC tokens in each dump
    def contains_iac_token(path: Path, tokens: Optional[list[str]] = None) -> bool:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if tokens is None:
            tokens = ["fffb28", "fffd28", "fffa28", "fffb19", "fffd19"]
        return any(t in content for t in tokens)

    assert any(
        contains_iac_token(p) for p in send_files
    ), "Send dumps should contain IAC tokens"
    assert any(
        contains_iac_token(p) for p in recv_files
    ), "Recv dumps should contain IAC tokens"
