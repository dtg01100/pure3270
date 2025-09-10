# CRUSH.md - Pure3270 Development Guide

## Build/Install
- Install: `pip install -e .`
- Install dev deps: `pip install -e .[test]`

## Linting/Formatting
- Check formatting: `black . --check`
- Format code: `black .`
- Lint: `flake8 .`

## Testing
- Run all tests: `pytest tests/`
- Run single test: `pytest tests/test_module.py::test_name`
- Run with coverage: `pytest tests/ --cov=pure3270`
- Run benchmarks: Look for tests marked with @pytest.mark.benchmark

## Code Style
- Python 3.8+ only, using standard library (no external deps)
- Use asyncio for async operations
- Follow existing patterns in session.py for sync/async wrappers
- Use context managers for resource management
- Prefer bytearray for binary data manipulation
- Use structured logging with appropriate levels
- Handle errors with custom exceptions (see exception.py)
- Prefer composition over inheritance
- Use properties for computed values
- 4-space indentation, no tabs
- Prefer double quotes for strings
- Type hints encouraged but not enforced
- Private methods start with underscore
- Unit tests in tests/ matching source structure
- Mock external dependencies in tests

## Additional Development Practices
- Use pytest-asyncio for async tests
- Use parametrized tests for testing multiple scenarios
- Use fixtures for test setup/teardown
- Write comprehensive tests for new features
- Maintain 80%+ test coverage
- Document public APIs with docstrings
- Follow semantic versioning for releases
- Use GitHub Actions for CI/CD
- Maintain compatibility with p3270 library
- Follow RFC specifications for protocol implementation