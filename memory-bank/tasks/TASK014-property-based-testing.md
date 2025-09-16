# TASK014: Implement Property-Based Testing

## Objective
Add property-based tests using Hypothesis for robust protocol and emulation testing.

## Requirements
- Target areas: data stream parsing, EBCDIC translation, screen buffer ops.
- Generate random valid/invalid inputs to verify invariants.

## Implementation Steps
1. Install Hypothesis in dev dependencies (pyproject.toml or requirements-dev.txt).
2. Create property tests in tests/property/ (e.g., test_data_stream_parsing.py).
3. Define strategies for 3270 orders, EBCDIC strings, screen states.
4. Run with pytest --hypothesis and integrate into CI.
5. Refactor existing tests to use Hypothesis where applicable.

## Success Metrics
- 20+ property tests covering core functions.
- Hypothesis shrinks failures to minimal examples.
- Increases test coverage by 10%.

## Dependencies
- Existing test suite (tests/)
