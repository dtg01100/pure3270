"""TN3270 (non-E) menu server - standard TN3270 negotiation."""

import asyncio

from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from pure3270.protocol.data_stream import SBA, SF
from pure3270.protocol.utils import (
    IAC,
    SB,
    SE,
    TELOPT_EOR,
    TELOPT_TTYPE,
    TTYPE_SEND,
    WILL,
)
from mock_server.tn3270_mock_server import TN3270MockServer


class Menu3270Server(TN3270MockServer):
    """Menu server using TN3270 (no E) protocol.

    Unlike TN3270E, this does not offer WILL TN3270E option.
    Sends 3270 data stream WITHOUT TN3270E header.
    """

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
            _send(bytes([IAC, WILL, TELOPT_TTYPE]), "WILL TTYPE")
            await writer.drain()
            await asyncio.sleep(0.02)

            _send(bytes([IAC, WILL, TELOPT_EOR]), "WILL EOR")
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

            menu_data = self.build_menu_stream()
            _send(menu_data, "3270-DATA")
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

    def get_sent_trace(self) -> list[bytes]:
        return list(self._trace)

    def get_received_trace(self) -> list[bytes]:
        return list(self._received)