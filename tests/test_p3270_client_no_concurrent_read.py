import pytest


def test_enter_does_not_raise_when_screen_buffer_present():
    """Verify that sending Enter via P3270Client doesn't cause read() concurrency errors
    when screen_buffer is present. This test simulates a _pure_session object
    with a screen_buffer and ensures _sendCommand's update path doesn't call
    into a conflicting read.
    """
    from pure3270.p3270_client import P3270Client

    class DummyBuffer:
        @property
        def ascii_buffer(self):
            return ""  # Safe property

    class DummySession:
        def __init__(self):
            self.screen_buffer = DummyBuffer()

        def send(self, data):
            # no-op
            pass

        def string(self, text):
            self.send(text.encode())

    client = P3270Client()
    client._pure_session = DummySession()
    client._connected = True

    # Should not raise
    client.sendEnter()
    # Also ensure other navigation keys are safe
    client.sendTab()
    client.sendPF(1)


def test_enter_does_not_invoke_read_when_screen_buffer_present():
    """Ensure that _sendCommand uses screen_buffer.ascii_buffer and does
    not call the session.read() method when the buffer is exposed.
    """
    from pure3270.p3270_client import P3270Client

    read_invoked = {"called": False}

    class DummyBuffer:
        @property
        def ascii_buffer(self):
            return ""  # safe property

    class DummySession:
        def __init__(self):
            self.screen_buffer = DummyBuffer()

        def read(self, timeout=None):
            # If read is called, set flag and raise to make test fail
            read_invoked["called"] = True
            raise RuntimeError("read invoked")

        def enter(self):
            # no-op
            return

        def tab(self):
            return

        def pf(self, n):
            return

    client = P3270Client()
    client._pure_session = DummySession()
    client._connected = True

    # Should not raise and should not have invoked read()
    client.sendEnter()
    client.sendTab()
    client.sendPF(1)

    assert read_invoked["called"] is False


def test_enter_handles_read_runtimeerror_when_no_buffer():
    """If no screen_buffer is exposed, _sendCommand may call read(); ensure
    it handles RuntimeError gracefully by catching it and not raising.
    """
    from pure3270.p3270_client import P3270Client

    class DummySession:
        def __init__(self):
            # no screen_buffer attribute
            self.read_called = False

        def read(self, timeout=None):
            self.read_called = True
            raise RuntimeError("concurrent read")

        def enter(self):
            return

        def tab(self):
            return

        def pf(self, n):
            return

    client = P3270Client()
    client._pure_session = DummySession()
    client._connected = True

    # Should not raise, and read should have been called (and handled)
    client.sendEnter()
    assert client._pure_session.read_called is True


@pytest.mark.parametrize(
    "method_name",
    [
        "sendPF",
        "sendPA",
        "saveScreen",
        "makeArgs",
        "foundTextAtPosition",
        "waitForStringAt",
        "waitForStringAtOffset",
        "readTextArea",
    ],
)
def test_signature_matches_p3270_reference(method_name):
    """Verify that P3270Client method parameter names match p3270.

    Renamed parameters between pure3270 and p3270 break callers that
    port from p3270 to pure3270. The parameter names of these
    methods MUST match p3270.P3270Client's signatures for
    drop-in replacement parity.

    Notes:
    - sendPF uses ``n`` (not ``pfNum``)
    - sendPA uses ``n`` (not ``paNum``)
    - saveScreen uses ``fileName`` and ``dataType`` (not ``filename``)
    - makeArgs takes no arguments (not ``*args``)
    - foundTextAtPosition uses ``sent_text`` (not ``text``)
    - waitForStringAt[Offset] uses ``string`` (not ``text``)
    - readTextArea uses 1-based ``row``, ``col``, ``rows``, ``cols``
      (not 0-based ``startRow``/``endRow`` style)

    The ``timeout`` parameter added to waitFor* methods is backward
    compatible (default value) and not checked here.
    """
    import inspect
    import os
    import sys

    # Try to find the real p3270 reference. The local ``p3270.py`` shim
    # at the project root re-exports pure3270.P3270Client, which would
    # always compare equal to itself; we want the actual external
    # reference. The repo's ``venv/lib/python3.13/site-packages`` is
    # the authoritative source in this environment.
    venv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "venv",
        "lib",
    )
    inserted_paths = []
    for sub in (
        "python3.9",
        "python3.10",
        "python3.11",
        "python3.12",
        "python3.13",
    ):
        candidate = os.path.join(venv_path, sub, "site-packages")
        if os.path.isdir(candidate) and candidate not in sys.path:
            sys.path.insert(0, candidate)
            inserted_paths.append(candidate)
    try:
        from p3270.p3270 import P3270Client as P3270
    except ImportError:
        for p in inserted_paths:
            try:
                sys.path.remove(p)
            except ValueError:
                pass
        pytest.skip("Real p3270 package not installed in any venv")
    finally:
        # Restore sys.path so the import does not leak into other tests
        for p in inserted_paths:
            try:
                sys.path.remove(p)
            except ValueError:
                pass

    from pure3270.p3270_client import P3270Client as Pure

    p_sig = inspect.signature(getattr(P3270, method_name))
    pure_sig = inspect.signature(getattr(Pure, method_name))
    p_params = list(p_sig.parameters.keys())
    pure_params = list(pure_sig.parameters.keys())
    # Every p3270 parameter must exist as the same name in pure3270.
    # pure3270 may add additional optional kwargs after the first N
    # (e.g. ``timeout`` on waitFor* methods) without breaking
    # drop-in compatibility.
    assert p_params == pure_params[: len(p_params)], (
        f"p3270.P3270Client.{method_name} parameters {p_params!r} "
        f"do not match pure3270.P3270Client.{method_name} parameters "
        f"{pure_params!r}. Param renames break drop-in compatibility."
    )
