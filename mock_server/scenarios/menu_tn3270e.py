"""Menu TN3270E server scenario - full TN3270E negotiation with menu screen."""

import asyncio

from mock_server.tn3270_mock_server import ServerConfig, TN3270MockServer
from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from pure3270.protocol.data_stream import SBA, SF
from pure3270.protocol.tn3270e_header import TN3270EHeader
from pure3270.protocol.utils import (
    DO,
    IAC,
    SB,
    SE,
    TELOPT_EOR,
    TELOPT_TN3270E,
    TELOPT_TTYPE,
    TN3270_DATA,
    TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS,
    TN3270E_IS,
    TN3270E_REQUEST,
    TN3270E_SEND,
    TTYPE_SEND,
    WILL,
)


class MenuTN3270EServer(TN3270MockServer):
    """TN3270E mock server providing full negotiation sequence and menu screen.

    Goals:
    - Send WILL TTYPE, WILL EOR, WILL TN3270E to client
    - Request terminal type (SB TTYPE SEND SE)
    - Perform TN3270E DEVICE-TYPE negotiation
    - Perform TN3270E FUNCTIONS negotiation
    - Send 3270 data stream with menu screen
    - Keep connection alive waiting for input
    """

    terminal_type: str | None = "IBM-3278-2-E"
    requested_device_type: str | None = None

    def __init__(
        self,
        config: ServerConfig | None = None,
        host: str | None = None,
        port: int | None = None,
        requested_device_type: str | None = None,
        functions_mode: str | None = None,
        terminal_type: str | None = None,
    ) -> None:
        if config is not None:
            super().__init__(config=config)
            self.requested_device_type = requested_device_type or config.terminal_type
            self.functions_mode = functions_mode or config.functions_mode
            self.terminal_type = terminal_type or config.terminal_type
        else:
            super().__init__(host=host, port=port)
            self.requested_device_type = requested_device_type
            self.functions_mode = (
                functions_mode if functions_mode is not None else "request"
            )
            self.terminal_type = (
                terminal_type if terminal_type is not None else "IBM-3278-2-E"
            )

    def build_menu_stream(self) -> bytes:
        """Build a minimal 3270 data stream for a simple menu screen."""
        wcc = bytes([0x00])
        sba_addr_1 = bytes([0x00, 0x00])
        sf_attr_1 = bytes([0xF0])
        text1 = translate_ascii_to_ebcdic("HELLO")
        sba_addr_2 = bytes([0x01, 0x10])
        sf_attr_2 = bytes([0xF0])
        text2 = translate_ascii_to_ebcdic("WORLD")
        return b"".join(
            [
                wcc,
                bytes([SBA]),
                sba_addr_1,
                bytes([SF]),
                sf_attr_1,
                text1,
                bytes([SBA]),
                sba_addr_2,
                bytes([SF]),
                sf_attr_2,
                text2,
            ]
        )

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Perform full TN3270E negotiation and send menu screen."""
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
            for opt_label, opt_code in [
                ("WILL TTYPE", TELOPT_TTYPE),
                ("WILL EOR", TELOPT_EOR),
                ("WILL TN3270E", TELOPT_TN3270E),
            ]:
                _send(bytes([IAC, WILL, opt_code]), opt_label)
                await writer.drain()
                await asyncio.sleep(0.02)

            _send(bytes([IAC, SB, TELOPT_TTYPE, TTYPE_SEND, IAC, SE]), "TTYPE SEND")
            await writer.drain()

            try:
                term_resp = await asyncio.wait_for(
                    reader.readuntil(bytes([IAC, SE])), timeout=1.5
                )
                self._received.append(term_resp)
                print(f"[MOCK] <- TTYPE RESP: {term_resp!r}")
            except Exception:
                print("[MOCK] (no TTYPE response within 1.5s)")

            if self.requested_device_type:
                requested = self.requested_device_type
                lu_name = ""
                _send(
                    bytes(
                        [IAC, SB, TELOPT_TN3270E, TN3270E_DEVICE_TYPE, TN3270E_REQUEST]
                    )
                    + requested.encode("ascii")
                    + b"\x00"
                    + lu_name.encode("ascii")
                    + bytes([IAC, SE]),
                    "TN3270E DEVICE-TYPE REQUEST",
                )
            else:
                _send(
                    bytes(
                        [
                            IAC,
                            SB,
                            TELOPT_TN3270E,
                            TN3270E_DEVICE_TYPE,
                            TN3270E_SEND,
                            IAC,
                            SE,
                        ]
                    ),
                    "TN3270E DEVICE-TYPE SEND",
                )
            await writer.drain()
            try:
                devtype_resp = await asyncio.wait_for(
                    reader.readuntil(bytes([IAC, SE])), timeout=1.5
                )
                self._received.append(devtype_resp)
                print(f"[MOCK] <- DEVICE-TYPE RESP: {devtype_resp!r}")
                device_type = self.requested_device_type or "IBM-3278-2"
                lu_name = "TDC01702"
                _send(
                    bytes(
                        [
                            IAC,
                            SB,
                            TELOPT_TN3270E,
                            TN3270E_DEVICE_TYPE,
                            TN3270E_IS,
                        ]
                    )
                    + device_type.encode("ascii")
                    + b"\x00"
                    + lu_name.encode("ascii")
                    + bytes([IAC, SE]),
                    "TN3270E DEVICE-TYPE IS",
                )
                await writer.drain()
            except Exception:
                print("[MOCK] (no DEVICE-TYPE response within 1.5s)")

            functions_bytes = bytes([0x01, 0x02, 0x03])
            if self.functions_mode == "request":
                _send(
                    bytes(
                        [
                            IAC,
                            SB,
                            TELOPT_TN3270E,
                            TN3270E_FUNCTIONS,
                            TN3270E_REQUEST,
                            *functions_bytes,
                            IAC,
                            SE,
                        ]
                    ),
                    "TN3270E FUNCTIONS REQUEST",
                )
            else:
                _send(
                    bytes(
                        [
                            IAC,
                            SB,
                            TELOPT_TN3270E,
                            TN3270E_FUNCTIONS,
                            TN3270E_SEND,
                            *functions_bytes,
                            IAC,
                            SE,
                        ]
                    ),
                    "TN3270E FUNCTIONS SEND",
                )
                _send(
                    bytes(
                        [
                            IAC,
                            SB,
                            TELOPT_TN3270E,
                            TN3270E_FUNCTIONS,
                            TN3270E_IS,
                            *functions_bytes,
                            IAC,
                            SE,
                        ]
                    ),
                    "TN3270E FUNCTIONS IS",
                )
            await writer.drain()
            try:
                functions_resp = await asyncio.wait_for(
                    reader.readuntil(bytes([IAC, SE])), timeout=1.0
                )
                self._received.append(functions_resp)
                print(f"[MOCK] <- FUNCTIONS RESP: {functions_resp!r}")
            except Exception:
                print("[MOCK] (no FUNCTIONS response within 1.0s)")

            header = TN3270EHeader(
                data_type=TN3270_DATA,
                request_flag=0,
                response_flag=0,
                seq_number=1,
            ).to_bytes()
            payload = self.build_menu_stream()
            _send(header + payload, "TN3270E 3270-DATA")
            _send(bytes([IAC, TELOPT_EOR]), "IAC EOR")
            await writer.drain()

            try:
                while True:
                    data = await asyncio.wait_for(reader.read(4096), timeout=30)
                    if not data:
                        break
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
