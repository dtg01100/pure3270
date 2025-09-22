"""
Negotiator for TN3270 protocol specifics.
Handles Telnet negotiation and TN3270E subnegotiation.
"""

import asyncio
import inspect
import logging
import sys
from enum import Enum  # Import Enum for state management
from typing import TYPE_CHECKING, Any, Awaitable, Dict, List, Optional

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
from .tn3270e_header import TN3270EHeader
from .trace_recorder import TraceRecorder  # Optional diagnostic recorder
from .utils import SNA_RESPONSE  # Import SNA_RESPONSE
from .utils import TELOPT_BIND_UNIT  # TELOPT 48
from .utils import (
    BIND_IMAGE,
    DO,
    DONT,
    NVT_DATA,
    PRINT_EOJ,
    QUERY_REPLY_CHARACTERISTICS,
    REQUEST,
    RESPONSE,
    SCS_DATA,
    SSCP_LU_DATA,
    TELOPT_BINARY,
    TELOPT_EOR,
)
from .utils import (
    TELOPT_OLD_ENVIRON as TELOPT_TERMINAL_LOCATION,  # Alias for RFC 1646 (TELOPT 36)
)
from .utils import (
    TELOPT_TN3270E,
    TELOPT_TTYPE,
    TN3270_DATA,
    TN3270E_BIND_IMAGE,
    TN3270E_DATA_STREAM_CTL,
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IBM_DYNAMIC,
    TN3270E_IS,
    TN3270E_REQUEST,
    TN3270E_RESPONSES,
    TN3270E_RSF_ALWAYS_RESPONSE,
    TN3270E_RSF_ERROR_RESPONSE,
    TN3270E_RSF_NEGATIVE_RESPONSE,
    TN3270E_RSF_NO_RESPONSE,
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
    UNBIND,
    WILL,
    WONT,
    send_iac,
    send_subnegotiation,
)

if TYPE_CHECKING:
    from .tn3270_handler import TN3270Handler

logger = logging.getLogger(__name__)


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
        recorder: Optional[TraceRecorder] = None,
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
        self.negotiated_response_mode: int = 0
        self._next_seq_number: int = 0  # For outgoing SEQ-NUMBER
        self._pending_requests: Dict[int, Any] = (
            {}
        )  # To store pending requests for response correlation
        self._device_type_is_event: Optional[asyncio.Event] = None
        self._functions_is_event: Optional[asyncio.Event] = None
        self._negotiation_complete: Optional[asyncio.Event] = (
            None  # Event for full negotiation completion
        )
        self._query_sf_response_event = (
            asyncio.Event()
        )  # New event for Query SF response
        self._printer_status_event = (
            asyncio.Event()
        )  # New event for printer status updates
        # Internal flag to signal forced failure (e.g., server refusal when fallback disabled)
        self._forced_failure: bool = False
        # Track server TN3270E support
        self._server_supports_tn3270e: bool = False
        # Buffer to accumulate negotiation bytes when inference is needed (e.g., tests)
        self._negotiation_trace = None  # type: Optional[bytes]
        # Optional trace recorder for diagnostics / tests
        self.recorder = recorder  # type: Optional[TraceRecorder]

    def _get_or_create_device_type_event(self) -> asyncio.Event:
        if self._device_type_is_event is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            if sys.version_info < (3, 10):
                self._device_type_is_event = asyncio.Event(loop=loop)
            else:
                self._device_type_is_event = asyncio.Event()
        return self._device_type_is_event

    def _get_or_create_functions_event(self) -> asyncio.Event:
        if self._functions_is_event is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            if sys.version_info < (3, 10):
                self._functions_is_event = asyncio.Event(loop=loop)
            else:
                self._functions_is_event = asyncio.Event()
        return self._functions_is_event

    def _get_or_create_negotiation_complete(self) -> asyncio.Event:
        if self._negotiation_complete is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            if sys.version_info < (3, 10):
                self._negotiation_complete = asyncio.Event(loop=loop)
            else:
                self._negotiation_complete = asyncio.Event()
        return self._negotiation_complete

    # ------------------------------------------------------------------
    # Recorder helpers
    # ------------------------------------------------------------------
    def _record_telnet(self, direction: str, command: int, option: int) -> None:
        if not self.recorder:
            return
        try:
            name_map = {DO: "DO", DONT: "DONT", WILL: "WILL", WONT: "WONT"}
            self.recorder.telnet(
                direction, name_map.get(command, f"0x{command:02x}"), option
            )
        except Exception:
            pass

    def _record_decision(
        self, requested: str, chosen: str, fallback_used: bool
    ) -> None:
        if self.recorder:
            try:
                self.recorder.decision(requested, chosen, fallback_used)
            except Exception:
                pass

    def _record_error(self, message: str) -> None:
        if self.recorder:
            try:
                self.recorder.error(message)
            except Exception:
                pass

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

    def _maybe_schedule_coro(self, coro: Awaitable[object]) -> None:
        """
        Schedule a coroutine to run in the running event loop if one exists.

        This allows methods to remain synchronous while still invoking
        async helpers without requiring the caller to await them.
        """
        try:
            loop = asyncio.get_running_loop()
            # Cast to Coroutine for create_task
            loop.create_task(coro)  # type: ignore[arg-type]
        except RuntimeError:
            # No running event loop; run synchronously for tests
            asyncio.run(coro)  # type: ignore[arg-type]

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

    async def _handle_tn3270e_response(
        self, header: TN3270EHeader, data: bytes = b""
    ) -> None:
        """
        Handles an incoming TN3270E header, correlating it with pending requests.

        Args:
            header: The received TN3270EHeader object.
            data: Optional data following the header for negative responses.
        """
        logger.debug(
            f"Entered _handle_tn3270e_response with header: data_type=0x{header.data_type:02x}, seq_number={header.seq_number}, request_flag=0x{header.request_flag:02x}, response_flag=0x{header.response_flag:02x}, data_len={len(data)}"
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
                    retry_count = request_info.get("retry_count", 0)
                    if retry_count < 3:
                        request_info["retry_count"] = retry_count + 1
                        self._pending_requests[seq_number] = request_info
                        await asyncio.sleep(0.5 * (2**retry_count))
                        await self._resend_request(request_type, seq_number)
                        return
                    else:
                        header.handle_negative_response(data)
                        logger.error("Max retries exceeded for DEVICE-TYPE SEND")
                elif header.is_error_response():
                    logger.error("Received error response for DEVICE-TYPE SEND.")
                self._get_or_create_device_type_event().set()
            elif request_type == "FUNCTIONS SEND":
                if header.is_positive_response():
                    logger.debug("Received positive response for FUNCTIONS SEND.")
                elif header.is_negative_response():
                    retry_count = request_info.get("retry_count", 0)
                    if retry_count < 3:
                        request_info["retry_count"] = retry_count + 1
                        self._pending_requests[seq_number] = request_info
                        await asyncio.sleep(0.5 * (2**retry_count))
                        await self._resend_request(request_type, seq_number)
                        return
                    else:
                        header.handle_negative_response(data)
                        logger.error("Max retries exceeded for FUNCTIONS SEND")
                elif header.is_error_response():
                    logger.error("Received error response for FUNCTIONS SEND.")
                self._get_or_create_functions_event().set()
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
            self._record_telnet("out", WILL, TELOPT_TTYPE)
            logger.debug("[NEGOTIATION] Sent IAC WILL TERMINAL-TYPE (fb 18)")
            send_iac(self.writer, b"\xfd\x18")  # DO TERMINAL-TYPE
            self._record_telnet("out", DO, TELOPT_TTYPE)
            logger.debug("[NEGOTIATION] Sent IAC DO TERMINAL-TYPE (fd 18)")
            # Per RFC 1091, after TTYPE negotiation, wait for the server to initiate BINARY/EOR/TN3270E negotiation.
            await self.writer.drain()
            logger.info(
                "[NEGOTIATION] Initial TTYPE negotiation commands sent. Awaiting server response..."
            )
        # The response for further negotiation is handled by handle_iac_command

    async def _negotiate_tn3270(self, timeout: Optional[float] = None) -> None:
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
            self._record_decision("ascii", "ascii", False)
            for ev in (
                self._get_or_create_device_type_event(),
                self._get_or_create_functions_event(),
                self._get_or_create_negotiation_complete(),
            ):
                ev.set()
            return
        if self.force_mode == "tn3270":
            logger.info(
                "[NEGOTIATION] force_mode=tn3270 specified; skipping TN3270E negotiation (basic TN3270 only)."
            )
            self.negotiated_tn3270e = False
            self._record_decision("tn3270", "tn3270", False)
            # Events set so upstream waits proceed
            for ev in (
                self._get_or_create_device_type_event(),
                self._get_or_create_functions_event(),
                self._get_or_create_negotiation_complete(),
            ):
                ev.set()
            return
        if self.force_mode == "tn3270e":
            logger.info(
                "[NEGOTIATION] force_mode=tn3270e specified; skipping TN3270E negotiation (TN3270E enabled)."
            )
            self.negotiated_tn3270e = True
            self._record_decision("tn3270e", "tn3270e", True)
            # Events set so upstream waits proceed
            for ev in (
                self._get_or_create_device_type_event(),
                self._get_or_create_functions_event(),
                self._get_or_create_negotiation_complete(),
            ):
                ev.set()
            return

        if self.writer is None:
            raise ProtocolError("Writer is None; cannot negotiate TN3270.")

        # Clear events before starting negotiation
        self._get_or_create_device_type_event().clear()
        self._get_or_create_functions_event().clear()
        self._get_or_create_negotiation_complete().clear()

        logger.info(
            "[NEGOTIATION] Starting TN3270E negotiation: waiting for server DEVICE-TYPE SEND."
        )

        try:
            async with safe_socket_operation():
                # Calculate per-step timeouts based on overall timeout
                if timeout is None:
                    timeout = 30.0  # Default timeout
                step_timeout = min(
                    timeout / 3, 10.0
                )  # Divide timeout into 3 steps, max 10s per step

                # Validate negotiation state before starting
                if not self._server_supports_tn3270e and self.force_mode != "tn3270e":
                    logger.warning(
                        "[NEGOTIATION] Server doesn't support TN3270E, but proceeding with negotiation"
                    )

                # Wait for each event with calculated per-step timeout
                logger.debug(
                    f"[NEGOTIATION] Waiting for DEVICE-TYPE with per-event timeout {step_timeout}s..."
                )
                await asyncio.wait_for(
                    self._get_or_create_device_type_event().wait(), timeout=step_timeout
                )
                logger.debug(
                    f"[NEGOTIATION] Waiting for FUNCTIONS with per-event timeout {step_timeout}s..."
                )
                await asyncio.wait_for(
                    self._get_or_create_functions_event().wait(), timeout=step_timeout
                )
                # Overall wait for completion with remaining timeout
                remaining_timeout = timeout - (2 * step_timeout)
                if remaining_timeout <= 0:
                    remaining_timeout = step_timeout
                logger.debug(
                    f"[NEGOTIATION] Waiting for full TN3270E negotiation with timeout {remaining_timeout}s..."
                )
                await asyncio.wait_for(
                    self._get_or_create_negotiation_complete().wait(),
                    timeout=remaining_timeout,
                )
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
                        await self._handle_sna_response(sna_response)
                    logger.debug(
                        "[NEGOTIATION] SNA response for printer BIND handled (stub)"
                    )

                # If ASCII mode was set (e.g., due to a WONT), do not mark TN3270E as negotiated.
                if getattr(self, "_ascii_mode", False):
                    logger.info(
                        "[NEGOTIATION] ASCII mode active; skipping TN3270E negotiated flag."
                    )
                    self.negotiated_tn3270e = False
                    self._record_decision(self.force_mode or "auto", "ascii", True)
                else:
                    self.negotiated_tn3270e = True
                    logger.info("[NEGOTIATION] TN3270E negotiation successful.")
                    self._record_decision(self.force_mode or "auto", "tn3270e", False)

                # Ensure events are created and set for completion
                self._get_or_create_negotiation_complete().set()

        except asyncio.TimeoutError:
            if self.force_mode == "tn3270e" and not self.allow_fallback:
                logger.error(
                    "[NEGOTIATION] TN3270E negotiation timed out and fallback disabled (force_mode=tn3270e); raising error."
                )
                self._record_error("timeout forcing tn3270e without fallback")
                # Ensure events are set so any awaiters unblock
                for ev in (
                    self._get_or_create_device_type_event(),
                    self._get_or_create_functions_event(),
                    self._get_or_create_negotiation_complete(),
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
                self._record_decision(self.force_mode or "auto", "ascii", True)
            self.negotiated_tn3270e = False
            for ev in (
                self._get_or_create_device_type_event(),
                self._get_or_create_functions_event(),
                self._get_or_create_negotiation_complete(),
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
                self._record_error(f"refused tn3270e without fallback: {e}")
                for ev in (
                    self._get_or_create_device_type_event(),
                    self._get_or_create_functions_event(),
                    self._get_or_create_negotiation_complete(),
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
                self._record_decision(self.force_mode or "auto", "ascii", True)
            self.negotiated_tn3270e = False
            for ev in (
                self._get_or_create_device_type_event(),
                self._get_or_create_functions_event(),
                self._get_or_create_negotiation_complete(),
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
            result = await self.handler._read_iac()  # type: ignore[attr-defined]
            return bytes(result)
        raise NotImplementedError("Handler required for reading IAC")

    async def handle_iac_command(self, command: int, option: int) -> None:
        """
        Handle Telnet IAC (Interpret As Command) commands.

        Args:
            command: The IAC command (DO, DONT, WILL, WONT).
            option: The Telnet option number.
        """
        from .utils import DO, DONT, WILL, WONT

        command_name = {DO: "DO", DONT: "DONT", WILL: "WILL", WONT: "WONT"}.get(
            command, f"0x{command:02x}"
        )
        option_name = self._get_option_name(option)

        logger.info(
            f"[TELNET] Handling IAC {command_name} {option_name} (0x{option:02x})"
        )

        if command == WILL:
            await self._handle_will(option)
        elif command == WONT:
            await self._handle_wont(option)
        elif command == DO:
            await self._handle_do(option)
        elif command == DONT:
            await self._handle_dont(option)
        else:
            logger.warning(f"[TELNET] Unknown IAC command 0x{command:02x}")

        # Record the telnet command for tracing
        self._record_telnet("in", command, option)

    def _get_option_name(self, option: int) -> str:
        """Get the human-readable name for a Telnet option."""
        from .utils import (
            TELOPT_BINARY,
            TELOPT_EOR,
            TELOPT_TTYPE,
            TELOPT_TN3270E,
            TELOPT_OLD_ENVIRON,
            TELOPT_SGA,
            TELOPT_ECHO,
        )

        option_names = {
            TELOPT_BINARY: "BINARY",
            TELOPT_EOR: "EOR",
            TELOPT_SGA: "SGA",
            TELOPT_ECHO: "ECHO",
            TELOPT_TTYPE: "TTYPE",
            TELOPT_TN3270E: "TN3270E",
            TELOPT_OLD_ENVIRON: "OLD-ENVIRON",
        }
        return option_names.get(option, f"0x{option:02x}")

    async def _handle_will(self, option: int) -> None:
        """Handle WILL command (server wants to enable option)."""
        from .utils import TELOPT_BINARY, TELOPT_EOR, TELOPT_TN3270E, DO, DONT

        if option == TELOPT_BINARY:
            logger.info("[TELNET] Server WILL BINARY - accepting")
            if self.writer:
                send_iac(self.writer, bytes([DO, TELOPT_BINARY]))
        elif option == TELOPT_EOR:
            logger.info("[TELNET] Server WILL EOR - accepting")
            if self.writer:
                send_iac(self.writer, bytes([DO, TELOPT_EOR]))
        elif option == TELOPT_TN3270E:
            logger.info("[TELNET] Server WILL TN3270E - accepting")
            if self.writer:
                send_iac(self.writer, bytes([DO, TELOPT_TN3270E]))
            # Mark that TN3270E is supported by server
            self._server_supports_tn3270e = True
        else:
            logger.info(
                f"[TELNET] Server WILL unknown option 0x{option:02x} - rejecting"
            )
            if self.writer:
                send_iac(self.writer, bytes([DONT, option]))

    async def _handle_wont(self, option: int) -> None:
        """Handle WONT command (server refuses option)."""
        from .utils import TELOPT_TN3270E

        logger.info(f"[TELNET] Server WONT 0x{option:02x}")

        if option == TELOPT_TN3270E:
            logger.warning(
                "[TELNET] Server refuses TN3270E - will fall back to TN3270 or ASCII"
            )
            self._server_supports_tn3270e = False
            # This might trigger fallback logic in negotiation

    async def _handle_do(self, option: int) -> None:
        """Handle DO command (server wants us to enable option)."""
        from .utils import TELOPT_BINARY, TELOPT_EOR, TELOPT_TTYPE, WILL, WONT

        if option == TELOPT_BINARY:
            logger.info("[TELNET] Server DO BINARY - accepting")
            if self.writer:
                send_iac(self.writer, bytes([WILL, TELOPT_BINARY]))
        elif option == TELOPT_EOR:
            logger.info("[TELNET] Server DO EOR - accepting")
            if self.writer:
                send_iac(self.writer, bytes([WILL, TELOPT_EOR]))
        elif option == TELOPT_TTYPE:
            logger.info("[TELNET] Server DO TTYPE - accepting")
            if self.writer:
                send_iac(self.writer, bytes([WILL, TELOPT_TTYPE]))
        else:
            logger.info(f"[TELNET] Server DO unknown option 0x{option:02x} - rejecting")
            if self.writer:
                send_iac(self.writer, bytes([WONT, option]))

    async def _handle_dont(self, option: int) -> None:
        """Handle DONT command (server wants us to disable option)."""
        logger.info(f"[TELNET] Server DONT 0x{option:02x}")
        # We generally accept DONT commands as they don't affect our operation

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
        if self.recorder:
            try:
                self.recorder.subneg(TELOPT_TERMINAL_LOCATION, sub_data)
            except Exception:
                pass
        logger.debug(f"Sent TERMINAL-LOCATION IS with LU name: {self._lu_name}")
        if self.writer is not None:
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

    async def handle_subnegotiation(self, option: int, sub_payload: bytes) -> None:
        """
        Handle Telnet subnegotiation for non-TN3270E options.

        Args:
            option: The Telnet option number.
            sub_payload: The subnegotiation payload.
        """
        logger.info(
            f"[TELNET] Handling subnegotiation for option 0x{option:02x}: {sub_payload.hex()}"
        )

        if option == TELOPT_TTYPE:
            # Terminal type subnegotiation
            await self._handle_terminal_type_subnegotiation(sub_payload)
        elif option == TELOPT_TN3270E:
            # This should have been handled by the specialized method, but handle it here as fallback
            await self._parse_tn3270e_subnegotiation(bytes([option]) + sub_payload)
        else:
            logger.warning(f"[TELNET] Unhandled subnegotiation option 0x{option:02x}")

    async def _parse_tn3270e_subnegotiation(self, data: bytes) -> None:
        """
        Parse TN3270E subnegotiation data.

        Args:
            data: The complete subnegotiation data (option + payload).
        """
        if len(data) < 2:
            logger.warning("[TN3270E] Subnegotiation data too short")
            return

        option = data[0]
        payload = data[1:]

        if option != TELOPT_TN3270E:
            logger.warning(f"[TN3270E] Expected TN3270E option, got 0x{option:02x}")
            return

        logger.info(f"[TN3270E] Parsing subnegotiation payload: {payload.hex()}")

        # Parse TN3270E subnegotiation commands
        i = 0
        while i < len(payload):
            if payload[i] == TN3270E_SEND:
                i += 1
                if i < len(payload):
                    send_type = payload[i]
                    logger.info(
                        f"[TN3270E] Received SEND command for type 0x{send_type:02x}"
                    )
                    await self._handle_tn3270e_send(send_type)
                else:
                    logger.warning("[TN3270E] Incomplete SEND command")
            elif payload[i] == TN3270E_IS:
                i += 1
                # Parse the response data
                response_data = payload[i:]
                logger.info(f"[TN3270E] Received IS response: {response_data.hex()}")
                await self._handle_tn3270e_is(response_data)
                break  # IS command consumes the rest of the payload
            else:
                logger.warning(
                    f"[TN3270E] Unknown subnegotiation command 0x{payload[i]:02x}"
                )
                break
            i += 1

    async def _handle_tn3270e_send(self, send_type: int) -> None:
        """
        Handle TN3270E SEND commands.

        Args:
            send_type: The type of data being requested.
        """
        if send_type == TN3270E_DEVICE_TYPE:
            logger.info("[TN3270E] Sending supported device types")
            await self._send_supported_device_types()
        elif send_type == TN3270E_FUNCTIONS:
            logger.info("[TN3270E] Sending supported functions")
            await self._send_functions_is()
        else:
            logger.warning(f"[TN3270E] Unknown SEND type 0x{send_type:02x}")

    async def _handle_tn3270e_is(self, response_data: bytes) -> None:
        """
        Handle TN3270E IS responses.

        Args:
            response_data: The response data.
        """
        logger.info(f"[TN3270E] Processing IS response: {response_data.hex()}")

        # Parse structured fields in the response
        pos = 0
        while pos < len(response_data):
            if response_data[pos] == 0x0F:  # SFH - Structured Field Header
                if pos + 2 < len(response_data):
                    sf_id = response_data[pos + 1]
                    length = response_data[pos + 2]
                    if pos + 3 + length <= len(response_data):
                        sf_data = response_data[pos + 3 : pos + 3 + length]
                        await self._handle_structured_field(sf_id, sf_data)
                        pos += 3 + length
                    else:
                        logger.warning("[TN3270E] Incomplete structured field")
                        break
                else:
                    logger.warning("[TN3270E] Incomplete structured field header")
                    break
            else:
                logger.warning(
                    f"[TN3270E] Expected structured field, got 0x{response_data[pos]:02x}"
                )
                break

    async def _handle_structured_field(self, sf_id: int, sf_data: bytes) -> None:
        """
        Handle a TN3270E structured field.

        Args:
            sf_id: Structured field ID.
            sf_data: Structured field data.
        """
        logger.debug(
            f"[TN3270E] Handling structured field 0x{sf_id:02x}: {sf_data.hex()}"
        )

        if sf_id == 0x81:  # CHARACTERISTICS
            # Update device type based on characteristics
            if len(sf_data) >= 5:
                model = sf_data[1]
                lu_type = sf_data[2]
                self.negotiated_device_type = f"IBM-327{lu_type // 16}-{model}"
                logger.info(
                    f"[TN3270E] Updated device type from characteristics: {self.negotiated_device_type}"
                )
        elif sf_id == 0x82:  # AID
            logger.debug("[TN3270E] Received AID structured field")
        elif sf_id == 0x03:  # USABLE AREA
            if len(sf_data) >= 2:
                rows = sf_data[0]
                cols = sf_data[1]
                logger.info(f"[TN3270E] Usable area: {rows}x{cols}")
        else:
            logger.debug(f"[TN3270E] Unhandled structured field 0x{sf_id:02x}")

    async def _handle_terminal_type_subnegotiation(self, payload: bytes) -> None:
        """
        Handle terminal type subnegotiation.

        Args:
            payload: The subnegotiation payload.
        """
        logger.info(f"[TTYPE] Handling terminal type subnegotiation: {payload.hex()}")

        if len(payload) >= 2:
            command = payload[0]
            if command == TN3270E_IS:
                # Server is sending terminal type
                term_type = payload[1:].decode("ascii", errors="ignore").rstrip("\x00")
                logger.info(f"[TTYPE] Server terminal type: {term_type}")
            elif command == TN3270E_SEND:
                # Server requests our terminal type
                logger.info(
                    "[TTYPE] Server requested terminal type, sending IBM-3278-2"
                )
                if self.writer:
                    from .utils import send_subnegotiation

                    response = b"\x00IBM-3278-2\x00"
                    send_subnegotiation(
                        self.writer,
                        bytes([TELOPT_TTYPE]),
                        bytes([TN3270E_IS]) + response,
                    )
                    await self.writer.drain()
        else:
            logger.warning("[TTYPE] Terminal type subnegotiation payload too short")

    def _validate_negotiation_state(self) -> bool:
        """
        Validate the current negotiation state for consistency.

        Returns:
            True if state is valid, False otherwise.
        """
        # Check that negotiated values are consistent
        if self.negotiated_tn3270e:
            if not self.negotiated_device_type:
                logger.warning(
                    "[NEGOTIATION] TN3270E negotiated but no device type set"
                )
                return False
            if self.negotiated_functions == 0:
                logger.warning(
                    "[NEGOTIATION] TN3270E negotiated but no functions negotiated"
                )
                return False

        # Check that ASCII mode is not set when TN3270E is negotiated
        if self.negotiated_tn3270e and getattr(self, "_ascii_mode", False):
            logger.error(
                "[NEGOTIATION] Invalid state: TN3270E negotiated but ASCII mode is active"
            )
            return False

        # Check that supported device types list is not empty
        if not self.supported_device_types:
            logger.warning("[NEGOTIATION] No supported device types configured")
            return False

        return True

    def _reset_negotiation_state(self) -> None:
        """
        Reset negotiation state to initial values.
        Used for error recovery or re-negotiation.
        """
        logger.debug("[NEGOTIATION] Resetting negotiation state")
        self.negotiated_tn3270e = False
        self._lu_name = None
        self.negotiated_device_type = None
        self.negotiated_functions = 0
        self.negotiated_response_mode = 0
        self._ascii_mode = False
        self._server_supports_tn3270e = False
        self._forced_failure = False

        # Clear events
        for event in [
            self._device_type_is_event,
            self._functions_is_event,
            self._negotiation_complete,
        ]:
            if event:
                event.clear()

        # Reset SNA session state
        self._sna_session_state = SnaSessionState.NORMAL

    @property
    def current_sna_session_state(self) -> SnaSessionState:
        """Get the current SNA session state."""
        return self._sna_session_state

    async def _handle_sna_response(self, sna_response: SnaResponse) -> None:
        """
        Handle SNA response from the mainframe.

        Args:
            sna_response: The SNA response to handle.
        """
        logger.debug(f"[SNA] Handling SNA response: {sna_response}")

        # Handle different SNA response types
        if sna_response.sense_code == SNA_SENSE_CODE_SUCCESS:
            logger.debug("[SNA] SNA response indicates success")
            # Reset session state on success
            self._sna_session_state = SnaSessionState.NORMAL
        elif sna_response.sense_code == SNA_SENSE_CODE_LU_BUSY:
            logger.warning("[SNA] LU busy, will retry after delay")
            self._sna_session_state = SnaSessionState.ERROR
            # Wait and retry BIND if active
            await asyncio.sleep(1)
            if hasattr(self, "is_bind_image_active") and self.is_bind_image_active:
                await self._resend_request("BIND-IMAGE", self._next_seq_number)
        else:
            logger.error(
                f"[SNA] SNA error response: sense_code={sna_response.sense_code}"
            )
            self._sna_session_state = SnaSessionState.ERROR
            # Could raise an exception or handle recovery here

    async def _resend_request(self, request_type: str, seq_number: int) -> None:
        """
        Resend a failed TN3270E request.

        Args:
            request_type: Type of request to resend.
            seq_number: Sequence number for the request.
        """
        logger.info(f"[TN3270E] Resending {request_type} request (seq={seq_number})")

        if request_type == "DEVICE-TYPE SEND":
            await self._send_supported_device_types()
        elif request_type == "FUNCTIONS SEND":
            await self._send_functions_is()
        elif request_type == "BIND-IMAGE":
            # Resend BIND-IMAGE request
            if hasattr(self, "is_bind_image_active") and self.is_bind_image_active:
                logger.info("[TN3270E] Resending BIND-IMAGE request")
                # Implementation would depend on how BIND-IMAGE is sent
        else:
            logger.warning(f"[TN3270E] Unknown request type for resend: {request_type}")

    async def _send_supported_device_types(self) -> None:
        """Send supported device types to the server."""
        logger.debug("[TN3270E] Sending supported device types")

        if not self.supported_device_types:
            logger.warning("[TN3270E] No supported device types configured")
            return

        # Send DEVICE-TYPE IS with first supported device type
        device_type = self.supported_device_types[0]
        logger.info(f"[TN3270E] Sending device type: {device_type}")

        if self.writer:
            from .utils import send_subnegotiation

            # Format: IS <device_type> CONNECT <lu_name>
            payload = bytes([TN3270E_IS]) + device_type.encode("ascii") + b" CONNECT"
            if self._lu_name:
                payload += b" " + self._lu_name.encode("ascii")
            payload += b"\x00"  # Null terminator

            send_subnegotiation(self.writer, bytes([TN3270E_DEVICE_TYPE]), payload)
            await self.writer.drain()

    async def _send_functions_is(self) -> None:
        """Send FUNCTIONS IS response to the server."""
        logger.debug("[TN3270E] Sending FUNCTIONS IS")

        # Send FUNCTIONS IS with negotiated functions
        functions = self.negotiated_functions
        logger.info(f"[TN3270E] Sending functions: 0x{functions:04x}")

        if self.writer:
            from .utils import send_subnegotiation

            payload = bytes([TN3270E_IS, (functions >> 8) & 0xFF, functions & 0xFF])
            send_subnegotiation(self.writer, bytes([TN3270E_FUNCTIONS]), payload)
            await self.writer.drain()

    def handle_bind_image(self, bind_image: BindImage) -> None:
        """
        Handle BIND-IMAGE structured field.

        Args:
            bind_image: The BIND-IMAGE to handle.
        """
        logger.info(f"[TN3270E] Handling BIND-IMAGE: {bind_image}")

        # Update session state based on BIND-IMAGE
        # Note: BindImage doesn't have bind_type attribute, check the actual structure
        # For now, assume it's a BIND if we receive it
        logger.info("[TN3270E] BIND-IMAGE received - session bound")
        self.is_bind_image_active = True
