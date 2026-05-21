"""SSCP-LU mode menu server - TN3270E with SSCP-LU session."""

import asyncio

from mock_server.tn3270_mock_server import ServerConfig, TN3270MockServer
from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from pure3270.protocol.utils import (
    IAC,
    SB,
    SE,
    SSCP_LU_DATA,
    TELOPT_EOR,
    TELOPT_TN3270E,
    TN3270E_DEVICE_TYPE,
    TN3270E_IS,
    WILL,
)


class MenuSSCP_LUServer(TN3270MockServer):
    """Menu server using TN3270E SSCP-LU mode.

    SSCP-LU is a sub-mode of TN3270E where the terminal behaves
    more like NVT line mode, gathering a line at a time.
    Uses TN3270E data type 0x07 for SSCP-LU.
    """

    terminal_type: str = "IBM-3278-2-E"
    lu_name: str = "LUNAME01"

    def __init__(
        self,
        config: ServerConfig | None = None,
        host: str | None = None,
        port: int | None = None,
        terminal_type: str | None = None,
        lu_name: str | None = None,
    ) -> None:
        if config is not None:
            super().__init__(config=config)
            self.terminal_type = terminal_type or config.terminal_type
            self.lu_name = lu_name or config.lu_name
        else:
            super().__init__(host=host, port=port)
            self.terminal_type = terminal_type or "IBM-3278-2-E"
            self.lu_name = lu_name or "LUNAME01"

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._client_tasks.append(task)
        self._trace: list[bytes] = []
        self._received: list[bytes] = []

        def _send(chunk: bytes, label: str | None = None) -> None:
            if label:
                print(f"[MOCK] -> {label}: {chunk!r}")
            writer.write(chunk)
            self._trace.append(chunk)

        print("[MOCK] handle_client invoked")
        try:
            _send(bytes([IAC, WILL, TELOPT_EOR]), "WILL EOR")
            await writer.drain()
            await asyncio.sleep(0.02)

            _send(bytes([IAC, WILL, TELOPT_TN3270E]), "WILL TN3270E")
            await writer.drain()
            await asyncio.sleep(0.02)

            device_type_is = (
                bytes([IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_IS])
                + self.terminal_type.encode("ascii")
                + b"\x00"
                + (self.lu_name or "LUNAME01").encode("ascii")
                + bytes([IAC, SE])
            )
            _send(device_type_is, "DEVICE-TYPE IS")
            await writer.drain()

            header = bytes([SSCP_LU_DATA, 0x00, 0x00, 0x00])
            menu_text = translate_ascii_to_ebcdic("SSCP-LU MODE MENU\nSelect: ")
            _send(header + menu_text, "SSCP-LU DATA")
            writer.write(header + menu_text)
            _send(bytes([IAC, TELOPT_EOR]), "IAC EOR")
            writer.write(bytes([IAC, TELOPT_EOR]))
            await writer.drain()

            try:
                while True:
                    data = await asyncio.wait_for(reader.read(4096), timeout=30)
                    if not data:
                        break
                    self._received.append(data)
            except asyncio.TimeoutError:
                pass
        except GeneratorExit:
            print("[MOCK] GeneratorExit during handle_client (loop closing)")
        except Exception as e:
            print(f"[MOCK] Exception in handle_client: {e}")
        finally:
            if task is not None and task in self._client_tasks:
                self._client_tasks.remove(task)
            try:
                transport = getattr(writer, "transport", None)
                if transport and not transport.is_closing():
                    writer.close()
            except RuntimeError:
                pass

    def get_sent_trace(self) -> list[bytes]:
        return list(self._trace)

    def get_received_trace(self) -> list[bytes]:
        return list(self._received)
