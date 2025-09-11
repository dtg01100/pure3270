# Pure3270 CI/CD Process

This document describes the CI/CD process for Pure3270.

## GitHub Actions Workflows

### 1. Quick CI (`.github/workflows/quick-ci.yml`)
- Runs on PRs to non-main branches
- Tests Python 3.9-3.11
- Fast feedback with linting, unit tests, and quick smoke test
- Completes in 2-5 minutes

### 2. Full CI (`.github/workflows/ci.yml`)
- Runs on PRs to main/develop and pushes to those branches
- Tests multiple Python versions (3.8-3.12)
- Comprehensive testing including integration tests
- Release validation and package publishing

## Release Process

### 1. Create a GitHub Release
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

## Test Protection

The CI/CD process ensures that:
- No release can be created without passing all tests
- No package can be pushed to PyPI without passing release validation
- Code quality is maintained through linting and formatting checks
- Compatibility is verified across multiple Python versions

## Manual Release Process (if needed)

If you need to manually release:

1. Run all tests:
   ```bash
   python -m pytest tests/
   python integration_test.py
   python release_test.py
   ```

2. Build the package:
   ```bash
   pip install build
   python -m build
   ```

3. Upload to PyPI:
   ```bash
   pip install twine
   twine upload dist/*
   ```