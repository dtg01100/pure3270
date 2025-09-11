"""
TN3270 protocol handler for pure3270.
Handles negotiation, data sending/receiving, and protocol specifics.
"""

import asyncio
import ssl
import logging
from typing import Optional
from .data_stream import DataStreamParser
from ..emulation.screen_buffer import ScreenBuffer
from .utils import send_iac, send_subnegotiation
from .exceptions import NegotiationError, ProtocolError, ParseError
from .negotiator import Negotiator

logger = logging.getLogger(__name__)


class TN3270Handler:
    """
    Handler for TN3270 protocol over Telnet.

    Manages stream I/O, negotiation, and data parsing for 3270 emulation.
    """

    async def connect(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        ssl_context: Optional[ssl.SSLContext] = None,
    ) -> None:
        """Connect the handler."""
        # If already have reader/writer (from fixture), validate and mark as connected
        if self.reader is not None and self.writer is not None:
            # Add stream validation
            if not hasattr(self.reader, "read") or not hasattr(self.writer, "write"):
                raise ValueError("Invalid reader or writer objects")
            self._connected = True
            return

        try:
            # Use provided params or fallback to instance values
            connect_host = host or self.host
            connect_port = port or self.port
            connect_ssl = ssl_context or self.ssl_context

            reader, writer = await asyncio.open_connection(
                connect_host, connect_port, ssl=connect_ssl
            )
            # Validate streams
            if reader is None or writer is None:
                raise ConnectionError("Failed to obtain valid reader/writer")
            if not hasattr(reader, "read") or not hasattr(writer, "write"):
                raise ConnectionError("Invalid stream objects returned")

            self.reader = reader
            self.writer = writer
            self._connected = True

            # Update negotiator with writer
            self.negotiator.writer = self.writer

            # Perform negotiation
            await self.negotiator.negotiate()
            await self.negotiator._negotiate_tn3270()
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Failed to connect: {e}")

    def __init__(
        self,
        reader: Optional[asyncio.StreamReader],
        writer: Optional[asyncio.StreamWriter],
        ssl_context: Optional[ssl.SSLContext] = None,
        host: str = "localhost",
        port: int = 23,
    ):
        """
        Initialize the TN3270 handler.

        Args:
            reader: Asyncio stream reader (can be None for testing).
            writer: Asyncio stream writer (can be None for testing).
            ssl_context: Optional SSL context for secure connections.
            host: Target host for connection.
            port: Target port for connection.

        Raises:
            ValueError: If reader or writer is None (when not in test mode).
        """
        self.reader = reader
        self.writer = writer
        self.ssl_context = ssl_context
        self.host = host
        self.port = port
        self.screen_buffer = ScreenBuffer()
        self.parser = DataStreamParser(self.screen_buffer)
        self._connected = False
        self.negotiator = Negotiator(self.writer, self.parser, self.screen_buffer, self)

    async def negotiate(self) -> None:
        """
        Perform initial Telnet negotiation.

        Delegates to negotiator.
        """
        await self.negotiator.negotiate()

    async def _negotiate_tn3270(self) -> None:
        """
        Negotiate TN3270E subnegotiation.

        Delegates to negotiator.
        """
        await self.negotiator._negotiate_tn3270()

    def set_ascii_mode(self) -> None:
        """
        Set the handler to ASCII mode fallback.

        Disables EBCDIC processing.
        """
        self.negotiator.set_ascii_mode()

    async def send_data(self, data: bytes) -> None:
        """
        Send data over the connection.

        Args:
            data: Bytes to send.

        Raises:
            ProtocolError: If writer is None or send fails.
        """
        if self.writer is None:
            logger.error("Not connected")
            raise ProtocolError("Writer is None; cannot send data.")
        self.writer.write(data)
        await self.writer.drain()

    async def receive_data(self, timeout: float = 5.0) -> bytes:
        """
        Receive data with timeout.

        Args:
            timeout: Receive timeout in seconds.

        Returns:
            Received bytes.

        Raises:
            asyncio.TimeoutError: If timeout exceeded.
            ProtocolError: If reader is None.
        """
        logger.debug(f"receive_data called on handler {id(self)}")
        logger.debug(f"Handler negotiator object ID: {id(self.negotiator)}")
        if self.reader is None:
            logger.error("Not connected")
            raise ProtocolError("Reader is None; cannot receive data.")
        try:
            logger.debug(f"Attempting to read data with timeout {timeout}")
            data = await asyncio.wait_for(self.reader.read(4096), timeout=timeout)
            logger.debug(f"Received {len(data)} bytes of data")
        except asyncio.TimeoutError:
            logger.debug("Timeout while reading data")
            raise
        except Exception as e:
            logger.error(f"Error reading data: {e}")
            raise
            
        # Check if we're in ASCII mode
        ascii_mode = self.negotiator._ascii_mode
        logger.debug(f"Checking ASCII mode: negotiator._ascii_mode = {ascii_mode} on negotiator object {id(self.negotiator)}")
        
        # Auto-detect ASCII mode based on data content for s3270 compatibility
        # s3270 automatically switches to ASCII mode when it detects VT100 sequences
        if not ascii_mode and len(data) > 0:
            # Check for common VT100 escape sequences that indicate ASCII mode
            if self._detect_vt100_sequences(data):
                logger.info("Detected VT100 sequences, enabling ASCII mode (s3270 compatibility)")
                ascii_mode = True
                # In s3270 compatibility mode, also set the negotiator ASCII mode
                self.negotiator._ascii_mode = True
        
        if ascii_mode:
            logger.debug("In ASCII mode, parsing VT100 data")
            # In ASCII mode, parse VT100 escape sequences and update screen buffer
            try:
                logger.debug(f"Parsing VT100 data ({len(data)} bytes)")
                from .vt100_parser import VT100Parser
                vt100_parser = VT100Parser(self.screen_buffer)
                vt100_parser.parse(data)
                logger.debug("VT100 parsing completed successfully")
            except Exception as e:
                logger.warning(f"Error parsing VT100 data: {e}")
                import traceback
                logger.warning(f"Traceback: {traceback.format_exc()}")
            return data
        # Parse and update screen buffer (simplified)
        logger.debug("In TN3270 mode, parsing 3270 data")
        try:
            self.parser.parse(data)
        except ParseError as e:
            logger.warning(f"Failed to parse received data: {e}")
            # Continue with raw data if parsing fails
        # Strip EOR if present
        if b"\xff\x19" in data:
            data = data.split(b"\xff\x19")[0]
        return data
        
    def _detect_vt100_sequences(self, data: bytes) -> bool:
        """
        Detect VT100 escape sequences in data for s3270 compatibility.
        
        Args:
            data: Raw data to check for VT100 sequences
            
        Returns:
            True if VT100 sequences detected, False otherwise
        """
        if len(data) < 2:
            return False
            
        # Check for ESC character followed by common VT100 sequences
        for i in range(len(data) - 1):
            if data[i] == 0x1b:  # ESC character
                # Common VT100 sequences:
                # ESC [ - CSI (Control Sequence Introducer)
                # ESC ( - Character set designation
                # ESC ) - Character set designation
                # ESC # - DEC commands
                # ESC 7 - Save cursor
                # ESC 8 - Restore cursor
                if i + 1 < len(data):
                    next_char = data[i + 1]
                    if next_char in [ord('['), ord('('), ord(')'), ord('#'), ord('7'), ord('8')]:
                        logger.debug(f"Detected VT100 escape sequence: ESC {chr(next_char) if chr(next_char).isprintable() else f'0x{next_char:02x}'}")
                        return True
                    # Check for other common sequences
                    elif next_char in [ord('D'), ord('M'), ord('c')]:  # IND, RI, RIS
                        logger.debug(f"Detected VT100 control sequence: ESC {chr(next_char)}")
                        return True
                        
        # Check for other VT100 indicators
        # Look for escape sequences that are more specific than just printable ASCII
        # VT100 data often contains control characters mixed with printable ASCII
        printable_ascii_count = sum(1 for b in data if 0x20 <= b <= 0x7e)
        control_char_count = sum(1 for b in data if b in [0x0a, 0x0d, 0x09, 0x08, 0x1b])
        total_chars = len(data)
        
        # Only suggest ASCII mode if we have a mix of printable and control characters
        # and a reasonable amount of printable text
        if total_chars > 0:
            printable_ratio = printable_ascii_count / total_chars
            control_ratio = control_char_count / total_chars
            
            # Require both printable text and some control characters for VT100 detection
            # Also require a minimum amount of printable text
            if (printable_ratio > 0.5 and control_ratio > 0.05 and 
                printable_ascii_count > 10):
                logger.debug(f"Mixed ASCII/control character pattern suggests ASCII mode: "
                           f"printable={printable_ratio:.2f}, control={control_ratio:.2f}")
                return True
            
            # Or if we have high density of printable ASCII with ESC characters
            esc_count = data.count(0x1b)
            if esc_count > 0 and printable_ratio > 0.6:
                logger.debug(f"ESC characters with high ASCII density ({esc_count} ESC chars, "
                           f"printable={printable_ratio:.2f}) suggests ASCII mode")
                return True
                
            # Or if we have very high density of printable ASCII characters (indicates ASCII terminal)
            # This is for systems that deliver their interface as plain ASCII text
            if printable_ratio > 0.8 and printable_ascii_count > 50:
                logger.debug(f"Very high ASCII character density ({printable_ratio:.2f}) "
                           f"suggests ASCII terminal mode")
                return True
        
        return False

    async def send_scs_data(self, scs_data: bytes) -> None:
        """
        Send SCS character data for printer sessions.

        Args:
            scs_data: SCS character data to send

        Raises:
            ProtocolError: If not connected or not a printer session
        """
        if not self._connected:
            raise ProtocolError("Not connected")

        if not self.negotiator.is_printer_session:
            raise ProtocolError("Not a printer session")

        if self.writer is None:
            raise ProtocolError("Writer is None; cannot send SCS data.")

        # Send SCS data
        self.writer.write(scs_data)
        await self.writer.drain()
        logger.debug(f"Sent {len(scs_data)} bytes of SCS data")

    async def send_print_eoj(self) -> None:
        """
        Send PRINT-EOJ (End of Job) command for printer sessions.

        Raises:
            ProtocolError: If not connected or not a printer session
        """
        if not self._connected:
            raise ProtocolError("Not connected")

        if not self.negotiator.is_printer_session:
            raise ProtocolError("Not a printer session")

        from .data_stream import DataStreamSender

        sender = DataStreamSender()
        eoj_command = sender.build_scs_ctl_codes(0x01)  # PRINT_EOJ

        if self.writer is None:
            raise ProtocolError("Writer is None; cannot send PRINT-EOJ.")

        self.writer.write(eoj_command)
        await self.writer.drain()
        logger.debug("Sent PRINT-EOJ command")

    async def _read_iac(self) -> bytes:
        """
        Read IAC (Interpret As Command) sequence.

        Returns:
            IAC response bytes.

        Raises:
            ParseError: If IAC parsing fails.
        """
        if self.reader is None:
            raise ProtocolError("Reader is None; cannot read IAC.")
        iac = await self.reader.readexactly(3)
        if iac[0] != 0xFF:
            raise ParseError("Invalid IAC sequence")
        return iac

    async def close(self) -> None:
        """Close the connection."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None
        self._connected = False

    def is_connected(self) -> bool:
        """Check if the handler is connected."""
        if self._connected and self.writer is not None and self.reader is not None:
            # Liveness check: try to check if writer is still open
            try:
                # Check if writer has is_closing method (asyncio.StreamWriter)
                if hasattr(self.writer, "is_closing") and self.writer.is_closing():
                    return False
                # Check if reader has at_eof method (asyncio.StreamReader)
                if hasattr(self.reader, "at_eof") and self.reader.at_eof():
                    return False
            except Exception:
                # If liveness check fails, assume not connected
                return False
            return True
        return False

    def is_printer_session_active(self) -> bool:
        """
        Check if this is a printer session.

        Returns:
            bool: True if this is a printer session
        """
        return self.negotiator.is_printer_session

    @property
    def negotiated_tn3270e(self) -> bool:
        """Get TN3270E negotiation status."""
        return self.negotiator.negotiated_tn3270e

    @property
    def lu_name(self) -> Optional[str]:
        """Get the LU name."""
        return self.negotiator.lu_name

    @lu_name.setter
    def lu_name(self, value: Optional[str]) -> None:
        """Set the LU name."""
        self.negotiator.lu_name = value

    @property
    def screen_rows(self) -> int:
        """Get screen rows."""
        return self.negotiator.screen_rows

    @property
    def screen_cols(self) -> int:
        """Get screen columns."""
        return self.negotiator.screen_cols

    @property
    def is_printer_session(self) -> bool:
        """Get printer session status."""
        return self.negotiator.is_printer_session

    @is_printer_session.setter
    def is_printer_session(self, value: bool) -> None:
        """Set printer session status."""
        self.negotiator.is_printer_session = value
