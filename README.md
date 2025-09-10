# Pure3270: Pure Python 3270 Terminal Emulation Library

[![Coverage Status](https://coveralls.io/repos/github/dlafreniere/pure3270/badge.svg?branch=main)](https://coveralls.io/github/dlafreniere/pure3270?branch=main)
[![Linting](https://img.shields.io/badge/linting-pass-brightgreen)](https://img.shields.io/badge/linting-pass-brightgreen)

Pure3270 is a self-contained, pure Python 3.8+ implementation of a 3270 terminal emulator, designed to emulate the functionality of the `s3270` terminal emulator. It integrates seamlessly with the `p3270` library through runtime monkey-patching, allowing you to replace `p3270`'s dependency on the external `s3270` binary without complex setup. The library uses standard asyncio for networking with no external telnet dependencies and supports TN3270 and TN3270E protocols, full 3270 emulation (screen buffer, fields, keyboard simulation), and optional SSL/TLS.

## What's New in v0.2.0

This release marks a significant milestone with the completion of all high and medium priority features. Key enhancements include:

- **Complete s3270 Compatibility**: Implementation of all missing s3270 actions including Compose(), Cookie(), Expect(), and Fail()
- **Full AID Support**: Complete support for all PA (1-3) and PF (1-24) keys
- **Async Refactor**: Complete async refactor with `AsyncSession` supporting connect, macro execution, and managed context
- **Protocol Enhancements**: Complete TN3270E protocol support with printer session capabilities
- **Enhanced Field Handling**: Improved field attribute handling and modification tracking for RMF/RMA commands
- **Comprehensive Macro Support**: Advanced macro execution with conditional branching and variable substitution

For detailed release notes, see [RELEASE_NOTES.md](RELEASE_NOTES.md).

Key features:
- **Zero-configuration opt-in**: Call [`enable_replacement()`](pure3270/__init__.py) to patch `p3270` automatically.
- **Standalone usage**: Use `Session` or `AsyncSession` directly without `p3270`.
- **Pythonic API**: Context managers, async support, and structured error handling.
- **Compatibility**: Mirrors `s3270` and `p3270` interfaces with enhancements.

For architecture details, see [`architecture.md`](architecture.md).

## Installation

Pure3270 requires Python 3.8 or later. It is recommended to use a virtual environment for isolation.

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

### Development Dependencies

For testing and linting, install additional tools:
```
pip install pytest-cov black flake8
```
- `pytest-cov`: For coverage reporting (e.g., `pytest --cov=pure3270`).
- `black`: For code formatting (e.g., `black .`).
- `flake8`: For linting (e.g., `flake8 .`).

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
    session.connect('your-host.example.com', port=23, ssl=False)
    session.send(b'key Enter')
    print(session.read())
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
screen_text = session.read()
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
    session.connect('your-host.example.com', port=23, ssl=False)
    session.send(b'key Enter')
    print(session.read())
finally:
    session.close()
```

Supports macros:
```python
session.execute_macro('String(hello);key Enter')
```

#### Asynchronous Usage

From [`pure3270/session.py`](pure3270/session.py:39), `AsyncSession` provides async support for non-blocking operations.

**Basic Connection and Send:**
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

**Executing Macros:**
```python
import asyncio
from pure3270 import AsyncSession

async def main():
    async with AsyncSession() as session:
        await session.connect('your-host.example.com', port=23, ssl=False)
        await session.execute_macro('String(hello);key Enter')
        print(await session.read())

asyncio.run(main())
```

**Using Managed Context:**
The `managed` context manager ensures proper session lifecycle:
```python
import asyncio
from pure3270 import AsyncSession

async def main():
    session = AsyncSession()
    async with session.managed():
        await session.connect('your-host.example.com', port=23, ssl=False)
        await session.send(b'key Enter')
        print(await session.read())
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
            await session.connect('your-host.example.com', port=23, ssl=False)
            await session.send(b'key Enter')
            print(await session.read())
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
pytest tests/ --cov=pure3270 --cov-report=html
```
This generates coverage reports and HTML output in `htmlcov/`.

For linting:
```
black . --check
flake8 .
```

### CI Setup

To automate testing and linting, set up GitHub Actions. Create `.github/workflows/ci.yml`:

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
        python-version: 3.8
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[dev]
    - name: Run tests
      run: pytest tests/ --cov=pure3270 --cov-report=xml
    - name: Lint
      run: |
        black . --check
        flake8 .
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

This runs tests, coverage, and linting on push/PR. Badges can be generated via services like Shields.io or Codecov for integration into the README.

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
  - If `p3270` version doesn't match (e.g., !=0.3.0, as checked in patches), logs a warning and skips patches gracefully (no error unless `strict_version=True`).
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
- **Patching Fails**: Check logs for version mismatches (e.g., `p3270` !=0.3.0). Set `strict_version=True` to raise errors. If `p3270` absent, use standalone mode.
- **Connection/Protocol Errors**: Verify host/port (default 23/992 for SSL). Enable DEBUG logging: `pure3270.setup_logging('DEBUG')`. Common: Host doesn't support TN3270; test with tools like `tn3270` client.
- **Screen Read Issues**: Ensure `read()` is called after `send()`. For empty screens, check if BIND negotiation succeeded (logs show).
- **Async/Sync Mix**: Use `Session` for sync code; `AsyncSession` for async. Don't mix in the same script without `asyncio.run()`.

For more, enable verbose logging or consult [`architecture.md`](architecture.md).

## Credits

Credits: Some tests and examples in this project are inspired by and adapted from the IBM s3270 terminal emulator project, which served as a valuable reference for 3270 protocol handling and emulation techniques.

## License and Contributing

See [`setup.py`](setup.py) for author info. Contributions welcome via issues/PRs.