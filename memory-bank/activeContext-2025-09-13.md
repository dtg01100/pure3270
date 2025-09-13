# Agent Context Snapshot - 2025-09-13

## Conversation Summary
- **Goal:** Fix all failing tests in pure3270, especially integration tests, to be robust and CI-safe.
- **Recent Focus:** Debugging advanced protocol negotiation (TN3270E) in integration_test.py, specifically ensuring the client sends and the server receives the FUNCTIONS SEND subnegotiation after DEVICE-TYPE IS, per RFC 2355.
- **Recent Actions:**
  - Instrumented client (Negotiator) with explicit debug logging before/after sending FUNCTIONS SEND.
  - Confirmed via logs that client calls _send_supported_functions and sends the correct bytes, but server never receives them.
  - Hypothesized event loop starvation or deadlock; patched client to yield to event loop (await asyncio.sleep(0.01)) after sending FUNCTIONS SEND.
  - Next step: rerun integration test to confirm if server now receives FUNCTIONS SEND and negotiation completes.

## Technical Inventory
- **Key files:**
  - run_all_tests.py: Orchestrates all test scripts.
  - integration_test.py: Contains all integration logic, mock servers, and test cases.
  - pure3270/protocol/negotiator.py: Client-side negotiation logic, now instrumented and patched.
- **Protocol references:** RFC 2355, RFC 1091, and workspace PDFs (progcomc.pdf, f1a1c840.pdf, hcsk7b30.pdf).
- **Mock servers:** TN3270ENegotiatingMockServer, BindImageMockServer, SNAAwareMockServer, LUNameMockServer, PrinterStatusMockServer.

## Problem Analysis
- **Observed:** Client sends FUNCTIONS SEND (confirmed by debug logs and writer.drain()), but server never logs receipt.
- **Hypothesis:** Event loop starvation or deadlock; client blocks waiting for response before server can process incoming data.
- **Action:** Added await asyncio.sleep(0.01) after sending FUNCTIONS SEND to yield to event loop.

## Next Steps
- Rerun integration test to confirm if server now receives FUNCTIONS SEND and negotiation completes.
- If still failing, further investigate event loop, buffer, or mock server read issues.

---

*This snapshot captures the agent's current context, reasoning, and next planned actions as of 2025-09-13. All technical details, hypotheses, and recent code changes are documented for continuity.*
