"""
Negotiator for TN3270 protocol specifics.
Handles Telnet negotiation and TN3270E subnegotiation.
"""

import asyncio
import logging
from typing import Optional, TYPE_CHECKING, List
from enum import Enum # Import Enum for state management
from .data_stream import DataStreamParser, SnaResponse, BindImage # Import SnaResponse and BindImage
from .utils import (
    send_iac,
    send_subnegotiation,
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IS,
    TN3270E_REQUEST,
    TN3270E_SEND,
    TN3270E_BIND_IMAGE,
    TN3270E_DATA_STREAM_CTL,
    TN3270E_RESPONSES,
    TN3270E_SCS_CTL_CODES,
    TN3270E_SYSREQ,
    TN3270E_IBM_DYNAMIC,
    TN3270E_SYSREQ_MESSAGE_TYPE,
    TN3270E_SYSREQ_ATTN,
    TN3270E_SYSREQ_BREAK,
    TN3270E_SYSREQ_CANCEL,
    TN3270E_SYSREQ_RESTART,
    TN3270E_SYSREQ_PRINT,
    TN3270E_SYSREQ_LOGOFF,
    TELOPT_TTYPE, TELOPT_BINARY, TELOPT_EOR, TELOPT_TN3270E,
    DO, DONT, WILL, WONT,
    TN3270E_RSF_POSITIVE_RESPONSE,
    TN3270E_RSF_NEGATIVE_RESPONSE,
    TN3270E_RSF_ERROR_RESPONSE,
    SNA_RESPONSE, # Import SNA_RESPONSE
    TELOPT_OLD_ENVIRON as TELOPT_TERMINAL_LOCATION, # Alias for RFC 1646 (TELOPT 36)
    TELOPT_BIND_UNIT, # TELOPT 48
)
from .exceptions import NegotiationError, ProtocolError, ParseError
from ..emulation.screen_buffer import ScreenBuffer
from .utils import QUERY_REPLY_CHARACTERISTICS
from .data_stream import (
    SNA_SENSE_CODE_SUCCESS, SNA_SENSE_CODE_INVALID_FORMAT,
    SNA_SENSE_CODE_NOT_SUPPORTED, SNA_SENSE_CODE_SESSION_FAILURE,
    SNA_SENSE_CODE_INVALID_REQUEST, SNA_SENSE_CODE_LU_BUSY,
    SNA_SENSE_CODE_INVALID_SEQUENCE, SNA_SENSE_CODE_NO_RESOURCES,
    SNA_SENSE_CODE_STATE_ERROR
)


if TYPE_CHECKING:
    from .tn3270_handler import TN3270Handler

logger = logging.getLogger(__name__)

from .tn3270e_header import TN3270EHeader
from .utils import TN3270_DATA, SCS_DATA, RESPONSE, BIND_IMAGE, UNBIND, NVT_DATA, REQUEST, SSCP_LU_DATA, PRINT_EOJ, TN3270E_RSF_NO_RESPONSE, TN3270E_RSF_ERROR_RESPONSE, TN3270E_RSF_ALWAYS_RESPONSE, TN3270E_RSF_POSITIVE_RESPONSE, TN3270E_RSF_NEGATIVE_RESPONSE

class SnaSessionState(Enum):
    """Represents the current state of the SNA session."""
    NORMAL = "NORMAL"
    ERROR = "ERROR"
    PENDING_RECOVERY = "PENDING_RECOVERY"
    SESSION_DOWN = "SESSION_DOWN"
    LU_BUSY = "LU_BUSY"
    INVALID_SEQUENCE = "INVALID_SEQUENCE"
    STATE_ERROR = "STATE_ERROR"

class Negotiator:
    """
    Handles TN3270 negotiation logic.
    """

    def __init__(
        self,
        writer: Optional[asyncio.StreamWriter],
        parser: Optional[DataStreamParser],
        screen_buffer: ScreenBuffer,
        handler: Optional["TN3270Handler"] = None,
        is_printer_session: bool = False,
    ):
        """
        Initialize the Negotiator.

        Args:
            writer: StreamWriter for sending commands.
            parser: DataStreamParser for parsing responses.
            screen_buffer: ScreenBuffer to update during negotiation.
            handler: TN3270Handler instance for accessing reader methods.
            is_printer_session: True if this is a printer session.
        """
        logger.debug("Negotiator.__init__ called")
        self.writer = writer
        self.parser = parser
        self.screen_buffer = screen_buffer
        self.handler = handler
        self._ascii_mode = False
        logger.debug(f"Negotiator._ascii_mode initialized to {self._ascii_mode}")
        self.negotiated_tn3270e = False
        self._lu_name: Optional[str] = None
        self.screen_rows = 24
        self.screen_cols = 80
        self.is_printer_session = is_printer_session
        self.printer_status: Optional[int] = None # New attribute for printer status
        self._sna_session_state: SnaSessionState = SnaSessionState.NORMAL # Initial SNA session state
        self.supported_device_types: List[str] = [
            "IBM-3278-2",
            "IBM-3278-3",
            "IBM-3278-4",
            "IBM-3278-5",
            "IBM-3279-2",
            "IBM-3279-3",
            "IBM-3279-4",
            "IBM-3279-5",
            "IBM-DYNAMIC",
        ]
        self.requested_device_type: Optional[str] = None
        self.negotiated_device_type: Optional[str] = None
        self.supported_functions: int = (
            TN3270E_BIND_IMAGE
            | TN3270E_DATA_STREAM_CTL
            | TN3270E_RESPONSES
            | TN3270E_SCS_CTL_CODES
        )
        self.negotiated_functions: int = 0
        self._next_seq_number: int = 0  # For outgoing SEQ-NUMBER
        self._pending_requests = {} # To store pending requests for response correlation
        self._device_type_is_event = asyncio.Event()
        self._functions_is_event = asyncio.Event()
        self._query_sf_response_event = asyncio.Event() # New event for Query SF response
        self._printer_status_event = asyncio.Event() # New event for printer status updates

    def _maybe_schedule_coro(self, coro) -> None:
        """
        Schedule a coroutine to run in the running event loop if one exists.

        This allows methods to remain synchronous while still invoking
        async helpers without requiring the caller to await them.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            # No running event loop in the current context (likely a sync unit test).
            # In that case, drop the background work — tests that need the result
            # should run in an async context.
            pass

    def _get_next_seq_number(self) -> int:
        """Get the next sequential number for TN3270E requests."""
        self._next_seq_number = (self._next_seq_number + 1) % 65536  # 16-bit sequence number
        return self._next_seq_number

    def _outgoing_request(self, request_type: str, data_type: int = TN3270_DATA, request_flag: int = 0, response_flag: int = TN3270E_RSF_POSITIVE_RESPONSE) -> TN3270EHeader:
        """
        Generates a TN3270E header for an outgoing request and stores it for correlation.

        Args:
            request_type: A string identifier for the type of request (e.g., "DEVICE-TYPE SEND", "FUNCTIONS SEND").
            data_type: The DATA-TYPE field of the TN3270E header.
            request_flag: The REQUEST-FLAG field of the TN3270E header.
            response_flag: The RESPONSE-FLAG field of the TN3270E header.

        Returns:
            The created TN3270EHeader object.
        """
        seq_number = self._get_next_seq_number()
        header = TN3270EHeader(data_type=data_type, request_flag=request_flag, response_flag=response_flag, seq_number=seq_number)
        self._pending_requests[seq_number] = {"type": request_type, "header": header}
        logger.debug(f"Outgoing request: {request_type} with SEQ-NUMBER {seq_number}, pending requests: {len(self._pending_requests)}")
        return header

    async def _handle_tn3270e_response(self, header: TN3270EHeader) -> None:
        """
        Handles an incoming TN3270E header, correlating it with pending requests.

        Args:
            header: The received TN3270EHeader object.
        """
        seq_number = header.seq_number
        if seq_number in self._pending_requests:
            request_info = self._pending_requests.pop(seq_number)
            request_type = request_info["type"]
            logger.debug(f"Correlated response for {request_type} with SEQ-NUMBER {seq_number}. Remaining pending requests: {len(self._pending_requests)}")

            # Process response based on request type and response flags
            if request_type == "DEVICE-TYPE SEND":
                if header.is_positive_response():
                    logger.debug("Received positive response for DEVICE-TYPE SEND.")
                elif header.is_negative_response():
                    logger.warning("Received negative response for DEVICE-TYPE SEND.")
                elif header.is_error_response():
                    logger.error("Received error response for DEVICE-TYPE SEND.")
                self._device_type_is_event.set()
            elif request_type == "FUNCTIONS SEND":
                if header.is_positive_response():
                    logger.debug("Received positive response for FUNCTIONS SEND.")
                elif header.is_negative_response():
                    logger.warning("Received negative response for FUNCTIONS SEND.")
                elif header.is_error_response():
                    logger.error("Received error response for FUNCTIONS SEND.")
                self._functions_is_event.set()
            else:
                logger.debug(f"Unhandled correlated response type: {request_type}")
        elif header.data_type == SNA_RESPONSE:
            logger.info(f"Received unsolicited SNA RESPONSE (SEQ-NUMBER: {seq_number}). Response flag: {header.get_response_flag_name()}")
            # If the SNA response is directly in a TN3270E header (unlikely for typical SNA,
            # but possible for simple host ACKs), we can log it here.
            # The actual parsing of detailed SNA response will happen in DataStreamParser
            # and then passed via _handle_sna_response.
        else:
            logger.warning(f"Received TN3270E header with unknown SEQ-NUMBER {seq_number}. Data type: {header.get_data_type_name()}, Response flag: {header.get_response_flag_name()}")
            # This could be an unsolicited response or a response to a request we didn't track.
            # Log and ignore as per instructions.

    async def negotiate(self) -> None:
        """
        Perform initial Telnet negotiation.

        Sends DO TERMINAL-TYPE and waits for responses.

        Raises:
            NegotiationError: If negotiation fails.
        """
        if self.writer is None:
            raise ProtocolError("Writer is None; cannot negotiate.")
        # Send IAC WILL TERMINAL-TYPE and IAC DO TERMINAL-TYPE
        send_iac(self.writer, b"\xfb\x18") # WILL TERMINAL-TYPE
        send_iac(self.writer, b"\xfd\x18") # DO TERMINAL-TYPE
        await self.writer.drain()
        # The response for TERMINAL-TYPE negotiation is handled by handle_iac_command

    async def _negotiate_tn3270(self, timeout: float = 5.0) -> None:
        """
        Negotiate TN3270E subnegotiation.

        Sends TN3270E request and waits for responses.

        Args:
            timeout: Maximum time to wait for negotiation responses.

        Raises:
            NegotiationError: On subnegotiation failure or timeout.
        """
        if self.writer is None:
            raise ProtocolError("Writer is None; cannot negotiate TN3270.")

        # Clear events before starting negotiation
        self._device_type_is_event.clear()
        self._functions_is_event.clear()

        # Send DEVICE-TYPE SEND subnegotiation to propose our supported types
        logger.info("Sending DEVICE-TYPE SEND for TN3270E negotiation.")
        self._outgoing_request("DEVICE-TYPE SEND")
        self._send_supported_device_types()
        await self.writer.drain()

        try:
            # Wait for DEVICE-TYPE IS response
            logger.debug(f"Waiting for DEVICE-TYPE IS response with timeout {timeout}s...")
            await asyncio.wait_for(self._device_type_is_event.wait(), timeout=timeout)
            logger.info(f"Received DEVICE-TYPE IS: {self.negotiated_device_type}")

            # Wait for FUNCTIONS IS response (if not already received)
            if not self._functions_is_event.is_set():
                logger.debug(f"Waiting for FUNCTIONS IS response with timeout {timeout}s...")
                await asyncio.wait_for(self._functions_is_event.wait(), timeout=timeout)
                logger.info(f"Received FUNCTIONS IS: 0x{self.negotiated_functions:02x}")

            self.negotiated_tn3270e = True
            logger.info("TN3270E negotiation successful.")

        except asyncio.TimeoutError:
            logger.warning(
                "TN3270E negotiation timed out. Falling back to ASCII/VT100 mode."
            )
            self.set_ascii_mode()
            self.negotiated_tn3270e = False
            raise NegotiationError("TN3270E negotiation timed out.")
        except Exception as e:
            logger.error(f"Error during TN3270E negotiation: {e}", exc_info=True)
            self.set_ascii_mode()
            self.negotiated_tn3270e = False
            raise NegotiationError(f"TN3270E negotiation failed: {e}")

    def set_ascii_mode(self) -> None:
        """
        Set to ASCII mode fallback, matching s3270 behavior.

        Disables EBCDIC processing and enables ASCII/VT100 terminal emulation.
        """
        logger.debug(
            f"BEFORE set_ascii_mode: _ascii_mode = {self._ascii_mode} on negotiator object {id(self)}"
        )
        self._ascii_mode = True
        logger.debug(
            f"AFTER set_ascii_mode: _ascii_mode = {self._ascii_mode} on negotiator object {id(self)}"
        )
        logger.info("Switched to ASCII/VT100 mode (s3270 compatibility)")

    async def _receive_data(self, timeout: float = 5.0) -> bytes:
        """
        Receive data with timeout (internal).

        Args:
            timeout: Receive timeout in seconds.

        Returns:
            Received bytes.

        Raises:
            asyncio.TimeoutError: If timeout exceeded.
        """
        if self.handler:
            return await self.handler.receive_data(timeout)
        raise NotImplementedError("Handler required for receiving data")

    async def _read_iac(self) -> bytes:
        """
        Read IAC sequence (internal).

        Returns:
            IAC response bytes.

        Raises:
            ParseError: If IAC parsing fails.
        """
        if self.handler:
            return await self.handler._read_iac()
        raise NotImplementedError("Handler required for reading IAC")

    async def handle_iac_command(self, command: int, option: int) -> None:
        """
        Handle incoming Telnet IAC commands (DO, DONT, WILL, WONT).

        Args:
            command: The IAC command (DO, DONT, WILL, WONT).
            option: The Telnet option associated with the command.
        """
        # Removed the local import, as it's now imported at the top of the file
        # from .utils import DO, DONT, WILL, WONT, TELOPT_TTYPE, TELOPT_BINARY, TELOPT_EOR, TELOPT_TN3270E

        if command == DO:
            logger.debug(f"Received IAC DO {option:#x}")
            if option == TELOPT_TTYPE: # Terminal Type
                send_iac(self.writer, bytes([WILL, TELOPT_TTYPE]))
            elif option == TELOPT_BINARY: # Binary Transmission
                send_iac(self.writer, bytes([WILL, TELOPT_BINARY]))
            elif option == TELOPT_EOR: # End of Record
                send_iac(self.writer, bytes([WILL, TELOPT_EOR]))
            elif option == TELOPT_TN3270E: # TN3270E
                send_iac(self.writer, bytes([WILL, TELOPT_TN3270E]))
            elif option == TELOPT_TERMINAL_LOCATION: # TERMINAL-LOCATION (RFC 1646)
                send_iac(self.writer, bytes([WILL, TELOPT_TERMINAL_LOCATION]))
                # If the server requests TERMINAL-LOCATION, we respond with our LU name
                await self._send_lu_name_is() # Await this call
            elif option == TELOPT_BIND_UNIT: # BIND-UNIT
                send_iac(self.writer, bytes([WILL, TELOPT_BIND_UNIT]))
            else:
                send_iac(self.writer, bytes([WONT, option]))
            await self.writer.drain() # Drain after sending IAC response
        elif command == DONT:
            logger.debug(f"Received IAC DONT {option:#x}")
            send_iac(self.writer, bytes([WONT, option]))
            await self.writer.drain()
        elif command == WILL:
            logger.debug(f"Received IAC WILL {option:#x}")
            if option == TELOPT_TTYPE:
                send_iac(self.writer, bytes([DO, TELOPT_TTYPE]))
            elif option == TELOPT_BINARY:
                send_iac(self.writer, bytes([DO, TELOPT_BINARY]))
            elif option == TELOPT_EOR:
                send_iac(self.writer, bytes([DO, TELOPT_EOR]))
            elif option == TELOPT_TN3270E:
                send_iac(self.writer, bytes([DO, TELOPT_TN3270E]))
            elif option == TELOPT_TERMINAL_LOCATION: # TERMINAL-LOCATION (RFC 1646)
                send_iac(self.writer, bytes([DO, TELOPT_TERMINAL_LOCATION]))
                # The host is telling us it WILL use TERMINAL-LOCATION, no action needed from client other than DO.
            elif option == TELOPT_BIND_UNIT: # BIND-UNIT
                send_iac(self.writer, bytes([DO, TELOPT_BIND_UNIT]))
            else:
                send_iac(self.writer, bytes([DONT, option]))
            await self.writer.drain()
        elif command == WONT:
            logger.debug(f"Received IAC WONT {option:#x}")
            send_iac(self.writer, bytes([DONT, option]))
            await self.writer.drain()

    async def _send_lu_name_is(self) -> None:
        """
        Sends the TERMINAL-LOCATION IS subnegotiation with the configured LU name.
        """
        if self.writer is None:
            logger.error("Cannot send LU name: writer is None")
            return

        lu_name_bytes = self._lu_name.encode("ascii") if self._lu_name else b""
        # The subnegotiation format is IAC SB <option> <suboption> <data> IAC SE
        # Here, <option> is TELOPT_TERMINAL_LOCATION, <suboption> is IS
        sub_data = bytes([TN3270E_IS]) + lu_name_bytes
        send_subnegotiation(self.writer, bytes([TELOPT_TERMINAL_LOCATION]), sub_data)
        logger.debug(f"Sent TERMINAL-LOCATION IS with LU name: {self._lu_name}")
        await self.writer.drain() # Ensure the data is sent immediately

    def is_printer_session_active(self) -> bool:
        """
        Check if this is a printer session.

        Returns:
            bool: True if printer session.
        """
        return self.is_printer_session

    @property
    def lu_name(self) -> Optional[str]:
        """Get the LU name."""
        return self._lu_name

    @lu_name.setter
    def lu_name(self, value: Optional[str]) -> None:
        """Set the LU name."""
        self._lu_name = value

    @property
    def is_data_stream_ctl_active(self) -> bool:
        """
        Check if DATA-STREAM-CTL function is active.
        """
        return bool(self.negotiated_functions & TN3270E_DATA_STREAM_CTL)

    async def handle_subnegotiation(self, option: int, data: bytes) -> None:
        """
        Handles incoming Telnet subnegotiation sequences.
        Dispatches to specific handlers based on the option.

        Args:
            option: The Telnet option for the subnegotiation.
            data: The subnegotiation data.
        """
        logger.debug(f"Received subnegotiation: Option=0x{option:02x}, Data={data.hex()}")

        if option == TELOPT_TN3270E:
            # Call the synchronous entry point which will schedule the async
            # parser as needed. Do not await the result here.
            self._parse_tn3270e_subnegotiation(data)
        elif option == TELOPT_TERMINAL_LOCATION:
            await self._handle_terminal_location_subnegotiation(data)
        elif option == TN3270E_SYSREQ_MESSAGE_TYPE:
            await self._handle_sysreq_subnegotiation(data)
        else:
            logger.debug(f"Unhandled subnegotiation option: 0x{option:02x} with data: {data.hex()}")

    def _parse_tn3270e_subnegotiation(self, data: bytes) -> None:
        """
        Synchronous entry point for TN3270E subnegotiation parsing.

        Tests call this method synchronously; internally we schedule the
        async implementation so existing async flows still work.
        """
        # Validate minimal length quickly
        if len(data) < 2:
            logger.warning(f"Invalid TN3270E subnegotiation data: {data.hex()}")
            return

        # Schedule the async parser to run in the background if needed
        try:
            coro = self._parse_tn3270e_subnegotiation_async(data)
            self._maybe_schedule_coro(coro)
        except Exception:
            # Fallback to calling the async function directly if scheduling fails
            try:
                import asyncio

                asyncio.run(self._parse_tn3270e_subnegotiation_async(data))
            except Exception:
                logger.exception("Failed to run TN3270E subnegotiation parser")

    async def _parse_tn3270e_subnegotiation_async(self, data: bytes) -> None:
        """
        Async implementation of TN3270E subnegotiation parsing.
        """
        # Parse subnegotiation header
        message_type = data[0] if len(data) > 0 else None
        message_subtype = data[1] if len(data) > 1 else None

        negotiation_types = [TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS]
        is_negotiation = message_type in negotiation_types if message_type is not None else False

        header_start = 2
        if not is_negotiation and len(data) >= header_start + 5 and message_type in [TN3270_DATA, SCS_DATA, RESPONSE, BIND_IMAGE, UNBIND, NVT_DATA, REQUEST, SSCP_LU_DATA, PRINT_EOJ]:
            tn3270e_header = TN3270EHeader.from_bytes(data[header_start:header_start+5])
            if tn3270e_header:
                await self._handle_tn3270e_response(tn3270e_header)
            else:
                logger.warning(f"Could not parse TN3270EHeader from subnegotiation data: {data.hex()}")

        if message_type == TN3270E_DEVICE_TYPE:
            await self._handle_device_type_subnegotiation_async(data[1:])
            self._device_type_is_event.set()
        elif message_type == TN3270E_FUNCTIONS:
            # FUNCTIONS handling can be synchronous for observers
            self._handle_functions_subnegotiation(data[1:])
            self._functions_is_event.set()
        elif message_type == BIND_IMAGE:
            logger.debug("Received BIND_IMAGE data type in TN3270E header. Data will be processed by DataStreamParser.")
        elif message_type == TN3270E_SYSREQ_MESSAGE_TYPE:
            await self._handle_sysreq_subnegotiation(data[1:])
        else:
            logger.debug(f"Unhandled TN3270E subnegotiation type: 0x{message_type:02x}")

    def _handle_device_type_subnegotiation(self, data: bytes) -> None:
        """
        Handle DEVICE-TYPE subnegotiation message.

        Args:
            data: DEVICE-TYPE subnegotiation data (message type already stripped)
        """
        # Quick validation
        if not data:
            logger.warning("Empty DEVICE-TYPE subnegotiation data")
            return

        sub_type = data[0]
        if sub_type == TN3270E_IS:
            # DEVICE-TYPE IS - server is telling us what device type to use
            if len(data) > 1:
                device_type_bytes = data[1:]
                null_pos = device_type_bytes.find(0x00)
                if null_pos != -1:
                    device_type_bytes = device_type_bytes[:null_pos]

                device_type = device_type_bytes.decode("ascii", errors="ignore").strip()
                logger.info(f"Server requested device type: {device_type}")

                if device_type == TN3270E_IBM_DYNAMIC:
                    logger.info("IBM-DYNAMIC device type negotiated")
                    self.negotiated_device_type = TN3270E_IBM_DYNAMIC
                    # Schedule query for device characteristics; may run async
                    try:
                        coro = self._send_query_sf(self.writer, 0x02)
                        # _send_query_sf is synchronous, but it may call async drains internally
                        # so we schedule it conservatively
                        self._maybe_schedule_coro(coro)
                    except Exception:
                        # Fallback: call directly if scheduling fails
                        try:
                            import asyncio

                            asyncio.run(self._send_query_sf(self.writer, 0x02))
                        except Exception:
                            logger.exception("Failed to send QUERY SF for IBM-DYNAMIC")
                else:
                    self.negotiated_device_type = device_type
        elif sub_type == TN3270E_REQUEST:
            logger.info("Server requested supported device types")
            self._send_supported_device_types()
        elif sub_type == TN3270E_SEND:
            logger.debug("Received DEVICE-TYPE SEND (echo from mock server?)")
        else:
            logger.warning(f"Unhandled DEVICE-TYPE subnegotiation subtype: 0x{sub_type:02x}")

    def _handle_functions_subnegotiation(self, data: bytes) -> None:
        """
        Handle FUNCTIONS subnegotiation message.

        Args:
            data: FUNCTIONS subnegotiation data (message type already stripped)
        """
        if not data: # Ensure data is not empty
            logger.warning("Empty FUNCTIONS subnegotiation data")
            return

        sub_type = data[0]
        if sub_type == TN3270E_IS:
            if len(data) > 1:
                function_bits = 0
                for i in range(1, len(data)):
                    function_bits |= data[i]

                logger.info(f"Server enabled functions: 0x{function_bits:02x}")
                self.negotiated_functions = function_bits

                # Log specific functions
                if function_bits & TN3270E_BIND_IMAGE:
                    logger.debug("BIND-IMAGE function enabled")
                if function_bits & TN3270E_DATA_STREAM_CTL:
                    logger.debug("DATA-STREAM-CTL function enabled")
                if function_bits & TN3270E_RESPONSES:
                    logger.debug("RESPONSES function enabled")
                if function_bits & TN3270E_SCS_CTL_CODES:
                    logger.debug("SCS-CTL-CODES function enabled")
                if function_bits & TN3270E_SYSREQ:
                    logger.debug("SYSREQ function enabled")
                if self.negotiated_device_type == TN3270E_IBM_DYNAMIC:
                    logger.info("IBM-DYNAMIC negotiated, consider dynamic screen sizing.")
        elif sub_type == TN3270E_REQUEST:
            logger.info("Server requested supported functions")
            self._send_supported_functions()
        else:
            logger.warning(f"Unhandled FUNCTIONS subnegotiation subtype: 0x{sub_type:02x}")

    def _send_supported_device_types(self) -> None:
        """Send our supported device types to the server."""
        if self.writer is None:
            logger.error("Cannot send device types: writer is None")
            return

        # Send DEVICE-TYPE SEND response with our supported types
        # For simplicity, we'll send all supported types
        device_type_bytes = b""
        for dev_type in self.supported_device_types:
            device_type_bytes += dev_type.encode("ascii") + b"\x00" # Null-terminated strings

        sub_data = bytes([TN3270E_DEVICE_TYPE, TN3270E_SEND]) + device_type_bytes
        send_subnegotiation(self.writer, bytes([0x28]), sub_data)
        logger.debug(f"Sent supported device types: {self.supported_device_types}")

    def _send_supported_functions(self) -> None:
        """Send our supported functions to the server."""
        if self.writer is None:
            logger.error("Cannot send functions: writer is None")
            return

        # Send FUNCTIONS SEND response with our supported functions
        function_bytes = [
            (self.supported_functions >> i) & 0xFF
            for i in range(0, 8, 8)
            if (self.supported_functions >> i) & 0xFF
        ]

        if function_bytes:
            sub_data = bytes([TN3270E_FUNCTIONS, TN3270E_SEND] + function_bytes)
            send_subnegotiation(self.writer, bytes([0x28]), sub_data)
            logger.debug(f"Sent supported functions: 0x{self.supported_functions:02x}")

    def _send_query_sf(self, writer, query_type: int) -> None:
        """
        Sends a Query Structured Field to the host.
        """
        from .data_stream import DataStreamSender
        sender = DataStreamSender()
        query_sf = sender.build_query_sf(query_type)
        send_subnegotiation(writer, bytes([0x28]), query_sf) # 0x28 is TN3270E option
        logger.debug(f"Sent Query SF for type: 0x{query_type:02x}")

    def _set_screen_dimensions_from_query_reply(self, rows: int, cols: int) -> None:
        """
        Updates the screen dimensions based on a received Query Reply Structured Field.
        This method is intended to be called by the DataStreamParser.

        Args:
            rows: The number of rows received from the Query Reply.
            cols: The number of columns received from the Query Reply.
        """
        logger.info(f"Updating screen dimensions from Query Reply: {rows}x{cols}")
        self.screen_rows = rows
        self.screen_cols = cols
        self.screen_buffer.rows = rows
        self.screen_buffer.cols = cols
        self.screen_buffer.size = rows * cols
        # Reinitialize buffer and attributes with new size
        self.screen_buffer.buffer = bytearray(b"\x40" * self.screen_buffer.size)
        self.screen_buffer.attributes = bytearray(self.screen_buffer.size * 3)
        self._query_sf_response_event.set()

    def update_printer_status(self, status_code: int) -> None:
        """
        Updates the internal printer status and sets an event.
        """
        logger.info(f"Updating printer status: 0x{status_code:02x}")
        self.printer_status = status_code
        self._printer_status_event.set()

    def _set_sna_session_state(self, new_state: SnaSessionState) -> None:
        """
        Updates the SNA session state.
        """
        if self._sna_session_state != new_state:
            logger.info(f"SNA Session State changed from {self._sna_session_state.value} to {new_state.value}")
            self._sna_session_state = new_state

    def _handle_sna_response(self, sna_response: SnaResponse) -> None:
        """
        Handles incoming SNA response objects from the DataStreamParser.
        This method implements the state machine logic based on SNA responses.
        """
        logger.info(f"Negotiator handling SNA Response: {sna_response}")

        if sna_response.is_positive():
            self._set_sna_session_state(SnaSessionState.NORMAL)
            logger.debug("SNA Response: Positive acknowledgment.")
            # Additional actions for positive response can be added here
            # e.g., clear error flags, confirm pending operations
        elif sna_response.is_negative():
            logger.warning(f"SNA Response: Negative acknowledgment. Sense Code: {sna_response.get_sense_code_name()}")
            # Transition state based on specific sense codes
            if sna_response.sense_code == SNA_SENSE_CODE_SESSION_FAILURE:
                self._set_sna_session_state(SnaSessionState.SESSION_DOWN)
                logger.error("SNA Session Failure detected. Session likely down.")
                # Trigger session termination or re-establishment attempt
            elif sna_response.sense_code == SNA_SENSE_CODE_LU_BUSY:
                self._set_sna_session_state(SnaSessionState.LU_BUSY)
                logger.warning("LU Busy. Retransmit or wait for LU available.")
                # Implement retransmission logic or back-off strategy
            elif sna_response.sense_code == SNA_SENSE_CODE_INVALID_SEQUENCE:
                self._set_sna_session_state(SnaSessionState.INVALID_SEQUENCE)
                logger.error("Invalid sequence. Protocol error, re-sync might be needed.")
                # Log error, potentially reset sequence numbers, or terminate session
            elif sna_response.sense_code == SNA_SENSE_CODE_STATE_ERROR:
                self._set_sna_session_state(SnaSessionState.STATE_ERROR)
                logger.error("SNA State Error. Unsynchronized state, recovery needed.")
                # Attempt recovery actions if defined, otherwise log and alert
            else:
                self._set_sna_session_state(SnaSessionState.ERROR)
                logger.error(f"Generic SNA Error: {sna_response.get_sense_code_name()}.")
            # In all negative cases, consider logging full details for diagnostics
            logger.debug(f"SNA Response details: {sna_response}")

        else:
            logger.info(f"SNA Response: Neither positive nor negative. Type: {sna_response.get_response_type_name()}")
            # Handle other types of SNA responses if necessary,
            # e.g., informational messages, status updates that don't imply error or success.

    @property
    def current_sna_session_state(self) -> SnaSessionState:
        """Get the current SNA session state."""
        return self._sna_session_state

    @property
    def is_bind_image_active(self) -> bool:
        """
        Check if BIND-IMAGE function is active.
        """
        return bool(self.negotiated_functions & TN3270E_BIND_IMAGE)

    def handle_bind_image(self, bind_image: BindImage) -> None:
        """Handle BIND-IMAGE structured field."""
        if bind_image.rows:
            self.screen_buffer.rows = bind_image.rows
            self.screen_rows = bind_image.rows
        if bind_image.cols:
            self.screen_buffer.cols = bind_image.cols
            self.screen_cols = bind_image.cols
        logger.info(f"Updated screen dimensions from BIND-IMAGE: {self.screen_rows}x{self.screen_cols}")

    async def _handle_terminal_location_subnegotiation(self, data: bytes) -> None:
        """
        Handle incoming TERMINAL-LOCATION subnegotiation message.
        This is typically used by the host to assign an LU name.

        Args:
            data: TERMINAL-LOCATION subnegotiation data.
        """
        if not data:
            logger.warning("Empty TERMINAL-LOCATION subnegotiation data.")
            return

        sub_type = data[0]
        if sub_type == TN3270E_IS: # Host is telling us the LU name
            if len(data) > 1:
                lu_name_bytes = data[1:]
                # Find null terminator if present
                null_pos = lu_name_bytes.find(0x00)
                if null_pos != -1:
                    lu_name_bytes = lu_name_bytes[:null_pos]
                
                try:
                    lu_name = lu_name_bytes.decode("ascii").strip()
                    self.lu_name = lu_name
                    logger.info(f"Received LU name from host: {self.lu_name}")
                except UnicodeDecodeError:
                    logger.warning(f"Could not decode LU name: {lu_name_bytes.hex()}")
            else:
                logger.warning("Empty LU name in TERMINAL-LOCATION IS subnegotiation.")
        elif sub_type == TN3270E_REQUEST: # Host is asking for our LU name
            logger.info("Host requested LU name. Sending configured LU name.")
            await self._send_lu_name_is()
        else:
            logger.debug(f"Unhandled TERMINAL-LOCATION subnegotiation subtype: 0x{sub_type:02x}")


    async def _handle_sysreq_subnegotiation(self, data: bytes) -> None:
        """
        Handle incoming SYSREQ subnegotiation message.

        Args:
            data: SYSREQ subnegotiation data (message type already stripped).
        """
        if not data:
            logger.warning("Empty SYSREQ subnegotiation data")
            return

        sysreq_command_code = data[0]
        sysreq_command_name = "UNKNOWN"

        # Map command codes back to names for logging
        if sysreq_command_code == TN3270E_SYSREQ_ATTN:
            sysreq_command_name = "ATTN"
        elif sysreq_command_code == TN3270E_SYSREQ_BREAK:
            sysreq_command_name = "BREAK"
        elif sysreq_command_code == TN3270E_SYSREQ_CANCEL:
            sysreq_command_name = "CANCEL"
        elif sysreq_command_code == TN3270E_SYSREQ_RESTART:
            sysreq_command_name = "RESTART"
        elif sysreq_command_code == TN3270E_SYSREQ_PRINT:
            sysreq_command_name = "PRINT"
        elif sysreq_command_code == TN3270E_SYSREQ_LOGOFF:
            sysreq_command_name = "LOGOFF"

        logger.info(f"Received SYSREQ command: {sysreq_command_name} (0x{sysreq_command_code:02x})")
        # Further actions based on SYSREQ command can be added here.
        # For now, just logging is sufficient as per the task.
