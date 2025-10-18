import asyncio
import logging
import os
from typing import Any, Optional

# IND$FILE structured field type
IND_FILE_SF_TYPE = 0xD0

# IND$FILE sub-commands
IND_FILE_UPLOAD = 0x00
IND_FILE_DOWNLOAD = 0x01
IND_FILE_DATA = 0x02
IND_FILE_EOF = 0x03
IND_FILE_ERROR = 0x04

logger = logging.getLogger(__name__)


class IndFileError(Exception):
    """Base exception for IND$FILE errors."""


class IndFileMessage:
    """Represents an IND$FILE protocol message."""

    def __init__(self, sub_command: int, payload: bytes = b""):
        self.sub_command = sub_command
        self.payload = payload

    @classmethod
    def create_upload_request(cls, filename: str) -> "IndFileMessage":
        """Create an upload request message."""
        filename_bytes = filename.encode("ascii") + b"\x00"
        return cls(IND_FILE_UPLOAD, filename_bytes)

    @classmethod
    def create_download_request(cls, filename: str) -> "IndFileMessage":
        """Create a download request message."""
        filename_bytes = filename.encode("ascii") + b"\x00"
        return cls(IND_FILE_DOWNLOAD, filename_bytes)

    @classmethod
    def create_data(cls, data: bytes) -> "IndFileMessage":
        """Create a data message."""
        return cls(IND_FILE_DATA, data)

    @classmethod
    def create_eof(cls) -> "IndFileMessage":
        """Create an end-of-file message."""
        return cls(IND_FILE_EOF)

    @classmethod
    def create_error(cls, error_msg: str) -> "IndFileMessage":
        """Create an error message."""
        error_bytes = error_msg.encode("ascii")
        return cls(IND_FILE_ERROR, error_bytes)

    def to_bytes(self) -> bytes:
        """Convert message to bytes for transmission."""
        return bytes([self.sub_command]) + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> "IndFileMessage":
        """Parse message from bytes."""
        if len(data) < 1:
            raise ValueError("IND$FILE message too short")
        sub_command = data[0]
        payload = data[1:] if len(data) > 1 else b""
        return cls(sub_command, payload)

    def get_filename(self) -> Optional[str]:
        """Extract filename from payload if present."""
        if self.payload and b"\x00" in self.payload:
            filename_bytes = self.payload.split(b"\x00", 1)[0]
            return filename_bytes.decode("ascii", errors="replace")
        return None

    def get_error_message(self) -> Optional[str]:
        """Extract error message from payload."""
        if self.payload:
            return self.payload.decode("ascii", errors="replace")
        return None


class IndFileTransfer:
    """Represents an ongoing IND$FILE transfer."""

    def __init__(self, direction: str, remote_name: str, local_path: str):
        self.direction = direction  # 'upload' or 'download'
        self.remote_name = remote_name
        self.local_path = local_path
        self.file_handle: Optional[Any] = None
        self.is_active = True
        self.bytes_transferred = 0

    def start(self) -> None:
        """Start the file transfer."""
        if self.direction == "download":
            # For downloads, create/truncate the local file
            self.file_handle = open(self.local_path, "wb")
        elif self.direction == "upload":
            # For uploads, the file should already be opened by the caller
            pass

    def write_data(self, data: bytes) -> None:
        """Write data to the file (for downloads)."""
        if self.file_handle and self.direction == "download":
            self.file_handle.write(data)
            self.file_handle.flush()  # Ensure data is written to disk
            self.bytes_transferred += len(data)

    def finish(self) -> None:
        """Finish the file transfer."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
        self.is_active = False

    def abort(self, error_msg: str) -> None:
        """Abort the file transfer."""
        self.finish()
        if os.path.exists(self.local_path) and self.direction == "download":
            try:
                os.remove(self.local_path)
            except OSError:
                pass  # Ignore cleanup errors
        logger.error(f"IND$FILE transfer aborted: {error_msg}")


class IndFile:
    """IND$FILE file transfer support for 3270 terminals."""

    def __init__(self, session: Any) -> None:
        self.session = session
        self.active_transfer: Optional[IndFileTransfer] = None

    async def send(self, local_path: str, remote_name: str) -> None:
        """Send a file to the host using IND$FILE protocol."""
        if self.active_transfer:
            raise IndFileError("Another file transfer is already in progress")

        try:
            if not os.path.exists(local_path):
                raise IndFileError(f"Local file does not exist: {local_path}")

            # Create transfer object
            self.active_transfer = IndFileTransfer("upload", remote_name, local_path)
            self.active_transfer.start()

            # Send upload request
            upload_msg = IndFileMessage.create_upload_request(remote_name)
            await self._send_ind_file_message(upload_msg)

            # Send file data in chunks
            with open(local_path, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    data_msg = IndFileMessage.create_data(chunk)
                    await self._send_ind_file_message(data_msg)

            # Send EOF
            eof_msg = IndFileMessage.create_eof()
            await self._send_ind_file_message(eof_msg)

            logger.info(f"Successfully sent file {local_path} as {remote_name}")

        except Exception as e:
            if self.active_transfer:
                self.active_transfer.abort(str(e))
                self.active_transfer = None
            logger.error(f"Failed to send file {local_path}: {e}")
            # Send error indication
            error_msg = IndFileMessage.create_error(str(e))
            await self._send_ind_file_message(error_msg)
            raise IndFileError(f"File transfer failed: {e}")
        finally:
            if self.active_transfer:
                self.active_transfer.finish()
                self.active_transfer = None

    async def receive(self, remote_name: str, local_path: str) -> None:
        """Receive a file from the host using IND$FILE protocol."""
        if self.active_transfer:
            raise IndFileError("Another file transfer is already in progress")

        try:
            # Create transfer object
            self.active_transfer = IndFileTransfer("download", remote_name, local_path)
            self.active_transfer.start()

            # Send download request
            download_msg = IndFileMessage.create_download_request(remote_name)
            await self._send_ind_file_message(download_msg)

            # Create an event to wait for transfer completion
            transfer_complete = asyncio.Event()

            # Store the completion event for the message handler to set
            self._transfer_complete_event = transfer_complete

            # Wait for the transfer to complete (with timeout)
            try:
                await asyncio.wait_for(transfer_complete.wait(), timeout=30.0)
                logger.info(f"Successfully received file {remote_name} to {local_path}")
            except asyncio.TimeoutError:
                if self.active_transfer:
                    self.active_transfer.abort("Transfer timeout")
                    self.active_transfer = None
                raise IndFileError(f"File receive timeout for {remote_name}")

        except Exception as e:
            if self.active_transfer:
                self.active_transfer.abort(str(e))
                self.active_transfer = None
            logger.error(f"Failed to receive file {remote_name}: {e}")
            raise IndFileError(f"File receive failed: {e}")
        finally:
            # Clean up the completion event
            if hasattr(self, "_transfer_complete_event"):
                delattr(self, "_transfer_complete_event")

    def handle_incoming_message(self, message: IndFileMessage) -> None:
        """Handle incoming IND$FILE message from the host."""
        try:
            if message.sub_command == IND_FILE_DATA:
                # Write data to file
                if self.active_transfer:
                    self.active_transfer.write_data(message.payload)
                    logger.debug(
                        f"IND$FILE: Wrote {len(message.payload)} bytes to file"
                    )
                else:
                    logger.warning("Received IND$FILE data but no active transfer")

            elif message.sub_command == IND_FILE_EOF:
                # End of file - finish transfer
                if self.active_transfer:
                    self.active_transfer.finish()
                    logger.info(
                        f"IND$FILE: Transfer completed for {self.active_transfer.remote_name}"
                    )
                    # Signal completion if we have a completion event
                    if hasattr(self, "_transfer_complete_event"):
                        self._transfer_complete_event.set()
                    self.active_transfer = None
                else:
                    logger.warning("Received IND$FILE EOF but no active transfer")

            elif message.sub_command == IND_FILE_ERROR:
                # Error from host
                error_msg = message.get_error_message() or "Unknown error"
                if self.active_transfer:
                    self.active_transfer.abort(f"Host error: {error_msg}")
                    # Signal completion on error
                    if hasattr(self, "_transfer_complete_event"):
                        self._transfer_complete_event.set()
                    self.active_transfer = None
                else:
                    logger.error(f"IND$FILE error from host: {error_msg}")

            elif message.sub_command == IND_FILE_UPLOAD:
                # Host is requesting upload - this initiates a host-to-client transfer
                filename = message.get_filename()
                if filename:
                    logger.info(f"IND$FILE: Host requesting upload of file: {filename}")
                    # For host-initiated uploads, we would need to accept or reject
                    # For now, we'll accept and prepare for incoming data
                    # In a full implementation, this might require user confirmation
                    self._handle_host_upload_request(filename)
                else:
                    logger.warning("IND$FILE upload request missing filename")

            elif message.sub_command == IND_FILE_DOWNLOAD:
                # Host is requesting download - this would be handled differently
                filename = message.get_filename()
                logger.debug(
                    f"IND$FILE download request from host for file: {filename}"
                )

        except Exception as e:
            logger.error(f"Error handling IND$FILE message: {e}")
            if self.active_transfer:
                self.active_transfer.abort(f"Message handling error: {e}")
                # Signal completion on error
                if hasattr(self, "_transfer_complete_event"):
                    self._transfer_complete_event.set()
                self.active_transfer = None
        finally:
            # Clean up any resources if needed
            pass

    def _handle_host_upload_request(self, filename: str) -> None:
        """Handle host-initiated upload request."""
        # For now, just log the request
        # In a full implementation, this would initiate a download transfer
        logger.info(f"Host upload request for {filename} - not yet implemented")

    def handle_incoming_data(self, data: bytes) -> None:
        """Handle incoming IND$FILE data from the host (legacy method)."""
        try:
            message = IndFileMessage.from_bytes(data)
            self.handle_incoming_message(message)
        except Exception as e:
            logger.error(f"Error parsing IND$FILE data: {e}")

    async def _send_ind_file_message(self, message: IndFileMessage) -> None:
        """Send an IND$FILE message."""
        # IND$FILE structured field format:
        # 0x88 (SF), length (2 bytes), 0xD0 (IND$FILE type), message_data
        message_data = message.to_bytes()
        length = len(message_data) + 3  # SF + length(2) + type(1) + message_data
        header = bytes(
            [
                0x88,  # structured field identifier
                (length >> 8) & 0xFF,
                length & 0xFF,
                IND_FILE_SF_TYPE,  # IND$FILE structured field type
            ]
        )
        await self.session.send_data(header + message_data)
