# Pure3270 3270 Terminal Emulator Library

**ALWAYS follow these instructions first** and only fallback to additional search and context gathering if the information here is incomplete or found to be in error.

Pure3270 is a pure Python 3270 terminal emulator library that replaces the s3270 binary dependency in p3270 setups. It provides both standalone Session/AsyncSession classes and monkey-patching capabilities for seamless p3270 integration.

## RFC Compliance and Protocol Standards

**CRITICAL**: When working with TN3270/TN3270E protocol implementation, **ALWAYS defer to RFC specifications** rather than assuming the current implementation or tests have correct behavior. The implementation may contain bugs, incomplete features, or non-standard workarounds that should be corrected to match RFC requirements.

### Key RFC References
- **RFC 1576**: TN3270 Current Practices
- **RFC 1646**: TN3270 Enhancements (TN3270E)
- **RFC 2355**: TN3270 Enhancements (updated)
- **RFC 854**: Telnet Protocol Specification
- **RFC 855**: Telnet Option Specifications
- **RFC 856**: Telnet Binary Transmission
- **RFC 857**: Telnet Echo Option
- **RFC 858**: Telnet Suppress Go Ahead Option
- **RFC 859**: Telnet Status Option
- **RFC 860**: Telnet Timing Mark Option
- **RFC 1091**: Telnet Terminal-Type Option

### Protocol Implementation Guidelines
1. **RFC First**: When implementing or modifying protocol behavior, consult the relevant RFC first
2. **Test Against RFC**: Validate implementation against RFC requirements, not just existing tests
3. **Document Deviations**: If current code deviates from RFC, document why and plan correction
4. **Standards Compliance**: Prefer standards-compliant behavior over backward compatibility with non-standard implementations
5. **Protocol Constants**: Use RFC-defined constants and values, not implementation-specific ones

### Common RFC vs Implementation Conflicts
- **Negotiation sequences**: Follow RFC 1576/2355 exactly for TN3270E negotiation
- **Data stream formats**: Use RFC-specified data stream structures
- **Error handling**: Implement RFC-defined error responses and sense codes
- **Device types**: Use RFC-standard device type names and capabilities
- **Option negotiation**: Follow Telnet RFCs for option negotiation timing and responses

## Working Effectively

### Bootstrap and Build
Set up the development environment:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
# .venv/Scripts/activate   # Windows

# Install package in editable mode (takes ~3 seconds)
pip install -e .

# Install development dependencies (may fail due to network timeouts)
# If pip install times out, document this as "pip install fails due to network limitations"
pip install -e .[test]
```

**NEVER CANCEL BUILDS**: Package installation typically takes 3 seconds. If network issues occur with PyPI, this is a known limitation - document as such.

### Core Development Commands

**Linting and formatting** (requires dependencies):
```bash
# Check code formatting
python -m black --check pure3270/

# Format code
python -m black pure3270/

# Run linter
python -m flake8 pure3270/
```

**Testing**:
```bash
# Quick smoke test (0.07 seconds) - ALWAYS use this for validation
python quick_test.py

# Run all built-in tests (0.6 seconds total)
# NOTE: Some tests may fail due to missing dependencies (integration, CI, comprehensive)
# Focus on: Quick Smoke Test, Navigation Method Test, Release Validation Test
python run_all_tests.py

# Integration test (may fail on missing dependencies)
python integration_test.py

# CI test suite (0.09 seconds)
python ci_test.py

# Release validation test
python release_test.py

# Unit tests (requires pytest)
python -m pytest tests/ -v
```

### Manual Validation Scenarios

**ALWAYS run these validation steps after making changes**:

1. **Import and basic functionality test** (0.08 seconds):
```bash
python -c "
import pure3270
session = pure3270.Session()
print('✓ Session created successfully')
print('✓ Available methods:', len([m for m in dir(session) if not m.startswith('_')]))
session.close()
print('✓ Session closed cleanly')
"
```

2. **Run quick smoke test** (0.07 seconds):
```bash
python quick_test.py
```

3. **Test standalone example** (0.08 seconds):
> **NOTE:** This command may fail with a connection error due to firewall rules blocking access to `mock-tn3270-host.example.com`. This is expected in most environments.
> For offline validation, use the quick smoke test (`python quick_test.py`) instead.
```bash
python examples/example_standalone.py
```

4. **Test patching functionality** (0.08 seconds):
```bash
python examples/example_patching.py
```

5. **Code compilation check** (0.05 seconds):
```bash
python -m py_compile pure3270/*.py
```

6. **Complete validation workflow** (0.6 seconds total):
```bash
python quick_test.py && python examples/example_standalone.py
```

**CRITICAL: Task Completion Requirements**
- **Linters MUST pass before considering any task finished**
- **ALWAYS run code formatting and linting checks**:
  ```bash
  # Format code first
  python -m black pure3270/
  
  # Then run linter - this MUST pass with no errors
  python -m flake8 pure3270/
  ```
- **Never mark a task as complete if linting fails**
- **Fix all linting errors before proceeding**
- **Code quality gates**: Formatting + Linting + Tests = Task Complete

## Build and Test Timing

- **Package installation**: 3 seconds
- **Quick smoke test**: 0.07 seconds
- **All tests suite**: 0.6 seconds
- **Standalone example**: 0.08 seconds
- **Patching example**: 0.08 seconds
- **Code compilation check**: 0.05 seconds

**NEVER CANCEL** these operations - they complete quickly.

## Key Architecture and Navigation

### Package Structure
```
pure3270/
├── __init__.py          # Main API exports (Session, AsyncSession, enable_replacement)
├── session.py           # Core Session classes (70KB main file)
├── emulation/           # 3270 terminal emulation logic
│   ├── screen_buffer.py # Screen buffer management with EBCDIC support
│   ├── ebcdic.py        # EBCDIC ↔ ASCII translation (IBM CP037)
│   └── printer_buffer.py # Printer session buffer management
├── protocol/            # TN3270/TN3270E protocol handling
│   ├── tn3270_handler.py # Main protocol handler with negotiation
│   ├── negotiator.py    # Telnet/TN3270E negotiation logic
│   ├── data_stream.py   # Data stream parsing and SNA responses
│   ├── tn3270e_header.py # TN3270E header parsing
│   ├── utils.py         # Protocol constants and utilities
│   └── exceptions.py    # Protocol-specific exceptions
├── patching/            # p3270 monkey-patching functionality
│   ├── patching.py      # MonkeyPatchManager for dynamic patching
│   └── s3270_wrapper.py # S3270 interface compatibility layer
└── examples/            # Runnable example scripts
    ├── example_standalone.py # Basic Session usage patterns
    └── example_patching.py   # p3270 integration patterns

Root level:
├── examples/            # Runnable example scripts
├── tests/               # Unit tests (require pytest)
├── pyproject.toml       # Modern Python packaging config
└── setup.py             # Traditional setuptools config
```

### Important Files to Check When Making Changes

- **Always check session.py** after modifying core functionality (main 70KB file)
- **Always run quick_test.py** after any change to validate basics
- **Always check examples/** when changing public APIs
- **Always run black formatting** before committing changes

### Common Validation Workflows

1. **After changing session.py**:
```bash
python quick_test.py && python examples/example_standalone.py
```

2. **After changing patching functionality**:
```bash
python examples/example_patching.py
```

3. **Before committing any change**:
```bash
python -m black pure3270/ && python run_all_tests.py
```

## Installation and Dependency Notes

### Core Package
- **Zero runtime dependencies** - uses Python standard library only
- **Python 3.8+ required** - supports up to Python 3.13
- **No external binaries needed** - pure Python implementation

### Development Dependencies (Optional)
These may fail to install due to network timeouts:
```bash
pytest >= 7.0          # Unit testing framework
pytest-asyncio >= 0.21 # Async test support
flake8 >= 7.0          # Code linting
black >= 24.0          # Code formatting
pytest-cov >= 5.0      # Coverage reporting
p3270 >= 0.1.6         # For patching integration tests
```

**If pip install fails**: Document as "pip install fails due to network limitations" and use alternative validation methods.

### Alternative Installation (when PyPI is inaccessible)
If pip install fails with network timeouts, the core package still works:
```bash
# Core functionality requires no external dependencies
python -c "import pure3270; print('✓ Core package works')"

# Use built-in validation instead of external test tools
python quick_test.py  # Built-in smoke test
python run_all_tests.py  # Built-in test suite
```

## Usage Patterns for Agents

### Basic Session Usage
```python
from pure3270 import Session

# Synchronous usage
with Session() as session:
    session.connect('hostname', port=23, ssl=False)
    session.send(b'String(username)')
    session.send(b'key Enter')
    response = session.read()
```

### Async Session Usage
```python
from pure3270 import AsyncSession
import asyncio

async def main():
    async with AsyncSession() as session:
        await session.connect('hostname', port=23)
        await session.send(b'key Enter')
        response = await session.read()

asyncio.run(main())
```

### p3270 Integration via Patching
```python
import pure3270
pure3270.enable_replacement()  # Apply patches

import p3270  # Now uses pure3270 under the hood
session = p3270.P3270Client()
session.connect('hostname')
```

## Key Capabilities

- **TN3270/TN3270E protocol support** - full 3270 terminal emulation
- **Screen buffer management** - field handling, attribute processing
- **Macro execution** - s3270-compatible command scripting
- **SSL/TLS support** - secure connections using Python ssl module
- **Async/sync APIs** - both Session and AsyncSession available
- **p3270 compatibility** - drop-in replacement via monkey patching

## Troubleshooting

### Network Issues
- **PyPI timeouts are common** - document as known limitation
- **p3270 not installed warnings are normal** - library works standalone

### Validation Failures
- **Integration tests may fail** - focus on quick_test.py and examples
- **Unit tests require pytest** - use alternative validation if unavailable
- **Expected test results**: Quick Smoke Test, Navigation Method Test, and Release Validation Test should PASS. Integration/CI/Comprehensive tests may fail due to missing dependencies.

### Build Issues
- **No external dependencies for core functionality** - should always work
- **Development tools may be unavailable** - document and use alternatives

Always prioritize the quick validation methods (quick_test.py, examples/) over complex test suites when dependencies are unavailable.

## Frequently Used Commands Quick Reference

**Essential validation commands** (copy-paste ready):
```bash
# Quick validation after changes (0.15 seconds total)
python quick_test.py && python examples/example_standalone.py

# Import test and session verification (0.08 seconds)
python -c "import pure3270; s=pure3270.Session(); print('✓ Works'); s.close()"

# Full test suite without external dependencies (0.6 seconds)
python run_all_tests.py

# Check code compiles (0.05 seconds)
python -m py_compile pure3270/*.py
```

**When linting tools are available**:
```bash
# Format and lint
python -m black pure3270/ && python -m flake8 pure3270/

# Complete pre-commit validation (ALL MUST PASS)
# Install pre-commit hooks first
pre-commit install
# Run all pre-commit hooks
pre-commit run --all-files
# Then run tests
python quick_test.py && python run_all_tests.py
```

## Code Patterns and Conventions

### Session Management Patterns
```python
# Context manager pattern (recommended)
with Session() as session:
    session.connect(host, port)
    # ... use session ...
# Automatically closed

# Manual lifecycle management
session = Session()
try:
    session.connect(host, port)
    # ... use session ...
finally:
    session.close()
```

### EBCDIC Translation Patterns
```python
from pure3270.emulation.ebcdic import EBCDICCodec

codec = EBCDICCodec()
# ASCII to EBCDIC
ebcdic_bytes = codec.encode("HELLO")
# EBCDIC to ASCII
ascii_text, errors = codec.decode(ebcdic_bytes)
```

### Data Stream Parsing Patterns
```python
from pure3270.protocol.data_stream import DataStreamParser

parser = DataStreamParser(screen_buffer)
# Parse TN3270 data stream
parser.parse(data_bytes, data_type=TN3270_DATA)
# Parse SNA response
parser.parse(sna_bytes, data_type=SNA_RESPONSE_DATA_TYPE)
```

### Monkey Patching Patterns
```python
from pure3270.patching.patching import MonkeyPatchManager

manager = MonkeyPatchManager()
# Apply module replacement
manager._apply_module_patch('p3270.s3270', Pure3270S3270Wrapper)
# Apply method patch
manager._apply_method_patch(SomeClass, 'method_name', new_method)
```

### Protocol Negotiation Patterns
```python
from pure3270.protocol.negotiator import Negotiator

negotiator = Negotiator(writer, parser, screen_buffer)
# Perform TN3270E negotiation
await negotiator._negotiate_tn3270(timeout=10.0)
# Send subnegotiation
await send_subnegotiation(writer, TN3270E_DEVICE_TYPE, device_type_bytes)
```

### Screen Buffer Management Patterns
```python
from pure3270.emulation.screen_buffer import ScreenBuffer, Field

# Create screen buffer
screen = ScreenBuffer(rows=24, cols=80)

# Create field
field = Field(
    start=(0, 0), end=(0, 10),
    protected=False, numeric=False,
    content=b"USERNAME"  # EBCDIC bytes
)

# Add to screen
screen.fields.append(field)

# Update screen content
screen.set_char(0, 0, 0xC8)  # 'H' in EBCDIC
```

### Exception Handling Patterns
```python
from pure3270.protocol.exceptions import NegotiationError, ProtocolError

try:
    await session.connect(host, port)
except NegotiationError as e:
    logger.error(f"Negotiation failed: {e}")
except ProtocolError as e:
    logger.error(f"Protocol error: {e}")
```

### Logging Patterns
```python
import logging

logger = logging.getLogger(__name__)

# Debug level for development
logger.debug("Detailed operation info")
# Info level for important operations
logger.info("Session connected successfully")
# Error level for failures
logger.error("Connection failed", exc_info=True)
```

### Async Context Manager Patterns
```python
class AsyncSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
```

### Command Parsing Patterns
```python
# s3270 command parsing in wrapper
def _execute_command(self, cmd: str) -> bool:
    cmd = cmd.strip()
    if cmd.startswith("Connect("):
        return self._handle_connect(cmd)
    elif cmd == "Enter":
        return self._handle_enter()
    # ... more command handlers
```

### SSL Context Patterns
```python
import ssl

# Create SSL context for secure connections
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED

# Use with session
await session.connect(host, port, ssl_context=ssl_context)
```

## Architecture Flow Patterns

### Session Creation Flow
1. `Session()` → creates `AsyncSession()` internally
2. `AsyncSession.__init__()` → creates `TN3270Handler`
3. `TN3270Handler.__init__()` → creates `Negotiator`, `DataStreamParser`, `ScreenBuffer`
4. Connection established via `connect()` method

### Data Processing Flow
1. Raw bytes received from network
2. `TN3270Handler` receives data
3. `DataStreamParser.parse()` processes data stream
4. `ScreenBuffer` updated with parsed content
5. `Field` objects created/updated as needed

### Protocol Negotiation Flow
1. `Negotiator.negotiate()` starts negotiation
2. Telnet options negotiated (BINARY, EOR, TTYPE)
3. TN3270E subnegotiation performed
4. Device type and functions negotiated
5. Session ready for data exchange

### Patching Flow
1. `enable_replacement()` called
2. `MonkeyPatchManager` applies patches
3. `sys.modules['p3270.s3270']` replaced with `Pure3270S3270Wrapper`
4. `p3270.P3270Client` uses pure3270 internally

## Testing Patterns

### Unit Test Structure
```python
import pytest
from pure3270 import Session

def test_session_creation():
    """Test basic session creation."""
    session = Session()
    assert session is not None
    assert hasattr(session, 'connect')

@pytest.mark.asyncio
async def test_async_connection():
    """Test async connection handling."""
    async with AsyncSession() as session:
        # Test connection logic
        pass
```

### Integration Test Patterns
```python
# Mock server for testing
class MockTN3270Server:
    async def start(self):
        # Start mock server
        pass

    async def handle_client(self, reader, writer):
        # Handle client connections
        pass
```

### Validation Test Patterns
```python
def test_imports():
    """Test all expected imports work."""
    import pure3270
    from pure3270 import Session, AsyncSession
    assert all([Session, AsyncSession])

def test_patching():
    """Test p3270 patching functionality."""
    pure3270.enable_replacement()
    import p3270
    client = p3270.P3270Client()
    assert 'pure3270' in str(type(client.s3270))
```

## Development Workflow Patterns

### Feature Development
1. **Plan**: Identify requirements and affected components
2. **Implement**: Make changes to relevant modules
3. **Test**: Run quick_test.py and relevant examples
4. **Validate**: Run full test suite
5. **Format**: Apply black formatting
6. **Lint**: Run flake8 linting (MUST pass with no errors)
7. **Commit**: Ensure all tests pass and linting is clean

### Bug Fix Workflow
1. **Reproduce**: Create minimal test case
2. **Debug**: Use logging and quick_test.py
3. **Fix**: Implement fix in appropriate module
4. **Verify**: Ensure fix works and doesn't break existing functionality
5. **Test**: Run all validation steps
6. **Lint**: Run flake8 linting (MUST pass with no errors)

### Code Review Checklist
- [ ] Imports work correctly
- [ ] Session creation/management works
- [ ] Protocol handling is correct
- [ ] EBCDIC translation is accurate
- [ ] Error handling is appropriate
- [ ] Logging is informative
- [ ] Tests pass (quick_test.py at minimum)
- [ ] Code is formatted with black
- [ ] **Linting passes with no flake8 errors**
- [ ] Examples still work

## Common Gotchas

### Session Lifecycle
- **Always close sessions** - use context managers when possible
- **Async sessions require await** - don't mix sync/async calls
- **Connection state matters** - check `is_connected()` before operations

### EBCDIC Handling
- **Always use EBCDICCodec** - don't manually translate bytes
- **Handle encoding errors** - codec returns error information
- **Screen buffer uses EBCDIC** - convert for display

### Protocol Constants
- **Use constants from utils.py** - don't hardcode values
- **Check data type flags** - TN3270_DATA vs SNA_RESPONSE_DATA_TYPE
- **Handle TN3270E headers** - parse before data processing

### Patching Limitations
- **Version compatibility** - check p3270 version before patching
- **Import order matters** - enable_replacement() before importing p3270
- **Method signatures** - ensure compatibility with expected interface

### Network Operations
- **Handle timeouts** - negotiation can take time
- **SSL context required** - for secure connections
- **Firewall considerations** - some environments block TN3270 ports

## Performance Considerations

### Memory Usage
- **Screen buffer size** - 24x80 = 1920 bytes baseline
- **Field storage** - each field stores EBCDIC content
- **Extended attributes** - additional memory for complex screens

### Network Efficiency
- **Batch operations** - send multiple commands together
- **Connection reuse** - keep sessions alive when possible
- **Async operations** - use AsyncSession for concurrent work

### Parsing Optimization
- **Stream processing** - parse data as received
- **State tracking** - maintain parser state between calls
- **Error recovery** - handle malformed data gracefully

This comprehensive guide ensures AI agents can work effectively with pure3270, understanding its architecture, patterns, and development workflows for immediate productivity.