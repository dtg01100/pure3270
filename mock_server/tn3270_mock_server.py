import asyncio
import struct
import threading
from typing import Awaitable, Callable, Optional

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


class TN3270MockServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 23270,
        scenario: Optional[
            Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]]
        ] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.scenario = scenario if scenario is not None else self.default_scenario
        self._server: Optional[asyncio.AbstractServer] = None

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        await self.scenario(reader, writer)

    async def default_scenario(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        writer.write(b"\xff\xfb\x19")  # IAC WILL EOR
        await writer.drain()
        await asyncio.sleep(0.1)
        writer.write(b"\x00\x00\x00\x00")  # Minimal header
        await writer.drain()
        await asyncio.sleep(0.1)
        writer.close()

    async def _start_in_loop(self) -> None:
        """Internal coroutine executed inside the server loop thread."""
        self._server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        print(
            f"TN3270MockServer started on {self.host}:{self.port} handler={self.handle_client.__qualname__} file={getattr(self.handle_client, '__code__', None) and self.handle_client.__code__.co_filename}"
        )

    def start_threaded(self) -> None:
        """Start server in its own thread + event loop.

        Tests previously started the server using an external loop that stopped
        immediately after scheduling serve_forever(), preventing client handling.
        This isolates the server lifecycle similar to Session's thread model.
        """
        if hasattr(self, "_thread"):
            raise RuntimeError("Server already started")

        self._loop = asyncio.new_event_loop()

        def _runner() -> None:
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._start_in_loop())
            # Keep loop alive to accept connections
            self._loop.run_forever()

        self._thread = threading.Thread(
            target=_runner, name="TN3270MockServer", daemon=True
        )
        self._thread.start()
        # Brief wait for bind
        while not getattr(self, "_server", None):
            pass

    async def start(self) -> None:  # backwards compatibility for existing scenarios
        self.start_threaded()

    async def start_async(self) -> None:
        self.start_threaded()

    async def stop(self) -> None:
        if getattr(self, "_loop", None) and getattr(self, "_server", None):

            def _close() -> None:
                assert self._server is not None
                self._server.close()

            self._loop.call_soon_threadsafe(_close)
            # Allow close to propagate
            await asyncio.sleep(0.05)
            # Wait for server socket to close cleanly to avoid pending task warnings
            try:
                if self._server is not None:
                    fut = asyncio.run_coroutine_threadsafe(
                        self._server.wait_closed(), self._loop
                    )
                    fut.result(timeout=1.0)
            except Exception:
                pass

            def _stop() -> None:
                self._loop.stop()

            self._loop.call_soon_threadsafe(_stop)
            if getattr(self, "_thread", None):
                self._thread.join(timeout=1.0)
            print(f"TN3270MockServer stopped on {self.host}:{self.port}")


class EnhancedTN3270MockServer(TN3270MockServer):
    """Enhanced TN3270/TN3270E mock server providing a closer-to-real
    Telnet option negotiation sequence and minimal TN3270E subnegotiation.

    Goals:
    - Send DO TTYPE, DO EOR, DO TN3270E to client
    - Request terminal type (SB TTYPE SEND SE)
    - Perform simplified TN3270E SEND subnegotiation advertising device type
    - Provide a minimal 3270-DATA record (placeholder) followed by EOR

    NOTE: This is intentionally simplified. It focuses on exercising the
    negotiation paths in pure3270 without emulating full 3270 data stream
    semantics. Future improvements can generate valid 3270 orders.
    """

    terminal_type: str = "IBM-3278-2-E"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 23270,
        requested_device_type: str | None = None,
        functions_mode: str = "request",
    ) -> None:
        super().__init__(host=host, port=port)
        # Optional: request a specific device type first to exercise REQUEST path
        self.requested_device_type = requested_device_type
        self.functions_mode = functions_mode

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Perform a minimal, server-initiated Telnet + TN3270E negotiation.

        We intentionally send only WILL for each option (standard Telnet pattern:
        server offers with WILL, client replies DO). Sending DO from the server is
        non-standard and confused the client's negotiator, which ignored bytes.

        Order chosen:
        1. WILL TTYPE
        2. WILL EOR
        3. WILL TN3270E
        4. SB TTYPE SEND SE  (ask client for terminal type list)
        5. SB TN3270E DEVICE-TYPE SEND SE (request device type negotiation)
        6. SB TN3270E FUNCTIONS SEND SE (request functions list)
        7. Minimal TN3270E 3270-DATA record + IAC EOR
        """

        self._trace: list[bytes] = []
        self._received: list[bytes] = []

        def _send(chunk: bytes, label: str | None = None) -> None:
            if label:
                print(f"[MOCK] -> {label}: {chunk!r}")
            writer.write(chunk)
            self._trace.append(chunk)

        print("[MOCK] handle_client invoked")
        try:
            # 1-3. Offer options with WILL only
            for opt_label, opt_code in [
                ("WILL TTYPE", TELOPT_TTYPE),
                ("WILL EOR", TELOPT_EOR),
                ("WILL TN3270E", TELOPT_TN3270E),
            ]:
                _send(bytes([IAC, WILL, opt_code]), opt_label)
                await writer.drain()
                await asyncio.sleep(0.02)

            # 4. Request terminal types (TTYPE SEND)
            _send(bytes([IAC, SB, TELOPT_TTYPE, TTYPE_SEND, IAC, SE]), "TTYPE SEND")
            await writer.drain()

            # Try to read at least one terminal type response (non-fatal if absent)
            try:
                term_resp = await asyncio.wait_for(
                    reader.readuntil(bytes([IAC, SE])), timeout=1.5
                )
                self._received.append(term_resp)
                print(f"[MOCK] <- TTYPE RESP: {term_resp!r}")
            except Exception:
                print("[MOCK] (no TTYPE response within 1.5s)")

            # 5. Device-type negotiation
            # Per RFC 2355 the server either SENDs (client chooses) or REQUESTs a specific type.
            # Sending both REQUEST and SEND back-to-back previously caused client confusion and
            # early shutdown (BrokenPipe). We now send only one primary directive and then wait
            # for the client "IS" response.
            # If a requested device type is set, exercise the REQUEST flow: ask the client to
            # change to that device type via DEVICE-TYPE REQUEST. Otherwise, use DEVICE-TYPE SEND.
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
                # Always initiate with DEVICE-TYPE SEND to solicit supported types
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
                # Read the client response (DEVICE-TYPE IS ...) if provided.
                devtype_resp = await asyncio.wait_for(
                    reader.readuntil(bytes([IAC, SE])), timeout=1.5
                )
                self._received.append(devtype_resp)
                print(f"[MOCK] <- DEVICE-TYPE RESP: {devtype_resp!r}")
                # Send DEVICE-TYPE IS selecting one model (requested or default)
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

            # 6. Provide TN3270E FUNCTIONS REQUEST IS or SEND with bitmap directly (simplified)
            # RFC 2355 allows REQUEST followed by IS to advertise supported functions.
            # We list a small set: DATA_STREAM_CTL(0x01), NEW_APPL(0x02), RESPONSES(0x03)
            functions_bytes = bytes([0x01, 0x02, 0x03])
            if self.functions_mode == "request":
                # 6a. Request supported functions; client may reply with IS.
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
                # 6b. SEND supported functions (server advertises functions); client may reply with IS
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
                # For test determinism, immediately follow with a FUNCTIONS IS so clients
                # that don't reply to SEND still receive an IS payload (exercise IS path).
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

            # 7. Send a minimal TN3270E 3270-DATA record followed by IAC EOR.
            # Create a small, valid 3270 data stream that uses WCC + SBA + SF + text bytes.
            from pure3270.protocol.data_stream import SBA, SF
            from pure3270.protocol.tn3270e_header import TN3270EHeader
            from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic

            header = TN3270EHeader(
                data_type=TN3270_DATA,
                request_flag=0,
                response_flag=0,
                seq_number=1,
            ).to_bytes()
            # Basic 3270 orders: WCC(0x00), SBA (Set Buffer Address) to address 0,
            # Start Field (SF) with a simple attribute byte, then EBCDIC text.
            # Extend payload to include a second SBA+SF+text to create two visible fields
            wcc = bytes([0x00])
            # First field: address 0
            sba_addr_1 = bytes([0x00, 0x00])
            sf_attr_1 = bytes([0xF0])
            text1 = translate_ascii_to_ebcdic("HELLO")
            # Second field: row 1, column 0 (address = 80 for 80 cols -> 0x50)
            # For 12-bit addressing, encode as two bytes: high 6 bits, low 6 bits
            # high = 0x01, low = 0x10 -> bytes([0x01, 0x10]) yields address 0x50
            sba_addr_2 = bytes([0x01, 0x10])
            sf_attr_2 = bytes([0xF0])
            text2 = translate_ascii_to_ebcdic("WORLD")
            payload = b"".join(
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
            _send(header + payload, "TN3270E 3270-DATA")
            _send(bytes([IAC, TELOPT_EOR]), "IAC EOR")
            await writer.drain()
            # Allow client to finish any pending negotiation responses before closing.
            await asyncio.sleep(0.2)
        except GeneratorExit:
            # Loop shutting down while awaiting read; suppress noisy RuntimeError
            print("[MOCK] GeneratorExit during handle_client (loop closing)")
        except Exception as e:  # pragma: no cover - debug visibility
            print(f"[MOCK] Exception in handle_client: {e}")
        finally:
            try:
                transport = getattr(writer, "transport", None)
                if transport and not transport.is_closing():
                    writer.close()
            except RuntimeError:
                # Event loop already closed
                pass

    def get_sent_trace(self) -> list[bytes]:
        """Return list of bytes chunks sent by server."""
        return list(self._trace)

    def get_received_trace(self) -> list[bytes]:
        """Return list of bytes chunks received from client during negotiation."""
        return list(self._received)


# Example scenario: negotiation failure (IAC WONT EOR)
async def negotiation_failure_scenario(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    writer.write(b"\xff\xfc\x19")  # IAC WONT EOR
    await writer.drain()
    await asyncio.sleep(0.1)
    writer.close()


# To run with a custom scenario, pass scenario=negotiation_failure_scenario

if __name__ == "__main__":
    # Example: python mock_server/tn3270_mock_server.py
    # For custom scenario: server = TN3270MockServer(scenario=negotiation_failure_scenario)
    server = TN3270MockServer()
    asyncio.run(server.start())
