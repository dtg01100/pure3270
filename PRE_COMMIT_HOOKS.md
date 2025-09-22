# Pre-commit Hooks

Pure3270 uses pre-commit hooks to maintain code quality and consistency. The hooks automatically format code and enforce various checks before each commit.

## Quick Start

```bash
# Install pre-commit (included in test dependencies)
pip install -e .[test]

# Install hooks
pre-commit install

# Now all commits will be automatically checked and formatted
```

## Automatic Formatting

**NEW**: Pre-commit hooks now automatically fix formatting issues and create formatting commits!

When you run `git commit`, the pre-commit hooks will:

1. **Check all other rules first** (flake8, mypy, etc.)
2. **Automatically apply formatting** with `black` and `isort` if needed
3. **Create a formatting commit** if changes were made
4. **Re-run all checks** to ensure everything passes

### Traditional Workflow (Before)
```bash
git add file.py
git commit -m "Add new feature"
# ❌ Commit fails due to formatting
black file.py
isort file.py
git add file.py
git commit -m "Add new feature"
# ✅ Success
```

### New Auto-Formatting Workflow
```bash
git add file.py
git commit -m "Add new feature"
# ✅ Auto-formats and commits, then applies your commit
# Results in two commits:
# 1. "chore(format): apply black + isort auto-formatting [skip ci]"
# 2. "Add new feature"
```

## Available Hooks

The pre-commit configuration includes:

### Code Formatting (Auto-fix)
- **black**: Python code formatter (automatically applied)
- **isort**: Import sorter (automatically applied)

### Code Quality (Check-only)
- **flake8**: Style guide enforcement
- **mypy**: Static type checking
- **bandit**: Security issue detection
- **pylint**: Comprehensive code analysis

### Git Hygiene
- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Ensures files end with a newline
- **check-yaml**: Validates YAML syntax
- **check-added-large-files**: Prevents large files from being committed

## Manual Usage

### Run All Hooks
```bash
# Standard pre-commit (old way)
pre-commit run --all-files

# New auto-formatting script (recommended)
python scripts/pre_commit_with_autofix.py --all-files

# Or use the convenient wrapper
./pre-commit.sh --all-files
```

### Run Specific Hooks
```bash
# Just formatting
./pre-commit.sh black isort

# Just linting
./pre-commit.sh flake8 mypy
```

### Manual Formatting
If you want to format without committing:
```bash
# Format all files
black .
isort . --profile=black

# Format specific files
black file1.py file2.py
isort file1.py file2.py --profile=black

# Use the existing auto-format script
python scripts/auto_format_commit.py --no-commit
```

## Configuration Files

- **`.pre-commit-config.yaml`**: Pre-commit hook configuration
- **`pyproject.toml`**: Black configuration (line length, etc.)
- **`mypy.ini`**: MyPy static type checker configuration
- **`.bandit`**: Bandit security checker configuration
- **`.pylintrc`**: Pylint configuration
- **`setup.cfg`**: Flake8 configuration

## Customization

### Skip Hooks for a Commit
```bash
# Skip all pre-commit hooks
git commit --no-verify -m "Emergency fix"

# Skip specific hooks (not recommended)
SKIP=flake8,mypy git commit -m "Work in progress"
```

### Disable Auto-formatting
If you prefer the old behavior (formatting checks fail instead of auto-fix):
```bash
# Use traditional pre-commit
pre-commit run --all-files

# Or use the script with no auto-commit
python scripts/pre_commit_with_autofix.py --all-files --no-auto-commit
```

## CI Integration

In GitHub Actions, pre-commit runs with `--no-auto-commit` to avoid creating commits in CI:

```yaml
- name: Run pre-commit hooks with auto-formatting
  run: |
    git config --local user.email "action@github.com"
    git config --local user.name "GitHub Action"
    python scripts/pre_commit_with_autofix.py --all-files --no-auto-commit
```

This ensures formatting is checked in CI but commits are only created locally during development.

## Troubleshooting

### Pre-commit Installation Issues
```bash
# Reinstall pre-commit
pip install --upgrade pre-commit
pre-commit clean
pre-commit install
```

### Hook Updates
```bash
# Update hook versions
pre-commit autoupdate

# Clear cache and reinstall
pre-commit clean
pre-commit install --install-hooks
```

### Bypass for Emergency Commits
```bash
# Skip all hooks (use sparingly)
git commit --no-verify -m "Emergency fix"
```

### Multiple Commits Issue
If auto-formatting creates too many commits, you can squash them:
```bash
# Squash last two commits (formatting + your change)
git reset --soft HEAD~2
git commit -m "Your combined message"
```

## Best Practices

1. **Let auto-formatting work**: Don't manually format before committing
2. **Small, focused commits**: Easier to review and less likely to need formatting
3. **Run hooks on all files occasionally**: `./pre-commit.sh --all-files`
4. **Update hooks regularly**: `pre-commit autoupdate`
5. **Don't skip hooks unnecessarily**: Use `--no-verify` only for emergencies

## Migration from Old Workflow

If you were using the old workflow with manual formatting:

**Old way:**
```bash
# Make changes
git add .
git commit -m "Change"  # Fails
python scripts/auto_format_commit.py
git commit -m "Change"  # Success
```

**New way:**
```bash
# Make changes
git add .
git commit -m "Change"  # Automatically formats and succeeds
```

The new workflow is more streamlined and reduces friction while maintaining code quality.