"""TN3270 protocol handler using telnetlib3 for networking."""

import logging
from typing import Optional, BinaryIO
import telnetlib3
from telnetlib3 import TelnetTerminalClient


logger = logging.getLogger(__name__)


class ProtocolError(Exception):
    """Base exception for protocol errors."""
    pass


class NegotiationError(ProtocolError):
    """Error during TN3270 negotiation."""
    pass


class TN3270Handler:
    """Handles TN3270/TN3270E protocol using telnetlib3."""

    def __init__(self, host: str, port: int = 23, ssl_context: Optional[BinaryIO] = None):
        """
        Initialize the TN3270Handler.

        :param host: Hostname or IP address.
        :param port: Port number (default 23 for telnet, 992 for secure).
        :param ssl_context: SSL context for secure connections (from SSLWrapper).
        """
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.telnet: Optional[TelnetTerminalClient] = None
        self.negotiated_tn3270e = False

    async def connect(self):
        """
        Establish connection and negotiate TN3270/TN3270E.

        :raises NegotiationError: If negotiation fails.
        """
        try:
            # Create telnet connection
            if self.ssl_context:
                # For SSL, telnetlib3 supports secure connections
                self.telnet = await telnetlib3.open_connection(
                    self.host, self.port, ssl=self.ssl_context
                )
            else:
                self.telnet = await telnetlib3.open_connection(self.host, self.port)

            logger.info(f"Connected to {self.host}:{self.port}")

            # Negotiate TN3270
            await self._negotiate_tn3270()

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}")

    async def _negotiate_tn3270(self):
        """Perform TN3270 negotiation."""
        # Send DO TN3270
        await self.telnet.request_negotiate(telnetlib3.TN3270)
        response = await self.telnet.read_until(b"\xff", timeout=5)

        if b"\xff\xfb\x27" in response:  # WILL TN3270
            logger.debug("TN3270 negotiated")
            # Further negotiate TN3270E if possible
            await self.telnet.request_negotiate(telnetlib3.TN3270E)
            eor_response = await self.telnet.read_until(b"\xff", timeout=5)
            if b"\xff\xfb\x24" in eor_response:  # WILL TN3270E
                self.negotiated_tn3270e = True
                logger.debug("TN3270E negotiated")
            else:
                logger.warning("TN3270E negotiation failed, falling back to TN3270")
        else:
            raise NegotiationError("TN3270 negotiation failed")

        # Send terminal type: 3270
        await self.telnet.request_subnegotiation(
            telnetlib3.TerminalType, b"IBM-3279-2-E"  # Example model
        )

    async def send_data(self, data: bytes):
        """
        Send 3270 data stream.

        :param data: 3270 data stream bytes.
        """
        if not self.telnet:
            raise ProtocolError("Not connected")
        await self.telnet.write(data)
        logger.debug(f"Sent {len(data)} bytes")

    async def receive_data(self, timeout: float = 5.0) -> bytes:
        """
        Receive 3270 data stream.

        :param timeout: Read timeout in seconds.
        :return: Received bytes.
        """
        if not self.telnet:
            raise ProtocolError("Not connected")
        data = await self.telnet.read_until(b"\x00", timeout=timeout)  # EOR or simple delimiter
        logger.debug(f"Received {len(data)} bytes")
        return data

    async def close(self):
        """Close the connection."""
        if self.telnet:
            await self.telnet.close()
            self.telnet = None
            logger.info("Connection closed")

    def is_connected(self) -> bool:
        """Check if connected."""
        return self.telnet is not None


# Sync wrapper for convenience (since telnetlib3 is async, use asyncio.run for sync calls)
import asyncio


def sync_connect(handler: TN3270Handler):
    """Synchronous wrapper for connect."""
    asyncio.run(handler.connect())


def sync_send(handler: TN3270Handler, data: bytes):
    """Synchronous wrapper for send_data."""
    asyncio.run(handler.send_data(data))


def sync_receive(handler: TN3270Handler, timeout: float = 5.0) -> bytes:
    """Synchronous wrapper for receive_data."""
    return asyncio.run(handler.receive_data(timeout))


def sync_close(handler: TN3270Handler):
    """Synchronous wrapper for close."""
    asyncio.run(handler.close())