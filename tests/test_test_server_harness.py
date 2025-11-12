import os
import socket
import subprocess
import types
from unittest import mock

import pytest

from test_server_harness import start_test_server, stop_test_server


class DummyProc:
    def __init__(self, stdout=None):
        self.stdout = stdout
        self.terminated = False
        self.killed = False
        self.returncode = None

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        # simulate immediate termination
        self.returncode = 0
        return 0


def test_start_test_server_success(monkeypatch, tmp_path):
    # Simulate socket.create_connection succeeding after some attempts
    calls = {"count": 0}

    def fake_create_connection(addr, timeout=1):
        calls["count"] += 1
        if calls["count"] >= 1:

            class Conn:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            return Conn()  # success (context manager-like)
        raise OSError()

    dummy = DummyProc(stdout=mock.Mock())

    def fake_popen(*_args, **_kwargs):
        return dummy

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    proc = start_test_server(9999, test_mode=False, host="127.0.0.1", timeout=1)
    assert proc is dummy

    # cleanup
    stop_test_server(proc)
    assert dummy.terminated or dummy.killed


def test_start_test_server_timeout(monkeypatch):
    # socket.create_connection always fails
    def fake_create_connection(addr, timeout=1):
        raise OSError("no connect")

    def fake_popen(*_args, **_kwargs):
        return DummyProc()

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    # short timeout
    proc = start_test_server(9998, test_mode=False, host="127.0.0.1", timeout=0.5)
    assert proc is None


def test_stop_test_server_timeout(monkeypatch):
    # simulate a process that doesn't stop on terminate
    class SlowProc(DummyProc):
        def wait(self, timeout=None):
            raise subprocess.TimeoutExpired(cmd="proc", timeout=timeout)

    slow = SlowProc()

    monkeypatch.setenv("PURE3270_TEST_SERVER_STOP_TIMEOUT", "0.01")

    # should not raise
    stop_test_server(slow)
    # if kill attempted, killed flag may be True
    assert slow.killed or slow.terminated
