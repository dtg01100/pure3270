# Pure3270 3270 Terminal Emulator Library

**ALWAYS follow these instructions first** and only fallback to additional search and context gathering if the information here is incomplete or found to be in error.

Pure3270 is a pure Python 3270 terminal emulator library that replaces the s3270 binary dependency in p3270 setups. It provides both standalone Session/AsyncSession classes and monkey-patching capabilities for seamless p3270 integration.

## Working Effectively

### Bootstrap and Build
Set up the development environment:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
# .venv\Scripts\activate   # Windows

# Install package in editable mode (takes ~3 seconds)
pip install -e .

# Install development dependencies (may fail due to network timeouts)
# If pip install times out, document this as "pip install fails due to network limitations"
pip install -e .[test]
```

**NEVER CANCEL BUILDS**: Package installation typically takes 3 seconds. If network issues occur with PyPI, this is a known limitation - document as such.

### Core Development Commands

**Linting and formatting** (requires dependencies):
```bash
# Check code formatting
python -m black --check pure3270/

# Format code
python -m black pure3270/

# Run linter
python -m flake8 pure3270/
```

**Testing**:
```bash
# Quick smoke test (0.07 seconds) - ALWAYS use this for validation
python quick_test.py

# Run all built-in tests (0.6 seconds total)
# NOTE: Some tests may fail due to missing dependencies (integration, CI, comprehensive)
# Focus on: Quick Smoke Test, Navigation Method Test, Release Validation Test
python run_all_tests.py

# Integration test (may fail on missing dependencies)
python integration_test.py

# CI test suite (0.09 seconds)
python ci_test.py

# Release validation test
python release_test.py

# Unit tests (requires pytest)
python -m pytest tests/ -v
```

### Manual Validation Scenarios

**ALWAYS run these validation steps after making changes**:

1. **Import and basic functionality test** (0.08 seconds):
```bash
python -c "
import pure3270
session = pure3270.Session()
print('✓ Session created successfully')
print('✓ Available methods:', len([m for m in dir(session) if not m.startswith('_')]))
session.close()
print('✓ Session closed cleanly')
"
```

2. **Run quick smoke test** (0.07 seconds):
```bash
python quick_test.py
```

3. **Test standalone example** (0.08 seconds):
```bash
python examples/example_standalone.py
```

4. **Test patching functionality** (0.08 seconds):
```bash
python examples/example_patching.py
```

5. **Code compilation check** (0.05 seconds):
```bash
python -m py_compile pure3270/*.py
```

6. **Complete validation workflow** (0.6 seconds total):
```bash
python quick_test.py && python examples/example_standalone.py
```

## Build and Test Timing

- **Package installation**: 3 seconds
- **Quick smoke test**: 0.07 seconds  
- **All tests suite**: 0.6 seconds
- **Standalone example**: 0.08 seconds
- **Patching example**: 0.08 seconds
- **Code compilation check**: 0.05 seconds

**NEVER CANCEL** these operations - they complete quickly.

## Key Architecture and Navigation

### Package Structure
```
pure3270/
├── __init__.py          # Main API exports (Session, AsyncSession, enable_replacement)
├── session.py           # Core Session classes (70KB main file)
├── emulation/           # 3270 terminal emulation logic
├── protocol/            # TN3270/TN3270E protocol handling  
└── patching/            # p3270 monkey-patching functionality

Root level:
├── examples/            # Runnable example scripts
├── tests/               # Unit tests (require pytest)
├── pyproject.toml       # Modern Python packaging config
└── setup.py             # Traditional setuptools config
```

### Important Files to Check When Making Changes

- **Always check session.py** after modifying core functionality (main 70KB file)
- **Always run quick_test.py** after any change to validate basics
- **Always check examples/** when changing public APIs
- **Always run black formatting** before committing changes

### Common Validation Workflows

1. **After changing session.py**:
```bash
python quick_test.py && python examples/example_standalone.py
```

2. **After changing patching functionality**:
```bash
python examples/example_patching.py
```

3. **Before committing any change**:
```bash
python -m black pure3270/ && python run_all_tests.py
```

## Installation and Dependency Notes

### Core Package
- **Zero runtime dependencies** - uses Python standard library only
- **Python 3.8+ required** - supports up to Python 3.13
- **No external binaries needed** - pure Python implementation

### Development Dependencies (Optional)
These may fail to install due to network timeouts:
```bash
pytest >= 7.0          # Unit testing framework
pytest-asyncio >= 0.21 # Async test support  
flake8 >= 7.0          # Code linting
black >= 24.0          # Code formatting
pytest-cov >= 5.0      # Coverage reporting
p3270 >= 0.1.6         # For patching integration tests
```

**If pip install fails**: Document as "pip install fails due to network limitations" and use alternative validation methods.

### Alternative Installation (when PyPI is inaccessible)
If pip install fails with network timeouts, the core package still works:
```bash
# Core functionality requires no external dependencies
python -c "import pure3270; print('✓ Core package works')"

# Use built-in validation instead of external test tools
python quick_test.py  # Built-in smoke test
python run_all_tests.py  # Built-in test suite
```

## Usage Patterns for Agents

### Basic Session Usage
```python
from pure3270 import Session

# Synchronous usage
with Session() as session:
    session.connect('hostname', port=23, ssl=False)
    session.send(b'String(username)')
    session.send(b'key Enter')
    response = session.read()
```

### Async Session Usage  
```python
from pure3270 import AsyncSession
import asyncio

async def main():
    async with AsyncSession() as session:
        await session.connect('hostname', port=23)
        await session.send(b'key Enter')
        response = await session.read()

asyncio.run(main())
```

### p3270 Integration via Patching
```python
import pure3270
pure3270.enable_replacement()  # Apply patches

import p3270  # Now uses pure3270 under the hood
session = p3270.P3270Client()
session.connect('hostname')
```

## Key Capabilities

- **TN3270/TN3270E protocol support** - full 3270 terminal emulation
- **Screen buffer management** - field handling, attribute processing
- **Macro execution** - s3270-compatible command scripting
- **SSL/TLS support** - secure connections using Python ssl module
- **Async/sync APIs** - both Session and AsyncSession available
- **p3270 compatibility** - drop-in replacement via monkey patching

## Troubleshooting

### Network Issues
- **PyPI timeouts are common** - document as known limitation
- **p3270 not installed warnings are normal** - library works standalone

### Validation Failures
- **Integration tests may fail** - focus on quick_test.py and examples
- **Unit tests require pytest** - use alternative validation if unavailable
- **Expected test results**: Quick Smoke Test, Navigation Method Test, and Release Validation Test should PASS. Integration/CI/Comprehensive tests may fail due to missing dependencies.

### Build Issues
- **No external dependencies for core functionality** - should always work
- **Development tools may be unavailable** - document and use alternatives

Always prioritize the quick validation methods (quick_test.py, examples/) over complex test suites when dependencies are unavailable.

## Frequently Used Commands Quick Reference

**Essential validation commands** (copy-paste ready):
```bash
# Quick validation after changes (0.15 seconds total)
python quick_test.py && python examples/example_standalone.py

# Import test and session verification (0.08 seconds)
python -c "import pure3270; s=pure3270.Session(); print('✓ Works'); s.close()"

# Full test suite without external dependencies (0.6 seconds)
python run_all_tests.py

# Check code compiles (0.05 seconds)  
python -m py_compile pure3270/*.py
```

**When linting tools are available**:
```bash
# Format and lint
python -m black pure3270/ && python -m flake8 pure3270/

# Complete pre-commit validation
python -m black pure3270/ && python quick_test.py && python run_all_tests.py
```