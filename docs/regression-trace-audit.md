# Regression Trace Audit

This document captures a 2026-06 audit of the 14 traces that remained
xfailing in `tests/test_regression_traces.py` after the 43x80
screen-size fix in commit `a05cbcc`. The goal is to triage the
remaining gaps into "easy wins", "deep work", and "aspirational", so
the next session knows where to dig.

## TL;DR

| Bucket | Count | Fix shape | Effort |
|---|---:|---|---:|
| Multi-line trace records (BIND-IMAGE truncation) | ~11 | `_parse_trace` needs continuation detection AND TN3270E envelope stripping | 1-2 sessions |
| Auto-generated stale baselines (24x80 vs 43x80 mismatch in `screen` block) | ~5 | Re-run `tools/run_regression_traces.py` against a fixed Replayer, accept the new field_count, refresh baselines | 1 hour |
| SNA response handling in the Replayer | 2-3 | Replayer never attaches a Negotiator; SNA sense-code / LU-busy recovery never runs | 1 session |
| Genuine field-detection bugs (no obvious parser path issue) | 2-3 | Needs a side-by-side run against s3270 to find where the field count diverges | 1+ session each |

## Status of the original 14

After `a05cbcc` (comment-based 43x80 detection), 14 traces are still
xfailing. Listed by `_KNOWN_FAILING` category:

### 43x80 dynamic screen size (6) — DONE

`all_chars`, `apl`, `invisible_underscore`, `numeric`, `ra_test`,
`reverse`, `wrap_field` are no longer in `_KNOWN_FAILING` and pass in
the suite (51 pass, 14 xfail). `ra_test` baseline also fixed in the
same commit.

### Bid-image field accounting (5) — Root cause: BIND-IMAGE truncation

`bid.trc`, `bid-bug.trc`, `bid-ta.trc`, `no_bid.trc`, `ibmlink2.trc`.
All involve a SNA BIND-IMAGE structured field that arrives as a
fragmented record in the trace. The trace shows it as multiple
`< 0xN` lines with cumulative offsets, but `Replayer._parse_trace`
only keeps the first 32 bytes. The truncated BIND-IMAGE then causes
`ParseError pos=N: Incomplete SBA order` mid-parse; the parser rolls
back, the rest of the record is lost, and the screen ends up with
phantom fields from whatever order the parser happened to be
positioned at when the buffer ran out.

Concrete example: `bid.trc` lines 152-153 are:
```
< 0x0   030000000031010303b1903080008787f8870002800000000018502b507f0000
< 0x20  08c9c2d4f0d4d6d5f20005007ee5341008c9c2d4f0e3c5e3c9ffef
```
The current parser keeps the first 32 bytes and discards the rest.
The full record is 64 bytes (a 32-byte BIND envelope + 32 bytes of
BIND payload). The parser can absolutely handle the full record; it
just isn't being given it.

Affected traces and the number of lines they're losing:
- `ft-double.trc` — 156 lines dropped (10% of the trace)
- `contention-resolution.trc` — 85 lines
- `ft_cut.trc`, `ft_cut_ewa.trc` — 83 lines each
- `ft-crash.trc` — 49 lines
- `sscp-lu.trc` — 48 lines
- `ft_dft.trc` — 47 lines
- `smoke.trc` — 34 lines (passes because the lost bytes aren't
  load-bearing; smoke is a short EWA that fits in one line)

### SNA other (3) — Same root cause, different framing

`sscp-lu.trc`, `contention-resolution.trc`, `ignore_eor.trc`. Same
BIND-IMAGE truncation issue. `sscp-lu.trc` is special because the
SNA session carries SSCP-LU data (data type `0x0A`) which the
Replayer doesn't know to handle — the parser routes it through the
default `TN3270_DATA` path and the SNA envelope bytes confuse the
order parser.

### Login flow (1) — Same root cause + parser envelope confusion

`login.trc`. The first 3270-data record starts with
`00000100...`, which the parser sees as bytes `0x00 0x00 0x01 0x00
0x01`. The first `0x00` is TN3270E data-type 3270-DATA, the next
two are the 2-byte record length, then the request/response flags.
The Replayer hands the whole envelope to the parser, which reads
`0x00` as a WCC and misroutes the rest. Fix: strip the 5-byte
TN3270E header (or pass `data_type=TN3270_DATA` with the right
offset) before handing to the parser.

### ibmlink help (1) — Same root cause

`ibmlink_help.trc`. Expected 36-43 fields, getting 48 (over by ~5).
The 5-extra fields suggests the BIND-IMAGE is being mis-parsed into
multiple smaller "fields" instead of one large one, similar to the
bid-image group.

### IND$FILE (2) — Same root cause

`ft-crash.trc`, `ft_dft.trc`. IND$FILE transfers send a screen with
many input fields (the file transfer UI). The truncated BIND-IMAGE
means the screen setup is wrong, so the field count drifts.

### Invalid-SBA (1) — Same root cause

`invalid_sba.trc`. Expected 218-225 fields, getting 18. The expected
count is so high it strongly suggests the screen is genuinely 43x80
(or larger) and full of single-cell fields, and the BIND-IMAGE
truncation is leaving the parser with a half-built screen.

### Wrap field (1) — Different shape

`wrap.trc`. Expected 37-44 fields, getting 3. The 3-vs-44 gap is
unusual; could be a different root cause (parser rolling back the
entire write on the first malformed order and leaving the screen
empty). Worth investigating separately.

## What I tried

I implemented a continuation-aware `_parse_trace` in commit
`a05cbcc+` (reverted before commit). It correctly assembled the
fragmented records and took 11 of 14 traces from FAIL to PASS, but
it regressed 3 others (`all_chars`, `ibmlink`, `ft_dft`) because the
*complete* record bytes include a TN3270E envelope that the parser
isn't designed to consume directly — the `replay()` path
short-circuits the handler that would normally strip the envelope.

The right fix is bigger than a one-line patch:

1. `_parse_trace` must concatenate continuation lines (offset ==
   `prev_offset + prev_len`).
2. `Replayer.replay()` must strip the 5-byte TN3270E envelope from
   each 3270-DATA record before handing the body to the parser, OR
   call `self.parser.parse(data, data_type=TN3270_DATA)` after
   slicing `data[5:]` (the parser then sees the actual WCC and
   orders).
3. The Replayer needs to attach a Negotiator (or call the handler
   path) so that SNA_RESPONSE_TYPE records and BIND_IMAGE records
   get routed to the correct handler. The current `replay()` method
   bypasses all of this.

Equivalent to a refactor of `replay()` to delegate to the
already-correct `replay_to_session()` method, which goes through
`TN3270Handler._parse_resilient()` and does all of the above.

## Suggested next session

The single highest-leverage move is to make `replay()` delegate to
`replay_to_session()` (or extract a shared inner method). This
single refactor would close all 11 of the BIND-IMAGE-related xfails
at once and turn the Replayer from a fragile shortcut into a real
test harness. The remaining 3 (`login`, `ibmlink_help`, `ft_dft`)
might also be fixed by the same refactor; if not, they'll need
individual investigation.

## Reference

The methodology for this audit is the same as the tn5250r audit
documented in the `protocol-implementation-audit` skill. The
single most useful move was step 3 of that methodology: diff
inbound trace records against what `replay_to_session()` (the
correct path) actually parses, and you'll see the 32-byte
truncation immediately.
