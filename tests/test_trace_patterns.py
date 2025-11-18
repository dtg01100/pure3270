import asyncio
import shutil
import time

import pytest

from mock_server.tn3270_mock_server import EnhancedTN3270MockServer
from pure3270 import Session


@pytest.mark.timeout(8)
def test_pure3270_server_trace_contains_expected_sequence():
    server = EnhancedTN3270MockServer(requested_device_type="IBM-3279-2-E")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.start())
    try:
        s = Session()
        s.open(server.host, server.port)
        deadline = time.time() + 5
        while time.time() < deadline and not s.tn3270e_mode:
            time.sleep(0.05)
        trace = server.get_sent_trace()
        # Flatten for simple substring search
        combined = b"".join(trace)
        assert b"\xff\xfb\x18" in combined  # WILL TTYPE
        assert b"\xff\xfb\x19" in combined  # WILL EOR
        assert b"\xff\xfb(" in combined  # WILL TN3270E
        # Validate that the Functions REQUEST payload (Type 0x03, Request 0x07) is present with our advertised bitmap
        assert (
            b"\xff\xfa(\x03\x07\x01\x02\x03" in combined
        )  # FUNCTIONS REQUEST with advertised bit flags
        s.close()
    finally:
        loop.run_until_complete(server.stop())
        loop.close()


@pytest.mark.timeout(8)
@pytest.mark.skipif(shutil.which("s3270") is None, reason="s3270 binary not available")
def test_optional_s3270_trace_pattern():
    server = EnhancedTN3270MockServer()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.start())
    try:
        # Launch s3270 client
        import subprocess

        proc = subprocess.Popen(
            ["s3270", f"{server.host}:{server.port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(0.5)
        trace = server.get_sent_trace()
        combined = b"".join(trace)
        assert b"\xff\xfb\x18" in combined
        assert b"\xff\xfb\x19" in combined
        assert b"\xff\xfb(" in combined
        proc.terminate()
    finally:
        loop.run_until_complete(server.stop())
        loop.close()
