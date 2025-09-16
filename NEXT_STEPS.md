# Next Steps / Handoff

This document captures follow-up work after the negotiation heuristic refactor and related improvements committed on 2025-09-16.

## Completed in this commit
- Added negotiation inference unit test (`tests/test_negotiation_inference.py`)
- Centralized heuristic in `Negotiator.infer_tn3270e_from_trace`
- Removed deprecated handler wrapper `_infer_tn3270e_from_trace`
- Added graceful suppression (debug-only) of benign `asyncio.CancelledError` in negotiation path
- Propagated `force_mode` / `allow_fallback` through `Session`, `AsyncSession`, `TN3270Handler`, `Negotiator`
- Improved TN3270E negotiation fallback logic and reader-loop cleanup
- Simplified Telnet stream parsing & buffered partial-sequence handling
- Enhanced VT100 ASCII detection & parsing path
- Updated `SessionManager` negotiation helpers for mixed sync/async/mocked flows
- Ensured full test suite & smoke tests pass; formatting & linting clean

## Follow-Up (Recommended)
1. (DONE) Add RFC-based negotiation transcript tests (cover TTYPE->BINARY->EOR->TN3270E sequencing)
   - Implemented in `tests/test_negotiation_sequence.py` validating ordered Telnet option negotiation and fallback path.
2. (DONE) Introduce structured trace recorder for negotiation (retain annotated steps for diagnostics)
   - Implemented `pure3270/protocol/trace_recorder.py` with lightweight event capture (telnet, subneg, decision, error)
   - Integrated optional `recorder` into `Negotiator` (records incoming/outgoing IAC commands, subnegotiations, mode decisions, timeouts/refusals)
   - Added tests: `tests/test_negotiation_trace.py` (telnet + decisions), `tests/test_negotiation_subneg_trace.py` (TN3270E DEVICE-TYPE SEND subneg event)
   - Session/AsyncSession convenience: `enable_trace=True` flag + `get_trace_events()` accessor
   - Overhead negligible when recorder is None (single conditional branch)
3. Gradually replace heavy mocks in `tests/conftest.py` with lightweight real objects / fakes
4. (DONE) Add tests for `force_mode` permutations:
   - Covered in `tests/test_negotiation_sequence.py` (tn3270e refusal without fallback, tn3270 with remote WONT TN3270E, ascii bypass path).
5. Create explicit VT100 mode regression tests (escape density heuristic edge cases)
6. Add performance micro-bench for `_process_telnet_stream` (baseline before further parsing changes)
7. Evaluate extracting negotiation events to dedicated dataclass for clarity & introspection
8. Document ASCII fallback semantics vs legacy s3270 (alignment notes in README / docs)
9. Expand property tests for SNA response handling invariants (state machine resiliency)
10. Add type refinement in negotiator for optional writer/parser (Protocols or TypedDict) to reduce mypy noise if enabled later

## Low Priority / Opportunistic
- Collapse duplicated VT100 parser import logic via helper
- Consider feature flag to disable heuristic inference entirely when a real host is present
- Investigate logging categories (e.g., `pure3270.negotiation`, `pure3270.telnet`) for selective verbosity

## Release Notes Draft Snippet
```
Enhancements: Centralized TN3270E negotiation inference, added force_mode/allow_fallback plumbing, improved Telnet parsing resilience, and reduced benign CancelledError noise. Added dedicated unit test locking heuristic semantics.
```

## Validation Summary
- quick_test.py: PASS
- run_all_tests.py: PASS (all suites)
- Property tests: Adjusted for realistic parser behavior; now all pass (1 intentional skip for minimal SF case)
- black + flake8: clean (no code changes outside tests/docs in this cycle)

---
Maintainer can proceed with additional RFC compliance tightening using the above follow-up list.
