# Tech Context

## Technologies Used

### Core Language
- **Python 3.8+**: Minimum version supporting asyncio features used
- **Asyncio**: For asynchronous network operations and session management
- **Typing**: Type hints for better code maintainability

### Protocols and Standards
- **TN3270/TN3270E**: Main protocol (RFC 1576, 1646, 2355)
- **Telnet**: Base protocol (RFC 854, 855, 856, 857, 858, 859, 860, 1091)
- **EBCDIC**: Character encoding for mainframe data (IBM CP037)
- **VT100**: ASCII fallback mode with escape sequence detection

### Development Tools
- **pytest**: Unit testing framework with async support
- **black**: Code formatting (line length 88)
- **flake8**: Code linting with strict rules
- **mypy**: Type checking (optional, not enforced)
- **coverage**: Test coverage reporting
- **Hypothesis**: Property-based testing framework (planned)
- **bandit**: Security analysis tool (planned)
- **pylint**: Code quality analysis (planned)
- **Sphinx**: API documentation generator (planned)
- **pre-commit**: Git hook management (planned)

### Build and Packaging
- **setup.py**: Traditional setuptools configuration
- **pyproject.toml**: Modern Python packaging (PEP 621)
- **pip**: Package installation and management

## Development Setup

### Environment Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS

# Install in editable mode
pip install -e .

# Install development dependencies (may fail due to network)
pip install -e .[test]
```

### Enhanced Validation Commands
```bash
# Quick smoke test (0.07 seconds)
python quick_test.py

# Modern CI system (recommended)
./ci.sh

# Full CI suite (matches GitHub Actions)
./ci.sh full

# Code formatting
python -m black pure3270/

# Linting
python -m flake8 pure3270/

# Type checking (planned)
python -m mypy pure3270/

# Security analysis (planned)
bandit -r pure3270/

# Code quality analysis (planned)
python -m pylint pure3270/

# Property-based testing (planned)
python property_tests.py

# Pre-commit hooks (planned)
pre-commit run --all-files

# Documentation generation (planned)
cd docs && make html
```

## Technical Constraints

### Zero Runtime Dependencies
- Only Python standard library allowed
- No external packages for core functionality
- Development tools are optional
- Enhancement tools will be development-only dependencies

### Performance Requirements
- Fast parsing for interactive sessions
- Low memory footprint
- Efficient EBCDIC translation
- Minimal overhead from enhancement tools

### Compatibility Requirements
- Python 3.8+ (supports asyncio features)
- Cross-platform (Linux, Windows, macOS)
- Both sync and async APIs
- p3270 compatibility maintained

### Protocol Constraints
- RFC-compliant TN3270E implementation
- Proper negotiation sequences
- Correct data stream structures
- Standard device types and capabilities

## Dependencies and Versions

### Core Dependencies (None)
Pure3270 has zero runtime dependencies.

### Development Dependencies
- pytest >= 7.0
- pytest-asyncio >= 0.21
- flake8 >= 7.0
- black >= 24.0
- pytest-cov >= 5.0
- p3270 >= 0.1.6 (for integration tests)
- hypothesis >= 6.0 (planned for property-based testing)
- bandit >= 1.7 (planned for security analysis)
- pylint >= 3.0 (planned for code quality analysis)
- Sphinx >= 7.0 (planned for documentation generation)
- pre-commit >= 3.0 (planned for git hooks)

### Python Version Support
- 3.8: Minimum supported
- 3.9-3.13: Fully supported
- Type hints use `typing` module for 3.8 compatibility
- Enhancement tools will support same version range

## Enhancement Tooling Integration

### Static Analysis Tools
The planned integration of static analysis tools will enhance code quality:
- **mypy**: Static type checking to catch type-related bugs early
- **bandit**: Security vulnerability detection in development code
- **pylint**: Comprehensive code quality analysis with detailed reporting

### Property-Based Testing
Hypothesis will be integrated for automatic edge case discovery:
- **Input Generation**: Automatic generation of diverse test inputs
- **Shrinking**: Automatic minimization of failing test cases
- **Coverage**: Enhanced test coverage through systematic exploration

### Pre-commit Hooks
Git hooks will enforce quality standards at commit time:
- **Formatting**: Automatic code formatting with black
- **Linting**: Style checking with flake8
- **Security**: Security scanning with bandit
- **Type Checking**: Static analysis with mypy

### Documentation Generation
Sphinx will provide professional API documentation:
- **Auto-documentation**: Automatic extraction from docstrings
- **Cross-references**: Links between related APIs
- **Multiple Formats**: HTML, PDF, and other output formats
- **Search Capability**: Built-in search across all documentation

### AI-Assisted Development
Copilot integration will accelerate development:
- **Code Suggestions**: AI-generated code for common patterns
- **Issue Analysis**: Automated analysis of bug reports
- **Fix Suggestions**: AI-assisted solutions for compatibility issues
- **Testing Assistance**: AI-generated test cases for edge cases
