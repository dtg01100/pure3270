Testing pure3270
================

Test Suite Overview
-------------------

The test suite includes:
- Unit tests for individual components
- Integration tests for protocol flows
- Property-based tests with Hypothesis
- Performance benchmarks
- Compatibility tests for p3270 patching

Running Tests
-------------

Basic test run:
.. code-block:: bash

    pytest tests/

With coverage:
.. code-block:: bash

    pytest --cov=pure3270 --cov-report=html tests/

Property-based tests:
.. code-block:: bash

    pytest -m property tests/

Integration tests (may require Hercules):
.. code-block:: bash

    pytest -m integration tests/

Test Fixtures
-------------

- `screen_buffer`: Mocked screen buffer for emulation tests
- `mock_tn3270_handler`: Mocked TN3270 handler for protocol tests
- `async_session`: Fixture for AsyncSession with cleanup
- `memory_limit_100mb`: Limits memory to 100MB for performance tests

Property-Based Testing
----------------------

Uses Hypothesis for edge case generation. Examples:

- Cursor movement boundary testing
- Invalid data stream parsing
- Field attribute combinations

Example property test:
.. code-block:: python

    @given(st.integers(min_value=0, max_value=23), st.integers(min_value=0, max_value=79))
    def test_cursor_movement_bounds(row, col):
        screen = ScreenBuffer(rows=24, cols=80)
        screen.move_cursor(row, col)
        assert 0 <= screen.cursor_row < 24
        assert 0 <= screen.cursor_col < 80

CI/CD Testing
-------------

GitHub Actions run:
- Unit/integration tests across Python 3.9-3.13
- Static analysis (mypy, pylint, bandit)
- Security scanning
- Documentation build verification
