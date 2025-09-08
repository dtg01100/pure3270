# Pure3270: Pure Python 3270 Terminal Emulation Library

Pure3270 is a self-contained, pure Python 3.8+ implementation of a 3270 terminal emulator, designed to emulate the functionality of the `s3270` terminal emulator. It integrates seamlessly with the `p3270` library through runtime monkey-patching, allowing you to replace `p3270`'s dependency on the external `s3270` binary without complex setup. The library uses standard asyncio for networking with no external telnet dependencies and supports TN3270 and TN3270E protocols, full 3270 emulation (screen buffer, fields, keyboard simulation), and optional SSL/TLS.

Key features:
- **Zero-configuration opt-in**: Call [`pure3270.enable_replacement()`](pure3270/__init__.py) to patch `p3270` automatically.
- **Standalone usage**: Use `Session` directly without `p3270`.
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
No external dependencies are required beyond the Python standard library.

For development (editable install):
```
pip install -e .
```

For distribution (from source):
```
pip install .
```

This uses the existing [`setup.py`](setup.py), which specifies no external dependencies. Deactivate the venv with `deactivate` when done.

## Quick Start and Usage Patterns

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
session.send('key Enter')
screen_text = session.read()
print(screen_text)
session.close()
```

This redirects `p3270.P3270Client` methods (`__init__`, `connect`, `send`, `read`) to pure3270 equivalents. Logs will indicate patching success.

### Standalone Usage
Use pure3270 directly without `p3270`:
```python
from pure3270 import Session

with Session() as session:
    session.connect('your-host.example.com', port=23, ssl=False)
    session.send('key PF3')
    screen_text = session.read()
    print(screen_text)
```

Supports macros:
```python
session.macro(['String(hello)', 'key Enter'])
```

For async usage, see the examples below.

#### Synchronous Example
```python
from pure3270 import Session

session = Session()
try:
    session.connect('your-host.example.com', port=23, ssl=False)
    session.send('key Enter')
    print(session.read())
finally:
    session.close()
```

#### Asynchronous Example
```python
import asyncio
from pure3270 import AsyncSession

async def main():
    async with AsyncSession() as session:
        await session.connect('your-host.example.com', port=23, ssl=False)
        await session.send('key Enter')
        print(await session.read())

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
    
    def __init__(self, rows: int = 24, cols: int = 80, force_3270: bool = False):
        """
        Initialize the Session.
        
        :param rows: Screen rows (default 24).
        :param cols: Screen columns (default 80).
        :param force_3270: Force TN3270 mode without negotiation (for testing).
        """

    def connect(self, host: str, port: int = 23, ssl: bool = False) -> None:
        """
        Connect to the TN3270 host (sync).
        
        :param host: Hostname or IP.
        :param port: Port (default 23).
        :param ssl: Use SSL/TLS if True.
        :raises SessionError: If connection fails.
        """

    def send(self, command: str) -> None:
        """
        Send a command or key (sync).
        
        :param command: Command or key (e.g., "key Enter", "String(hello)").
        :raises SessionError: If send fails.
        """

    def read(self) -> str:
        """
        Read the current screen content (sync).
        
        :return: Screen text as string.
        :raises SessionError: If read fails.
        """

    def macro(self, sequence: Sequence[str]) -> None:
        """
        Execute a macro sequence (sync).
        
        :param sequence: List of commands.
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

### AsyncSession
Asynchronous 3270 session handler.

From [`pure3270/session.py`](pure3270/session.py:39):
```
class AsyncSession:
    """Asynchronous 3270 session handler."""

    def __init__(
        self, rows: int = 24, cols: int = 80, force_3270: bool = False
    ):
        """
        Initialize the AsyncSession.

        :param rows: Screen rows (default 24).
        :param cols: Screen columns (default 80).
        :param force_3270: Force TN3270 mode without negotiation (for testing).
        """

    async def connect(
        self, host: str, port: int = 23, ssl: bool = False
    ) -> None:
        """
        Connect to the TN3270 host.

        :param host: Hostname or IP.
        :param port: Port (default 23).
        :param ssl: Use SSL/TLS if True.
        :raises SessionError: If connection fails.
        """

    async def send(self, command: str) -> None:
        """
        Send a command or key to the host.

        :param command: Command or key (e.g., "key Enter", "String(hello)").
        :raises SessionError: If send fails.
        """

    async def read(self) -> str:
        """
        Read the current screen content.

        :return: Screen text as string.
        :raises SessionError: If read fails.
        """

    async def macro(self, sequence: Sequence[str]) -> None:
        """
        Execute a macro sequence of commands.

        :param sequence: List of commands.
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