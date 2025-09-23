# Progress Log

## Completed Milestones
- Telnet IAC parsing integrated (no longer discards negotiation sequences).
- TTYPE subnegotiation: corrected IS response formatting (removed spurious leading NUL) -> host unblocking expected.
- ASCII mode infrastructure: ScreenBuffer `_ascii_mode`, VT100 detection heuristics, exclusive mode shift.
- Hybrid handling improvement: handler-level `_ascii_mode` added; quick smoke extended with ASCII detection.

## In Flight / Pending
- Screen parity snapshot system (not started).
- API parity audit for `P3270Client` (not started).
- Licensing & attribution docs + scaffolding (not started).
- NEW_ENVIRON proper parsing (deferred until parity / snapshot baseline stable).

## Open Issues / Technical Debt
- Misuse of NEW_ENVIRON currently hacked with NAWS-like reply (documented).
- Lack of configurable terminal model selection (hardcoded `IBM-3278-2`).
- No automated regression test capturing real host negotiation trace (would require recorded pcap or byte log fixture).

## Recent Validation
- `quick_test.py` passes all sections including new ASCII detection.
- Local compile check passes (`py_compile`).

## Short-Term Priorities
1. Implement portable snapshot format for ASCII screens.
2. Provide API completeness test to prevent accidental method regression.
3. Add licensing attribution before integrating any externally inspired parsing logic.
