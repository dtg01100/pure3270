"""Coverage tests for pure3270.ind_file.

Covers the public API used by pure3270.session for mainframe file transfer:
    * IndFileMessage parsing and helpers
    * IndFileTransfer lifecycle (start / write_data / finish / abort)
    * IndFile.send() and IndFile.receive() end-to-end with a mocked session
    * IndFile.handle_incoming_message() for every documented sub-command
    * IndFile._send_ind_file_message() framing
    * IndFile.handle_incoming_data() (legacy entry point)
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pure3270.ind_file import (
    IND_FILE_DATA,
    IND_FILE_DOWNLOAD,
    IND_FILE_EOF,
    IND_FILE_ERROR,
    IND_FILE_SF_TYPE,
    IND_FILE_UPLOAD,
    IndFile,
    IndFileError,
    IndFileMessage,
    IndFileTransfer,
)


def _make_session() -> MagicMock:
    """Build a MagicMock session with an AsyncMock send_data method."""
    session = MagicMock()
    session.send_data = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# IndFileMessage parsing and helpers
# ---------------------------------------------------------------------------


class TestIndFileMessageParsing:
    """IndFileMessage.from_bytes edge cases."""

    def test_from_bytes_empty_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="too short"):
            IndFileMessage.from_bytes(b"")

    def test_from_bytes_single_byte_has_empty_payload(self) -> None:
        msg = IndFileMessage.from_bytes(b"\x03")  # 0x03 = IND_FILE_EOF
        assert msg.sub_command == IND_FILE_EOF
        assert msg.payload == b""

    def test_from_bytes_multi_byte_captures_payload(self) -> None:
        msg = IndFileMessage.from_bytes(b"\x02hello world")
        assert msg.sub_command == IND_FILE_DATA
        assert msg.payload == b"hello world"


class TestIndFileMessageFilename:
    """IndFileMessage.get_filename behavior."""

    def test_get_filename_no_nul_returns_none(self) -> None:
        msg = IndFileMessage(IND_FILE_UPLOAD, b"NO_NUL_HERE")
        assert msg.get_filename() is None

    def test_get_filename_with_nul_splits_correctly(self) -> None:
        msg = IndFileMessage(IND_FILE_UPLOAD, b"FILE.TXT\x00trailing")
        assert msg.get_filename() == "FILE.TXT"

    def test_get_filename_non_ascii_uses_replace(self) -> None:
        # 0xC3 0xA9 is "é" in UTF-8 — invalid as ASCII, must not raise
        msg = IndFileMessage(IND_FILE_UPLOAD, b"\xc3\xa9\x00")
        # errors="replace" yields U+FFFD for non-ASCII bytes
        assert msg.get_filename() == "\ufffd\ufffd"

    def test_get_filename_empty_payload_returns_none(self) -> None:
        msg = IndFileMessage(IND_FILE_UPLOAD, b"")
        assert msg.get_filename() is None


class TestIndFileMessageErrorText:
    """IndFileMessage.get_error_message behavior."""

    def test_get_error_message_empty_returns_none(self) -> None:
        msg = IndFileMessage(IND_FILE_ERROR, b"")
        assert msg.get_error_message() is None

    def test_get_error_message_with_payload(self) -> None:
        msg = IndFileMessage(IND_FILE_ERROR, b"File not found")
        assert msg.get_error_message() == "File not found"

    def test_get_error_message_non_ascii_uses_replace(self) -> None:
        msg = IndFileMessage(IND_FILE_ERROR, b"\xff\xfe")
        assert msg.get_error_message() == "\ufffd\ufffd"


# ---------------------------------------------------------------------------
# IndFileTransfer lifecycle
# ---------------------------------------------------------------------------


class TestIndFileTransferLifecycle:
    """IndFileTransfer state machine: start / write_data / finish / abort."""

    def test_constructor_initializes_defaults(self) -> None:
        t = IndFileTransfer("upload", "remote.txt", "/tmp/local.txt")
        assert t.direction == "upload"
        assert t.remote_name == "remote.txt"
        assert t.local_path == "/tmp/local.txt"
        assert t.file_handle is None
        assert t.is_active is True
        assert t.bytes_transferred == 0

    def test_download_start_opens_file_for_write(self, tmp_path) -> None:
        local = tmp_path / "dl.bin"
        t = IndFileTransfer("download", "REMOTE", str(local))
        t.start()
        try:
            handle = t.file_handle
            assert handle is not None, "file_handle should be set after start()"
            assert not handle.closed
            assert t.is_active is True
        finally:
            t.finish()

    def test_upload_start_is_noop(self) -> None:
        t = IndFileTransfer("upload", "REMOTE", "/does/not/matter")
        t.start()
        assert t.file_handle is None
        assert t.is_active is True

    def test_write_data_writes_and_increments(self, tmp_path) -> None:
        local = tmp_path / "write.bin"
        t = IndFileTransfer("download", "R", str(local))
        t.start()
        try:
            t.write_data(b"abc")
            t.write_data(b"defgh")
            assert t.bytes_transferred == 8
            assert local.read_bytes() == b"abcdefgh"
        finally:
            t.finish()

    def test_finish_closes_handle_and_marks_inactive(self, tmp_path) -> None:
        local = tmp_path / "finish.bin"
        t = IndFileTransfer("download", "R", str(local))
        t.start()
        handle = t.file_handle
        assert handle is not None
        t.finish()
        assert t.file_handle is None
        assert t.is_active is False
        assert handle.closed

    def test_finish_with_no_handle_is_safe(self) -> None:
        t = IndFileTransfer("upload", "R", "/tmp/x")
        t.finish()  # must not raise
        assert t.is_active is False

    def test_abort_download_removes_local_file(self, tmp_path) -> None:
        local = tmp_path / "abort.bin"
        t = IndFileTransfer("download", "R", str(local))
        t.start()
        assert local.exists()
        t.abort("test")
        assert not local.exists()
        assert t.is_active is False

    def test_abort_upload_does_not_remove_local_file(self, tmp_path) -> None:
        local = tmp_path / "upload.bin"
        local.write_bytes(b"keep me")
        t = IndFileTransfer("upload", "R", str(local))
        # upload.start() is a no-op; don't open a handle
        t.abort("test")
        assert local.exists()
        assert local.read_bytes() == b"keep me"

    def test_start_download_bad_path_raises_and_marks_inactive(self, tmp_path) -> None:
        bad_dir = tmp_path / "does" / "not" / "exist"
        t = IndFileTransfer("download", "R", str(bad_dir))
        with pytest.raises(IndFileError, match="Failed to open local file"):
            t.start()
        assert t.is_active is False
        assert t.file_handle is None


# ---------------------------------------------------------------------------
# IndFile.send()
# ---------------------------------------------------------------------------


class TestIndFileSend:
    """IndFile.send() happy paths, boundary conditions, and error paths."""

    @pytest.mark.asyncio
    async def test_send_small_file_emits_three_messages(self, tmp_path, caplog) -> None:
        local = tmp_path / "small.txt"
        payload = b"hello mainframe"
        local.write_bytes(payload)

        session = _make_session()
        ind_file = IndFile(session)

        with caplog.at_level(logging.INFO, logger="pure3270.ind_file"):
            await ind_file.send(str(local), "REMOTE.TXT")

        # 3 SFs: upload request, 1 data chunk, EOF
        assert session.send_data.await_count == 3
        # Local file must NOT be modified by an upload (read-only).
        assert local.read_bytes() == payload
        # Info log confirms successful transfer.
        assert any("Successfully sent file" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_send_boundary_at_4096_bytes_emits_three_messages(
        self, tmp_path
    ) -> None:
        local = tmp_path / "boundary.bin"
        local.write_bytes(b"x" * 4096)  # exactly one full chunk

        session = _make_session()
        ind_file = IndFile(session)

        await ind_file.send(str(local), "REMOTE.BIN")

        # upload + 1 data + eof = 3 SFs
        assert session.send_data.await_count == 3

    @pytest.mark.asyncio
    async def test_send_multi_chunk_file_emits_multiple_data_messages(
        self, tmp_path
    ) -> None:
        # 8193 bytes → two full 4096 chunks plus 1 trailing byte chunk.
        local = tmp_path / "multi.bin"
        local.write_bytes(b"y" * 8193)

        session = _make_session()
        ind_file = IndFile(session)

        await ind_file.send(str(local), "REMOTE.BIN")

        # upload + 3 data + eof = 5 SFs.
        assert session.send_data.await_count == 5

    @pytest.mark.asyncio
    async def test_send_missing_local_file_raises(self, tmp_path, caplog) -> None:
        session = _make_session()
        ind_file = IndFile(session)
        missing = tmp_path / "nope.bin"

        with caplog.at_level(logging.INFO, logger="pure3270.ind_file"):
            with pytest.raises(IndFileError, match="Local file does not exist"):
                await ind_file.send(str(missing), "REMOTE.BIN")

        # No SFs were sent at all before the failure — we never told the
        # host we were uploading, so nothing to abort.
        assert session.send_data.await_count == 0
        assert ind_file.active_transfer is None

    @pytest.mark.asyncio
    async def test_send_when_active_transfer_already_set(self, tmp_path) -> None:
        session = _make_session()
        ind_file = IndFile(session)
        # Park a pre-existing transfer; send() must reject before doing any I/O.
        ind_file.active_transfer = IndFileTransfer("upload", "OTHER", "/tmp/other")

        local = tmp_path / "would_send.txt"
        local.write_bytes(b"x")

        with pytest.raises(IndFileError, match="Another file transfer is already"):
            await ind_file.send(str(local), "REMOTE.TXT")

        assert session.send_data.await_count == 0

    @pytest.mark.asyncio
    async def test_send_session_raises_aborts_and_sends_error_sf(
        self, tmp_path, caplog
    ) -> None:
        local = tmp_path / "boom.bin"
        local.write_bytes(b"payload")
        session = _make_session()
        # First send (upload request) raises; second send (error SF) succeeds.
        session.send_data.side_effect = [RuntimeError("net down"), None]

        ind_file = IndFile(session)

        with caplog.at_level(logging.INFO, logger="pure3270.ind_file"):
            with pytest.raises(IndFileError, match="File transfer failed"):
                await ind_file.send(str(local), "REMOTE.BIN")

        # Two send_data calls: upload request (failed) + error SF (succeeded).
        assert session.send_data.await_count == 2
        # After abort, active transfer is cleared.
        assert ind_file.active_transfer is None
        # The second SF must be the error message framing.
        second_call_bytes = session.send_data.await_args_list[1].args[0]
        assert second_call_bytes[0] == 0x88
        assert second_call_bytes[3] == IND_FILE_SF_TYPE
        # sub_command byte (IND_FILE_ERROR == 0x04) sits right after the header
        assert second_call_bytes[4] == IND_FILE_ERROR


# ---------------------------------------------------------------------------
# IndFile.receive()
# ---------------------------------------------------------------------------


class TestIndFileReceive:
    """IndFile.receive() lifecycle and error handling."""

    @pytest.mark.asyncio
    async def test_receive_happy_path_completes_when_event_set(
        self, tmp_path, caplog
    ) -> None:
        local = tmp_path / "happy.bin"
        session = _make_session()
        ind_file = IndFile(session)

        task = asyncio.create_task(ind_file.receive("REMOTE.BIN", str(local)))

        # Poll until receive() stores the completion event on self, then set it.
        for _ in range(400):
            if hasattr(ind_file, "_transfer_complete_event"):
                ind_file._transfer_complete_event.set()
                break
            await asyncio.sleep(0.005)
        else:  # pragma: no cover - defensive
            task.cancel()
            pytest.fail("receive() never installed _transfer_complete_event")

        await task

        # Local file was opened (download direction) but no data was written.
        assert local.exists()
        assert local.read_bytes() == b""
        # finally block cleaned up the event attribute.
        assert not hasattr(ind_file, "_transfer_complete_event")
        # The download request SF was sent exactly once.
        assert session.send_data.await_count == 1

    @pytest.mark.asyncio
    async def test_receive_when_active_transfer_already_set(self, tmp_path) -> None:
        local = tmp_path / "busy.bin"
        session = _make_session()
        ind_file = IndFile(session)
        ind_file.active_transfer = IndFileTransfer("download", "OTHER", str(local))

        with pytest.raises(IndFileError, match="Another file transfer is already"):
            await ind_file.receive("REMOTE.BIN", str(local))

        assert session.send_data.await_count == 0
        # The pre-existing active transfer was not touched.
        assert ind_file.active_transfer is not None

    @pytest.mark.asyncio
    async def test_receive_timeout_aborts_active_transfer(self, tmp_path) -> None:
        local = tmp_path / "timeout.bin"
        session = _make_session()
        ind_file = IndFile(session)

        # Force asyncio.wait_for to raise TimeoutError inside receive().
        with patch(
            "pure3270.ind_file.asyncio.wait_for",
            side_effect=asyncio.TimeoutError,
        ):
            with pytest.raises(IndFileError, match="File receive timeout"):
                await ind_file.receive("REMOTE.BIN", str(local))

        # Abort on timeout cleans up the file and clears the active transfer.
        assert ind_file.active_transfer is None
        assert not local.exists()
        # finally must remove the event attr even on the timeout path.
        assert not hasattr(ind_file, "_transfer_complete_event")

    @pytest.mark.filterwarnings(
        "ignore::RuntimeWarning"
    )  # benign mock+asyncio GC warning, see test
    @pytest.mark.asyncio
    async def test_receive_exception_during_send_aborts_and_raises(
        self, tmp_path, caplog
    ) -> None:
        local = tmp_path / "send_fail.bin"
        session = _make_session()

        # Use a real coroutine function for the failure so AsyncMock's
        # internal coroutine bookkeeping doesn't leak a never-awaited
        # Event.wait() warning during GC.
        async def _failing_send(_data: bytes) -> None:
            raise RuntimeError("transport gone")

        session.send_data.side_effect = _failing_send
        ind_file = IndFile(session)

        with caplog.at_level(logging.INFO, logger="pure3270.ind_file"):
            with pytest.raises(IndFileError, match="File receive failed"):
                await ind_file.receive("REMOTE.BIN", str(local))

        # active transfer is aborted (download direction removes the local file)
        assert ind_file.active_transfer is None
        assert not local.exists()
        # finally cleaned up the event attribute even though we never set it.
        assert not hasattr(ind_file, "_transfer_complete_event")


# ---------------------------------------------------------------------------
# IndFile.handle_incoming_message()
# ---------------------------------------------------------------------------


class TestHandleIncomingMessageData:
    """IND_FILE_DATA dispatch."""

    def test_data_with_active_transfer_writes_payload(self, tmp_path) -> None:
        local = tmp_path / "data.bin"
        ind_file = IndFile(_make_session())
        t = IndFileTransfer("download", "REMOTE", str(local))
        t.start()
        ind_file.active_transfer = t

        try:
            ind_file.handle_incoming_message(IndFileMessage(IND_FILE_DATA, b"chunk1"))
            ind_file.handle_incoming_message(IndFileMessage(IND_FILE_DATA, b"-chunk2"))
            assert t.bytes_transferred == 13
            assert local.read_bytes() == b"chunk1-chunk2"
        finally:
            t.finish()

    def test_data_with_no_active_transfer_logs_warning(self, caplog) -> None:
        ind_file = IndFile(_make_session())
        with caplog.at_level(logging.WARNING, logger="pure3270.ind_file"):
            ind_file.handle_incoming_message(IndFileMessage(IND_FILE_DATA, b"orphan"))
        assert any(
            "Received IND$FILE data but no active transfer" in r.message
            for r in caplog.records
        )


class TestHandleIncomingMessageEof:
    """IND_FILE_EOF dispatch."""

    def test_eof_with_active_transfer_finishes_and_signals(
        self, tmp_path, caplog
    ) -> None:
        local = tmp_path / "eof.bin"
        ind_file = IndFile(_make_session())
        t = IndFileTransfer("download", "REMOTE", str(local))
        t.start()
        ind_file.active_transfer = t
        ind_file._transfer_complete_event = asyncio.Event()

        with caplog.at_level(logging.INFO, logger="pure3270.ind_file"):
            ind_file.handle_incoming_message(IndFileMessage(IND_FILE_EOF))

        # transfer was finished (handle closed, is_active=False)
        assert t.file_handle is None
        assert t.is_active is False
        # completion event was set
        assert ind_file._transfer_complete_event.is_set()
        # active transfer cleared
        assert ind_file.active_transfer is None

    def test_eof_with_no_active_transfer_logs_warning(self, caplog) -> None:
        ind_file = IndFile(_make_session())
        with caplog.at_level(logging.WARNING, logger="pure3270.ind_file"):
            ind_file.handle_incoming_message(IndFileMessage(IND_FILE_EOF))
        assert any(
            "Received IND$FILE EOF but no active transfer" in r.message
            for r in caplog.records
        )


class TestHandleIncomingMessageError:
    """IND_FILE_ERROR dispatch."""

    def test_error_with_payload_aborts_and_signals(self, tmp_path, caplog) -> None:
        local = tmp_path / "err.bin"
        ind_file = IndFile(_make_session())
        t = IndFileTransfer("download", "REMOTE", str(local))
        t.start()
        ind_file.active_transfer = t
        ind_file._transfer_complete_event = asyncio.Event()

        with caplog.at_level(logging.INFO, logger="pure3270.ind_file"):
            ind_file.handle_incoming_message(
                IndFileMessage(IND_FILE_ERROR, b"disk full")
            )

        # Transfer aborted → file removed (download direction).
        assert not local.exists()
        # Completion event was set so a waiting receive() unblocks.
        assert ind_file._transfer_complete_event.is_set()
        # Active transfer cleared.
        assert ind_file.active_transfer is None

    def test_error_with_no_active_transfer_logs_error(self, caplog) -> None:
        ind_file = IndFile(_make_session())
        with caplog.at_level(logging.ERROR, logger="pure3270.ind_file"):
            ind_file.handle_incoming_message(IndFileMessage(IND_FILE_ERROR, b"oops"))
        assert any("IND$FILE error from host" in r.message for r in caplog.records)


class TestHandleIncomingMessageUpload:
    """IND_FILE_UPLOAD dispatch."""

    def test_upload_with_valid_filename_invokes_handler(self, caplog) -> None:
        ind_file = IndFile(_make_session())
        with (
            patch.object(ind_file, "_handle_host_upload_request") as mock_handler,
            caplog.at_level(logging.INFO, logger="pure3270.ind_file"),
        ):
            ind_file.handle_incoming_message(
                IndFileMessage(IND_FILE_UPLOAD, b"REMOTE.DAT\x00")
            )
        mock_handler.assert_called_once_with("REMOTE.DAT")
        assert any(
            "Host requesting upload of file" in r.message for r in caplog.records
        )

    def test_upload_missing_filename_logs_warning(self, caplog) -> None:
        ind_file = IndFile(_make_session())
        with caplog.at_level(logging.WARNING, logger="pure3270.ind_file"):
            ind_file.handle_incoming_message(
                IndFileMessage(IND_FILE_UPLOAD, b"no-nul-here")
            )
        assert any(
            "IND$FILE upload request missing filename" in r.message
            for r in caplog.records
        )


class TestHandleIncomingMessageDownload:
    """IND_FILE_DOWNLOAD dispatch."""

    def test_download_logs_debug(self, caplog) -> None:
        ind_file = IndFile(_make_session())
        with caplog.at_level(logging.DEBUG, logger="pure3270.ind_file"):
            ind_file.handle_incoming_message(
                IndFileMessage(IND_FILE_DOWNLOAD, b"FILE.TXT\x00")
            )
        assert any(
            "IND$FILE download request from host" in r.message for r in caplog.records
        )


class TestHandleIncomingMessageException:
    """Exception inside handle_incoming_message() must abort any active transfer."""

    def test_handler_exception_aborts_active_transfer(self, tmp_path, caplog) -> None:
        local = tmp_path / "exc.bin"
        ind_file = IndFile(_make_session())
        t = IndFileTransfer("download", "REMOTE", str(local))
        t.start()
        ind_file.active_transfer = t
        ind_file._transfer_complete_event = asyncio.Event()

        # Force write_data to raise so the outer try/except in
        # handle_incoming_message runs.
        with (
            patch.object(t, "write_data", side_effect=RuntimeError("disk full")),
            caplog.at_level(logging.INFO, logger="pure3270.ind_file"),
        ):
            ind_file.handle_incoming_message(IndFileMessage(IND_FILE_DATA, b"x"))

        # Abort on error path cleans up the file and clears active transfer.
        assert ind_file.active_transfer is None
        assert not local.exists()
        # Waiters get unblocked.
        assert ind_file._transfer_complete_event.is_set()


class TestHandleHostUploadRequest:
    """The internal helper that backs IND_FILE_UPLOAD."""

    def test_logs_info_with_filename(self, caplog) -> None:
        ind_file = IndFile(_make_session())
        with caplog.at_level(logging.INFO, logger="pure3270.ind_file"):
            ind_file._handle_host_upload_request("REMOTE.DAT")
        assert any(
            "Host upload request for REMOTE.DAT" in r.message for r in caplog.records
        )


# ---------------------------------------------------------------------------
# _send_ind_file_message framing
# ---------------------------------------------------------------------------


class TestSendIndFileMessage:
    """Verify the structured-field framing emitted to the session."""

    @pytest.mark.asyncio
    async def test_message_framing_has_sf_header_and_length(self) -> None:
        session = _make_session()
        ind_file = IndFile(session)
        msg = IndFileMessage.create_data(b"hello")

        await ind_file._send_ind_file_message(msg)

        sent_bytes = session.send_data.await_args.args[0]
        # First four bytes are the structured-field header.
        assert sent_bytes[0] == 0x88
        length = (sent_bytes[1] << 8) | sent_bytes[2]
        assert sent_bytes[3] == IND_FILE_SF_TYPE
        # length counts itself + the type byte + the message body.
        message_data = msg.to_bytes()
        assert length == len(message_data) + 3
        # The body is the message's to_bytes() output (sub-command + payload).
        assert sent_bytes[4:] == message_data

    @pytest.mark.asyncio
    async def test_message_framing_handles_large_payload(self) -> None:
        session = _make_session()
        ind_file = IndFile(session)
        big = b"A" * 5000
        msg = IndFileMessage.create_data(big)

        await ind_file._send_ind_file_message(msg)

        sent_bytes = session.send_data.await_args.args[0]
        length = (sent_bytes[1] << 8) | sent_bytes[2]
        # 5000 + 1 (sub_command) + 3 (header bytes) = 5004
        assert length == 5004
        assert sent_bytes[4:] == b"\x02" + big


# ---------------------------------------------------------------------------
# handle_incoming_data (legacy entry point)
# ---------------------------------------------------------------------------


class TestHandleIncomingDataLegacy:
    """The bytes-in dispatcher used by the data stream parser."""

    def test_valid_bytes_delegates_to_handle_incoming_message(self) -> None:
        ind_file = IndFile(_make_session())
        with patch.object(ind_file, "handle_incoming_message") as mock_inner:
            msg = IndFileMessage.create_data(b"chunk")
            ind_file.handle_incoming_data(msg.to_bytes())
        mock_inner.assert_called_once()
        delegated = mock_inner.call_args.args[0]
        assert delegated.sub_command == IND_FILE_DATA
        assert delegated.payload == b"chunk"

    def test_empty_bytes_logs_error_and_does_not_raise(self, caplog) -> None:
        ind_file = IndFile(_make_session())
        with caplog.at_level(logging.ERROR, logger="pure3270.ind_file"):
            # from_bytes raises ValueError on empty input; the except
            # branch must swallow it and log.
            ind_file.handle_incoming_data(b"")
        assert any("Error parsing IND$FILE data" in r.message for r in caplog.records)

    def test_arbitrary_bytes_do_not_raise(self) -> None:
        ind_file = IndFile(_make_session())
        # from_bytes accepts anything non-empty and handle_incoming_message
        # is tolerant of unknown sub-commands. The legacy entry point must
        # never leak an exception regardless of payload content.
        ind_file.handle_incoming_data(b"\xff\xfe\xfd")
        ind_file.handle_incoming_data(b"\x00")
        ind_file.handle_incoming_data(b"plain bytes")


# ---------------------------------------------------------------------------
# Constants sanity
# ---------------------------------------------------------------------------


class TestIndFileConstants:
    """Protocol constants and IndFileError must be exported."""

    def test_constants_have_expected_values(self) -> None:
        assert IND_FILE_UPLOAD == 0x00
        assert IND_FILE_DOWNLOAD == 0x01
        assert IND_FILE_DATA == 0x02
        assert IND_FILE_EOF == 0x03
        assert IND_FILE_ERROR == 0x04
        assert IND_FILE_SF_TYPE == 0xD0

    def test_ind_file_error_is_exception(self) -> None:
        assert issubclass(IndFileError, Exception)
