#!/usr/bin/env python3
"""
Reusable test server harness helpers.

Provides start_test_server() and stop_test_server() which other test harness
scripts can import to start the workspace's `test_server.py` script in a
subprocess and wait until it's accepting connections.
"""

import os
import socket
import subprocess
import sys
import time
from subprocess import STDOUT
from typing import Any, List, Optional, Union, cast


def start_test_server(
    port: int,
    test_mode: bool = True,
    host: str = "127.0.0.1",
    server_script: Optional[str] = None,
    timeout: float = 15.0,
    mode: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    capture_output: bool = False,
) -> Optional[subprocess.Popen[Any]]:
    """Start the TN3270 test server and wait for it to be ready.

    Returns the subprocess.Popen instance or None on failure/timeouts.
    """
    try:
        if server_script is None:
            server_script = os.path.join(os.path.dirname(__file__), "test_server.py")

        logname = f"test_server_{port}.log"
        lf = open(logname, "a")
        cmd = [sys.executable, server_script, "--host", host, "--port", str(port)]
        # Mode option if provided
        if mode:
            cmd.extend(["--mode", mode])
        else:
            cmd.extend(["--mode", "auto"])

        if test_mode:
            cmd.append("--test-sequence")

        if extra_args:
            cmd.extend(extra_args)

        print(
            f"🔁 Starting local test server (port {port}): {' '.join(cmd)} (log -> {logname})"
        )
        if capture_output:
            proc = cast(
                subprocess.Popen[Any],
                subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                ),
            )
        else:
            proc = subprocess.Popen(cmd, stdout=lf, stderr=STDOUT)

        # wait until server is listening (timeout may be overridden by env)
        env_timeout = os.getenv("PURE3270_TEST_SERVER_TIMEOUT")
        try:
            final_timeout = (
                float(env_timeout) if env_timeout is not None else float(timeout)
            )
        except Exception:
            final_timeout = float(timeout)

        start = time.time()
        while time.time() - start < final_timeout:
            try:
                with socket.create_connection((host, port), timeout=1):
                    print("✅ Test server is accepting connections")
                    return proc
            except Exception:
                time.sleep(0.2)
        print("❌ Timeout waiting for test server to start")
        return None
    except Exception as e:
        print(f"⚠️ Failed to start local test server: {e}")
        return None


def stop_test_server(proc: Optional[subprocess.Popen[Any]]) -> None:
    """Stop the test server process started by start_test_server."""
    if proc is None:
        return

    print("🛑 Stopping local test server")
    # Allow configurable stop timeout
    env_stop = os.getenv("PURE3270_TEST_SERVER_STOP_TIMEOUT")
    try:
        stop_timeout = float(env_stop) if env_stop is not None else 5.0
    except Exception:
        stop_timeout = 5.0

    try:
        proc.terminate()
        proc.wait(timeout=stop_timeout)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            proc.wait(timeout=2)
        except Exception:
            pass
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
