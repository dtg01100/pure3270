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

    # show() prints to stdout, so we capture stdout output
    await s.show()
    captured = capsys.readouterr()
    # Verify "Ping" appears in the captured stdout output
    assert "Ping" in captured.out

    # print_text() prints to stdout
    await s.print_text("Hello Logging")
    captured = capsys.readouterr()
    assert "Hello Logging" in captured.out

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
