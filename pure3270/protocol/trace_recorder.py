import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

__all__ = [
    "BaseEvent",
    "TelnetOptionEvent",
    "SubnegotiationEvent",
    "ModeDecisionEvent",
    "ErrorEvent",
    "TraceRecorder",
]


@dataclass
class BaseEvent:
    ts: float
    kind: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:  # minimal helper
        return {"ts": self.ts, "kind": self.kind, **self.details}


@dataclass
class TelnetOptionEvent(BaseEvent):
    pass


@dataclass
class SubnegotiationEvent(BaseEvent):
    pass


@dataclass
class ModeDecisionEvent(BaseEvent):
    pass


@dataclass
class ErrorEvent(BaseEvent):
    pass


class TraceRecorder:
    """Lightweight ordered recorder for negotiation-related events.

    Intended for diagnostics and tests. Low overhead when disabled (Negotiator simply
    skips recording if `recorder is None`). Timestamps are relative to recorder
    creation (monotonic start baseline subtracted).
    """

    def __init__(self) -> None:
        self._events: List[BaseEvent] = []
        self._start = time.monotonic()

    # Internal -----------------------------------------------------------------
    def _now(self) -> float:
        return time.monotonic() - self._start

    def record(self, kind: str, **details: Any) -> None:
        evt = BaseEvent(ts=self._now(), kind=kind, details=details)
        self._events.append(evt)

    # Public API ---------------------------------------------------------------
    def events(self) -> List[BaseEvent]:  # shallow copy for safety
        return list(self._events)

    def to_json(self, *, indent: Optional[int] = None) -> str:
        return json.dumps(
            [e.to_dict() for e in self._events], indent=indent, sort_keys=True
        )

    # Convenience wrappers for clarity ----------------------------------------
    def telnet(self, direction: str, command: str, option: int) -> None:
        self.record("telnet", direction=direction, command=command, option=option)

    def subneg(self, option: int, payload: bytes) -> None:
        preview = payload[:32]
        self.record("subneg", option=option, length=len(payload), preview=preview.hex())

    def decision(self, requested: str, chosen: str, fallback_used: bool) -> None:
        self.record(
            "decision", requested=requested, chosen=chosen, fallback_used=fallback_used
        )

    def error(self, message: str) -> None:
        self.record("error", message=message)
