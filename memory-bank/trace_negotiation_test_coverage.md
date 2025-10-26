---
applyTo: '**'
---
# Trace-Based Protocol Negotiation Test Coverage (Memory)

## Current Coverage
- Telnet option negotiation (WILL/DO/WONT/DONT)
- Terminal type negotiation
- TN3270E protocol negotiation
- Device type negotiation
- TN3270E functions negotiation
- BIND image handling
- Sequence validation
- Coverage reporting

## Identified Gaps
1. Negative/Failure Scenarios: No explicit tests for negotiation failures, unsupported options, or error handling.
2. Edge Cases: No tests for repeated negotiation, option renegotiation, or out-of-order negotiation.
3. Subnegotiation Details: No deep validation of subnegotiation payloads (terminal type values, TN3270E function lists).
4. Option Rejection: No checks for WONT/DONT responses or fallback behavior.
5. Extended Attributes: No coverage for extended TN3270E features (SCS-CTL-CODES, SYSREQ) beyond presence.
6. Trace Completeness: No validation that all expected negotiation steps in the trace are exercised.
7. Protocol Error Handling: No tests for malformed negotiation messages or protocol errors.
8. RFC Compliance: No explicit assertion that negotiation sequences match RFC 1576/2355 requirements.
9. Device Type Fallback: No test for fallback to default device type if negotiation fails.
10. Negotiation Timing: No checks for negotiation timeouts or delays.

## Next Steps
- Add targeted tests for each identified gap.
- Incrementally implement and validate new tests.
- Update memory and todo list after each step.
