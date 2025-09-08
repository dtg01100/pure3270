"""TN3270 protocol handler using telnetlib3 for networking."""

import logging
from typing import Optional, BinaryIO
import asyncio

# TN3270E constants
IAC = 0xff
SB = 0xfa
SE = 0xf0
DO = 0xfd
DONT = 0xfe
WILL = 0xfb
WONT = 0xfc
TELOPT_TN3270E = 24
TN3270E_OP_DEVICE_TYPE = 0
TN3270E_OP_REQUEST = 1
TN3270E_OP_IS = 2
TN3270E_OP_REJECT = 3
TN3270E_OP_FUNCTIONS = 1
TN3270E_DT_BIND_IMAGE = 4
TN3270E_DT_UNBIND = 5
TN3270E_DT_3270_DATA = 0
TN3270E_FUNC_BIND_IMAGE = 1
TN3270E_FUNC_RESPONSES = 3
TN3270E_FUNC_SYSREQ = 5
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
        self.reader = None
        self.writer = None
        self.negotiated_tn3270e = False
        self.supports_tn3270 = False
        self.lu_name: Optional[str] = None
        self.screen_rows = 24
        self.screen_cols = 80
        self.bound = False

    async def connect(self):
        """
        Establish connection and negotiate TN3270/TN3270E.

        :raises ConnectionError: If connection fails.
        :raises NegotiationError: If negotiation fails.
        """
        try:
            if self.ssl_context:
                self.reader, self.writer = await asyncio.open_connection(self.host, self.port, ssl=self.ssl_context)
            else:
                self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            # Skip WONT ENVIRON to avoid connection reset
            logger.debug("Skipping WONT ENVIRON")

            # Read any initial data from server
            try:
                initial_data = await self.reader.read(1024)
                logger.debug(f"Initial data from server: {initial_data.hex() if initial_data else 'None'}")
            except Exception as e:
                logger.warning(f"Initial read warning: {e}")

            logger.info(f"Connected to {self.host}:{self.port}")

            # Negotiate TN3270
            await self._negotiate_tn3270()

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}")

    async def _negotiate_tn3270(self):
        """Perform TN3270 negotiation aligned with s3270."""
        # Send DO TN3270E directly
        do_tn3270e = b'\xff\xfd\x24'  # IAC DO TN3270E
        await self.writer.write(do_tn3270e)
        await self.writer.drain()
        logger.debug(f"Sent DO TN3270E: {do_tn3270e.hex()}")
        try:
            response = await asyncio.wait_for(self.reader.read(1024), timeout=5.0)
            logger.debug(f"Response to DO TN3270E: {response.hex()}")
        except asyncio.TimeoutError as e:
            logger.warning(f"Timeout waiting for DO TN3270E response: {e}")
            self.supports_tn3270 = False
            self.negotiated_tn3270e = False
            return
        except Exception as e:
            logger.warning(f"Unexpected error on DO TN3270E read: {e}")
            self.supports_tn3270 = False
            self.negotiated_tn3270e = False
            return

        if b"\xff\xfb\x24" in response:  # WILL TN3270E
            logger.info("Received WILL TN3270E")
            # Send SB TN3270E DEVICE_TYPE REQUEST
            model = b'IBM-3279-4-E'
            sb_device_request = b'\xff\xfa\x18\x00\x01' + model + b'\xff\xf0'  # IAC SB TELOPT DEVICE_TYPE REQUEST model IAC SE
            await self.writer.write(sb_device_request)
            await self.writer.drain()
            logger.debug(f"Sent SB DEVICE_TYPE REQUEST: {sb_device_request.hex()}")
            try:
                dev_response = await asyncio.wait_for(self.reader.read(1024), timeout=5.0)
                logger.debug(f"Device type response: {dev_response.hex()}")
            except asyncio.TimeoutError as e:
                logger.warning(f"Timeout waiting for device type response: {e}")
                self.negotiated_tn3270e = False
                self.supports_tn3270 = True  # Assume basic
                return
            except Exception as e:
                logger.warning(f"Error on device type read: {e}")
                self.negotiated_tn3270e = False
                self.supports_tn3270 = True
                return

            if b"\xff\xfa\x18\x00\x02" in dev_response:  # SB DEVICE_TYPE IS
                logger.info("Received DEVICE_TYPE IS, proceeding to FUNCTIONS")
                # Send SB TN3270E FUNCTIONS REQUEST with bitmap 0x15
                # (BIND_IMAGE=1, RESPONSES=3 bit2=4, SYSREQ=5 bit4=16 -> 1+4+16=21=0x15)
                bitmap = b'\x15'
                sb_functions_request = (b'\xff\xfa\x18\x01\x01' + bitmap +
                                      b'\xff\xf0')  # IAC SB TELOPT FUNCTIONS REQUEST bitmap IAC SE
                await self.writer.write(sb_functions_request)
                await self.writer.drain()
                logger.debug(f"Sent SB FUNCTIONS REQUEST: {sb_functions_request.hex()}")
                try:
                    func_response = await asyncio.wait_for(self.reader.read(1024), timeout=5.0)
                    logger.debug(f"Functions response: {func_response.hex()}")
                except asyncio.TimeoutError as e:
                    logger.warning(f"Timeout waiting for functions response: {e}")
                    self.negotiated_tn3270e = False
                    self.supports_tn3270 = False  # Fallback to ASCII on timeout
                    return
                except Exception as e:
                    logger.warning(f"Error on functions read: {e}")
                    self.negotiated_tn3270e = False
                    self.supports_tn3270 = False
                    return

                if b"\xff\xfa\x18\x01\x02" in func_response:  # SB FUNCTIONS IS
                    logger.info("Received FUNCTIONS IS, full TN3270E negotiated")
                    self.negotiated_tn3270e = True
                    self.supports_tn3270 = True
                else:
                    logger.warning("No FUNCTIONS IS, partial negotiation - fallback to ASCII")
                    self.negotiated_tn3270e = False
                    self.supports_tn3270 = False
            elif b"\xff\xfa\x18\x00\x03" in dev_response:  # SB DEVICE_TYPE REJECT
                reject_reason = dev_response[dev_response.find(b'\xff\xfa\x18\x00\x03') + 5] if len(dev_response) > 5 else 0
                if reject_reason == 0x01:  # TN3270E_REASON_UNSUPPORTED_REQ
                    logger.info("Received DEVICE_TYPE REJECT with UNSUPPORTED_REQ, fallback to ASCII")
                else:
                    logger.info(f"Received DEVICE_TYPE REJECT with reason 0x{reject_reason:02x}, fallback to ASCII")
                self.negotiated_tn3270e = False
                self.supports_tn3270 = False
            else:
                logger.warning("Unexpected device type response - fallback to ASCII")
                self.negotiated_tn3270e = False
                self.supports_tn3270 = False
        elif b"\xff\xfc\x24" in response:  # WONT TN3270E
            logger.info("Received WONT TN3270E, falling back to ASCII")
            self.supports_tn3270 = False
            self.negotiated_tn3270e = False
        else:
            logger.warning("No clear TN3270E response, assuming ASCII fallback")
            self.supports_tn3270 = False
            self.negotiated_tn3270e = False
        # Continue to EOR and terminal type anyway

        # Send DO EOR for TN3270
        do_eor = b'\xff\xfd\x19'  # IAC DO EOR
        await self.writer.write(do_eor)
        await self.writer.drain()
        logger.debug(f"Sent DO EOR: {do_eor.hex()}")
        try:
            eor_resp = await asyncio.wait_for(self.reader.read(1024), timeout=5.0)
            logger.debug(f"Response to DO EOR: {eor_resp.hex()}")
        except asyncio.TimeoutError as e:
            logger.warning(f"Timeout waiting for DO EOR response: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error on DO EOR read: {e}")
        else:
            if b"\xff\xfb\x19" in eor_resp:
                logger.info("Received WILL EOR")
            else:
                logger.warning("EOR not accepted or no response, continuing")

    async def send_data(self, data: bytes):
        """
        Send 3270 data stream.

        :param data: 3270 data stream bytes.
        :raises ProtocolError: If not connected.
        """
        if self.writer is None:
            logger.error("Not connected")
            raise ProtocolError("Not connected")
        await self.writer.write(data)
        await self.writer.drain()
        logger.debug(f"Sent {len(data)} bytes")

    async def receive_data(self, timeout: float = 10.0) -> bytes:
        """
        Receive 3270 data stream, handling TN3270E headers and BIND/UNBIND.
        Loops until EOR or full buffer, matching s3270 blocking behavior.

        :param timeout: Overall read timeout in seconds (default 10s like s3270).
        :return: Received bytes (stripped of TN3270E header if applicable, up to EOR).
        :raises ProtocolError: If not connected.
        """
        if self.reader is None:
            logger.error("Not connected")
            raise ProtocolError("Not connected")

        logger.info(f"Starting blocking read with {timeout}s timeout (waiting for EOR or full response)")
        full_data = b""
        start_time = asyncio.get_event_loop().time()
        while True:
            remaining_time = timeout - (asyncio.get_event_loop().time() - start_time)
            if remaining_time <= 0:
                logger.warning("Read timeout exceeded, returning partial data")
                break
            try:
                chunk = await asyncio.wait_for(self.reader.read(4096), timeout=remaining_time)
                if not chunk:
                    logger.info("Connection closed by peer")
                    break
                full_data += chunk
                logger.debug(f"Received chunk of {len(chunk)} bytes, total {len(full_data)} bytes")

                # Check for EOR (IAC EOR)
                if IAC in full_data[-2:] and full_data[-1] == 0x19:  # EOR is 0x19
                    logger.info("EOR detected, completing read")
                    full_data = full_data[:-2]  # Remove IAC EOR
                    break

                # For non-TN3270E, check for GA (IAC GA 249)
                if not self.negotiated_tn3270e and IAC in full_data[-2:] and full_data[-1] == 0xf9:  # GA is 0xf9
                    logger.info("GA detected in fallback mode, completing read")
                    full_data = full_data[:-2]  # Remove IAC GA
                    break

                # Arbitrary full buffer check (e.g., screen size * 2 for safety)
                if len(full_data) > self.screen_rows * self.screen_cols * 2:
                    logger.info("Full buffer reached, completing read")
                    break

            except asyncio.TimeoutError:
                logger.warning(f"Chunk read timeout after {remaining_time}s, checking data")
                if IAC in full_data[-2:] and full_data[-1] in (0x19, 0xf9):  # EOR or GA
                    logger.info("EOR/GA found after timeout, completing read")
                    if full_data[-1] == 0x19:
                        full_data = full_data[:-2]
                    break
                else:
                    logger.warning("No EOR/GA after timeout, returning partial data")
                    break
            except Exception as e:
                logger.error(f"Error during receive: {e}")
                raise ProtocolError(f"Receive error: {e}")

        logger.info(f"Read completed: {len(full_data)} bytes")
        data = full_data

        # Strip Telnet IAC sequences (basic, including subnegotiations)
        clean_data = b""
        i = 0
        while i < len(data):
            if data[i] == IAC:
                if i + 1 < len(data):
                    cmd = data[i + 1]
                    if cmd == SB:
                        # Skip subnegotiation until SE
                        j = i + 2
                        while j < len(data) and data[j] != SE:
                            j += 1
                        if j < len(data) and data[j] == SE:
                            j += 1
                        i = j
                        continue
                    elif cmd in (WILL, WONT, DO, DONT):
                        i += 3
                        continue
                    else:
                        i += 2
                        continue
                else:
                    break
            else:
                clean_data += bytes([data[i]])
                i += 1
        data = clean_data

        if self.negotiated_tn3270e and len(data) >= 6:
            data_type = data[0]
            if data_type == TN3270E_DT_BIND_IMAGE:
                logger.info("Received BIND_IMAGE")
                bind_data = data[6:]
                if len(bind_data) > 0 and bind_data[0] == 0xF0:  # BIND RU type
                    # Basic PLU name parse (standard offset 17 for length, 18 for name)
                    if len(bind_data) > 18:
                        name_len = bind_data[17]
                        if 0 < name_len <= 8 and len(bind_data) >= 18 + name_len:
                            try:
                                self.lu_name = bind_data[18:18 + name_len].decode('ascii', errors='ignore')
                                logger.info(f"Parsed LU name from BIND: {self.lu_name}")
                            except Exception as e:
                                logger.warning(f"Failed to decode LU name: {e}")
                    # Basic screen size parse (SSIZE at offset 8)
                    if len(bind_data) > 9:
                        ssize = bind_data[8]
                        if ssize == 0x00:
                            self.screen_rows = 24
                            self.screen_cols = 80
                        elif ssize == 0x41:
                            self.screen_rows = 24
                            self.screen_cols = 132
                        elif ssize == 0xC4:
                            self.screen_rows = 32
                            self.screen_cols = 80
                        # Add more mappings if needed
                        logger.info(f"Parsed screen size from BIND: {self.screen_rows} x {self.screen_cols}")
                    self.bound = True
                return b''  # No screen data in BIND
            elif data_type == TN3270E_DT_UNBIND:
                logger.info("Received UNBIND")
                if len(data) > 6:
                    reason = data[6]
                    logger.info(f"UNBIND reason code: 0x{reason:02x}")
                self.bound = False
                self.lu_name = None
                return b''  # No screen data in UNBIND
            # For 3270_DATA or other, strip header and return payload
            elif data_type == TN3270E_DT_3270_DATA:
                logger.debug("Received TN3270E 3270_DATA, stripping header")
                return data[6:]
            # Handle other data types as raw for now
            return data[6:] if len(data) >= 6 else data
        # Fallback for non-TN3270E
        return data

    async def close(self):
        """Close the connection."""
        if self.writer is not None:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.warning(f"Close warning: {e}")
            self.writer = None
            self.reader = None
            logger.info("Connection closed")

    def is_connected(self) -> bool:
        """Check if connected."""
        return self.writer is not None

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
