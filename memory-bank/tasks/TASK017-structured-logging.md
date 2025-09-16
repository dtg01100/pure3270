# TASK017: Implement Structured Logging

## Objective
Replace print/debug statements with structured JSON logging for better observability.

## Requirements
- Use logging module with JSON formatter.
- Log levels: DEBUG for protocol, INFO for sessions, ERROR for failures.
- Include context: session ID, timestamps, structured fields.

## Implementation Steps
1. Configure logging in pure3270/__init__.py with JSONHandler.
2. Refactor debug prints in session.py, data_stream.py to logger.
3. Add log messages for key events: connect, parse, errors.
4. Update tests to capture and assert log output.
5. Document logging config in README.md.

## Success Metrics
- All debug output converted to structured logs.
- Logs parseable by tools like ELK or jq.
- No loss of debug info.

## Dependencies
- Enhanced exceptions (TASK012)