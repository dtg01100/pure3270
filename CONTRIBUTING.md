# Contributing to Pure3270

Thank you for your interest in contributing to Pure3270! This document provides guidelines and information for contributors.

## Table of Contents
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Code of Conduct](#code-of-conduct)

## Getting Started

### Prerequisites
- Python 3.8 or later
- Git
- Familiarity with 3270 terminal protocols (helpful but not required)

### Development Setup
1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pure3270.git
   cd pure3270
   ```
3. Set up the development environment:
   ```bash
   pip install -e .[dev]
   ```
4. Run the tests to ensure everything works:
   ```bash
   python -m pytest
   ```

## Development Process

### Branching Strategy
- `main`: Production-ready code
- `develop`: Integration branch for features
- Feature branches: `feature/description-of-feature`
- Bug fixes: `bugfix/description-of-fix`
- Hotfixes: `hotfix/description-of-fix`

### Task Management
- Check the `TODO.md` file for current priorities
- Review `memory-bank/tasks/` for detailed task descriptions
- Use `DOCUMENTATION_INDEX.md` to find relevant documentation

### AI Assistant Integration
Pure3270 uses AI assistants for development. See:
- `.github/instructions/` - Task implementation guidelines
- `.github/prompts/` - AI assistant prompt templates
- `.github/chatmodes/` - AI assistant behavior modes

## Code Standards

### Python Code Style
- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Maximum line length: 88 characters (Black formatter default)
- Use descriptive variable and function names

### Code Quality Tools
The project uses several quality assurance tools:
- **Black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking
- **pylint**: Code analysis
- **bandit**: Security scanning

Run all quality checks:
```bash
python run_full_ci.py
```

### Commit Messages
Use conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/modifications
- `chore`: Maintenance tasks

## Testing

### Test Structure
- Unit tests: `tests/test_*.py`
- Integration tests: `tests/test_*_integration.py`
- Trace replay tests: `tests/test_*_traces.py`
- Performance tests: `tests/test_*_performance.py`

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_protocol.py

# Run with coverage
python -m pytest --cov=pure3270

# Run trace replay tests
python -m pytest tests/test_trace_replay.py
```

### Test Data
- Expected outputs: `tests/data/expected/`
- Test traces: `tests/data/traces/`
- Generate expected outputs: `python tools/generate_expected_outputs.py`

### Writing Tests
- Use descriptive test names
- Test both success and failure cases
- Include docstrings explaining test purpose
- Use fixtures for common test setup

## Documentation

### Documentation Standards
- Use Markdown for all documentation
- Follow the style guide in `.github/instructions/markdown.instructions.md`
- Keep documentation up to date with code changes

### Documentation Organization
See `DOCUMENTATION_INDEX.md` and `docs/README.md` for organization guidelines.

### Validation
```bash
# Validate documentation organization
python tools/validate_documentation.py --check

# Generate validation report
python tools/validate_documentation.py --report
```

## Submitting Changes

### Pull Request Process
1. Ensure all tests pass
2. Update documentation if needed
3. Run quality checks: `python run_full_ci.py`
4. Create a pull request with a clear description
5. Address review feedback

### Pull Request Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Commit messages follow conventional format
- [ ] No new linting errors
- [ ] Type hints added for new code
- [ ] Backward compatibility maintained

### Review Process
- At least one maintainer review required
- CI checks must pass
- Documentation validation must pass
- Consensus on architectural changes

## Code of Conduct

### Our Standards
- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers learn and contribute
- Maintain professional communication

### Unacceptable Behavior
- Harassment or discrimination
- Personal attacks
- Disruptive or trolling comments
- Spamming or off-topic content

### Enforcement
Violations of the code of conduct may result in:
- Warning from maintainers
- Temporary ban from contributing
- Permanent ban in severe cases

## Getting Help

### Resources
- **README.md**: Project overview and getting started
- **DOCUMENTATION_INDEX.md**: Complete documentation index
- **memory-bank/**: Project context and technical details
- **examples/**: Working code examples

### Communication
- **Issues**: Bug reports and feature requests
- **Discussions**: General questions and community discussion
- **Pull Requests**: Code review and implementation discussion

### Finding Tasks
- Check `TODO.md` for current priorities
- Look at issues labeled "good first issue"
- Review `memory-bank/tasks/` for detailed task descriptions

## Recognition

Contributors are recognized in:
- Git commit history
- CHANGELOG.md (for significant contributions)
- Project documentation

Thank you for contributing to Pure3270! 🎉
