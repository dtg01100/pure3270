## TODO List

- [x] Add diagnostic dumping of negotiation bytes and replay events to tools/compare_replay_with_s3270.py and tools/trace_replay_server.py
- [x] Create a byte-level comparator script (tools/negotiation_diff.py) to diff IAC sequences and highlight differences
- [x] Add unit tests for negotiation sequence parity and for EBCDIC decode parity for representative traces
- [x] Align negotiator payload formatting & ordering with s3270 (based on diffs) and add regression tests
- [x] Fix to_text EBCDIC codec behavior and field attribute masking to match s3270 Ascii(), then update tests
- [ ] Integrate new regression traces into the CI and add a nightly comparison job for s3270 parity
