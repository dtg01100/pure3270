"""
Negotiator for TN3270 protocol specifics.
Handles Telnet negotiation and TN3270E subnegotiation.
"""

import asyncio
import logging
from typing import Optional, TYPE_CHECKING, List
from .data_stream import DataStreamParser
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
)
from .exceptions import NegotiationError, ProtocolError, ParseError
from ..emulation.screen_buffer import ScreenBuffer

if TYPE_CHECKING:
    from .tn3270_handler import TN3270Handler

logger = logging.getLogger(__name__)


class Negotiator:
    """
    Handles TN3270 negotiation logic.
    """

    def __init__(
        self,
        writer: Optional[asyncio.StreamWriter],
        parser: DataStreamParser,
        screen_buffer: ScreenBuffer,
        handler: Optional["TN3270Handler"] = None,
    ):
        """
        Initialize the Negotiator.

        Args:
            writer: StreamWriter for sending commands.
            parser: DataStreamParser for parsing responses.
            screen_buffer: ScreenBuffer to update during negotiation.
            handler: TN3270Handler instance for accessing reader methods.
        """
        self.writer = writer
        self.parser = parser
        self.screen_buffer = screen_buffer
        self.handler = handler
        self._ascii_mode = False
        self.negotiated_tn3270e = False
        self._lu_name: Optional[str] = None
        self.screen_rows = 24
        self.screen_cols = 80
        self.is_printer_session = False
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

    async def negotiate(self) -> None:
        """
        Perform initial Telnet negotiation.

        Sends DO TERMINAL-TYPE and waits for responses.

        Raises:
            NegotiationError: If negotiation fails.
        """
        if self.writer is None:
            raise ProtocolError("Writer is None; cannot negotiate.")
        send_iac(self.writer, b"\xff\xfd\x27")  # DO TERMINAL-TYPE
        await self.writer.drain()
        # Handle response (simplified)
        data = await self._read_iac()
        if not data:
            raise NegotiationError("No response to DO TERMINAL-TYPE")

    async def _negotiate_tn3270(self) -> None:
        """
        Negotiate TN3270E subnegotiation.

        Sends TN3270E request and handles BIND, etc.

        Raises:
            NegotiationError: On subnegotiation failure.
        """
        if self.writer is None:
            raise ProtocolError("Writer is None; cannot negotiate TN3270.")
        # Send TN3270E subnegotiation
        tn3270e_request = b"\x00\x00\x01\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        send_subnegotiation(self.writer, b"\x19", tn3270e_request)
        await self.writer.drain()
        # Parse response
        try:
            response = await self._receive_data(10.0)
            if (
                b"\x28" in response or b"\xff\xfb\x24" in response
            ):  # TN3270E positive response
                self.negotiated_tn3270e = True
                self.parser.parse(response)
                logger.info("TN3270E negotiation successful")

                # Check if this is a printer session based on LU name or BIND response
                if self.lu_name and ("LTR" in self.lu_name or "PTR" in self.lu_name):
                    self.is_printer_session = True
                    logger.info(f"Printer session detected for LU: {self.lu_name}")
            else:
                self.negotiated_tn3270e = False
                self.set_ascii_mode()
                logger.info("TN3270E negotiation failed, fallback to ASCII")
        except (ParseError, ProtocolError, asyncio.TimeoutError) as e:
            logger.warning(f"TN3270E negotiation failed with specific error: {e}")
            self.negotiated_tn3270e = False
            self.set_ascii_mode()
        except Exception as e:
            logger.error(f"Unexpected error during TN3270E negotiation: {e}")
            self.negotiated_tn3270e = False
            self.set_ascii_mode()

    def set_ascii_mode(self) -> None:
        """
        Set to ASCII mode fallback.

        Disables EBCDIC processing.
        """
        self._ascii_mode = True

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

    def _parse_tn3270e_subnegotiation(self, data: bytes) -> None:
        """
        Parse TN3270E subnegotiation message.

        Args:
            data: TN3270E subnegotiation data (without IAC SB and IAC SE)
        """
        if len(data) < 3:
            logger.warning(f"Invalid TN3270E subnegotiation data: {data.hex()}")
            return

        # Parse subnegotiation header
        # data[0] = TN3270E option (should be 0x28)
        # data[1] = message type
        # data[2] = message sub-type

        if data[0] != 0x28:  # TN3270E option
            logger.warning(f"Invalid TN3270E option in subnegotiation: 0x{data[0]:02x}")
            return

        message_type = data[1] if len(data) > 1 else None
        message_subtype = data[2] if len(data) > 2 else None

        if message_type == TN3270E_DEVICE_TYPE:
            self._handle_device_type_subnegotiation(data[1:])
        elif message_type == TN3270E_FUNCTIONS:
            self._handle_functions_subnegotiation(data[1:])
        else:
            logger.debug(f"Unhandled TN3270E subnegotiation type: 0x{message_type:02x}")

    def _handle_device_type_subnegotiation(self, data: bytes) -> None:
        """
        Handle DEVICE-TYPE subnegotiation message.

        Args:
            data: DEVICE-TYPE subnegotiation data (message type already stripped)
        """
        if len(data) < 2:
            logger.warning("Invalid DEVICE-TYPE subnegotiation data")
            return

        sub_type = data[0]

        if sub_type == TN3270E_IS:
            # DEVICE-TYPE IS - server is telling us what device type to use
            if len(data) > 1:
                # Extract device type string (null-terminated or until end)
                device_type_bytes = data[1:]
                # Find null terminator if present
                null_pos = device_type_bytes.find(0x00)
                if null_pos != -1:
                    device_type_bytes = device_type_bytes[:null_pos]

                device_type = device_type_bytes.decode("ascii", errors="ignore").strip()
                logger.info(f"Server requested device type: {device_type}")

                # Handle IBM-DYNAMIC specially
                if device_type == TN3270E_IBM_DYNAMIC:
                    logger.info("IBM-DYNAMIC device type negotiated")
                    self.negotiated_device_type = TN3270E_IBM_DYNAMIC
                    # For IBM-DYNAMIC, we may need to negotiate screen size dynamically
                else:
                    self.negotiated_device_type = device_type

        elif sub_type == TN3270E_REQUEST:
            # DEVICE-TYPE REQUEST - server is asking what device types we support
            logger.info("Server requested supported device types")
            self._send_supported_device_types()
        else:
            logger.warning(
                f"Unhandled DEVICE-TYPE subnegotiation subtype: 0x{sub_type:02x}"
            )

    def _handle_functions_subnegotiation(self, data: bytes) -> None:
        """
        Handle FUNCTIONS subnegotiation message.

        Args:
            data: FUNCTIONS subnegotiation data (message type already stripped)
        """
        if len(data) < 2:
            logger.warning("Invalid FUNCTIONS subnegotiation data")
            return

        sub_type = data[0]

        if sub_type == TN3270E_IS:
            # FUNCTIONS IS - server is telling us what functions are enabled
            if len(data) > 1:
                # Parse function bits
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

        elif sub_type == TN3270E_REQUEST:
            # FUNCTIONS REQUEST - server is asking what functions we support
            logger.info("Server requested supported functions")
            self._send_supported_functions()
        else:
            logger.warning(
                f"Unhandled FUNCTIONS subnegotiation subtype: 0x{sub_type:02x}"
            )

    def _send_supported_device_types(self) -> None:
        """Send our supported device types to the server."""
        if self.writer is None:
            logger.error("Cannot send device types: writer is None")
            return

        # Send DEVICE-TYPE SEND response with our supported types
        # For simplicity, we'll just send our first supported type
        if self.supported_device_types:
            device_type = self.supported_device_types[0].encode("ascii") + b"\x00"
            sub_data = bytes([TN3270E_DEVICE_TYPE, TN3270E_SEND]) + device_type
            send_subnegotiation(self.writer, bytes([0x28]), sub_data)
            logger.debug(
                f"Sent supported device type: {self.supported_device_types[0]}"
            )

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
