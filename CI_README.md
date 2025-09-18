# Pure3270 Local CI System

This directory contains scripts to run the same tests locally that are executed in GitHub Actions CI workflows. This ensures consistency between local development and CI environments.

## Overview

The GitHub Actions workflows test multiple aspects:

- **Unit Tests**: pytest with markers for test categorization
- **Integration Tests**: Full integration test suite
- **Static Analysis**: mypy, pylint, bandit, flake8
- **Code Formatting**: black, isort via pre-commit hooks
- **Coverage**: pytest-cov for coverage reporting
- **Multiple Python Versions**: 3.9, 3.10, 3.11, 3.12, 3.13

## Quick Start

### Option 1: Use the shell script (recommended)
```bash
# Quick CI tests (most common)
./ci.sh

# Full CI suite (matches GitHub Actions)
./ci.sh full

# Format code
./ci.sh format

# Setup development environment
./ci.sh setup
```

### Option 2: Use Python scripts directly
```bash
# Quick tests
python local_ci.py

# Full CI suite
python local_ci.py --full

# Pre-commit checks only
python local_ci.py --pre-commit

# Static analysis only
python local_ci.py --static
```

### Option 3: Use the comprehensive script
```bash
# All tests with full control
python run_full_ci.py

# Skip certain test types
python run_full_ci.py --skip-coverage --skip-integration

# Fast mode (stop on first failure)
python run_full_ci.py --fast
```

## Scripts Overview

### `ci.sh` - Main Entry Point
Bash script that provides a make-like interface for common tasks:

- `./ci.sh` or `./ci.sh quick` - Quick CI tests
- `./ci.sh full` - Full CI suite
- `./ci.sh format` - Code formatting
- `./ci.sh precommit` - Pre-commit checks
- `./ci.sh static` - Static analysis
- `./ci.sh smoke` - Smoke test only
- `./ci.sh setup` - Development environment setup
- `./ci.sh clean` - Clean build artifacts
- `./ci.sh help` - Show all commands

### `local_ci.py` - Python Wrapper
Provides common CI presets:

- Default: Quick CI (unit tests + smoke test)
- `--full`: Complete CI suite
- `--pre-commit`: Pre-commit hooks only
- `--static`: Static analysis only
- `--format`: Code formatting

### `run_full_ci.py` - Comprehensive CI Runner
Full-featured CI script that replicates all GitHub Actions tests:

- Unit tests with pytest
- Integration tests
- Static analysis (mypy, pylint, bandit, flake8)
- Pre-commit hooks
- Coverage reporting
- Dependency checking
- Colored output and progress reporting

## GitHub Actions Workflows Replicated

### `ci.yml` - Main CI Workflow
- **Triggers**: Push to main/develop, PRs to main
- **Tests**: Unit tests, integration tests, static analysis, coverage
- **Python versions**: 3.9-3.13
- **Local equivalent**: `./ci.sh full` or `python run_full_ci.py`

### `quick-ci.yml` - Quick CI Workflow
- **Triggers**: PRs to main/develop
- **Tests**: Unit tests only (faster feedback)
- **Python versions**: 3.10-3.13
- **Local equivalent**: `./ci.sh` or `python local_ci.py`

### `pre-commit.yml` - Pre-commit Hooks
- **Triggers**: Push/PR to main/develop
- **Tests**: black, isort, flake8, mypy, pylint, bandit
- **Local equivalent**: `./ci.sh precommit` or `python local_ci.py --pre-commit`

### `static-analysis.yml` - Static Analysis
- **Triggers**: Push/PR to main/develop
- **Tests**: mypy, pylint, bandit
- **Python versions**: 3.9-3.13
- **Local equivalent**: `./ci.sh static` or `python local_ci.py --static`

### `comprehensive-python-testing.yml` - Comprehensive Tests
- **Triggers**: Push to main/develop, PRs to main
- **Tests**: All tests across all Python versions
- **Local equivalent**: `./ci.sh github` or `python run_full_ci.py`

## Configuration Files

The local CI scripts use the same configuration files as GitHub Actions:

- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `mypy.ini` - MyPy type checker settings
- `.pylintrc` - Pylint linter configuration
- `.bandit` - Bandit security scanner settings
- `pyproject.toml` - Package configuration and tool settings

## Dependencies

### Required
- Python 3.9+ (3.11+ recommended)
- pip

### Optional (for full functionality)
- pytest - Unit testing
- pytest-cov - Coverage reporting
- mypy - Type checking
- pylint - Linting
- bandit - Security analysis
- flake8 - Style checking
- black - Code formatting
- isort - Import sorting
- pre-commit - Git hooks

### Installing Dependencies
```bash
# Install with test dependencies
pip install -e .[test]

# Or install manually
pip install pytest pytest-cov mypy pylint bandit flake8 black isort pre-commit

# Using the setup script
./ci.sh setup
```

## Usage Patterns

### Before Committing
```bash
# Format code and run quick checks
./ci.sh format
./ci.sh precommit
```

### Before Pushing
```bash
# Run the same tests as GitHub Actions
./ci.sh full
```

### During Development
```bash
# Quick feedback loop
./ci.sh quick

# Just run tests that are likely to fail
./ci.sh smoke
```

### Debugging CI Failures
```bash
# Run the exact same tests as GitHub Actions
python run_full_ci.py

# Run with verbose output
python run_full_ci.py --fast

# Run specific test types
python run_full_ci.py --skip-coverage --skip-integration
```

## Exit Codes

All scripts follow standard Unix conventions:
- **0**: Success - all tests passed
- **1**: Failure - one or more tests failed
- **2**: Error - script error or missing dependencies

## Integration with IDEs

### VS Code
The scripts work well with VS Code's integrated terminal:
```json
// In .vscode/tasks.json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Quick CI",
            "type": "shell",
            "command": "./ci.sh",
            "group": "test"
        },
        {
            "label": "Format Code",
            "type": "shell",
            "command": "./ci.sh format",
            "group": "build"
        }
    ]
}
```

### Pre-commit Integration
```bash
# Install pre-commit hooks to run on git commit
./ci.sh setup

# Or manually
pre-commit install
```

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   # Solution: Install missing tools
   pip install pytest mypy pylint bandit flake8 black isort
   ```

2. **Permission Denied on ci.sh**
   ```bash
   # Solution: Make executable
   chmod +x ci.sh
   ```

3. **Tests Fail Locally but Pass on GitHub**
   - Check Python version differences
   - Ensure same dependencies are installed
   - Check for local environment issues

4. **Slow Test Runs**
   ```bash
   # Use fast mode
   ./ci.sh quick

   # Or skip slow tests
   python run_full_ci.py --fast --skip-coverage
   ```

### Getting Help

```bash
# Show available commands
./ci.sh help

# Check tool availability
python run_full_ci.py --install-deps
```

## Extending the CI System

To add new tests that should run both locally and in GitHub Actions:

1. **Add to GitHub Actions**: Update the relevant `.github/workflows/*.yml` file
2. **Add to Local CI**: Update `run_full_ci.py` to include the new test
3. **Add Shortcut**: Add a new command to `ci.sh` if needed
4. **Update Documentation**: Update this README

## CI Parity Checklist (GA ↔ Local)

Use this short checklist whenever you change tests, add new checks, or adjust tooling:

- Quick smoke present in both:
    - Local: `python quick_test.py` runs inside `run_full_ci.py`
    - GA: quick step in `ci.yml` and `quick-ci.yml`
- Unit tests selection matches:
    - Local: `pytest tests/ -v -m "not integration"`
    - GA: same invocation in `ci.yml` and `quick-ci.yml`
- Integration tests alignment:
    - Local: `integration_test.py` via `run_full_ci.py` (skippable)
    - GA: executed in `ci.yml` when present
- Static analysis parity:
    - Tools: `mypy`, `pylint`, `flake8`, `bandit`
    - Local: `run_full_ci.py` > Static Analysis section
    - GA: `ci.yml` and `static-analysis.yml`
- Macro DSL guard enabled in both:
    - Local: `python tools/forbid_macros.py`
    - GA: dedicated step in workflows
- Pre-commit hooks (format/isort/etc.)
    - Local: `pre-commit run --all-files` via `run_full_ci.py`
    - GA: pre-commit step in `ci.yml`
- Coverage settings match when enabled:
    - Local: pytest-cov in `run_full_ci.py`
    - GA: coverage step and Codecov upload in `ci.yml`
- Python versions list documented and consistent:
    - GA matrices cover 3.9–3.13
    - Keep any version change reflected here and in workflows
- Document intentional deltas:
    - If GA diverges (env limits, speed), document in `CI_README.md` with rationale

Before merging changes that affect CI:

1. Run `python run_full_ci.py` locally and ensure it’s green
2. Verify `.github/workflows/*.yml` reflect the same groups/flags
3. Update `all_test_files.txt` if helper scripts depend on it

## Performance

Typical run times on modern hardware:

- **Smoke test**: 0.1 seconds
- **Quick CI**: 5-15 seconds
- **Full CI**: 30-60 seconds
- **With coverage**: 60-120 seconds

The scripts are optimized to fail fast and provide quick feedback during development.
