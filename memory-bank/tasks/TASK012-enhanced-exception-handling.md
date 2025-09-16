# TASK012: Implement Enhanced Exception Handling

## Objective
Enhance exception handling across Pure3270 to include contextual information, improving debugging and error recovery.

## Requirements
- Add context to exceptions: session state, recent operations, data stream snippets.
- Implement custom exception hierarchy extending existing ones.
- Integrate with logging for detailed error traces.
- Ensure p3270 compatibility is maintained.

## Implementation Steps
1. Define new exception classes in pure3270/exceptions.py (e.g., ProtocolError with context).
2. Update key methods in session.py, data_stream.py, negotiator.py to raise contextual exceptions.
3. Add exception context builders (e.g., capture screen buffer state, recent sends/receives).
4. Update tests to verify exception raising and context extraction.
5. Document new exceptions in docs/source/api.rst.

## Success Metrics
- All major error paths include context in exceptions.
- Tests cover 90% of exception scenarios with context validation.
- No performance degradation (<5% overhead).

## Dependencies
- Structured logging (TASK017)
- Updated documentation (TASK016)