# Pure3270: Pure Python 3270 Terminal Emulation Library

![PyPI version](https://img.shields.io/pypi/v/pure3270)
![Python versions](https://img.shields.io/pypi/pyversions/pure3270)
![License](https://img.shields.io/github/license/dtg01100/pure3270)

[![CI](https://github.com/dtg01100/pure3270/actions/workflows/ci.yml/badge.svg)](https://github.com/dtg01100/pure3270/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/github/actions/coverage/dtg01100/pure3270/main)](https://dtg01100.github.io/pure3270/)
[![Static Analysis](https://github.com/dtg01100/pure3270/actions/workflows/static-analysis.yml/badge.svg)](https://github.com/dtg01100/pure3270/actions/workflows/static-analysis.yml)

Pure3270 is a self-contained, pure Python 3.10+ implementation of a 3270 terminal emulator, designed to emulate the functionality of the `s3270` terminal emulator. It integrates seamlessly with the `p3270` library through runtime monkey-patching, allowing you to replace `p3270`'s dependency on the external `s3270` binary without complex setup. The library uses standard asyncio for networking with no external telnet dependencies and supports TN3270 and TN3270E protocols, full 3270 emulation (screen buffer, fields, keyboard simulation), and optional SSL/TLS.

New in recent builds: optional negotiation trace recorder for deterministic inspection of Telnet/TN3270E negotiation (see "Negotiation Trace Recorder").

## Table of Contents

- [What's New in v0.2.1](#whats-new-in-v021)
- [Installation](#installation)
    - [Create and Activate Virtual Environment](#1-create-and-activate-virtual-environment)
    - [Install Pure3270](#2-install-pure3270)
    - [Development Container (DevContainer)](#development-container-devcontainer)
    - [Development Dependencies](#development-dependencies)
    - [Pre-commit Hooks](#pre-commit-hooks)
- [Documentation](#documentation)
- [Exports](#exports)
    - [Quick Start Snippets](#quick-start-snippets)
- [Usage](#usage)
    - [Patching p3270 for Seamless Integration](#patching-p3270-for-seamless-integration)
    - [Standalone Usage](#standalone-usage)
        - [Synchronous Usage](#synchronous-usage)
        - [Asynchronous Usage](#asynchronous-usage)
        - [Negotiation Trace Recorder](#negotiation-trace-recorder)
- [API Reference](#api-reference)
- [Testing](#testing)
    - [Running Tests](#running-tests)
    - [Coverage Reports](#coverage-reports)
- [CI Setup](#ci-setup)
- [Contribution Guidelines](#contribution-guidelines)
- [Migration Guide from s3270 / p3270](#migration-guide-from-s3270--p3270)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Credits](#credits)
- [License and Contributing](#license-and-contributing)

## What's New in v0.2.1

This release marks a significant milestone with the completion of all high and medium priority features. Key enhancements include:

- **Complete s3270 Compatibility**: Implementation of all missing s3270 actions including Compose(), Cookie(), Expect(), and Fail()
- **Full AID Support**: Complete support for all PA (1-3) and PF (1-24) keys
- **Async Refactor**: Complete async refactor with `AsyncSession` supporting connect and managed context
- **Protocol Enhancements**: Complete TN3270E protocol support with printer session capabilities
- **Enhanced Field Handling**: Improved field attribute handling and modification tracking for RMF/RMA commands

Important: Macro scripting/DSL has been removed and will not be reintroduced. Pull requests adding macro DSL will be declined.

For detailed release notes, see [RELEASE_NOTES.md](RELEASE_NOTES.md).

## Scope and Limitations

Macro mode is out of scope for this project and will not be implemented. It was removed and will not be reintroduced.

Key features:
- **Zero-configuration opt-in**: Call [`enable_replacement()`](pure3270/__init__.py) to patch `p3270` automatically.
- **Standalone usage**: Use `Session` or `AsyncSession` directly without `p3270`.
- **Pythonic API**: Context managers, async support, and structured error handling.
- **Compatibility**: Mirrors `s3270` and `p3270` interfaces with enhancements.

For architecture details, see [`architecture.md`](architecture.md).

## Installation

Pure3270 now requires Python 3.10 or later. It is recommended to use a virtual environment for isolation.

### 1. Create and Activate Virtual Environment

Create a virtual environment in your project directory:
```
python -m venv .venv
```

Activate it:
- On Unix/macOS:
  ```
  source .venv/bin/activate
  ```
- On Windows:
  ```
  .venv\Scripts\activate
  ```

### 2. Install Pure3270

No external dependencies are required beyond the Python standard library for core usage.

For development (editable install):
```
pip install -e .
```

For distribution (from source):
```
pip install .
```

This uses the existing [`setup.py`](setup.py), which specifies no external dependencies. Deactivate the venv with `deactivate` when done.

### Development Container (DevContainer)

For the most seamless development experience, use the included devcontainer configuration. This provides a fully configured development environment with all dependencies pre-installed.

#### Requirements
- [Visual Studio Code](https://code.visualstudio.com/)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

#### Setup
1. Open the project in VS Code
2. When prompted, click "Reopen in Container" or use Command Palette: `Dev Containers: Reopen in Container`
3. The container will automatically install all dependencies and development tools

The devcontainer includes:
- Python 3.12 environment
- All development dependencies (pytest, black, flake8, etc.)
- Pre-configured linting and formatting tools
- Ready-to-use development environment

For more information, see [`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json).

### Development Dependencies

For testing and linting, install additional tools:
```
pip install pytest-cov black flake8
```
- `pytest-cov`: For coverage reporting (e.g., `pytest --cov=pure3270`).
- `black`: For code formatting (e.g., `black .`).
- `flake8`: For linting (e.g., `flake8 .`).

### Pre-commit Hooks

To maintain code quality and consistency, Pure3270 uses pre-commit hooks. These hooks automatically check and format code before each commit.

To set up pre-commit hooks:

```
# Install pre-commit (already included in test dependencies)
pip install -e .[test]

# Install the Git hook scripts
pre-commit install
```

The hooks will now run automatically on each `git commit`. You can also run them manually:

```
# Run all hooks on all files
pre-commit run --all-files
```

For more information about pre-commit hooks, see [PRE_COMMIT_HOOKS.md](PRE_COMMIT_HOOKS.md).

## Documentation

Pure3270 includes comprehensive API documentation built with Sphinx. The documentation covers all public APIs and provides usage examples.

### Building Documentation

To build the documentation locally:

```bash
# Install documentation dependencies
pip install -e .[docs]

# Build HTML documentation
./build_docs.sh
```

The documentation will be available in `docs/build/html/index.html`.

### Online Documentation

Online documentation is available at [https://dtg01100.github.io/pure3270/](https://dtg01100.github.io/pure3270/).

## Exports

The main classes and functions are exported from the top-level module for easy import. From [`pure3270/__init__.py`](pure3270/__init__.py):

```python
from pure3270 import Session, AsyncSession, enable_replacement
```

### Quick Start Snippets

**Enable Patching:**
```python
import pure3270
pure3270.enable_replacement()  # Patches p3270 for seamless integration
```

**Synchronous Session:**
```python
from pure3270 import Session

with Session() as session:
    session.connect('your-host.example.com', port=23, ssl_context=None)
    session.key('Enter')
    print(session.ascii(session.read()))
```

**Asynchronous Session:**
```python
import asyncio
from pure3270 import AsyncSession

async def main():
    async with AsyncSession() as session:
        await session.connect('your-host.example.com', port=23, ssl=False)
        await session.send(b'key Enter')
        print(await session.read())

asyncio.run(main())
```

## Usage

### Patching p3270 for Seamless Integration

To replace `p3270`'s `s3270` dependency with pure3270:
1. Install `p3270` in your venv: `pip install p3270`.
2. Enable patching before importing `p3270`.

Example:
```python
import pure3270
pure3270.enable_replacement()  # Applies global patches to p3270

import p3270
session = p3270.P3270Client()  # Now uses pure3270 under the hood
session.connect('your-host.example.com', port=23, ssl=False)
session.send(b'key Enter')
screen_text = session.ascii(session.read())
print(screen_text)
session.close()
```

This redirects `p3270.P3270Client` methods (`__init__`, `connect`, `send`, `read`) to pure3270 equivalents. Logs will indicate patching success.

### Standalone Usage

Use pure3270 directly without `p3270`.

#### Synchronous Usage

From [`pure3270/session.py`](pure3270/session.py:149):
```python
from pure3270 import Session

session = Session()
try:
    session.connect('your-host.example.com', port=23, ssl_context=None)
    session.key('Enter')
    print(session.ascii(session.read()))
finally:
    session.close()
```

Important: Macro scripting/DSL has been removed and will not be reintroduced. PRs proposing its return will not be accepted.

#### Asynchronous Usage

From [`pure3270/session.py`](pure3270/session.py:39), `AsyncSession` provides async support for non-blocking operations.

**Basic Connection and Send:**
```python
import asyncio
from pure3270 import AsyncSession

async def main():
    async with AsyncSession() as session:
        await session.connect('your-host.example.com', port=23, ssl_context=None)
        await session.key('Enter')
        print(session.ascii(await session.read()))

asyncio.run(main())
```

### Negotiation Trace Recorder

For debugging negotiation flows (Telnet DO/WILL/DONT/WONT, TN3270E device/function exchanges, fallbacks, timeouts) enable the built-in lightweight trace recorder.

Enable it via the `enable_trace` flag on `Session` / `AsyncSession`:

```python
from pure3270 import Session

session = Session(enable_trace=True)
session.connect('host.example.com', 23)
# ... perform operations / initial negotiation happens during connect ...
events = session.get_trace_events()
for e in events:
    print(e.kind, e.details)
session.close()
```

Async variant:

```python
import asyncio
from pure3270 import AsyncSession

async def main():
    async with AsyncSession(enable_trace=True) as s:
        await s.connect('host.example.com', 23)
        # Inspect negotiation events
        for e in s.get_trace_events():
            print(f"{e.kind}: {e.details}")

asyncio.run(main())
```

Event kinds currently recorded:

- `telnet` – Incoming/outgoing Telnet option commands (fields: direction, command, option)
- `subneg` – Raw subnegotiation payloads (fields: option, length, preview)
- `decision` – Final mode decision or fallback (fields: requested, chosen, fallback_used)
- `error` – Negotiation errors/timeouts/refusals (fields: message)

The recorder is inert when disabled (single conditional branch), so leaving it off in production has negligible overhead.

You can serialize the event list manually if needed:

```python
import json
json_payload = json.dumps([{'kind': e.kind, **e.details, 'ts': e.ts} for e in session.get_trace_events()], indent=2)
```

Future enhancements may add richer structured field tracing and export helpers.


**Using Managed Context:**
The `managed` context manager ensures proper session lifecycle:
```python
import asyncio
from pure3270 import AsyncSession

async def main():
    session = AsyncSession()
    async with session.managed():
        await session.connect('your-host.example.com', port=23, ssl_context=None)
        await session.key('Enter')
        print(session.ascii(await session.read()))
    # Session is automatically closed here

asyncio.run(main())
```

**Handling Errors:**
Use try-except for robust error handling:
```python
import asyncio
from pure3270 import AsyncSession, SessionError

async def main():
    try:
        async with AsyncSession() as session:
            await session.connect('your-host.example.com', port=23, ssl_context=None)
            await session.key('Enter')
            print(session.ascii(await session.read()))
    except SessionError as e:
        print(f"Session error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

asyncio.run(main())
```

See the `examples/` directory for runnable scripts demonstrating these patterns.

## API Reference

### enable_replacement()

Top-level function to apply monkey patches to `p3270` for transparent integration.

From [`pure3270/patching/patching.py`](pure3270/patching/patching.py:216):
```
def enable_replacement(
    patch_sessions: bool = True,
    patch_commands: bool = True,
    strict_version: bool = False
) -> MonkeyPatchManager:
    """
    Top-level API for zero-configuration opt-in patching.

    Applies global patches to p3270 for seamless pure3270 integration.
    Supports selective patching and fallback detection.

    :param patch_sessions: Patch session initialization and methods (default True).
    :param patch_commands: Patch command execution (default True).
    :param strict_version: Raise error on version mismatch (default False).
    :return: The MonkeyPatchManager instance for manual control.
    :raises Pure3270PatchError: If strict and patching fails.
    """
```

Returns a `MonkeyPatchManager` for advanced control (e.g., `manager.unpatch()`).

### Session

Synchronous session handler for 3270 connections.

From [`pure3270/session.py`](pure3270/session.py:149):
```
class Session:
    """
    Synchronous 3270 session handler (wraps AsyncSession).
    """

    def __init__(self, host: Optional[str] = None, port: int = 23, ssl_context: Optional[Any] = None):
        """
        Initialize the Session.

        :param host: Hostname or IP.
        :param port: Port (default 23).
        :param ssl_context: SSL context for secure connections.
        """

    def connect(self, host: Optional[str] = None, port: Optional[int] = None, ssl_context: Optional[Any] = None) -> None:
        """
        Connect to the TN3270 host (sync).

        :param host: Hostname or IP.
        :param port: Port (default 23).
        :param ssl_context: SSL context for secure connections.
        :raises SessionError: If connection fails.
        """

    def send(self, data: bytes) -> None:
        """
        Send data to the host (sync).

        :param data: Data to send.
        :raises SessionError: If send fails.
        """

    def read(self, timeout: float = 5.0) -> bytes:
        """
        Read data from the host (sync).

        :param timeout: Read timeout in seconds.
        :return: Data received from host.
        :raises SessionError: If read fails.
        """

    def execute_macro(self, macro: str, vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Execute a macro (sync).

        :param macro: Macro to execute.
        :param vars: Variables for macro execution.
        :return: Macro execution results.
        """

    def close(self) -> None:
        """
        Close the session (sync).
        """

    @property
    def connected(self) -> bool:
        """
        Check if connected.
        """
```

Supports context manager: `with Session() as session: ...` (auto-closes on exit).

Additional properties:
- `tn3270_mode: bool` - Check if TN3270 mode is active.
- `tn3270e_mode: bool` - Check if TN3270E mode is active.
- `lu_name: Optional[str]` - Get the bound LU name.

### New s3270 Actions (High/Medium Priority Items)

Additional methods added for enhanced s3270 compatibility:

- `pf(self, n: int) -> None`: Send PF (Program Function) key (1-24).
- `pa(self, n: int) -> None`: Send PA (Program Attention) key (1-3).
- `compose(self, text: str) -> None`: Compose special characters or key combinations.
- `cookie(self, cookie_string: str) -> None`: Set HTTP cookie for web-based emulators.
- `expect(self, pattern: str, timeout: float = 10.0) -> bool`: Wait for a pattern to appear on screen.
- `fail(self, message: str) -> None`: Cause script to fail with a message.

### AsyncSession

Asynchronous 3270 session handler.

From [`pure3270/session.py`](pure3270/session.py:39):
```
class AsyncSession:
    """Asynchronous 3270 session handler."""

    def __init__(
        self, host: Optional[str] = None, port: int = 23, ssl_context: Optional[Any] = None
    ):
        """
        Initialize the AsyncSession.

        :param host: Hostname or IP.
        :param port: Port (default 23).
        :param ssl_context: SSL context for secure connections.
        """

    async def connect(
        self, host: Optional[str] = None, port: Optional[int] = None, ssl_context: Optional[Any] = None
    ) -> None:
        """
        Connect to the TN3270 host.

        :param host: Hostname or IP.
        :param port: Port (default 23).
        :param ssl_context: SSL context for secure connections.
        :raises SessionError: If connection fails.
        """

    async def send(self, data: bytes) -> None:
        """
        Send data to the host.

        :param data: Data to send.
        :raises SessionError: If send fails.
        """

    async def read(self, timeout: float = 5.0) -> bytes:
        """
        Read data from the host.

        :param timeout: Read timeout in seconds.
        :return: Data received from host.
        :raises SessionError: If read fails.
        """

    async def execute_macro(self, macro: str, vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Execute a macro.

        :param macro: Macro to execute.
        :param vars: Variables for macro execution.
        :return: Macro execution results.
        """

    async def close(self) -> None:
        """Close the session."""

    @property
    def connected(self) -> bool:
        """Check if connected."""

    @asynccontextmanager
    async def managed(self):
        """Context manager for the session."""
```

Supports async context manager: `async with session.managed(): ...` (auto-closes on exit).

Additional properties:
- `tn3270_mode: bool` - Check if TN3270 mode is active.
- `tn3270e_mode: bool` - Check if TN3270E mode is active.
- `lu_name: Optional[str]` - Get the bound LU name.

### Other Exports

- `setup_logging(level: str = "INFO")`: Configure logging for the library.
- Exceptions: `Pure3270Error`, `SessionError`, `ProtocolError`, `NegotiationError`, `ParseError`, `Pure3270PatchError`.

For full details, refer to the source code or inline docstrings.

## Testing

Pure3270 includes comprehensive tests in the `tests/` directory, enhanced with edge cases for async operations, protocol handling, and patching.

### Running Tests

Install dev dependencies (see Installation). Then:
```
pytest tests/
```

### Memory Limiting

Tests can be run with memory limits to prevent excessive memory usage and detect memory leaks. See [MEMORY_LIMITING.md](MEMORY_LIMITING.md) for details.

### Coverage Reports

You can generate local coverage reports without using external services:

```bash
# Terminal report
pytest --cov=pure3270

# HTML report (creates interactive report in htmlcov/ directory)
pytest --cov=pure3270 --cov-report=html

# Detailed terminal report showing line numbers missing coverage
pytest --cov=pure3270 --cov-report=term-missing

# XML report (useful for CI/CD integration)
pytest --cov=pure3270 --cov-report=xml
```

You can also combine multiple report formats:
```bash
pytest --cov=pure3270 --cov-report=html --cov-report=term-missing
```

For linting:
```
black . --check
flake8 .
```

### CI Setup

This project uses GitHub Actions for continuous integration. The workflows are defined in `.github/workflows/`:

1. `python-package.yml` - Runs tests and linting across multiple Python versions
2. `reports.yml` - Generates and publishes coverage and linting reports
3. `python-publish.yml` - Publishes releases to PyPI

Reports are automatically generated on each push and pull request. Coverage reports are published to [GitHub Pages](https://dtg01100.github.io/pure3270/) for easy access.

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
    python-version: 3.10
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[dev]
    - name: Run tests with coverage
      run: pytest tests/ --cov=pure3270 --cov-report=xml --cov-report=html
    - name: Lint
      run: |
        black . --check
        flake8 .
    - name: Archive code coverage results
      uses: actions/upload-artifact@v4
      with:
        name: coverage-report
        path: htmlcov/
```

This runs tests, coverage, and linting on push/PR without requiring external coverage services. Coverage reports are uploaded as artifacts and published to GitHub Pages for the main branch.

## Contribution Guidelines

Contributions are welcome! Please follow these steps:

1. Fork the repository and create a feature branch.
2. Install dev dependencies and run tests/linting locally.
3. Make changes and add tests for new features.
4. Ensure code passes `black` formatting and `flake8` linting.
5. Submit a pull request with a clear description of changes.

See the tests for examples. For major changes, open an issue first.

## Migration Guide from s3270 / p3270

Pure3270 replaces the binary `s3270` dependency in `p3270` setups, eliminating the need for external installations (e.g., no compiling or downloading `s3270` binaries).

### Key Changes

- **Binary Replacement via Patching**: Call `pure3270.enable_replacement()` before importing `p3270`. This monkey-patches `p3270.P3270Client` to delegate to pure3270's `Session`, handling connections, sends, and reads internally using standard asyncio instead of spawning `s3270` processes.
- **Zero-Config Opt-In**: No changes to your `p3270` code required. The patching is global by default but reversible.
- **Handling Mismatches**:
  - If `p3270` version doesn't match (e.g., !=0.1.6, as checked in patches), logs a warning and skips patches gracefully (no error unless `strict_version=True`).
  - If `p3270` is not installed, patching simulates with mocks and logs a warning; use standalone `pure3270.Session` instead.
  - Protocol differences: Pure3270 uses pure Python telnet/SSL, so ensure hosts support TN3270/TN3270E (RFC 1576/2355). SSL uses Python's `ssl` module.

### Before / After

**Before (with s3270)**:
- Install `s3270` binary.
- `import p3270; session = p3270.P3270Client(); session.connect(...)` (spawns s3270).

**After (with pure3270)**:
- Install pure3270 as above.
- `import pure3270; pure3270.enable_replacement(); import p3270; session = p3270.P3270Client(); session.connect(...)` (uses pure Python emulation).

Test migration by checking logs for "Patched Session ..." messages. For standalone scripts, switch to `from pure3270 import Session`.

## Examples

See the [`examples/`](examples/) directory for practical scripts:
- [`example_patching.py`](examples/example_patching.py): Demonstrates applying patches and verifying redirection.
- [`example_end_to_end.py`](examples/example_end_to_end.py): Full p3270 usage after patching (with mock host).
- [`example_standalone.py`](examples/example_standalone.py): Direct pure3270 usage without p3270.

Run them in your activated venv: `python examples/example_patching.py`. Replace mock hosts with real TN3270 servers (e.g., IBM z/OS systems) for production.

## Troubleshooting

- **Venv Activation Issues**: Ensure the venv is activated (prompt shows `(.venv)`). On Windows, use `Scripts\activate.bat`. If `pip` installs globally, recreate the venv.
- **Patching Fails**: Check logs for version mismatches (e.g., `p3270` !=0.1.6). Set `strict_version=True` to raise errors. If `p3270` absent, use standalone mode.
- **Connection/Protocol Errors**: Verify host/port (default 23/992 for SSL). Enable DEBUG logging: `pure3270.setup_logging('DEBUG')`. Common: Host doesn't support TN3270; test with tools like `tn3270` client.
- **Screen Read Issues**: Ensure `read()` is called after `send()`. For empty screens, check if BIND negotiation succeeded (logs show).
- **Async/Sync Mix**: Use `Session` for sync code; `AsyncSession` for async. Don't mix in the same script without `asyncio.run()`.

For more, enable verbose logging or consult [`architecture.md`](architecture.md).

## Credits

Credits: Some tests and examples in this project are inspired by and adapted from the IBM s3270 terminal emulator project, which served as a valuable reference for 3270 protocol handling and emulation techniques.

## License and Contributing

See [`setup.py`](setup.py) for author info. Contributions welcome via issues/PRs.
