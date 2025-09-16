# Property-Based Testing for Pure3270

This directory contains property-based tests for the Pure3270 library using the Hypothesis framework.

## Overview

Property-based testing is a methodology where instead of writing individual test cases with specific inputs and expected outputs, we define general properties that should hold true for all valid inputs to our functions. The Hypothesis framework automatically generates a wide range of test cases to try to falsify these properties.

## Running Property-Based Tests

To run only the property-based tests:

```bash
pytest -m property
```

To run all tests including property-based tests:

```bash
pytest
```

To run with verbose output (to see the generated examples):

```bash
pytest --hypothesis-verbosity=verbose
```

To see statistics about the test execution:

```bash
pytest --hypothesis-show-statistics
```

## Test Structure

- `test_ebcdic_properties.py`: Tests for the EBCDIC codec implementation
- `test_screen_buffer_properties.py`: Tests for screen buffer operations
- `test_data_stream_properties.py`: Tests for data stream parsing and generation

## Writing New Property-Based Tests

1. Identify a component that would benefit from property-based testing
2. Determine the invariants or properties that should always hold true
3. Create strategies for generating valid inputs
4. Write tests using the `@given` decorator
5. Use appropriate settings to control test execution

Example:

```python
from hypothesis import given, strategies as st

@given(st.integers(), st.integers())
def test_addition_commutative(a, b):
    assert a + b == b + a
```

## Best Practices

1. Focus on invariants rather than specific outcomes
2. Test preconditions and postconditions explicitly
3. Use domain-specific knowledge to create meaningful strategies
4. Combine multiple properties to fully specify behavior
5. Keep test execution time reasonable using `@settings`
6. Mark slow tests with the `@pytest.mark.slow` decorator
