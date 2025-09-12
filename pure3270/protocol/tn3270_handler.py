"""
TN3270 protocol handler for pure3270.
Handles negotiation, data sending/receiving, and protocol specifics.
"""

import asyncio
import ssl
import logging
from typing import Optional
from .data_stream import DataStreamParser, SnaResponse # Import SnaResponse
from ..emulation.screen_buffer import ScreenBuffer
from ..emulation.printer_buffer import PrinterBuffer # Import PrinterBuffer
from .utils import send_iac, send_subnegotiation, TN3270_DATA, TN3270E_SYSREQ, TN3270E_SYSREQ_MESSAGE_TYPE, TN3270E_SYSREQ_ATTN, TN3270E_SYSREQ_BREAK, TN3270E_SYSREQ_CANCEL, TN3270E_SYSREQ_RESTART, TN3270E_SYSREQ_PRINT, TN3270E_SYSREQ_LOGOFF
from .exceptions import NegotiationError, ProtocolError, ParseError
from .negotiator import Negotiator
from .tn3270e_header import TN3270EHeader

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
            await self.negotiator._negotiate_tn3270(timeout=10.0) # Increased timeout for negotiation
        except Exception as e:
            logger.error(f"Connection failed: {e}", exc_info=True)
            raise ConnectionError(f"Failed to connect: {e}")

    def __init__(
        self,
        reader: Optional[asyncio.StreamReader],
        writer: Optional[asyncio.StreamWriter],
        ssl_context: Optional[ssl.SSLContext] = None,
        host: str = "localhost",
        port: int = 23,
        is_printer_session: bool = False, # New parameter for printer session
    ):
        """
        Initialize the TN3270 handler.

        Args:
            reader: Asyncio stream reader (can be None for testing).
            writer: Asyncio stream writer (can be None for testing).
            ssl_context: Optional SSL context for secure connections.
            host: Target host for connection.
            port: Target port for connection.
            is_printer_session: True if this handler is for a printer session.

        Raises:
            ValueError: If reader or writer is None (when not in test mode).
        """
        self.reader = reader
        self.writer = writer
        self.ssl_context = ssl_context
        self.host = host
        self.port = port
        self.screen_buffer = ScreenBuffer()
        self.printer_buffer = PrinterBuffer() if is_printer_session else None # Initialize PrinterBuffer if it's a printer session

        # Initialize negotiator first, then pass it to the parser
        self.negotiator = Negotiator(self.writer, None, self.screen_buffer, self) # Pass None for parser initially
        self.negotiator.is_printer_session = is_printer_session # Set printer session after initialization
        self.parser = DataStreamParser(self.screen_buffer, self.printer_buffer, self.negotiator) # Pass printer_buffer
        # Now update the negotiator with the parser instance
        self.negotiator.parser = self.parser
        self._connected = False
        self._telnet_buffer = b"" # Buffer for incomplete Telnet sequences

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

        # If DATA-STREAM-CTL is active, prepend TN3270EHeader
        if self.negotiator.is_data_stream_ctl_active:
            # For now, default to TN3270_DATA for outgoing messages
            # In a more complex scenario, this data_type might be passed as an argument
            header = self.negotiator._outgoing_request("CLIENT_DATA", data_type=TN3270_DATA)
            data_to_send = header.to_bytes() + data
            logger.debug(f"Prepending TN3270E header for outgoing data. Header: {header}")
        else:
            data_to_send = data

        self.writer.write(data_to_send)
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
            logger.debug(f"Received {len(data)} bytes of data: {data.hex()}")
        except asyncio.TimeoutError:
            logger.debug("Timeout while reading data")
            raise
        except Exception as e:
            logger.error(f"Error reading data: {e}", exc_info=True)
            raise

        # Process incoming data, handling IAC sequences and extracting 3270 data
        processed_data, ascii_mode_detected = await self._process_telnet_stream(data)

        # If ASCII mode was detected by the stream processor, update negotiator
        if ascii_mode_detected:
            self.negotiator.set_ascii_mode()

        # Check if we're in ASCII mode
        ascii_mode = self.negotiator._ascii_mode
        logger.debug(
            f"Checking ASCII mode: negotiator._ascii_mode = {ascii_mode} on negotiator object {id(self.negotiator)}"
        )

        if ascii_mode:
            logger.debug("In ASCII mode, parsing VT100 data")
            # In ASCII mode, parse VT100 escape sequences and update screen buffer
            try:
                logger.debug(f"Parsing VT100 data ({len(processed_data)} bytes)")
                from .vt100_parser import VT100Parser

                vt100_parser = VT100Parser(self.screen_buffer)
                vt100_parser.parse(processed_data)
                logger.debug("VT100 parsing completed successfully")
            except Exception as e:
                logger.warning(f"Error parsing VT100 data: {e}")
                import traceback

                logger.warning(f"Traceback: {traceback.format_exc()}")
            return processed_data
        # Parse and update screen buffer (simplified)
        logger.debug("In TN3270 mode, parsing 3270 data")
        # Extract TN3270E header for data type and sequence number
        from .tn3270e_header import TN3270EHeader
        from .utils import TN3270_DATA, SCS_DATA, PRINTER_STATUS_DATA_TYPE

        data_type = TN3270_DATA # Default to TN3270_DATA
        header_len = 0
        if len(processed_data) >= 5:
            tn3270e_header = TN3270EHeader.from_bytes(processed_data[:5])
            if tn3270e_header:
                data_type = tn3270e_header.data_type
                header_len = 5
                # Log header details if present
                logger.debug(f"Received TN3270E header: {tn3270e_header}")
                # Pass the header to the negotiator for correlation
                self.negotiator._handle_tn3270e_response(tn3270e_header)

                # If it's SCS data, ensure it's routed to the printer buffer
                if data_type == SCS_DATA and self.printer_buffer:
                    logger.debug(f"Routing SCS_DATA to printer buffer.")
                    self.parser.parse(processed_data[header_len:], data_type=data_type)
                    return processed_data # SCS data doesn't update screen
                elif data_type == PRINTER_STATUS_DATA_TYPE and self.printer_buffer:
                    logger.debug(f"Routing PRINTER_STATUS_DATA_TYPE to printer buffer handler.")
                    self.parser.parse(processed_data[header_len:], data_type=data_type)
                    return processed_data # Printer status data doesn't update screen


        # Pass data type to parser for appropriate handling (e.g., SCS data)
        try:
            self.parser.parse(processed_data[header_len:], data_type=data_type)
        except ParseError as e:
            logger.warning(f"Failed to parse received data: {e}")
            # Continue with raw data if parsing fails
        return processed_data

    async def _process_telnet_stream(self, raw_data: bytes) -> (bytes, bool):
        """
        Process raw Telnet stream, handle IAC sequences, and return 3270 data.
        This also detects VT100 sequences for s3270 compatibility.

        Args:
            raw_data: Raw bytes received from the connection.

        Returns:
            Tuple of (cleaned_3270_data, ascii_mode_detected).
        """
        from .utils import IAC, SB, SE, WILL, WONT, DO, DONT, EOR, TN3270E, BRK

        cleaned_data = bytearray()
        i = 0
        ascii_mode_detected = False

        # Add any previously incomplete data to the beginning of the current raw_data
        full_data = self._telnet_buffer + raw_data
        self._telnet_buffer = b"" # Clear the buffer

        while i < len(full_data):
            if full_data[i] == IAC:
                if i + 1 < len(full_data):
                    command = full_data[i + 1]
                    if command == IAC:  # Escaped IAC
                        cleaned_data.append(IAC)
                        i += 2
                    elif command == SB:  # Subnegotiation
                        j = i + 2
                        # Find IAC SE
                        while j < len(full_data) and not (
                            full_data[j] == IAC and j + 1 < len(full_data) and full_data[j + 1] == SE
                        ):
                            j += 1
                        if j + 1 < len(full_data) and full_data[j + 1] == SE:
                            # Found IAC SE
                            sub_option = full_data[i + 2] if i + 2 < j else None
                            sub_data = full_data[i + 3 : j]

                            # Pass all subnegotiations to the negotiator for handling
                            await self.negotiator.handle_subnegotiation(sub_option, sub_data)
                            i = j + 2
                        else:
                            # Incomplete subnegotiation, buffer remaining data
                            self._telnet_buffer = full_data[i:]
                            break
                    elif command in (DO, DONT, WILL, WONT):
                        if i + 2 < len(full_data):
                            option = full_data[i + 2]
                            await self.negotiator.handle_iac_command(command, option) # Await this call
                            i += 3
                        else:
                            # Incomplete command, buffer remaining data
                            self._telnet_buffer = full_data[i:]
                            break
                    elif command == EOR: # End of Record
                        logger.debug("Received IAC EOR")
                        i += 2
                    elif command == TN3270E: # TN3270E option (should be handled by subnegotiation)
                        logger.debug("Received TN3270E option")
                        i += 2
                    elif command == BRK: # Break command
                        logger.debug("Received IAC BRK")
                        # Handle BREAK command - for now, just log it
                        # In a more complete implementation, this might trigger some specific behavior
                        i += 2
                    else:
                        logger.debug(f"Unhandled IAC command: 0x{command:02x}")
                        i += 2
                else:
                    # Incomplete IAC sequence, buffer remaining data
                    self._telnet_buffer = full_data[i:]
                    break
            else:
                cleaned_data.append(full_data[i])
                i += 1

        # Detect VT100 sequences in the *original* raw data for s3270 compatibility
        # This method is not implemented here but is a placeholder for future
        # compatibility with s3270's VT100 detection.
        # if not ascii_mode_detected and self._detect_vt100_sequences(raw_data):
        #     ascii_mode_detected = True

        return bytes(cleaned_data), ascii_mode_detected


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

    async def send_printer_status_sf(self, status_code: int) -> None:
        """
        Send a Printer Status Structured Field to the host.

        Args:
            status_code: The status code to send (e.g., DEVICE_END, INTERVENTION_REQUIRED).

        Raises:
            ProtocolError: If not connected or writer is None.
        """
        if not self._connected:
            raise ProtocolError("Not connected")
        if self.writer is None:
            raise ProtocolError("Writer is None; cannot send printer status SF.")

        from .data_stream import DataStreamSender
        sender = DataStreamSender()
        status_sf = sender.build_printer_status_sf(status_code)
        self.writer.write(status_sf)
        await self.writer.drain()
        logger.debug(f"Sent Printer Status SF: 0x{status_code:02x}")

    async def send_sysreq_command(self, command_code: int) -> None:
        """
        Send a SYSREQ command to the host.

        Args:
            command_code: The byte code representing the SYSREQ command.
        """
        if not self._connected:
            raise ProtocolError("Not connected")
        if self.writer is None:
            raise ProtocolError("Writer is None; cannot send SYSREQ command.")

        if not (self.negotiator.negotiated_functions & TN3270E_SYSREQ):
            logger.warning(f"SYSREQ function not negotiated. Cannot send command 0x{command_code:02x}")
            # Fallback to Telnet ATTN if the command is ATTN and SYSREQ is not negotiated
            if command_code == TN3270E_SYSREQ_ATTN:
                logger.info("Falling back to Telnet ATTN (IAC IP).")
                send_iac(self.writer, b"\xf7") # IAC IP
                await self.writer.drain()
                return
            else:
                raise ProtocolError(f"SYSREQ function not negotiated for command 0x{command_code:02x}")

        # Construct TN3270E SYSREQ subnegotiation
        # IAC SB TN3270E SYSREQ_MESSAGE_TYPE SYSREQ_COMMAND_CODE IAC SE
        sub_data = bytes([TN3270E_SYSREQ_MESSAGE_TYPE, command_code])
        send_subnegotiation(self.writer, bytes([0x28]), sub_data) # 0x28 is TN3270E option
        await self.writer.drain()
        logger.debug(f"Sent TN3270E SYSREQ command: 0x{command_code:02x}")


    async def send_break(self) -> None:
        """
        Send a Telnet BREAK command (IAC BRK) to the host.

        Raises:
            ProtocolError: If not connected or writer is None.
        """
        if not self._connected:
            raise ProtocolError("Not connected")
        if self.writer is None:
            raise ProtocolError("Writer is None; cannot send BREAK command.")

        from .utils import IAC, BRK
        send_iac(self.writer, bytes([BRK]))
        await self.writer.drain()
        logger.debug("Sent Telnet BREAK command (IAC BRK)")

    async def send_soh_message(self, status_code: int) -> None:
        """
        Send an SOH (Start of Header) message for printer status to the host.

        Args:
            status_code: The status code to send (e.g., SOH_SUCCESS, SOH_DEVICE_END).

        Raises:
            ProtocolError: If not connected or writer is None.
        """
        if not self._connected:
            raise ProtocolError("Not connected")
        if self.writer is None:
            raise ProtocolError("Writer is None; cannot send SOH message.")

        from .data_stream import DataStreamSender
        sender = DataStreamSender()
        soh_message = sender.build_soh_message(status_code)
        self.writer.write(soh_message)
        await self.writer.drain()
        logger.debug(f"Sent SOH message with status: 0x{status_code:02x}")

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

    @property
    def printer_status(self) -> Optional[int]:
        """Get the current printer status."""
        return self.negotiator.printer_status

    @property
    def sna_session_state(self) -> str:
        """Get the current SNA session state."""
        return self.negotiator.current_sna_session_state.value
