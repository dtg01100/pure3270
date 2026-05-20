# Pure3270 Formal Validation Suite

## Purpose

Provide a comprehensive, CI-enforceable validation framework that verifies pure3270's networking code works correctly without requiring access to a real TN3270 server. The suite combines RFC compliance tracking, wire-level protocol verification, end-to-end acceptance scenarios, and fuzzing into a single `python -m pure3270.validation` command.

## Architecture

```
pure3270/validation/
├── __init__.py
├── __main__.py              # CLI entry point
├── report.py                # Serializable report data model
├── conftest.py              # Pytest fixtures for validation tests
├── matrix/                  # RFC compliance matrix
│   ├── __init__.py
│   ├── rfc854.yaml          # RFC 854 requirements
│   ├── rfc1091.yaml         # RFC 1091 requirements
│   ├── rfc1576.yaml         # RFC 1576 requirements
│   ├── rfc2355.yaml         # RFC 2355 requirements
│   ├── checker.py           # Loads YAML, cross-refs tests
│   └── reporter.py          # Generates report
├── wire/                    # Wire-level test vectors
│   ├── __init__.py
│   ├── vectors/             # YAML test vector files
│   │   ├── telnet_negotiation.yaml
│   │   ├── tn3270e.yaml
│   │   ├── data_stream.yaml
│   │   └── error_handling.yaml
│   ├── runner.py            # Vector execution engine
│   └── test_vectors.py      # Pytest wrapper
├── acceptance/              # End-to-end scenarios
│   ├── __init__.py
│   ├── scenarios.py         # Scenario DSL + StepKind
│   ├── runner.py            # Scenario executor
│   └── test_scenarios.py    # Pytest wrapper
└── fuzz/                    # Property-based + random testing
    ├── __init__.py
    ├── test_state_machine.py
    └── test_protocol.py
```

### Reused infrastructure (no duplication)

- `mock_server/tn3270_mock_server.py` → acceptance runner (EnhancedTN3270MockServer)
- `tests/mocks/network_handlers.py` → wire tests (MockAsyncReader, MockAsyncWriter)
- `tests/utils/test_helpers.py` → timeouts, assertions (all subsystems)
- `pure3270/validate_suite/` → absorbed into matrix/tests/ and deprecated via README
- `tests/property/` → fuzz subsystem extends this pattern

## Subsystems

### 1. RFC Compliance Matrix

Structured YAML files mapping each RFC section's requirements to test coverage.

**Data format:**

```yaml
rfc: 2355
title: TN3270 Enhancements
url: https://datatracker.ietf.org/doc/html/rfc2355
sections:
  - section: "3"
    title: TN3270E Message Header
    requirements:
      - id: "3.1"
        text: "TN3270E header must be exactly 5 bytes"
        rfc_keyword: MUST
        tests:
          - "pure3270.validation.test_rfc2355::TestHeaderFormat::test_header_is_5_bytes"
        status: tested
```

**Status values:** `tested` | `partial` | `missing` | `not_applicable`

**Checker** (`checker.py`):
- Loads all RFC YAML files → flatten to requirement list
- Verifies each `tests[]` entry points to an actual pytest test function (exists, callable)
- Reports: section-level counts, overall percentage, missing requirements list
- `--ci` mode: exit non-zero if any `tested` reference is stale or if coverage drops below configurable threshold

**Coverage includes:** RFC 854 (§3, §4, §5, §10, §17), RFC 1091, RFC 1576, RFC 2355 (§3, §7, §8, §9, §10, §11, §13).

### 2. Wire-Level Test Vectors

Structured byte-level protocol tests. Each vector specifies server input bytes, expected client output bytes, and expected state machine outcome.

**Format** (`vectors/telnet_negotiation.yaml`):

```yaml
vectors:
  - id: negotiate-tn3270e
    description: "Server sends IAC WILL TN3270E, client responds DO TN3270E then negotiates device-type"
    tags: [rfc2355, negotiation]
    server_sends:
      - b: "ffe8fffb28"                    # IAC DO TTYPE + IAC WILL TN3270E
      - after: client_responds
      - b: "fffa280102ff24fff0"            # SB TN3270E DEVICE-TYPE SEND SE
    expected_client_writes:
      - contains: "fffd18"                 # IAC DO TTYPE
      - contains: "fffd28"                 # IAC DO TN3270E
    assert_state: TN3270_MODE
```

**Runner** (`runner.py`):
- Creates real `TN3270Handler` with `MockAsyncReader` + `MockAsyncWriter`
- Feeds server bytes sequentially, awaiting `after: client_responds` points
- Asserts `expected_client_writes` against accummulated writer buffer
- Supports match modes: `exact`, `contains`, `pattern` (regex)
- Supports `assert_state` and `assert_screen_contains`

**Test vector inventory** (planned):
- `telnet_negotiation.yaml`: ~15 vectors (DO/DONT/WILL/WONT for BINARY, SGA, EOR, TTYPE, TN3270E; subnegotiation SEND/IS; IAC IAC escaping; NOP, AYT, IP, BRK)
- `tn3270e.yaml`: ~15 vectors (DEVICE-TYPE CONNECT/ASSOCIATE/REJECT; FUNCTIONS bits; 5-byte header encode/decode; sequence number wraparound; RESPONSE handling)
- `data_stream.yaml`: ~10 vectors (WCC, SBA, SF, RA, GE, Write, Erase/Write, Erase/Write Alternate)
- `error_handling.yaml`: ~10 vectors (connection reset during read, timeout, malformed IAC, truncated subnegotiation, out-of-order sequence numbers, invalid data types)

### 3. End-to-End Acceptance Scenarios

Scripted scenarios running a real `Session` against `EnhancedTN3270MockServer` (TCP, real handler, real screen buffer).

**Scenario DSL:**

```python
Scenario(
    name="basic_connect_send_receive_disconnect",
    steps=[
        S.StartServer(handler="enhanced", auto_port=True),
        S.Connect(host="127.0.0.1", port="$server_port"),
        S.AssertState("TN3270_MODE"),
        S.SendKey("ENTER"),
        S.AssertScreenUpdated(),
        S.Disconnect(),
        S.AssertState("DISCONNECTED"),
    ],
    timeout=10.0,
)
```

**Step kinds:**
| Step | Description |
|------|-------------|
| `StartServer` | Start EnhancedTN3270MockServer in background thread |
| `Connect` | Call session.connect(host, port) with timeout |
| `SendKey` | Send a key (ENTER, PF1-PF12, PA1-PA3, TAB, CLEAR) |
| `SendData` | Send raw bytes |
| `ReceiveData` | Call session.read(timeout), return data |
| `AssertState` | Assert handler state machine state |
| `AssertScreenContains` | Assert screen buffer has specific text |
| `AssertScreenUpdated` | Assert screen changed since last read |
| `Wait` | Sleep for N seconds |
| `CaptureBytes` | Tag this point for post-hoc byte analysis |
| `Disconnect` | Call session.close() |

**Pre-built scenarios:** basic_connect, session_send_receive, pf_keys, ascii_fallback, reconnect, timeout_recovery, printer_session, ssl_connect.

**Dual-target design:** Same scenarios work against mock server (`PURE3270_VALIDATION_TARGET=mock`) and real server (`PURE3270_VALIDATION_TARGET=real`, `PURE3270_TEST_HOST=...`). Real server mode skips `StartServer` and `AssertState` steps.

### 4. Fuzzing

Property-based tests using Hypothesis, verifying invariants under random inputs.

**State machine fuzzing** (`test_state_machine.py`):
- Generate random sequences of operations (connect, send, receive, close, send_break, interrupt, negotiate)
- Verify: no crashes, no hangs, always terminates in valid state
- Verify: invalid state transitions always raise `StateTransitionError`
- 200 random sequences per run

**Protocol fuzzing** (`test_protocol.py`):
- Generate random byte sequences (0-4096 bytes)
- Feed to `handler.receive_data(timeout=0.5)` via MockAsyncReader
- Verify: returns bytes or None (never crashes), never hangs, writer buffer is valid telnet (IAC properly escaped)
- 500 random sequences per run

**Invariants:**
1. No undocumented exceptions (only `SessionError`, `ConnectionError`, `ProtocolError`)
2. No hangs (all operations bounded by timeouts)
3. State machine always lands in a valid state
4. Screen buffer never contains partial/invalid state
5. Writer buffer always contains valid telnet sequences

### 5. CLI Entry Point

```
$ python -m pure3270.validation [OPTIONS]

Options:
  --rfc-matrix        Run RFC compliance matrix check
  --wire              Run wire-level protocol tests
  --acceptance        Run end-to-end acceptance scenarios
  --fuzz              Run fuzzing tests
  --all               Run everything (default)
  --report-json FILE  Write JSON report
  --ci                Strict mode: exit non-zero on any gap/failure
  --verbose           Detailed per-test output
  --skip-slow         Skip acceptance and fuzz (fast mode)
```

**Exit codes:** 0 = all passed; 1 = test failures; 2 = coverage gaps; 3 = both.

**CI integration:** `python -m pure3270.validation --ci --skip-slow` can run in CI on every commit. Full suite runs nightly or on demand.

## Implementation Plan

### Phase 1: Package skeleton + RFC matrix (Day 1)
- Create `pure3270/validation/` with `__init__.py`, `__main__.py`, `report.py`
- Write RFC YAML files for 854, 1091, 1576, 2355
- Implement checker.py + reporter.py
- Write `matrix/test_rfc2355.py` and `matrix/test_rfc854.py` (move from validate_suite)
- Deprecate `pure3270/validate_suite/`

### Phase 2: Wire-level vectors (Day 2)
- Write `wire/vectors/*.yaml` (50 vectors)
- Implement wire/runner.py
- Write wire/test_vectors.py (pytest adapter)
- Wire tests pass against real components

### Phase 3: Acceptance scenarios (Day 3)
- Write `acceptance/scenarios.py` (scenario DSL + StepKind)
- Write all 8 pre-built scenarios
- Implement acceptance/runner.py
- Acceptance scenarios pass against mock server

### Phase 4: Fuzzing + CLI polish (Day 4)
- Write `fuzz/test_state_machine.py`
- Write `fuzz/test_protocol.py`
- Wire up CLI with subcommand dispatch
- Test all entry points, verify report output

### Phase 5: CI integration + docs (Day 5)
- Add CI config (validate --ci --skip-slow)
- Document in CONTRIBUTING.md
- Update AGENTS.md with new commands
- Full suite passes cleanly

## Constraints

- **No new dependencies**: Uses existing Hypothesis (already in test deps), PyYAML (already in deps), and stdlib only
- **No network access in CI**: Acceptance scenarios use in-process mock server only
- **Reuse, don't duplicate**: Every component above reuses existing infrastructure
- **CI-fast by default**: `--skip-slow` runs matrix + wire only (<30s)
