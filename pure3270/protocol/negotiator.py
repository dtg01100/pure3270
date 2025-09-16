"""
Negotiator for TN3270 protocol specifics.
Handles Telnet negotiation and TN3270E subnegotiation.
"""

import asyncio
import logging
from enum import Enum  # Import Enum for state management
from typing import TYPE_CHECKING, List, Optional

from ..emulation.screen_buffer import ScreenBuffer
from .data_stream import (  # Import SnaResponse and BindImage
    SNA_SENSE_CODE_INVALID_FORMAT,
    SNA_SENSE_CODE_INVALID_REQUEST,
    SNA_SENSE_CODE_INVALID_SEQUENCE,
    SNA_SENSE_CODE_LU_BUSY,
    SNA_SENSE_CODE_NO_RESOURCES,
    SNA_SENSE_CODE_NOT_SUPPORTED,
    SNA_SENSE_CODE_SESSION_FAILURE,
    SNA_SENSE_CODE_STATE_ERROR,
    SNA_SENSE_CODE_SUCCESS,
    BindImage,
    DataStreamParser,
    SnaResponse,
)
from .errors import (
    handle_drain,
    raise_negotiation_error,
    raise_protocol_error,
    safe_socket_operation,
)
from .exceptions import NegotiationError, ParseError, ProtocolError
from .utils import SNA_RESPONSE  # Import SNA_RESPONSE
from .utils import TELOPT_BIND_UNIT  # TELOPT 48
from .utils import DO, DONT, QUERY_REPLY_CHARACTERISTICS, TELOPT_BINARY, TELOPT_EOR
from .utils import (
    TELOPT_OLD_ENVIRON as TELOPT_TERMINAL_LOCATION,
)  # Alias for RFC 1646 (TELOPT 36)
from .utils import (
    TELOPT_TN3270E,
    TELOPT_TTYPE,
    TN3270E_BIND_IMAGE,
    TN3270E_DATA_STREAM_CTL,
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IBM_DYNAMIC,
    TN3270E_IS,
    TN3270E_REQUEST,
    TN3270E_RESPONSES,
    TN3270E_RSF_ERROR_RESPONSE,
    TN3270E_RSF_NEGATIVE_RESPONSE,
    TN3270E_RSF_POSITIVE_RESPONSE,
    TN3270E_SCS_CTL_CODES,
    TN3270E_SEND,
    TN3270E_SYSREQ,
    TN3270E_SYSREQ_ATTN,
    TN3270E_SYSREQ_BREAK,
    TN3270E_SYSREQ_CANCEL,
    TN3270E_SYSREQ_LOGOFF,
    TN3270E_SYSREQ_MESSAGE_TYPE,
    TN3270E_SYSREQ_PRINT,
    TN3270E_SYSREQ_RESTART,
    WILL,
    WONT,
    send_iac,
    send_subnegotiation,
)

if TYPE_CHECKING:
    from .tn3270_handler import TN3270Handler

logger = logging.getLogger(__name__)

from .tn3270e_header import TN3270EHeader
from .utils import (
    BIND_IMAGE,
    NVT_DATA,
    PRINT_EOJ,
    REQUEST,
    RESPONSE,
    SCS_DATA,
    SSCP_LU_DATA,
    TN3270_DATA,
    TN3270E_RSF_ALWAYS_RESPONSE,
    TN3270E_RSF_ERROR_RESPONSE,
    TN3270E_RSF_NEGATIVE_RESPONSE,
    TN3270E_RSF_NO_RESPONSE,
    TN3270E_RSF_POSITIVE_RESPONSE,
    UNBIND,
)


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
        force_mode: Optional[str] = None,
        allow_fallback: bool = True,
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
        logger.info(
            f"Negotiator created: id={id(self)}, writer={writer}, parser={parser}, screen_buffer={screen_buffer}, handler={handler}, is_printer_session={is_printer_session}"
        )
        self.writer = writer
        self.parser = parser
        self.screen_buffer = screen_buffer
        self.handler = handler
        self._ascii_mode = False
        logger.debug(f"Negotiator._ascii_mode initialized to {self._ascii_mode}")
        # Mode negotiation / override controls
        self.force_mode = (force_mode or None) if force_mode else None
        if self.force_mode not in (None, "ascii", "tn3270", "tn3270e"):
            raise ValueError(
                "force_mode must be one of None, 'ascii', 'tn3270', 'tn3270e'"
            )
        self.allow_fallback = allow_fallback
        self.negotiated_tn3270e = False
        self._lu_name: Optional[str] = None
        self.screen_rows = 24
        self.screen_cols = 80
        self.is_printer_session = is_printer_session
        self.printer_status: Optional[int] = None  # New attribute for printer status
        self._sna_session_state: SnaSessionState = (
            SnaSessionState.NORMAL
        )  # Initial SNA session state
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
            "IBM-3287-P",  # Printer LU type for 3287 printer emulation
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
        self._pending_requests = (
            {}
        )  # To store pending requests for response correlation
        self._device_type_is_event = asyncio.Event()
        self._functions_is_event = asyncio.Event()
        self._negotiation_complete = (
            asyncio.Event()
        )  # Event for full negotiation completion
        self._query_sf_response_event = (
            asyncio.Event()
        )  # New event for Query SF response
        self._printer_status_event = (
            asyncio.Event()
        )  # New event for printer status updates
        # Internal flag to signal forced failure (e.g., server refusal when fallback disabled)
        self._forced_failure: bool = False
        # Buffer to accumulate negotiation bytes when inference is needed (e.g., tests)
        self._negotiation_trace: bytes | None = None

    # ------------------------------------------------------------------
    # Inference / compatibility helpers
    # ------------------------------------------------------------------
    def infer_tn3270e_from_trace(self, trace: bytes) -> bool:
        """Infer TN3270E negotiation success from raw Telnet negotiation bytes.

        This mirrors the temporary heuristic previously implemented in the
        handler. We keep it here so that test fixtures can rely on a single
        canonical implementation and the handler stays slim.

        Rules:
          1. If IAC WONT TN3270E (FF FC 24) appears => failure (False).
          2. Else if IAC WILL EOR (FF FB 19) appears => success (True).
          3. Otherwise => False.

        The heuristic is intentionally conservative; explicit refusal always
        wins over implied success.
        """
        if not trace:
            return False
        try:
            if b"\xff\xfc\x24" in trace:
                return False
            if b"\xff\xfb\x19" in trace:
                return True
        except Exception:
            pass
        return False

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
            # No running event loop; run synchronously for tests
            asyncio.run(coro)

    def _get_next_seq_number(self) -> int:
        """Get the next sequential number for TN3270E requests."""
        self._next_seq_number = (
            self._next_seq_number + 1
        ) % 65536  # 16-bit sequence number
        return self._next_seq_number

    def _outgoing_request(
        self,
        request_type: str,
        data_type: int = TN3270_DATA,
        request_flag: int = 0,
        response_flag: int = TN3270E_RSF_POSITIVE_RESPONSE,
    ) -> TN3270EHeader:
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
        header = TN3270EHeader(
            data_type=data_type,
            request_flag=request_flag,
            response_flag=response_flag,
            seq_number=seq_number,
        )
        self._pending_requests[seq_number] = {"type": request_type, "header": header}
        logger.debug(
            f"Outgoing request: {request_type} with SEQ-NUMBER {seq_number}, pending requests: {len(self._pending_requests)}"
        )
        return header

    async def _handle_tn3270e_response(self, header: TN3270EHeader) -> None:
        """
        Handles an incoming TN3270E header, correlating it with pending requests.

        Args:
            header: The received TN3270EHeader object.
        """
        logger.debug(
            f"Entered _handle_tn3270e_response with header: data_type=0x{header.data_type:02x}, seq_number={header.seq_number}, request_flag=0x{header.request_flag:02x}, response_flag=0x{header.response_flag:02x}"
        )
        seq_number = header.seq_number
        if seq_number in self._pending_requests:
            request_info = self._pending_requests.pop(seq_number)
            request_type = request_info["type"]
            logger.debug(
                f"Correlated response for {request_type} with SEQ-NUMBER {seq_number}. Remaining pending requests: {len(self._pending_requests)}"
            )

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
            logger.info(
                f"Received unsolicited SNA RESPONSE (SEQ-NUMBER: {seq_number}). Response flag: {header.get_response_flag_name()}"
            )
            # If the SNA response is directly in a TN3270E header (unlikely for typical SNA,
            # but possible for simple host ACKs), we can log it here.
            # The actual parsing of detailed SNA response will happen in DataStreamParser
            # and then passed via _handle_sna_response.
        else:
            logger.warning(
                f"Received TN3270E header with unknown SEQ-NUMBER {seq_number}. Data type: {header.get_data_type_name()}, Response flag: {header.get_response_flag_name()}"
            )
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
        async with safe_socket_operation():
            logger.info(
                "[NEGOTIATION] Sending IAC WILL TERMINAL-TYPE and IAC DO TERMINAL-TYPE"
            )
            send_iac(self.writer, b"\xfb\x18")  # WILL TERMINAL-TYPE
            logger.debug("[NEGOTIATION] Sent IAC WILL TERMINAL-TYPE (fb 18)")
            send_iac(self.writer, b"\xfd\x18")  # DO TERMINAL-TYPE
            logger.debug("[NEGOTIATION] Sent IAC DO TERMINAL-TYPE (fd 18)")
            # Per RFC 1091, after TTYPE negotiation, wait for the server to initiate BINARY/EOR/TN3270E negotiation.
            await self.writer.drain()
            logger.info(
                "[NEGOTIATION] Initial TTYPE negotiation commands sent. Awaiting server response..."
            )
        # The response for further negotiation is handled by handle_iac_command

    async def _negotiate_tn3270(self, timeout: float = 10.0) -> None:
        """
        Negotiate TN3270E subnegotiation.
        Waits for server-initiated SEND and responds via handle_subnegotiation.

        Args:
            timeout: Maximum time to wait for negotiation responses.

        Raises:
            NegotiationError: On subnegotiation failure or timeout.
        """
        # Short-circuit for forced modes that do not require TN3270E negotiation
        if self.force_mode == "ascii":
            logger.info(
                "[NEGOTIATION] force_mode=ascii specified; skipping TN3270E negotiation and enabling ASCII mode."
            )
            self.set_ascii_mode()
            self.negotiated_tn3270e = False
            for ev in (
                self._device_type_is_event,
                self._functions_is_event,
                self._negotiation_complete,
            ):
                ev.set()
            return
        if self.force_mode == "tn3270":
            logger.info(
                "[NEGOTIATION] force_mode=tn3270 specified; skipping TN3270E negotiation (basic TN3270 only)."
            )
            self.negotiated_tn3270e = False
            # Events set so upstream waits proceed
            for ev in (
                self._device_type_is_event,
                self._functions_is_event,
                self._negotiation_complete,
            ):
                ev.set()
            return

        if self.writer is None:
            raise ProtocolError("Writer is None; cannot negotiate TN3270.")

        # Clear events before starting negotiation
        self._device_type_is_event.clear()
        self._functions_is_event.clear()
        self._negotiation_complete.clear()

        logger.info(
            "[NEGOTIATION] Starting TN3270E negotiation: waiting for server DEVICE-TYPE SEND."
        )

        try:
            async with safe_socket_operation():
                # Wait for each event with per-step timeout
                logger.debug(
                    f"[NEGOTIATION] Waiting for DEVICE-TYPE with per-event timeout 5.0s..."
                )
                await asyncio.wait_for(self._device_type_is_event.wait(), timeout=5.0)
                logger.debug(
                    f"[NEGOTIATION] Waiting for FUNCTIONS with per-event timeout 5.0s..."
                )
                await asyncio.wait_for(self._functions_is_event.wait(), timeout=5.0)
                # Overall wait for completion
                logger.debug(
                    f"[NEGOTIATION] Waiting for full TN3270E negotiation with timeout {timeout}s..."
                )
                await asyncio.wait_for(self._negotiation_complete.wait(), timeout=5.0)
                logger.info(
                    f"[NEGOTIATION] TN3270E negotiation complete: device={self.negotiated_device_type}, functions=0x{self.negotiated_functions:02x}"
                )

                # Add SNA response handling post-BIND for printer LU types
                if self.is_printer_session:
                    logger.debug(
                        "[NEGOTIATION] Printer session: awaiting SNA response post-BIND"
                    )
                    # Stub for SNA response handling in printer session
                    if self.parser:
                        # Simulate a positive SNA response for BIND in printer session
                        from .data_stream import (
                            SNA_COMMAND_RESPONSE,
                            SNA_FLAGS_RSP,
                            SNA_SENSE_CODE_SUCCESS,
                            SnaResponse,
                        )

                        sna_response = SnaResponse(
                            SNA_COMMAND_RESPONSE, SNA_FLAGS_RSP, SNA_SENSE_CODE_SUCCESS
                        )
                        self._handle_sna_response(sna_response)
                    logger.debug(
                        "[NEGOTIATION] SNA response for printer BIND handled (stub)"
                    )

                # If ASCII mode was set (e.g., due to a WONT), do not mark TN3270E as negotiated.
                if getattr(self, "_ascii_mode", False):
                    logger.info(
                        "[NEGOTIATION] ASCII mode active; skipping TN3270E negotiated flag."
                    )
                    self.negotiated_tn3270e = False
                else:
                    self.negotiated_tn3270e = True
                    logger.info("[NEGOTIATION] TN3270E negotiation successful.")

        except asyncio.TimeoutError:
            if self.force_mode == "tn3270e" and not self.allow_fallback:
                logger.error(
                    "[NEGOTIATION] TN3270E negotiation timed out and fallback disabled (force_mode=tn3270e); raising error."
                )
                # Ensure events are set so any awaiters unblock
                for ev in (
                    self._device_type_is_event,
                    self._functions_is_event,
                    self._negotiation_complete,
                ):
                    ev.set()
                raise_negotiation_error(
                    "TN3270E negotiation timed out (fallback disabled)"
                )
            logger.warning(
                "[NEGOTIATION] TN3270E negotiation timed out. Falling back to ASCII/VT100 mode."
            )
            if self.allow_fallback:
                self.set_ascii_mode()
            self.negotiated_tn3270e = False
            for ev in (
                self._device_type_is_event,
                self._functions_is_event,
                self._negotiation_complete,
            ):
                ev.set()
            raise_negotiation_error("TN3270E negotiation timed out")
        except asyncio.CancelledError:
            # Treat cancellation as a benign event (e.g. session close) without noisy traceback
            logger.debug("[NEGOTIATION] TN3270E negotiation task cancelled")
            # Propagate so upstream logic (e.g. context manager) can respond appropriately
            raise
        except Exception as e:
            # If a forced failure has been recorded (e.g., WONT TN3270E with fallback disabled)
            if (
                self._forced_failure
                and self.force_mode == "tn3270e"
                and not self.allow_fallback
            ):
                logger.error(
                    f"[NEGOTIATION] TN3270E negotiation explicitly refused and fallback disabled: {e}"
                )
                for ev in (
                    self._device_type_is_event,
                    self._functions_is_event,
                    self._negotiation_complete,
                ):
                    ev.set()
                raise_negotiation_error(
                    "TN3270E negotiation refused by host (fallback disabled)", e
                )
            logger.error(
                f"[NEGOTIATION] Error during TN3270E negotiation: {e}", exc_info=True
            )
            if self.allow_fallback:
                self.set_ascii_mode()
            self.negotiated_tn3270e = False
            for ev in (
                self._device_type_is_event,
                self._functions_is_event,
                self._negotiation_complete,
            ):
                ev.set()
            raise_negotiation_error(f"TN3270E negotiation failed: {e}", e)

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
        # Propagate to handler if present
        if self.handler:
            self.handler._ascii_mode = True
            logger.debug(f"Propagated ASCII mode to handler {id(self.handler)}")
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
        # Log the raw IAC command and option for debugging
        logger.debug(
            f"Negotiator.handle_iac_command called with command=0x{command:02x}, option=0x{option:02x}"
        )
        """
        Handle incoming Telnet IAC commands (DO, DONT, WILL, WONT).

        Args:
            command: The IAC command (DO, DONT, WILL, WONT).
            option: The Telnet option associated with the command.
        """
        logger.info(
            f"[NEGOTIATION] Received IAC command: {command:#x}, option: {option:#x}"
        )
        if command == DO:
            logger.debug(f"[NEGOTIATION] Received IAC DO {option:#x}")
            if option == TELOPT_TTYPE:  # Terminal Type
                logger.info(
                    "[NEGOTIATION] Sending IAC WILL TTYPE in response to DO TTYPE"
                )
                send_iac(self.writer, bytes([WILL, TELOPT_TTYPE]))
            elif option == TELOPT_BINARY:  # Binary Transmission
                logger.info(
                    "[NEGOTIATION] Sending IAC WILL BINARY in response to DO BINARY"
                )
                send_iac(self.writer, bytes([WILL, TELOPT_BINARY]))
            elif option == TELOPT_EOR:  # End of Record
                logger.info("[NEGOTIATION] Sending IAC WILL EOR in response to DO EOR")
                send_iac(self.writer, bytes([WILL, TELOPT_EOR]))
            elif option == TELOPT_TN3270E:  # TN3270E
                logger.info(
                    "[NEGOTIATION] Sending IAC WILL TN3270E in response to DO TN3270E"
                )
                send_iac(self.writer, bytes([WILL, TELOPT_TN3270E]))
            elif option == TELOPT_TERMINAL_LOCATION:  # TERMINAL-LOCATION (RFC 1646)
                logger.info(
                    "[NEGOTIATION] Sending IAC WILL TERMINAL-LOCATION in response to DO TERMINAL-LOCATION"
                )
                send_iac(self.writer, bytes([WILL, TELOPT_TERMINAL_LOCATION]))
                # If the server requests TERMINAL-LOCATION, we respond with our LU name
                await self._send_lu_name_is()
            elif option == TELOPT_BIND_UNIT:  # BIND-UNIT
                logger.info(
                    "[NEGOTIATION] Sending IAC WILL BIND-UNIT in response to DO BIND-UNIT"
                )
                send_iac(self.writer, bytes([WILL, TELOPT_BIND_UNIT]))
            else:
                logger.info(
                    f"[NEGOTIATION] Sending IAC WONT {option:#x} in response to DO {option:#x}"
                )
                send_iac(self.writer, bytes([WONT, option]))
            # Attempt to drain if available; if writer.drain is a MagicMock/AsyncMock
            # tests will handle awaiting it; otherwise await to flush network buffers.
            if hasattr(self.writer, "drain"):
                await self.writer.drain()
        elif command == DONT:
            logger.info(f"[NEGOTIATION] Received IAC DONT {option:#x}")
            send_iac(self.writer, bytes([WONT, option]))
            if hasattr(self.writer, "drain"):
                await self.writer.drain()
        elif command == WILL:
            logger.info(f"[NEGOTIATION] Received IAC WILL {option:#x}")
            if option == TELOPT_TTYPE:
                logger.info(
                    "[NEGOTIATION] Sending IAC DO TTYPE in response to WILL TTYPE"
                )
                send_iac(self.writer, bytes([DO, TELOPT_TTYPE]))
            elif option == TELOPT_BINARY:
                logger.info(
                    "[NEGOTIATION] Sending IAC DO BINARY in response to WILL BINARY"
                )
                send_iac(self.writer, bytes([DO, TELOPT_BINARY]))
            elif option == TELOPT_EOR:
                logger.info("[NEGOTIATION] Sending IAC DO EOR in response to WILL EOR")
                send_iac(self.writer, bytes([DO, TELOPT_EOR]))
            elif option == TELOPT_TN3270E:
                logger.info(
                    "[NEGOTIATION] Sending IAC DO TN3270E in response to WILL TN3270E"
                )
                send_iac(self.writer, bytes([DO, TELOPT_TN3270E]))
            elif option == TELOPT_TERMINAL_LOCATION:  # TERMINAL-LOCATION (RFC 1646)
                logger.info(
                    "[NEGOTIATION] Sending IAC DO TERMINAL-LOCATION in response to WILL TERMINAL-LOCATION"
                )
                send_iac(self.writer, bytes([DO, TELOPT_TERMINAL_LOCATION]))
                # The host is telling us it WILL use TERMINAL-LOCATION, no action needed from client other than DO.
            elif option == TELOPT_BIND_UNIT:  # BIND-UNIT
                logger.info(
                    "[NEGOTIATION] Sending IAC DO BIND-UNIT in response to WILL BIND-UNIT"
                )
                send_iac(self.writer, bytes([DO, TELOPT_BIND_UNIT]))
            else:
                logger.info(
                    f"[NEGOTIATION] Sending IAC DONT {option:#x} in response to WILL {option:#x}"
                )
                send_iac(self.writer, bytes([DONT, option]))
            if hasattr(self.writer, "drain"):
                await self.writer.drain()
        elif command == WONT:
            logger.info(f"[NEGOTIATION] Received IAC WONT {option:#x}")
            send_iac(self.writer, bytes([DONT, option]))
            if hasattr(self.writer, "drain"):
                await self.writer.drain()
            # If the remote explicitly refuses TN3270E (or related terminal/location option),
            # immediately fallback so negotiation doesn't hang waiting for TN3270E subnegotiation replies.
            if option in (TELOPT_TN3270E, TELOPT_TERMINAL_LOCATION):
                if self.force_mode == "tn3270e" and not self.allow_fallback:
                    logger.error(
                        f"Remote refused TN3270E/TERMINAL-LOCATION (WONT 0x{option:02x}); fallback disabled (force_mode=tn3270e)."
                    )
                    self._forced_failure = True
                    # Unblock waiters so negotiation routine can raise
                    for ev in (
                        self._device_type_is_event,
                        self._functions_is_event,
                        self._negotiation_complete,
                    ):
                        try:
                            ev.set()
                        except Exception:
                            pass
                elif self.force_mode == "tn3270":
                    # In forced basic TN3270 mode, ignore refusal of TN3270E without falling back to ASCII.
                    logger.info(
                        f"Remote refused TN3270E (WONT 0x{option:02x}); continuing in forced basic TN3270 mode."
                    )
                    for ev in (
                        self._device_type_is_event,
                        self._functions_is_event,
                        self._negotiation_complete,
                    ):
                        try:
                            ev.set()
                        except Exception:
                            pass
                else:
                    logger.info(
                        f"Remote refused TN3270E/TERMINAL-LOCATION (WONT 0x{option:02x}) -- falling back to ASCII/VT100 mode"
                    )
                    if self.allow_fallback:
                        self.set_ascii_mode()
                    self.negotiated_tn3270e = False
                    # Unblock any waiters so negotiation can complete/fallback
                    for ev in (
                        self._device_type_is_event,
                        self._functions_is_event,
                        self._negotiation_complete,
                    ):
                        try:
                            ev.set()
                        except Exception:
                            pass

    @handle_drain
    async def _send_lu_name_is(self) -> None:
        """
        Sends the TERMINAL-LOCATION IS subnegotiation with the configured LU name.
        """
        if self.writer is None:
            raise_protocol_error("Cannot send LU name: writer is None")

        lu_name_bytes = self._lu_name.encode("ascii") if self._lu_name else b""
        # The subnegotiation format is IAC SB <option> <suboption> <data> IAC SE
        # Here, <option> is TELOPT_TERMINAL_LOCATION, <suboption> is IS
        sub_data = bytes([TN3270E_IS]) + lu_name_bytes
        send_subnegotiation(self.writer, bytes([TELOPT_TERMINAL_LOCATION]), sub_data)
        logger.debug(f"Sent TERMINAL-LOCATION IS with LU name: {self._lu_name}")
        await self.writer.drain()  # Ensure the data is sent immediately

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
        print(
            f"Negotiator: handle_subnegotiation called with option=0x{option:02x}, data={data.hex()}"
        )
        logger.debug(
            f"Received subnegotiation: Option=0x{option:02x}, Data={data.hex()}"
        )

        if option == TELOPT_TN3270E:
            result = self._parse_tn3270e_subnegotiation(data)
            # If the result is awaitable, await it
            if result is not None and hasattr(result, "__await__"):
                await result
        elif option == TELOPT_TERMINAL_LOCATION:
            await self._handle_terminal_location_subnegotiation(data)
        elif option == TN3270E_SYSREQ_MESSAGE_TYPE:
            await self._handle_sysreq_subnegotiation(data)
        else:
            logger.debug(
                f"Unhandled subnegotiation option: 0x{option:02x} with data: {data.hex()}"
            )

    def _parse_tn3270e_subnegotiation(self, data: bytes):
        """
        Flexible entry point for TN3270E subnegotiation parsing.

        This wrapper supports being called from synchronous test code as well as
        awaited from async code. It dispatches the real work to
        _parse_tn3270e_subnegotiation_async and, when possible, schedules it on the
        running loop (returning the scheduled Task). If no running loop exists it
        will run the coroutine to completion synchronously via asyncio.run and
        return a completed awaitable.

        For negotiation messages (DEVICE-TYPE / FUNCTIONS) we provide a fast-path
        synchronous handler so synchronous test code that calls this wrapper
        without awaiting still observes immediate state changes (negotiated flags
        and events). Additionally, if the payload is TELOPT_TN3270E followed immediately
        by a 5-byte TN3270E header, parse and dispatch that header synchronously so
        tests that supply TELOPT + header bytes observe immediate correlation.
        """
        import asyncio
        import inspect

        if len(data) < 2:
            logger.warning(f"Invalid TN3270E subnegotiation data: {data.hex()}")
            return None

        # If the data begins with TELOPT_TN3270E and the following bytes could be
        # a 5-byte TN3270E header, only parse it as a header when the first byte
        # after TELOPT looks like a TN3270E DATA-TYPE (not a negotiation message
        # type such as DEVICE-TYPE or FUNCTIONS). This avoids mis-parsing DEVICE-
        # TYPE/FUNCTIONS messages as binary headers.
        try:
            if data[0] == TELOPT_TN3270E and len(data) >= 6:
                potential_type = data[1]
                header_types = [
                    TN3270_DATA,
                    SCS_DATA,
                    RESPONSE,
                    BIND_IMAGE,
                    UNBIND,
                    NVT_DATA,
                    REQUEST,
                    SSCP_LU_DATA,
                    PRINT_EOJ,
                    SNA_RESPONSE,
                ]
                # Exclude TN3270E negotiation message types from header parsing so that
                # TELOPT-prefixed DEVICE-TYPE and FUNCTIONS messages take the fast-path
                # synchronous handling below instead of being mis-parsed as binary headers.
                if potential_type in header_types and potential_type not in (
                    TN3270E_DEVICE_TYPE,
                    TN3270E_FUNCTIONS,
                ):
                    header = TN3270EHeader.from_bytes(data[1:6])
                    if header:
                        # Call the handler. If it's been patched with a MagicMock this
                        # call will be recorded; if it's the real coroutine, schedule it.
                        logger.debug(
                            f"About to call _handle_tn3270e_response from wrapper with header from data: {data[1:6].hex() if len(data) >= 6 else data.hex()}"
                        )
                        try:
                            res = self._handle_tn3270e_response(header)

                            if inspect.isawaitable(res):
                                try:
                                    loop = asyncio.get_running_loop()
                                    loop.create_task(res)
                                except RuntimeError:
                                    asyncio.run(res)
                        except Exception:
                            # Best-effort only; don't let parsing errors break the caller.
                            pass
                        return None
        except Exception:
            # Fall through to normal handling if any of the above fails.
            pass

        # Fast-path: if payload contains explicit TN3270E negotiation message types,
        # handle them synchronously so tests that call the wrapper directly observe
        # immediate effects.
        try:
            offset = 0
            if data[0] == TELOPT_TN3270E:
                # Form: TELOPT_TN3270E, message_type, ...
                if len(data) >= 2:
                    message_type = data[1]
                    payload = data[2:]
                else:
                    message_type = None
                    payload = b""
            else:
                # Form: message_type, ...
                message_type = data[0]
                payload = data[1:]
        except Exception:
            message_type = None
            payload = data[1:] if len(data) > 1 else b""

        if message_type in (TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS):
            # Call synchronous handlers directly so state changes are immediate.
            if message_type == TN3270E_DEVICE_TYPE:
                self._handle_device_type_subnegotiation(payload)
            else:
                self._handle_functions_subnegotiation(payload)
            # Check if both events are set to complete negotiation
            if (
                self._device_type_is_event.is_set()
                and self._functions_is_event.is_set()
            ):
                self._negotiation_complete.set()
            return None

        # Otherwise, dispatch to the async parser as before.
        coro = self._parse_tn3270e_subnegotiation_async(data)
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(coro)
            logger.debug(f"Scheduled TN3270E subnegotiation parser as task: {task}")
            return task  # Task is awaitable; callers may await it or ignore it.
        except RuntimeError:
            # No running loop; run to completion synchronously so sync tests still get behavior.
            try:
                result = asyncio.run(coro)
            except Exception as e:
                logger.exception(
                    f"Error running TN3270E subnegotiation parser synchronously: {e}"
                )
                return None

            class _CompletedAwaitable:
                def __await__(self_inner):
                    async def _ret():
                        return result

                    return _ret().__await__()

            return _CompletedAwaitable()

    async def _parse_tn3270e_subnegotiation_async(self, data: bytes) -> None:
        """
        Async implementation of TN3270E subnegotiation parsing.

        This function accepts either form:
          - data starting with the TN3270E option byte (TELOPT_TN3270E) followed by
            the TN3270E message-type and subtype; or
          - data starting directly with the TN3270E message-type.

        It normalizes both forms so downstream handlers always receive "message data"
        where the first byte is the message-type and the remainder are message-specific bytes.
        """
        if not data:
            logger.warning("Empty TN3270E subnegotiation data")
            return

        # Normalize optional leading TELOPT_TN3270E (0x28)
        offset = 0
        if data[0] == TELOPT_TN3270E:
            offset = 1

        # If the input is TELOPT_TN3270E, prefer to treat it as a TN3270E message
        # (DEVICE-TYPE / FUNCTIONS) when those message types are present. Only
        # treat TELOPT + following bytes as a 5-byte TN3270E header when the first
        # byte after TELOPT looks like a true TN3270E DATA-TYPE (e.g., TN3270_DATA,
        # SCS_DATA, RESPONSE, etc.). This avoids mis-parsing DEVICE-TYPE (0x00)
        # and FUNCTIONS (0x01) messages as binary headers.
        if offset == 1:
            # If this appears to be a negotiation message, let the normal message
            # dispatching logic handle it below.
            if len(data) > offset and data[offset] in (
                TN3270E_DEVICE_TYPE,
                TN3270E_FUNCTIONS,
            ):
                # fall through to message handling
                pass
            else:
                # Only consider parsing a bare header when the following byte is a
                # recognized DATA-TYPE for TN3270E headers.
                potential_type = data[offset] if len(data) > offset else None
                header_types = [
                    TN3270_DATA,
                    SCS_DATA,
                    RESPONSE,
                    BIND_IMAGE,
                    UNBIND,
                    NVT_DATA,
                    REQUEST,
                    SSCP_LU_DATA,
                    PRINT_EOJ,
                    SNA_RESPONSE,
                ]
                # Avoid mis-parsing negotiation messages (DEVICE-TYPE / FUNCTIONS)
                # as TN3270E headers when numeric values overlap (e.g., 0x00).
                if (
                    potential_type in header_types
                    and potential_type not in (TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS)
                    and len(data) - offset >= 5
                ):
                    tn3270e_header = TN3270EHeader.from_bytes(data[offset : offset + 5])
                    if tn3270e_header:
                        logger.debug(
                            f"About to call _handle_tn3270e_response from async offset=1 with header from data: {data[offset:offset+5].hex()}"
                        )
                        await self._handle_tn3270e_response(tn3270e_header)
                        return

        # Ensure we have at least a message-type byte after normalization
        if len(data) <= offset:
            logger.warning(
                f"Invalid TN3270E subnegotiation data after normalization: {data.hex()}"
            )
            return

        message_type = data[offset]
        message_subtype = data[offset + 1] if len(data) > offset + 1 else None

        # Header parsing: when data contains a TN3270E header (DATA-TYPE ... + 5 bytes header)
        header_start = offset + 2
        if (
            message_type not in (TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS)
            and len(data) >= header_start + 5
            and message_type
            in [
                TN3270_DATA,
                SCS_DATA,
                RESPONSE,
                BIND_IMAGE,
                UNBIND,
                NVT_DATA,
                REQUEST,
                SSCP_LU_DATA,
                PRINT_EOJ,
            ]
        ):
            tn3270e_header = TN3270EHeader.from_bytes(
                data[header_start : header_start + 5]
            )
            if tn3270e_header:
                logger.debug(
                    f"About to call _handle_tn3270e_response from async header block with header from data: {data[header_start:header_start+5].hex()}"
                )
                await self._handle_tn3270e_response(tn3270e_header)
            else:
                logger.warning(
                    f"Could not parse TN3270EHeader from subnegotiation data: {data.hex()}"
                )

        # Dispatch negotiation/message handlers with message payload (strip message_type)
        message_payload = data[offset + 1 :]

        if message_type == TN3270E_DEVICE_TYPE:
            self._handle_device_type_subnegotiation(message_payload)
        elif message_type == TN3270E_FUNCTIONS:
            # FUNCTIONS handling can be synchronous for observers
            self._handle_functions_subnegotiation(message_payload)
        elif message_type == BIND_IMAGE:
            logger.debug(
                "Received BIND_IMAGE data type in TN3270E header. Data will be processed by DataStreamParser."
            )
        elif message_type == TN3270E_SYSREQ_MESSAGE_TYPE:
            await self._handle_sysreq_subnegotiation(message_payload)
        else:
            logger.debug(f"Unhandled TN3270E subnegotiation type: 0x{message_type:02x}")

        # Check if both events are set to complete negotiation
        if self._device_type_is_event.is_set() and self._functions_is_event.is_set():
            self._negotiation_complete.set()

    def _handle_device_type_subnegotiation(self, data: bytes) -> None:
        """
        Handle DEVICE-TYPE subnegotiation message.

        Args:
            data: DEVICE-TYPE subnegotiation data (message type already stripped)
        """
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
                logger.info(f"Server assigned device type: {device_type}")
                self.negotiated_device_type = device_type

                if device_type == TN3270E_IBM_DYNAMIC:
                    logger.info("IBM-DYNAMIC device type negotiated")
                    # Schedule query for device characteristics; may run async
                    try:
                        coro = self._send_query_sf(
                            self.writer, QUERY_REPLY_CHARACTERISTICS
                        )
                        self._maybe_schedule_coro(coro)
                    except Exception:
                        try:
                            # Use _maybe_schedule_coro instead of asyncio.create_task to handle both sync/async contexts
                            self._maybe_schedule_coro(
                                self._send_query_sf(
                                    self.writer, QUERY_REPLY_CHARACTERISTICS
                                )
                            )
                        except Exception:
                            logger.exception("Failed to send QUERY SF for IBM-DYNAMIC")
            self._device_type_is_event.set()
            # NOTE: According to RFC 2355, the server should initiate FUNCTIONS negotiation
            # The client should wait for the server to send FUNCTIONS SEND, not send it immediately
            logger.debug(
                "[RFC 2355] Received DEVICE-TYPE IS. Waiting for server to initiate FUNCTIONS negotiation."
            )
        elif sub_type == TN3270E_SEND:
            logger.info("Received DEVICE-TYPE SEND, sending supported device types")
            self._send_supported_device_types()
        elif sub_type == TN3270E_REQUEST:
            logger.info("Received DEVICE-TYPE REQUEST, sending supported device types")
            self._send_supported_device_types()
        else:
            logger.warning(
                f"Unhandled DEVICE-TYPE subnegotiation subtype: 0x{sub_type:02x}"
            )

    @handle_drain
    async def _send_device_type_is(self, device_type: str) -> None:
        """Send DEVICE-TYPE IS response."""
        if self.writer is None:
            raise_protocol_error("Cannot send DEVICE-TYPE IS: writer is None")
        device_type_bytes = device_type.encode("ascii") + b"\x00"
        sub_data = bytes([TN3270E_DEVICE_TYPE, TN3270E_IS]) + device_type_bytes
        send_subnegotiation(self.writer, bytes([TELOPT_TN3270E]), sub_data)
        await self.writer.drain()
        logger.info(f"Sent DEVICE-TYPE IS: {device_type}")
        self._device_type_is_event.set()

    def _handle_functions_subnegotiation(self, data: bytes) -> None:
        """
        Handle FUNCTIONS subnegotiation message.

        Args:
            data: FUNCTIONS subnegotiation data (message type already stripped)
        """
        if not data:  # Ensure data is not empty
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
                    logger.info(
                        "IBM-DYNAMIC negotiated, consider dynamic screen sizing."
                    )
            else:
                # Empty functions IS - treat as no functions supported
                logger.warning("Received empty FUNCTIONS IS; no functions supported")
                self.negotiated_functions = 0
            self._functions_is_event.set()
            # Check if both events are set to complete negotiation
            if (
                self._device_type_is_event.is_set()
                and self._functions_is_event.is_set()
            ):
                self._negotiation_complete.set()
        elif sub_type == TN3270E_SEND:
            logger.info(
                "Received FUNCTIONS SEND, responding with IS supported functions"
            )
            self._maybe_schedule_coro(self._send_functions_is())
        elif sub_type == TN3270E_REQUEST:
            logger.info(
                "Received FUNCTIONS REQUEST, responding with IS supported functions"
            )
            self._maybe_schedule_coro(self._send_functions_is())
        else:
            logger.warning(
                f"Unhandled FUNCTIONS subnegotiation subtype: 0x{sub_type:02x}"
            )

    @handle_drain
    async def _send_functions_is(self) -> None:
        """Send FUNCTIONS IS response."""
        if self.writer is None:
            raise_protocol_error("Cannot send FUNCTIONS IS: writer is None")
        functions_byte = bytes([self.supported_functions])
        sub_data = bytes([TN3270E_FUNCTIONS, TN3270E_IS]) + functions_byte
        send_subnegotiation(self.writer, bytes([TELOPT_TN3270E]), sub_data)
        await self.writer.drain()
        logger.info(f"Sent FUNCTIONS IS: 0x{self.supported_functions:02x}")
        self._functions_is_event.set()

    def _send_supported_device_types(self) -> None:
        """
        Send the list of supported device types (DEVICE-TYPE SEND).

        This method is synchronous so tests can call it directly; it uses
        send_subnegotiation() which already guards AsyncMock awaitables.
        """
        if self.writer is None:
            logger.error("Cannot send supported device types: writer is None")
            return

        # Build null-terminated list of supported device type strings
        try:
            data = b"".join(
                dt.encode("ascii") + b"\x00" for dt in self.supported_device_types
            )
        except Exception:
            # Fallback to an empty payload if encoding fails
            data = b""

        sub_data = bytes([TN3270E_DEVICE_TYPE, TN3270E_SEND]) + data
        send_subnegotiation(self.writer, bytes([TELOPT_TN3270E]), sub_data)
        # Do not await drain here; callers/tests handle awaiting drain if needed.

    @handle_drain
    async def _send_supported_functions(self) -> None:
        # Log the outgoing supported functions
        print(
            f"Negotiator: _send_supported_functions called. Supported functions: 0x{self.supported_functions:02x}"
        )
        logger.info("[DEBUG] Entering _send_supported_functions")
        """Send our supported functions to the server."""
        if self.writer is None:
            raise_protocol_error("Cannot send functions: writer is None")

        # Send FUNCTIONS SEND response with our supported functions
        function_bytes = [
            (self.supported_functions >> i) & 0xFF
            for i in range(0, 8, 8)
            if (self.supported_functions >> i) & 0xFF
        ]

        if function_bytes:
            sub_data = bytes([TN3270E_FUNCTIONS, TN3270E_SEND] + function_bytes)
            logger.info(f"[DEBUG] About to send FUNCTIONS SEND: {sub_data.hex()}")
            print(
                f"[CLIENT DEBUG] About to send FUNCTIONS SEND subnegotiation: {sub_data.hex()}"
            )
            print(f"[CLIENT DEBUG] Full SB: IAC SB TN3270E {sub_data.hex()} IAC SE")
            send_subnegotiation(self.writer, bytes([0x28]), sub_data)
            print(
                f"[CLIENT DEBUG] FUNCTIONS SEND subnegotiation sent via send_subnegotiation."
            )
            logger.debug(f"Sent supported functions: 0x{self.supported_functions:02x}")
            await self.writer.drain()
            await asyncio.sleep(0.01)  # Yield to allow server to process
            print(
                f"[CLIENT DEBUG] writer.drain() completed after sending FUNCTIONS SEND."
            )
            logger.info("[DEBUG] writer.drain() completed after sending FUNCTIONS SEND")
        else:
            print(f"[CLIENT DEBUG] No function bytes to send, skipping FUNCTIONS SEND.")
        logger.info("[DEBUG] Exiting _send_supported_functions")

    async def _send_query_sf(self, writer, query_type: int) -> None:
        """
        Sends a Query Structured Field to the host.
        """
        from .data_stream import DataStreamSender

        sender = DataStreamSender()
        query_sf = sender.build_query_sf(query_type)
        send_subnegotiation(writer, bytes([0x28]), query_sf)  # 0x28 is TN3270E option
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
            logger.info(
                f"SNA Session State changed from {self._sna_session_state.value} to {new_state.value}"
            )
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
            # Call handler method for state update
            if self.handler:
                self.handler._update_session_state_from_sna_response(sna_response)
        elif sna_response.is_negative():
            logger.warning(
                f"SNA Response: Negative acknowledgment. Sense Code: {sna_response.get_sense_code_name()}"
            )
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
                logger.error(
                    "Invalid sequence. Protocol error, re-sync might be needed."
                )
                # Log error, potentially reset sequence numbers, or terminate session
            elif sna_response.sense_code == SNA_SENSE_CODE_STATE_ERROR:
                self._set_sna_session_state(SnaSessionState.STATE_ERROR)
                logger.error("SNA State Error. Unsynchronized state, recovery needed.")
            else:
                self._set_sna_session_state(SnaSessionState.ERROR)
                logger.error(
                    f"Generic SNA Error: {sna_response.get_sense_code_name()}."
                )
            # In all negative cases, consider logging full details for diagnostics
            logger.debug(f"SNA Response details: {sna_response}")

        else:
            logger.info(
                f"SNA Response: Neither positive nor negative. Type: {sna_response.get_response_type_name()}"
            )
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

        new_size = self.screen_rows * self.screen_cols
        self.screen_buffer.buffer = bytearray(b"\x40" * new_size)
        self.screen_buffer.attributes = bytearray(new_size * 3)
        logger.info(f"Reinitialized buffer and attributes for new size: {new_size}")

        # Log query reply IDs if present
        if hasattr(bind_image, "query_reply_ids") and bind_image.query_reply_ids:
            logger.info(
                f"BIND-IMAGE specifies Query Reply IDs: {bind_image.query_reply_ids}"
            )

        logger.info(
            f"Updated screen dimensions from BIND-IMAGE: {self.screen_rows}x{self.screen_cols}"
        )

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
        if sub_type == TN3270E_IS:  # Host is telling us the LU name
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
        elif sub_type == TN3270E_REQUEST:  # Host is asking for our LU name
            logger.info("Host requested LU name. Sending configured LU name.")
            await self._send_lu_name_is()
        else:
            logger.debug(
                f"Unhandled TERMINAL-LOCATION subnegotiation subtype: 0x{sub_type:02x}"
            )

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

        logger.info(
            f"Received SYSREQ command: {sysreq_command_name} (0x{sysreq_command_code:02x})"
        )
        # Further actions based on SYSREQ command can be added here.
        # For now, just logging is sufficient as per the task.
