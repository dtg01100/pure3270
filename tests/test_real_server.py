import pytest
import os
from pure3270.session import Session
import logging

# Telnet constants for test
IAC = 0xff
DO = 0xfd
WONT = 0xfc

@pytest.fixture(params=[False, True], scope="session")
def real_session(request):
    if os.getenv("TEST_REAL_SERVER") != "1":
        pytest.skip("Real server tests skipped unless TEST_REAL_SERVER=1")
    host = os.getenv('REAL_HOST', 'localhost')
    port = int(os.getenv('REAL_PORT', '23'))
    session = Session(force_3270=request.param)
    try:
        session.connect(host, port)
        yield session
    finally:
        session.close()


def test_connection(real_session, caplog):
    """Test successful connection to real TN3270 server."""
    caplog.set_level(logging.DEBUG)
    assert real_session.connected is True
    expected_mode = real_session._async_session.force_3270  # Access internal for expectation
    assert real_session.tn3270_mode == expected_mode, f"Mode mismatch: expected {expected_mode}"
    assert real_session.tn3270e_mode == expected_mode, f"TN3270E mode mismatch: expected {expected_mode}"
    if expected_mode:
        assert "forced TN3270 mode" in caplog.text
        assert real_session.lu_name == "DEFAULT"
        print("Forced TN3270 mode verified")
    else:
        assert "Sent DO TN3270E" in caplog.text
        assert "Received WONT TN3270E" in caplog.text
        assert real_session.lu_name is None
        print("New negotiation logs verified: fallback to ASCII confirmed")


def test_initial_screen_read(real_session, caplog):
    """Test reading initial screen buffer from real server, verifying login screen."""
    caplog.set_level(logging.DEBUG)
    import time
 
    # Send Clear to trigger initial screen/login
    real_session.send("key Clear")
    print("Sent 'key Clear' to trigger screen")
 
    # Retry read up to 30 seconds total
    max_wait = 30
    waited = 0
    screen = ""
    while waited < max_wait:
        try:
            screen = real_session.read()
            if screen.strip():  # Non-empty after strip
                break
        except Exception as e:
            print(f"Read attempt failed after {waited}s: {e}")
        time.sleep(1)
        waited += 1
 
    assert isinstance(screen, str), "Screen read failed to return string"
    assert len(screen.strip()) > 0, "Screen is empty after wait"
    print(f"Initial screen (first 200 chars): {screen[:200]}")
    print(f"Full screen length: {len(screen)}")
 
    if not real_session.tn3270_mode:
        # Verify readable login screen content via fallback
        assert "sign on" in screen.lower() or "login" in screen.lower() or "userid" in screen.lower() or "password" in screen.lower(), "No readable login content found via ASCII fallback"
        print("Login screen verified: readable content received via fallback")
        assert "Fallback ASCII read successful" in caplog.text
        print(f"ASCII fallback screen (first 200 chars): {screen[:200]}")
    else:
        assert "TN3270E mode: parsing 3270 data stream" in caplog.text or "Screen read successfully" in caplog.text
        print("Forced TN3270 mode: garbled EBCDIC screen non-empty (expected due to ASCII server)")
        print(f"Garbled EBCDIC screen (first 200 chars): {screen[:200]}")
    print(f"Full screen:\n{screen}")


def test_send_clear_and_read(real_session):
    """Test sending clear command and reading updated screen."""
    real_session.send("key Clear")
    screen = real_session.read()
    assert isinstance(screen, str)
    assert len(screen.strip()) > 0, "Screen is empty after send clear"
    print(f"Screen after send clear (first 200 chars): {screen[:200]}")
    # No specific content assertion as server response varies; check for successful read
    if real_session.tn3270_mode:
        print("Forced TN3270 mode: garbled screen expected")
    else:
        print("ASCII fallback: readable screen expected")

def test_lu_name(real_session):
    """Test LU name property."""
    expected_mode = real_session._async_session.force_3270
    if expected_mode:
        assert real_session.lu_name == "DEFAULT"
        print("LU name in force mode: DEFAULT")
    else:
        assert real_session.lu_name is None
        print("LU name in normal mode: None (no BIND expected)")
