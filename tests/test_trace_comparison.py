import asyncio
import shutil
import subprocess
import time

import pytest

from mock_server.tn3270_mock_server import EnhancedTN3270MockServer
from pure3270 import Session

S3270_PATH = shutil.which("s3270")


@pytest.mark.skipif(S3270_PATH is None, reason="s3270 binary not available")
@pytest.mark.timeout(15)
def test_trace_comparison_pure3270_vs_s3270():
    # Start server for pure3270
    server_pure = EnhancedTN3270MockServer(port=23270)
    server_pure.start_threaded()
    try:
        s = Session()
        s.open(server_pure.host, server_pure.port)
        deadline = time.time() + 5
        while time.time() < deadline and not s.tn3270e_mode:
            time.sleep(0.05)
        s.close()
        pure_received = b"".join(server_pure.get_received_trace())
    finally:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server_pure.stop())
        loop.close()

    # Start server for s3270
    server_s = EnhancedTN3270MockServer(port=23271)
    server_s.start_threaded()
    try:
        proc = subprocess.Popen(
            [S3270_PATH, f"{server_s.host}:{server_s.port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(2.0)
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        s3270_received = b"".join(server_s.get_received_trace())
    finally:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server_s.stop())
        loop.close()

    # Basic common checks for both traces
    assert b"\xff\xfd\x18" in pure_received, "Missing DO TTYPE from pure3270"
    assert b"\xff\xfd\x18" in s3270_received, "Missing DO TTYPE from s3270"
    assert b"\xff\xfd\x19" in pure_received, "Missing DO EOR from pure3270"
    assert b"\xff\xfd\x19" in s3270_received, "Missing DO EOR from s3270"
    assert b"\xff\xfd\x28" in pure_received, "Missing DO TN3270E from pure3270"
    assert b"\xff\xfd\x28" in s3270_received, "Missing DO TN3270E from s3270"
    assert (
        b"\xff\xfa\x18" in pure_received
    ), "Missing TTYPE subnegotiation from pure3270"
    assert b"\xff\xfa\x18" in s3270_received, "Missing TTYPE subnegotiation from s3270"
    # Check that at least one DEVICE-TYPE/ TN3270E related payload or DO was sent to both
    assert any(
        p in pure_received for p in (b"\xff\xfa\x28", b"\xff\xfd\x28", b"\xff\xfb\x28")
    ), "Missing TN3270E subnegotiation/DO/WILL from pure3270"
    assert any(
        p in s3270_received for p in (b"\xff\xfa\x28", b"\xff\xfd\x28", b"\xff\xfb\x28")
    ), "Missing TN3270E subnegotiation/DO/WILL from s3270"
