# Pure3270 Testing

This document describes how to run tests for the Pure3270 library.

## Test Scripts

### 1. Quick Smoke Test (`quick_test.py`)
Fast test to verify basic functionality:
```bash
python quick_test.py
```

### 2. Integration Test (`integration_test.py`)
Comprehensive integration test:
```bash
python integration_test.py
```

### 3. CI/CD Test (`ci_test.py`)
Lightweight tests that can run in CI/CD environments:
```bash
python ci_test.py
```

### 4. Comprehensive Test (`comprehensive_test.py`)
More thorough tests including navigation method verification:
```bash
python comprehensive_test.py
```

### 5. Navigation Method Test (`navigation_method_test.py`)
Specifically tests that all navigation methods are implemented:
```bash
python navigation_method_test.py
```

### 6. Release Validation Test (`release_test.py`)
Comprehensive test suite for release validation:
```bash
python release_test.py
```

### 7. Run All Tests Script (`run_all_tests.py`)
Convenience script to run all tests:
```bash
python run_all_tests.py
```

## Running Unit Tests

Run the full unit test suite:
```bash
python -m pytest tests/ -v
```

## Code Quality Checks

### Linting
```bash
python -m flake8 pure3270/
```

### Code Formatting
Check code formatting:
```bash
python -m black --check pure3270/
```

Format code:
```bash
python -m black pure3270/
```

## Test Coverage

The test suite verifies:
- Module imports
- Class instantiation
- Mock server connectivity
- Navigation method availability
- p3270 library patching
- Session management
- Macro execution
- Screen buffer operations
- Basic functionality
- CLI functionality

## Requirements

- Python 3.7+
- Required Python packages (see `setup.py`)

## GitHub Actions CI

The project includes GitHub Actions workflows for automated testing:

- `.github/workflows/ci.yml` - Comprehensive CI with multiple Python versions
- `.github/workflows/release.yml` - Release workflow with validation

These workflows automatically run:
- Unit tests
- Linting (flake8)
- Code formatting checks (black)
- Integration tests
- Release validation tests