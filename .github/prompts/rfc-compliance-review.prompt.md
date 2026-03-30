# RFC Compliance Review Prompt

## Goal
Review Pure3270 protocol implementation code for RFC compliance and identify deviations or improvements.

## Context
Pure3270 implements TN3270/TN3270E protocols per RFC specifications. This prompt helps ensure code changes maintain RFC compliance.

## Relevant RFCs
- **RFC 1576**: TN3270 current practice
- **RFC 1646/2355**: TN3270E enhancements
- **RFC 1091**: Telnet Terminal-Type option
- **RFC 1572**: Telnet Environment option (NEW_ENVIRON)
- **RFC 854-860**: Telnet protocol suite
- **RFC 854**: NVT (ASCII fallback)

## Steps

### 1. Identify Protocol Code
Review the provided code for:
- Telnet command sequences (IAC, DO, DONT, WILL, WONT, SB, SE)
- TN3270 negotiation flows
- TN3270E header processing
- Environment option handling
- Terminal-type negotiation

### 2. Check Against RFC Requirements
For each protocol operation:
- Verify command sequences match RFC specifications
- Check byte ordering and structure
- Validate negotiation state machine
- Ensure proper error handling
- Confirm timing and sequencing

### 3. Identify Deviations
Flag any:
- Hardcoded protocol values (should use constants from `protocol/utils.py`)
- Non-standard sequences
- Missing error cases
- Race conditions or state issues
- Memory or resource leaks

### 4. Suggest Improvements
For each issue found:
- Cite specific RFC section
- Provide corrected code
- Explain the rationale
- Note any compatibility implications

## Output Format

```markdown
## RFC Compliance Review

### Code Reviewed
- File: `[file path]`
- Function: `[function name]`
- Lines: `[line range]`

### Compliance Status
[OK] **Compliant** / [WARNING] **Minor Issues** / [FAIL] **Major Deviations**

### Issues Found

#### Issue 1: [Brief Description]
**RFC Reference**: RFC XXXX Section Y.Y
**Severity**: [Critical/Major/Minor]
**Location**: `[code snippet]`

**Problem**:
[Description of the compliance issue]

**Recommended Fix**:
```python
[Corrected code]
```

**Rationale**:
[Explanation of why this change is needed]

### Summary
- Total Issues: [count]
- Critical: [count]
- Major: [count]
- Minor: [count]

### Next Steps
1. [Action item 1]
2. [Action item 2]
3. [Action item 3]

### Validation
After fixes, run:
```bash
python quick_test.py
python -m pytest tests/protocol/test_[module].py -v
python run_full_ci.py
```
```

## Examples

### Example Usage

**User**:
```
/rfc-compliance-review
File: pure3270/protocol/negotiator.py
Function: _send_terminal_type()
Lines: 145-178
```

**Agent Response**:
```markdown
## RFC Compliance Review

### Code Reviewed
- File: `pure3270/protocol/negotiator.py`
- Function: `_send_terminal_type()`
- Lines: 145-178

### Compliance Status
[WARNING] **Minor Issues**

### Issues Found

#### Issue 1: Missing NUL byte after IS command
**RFC Reference**: RFC 1091 Section 2
**Severity**: Minor
**Location**: `IAC SB TERMINAL-TYPE IS terminal_type IAC SE`

**Problem**:
RFC 1091 Section 2 specifies that the IS command should be followed by exactly one byte of data (the terminal type), terminated by IAC SE. Current implementation may include extra bytes.

**Recommended Fix**:
```python
# Before
self._send_subnegotiation(
    telnet.TERMINAL_TYPE,
    bytes([telnet.TERMINAL_TYPE_IS]) + self.terminal_type.encode('ascii')
)

# After (ensure single NUL if needed)
terminal_bytes = self.terminal_type.encode('ascii')
self._send_subnegotiation(
    telnet.TERMINAL_TYPE,
    bytes([telnet.TERMINAL_TYPE_IS]) + terminal_bytes
)
# Verify no extra NUL bytes appended
```

**Rationale**:
Some TN3270 servers are strict about IS format. Extra bytes may cause negotiation failures.

### Summary
- Total Issues: 1
- Critical: 0
- Major: 0
- Minor: 1

### Next Steps
1. Fix the IS command format
2. Add test case for RFC 1091 compliance
3. Test against strict TN3270 servers

### Validation
After fixes, run:
```bash
python quick_test.py
python -m pytest tests/protocol/test_negotiator.py::test_terminal_type_negotiation -v
python run_full_ci.py
```
```

## Constraints

- **ALWAYS** cite specific RFC sections
- **NEVER** suggest changes that violate RFC without strong justification
- **PREFER** RFC compliance over legacy compatibility
- **USE** constants from `protocol/utils.py`
- **FOLLOW** Pure3270 code style (Black, mypy strict)

## Related Prompts

- `/prompt create-implementation-plan` - Plan RFC-compliant implementation
- `/chatmode blueprint-mode` - Specification-first development
- `/chatmode debug` - Debug protocol negotiation issues

---

**Usage**: `/prompt rfc-compliance-review`
**Category**: Code Review, Protocol Compliance
**Expertise Level**: Advanced
