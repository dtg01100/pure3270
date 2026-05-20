"""SSCP-LU mode menu server - TN3270E with SSCP-LU session."""

import asyncio

from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from pure3270.protocol.utils import (
    IAC,
    WILL,
    SB,
    SE,
    TELOPT_EOR,
    TELOPT_TN3270E,
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IS,
    SSCP_LU_DATA,
)

from mock_server.tn3270_mock_server import TN3270MockServer


class MenuSSCP_LUServer(TN3270MockServer):
    """Menu server using TN3270E SSCP-LU mode.

    SSCP-LU is a sub-mode of TN3270E where the terminal behaves
    more like NVT line mode, gathering a line at a time.
    Uses TN3270E data type 0x07 for SSCP-LU.
    """

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        writer.write(bytes([IAC, WILL, TELOPT_EOR]))
        await writer.drain()
        writer.write(bytes([IAC, WILL, TELOPT_TN3270E]))
        await writer.drain()

        writer.write(bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_IS]))
        await writer.drain()

        device_type = self.config.terminal_type if self.config else "IBM-3278-2-E"
        lu_name = self.config.lu_name if self.config else "LUNAME01"

        device_type_is = (
            bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_IS])
            + device_type.encode("ascii")
            + b"\x00"
            + lu_name.encode("ascii")
            + bytes([IAC, SE])
        )
        writer.write(device_type_is)
        await writer.drain()

        header = bytes([SSCP_LU_DATA, 0x00, 0x00, 0x00])
        menu_text = translate_ascii_to_ebcdic("SSCP-LU MODE MENU\nSelect: ")
        writer.write(header + menu_text)
        writer.write(bytes([IAC, TELOPT_EOR]))
        await writer.drain()

        try:
            while True:
                data = await asyncio.wait_for(reader.read(4096), timeout=30)
                if not data:
                    break
        except asyncio.TimeoutError:
            pass