# Pure3270 Workspace Instructions

## Project Overview

Pure3270 is a pure Python 3.10+ TN3270/TN3270E terminal emulator and drop-in replacement for `p3270.P3270Client`. It provides a self-contained implementation with zero runtime dependencies, using only Python standard library.

**Key Characteristics:**
- **Public API**: `pure3270.Session`, `pure3270.AsyncSession`, and `pure3270.P3270Client`
- **Core Flow**: Session -> TN3270 handler -> Negotiator -> DataStream parser -> ScreenBuffer (EBCDIC)
- **RFC-First**: Implement per RFCs (1576, 1646/2355, 854-860, 1091, 1572)
- **Zero Dependencies**: Standard library only (asyncio, ssl, logging, struct)

## Essential Commands

### Quick Validation (Run After Every Change)
```bash
# Smoke test (0.07s)
python quick_test.py

# Compile check
python -m py_compile pure3270/*.py

# Full CI summary
python run_full_ci.py
```

### Development Workflow
```bash
# Install for development
pip install -e .[test]

# Format code
python -m black pure3270/

# Lint code
python -m flake8 pure3270/

# Type check
python -m mypy pure3270/

# Run tests
python -m pytest tests/ -v
python run_all_tests.py  # Alternative (0.6s)

# Pre-commit hooks
pre-commit run --all-files
```

## Critical Non-Negotiables

### WARNING: ABSOLUTELY FORBIDDEN
- **NO Macro DSL**: `execute_macro`, `load_macro`, `MacroError` are permanently removed
  - CI blocks this via `tools/forbid_macros.py`
  - Do NOT add or reference macro functionality
  - Pull requests adding macro DSL will be declined

### WARNING: MUST FOLLOW
- **RFC Compliance**: Always defer to RFC specifications over legacy quirks
- **Use Constants**: Import from `protocol/utils.py` - never hardcode protocol values
- **EBCDIC Handling**: Use `EBCDICCodec` from `emulation/ebcdic.py` only
- **Context Managers**: Always use context managers for sessions, ensure cleanup
- **Logging**: Use `logging.getLogger(__name__)` with appropriate levels
- **Exceptions**: Raise specific exceptions from `protocol/exceptions.py`

## Architecture & Key Files

### Core Modules (Study These First)
```
pure3270/
+-- __init__.py              # Public API exports
+-- session.py               # Session & AsyncSession (entry point, large)
+-- p3270_client.py          # p3270-compatible client
+-- emulation/
|   +-- screen_buffer.py     # Fields, attributes, cursor, rendering
|   +-- ebcdic.py            # EBCDIC codec, translation tables
+-- protocol/
|   +-- negotiator.py        # Telnet/TN3270E negotiation
|   +-- tn3270_handler.py    # Connection, negotiation, data stream
|   +-- data_stream.py       # 3270 data stream parsing/sending
|   +-- utils.py             # Protocol constants, telnet commands
|   +-- exceptions.py        # Custom exceptions
|   +-- printer.py           # Printer session support
|   +-- tn3270e_header.py    # TN3270E header processing
+-- trace/                   # Negotiation trace recorder
+-- utils/                   # Utility functions
```

### Documentation Files
- `AGENTS.md` - Development guide for AI agents (code style, testing)
- `.github/copilot-instructions.md` - Quick-start guide
- `docs/architecture/architecture.md` - Detailed architecture
- `memory-bank/` - Project context, progress, tasks
- `README.md` - User documentation, installation, examples

## Code Style & Conventions

### Formatting
- **Line Length**: 88 chars (Black), 127 for flake8
- **Formatter**: Black required before commits
- **Imports**: isort with black profile (stdlib → third-party → local)
- **No trailing whitespace** or missing newlines

### Type System
- **Strict Typing**: mypy strict mode for `pure3270/`
- **Type Hints**: Required for all functions and variables
- **Python 3.10+**: Use modern typing (`Union` as `|`, etc.)

### Naming
- **Classes**: PascalCase (`Session`, `ScreenBuffer`, `EBCDICCodec`)
- **Functions/Variables**: snake_case (`connect`, `send_data`, `screen_buffer`)
- **Constants**: UPPER_SNAKE_CASE (`TN3270_DATA`, `DEFAULT_PORT`)
- **Private**: Underscore prefix (`_internal_method`)

### Error Handling Pattern
```python
from pure3270.protocol.exceptions import ProtocolError, NegotiationError

try:
    # protocol operation
except ProtocolError as e:
    logger.error("Protocol failure: %s", e)
    raise
```

## Testing Strategy

### Test Categories
- **Smoke**: `quick_test.py` (must pass always)
- **Unit**: `tests/unit/` - isolated component tests
- **Integration**: `tests/integration/` - live host tests (may flake)
- **Property-based**: `tests/property/` - Hypothesis tests
- **Markers**: Use `@pytest.mark.slow`, `@pytest.mark.integration`

### Critical Rules
- **LINTING MUST PASS**: flake8 with no errors before task completion
- **Quick validation**: Always run `quick_test.py` after changes
- **Coverage**: Focus on core functionality, exclude tests from coverage
- **NEVER cancel builds**: Operations complete in seconds

## Protocol Implementation Guidelines

### RFC Priority Order
1. RFC 1576, 1646/2355 (TN3270/TN3270E)
2. RFC 1091 (Terminal Type)
3. RFC 1572 (NEW_ENVIRON)
4. RFC 854-860 (Telnet)
5. RFC 854 (NVT/ASCII fallback)

### Negotiation Flow
```
Client → Server: IAC DO TERMINAL-TYPE
Server → Client: IAC WILL TERMINAL-TYPE
Client → Server: IAC SB TERMINAL-TYPE SEND IAC SE
Server → Client: IAC SB TERMINAL-TYPE IS IBM-3278-2 IAC SE
... TN3270 negotiation continues ...
```

### Key Protocol Constants
```python
from pure3270.protocol.utils import (
    TN3270_DATA,      # 3270 data type
    TN3270E_DATA,     # TN3270E extended data
    DEFAULT_PORT,     # 23 for TN3270, 992 for secure
    # ... more constants
)
```

## Async vs Sync Patterns

### Correct Usage
```python
# Sync code (wraps AsyncSession internally)
from pure3270 import Session

with Session() as session:
    session.connect(host)
    # ... operations ...

# Async code (use AsyncSession directly)
from pure3270 import AsyncSession

async with AsyncSession() as session:
    await session.connect(host)
    # ... operations ...
```

### ⚠️ Common Pitfalls
- Don't mix sync/async patterns
- Always use context managers for cleanup
- Network CI flakes common; prioritize local smoke tests
- EBCDIC internally, convert to Unicode for display

## Development Environment

### Virtual Environment (Required)
```bash
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
pip install -e .[test]
```

### Pre-commit Setup
```bash
pre-commit install
pre-commit run --all-files
```

### Network Limitations
If PyPI is unreachable:
- Note: "pip install fails due to network limitations"
- Rely on quick tests and local validation
- Use `timeout` command for network operations (30s default)

## Memory Bank Usage

This project uses the Memory Bank system for maintaining context:

```
memory-bank/
├── projectbrief.md      # Core goals, constraints
├── productContext.md    # Why this exists, problems solved
├── activeContext.md     # Current focus, recent changes
├── systemPatterns.md    # Architecture, design patterns
├── techContext.md       # Technologies, setup, constraints
├── progress.md          # What works, what's left
└── tasks/
    ├── _index.md        # Task index with statuses
    └── TASKXXX-*.md     # Individual task files
```

**When to Update Memory Bank:**
- After implementing significant changes
- When discovering new patterns
- When user requests: "update memory bank"
- When context needs clarification

## Examples & Quick Start

### Basic Connection
```python
import pure3270

# Quick test
s = pure3270.Session()
s.connect('pub400.com')
print(s.read_screen())
s.close()
```

### Context Manager (Recommended)
```python
from pure3270 import Session

with Session() as session:
    session.connect('pub400.com')
    session.send('USERID')
    session.send_enter()
    screen = session.read_screen()
```

### Async Usage
```python
from pure3270 import AsyncSession
import asyncio

async def main():
    async with AsyncSession() as session:
        await session.connect('pub400.com')
        await session.send('USERID')
        await session.send_enter()
        screen = await session.read_screen()

asyncio.run(main())
```

## Troubleshooting

### Common Issues
1. **Connection hangs**: Use timeout wrapper, check port (23 vs 992)
2. **EBCDIC garbled**: Ensure using `EBCDICCodec`, not manual translation
3. **Negotiation fails**: Check RFC compliance, use constants from utils.py
4. **Tests flake**: Network tests may fail; prioritize local smoke tests

### Debug Tools
```bash
# Negotiation trace
python -m pure3270.trace.negotiation_test

# Server traffic logging
python debug_client_traffic.py

# Byte-level debugging
python debug_ebcdic_bytes.py
```

## When Editing Core Behavior

### Checklist
1. Touching protocol? → Validate against RFCs
2. Changed `session.py` or protocol? → Run: `quick_test.py` → examples → `run_full_ci.py`
3. Public API changes? → Update `__init__.py` and check `examples/`
4. New constants? → Add to `protocol/utils.py`, don't hardcode

### Validation Sequence
```bash
# After any core change:
python quick_test.py                    # Smoke
python -m py_compile pure3270/*.py      # Compile
python -m black pure3270/               # Format
python -m flake8 pure3270/              # Lint (MUST PASS)
python run_full_ci.py                   # Full CI
```

## Related Documentation

- **Architecture**: `docs/architecture/architecture.md`
- **Contributing**: `CONTRIBUTING.md`, `docs/guides/CONTRIBUTING.md`
- **CI Setup**: `.github/workflows/ci.yml`, `run_full_ci.py`, `CI_README.md`
- **Security**: `.github/instructions/security-and-owasp.instructions.md`
- **Task Implementation**: `.github/instructions/task-implementation.instructions.md`

## AI Agent Tips

### What Works Well
- RFC-first implementation approach
- Zero-dependency philosophy
- Comprehensive test suite (1,105+ tests)
- Memory Bank for context preservation
- Quick smoke test for rapid validation

### What to Avoid
- Adding macro DSL (permanently removed)
- Hardcoding protocol values
- Mixing sync/async patterns
- Manual EBCDIC translation
- Skipping linting checks

### Preferred Patterns
- Context managers for resource cleanup
- Specific exceptions over generic
- Constants over literals
- Async patterns internally
- RFC compliance over legacy quirks
