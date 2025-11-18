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
