## TODO List

- [x] Add diagnostic dumping of negotiation bytes and replay events to tools/compare_replay_with_s3270.py and tools/trace_replay_server.py
- [x] Create a byte-level comparator script (tools/negotiation_diff.py) to diff IAC sequences and highlight differences
- [x] Add unit tests for negotiation sequence parity and for EBCDIC decode parity for representative traces
- [x] Align negotiator payload formatting & ordering with s3270 (based on diffs) and add regression tests
- [x] Fix to_text EBCDIC codec behavior and field attribute masking to match s3270 Ascii(), then update tests
- [x] Integrate new regression traces into the CI and add a nightly comparison job for s3270 parity
  - Added `tools/run_regression_traces.py` (replays every trace, validates against `*_expected.json`)
  - Added `tests/test_regression_traces.py` (parametrized pytest wrapper, 65 traces; known drifts marked `@pytest.mark.xfail(strict=True)`)
  - Added `tools/run_s3270_parity.py` and `tools/diff_parity_reports.py` for the nightly s3270 comparison
  - Added `tools/render_regression_summary.py` for `$GITHUB_STEP_SUMMARY` output
  - Updated `.github/workflows/trace_replay_tests.yml` to run the full parametrized suite on every PR
  - Added `.github/workflows/nightly-s3270-parity.yml` (cron `0 2 * * *`, builds s3270, runs parity, diffs against last successful run, opens issue on new regression)
