"""Scenario DSL for end-to-end acceptance testing."""

from dataclasses import dataclass, field
from typing import Any


class StepKind:
    """Step types for scenario definitions."""

    @dataclass
    class StartServer:
        handler: str = "enhanced"
        auto_port: bool = True

    @dataclass
    class Connect:
        host: str = "127.0.0.1"
        port: Any = "$server_port"

    @dataclass
    class SendKey:
        key: str = "ENTER"

    @dataclass
    class SendData:
        data: bytes = b""

    @dataclass
    class ReceiveData:
        timeout: float = 5.0

    @dataclass
    class AssertState:
        state: str = "TN3270_MODE"

    @dataclass
    class AssertScreenContains:
        text: str = ""

    @dataclass
    class AssertScreenUpdated:
        pass

    @dataclass
    class Wait:
        seconds: float = 0.5

    @dataclass
    class Disconnect:
        pass


@dataclass
class Scenario:
    name: str
    steps: list[Any]
    timeout: float = 10.0
    description: str = ""
    tags: list[str] = field(default_factory=list)


def create_default_scenarios() -> list[Scenario]:
    S = StepKind
    return [
        Scenario(
            name="basic_connect_disconnect",
            description="Connect to mock server, verify TN3270E mode, disconnect",
            tags=["smoke", "connect"],
            steps=[
                S.StartServer(handler="enhanced", auto_port=True),
                S.Connect(host="127.0.0.1", port="$server_port"),
                S.AssertState("TN3270_MODE"),
                S.Disconnect(),
                S.AssertState("DISCONNECTED"),
            ],
            timeout=10.0,
        ),
        Scenario(
            name="send_enter_receive",
            description="Connect, send ENTER, read response, verify screen updated",
            tags=["smoke", "keyboard", "receive"],
            steps=[
                S.StartServer(handler="enhanced", auto_port=True),
                S.Connect(host="127.0.0.1", port="$server_port"),
                S.AssertState("TN3270_MODE"),
                S.SendKey("ENTER"),
                S.ReceiveData(timeout=0.5),
                S.AssertScreenUpdated(),
                S.Disconnect(),
            ],
            timeout=10.0,
        ),
        Scenario(
            name="ascii_fallback",
            description="Connect to server that rejects TN3270E, verify basic TN3270 mode fallback",
            tags=["fallback", "basic", "connect"],
            steps=[
                S.StartServer(handler="basic", auto_port=True),
                S.Connect(host="127.0.0.1", port="$server_port"),
                S.AssertState("TN3270_MODE"),
                S.Disconnect(),
            ],
            timeout=10.0,
        ),
        Scenario(
            name="reconnect",
            description="Connect, disconnect, reconnect to verify session reuse",
            tags=["connect", "reconnect"],
            steps=[
                S.StartServer(handler="enhanced", auto_port=True),
                S.Connect(host="127.0.0.1", port="$server_port"),
                S.AssertState("TN3270_MODE"),
                S.Disconnect(),
                S.AssertState("DISCONNECTED"),
                S.Connect(host="127.0.0.1", port="$server_port"),
                S.AssertState("TN3270_MODE"),
                S.Disconnect(),
            ],
            timeout=20.0,
        ),
        Scenario(
            name="pf_keys",
            description="Connect, send PF1-PF3 keys, verify each response",
            tags=["keyboard", "pfkeys"],
            steps=[
                S.StartServer(handler="enhanced", auto_port=True),
                S.Connect(host="127.0.0.1", port="$server_port"),
                S.AssertState("TN3270_MODE"),
                S.SendKey("PF1"),
                S.ReceiveData(timeout=0.5),
                S.SendKey("PF2"),
                S.ReceiveData(timeout=0.5),
                S.SendKey("PF3"),
                S.ReceiveData(timeout=0.5),
                S.Disconnect(),
            ],
            timeout=15.0,
        ),
        Scenario(
            name="timeout_recovery",
            description="Connect with very short timeout, verify timeout handling",
            tags=["timeout", "error"],
            steps=[
                S.StartServer(handler="basic", auto_port=True),
                S.Connect(host="127.0.0.1", port="$server_port"),
                S.ReceiveData(timeout=0.1),
                S.Disconnect(),
            ],
            timeout=10.0,
        ),
        Scenario(
            name="printer_session",
            description="Connect as printer session, send SCS data",
            tags=["printer", "scs"],
            steps=[
                S.StartServer(handler="enhanced", auto_port=True),
                S.Connect(host="127.0.0.1", port="$server_port"),
                S.AssertState("TN3270_MODE"),
                S.SendData(b"\x04\xf1\xf2\xf3\xf4"),
                S.Disconnect(),
            ],
            timeout=10.0,
        ),
    ]
