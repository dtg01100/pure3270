"""NVT mode menu server - plain TELNET without 3270."""

import asyncio

from mock_server.tn3270_mock_server import TN3270MockServer
from pure3270.protocol.utils import IAC, TELOPT_BINARY, TELOPT_EOR, WILL


class MenuNVTServer(TN3270MockServer):
    """Menu server in NVT (character) mode.

    No 3270 negotiation - just plain TELNET with ASCII text.
    Useful for testing ASCII/VT100 fallback behavior.
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
            _send(bytes([IAC, WILL, TELOPT_BINARY]), "WILL BINARY")
            await writer.drain()
            await asyncio.sleep(0.02)

            _send(bytes([IAC, WILL, TELOPT_EOR]), "WILL EOR")
            await writer.drain()
            await asyncio.sleep(0.02)

            menu = "MAIN MENU\n"
            menu += "=========\n"
            menu += "A. Option A\n"
            menu += "B. Option B\n"
            menu += "C. Option C\n"
            menu += "\nSelect: "

            _send(menu.encode("ascii"), "MENU")
            await writer.drain()

            try:
                while True:
                    data = await asyncio.wait_for(reader.read(1024), timeout=30)
                    if not data:
                        break
                    self._received.append(data)
                    writer.write(data)
                    await writer.drain()
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
