# Contributing to Pure3270

Thanks for your interest in contributing! Before you start, please note:

## Macro DSL Policy (Permanent)

Macro scripting/DSL was removed from Pure3270 and will not be reintroduced.

- Do not submit PRs that add or reintroduce a macro DSL, `execute_macro`, `load_macro`, or `MacroError`.
- The CI includes a guard (`tools/forbid_macros.py`) that fails if macro DSL code or references are added back.
- Discussions and issues proposing macro DSL will be closed. Focus contributions on protocol compliance, emulation fidelity, and API quality.

## How to contribute

1. Open an issue describing the bug/feature.
2. Create a feature branch from the latest `main`.
3. Add tests for your change when practical.
4. **Add proper attribution** for any third-party code using the attribution scaffolding system.
5. Run local CI: `./ci.sh` (or `python run_full_ci.py --fast`).
6. **Code formatting is automatic**: Pre-commit hooks will auto-format and create formatting commits.
7. Submit a PR with a clear description and rationale.

## Attribution Requirements

When contributing code that is ported from or inspired by third-party sources, you must include proper attribution:

### Attribution Scaffolding System

Pure3270 provides an attribution scaffolding system to ensure consistent, legally compliant attribution:

```bash
# Interactive mode (recommended)
python tools/generate_attribution.py --interactive

# Or use command-line options
python tools/generate_attribution.py --type module \
    --source "IBM s3270/x3270" \
    --url "https://github.com/rhacker/x3270" \
    --license "BSD-3-Clause" \
    --description "TN3270 protocol implementation based on s3270"
```

### Attribution Types

- **Module-level**: For entire files with ported code
- **Function/method**: For specific functions from third-party sources
- **Class**: For classes inspired by other implementations
- **Protocol**: For RFC-based protocol implementations
- **s3270 compatibility**: For code maintaining s3270 compatibility
- **EBCDIC codec**: For encoding/decoding implementations

### Validation

Run attribution validation tests:

```bash
python -m pytest tests/test_attribution_validation.py -v
```

See `tools/ATTRIBUTION_GUIDE.md` for comprehensive documentation.

### Offline Validation

Pure3270 includes comprehensive offline validation tools that test functionality without requiring network access:

#### Quick Validation
```bash
# Run all offline validation tests
python tools/run_offline_validation.py

# Run individual validation components
python tools/synthetic_data_generator.py generate test_data 10  # Generate test data
python tools/synthetic_data_generator.py test test_data/synthetic_test_cases.json  # Test parsing
python tools/screen_buffer_regression_test.py generate test_output 5  # Generate screen tests
python tools/screen_buffer_regression_test.py run test_output  # Run screen tests
python tools/performance_benchmark.py  # Run performance benchmarks
```

#### Validation Components

- **Terminal Models**: Tests all 13 IBM 3270 terminal models (3278-2/3/4/5, 3279-2/3/4/5, etc.)
- **Protocol State Machine**: Validates TN3270 handler state transitions and history tracking
- **Synthetic Data Streams**: Generates and tests valid TN3270 data streams with various orders
- **Screen Buffer Operations**: Regression testing for screen buffer write/read operations
- **Trace Replay**: Validates protocol handling against s3270 trace files
- **Performance Benchmarks**: Measures performance of core operations

#### Integration Tests

Run integration tests that combine multiple validation approaches:

```bash
python -m pytest tests/test_integration_validation.py -v
```

These tests ensure all validation tools work together and provide comprehensive coverage.

## Code style

- Python 3.10+
- Standard library only for runtime; optional dev tools for tests/linting.
- **Formatting is automatic**: `black` and `isort` are applied automatically by pre-commit hooks.
- Follow RFCs for TN3270/TN3270E and Telnet behavior.

## Development Workflow

### Setup
```bash
# Install with development dependencies
pip install -e .[test]

# Install pre-commit hooks
pre-commit install
```

### Making Changes
```bash
# Create feature branch
git checkout -b feature/my-feature

# Make your changes
# ... edit files ...

# Commit (auto-formatting will be applied)
git add .
git commit -m "Add my feature"
# ✅ Pre-commit hooks auto-format and create commits as needed

# Run tests
python quick_test.py
./ci.sh  # Full CI suite
```

### Manual Commands (if needed)
```bash
# Manual formatting (usually not needed)
black .
isort . --profile=black

# Manual pre-commit run
./pre-commit.sh --all-files

# Run specific hooks
./pre-commit.sh black isort flake8
```
