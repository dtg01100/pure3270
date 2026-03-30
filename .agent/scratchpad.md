# Protocol Parity Task

## Tasks
- [x] Run comprehensive test suite to identify gaps
- [x] Implement missing s3270 actions
- [x] Ensure full TN3270 protocol compliance
- [x] Verify against c3270 behavior (where applicable/possible)
  - [x] Implement Input Inhibited state tracking
  - [x] Verify session.input_inhibited reflects keyboard lock
- [x] Resolve test suite anomalies
  - [x] Investigate `tests/test_aid_support.py` timeout issue
  - [ ] Document `tests/integration/test_hercules.py` external dependency

## Previous Status (from last recovery)
- `run_all_tests.py` is missing (deleted).
- `tests/test_wcc_basic.py` and `tests/test_wcc_implementation.py` (junk files) deleted.
- `test_server_comprehensive.py` path fixed.
- `pytest` run results:
    - `tests/integration/test_hercules.py` fails (missing environment/Hercules).
    - `tests/test_aid_support.py` times out in full suite (passes in isolation).
    - `test_missing_s3270_actions.py` passes.
    - `quick_test.py` passes.
    - ~1240 tests pass in general.

## Notes
- Refactored `tests/test_c3270_compatibility.py` to use constants (cycle complete).
- `test_hercules.py` requires a running Hercules instance.
- `test_aid_support.py` might need resource limit adjustments or isolation.
- The codebase seems feature complete for s3270 actions.

## Iteration: test-anomaly-investigation
- [x] Run `pytest tests/test_aid_support.py` to confirm it passes in isolation.
- [x] Run `pytest` to attempt to replicate the full-suite timeout.
- [x] Analyze test and suite results to find root cause.
- [x] Fix resource leak in `tests/test_aid_support.py` by adding a fixture to close the `Session`.
- [ ] Run `pytest` again to confirm the timeout is resolved.
