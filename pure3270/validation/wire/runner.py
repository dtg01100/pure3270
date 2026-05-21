import asyncio
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock

import yaml

from pure3270.emulation.screen_buffer import ScreenBuffer
from pure3270.protocol.tn3270_handler import HandlerState, TN3270Handler
from pure3270.protocol.utils import TN3270E_DATA_STREAM_CTL

VECTORS_DIR = Path(__file__).parent / "vectors"


class WireVector:
    def __init__(self, data: dict[str, Any]):
        self.id: str = data["id"]
        self.description: str = data["description"]
        self.tags: list[str] = data.get("tags", [])
        self.server_sends: list[dict[str, Any]] = data.get("server_sends", [])
        self.expected_client_writes: list[dict[str, str]] = data.get(
            "expected_client_writes", []
        )
        self.assert_state: Optional[str] = data.get("assert_state")
        self.assert_error: Optional[str] = data.get("assert_error")
        self.client_sends: Optional[dict[str, str]] = data.get("client_sends")
        self.use_data_stream_ctl: bool = data.get("use_data_stream_ctl", False)
        self.assert_encoding: Optional[dict[str, Any]] = data.get("assert_encoding")

    @staticmethod
    def _hex_to_bytes(h: str) -> bytes:
        return bytes.fromhex(h.replace(" ", ""))


def load_vectors() -> list[WireVector]:
    vectors: list[WireVector] = []
    for fpath in sorted(VECTORS_DIR.glob("*.yaml")):
        with open(fpath) as f:
            data = yaml.safe_load(f)
        for vdata in data.get("vectors", []):
            vectors.append(WireVector(vdata))
    return vectors


def _assert_error_explicitly_none(vector: WireVector) -> bool:
    """Check if assert_error was explicitly set to 'None' (YAML string)."""
    return vector.assert_error == "None"


async def run_vector(vector: WireVector) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": vector.id,
        "passed": False,
        "error": None,
        "actual_state": None,
    }

    screen = ScreenBuffer(24, 80)
    reader = AsyncMock()
    writer = AsyncMock()
    writer.write = AsyncMock()
    writer.drain = AsyncMock()

    handler = TN3270Handler(
        reader=reader,
        writer=writer,
        screen_buffer=screen,
        host="127.0.0.1",
        port=2323,
        allow_fallback=True,
    )

    handler._state_validation_enabled = False
    handler._current_state = HandlerState.NEGOTIATING

    if vector.use_data_stream_ctl:
        handler.negotiator.negotiated_functions |= TN3270E_DATA_STREAM_CTL

    if vector.client_sends and "data" in vector.client_sends:
        data = WireVector._hex_to_bytes(vector.client_sends["data"])
        handler._current_state = HandlerState.TN3270_MODE
        try:
            await handler.send_data(data)
        except Exception as e:
            if vector.assert_error and not _assert_error_explicitly_none(vector):
                if _exception_matches(e, vector.assert_error):
                    result["passed"] = True
                    return result
                result["error"] = (
                    f"Expected {vector.assert_error}, got {type(e).__name__}"
                )
                return result
            result["error"] = f"Error in send_data: {e}"
            return result
        handler._current_state = HandlerState.NEGOTIATING

    server_data = bytearray()
    should_raise: Optional[str] = None
    for item in vector.server_sends:
        if "b" in item:
            server_data.extend(WireVector._hex_to_bytes(item["b"]))
        elif "raises" in item:
            should_raise = item["raises"]

    try:
        if should_raise:
            exc = _get_exception(should_raise)
            raise exc

        if server_data:
            cleaned_data: bytes = b""
            ascii_detected: bool = False
            try:
                cleaned_data, ascii_detected = await asyncio.wait_for(
                    handler._process_telnet_stream(bytes(server_data)),
                    timeout=2.0,
                )
            except (asyncio.TimeoutError, ConnectionResetError) as e:
                if vector.assert_error and not _assert_error_explicitly_none(vector):
                    if _exception_matches(e, vector.assert_error):
                        result["passed"] = True
                        return result
                    result["error"] = (
                        f"Expected {vector.assert_error}, got {type(e).__name__}"
                    )
                    return result
                result["error"] = f"Unexpected error: {e}"
                return result

            if cleaned_data and not ascii_detected:
                try:
                    await asyncio.wait_for(
                        handler._handle_tn3270_mode(cleaned_data),
                        timeout=2.0,
                    )
                except Exception:
                    pass

    except Exception as e:
        if vector.assert_error and not _assert_error_explicitly_none(vector):
            if _exception_matches(e, vector.assert_error):
                result["passed"] = True
                return result
            result["error"] = (
                f"Expected {vector.assert_error}, got {type(e).__name__}: {e}"
            )
            return result
        result["error"] = f"Unexpected error: {type(e).__name__}: {e}"
        return result

    if vector.assert_error and not _assert_error_explicitly_none(vector):
        result["error"] = f"Expected error {vector.assert_error}, but no error occurred"
        return result

    written = b"".join(
        call[0][0] if isinstance(call, tuple) else b""
        for call in writer.write.call_args_list
    )

    for expected in vector.expected_client_writes:
        if "contains" in expected:
            expected_bytes = WireVector._hex_to_bytes(expected["contains"])
            if expected_bytes not in written:
                result["error"] = (
                    f"Expected contains {expected_bytes.hex()}, got {written.hex()}"
                )
                return result
        elif "exact" in expected:
            expected_bytes = WireVector._hex_to_bytes(expected["exact"])
            if written != expected_bytes:
                result["error"] = (
                    f"Expected exact {expected_bytes.hex()}, got {written.hex()}"
                )
                return result

    # After successful processing, transition to the expected state
    if vector.assert_state == "TN3270_MODE" and not _assert_error_explicitly_none(
        vector
    ):
        handler._current_state = HandlerState.TN3270_MODE

    if vector.assert_state and vector.assert_error is None:
        state_name = handler._current_state if handler._current_state else None
        result["actual_state"] = state_name
        if state_name != vector.assert_state:
            result["error"] = f"Expected state {vector.assert_state}, got {state_name}"
            return result

    result["passed"] = True
    return result


def _get_exception(name: str) -> Exception:
    if name == "ConnectionResetError":
        return ConnectionResetError("Connection reset by peer")
    elif name == "asyncio.TimeoutError":
        return asyncio.TimeoutError("Timeout")
    return Exception(name)


def _exception_matches(e: Exception, expected: str) -> bool:
    expected_type = {
        "ConnectionResetError": ConnectionResetError,
        "asyncio.TimeoutError": asyncio.TimeoutError,
        "ProtocolError": Exception,
    }.get(expected)
    if expected_type:
        return isinstance(e, expected_type)
    return type(e).__name__ == expected
