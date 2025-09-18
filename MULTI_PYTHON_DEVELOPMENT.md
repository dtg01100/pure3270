# Multi-Python Development Environment

The Pure3270 project now supports comprehensive local testing across all Python versions in our CI matrix (3.9, 3.10, 3.11, 3.12, 3.13) using a Docker devcontainer with pyenv.

## Quick Start

After opening the project in VS Code with the devcontainer, all Python versions are automatically installed and configured.

### Available Commands

```bash
# Test across all Python versions (quick smoke test)
test-all-pythons

# Run full CI across all Python versions
run-full-ci-all-pythons

# Switch to a specific Python version
switch-python 3.9.21
switch-python 3.12.11

# List all available Python versions
pyenv versions
```

### Manual Version Switching

```bash
# Using pyenv directly
pyenv shell 3.9.21
python --version  # Should show Python 3.9.21

# Using our convenience script
switch-python 3.10.14
python --version  # Should show Python 3.10.14
```

### Testing Workflows

#### 1. Quick Validation Across All Versions
```bash
test-all-pythons
```
This runs `python quick_test.py` in each Python version and provides a summary.

#### 2. Full CI Across All Versions
```bash
run-full-ci-all-pythons
```
This runs `python run_full_ci.py` in each Python version for comprehensive testing.

#### 3. Test Specific Version
```bash
switch-python 3.9.21
python quick_test.py
python run_full_ci.py
```

#### 4. Using Tox (Alternative)
```bash
# Install tox first
pip install tox

# Quick smoke test across all versions
tox -e smoke

# Full CI across all versions
tox -e fullci

# Test specific version
tox -e py39

# Run linting
tox -e lint

# Format code
tox -e format
```

## Python Version Matrix

The following Python versions are installed and available:

| Version | pyenv Name | Status | Notes |
|---------|------------|--------|--------|
| 3.9.21  | 3.9.21     | ✅ Active | Oldest supported version |
| 3.10.14 | 3.10.14    | ✅ Active | LTS version |
| 3.11.10 | 3.11.10    | ✅ Active | LTS version |
| 3.12.11 | 3.12.11    | ✅ Active | **Default** - Current stable |
| 3.13.1  | 3.13.1     | ✅ Active | Latest version |

## Development Workflow

### 1. Standard Development
Use Python 3.12 (default) for day-to-day development:
```bash
# Default version is already 3.12
python --version  # Python 3.12.11
python quick_test.py
```

### 2. Cross-Version Validation
Before committing changes, test across all versions:
```bash
test-all-pythons
```

### 3. Debugging Version-Specific Issues
If a specific Python version fails:
```bash
switch-python 3.9.21
python quick_test.py
# Debug the specific issue
```

### 4. CI Parity Validation
Ensure local results match GitHub Actions:
```bash
run-full-ci-all-pythons
```
This should match the results from our GitHub Actions CI matrix.

## Package Installation

Each Python version has pure3270 installed in editable mode with test dependencies:

```bash
# Current version
pip list | grep pure3270

# Switch and check another version
switch-python 3.10.14
pip list | grep pure3270
```

## Troubleshooting

### pyenv Not Found
If pyenv commands don't work, ensure it's properly initialized:
```bash
export PATH="/home/vscode/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

### Python Version Not Available
List available versions:
```bash
pyenv versions
```

If a version is missing, it may not have installed properly. Check the setup logs or manually install:
```bash
pyenv install 3.9.21
```

### Package Not Installed
If pure3270 is not available in a Python version:
```bash
switch-python 3.9.21
pip install -e .
pip install -e .[test]  # May fail for some versions
```

### Test Dependencies Missing
Some Python versions may not support all test dependencies:
```bash
switch-python 3.13.1
pip install pytest pytest-asyncio  # Core testing only
```

## Configuration Files

### devcontainer.json
- Configures VS Code extensions for Python development
- Sets up Docker build with custom Dockerfile
- Configures Python interpreter paths for all versions

### Dockerfile
- Installs pyenv and build dependencies
- Compiles Python 3.9.21, 3.10.14, 3.11.10, 3.12.11, 3.13.1
- Sets up user environment and PATH

### setup-python-versions.sh
- Post-create script that installs pure3270 in all Python versions
- Creates convenience scripts in /home/vscode/bin/
- Sets default Python version to 3.12.11

### tox.ini
- Alternative testing configuration using tox
- Supports isolated testing environments
- Includes linting and coverage configurations

## CI Alignment

This local setup exactly mirrors our GitHub Actions CI matrix:

**GitHub Actions Matrix:**
```yaml
strategy:
  matrix:
    python-version: ["3.9", "3.10", "3.11", "3.12", "3.13"]
```

**Local Versions:**
- 3.9.21 (maps to CI "3.9")
- 3.10.14 (maps to CI "3.10")
- 3.11.10 (maps to CI "3.11")
- 3.12.11 (maps to CI "3.12")
- 3.13.1 (maps to CI "3.13")

Both environments run the same test commands:
- `python quick_test.py`
- `python run_full_ci.py`

## Best Practices

1. **Default Development**: Use Python 3.12 for daily work
2. **Pre-Commit Validation**: Run `test-all-pythons` before committing
3. **CI Debugging**: Use `run-full-ci-all-pythons` to reproduce CI issues locally
4. **Version-Specific Debugging**: Switch to the problematic version for focused debugging
5. **Clean Testing**: Use tox for isolated environment testing when needed

## Performance Notes

- **Container Build Time**: ~15-20 minutes (Python compilation)
- **Setup Script Time**: ~5-10 minutes (package installation across versions)
- **Quick Test Time**: ~0.07 seconds per version (~0.35 seconds total)
- **Full CI Time**: ~0.6 seconds per version (~3 seconds total)

The devcontainer is built once and reused, so the setup time is amortized across development sessions.
