# Tech Context

## Languages & Versions
- Python 3.11+ targeted (code references 3.10 minimum in README; internal guidance mentions 3.11+).

## Dependencies
- Runtime: Standard library only.
- Dev/Test (optional): pytest, pytest-asyncio, black, flake8, coverage. Not always installable in restricted environment; quick smoke script used as fallback.

## Key Modules
- `pure3270/protocol/negotiator.py`: Telnet + TN3270E option handling, subnegotiations, ASCII mode flag bridging.
- `pure3270/protocol/tn3270_handler.py`: Stream processing, IAC parsing, VT100 detection, dispatch.
- `pure3270/emulation/screen_buffer.py`: Unified buffer for EBCDIC or ASCII. Fields & attributes for 3270 mode.
- `pure3270/p3270_client.py`: Native p3270-compatible facade.

## Testing Strategy
- `quick_test.py`: Always runnable, covers imports, native client, navigation methods, mock connectivity, ASCII detection.
- Pytest suite (optional) includes fuzz, negotiation, emulation, protocol, VT100 offline tests.

## Negotiation Edge Cases
- Host sends repeated TTYPE SEND until client replies with IS (fixed to send `IBM-3278-2`).
- NEW_ENVIRON misuse treated as NAWS surrogate to unblock host data.

## Limitations
- No full NEW-ENVIRON var parsing yet.
- Terminal type not configurable via public API.
- No persistent snapshot of actual host login screen yet.
