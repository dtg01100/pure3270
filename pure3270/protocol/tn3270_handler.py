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

logger = logging.getLogger(__name__)

class TN3270Handler:
    """
    Handler for TN3270 protocol over Telnet.
    
    Manages stream I/O, negotiation, and data parsing for 3270 emulation.
    """

    async def connect(self, host: Optional[str] = None, port: Optional[int] = None, ssl_context: Optional[ssl.SSLContext] = None) -> None:
        """Connect the handler."""
        # If already have reader/writer (from fixture), just mark as connected
        if self.reader is not None and self.writer is not None:
            self._connected = True
            return
            
        try:
            # Use provided params or fallback to instance values
            connect_host = host or self.host
            connect_port = port or self.port
            connect_ssl = ssl_context or self.ssl_context
            
            reader, writer = await asyncio.open_connection(connect_host, connect_port, ssl=connect_ssl)
            self.reader = reader
            self.writer = writer
            self._connected = True
            
            # Perform negotiation
            await self._negotiate_tn3270()
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Failed to connect: {e}")

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, ssl_context: Optional[ssl.SSLContext] = None, host: str = "localhost", port: int = 23):
        """
        Initialize the TN3270 handler.
        
        Args:
            reader: Asyncio stream reader.
            writer: Asyncio stream writer.
            ssl_context: Optional SSL context for secure connections.
            host: Target host for connection.
            port: Target port for connection.
        
        Raises:
            ValueError: If reader or writer is None.
        """
        if reader is None or writer is None:
            raise ValueError("Reader and writer must not be None.")
        self.reader = reader
        self.writer = writer
        self.ssl_context = ssl_context
        self.host = host
        self.port = port
        self.screen_buffer = ScreenBuffer()
        self.parser = DataStreamParser(self.screen_buffer)
        self._ascii_mode = False
        self._connected = False  # Start as not connected
        self.negotiated_tn3270e = False
        self.lu_name = None
        self.screen_rows = 24
        self.screen_cols = 80

    async def negotiate(self) -> None:
        """
        Perform initial Telnet negotiation.
        
        Sends DO TERMINAL-TYPE and waits for responses.
        
        Raises:
            NegotiationError: If negotiation fails.
        """
        if self.writer is None:
            raise ProtocolError("Writer is None; cannot negotiate.")
        send_iac(self.writer, b'\xff\xfd\x27')  # DO TERMINAL-TYPE
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
        tn3270e_request = b'\x00\x00\x01\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        send_subnegotiation(self.writer, b'\x19', tn3270e_request)
        await self.writer.drain()
        # Parse response
        try:
            response = await self.receive_data(10.0)
            if b'\x28' in response or b'\xff\xfb\x24' in response:  # TN3270E positive response
                self.negotiated_tn3270e = True
                self.parser.parse(response)
                logger.info("TN3270E negotiation successful")
            else:
                self.negotiated_tn3270e = False
                self.set_ascii_mode()
                logger.info("TN3270E negotiation failed, fallback to ASCII")
        except Exception:
            self.negotiated_tn3270e = False
            self.set_ascii_mode()

    def set_ascii_mode(self) -> None:
        """
        Set the handler to ASCII mode fallback.
        
        Disables EBCDIC processing.
        """
        self._ascii_mode = True

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
        if self.reader is None:
            logger.error("Not connected")
            raise ProtocolError("Reader is None; cannot receive data.")
        try:
            data = await asyncio.wait_for(self.reader.read(4096), timeout=timeout)
        except asyncio.TimeoutError:
            raise
        if self._ascii_mode:
            return data
        # Parse and update screen buffer (simplified)
        self.parser.parse(data)
        # Strip EOR if present
        if b'\xff\x19' in data:
            data = data.split(b'\xff\x19')[0]
        return data

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
        return self._connected and self.writer is not None and self.reader is not None
