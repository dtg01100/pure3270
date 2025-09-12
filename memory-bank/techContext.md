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

### Validation Commands
```bash
# Quick smoke test (0.07 seconds)
python quick_test.py

# All built-in tests (0.6 seconds)
python run_all_tests.py

# Code formatting
python -m black pure3270/

# Linting
python -m flake8 pure3270/
```

## Technical Constraints

### Zero Runtime Dependencies
- Only Python standard library allowed
- No external packages for core functionality
- Development tools are optional

### Performance Requirements
- Fast parsing for interactive sessions
- Low memory footprint
- Efficient EBCDIC translation

### Compatibility Requirements
- Python 3.8+ (supports asyncio features)
- Cross-platform (Linux, Windows, macOS)
- Both sync and async APIs

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

### Python Version Support
- 3.8: Minimum supported
- 3.9-3.13: Fully supported
- Type hints use `typing` module for 3.8 compatibility
