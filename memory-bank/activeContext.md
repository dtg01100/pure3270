# Active Context (as of 2025-09-23)

## Recently Completed
- Implemented TTYPE SEND -> IS reply (removed malformed extra NUL) enabling host to proceed after terminal type negotiation.
- Added hybrid VT100/TN3270 handling improvements: exclusive ASCII activation, handler-level flag, quick smoke ASCII detection.

## Recently Completed (October 2025)
- **✅ Attribution & Porting Infrastructure**: All tasks completed (TASK004, TASK005, TASK006)
  - THIRD_PARTY_NOTICES.md created with x3270 BSD-3-Clause license
  - PORTING_GUIDELINES.md enhanced with RFC-first development philosophy
  - Attribution scaffolding system validated (27/27 tests passing)
- **✅ P3270Client API Compatibility**: Full parity achieved (TASK003)

## Current Focus
Ready to proceed with:
1. Screen parity regression scaffolding (capture deterministic snapshot representation for ASCII/NVT screens).
2. NEW_ENVIRON proper parsing (deferred until snapshot baseline stable).

## Key Decisions
- Temporary compatibility: treat DO NEW_ENVIRON (0x27) as NAWS-like sizing; must be replaced with real NEW-ENVIRON parser for standards compliance.
- Default terminal type: `IBM-3278-2` (baseline). Will consider making configurable once parity validated.
- ASCII mode once enabled is irreversible per handler lifecycle (simplifies parsing logic, avoids mixed-mode complexity for now).

## Known Gaps / Risks
- Lack of snapshot tests: no guard yet against regressions in VT100 rendering.
- No structured NEW_ENVIRON support; potential breakage if host expects var/value negotiation semantics.
- Absence of license attribution file could delay acceptance of future ported snippets.

## Next Planned Steps
1. Implement minimal snapshot representation + test harness to compare expected ASCII screen content (generate canonical normalization: strip trailing spaces per line, unify line endings).
2. Expand quick smoke to optionally load a stored snapshot and verify rendering function output (conditional to keep runtime minimal).
3. NEW_ENVIRON proper parsing (when snapshot baseline is stable).

## Metrics / Validation Hooks
- `quick_test.py` now includes ASCII detection PASS criteria.
- Future: add `python tools/validate_screen_snapshot.py` to assert snapshot fidelity.
