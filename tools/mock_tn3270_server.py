#!/usr/bin/env python3
"""
Mock TN3270 Server for Fuzz Testing.

A simple TN3270 server that responds to client commands with synthetic
screens, suitable for differential fuzz testing between pure3270 and s3270.

Features:
- Handles TN3270 protocol negotiation
- Maintains screen buffer state
- Responds to basic commands (Clear, Enter, PF keys, text input)
- Generates deterministic screens for reproducible testing
- Supports multiple concurrent connections

Usage:
    python tools/mock_tn3270_server.py [--port PORT] [--host HOST]
"""

import asyncio
import logging
import struct
import sys
from pathlib import Path
from typing import Optional

# Add pure3270 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pure3270.emulation.ebcdic import (
    translate_ascii_to_ebcdic,
    translate_ebcdic_to_ascii,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TN3270 protocol constants
IAC = 255  # Interpret As Command
DO = 253
DONT = 254
WILL = 251
WONT = 252
SB = 250  # Subnegotiation Begin
SE = 240  # Subnegotiation End

# Telnet options
TELOPT_BINARY = 0
TELOPT_ECHO = 1
TELOPT_TTYPE = 24
TELOPT_EOR = 25
TELOPT_TN3270E = 40

# TN3270 commands
CMD_ERASE_WRITE = 0xF5
CMD_ERASE_WRITE_ALT = 0x7E
CMD_READ_BUFFER = 0xF2
CMD_WRITE = 0xF1
CMD_READ_MODIFIED = 0xF6

# TN3270 orders
ORDER_SF = 0x1D  # Start Field
ORDER_SBA = 0x11  # Set Buffer Address
ORDER_IC = 0x13  # Insert Cursor
ORDER_PT = 0x05  # Program Tab
ORDER_RA = 0x3C  # Repeat to Address
ORDER_EUA = 0x12  # Erase Unprotected to Address

# AID codes
AID_ENTER = 0x7D
AID_PF1 = 0xF1
AID_PF2 = 0xF2
AID_PF3 = 0xF3
AID_CLEAR = 0x6D
AID_PA1 = 0x6C
AID_PA2 = 0x6E
AID_PA3 = 0x6B


class MockTN3270Server:
    """Simple mock TN3270 server for fuzz testing."""

    def __init__(self, rows: int = 24, cols: int = 80):
        self.rows = rows
        self.cols = cols
        self.buffer_size = rows * cols
        self.active_connections = 0

    def _create_welcome_screen(self) -> bytes:
        """Create a simple welcome screen."""
        # Build a simple TN3270 data stream with Erase/Write command
        screen = bytearray()

        # Command: Erase/Write
        screen.append(CMD_ERASE_WRITE)

        # WCC (Write Control Character): Reset, unlock keyboard
        screen.append(0xC3)

        # Write welcome message at position 0,0
        welcome_text = "Mock TN3270 Server - Ready for Testing"
        welcome_ebcdic = translate_ascii_to_ebcdic(welcome_text)
        screen.extend(welcome_ebcdic)

        return bytes(screen)

    def _create_response_screen(self, aid: int, data: bytes) -> bytes:
        """Create a response screen based on AID and input data."""
        screen = bytearray()

        # Command: Erase/Write
        screen.append(CMD_ERASE_WRITE)

        # WCC
        screen.append(0xC3)

        # Create response based on AID
        if aid == AID_ENTER:
            response_text = f"ENTER received - {len(data)} bytes"
        elif aid == AID_CLEAR:
            response_text = "Screen cleared"
        elif aid == AID_PF1:
            response_text = "PF1 pressed"
        elif aid == AID_PF2:
            response_text = "PF2 pressed"
        elif aid == AID_PF3:
            response_text = "PF3 pressed"
        elif aid == AID_PA1:
            response_text = "PA1 pressed"
        elif aid == AID_PA2:
            response_text = "PA2 pressed"
        elif aid == AID_PA3:
            response_text = "PA3 pressed"
        else:
            response_text = f"AID 0x{aid:02X} received"

        response_ebcdic = translate_ascii_to_ebcdic(response_text)
        screen.extend(response_ebcdic)

        # Add a line showing what data was received (truncated)
        if len(data) > 3:  # Skip AID, cursor pos
            data_preview = data[3 : min(len(data), 40)]
            try:
                data_ascii = translate_ebcdic_to_ascii(data_preview)
                data_line = f" | Data: {data_ascii}"
                # Position at row 2
                screen.append(ORDER_SBA)
                screen.extend(self._encode_buffer_address(self.cols * 1))
                screen.extend(translate_ascii_to_ebcdic(data_line))
            except Exception:
                pass

        return bytes(screen)

    def _encode_buffer_address(self, addr: int) -> bytes:
        """Encode buffer address in TN3270 format (12-bit or 14-bit)."""
        # Use simple 12-bit encoding for addresses < 4096
        if addr < 4096:
            high = ((addr >> 6) & 0x3F) | 0x40
            low = (addr & 0x3F) | 0x40
            return bytes([high, low])
        else:
            # 14-bit encoding
            high = ((addr >> 8) & 0x3F) | 0x40
            low = addr & 0xFF
            return bytes([high, low])

    async def _send_telnet_options(self, writer: asyncio.StreamWriter):
        """Send initial telnet option negotiation."""
        # DO TERMINAL-TYPE
        writer.write(bytes([IAC, DO, TELOPT_TTYPE]))

        # DO EOR
        writer.write(bytes([IAC, DO, TELOPT_EOR]))

        # DO BINARY
        writer.write(bytes([IAC, DO, TELOPT_BINARY]))

        # WILL EOR
        writer.write(bytes([IAC, WILL, TELOPT_EOR]))

        # WILL BINARY
        writer.write(bytes([IAC, WILL, TELOPT_BINARY]))

        await writer.drain()

    async def _send_data(self, writer: asyncio.StreamWriter, data: bytes):
        """Send TN3270 data with IAC EOR marker."""
        writer.write(data)
        # Send EOR marker
        writer.write(bytes([IAC, 0xEF]))  # IAC EOR
        await writer.drain()

    async def handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Handle a single client connection."""
        client_addr = writer.get_extra_info("peername")
        logger.info(f"New connection from {client_addr}")
        self.active_connections += 1

        try:
            # Send telnet options
            await self._send_telnet_options(writer)

            # Wait a bit for client to respond to options
            await asyncio.sleep(0.1)

            # Send welcome screen
            await self._send_data(writer, self._create_welcome_screen())

            # Handle client commands
            while True:
                try:
                    data = await asyncio.wait_for(reader.read(4096), timeout=30.0)
                except asyncio.TimeoutError:
                    logger.debug(f"[{client_addr}] Timeout waiting for data")
                    break

                if not data:
                    logger.info(f"[{client_addr}] Client closed connection")
                    break

                # Process telnet commands and TN3270 data
                i = 0
                tn3270_data = bytearray()
                while i < len(data):
                    if data[i] == IAC and i + 1 < len(data):
                        cmd = data[i + 1]
                        if cmd in (DO, DONT, WILL, WONT) and i + 2 < len(data):
                            opt = data[i + 2]
                            logger.debug(f"[{client_addr}] Telnet: {cmd} {opt}")

                            # Respond to options
                            if cmd == WILL:
                                # Client will do something - acknowledge
                                writer.write(bytes([IAC, DO, opt]))
                            elif cmd == DO:
                                # Client wants us to do something
                                if opt in (TELOPT_BINARY, TELOPT_EOR):
                                    writer.write(bytes([IAC, WILL, opt]))
                                else:
                                    writer.write(bytes([IAC, WONT, opt]))

                            i += 3
                        elif cmd == SB:
                            # Subnegotiation - skip until SE
                            i += 2
                            while i < len(data) and not (
                                data[i] == IAC
                                and i + 1 < len(data)
                                and data[i + 1] == SE
                            ):
                                i += 1
                            i += 2  # Skip IAC SE
                        elif cmd == IAC:
                            # Escaped IAC
                            tn3270_data.append(IAC)
                            i += 2
                        else:
                            i += 2
                    else:
                        tn3270_data.append(data[i])
                        i += 1

                # Process TN3270 data if present
                if tn3270_data:
                    logger.debug(
                        f"[{client_addr}] TN3270 data: {len(tn3270_data)} bytes"
                    )

                    # Extract AID if present
                    if len(tn3270_data) > 0:
                        aid = tn3270_data[0]

                        # Generate response
                        response = self._create_response_screen(aid, bytes(tn3270_data))
                        await self._send_data(writer, response)

                await writer.drain()

        except Exception as e:
            logger.error(f"[{client_addr}] Error: {e}", exc_info=True)
        finally:
            logger.info(f"[{client_addr}] Connection closed")
            writer.close()
            await writer.wait_closed()
            self.active_connections -= 1

    async def start_server(self, host: str = "127.0.0.1", port: int = 2324):
        """Start the mock TN3270 server."""
        server = await asyncio.start_server(self.handle_connection, host, port)

        logger.info(f"Mock TN3270 server started on {host}:{port}")
        logger.info(f"Screen size: {self.rows}x{self.cols}")

        try:
            async with server:
                await server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Mock TN3270 server for fuzz testing")
    parser.add_argument(
        "--port", "-p", type=int, default=2324, help="Port to listen on (default: 2324)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--rows", type=int, default=24, help="Screen rows (default: 24)"
    )
    parser.add_argument(
        "--cols", type=int, default=80, help="Screen columns (default: 80)"
    )

    args = parser.parse_args()

    server = MockTN3270Server(rows=args.rows, cols=args.cols)
    await server.start_server(host=args.host, port=args.port)


if __name__ == "__main__":
    asyncio.run(main())
