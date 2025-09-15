# Pre-commit Hooks for Pure3270

This document explains how to set up and use pre-commit hooks in the Pure3270 project to maintain code quality and consistency.

## What are Pre-commit Hooks?

Pre-commit hooks are scripts that run automatically before each Git commit. They help ensure code quality by automatically checking and formatting code before it's committed to the repository.

## Benefits

- **Consistent Code Style**: Automatically format code with Black and sort imports with isort
- **Error Detection**: Catch style violations, security issues, and potential bugs early
- **Time Savings**: Automate code quality checks, reducing manual review time
- **Team Consistency**: Ensure all contributors follow the same coding standards

## Setup

### 1. Install Pre-commit

Pre-commit is included in the project's development dependencies. If you haven't already, install the development dependencies:

```bash
pip install -e .[test]
```

### 2. Install Git Hook Scripts

Install the pre-commit hook scripts:

```bash
pre-commit install
```

This will set up the hooks to run automatically on each `git commit`.

## Usage

### Automatic Usage

Once installed, the hooks will run automatically whenever you commit changes:

```bash
git add .
git commit -m "Your commit message"
```

If any hooks fail, the commit will be aborted. You'll need to fix the issues and try again.

### Manual Usage

You can also run the hooks manually:

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hooks
pre-commit run black
pre-commit run flake8

# Run on specific files
pre-commit run black --files path/to/file.py
```

### Skipping Hooks

In exceptional cases, you can skip hooks:

```bash
# Skip all hooks
git commit -m "WIP" --no-verify

# Skip specific hooks (not recommended)
SKIP=flake8 git commit -m "Your message"
```

## Hooks Configuration

The hooks are configured in `.pre-commit-config.yaml`. Currently, the following hooks are enabled:

### Code Formatting and Style
- **black**: Automatically formats Python code
- **isort**: Sorts and organizes imports
- **flake8**: Checks for style guide violations

### General File Quality
- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Ensures files end with a newline
- **check-yaml**: Validates YAML files
- **check-added-large-files**: Prevents accidentally committing large files

## Adding New Hooks

To add new hooks:

1. Update `.pre-commit-config.yaml` with the new hook configuration
2. Run `pre-commit install` to update the hooks
3. Optionally run `pre-commit run --all-files` to run the new hooks on all files

## Updating Hooks

To update hooks to their latest versions:

```bash
pre-commit autoupdate
```

## CI Integration

Pre-commit hooks are also validated in the CI pipeline to ensure all code meets quality standards, even if a developer hasn't installed the hooks locally.

## Troubleshooting

### Hook Installation Issues

If you encounter issues installing hooks:

```bash
# Clear cache and reinstall
pre-commit clean
pre-commit install
```

### Performance Issues

If hooks are running slowly:

```bash
# Install hook environments without waiting for first run
pre-commit install-hooks
```

### Specific Tool Issues

If you're having issues with a specific tool:

```bash
# Run just that tool to see detailed output
pre-commit run black --verbose
```

## Best Practices

1. **Run hooks regularly**: Don't wait until commit time to discover issues
2. **Keep hooks up to date**: Regularly run `pre-commit autoupdate`
3. **Don't skip hooks**: Only use `--no-verify` for emergency situations
4. **Fix issues immediately**: Address hook failures before proceeding
5. **Configure appropriately**: Adjust hook settings in `.pre-commit-config.yaml` as needed

## Additional Resources

- [Pre-commit Documentation](https://pre-commit.com/)
- [Pre-commit Hooks Repository](https://pre-commit.com/hooks.html)