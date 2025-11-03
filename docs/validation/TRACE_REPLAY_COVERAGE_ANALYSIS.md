# Trace Replay Coverage Analysis

## Executive Summary

**Question:** Does our trace replay functionality exercise all of the features exposed in the trace files?

**Answer:** **No, there are significant gaps.** The current trace replay infrastructure has two separate implementations with different coverage levels:

1. **TraceReplayServer** (tools/trace_replay_server.py) - Network-based replay server
2. **test_trace_replay.py** (tools/test_trace_replay.py) - Direct parsing validation

Neither implementation fully exercises all protocol features present in the trace files.

## Trace File Features Analysis

### Features Found in Sample Traces

From examining `smoke.trc` and `login.trc`, the trace files contain:

#### 1. **Telnet Protocol Negotiation** (✗ NOT REPLAYED)
- `WILL/DO/WONT/DONT` commands
- Terminal type negotiation (TERMINAL-TYPE)
- Binary mode negotiation
- End-of-record (EOR) negotiation
- NEW-ENVIRON negotiation
- Examples:
  ```
  RCVD DO TERMINAL TYPE (fffd18)
  SENT WILL TERMINAL TYPE (fffb18)
  RCVD SB TERMINAL TYPE SEND
  SENT SB TERMINAL TYPE IS IBM-3278-4-E SE
  ```

#### 2. **TN3270E Protocol Features** (✗ NOT REPLAYED)
- TN3270E mode negotiation
- Device type negotiation with ASSOCIATE
- Function negotiation (BIND-IMAGE, DATA-STREAM-CTL, RESPONSES, SCS-CTL-CODES, SYSREQ)
- TN3270E headers with response types
- Examples:
  ```
  RCVD SB TN3270E DEVICE-TYPE IS IBM-3287-1 CONNECT TDC01902 SE
  RCVD SB TN3270E FUNCTIONS IS BIND-IMAGE DATA-STREAM-CTL RESPONSES SE
  RCVD TN3270E(3270-DATA ALWAYS-RESPONSE 2)
  SENT TN3270E(RESPONSE POSITIVE-RESPONSE 2) DEVICE-END
  ```

#### 3. **3270 Data Stream Commands** (✓ PARTIALLY REPLAYED)
- Write commands (Write, EraseWrite, EraseWriteAlternate)
- Write Control Characters (WCC): reset, restore, resetMDT, startprinter, unformatted
- Screen formatting (SF, SFE, SA, RA, EUA, GE, MF)
- Field attributes (protected, numeric, intensified, hidden, modified)
- Extended attributes (color, highlighting, character sets, transparency)
- Order codes (SBA, SF, SFE, SA, RA, IC, PT, GE, MF, EUA)
- **Coverage:** DataStreamParser handles these, BUT test_trace_replay.py only validates basic parsing

#### 4. **Printer Protocol** (✗ NOT REPLAYED)
- Print jobs with SCS (SNA Character Stream) data
- Print job start/end markers
- PRINT-EOJ events
- Printer responses
- Examples:
  ```
  < Write(reset,unformatted,startprinter) 'USER: PKA6039...'
  RCVD TN3270E(PRINT-EOJ NO-RESPONSE 0)
  End of print job.
  ```

#### 5. **BIND Images** (✗ NOT REPLAYED)
- Session establishment parameters
- LU-LU session configuration
- Examples:
  ```
  RCVD TN3270E(BIND-IMAGE NO-RESPONSE 0)
  Now operating in TN3270E 3270 mode.
  ```

#### 6. **AID (Attention Identifier) Codes** (✗ NOT TESTED)
- Enter, Clear, PF keys
- PA keys
- Selector pen
- These are in traces but not validated in replay

#### 7. **Extended Field Attributes** (✓ PARTIALLY REPLAYED)
- Colors (blue, red, pink, green, turquoise, yellow, neutralWhite)
- Highlighting (normal, blink, reverse, underscore)
- Character sets
- Field validation
- **Coverage:** DataStreamParser handles these, minimal validation

#### 8. **Structured Fields** (✗ NOT CLEARLY TESTED)
- Query replies
- Partition management
- OIA (Operator Information Area) updates
- Read partition query responses

#### 9. **DBCS (Double-Byte Character Set)** (? UNKNOWN)
- Files like `dbcs-wrap.trc`, `korean.trc` suggest DBCS support
- Unknown if properly tested

#### 10. **Error Conditions** (✓ PRESENT IN TRACES)
- Invalid commands (invalid_command.trc)
- Short/truncated data (short_*.trc files)
- Protocol violations
- **Coverage:** Files exist but unknown if properly tested

## Current Implementation Analysis

### TraceReplayServer (tools/trace_replay_server.py)

**What it does:**
- Parses trace files into send/receive events
- Acts as a TN3270 server, replaying receive events to clients
- Validates client send events match expected sequence
- Provides bidirectional replay with connection management

**What it DOESN'T do:**
1. ✗ Does NOT parse or interpret 3270 data stream content
2. ✗ Does NOT validate screen buffer state
3. ✗ Does NOT exercise telnet negotiation (just replays raw bytes)
4. ✗ Does NOT validate TN3270E protocol semantics
5. ✗ Does NOT test printer functionality
6. ✗ Does NOT validate field attributes or screen formatting
7. ✗ Does NOT check AID code handling

**Purpose:** Network-level byte-for-byte replay, not semantic validation

### test_trace_replay.py (tools/test_trace_replay.py)

**What it does:**
- Extracts hex data from trace lines
- Feeds records to DataStreamParser
- Validates basic parsing succeeds
- Prints screen buffer and field information

**What it DOESN'T do:**
1. ✗ Does NOT validate telnet/TN3270E negotiation sequences
2. ✗ Does NOT test actual network communication
3. ✗ Does NOT validate screen output against expected state
4. ✗ Does NOT test printer functionality
5. ✗ Does NOT validate AID code processing
6. ✗ Does NOT test BIND image handling
7. ✗ Does NOT verify extended attribute rendering
8. ✗ Does NOT test client-to-server data flow (only server-to-client)

**Purpose:** Basic parser smoke testing, not comprehensive validation

## Coverage Gaps Summary

### Major Gaps

| Feature Category | In Traces? | TraceReplayServer | test_trace_replay.py | Impact |
|-----------------|-----------|-------------------|---------------------|---------|
| Telnet Negotiation | ✓ Yes | ✗ No | ✗ No | **HIGH** |
| TN3270E Protocol | ✓ Yes | ✗ No | ✗ No | **HIGH** |
| BIND Images | ✓ Yes | ✗ No | ✗ No | **HIGH** |
| Printer Protocol | ✓ Yes | ✗ No | ✗ No | **MEDIUM** |
| AID Processing | ✓ Yes | ✗ No | ✗ No | **MEDIUM** |
| Client-to-Server Data | ✓ Yes | ✓ Partial | ✗ No | **MEDIUM** |
| Screen State Validation | ✓ Implicit | ✗ No | ✗ No | **HIGH** |
| Extended Attributes | ✓ Yes | ✗ No | ✓ Minimal | **MEDIUM** |
| Error Handling | ✓ Yes | ✗ No | ✗ No | **MEDIUM** |
| DBCS Support | ✓ Yes | ✗ No | ✗ No | **LOW** |

### What IS Tested

1. ✓ Basic 3270 data stream parsing (commands, orders, attributes)
2. ✓ Screen buffer updates (minimal validation)
3. ✓ Field parsing (minimal validation)
4. ✓ Byte-level network replay (no semantic validation)

### What is NOT Tested

1. ✗ Protocol negotiation sequences (telnet, TN3270E)
2. ✗ Session establishment (BIND)
3. ✗ Bi-directional protocol flow with validation
4. ✗ Screen state correctness (pixel-perfect comparison)
5. ✗ Printer functionality
6. ✗ AID code handling
7. ✗ Error recovery and edge cases
8. ✗ Extended color and highlighting rendering
9. ✗ DBCS character handling

## Recommendations

### Immediate Actions

1. **Document Current Coverage**
   - Create comprehensive test coverage map
   - Identify which trace files test which features
   - Mark features as tested/untested

2. **Enhance test_trace_replay.py**
   ```python
   # Add validation for:
   - Expected screen content (not just "does it parse")
   - Field attribute correctness
   - AID code processing
   - Error condition handling
   ```

3. **Create Integration Tests**
   - Use TraceReplayServer with pure3270 Session
   - Test full protocol negotiation flow
   - Validate bidirectional communication
   - Test TN3270E features (headers, responses, BIND)

### Medium-Term Improvements

1. **Separate Test Categories**
   - Protocol negotiation tests (telnet, TN3270E)
   - Data stream parsing tests (current focus)
   - Screen rendering tests (visual validation)
   - Printer tests
   - Error handling tests

2. **Add Expected Output Files**
   - For each .trc file, create .expected file with:
     - Expected final screen state
     - Expected field attributes
     - Expected AID codes
   - Compare actual vs expected

3. **Create Feature-Specific Tests**
   - BIND image parsing
   - TN3270E header handling
   - Printer SCS parsing
   - DBCS character support
   - Extended attribute rendering

### Long-Term Strategy

1. **Full Protocol Validator**
   - Combine TraceReplayServer + test_trace_replay.py concepts
   - Add semantic validation at each protocol layer
   - Create comprehensive test suite

2. **Regression Testing**
   - Use traces as regression tests
   - Detect when changes break protocol handling
   - Validate against s3270 behavior

3. **Coverage Metrics**
   - Track which protocol features are tested
   - Measure code coverage from trace tests
   - Identify untested code paths

## Conclusion

The current trace replay infrastructure provides **basic smoke testing** of 3270 data stream parsing but does **NOT comprehensively exercise** the full protocol features present in the trace files.

**Key Finding:** We are testing ~30-40% of the features exposed in trace files:
- ✓ Basic data stream parsing
- ✓ Screen buffer updates (minimal)
- ✗ Protocol negotiation (0%)
- ✗ TN3270E features (0%)
- ✗ Printer functionality (0%)
- ✗ BIND processing (0%)
- ✗ Semantic validation (0%)

**Recommendation:** Enhance test_trace_replay.py to add semantic validation and create integration tests using TraceReplayServer to test full protocol flows.
