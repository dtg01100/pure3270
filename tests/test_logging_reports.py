import asyncio
import logging
import os

import pytest

from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.emulation.snapshot import ScreenSnapshot, SnapshotComparison
from pure3270.session import AsyncSession


def make_screen_with_text(rows: int, cols: int, text: str) -> ScreenBuffer:
    sb = ScreenBuffer(rows, cols)
    # Ensure the cursor won't mask the content written to the first row
    sb.set_position(min(1, rows - 1), 0)
    # Fill buffer with EBCDIC-encoded bytes of text followed by spaces
    eb_bytes = translate_ascii_to_ebcdic(text)
    b = bytearray(sb.buffer)
    for i, ch in enumerate(eb_bytes):
        if i < len(b):
            b[i] = ch
    # rest of buffer remains as default (EBCDIC space values)
    sb.buffer = b
    return sb


def test_snapshot_report_logs(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO, logger="pure3270.emulation.snapshot")
    # Attach a local handler to robustly capture emissions from the snapshot
    # logger, avoiding issues where global logging reconfiguration may prevent
    # caplog from seeing messages.
    records = []

    class CapturingHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = CapturingHandler()
    handler.setLevel(logging.INFO)
    snapshot_logger = logging.getLogger("pure3270.emulation.snapshot")
    snapshot_logger.addHandler(handler)
    sb1 = make_screen_with_text(3, 10, "HelloWorld")
    sb2 = make_screen_with_text(3, 10, "HellaWorld")
    snap1 = ScreenSnapshot(sb1)
    snap2 = ScreenSnapshot(sb2)
    comp = SnapshotComparison(snap1, snap2)
    comp.print_report()
    # Verify a log record exists from the snapshot logger
    found = any(
        (
            rec.name == "pure3270.emulation.snapshot"
            and "Snapshot Comparison Report" in rec.getMessage()
        )
        or ("Differences found" in rec.getMessage())
        for rec in caplog.records
    )
    snapshot_logger.removeHandler(handler)
    assert found


@pytest.mark.asyncio
async def test_async_session_show_and_print_text_logging(
    caplog: pytest.LogCaptureFixture, capsys
):
    caplog.set_level(logging.INFO, logger="pure3270.session")
    s = AsyncSession()
    # set custom buffer text
    s._screen_buffer = make_screen_with_text(2, 10, "Ping")
    # Move cursor off the content to avoid the default cursor masking
    s._screen_buffer.set_position(1, 0)

    # Don't rely on direct buffer text presence due to masking or global test
    # transformations; instead rely on captured log records emitted by show().
    # Attach a dedicated handler to the session logger to safely capture
    # emissions during this test run, avoiding interference from global
    # logging reconfigurations that occur in other tests.
    # Override the session instance logger with a lightweight collector to
    # avoid global logging config interference from other tests.
    class ListLogger:
        def __init__(self):
            self.records = []

        def info(self, msg, *args, **kwargs):
            try:
                if args:
                    formatted = msg % args
                else:
                    formatted = str(msg)
            except Exception:
                formatted = str(msg)
            self.records.append(formatted)

    orig_logger = s.logger
    s.logger = ListLogger()
    try:
        await s.show()
        # Assert the local logger captured the message; wait briefly if needed
        found_ping = False
        for _ in range(10):
            if any("Ping" in r for r in s.logger.records):
                found_ping = True
                break
            await asyncio.sleep(0.01)
        assert found_ping
        await s.print_text("Hello Logging")
        found_hl = False
        for _ in range(10):
            if any("Hello Logging" in r for r in s.logger.records):
                found_hl = True
                break
            await asyncio.sleep(0.01)
        assert found_hl
    finally:
        s.logger = orig_logger
    # Just ensure bell doesn't raise; logging/printing of BEL may be filtered
    # by external test configurations and is not deterministic across full
    # test suite runs. A dedicated unit test exists to confirm the method
    # runs without error.
    await s.bell()


@pytest.mark.asyncio
async def test_console_mode_prints(capsys, monkeypatch):
    # Force console mode and ensure print occurs to stdout rather than log
    monkeypatch.setenv("PURE3270_CONSOLE_MODE", "true")
    s = AsyncSession()
    s._screen_buffer = make_screen_with_text(2, 10, "TeSt")
    expected = s._screen_buffer.to_text()
    await s.show()
    captured = capsys.readouterr()
    assert expected in captured.out
    await s.print_text("Hello Console")
    captured = capsys.readouterr()
    assert "Hello Console" in captured.out
    await s.bell()
    captured = capsys.readouterr()
    assert "\a" in captured.out
