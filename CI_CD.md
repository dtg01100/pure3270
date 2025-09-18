# Pure3270 CI/CD Process

This document describes the CI/CD process for Pure3270.

## Local CI Testing

**IMPORTANT**: Your local CI runs should test everything that is tested by GitHub Actions. Use the comprehensive local CI system:

```bash
# Quick CI tests (like GitHub quick-ci.yml)
./ci.sh

# Full CI suite (like GitHub ci.yml)
./ci.sh full

# Specific test types
./ci.sh format      # Code formatting
./ci.sh precommit   # Pre-commit checks
./ci.sh static      # Static analysis
./ci.sh smoke       # Basic smoke test
```

See [CI_README.md](CI_README.md) for complete local CI documentation.

## GitHub Actions Workflows

### 1. Quick CI (`.github/workflows/quick-ci.yml`)
- Runs on PRs to non-main branches
- Tests Python 3.10-3.13
- Fast feedback with linting, unit tests, and quick smoke test
- **Local equivalent**: `./ci.sh` or `python local_ci.py`
- Completes in 2-5 minutes

### 2. Full CI (`.github/workflows/ci.yml`)
- Runs on PRs to main/develop and pushes to those branches
- Tests multiple Python versions (3.9-3.13)
- Comprehensive testing including integration tests, static analysis, coverage
- **Local equivalent**: `./ci.sh full` or `python run_full_ci.py`
- Release validation and package publishing

### 3. Pre-commit Hooks (`.github/workflows/pre-commit.yml`)
- Runs on push/PR to main/develop
- Validates code formatting, linting, type checking
- **Local equivalent**: `./ci.sh precommit` or `pre-commit run --all-files`

### 4. Static Analysis (`.github/workflows/static-analysis.yml`)
- Runs mypy, pylint, bandit across all Python versions
- **Local equivalent**: `./ci.sh static` or `python run_full_ci.py --skip-hooks --skip-coverage --skip-integration`

## Release Process

## Pre-Release Testing

Before creating a release, ensure all tests pass locally using the same tests as GitHub Actions:

```bash
# Run the same tests as GitHub Actions
./ci.sh full

# Or simulate GitHub Actions exactly
./ci.sh github
```

This ensures your release will pass CI before you publish it.

## Release Process

### 1. Create a GitHub Release
- Run full local CI tests first: `./ci.sh full`
- Navigate to the "Releases" section in GitHub
- Click "Draft a new release"
- Create a new tag (e.g., v1.2.3)
- Fill in release notes
- Publish the release

### 2. Automated Release Validation
When a release is published, the following automated steps occur:
1. All tests must pass (unit tests, integration tests, release validation)
2. Package is built using `python -m build`
3. Package is uploaded as artifacts
4. Package is published to PyPI using trusted publishing

## Local Development Workflow

### Before Committing
```bash
# Format code and run quick checks
./ci.sh format
./ci.sh precommit
```

### Automatic Formatting Workflow

The repository uses pre-commit hooks that run Black and isort in *check-only* mode. They purposely fail (rejecting the commit) when formatting changes are required, without directly modifying files. This keeps feature commits free from unrelated formatting noise.

When a commit is rejected due to formatting:

1. Run the auto-format helper:
   ```bash
   python scripts/auto_format_commit.py
   ```
2. The script will:
   - Apply Black + isort formatting (using `pyproject.toml` config)
   - Stage only files modified by formatting
   - Create a conventional commit: `chore(format): apply black + isort auto-formatting` (with `[skip ci]`)

If you want to review the changes before committing:
```bash
python scripts/auto_format_commit.py --no-commit
git diff --cached
git commit -m "chore(format): apply black + isort auto-formatting"
```

If you have additional unstaged work unrelated to formatting and still want to run the script, supply `--allow-mixed` (not generally recommended because it may stage only some files):
```bash
python scripts/auto_format_commit.py --allow-mixed
```

To customize the commit message:
```bash
python scripts/auto_format_commit.py -m "chore(format): re-run formatters"
```

Commit template for formatting-only commits lives at `.gitmessage-formatting` (optional local usage: `git config commit.template .gitmessage-formatting`).

Why this design:
- Prevents accidental inclusion of large mechanical diffs in feature commits
- Keeps blame clean and improves review signal
- Makes CI output clearer by isolating formatting adjustments

Typical workflow example:
```bash
# Make code changes
git add .
git commit -m "feat: add new negotiation logic"  # Fails due to formatting
python scripts/auto_format_commit.py              # Creates formatting commit
git commit -m "feat: add new negotiation logic"  # Now succeeds
```

Resequencing commits (optional): After creating the formatting commit you can (if desired) interactively rebase to squash it into your feature commit, though generally leaving separate `chore(format)` commits is preferred for transparency.

Edge cases handled by the script:
- No changes needed -> exits successfully with message
- Unstaged non-format changes present -> aborts (unless `--allow-mixed`)
- Formatter instability -> warns but proceeds

CI Note: Formatting commits are tagged with `[skip ci]` to avoid spending CI resources on mechanical updates. Remove the tag if you specifically want CI to run for a formatting commit.

### Before Pushing
```bash
# Run the same tests as GitHub Actions
./ci.sh full
```

### Daily Development
```bash
# Quick feedback loop
./ci.sh          # Quick tests
./ci.sh smoke     # Basic validation
```

## Test Protection

The CI/CD process ensures that:
- **Local and GitHub Actions parity**: The same tests run locally and in CI
- No release can be created without passing all tests
- No package can be pushed to PyPI without passing release validation
- Code quality is maintained through linting and formatting checks
- Compatibility is verified across multiple Python versions
- Static analysis catches potential issues early

## Manual Release Process (if needed)

If you need to manually release:

1. **Run local CI first** (matches GitHub Actions exactly):
   ```bash
   ./ci.sh full
   ```

2. Run all tests manually:
   ```bash
   # Modern CI system (recommended)
   ./ci.sh full

   # Or run pytest directly
   python -m pytest tests/
   ```

3. Build the package:
   ```bash
   pip install build
   python -m build
   ```

4. Upload to PyPI:
   ```bash
   pip install twine
   twine upload dist/*
   ```

## Troubleshooting CI Failures

### Local Testing Failed
```bash
# Check what specifically failed
./ci.sh full

# Test individual components
./ci.sh static     # Static analysis
./ci.sh precommit  # Pre-commit hooks
./ci.sh smoke      # Basic functionality
```

### GitHub Actions vs Local Differences
```bash
# Use the GitHub simulation mode
./ci.sh github

# Check specific Python version compatibility
python3.9 -m pytest tests/  # If available
python3.11 -m pytest tests/
```

### Format Issues
```bash
# Auto-format code
./ci.sh format

# Check what needs formatting
black --check pure3270/
isort --check-only pure3270/
```

## CI Scripts Reference

- `./ci.sh` - Main entry point (see `./ci.sh help`)
- `python local_ci.py` - Python wrapper with presets
- `python run_full_ci.py` - Comprehensive CI runner
- See [CI_README.md](CI_README.md) for complete documentation
