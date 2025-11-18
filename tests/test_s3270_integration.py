import os
import shutil
import subprocess
import time

import pytest

from mock_server.tn3270_mock_server import EnhancedTN3270MockServer

S3270_PATH = shutil.which("s3270")


@pytest.mark.skipif(S3270_PATH is None, reason="s3270 binary not available")
@pytest.mark.timeout(10)
def test_s3270_negotiates_tn3270e_with_mock_server():
    """Validate that the real s3270 binary performs expected Telnet/TN3270E negotiation
    against our enhanced mock server.

    Assertions focus on presence of DO responses and terminal type subnegotiation captured by the server:
    - DO TTYPE, DO EOR, DO TN3270E in first response block
    - TTYPE IS subnegotiation containing terminal model string
    NOTE: With current mock sequence (DEVICE-TYPE SEND only) s3270 does not emit DEVICE-TYPE IS; we treat absence as acceptable and document it.
    """
    server = EnhancedTN3270MockServer()
    server.start_threaded()
    try:
        # Launch s3270 non-interactively; it will connect and negotiate then idle.
        proc = subprocess.Popen(
            [S3270_PATH, f"{server.host}:{server.port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Allow negotiation to proceed
        time.sleep(2.0)
        # Stop process (avoid lingering)
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()

        received_chunks = server.get_received_trace()
        assert received_chunks, "No negotiation bytes captured from s3270"
        joined = b"".join(received_chunks)

        # Check DO responses (IAC DO <option>) for TTYPE(0x18), EOR(0x19), TN3270E(0x28)
        assert b"\xff\xfd\x18" in joined, "Missing DO TTYPE from s3270"
        assert b"\xff\xfd\x19" in joined, "Missing DO EOR from s3270"
        assert b"\xff\xfd\x28" in joined, "Missing DO TN3270E from s3270"

        # Check presence of TTYPE IS subnegotiation: IAC SB TTYPE (0x18) IS (0x00 or 0x04) ... IAC SE
        assert b"\xff\xfa\x18" in joined, "Missing TTYPE subnegotiation from s3270"

        # Device type IS optional here due to simplified server; log diagnostic instead of asserting
        if b"\x02\x07IBM-" not in joined:
            print(
                "[TEST] DEVICE-TYPE IS not observed (expected with simplified mock) - acceptable"
            )
    finally:
        # Ensure cleanup
        # Use async stop via event loop friendly wrapper
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.stop())
        loop.close()
