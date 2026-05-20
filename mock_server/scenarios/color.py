"""Color display server - tests 3279 color and extended attributes."""

import asyncio
from pure3270.protocol.utils import (
    IAC,
    WILL,
    SB,
    SE,
    WILL,
    TELOPT_EOR,
    TELOPT_TN3270E,
    TN3270_DATA,
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IS,
    TN3270E_SEND,
    TN3270E_REQUEST,
    TTYPE_SEND,
    TELOPT_TTYPE,
)
from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from mock_server.tn3270_mock_server import TN3270MockServer


class ColorServer(TN3270MockServer):
    """Server that sends color/attribute display.

    Sends a screen demonstrating various 3279 color attributes
    and extended attribute types.
    """

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        writer.write(bytes([IAC, WILL, TELOPT_TTYPE]))
        await writer.drain()
        writer.write(bytes([IAC, WILL, TELOPT_EOR]))
        await writer.drain()
        writer.write(bytes([IAC, WILL, TELOPT_TN3270E]))
        await writer.drain()

        writer.write(bytes([IAC, SB, TELOPT_TTYPE, TTYPE_SEND, IAC, SE]))
        await writer.drain()

        try:
            await asyncio.wait_for(reader.readuntil(bytes([IAC, SE])), timeout=1.5)
        except Exception:
            pass

        device_type = "IBM-3279-2-E"
        lu_name = "COLOR01"
        writer.write(
            bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_IS])
            + device_type.encode("ascii")
            + b"\x00"
            + lu_name.encode("ascii")
            + bytes([IAC, SE])
        )
        await writer.drain()

        from pure3270.protocol.tn3270e_header import TN3270EHeader

        header = TN3270EHeader(
            data_type=TN3270_DATA,
            request_flag=0,
            response_flag=0,
            seq_number=1,
        ).to_bytes()

        buffer = bytearray()
        buffer.append(0x00)

        buffer.extend(self.build_sba(0, 0))
        buffer.append(0x1D)
        buffer.append(0xF4)
        buffer.extend(translate_ascii_to_ebcdic("COLOR TEST SCREEN"))

        buffer.extend(self.build_sba(2, 0))
        buffer.append(0x1D)
        buffer.append(0xF1)
        buffer.extend(translate_ascii_to_ebcdic("Blue Text"))

        buffer.extend(self.build_sba(4, 0))
        buffer.append(0x1D)
        buffer.append(0xF2)
        buffer.extend(translate_ascii_to_ebcdic("Red Text"))

        buffer.extend(self.build_sba(6, 0))
        buffer.append(0x1D)
        buffer.append(0xF3)
        buffer.extend(translate_ascii_to_ebcdic("Green Text"))

        writer.write(header + bytes(buffer))
        writer.write(bytes([IAC, TELOPT_EOR]))
        await writer.drain()

        try:
            while True:
                data = await asyncio.wait_for(reader.read(4096), timeout=30)
                if not data:
                    break
        except asyncio.TimeoutError:
            pass

    def build_sba(self, row: int, col: int) -> bytes:
        """Build SBA order for 12-bit addressing."""
        addr = (row * 80) + col
        high = (addr >> 6) | 0x40
        low = (addr & 0x3F) | 0x40
        return bytes([0x11, high, low])