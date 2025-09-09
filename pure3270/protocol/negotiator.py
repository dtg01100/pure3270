"""
Negotiator for TN3270 protocol specifics.
Handles Telnet negotiation and TN3270E subnegotiation.
"""

import asyncio
import logging
from typing import Optional, TYPE_CHECKING
from .data_stream import DataStreamParser
from .utils import send_iac, send_subnegotiation
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