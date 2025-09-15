# Static Analysis Tools for Pure3270

This document explains how to use the static analysis tools that have been integrated into the Pure3270 project.

## Tools Included

1. **mypy** - Static type checking
2. **bandit** - Security analysis
3. **pylint** - Code quality analysis

## Installation

The static analysis tools are included as optional dependencies in the project. To install them, run:

```bash
pip install -e .[test]
```

## Pre-commit Hooks

The project uses pre-commit hooks to automatically run static analysis tools before each commit. This ensures code quality is maintained consistently.

### Setup

To install pre-commit hooks:

```bash
# Install pre-commit framework (already included in test dependencies)
# pip install -e .[test]

# Install the Git hook scripts
pre-commit install
```

### Usage

Once installed, the hooks will run automatically when you commit changes:

```bash
git add .
git commit -m "Your commit message"
```

You can also run the hooks manually on all files:

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hooks
pre-commit run black
pre-commit run flake8
```

## Running Static Analysis

### Option 1: Using the Helper Script (Recommended)

The project includes a helper script `run_static_analysis.py` that makes it easy to run all static analysis tools:

```bash
# Run all tools
python run_static_analysis.py

# Run specific tools
python run_static_analysis.py --tools mypy
python run_static_analysis.py --tools bandit pylint
python run_static_analysis.py --tools all

# Run tools in parallel
python run_static_analysis.py --parallel
```

### Option 2: Running Tools Individually

You can also run each tool individually:

```bash
# Run mypy
python -m mypy pure3270/

# Run bandit
python -m bandit -r pure3270/ -c .bandit

# Run pylint
python -m pylint pure3270/
```

## Configuration Files

Each tool has its own configuration file:

- **mypy**: `mypy.ini`
- **bandit**: `.bandit`
- **pylint**: `.pylintrc`

These files contain project-specific configurations that balance thoroughness with practicality.

## CI/CD Integration

The static analysis tools are integrated into the GitHub Actions workflows:

1. **Quick CI** (`quick-ci.yml`): Runs on PRs to non-main branches
2. **Full CI** (`ci.yml`): Runs on PRs to main/develop and pushes to those branches
3. **Static Analysis** (`static-analysis.yml`): Dedicated workflow for static analysis
4. **Reports** (`reports.yml`): Generates reports including static analysis results

Pre-commit hooks are also validated in CI to ensure all code meets quality standards.

## Addressing Issues

When the static analysis tools find issues, you should:

1. **For mypy issues**: Add type annotations to resolve type errors
2. **For bandit issues**: Review security concerns and either fix them or add `# nosec` comments if the code is safe
3. **For pylint issues**: Fix code quality issues or disable specific warnings if they are false positives

## Gradual Adoption

The tools are configured for gradual adoption:

- **mypy** starts with basic type checking and can be made stricter over time
- **bandit** focuses on medium+ severity issues initially
- **pylint** has balanced settings that avoid excessive false positives

As the codebase improves, you can increase the strictness of these tools by modifying their configuration files.