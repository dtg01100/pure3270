# Mock Server Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `mock_server/tn3270_mock_server.py` into a comprehensive TN3270 test server framework with multiple scenario types, TLS support, realistic 3270 data streams, and x3270 target integration.

**Architecture:** Scenario-based server using async Python. Each scenario is a class extending a base server with configurable via dataclass. Scenarios registered in a dict for CLI lookup. Screen builders construct realistic 3270 data streams for menu screens.

**Tech Stack:** Python 3.10+, asyncio, ssl, dataclasses

---

## File Structure

```
mock_server/
  __init__.py              # Create: re-exports, ServerConfig
  tn3270_mock_server.py    # Modify: refactor with registry, CLI, backward compat
  screen_builders.py        # Create: 3270 data stream builders
  tls_certs.py              # Create: embedded TLS cert/key
  scenarios/
    __init__.py            # Create: scenario registry dict
    echo.py                # Create: EchoServer
    negotiation_failure.py # Create: NegotiationFailureServer
    menu_nvt.py            # Create: MenuNVTServer
    menu_3270.py           # Create: Menu3270Server
    menu_tn3270e.py        # Create: MenuTN3270EServer (current EnhancedTN3270MockServer)
    menu_sscp_lu.py        # Create: MenuSSCP_LUServer
    color.py               # Create: ColorServer
    tn3270_only.py         # Create: TN3270OnlyServer
```

**Modify:**
- `tests/test_enhanced_mock_server.py` - Update imports to use new scenario classes

---

## Task 1: Create mock_server Directory Structure and Re-exports

**Files:**
- Create: `mock_server/__init__.py`
- Create: `mock_server/scenarios/__init__.py`

- [ ] **Step 1: Create mock_server/__init__.py**

```python
"""Mock TN3270 server for testing pure3270."""

from dataclasses import dataclass
from typing import Optional

# Re-export main classes for backwards compatibility
from mock_server.tn3270_mock_server import (
    TN3270MockServer,
    EnhancedTN3270MockServer,
)

# Re-export config
from mock_server.tn3270_mock_server import ServerConfig

__all__ = [
    "TN3270MockServer",
    "EnhancedTN3270MockServer",
    "ServerConfig",
]
```

- [ ] **Step 2: Create mock_server/scenarios/__init__.py with empty registry**

```python
"""Scenario registry for mock TN3270 servers."""

from typing import Type

from mock_server.tn3270_mock_server import TN3270MockServer

SCENARIOS: dict[str, Type[TN3270MockServer]] = {}
```

- [ ] **Step 3: Commit**

```bash
git add mock_server/__init__.py mock_server/scenarios/__init__.py
git commit -m "feat(mock_server): create directory structure"
```

---

## Task 2: Refactor tn3270_mock_server.py with ServerConfig and Base Logic

**Files:**
- Modify: `mock_server/tn3270_mock_server.py`

- [ ] **Step 1: Add ServerConfig dataclass at top of file**

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

class TLSMode(Enum):
    NONE = "none"
    IMMEDIATE = "immediate"
    NEGOTIATED = "negotiated"

@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 0
    scenario: str = "enhanced"
    terminal_type: str = "IBM-3278-2-E"
    lu_name: str = "LUNAME01"
    functions_mode: str = "send"  # "send" | "request"
    tls_mode: TLSMode = TLSMode.NONE
```

- [ ] **Step 2: Update TN3270MockServer.__init__ to accept config**

Modify `__init__` to accept `config: ServerConfig | None = None` and store as `self.config`. Extract parameters from config if provided, falling back to current defaults for backward compat.

- [ ] **Step 3: Update EnhancedTN3270MockServer to use new structure**

Keep `EnhancedTN3270MockServer` working as-is but internally use config. Make it register with SCENARIOS dict.

- [ ] **Step 4: Add CLI argument parsing at bottom of file**

```python
def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="TN3270 Mock Server")
    parser.add_argument("--type", "-t", default="enhanced",
                        choices=list(SCENARIOS.keys()),
                        help="Scenario type")
    parser.add_argument("--port", "-p", type=int, default=0,
                        help="Port (0 for auto)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available scenarios")
    args = parser.parse_args()

    if args.list:
        print("Available scenarios:")
        for name in SCENARIOS:
            print(f"  {name}")
        return

    config = ServerConfig(
        host=args.host,
        port=args.port,
        scenario=args.type,
    )
    server = TN3270MockServer(config=config)
    # ... start server
```

- [ ] **Step 5: Test imports still work**

Run: `python -c "from mock_server import TN3270MockServer, EnhancedTN3270MockServer; print('OK')"`
Expected: OK

- [ ] **Step 6: Commit**

```bash
git add mock_server/tn3270_mock_server.py
git commit -m "feat(mock_server): add ServerConfig and CLI"
```

---

## Task 3: Create screen_builders.py with 3270 Data Stream Helpers

**Files:**
- Create: `mock_server/screen_builders.py`

- [ ] **Step 1: Create file with menu screen builder**

```python
"""3270 data stream builders for mock server scenarios."""

from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from pure3270.protocol.data_stream import SBA, SF, WCC, EW, EW干啥, RA, etc

def build_menu_screen(
    title: str,
    options: list[tuple[str, str]],
    width: int = 80,
) -> bytes:
    """Build a formatted 3270 menu screen.

    Args:
        title: Screen title (ASCII)
        options: List of (label, description) tuples

    Returns:
        Complete 3270 data stream bytes (WCC + orders + text + IAC EOR)
    """
    # WCC: keyboard reset, audible alarm, etc.
    wcc_byte = bytes([0x00])  # No special WCC flags

    # Build buffer starting with WCC
    buffer = bytearray(wcc_byte)

    # Title: position 0,0 and write
    row, col = 0, 0
    buffer.extend(build_sba(row, col))
    buffer.extend(translate_ascii_to_ebcdic(title))

    # Each option: row, protected field with description
    for i, (label, desc) in enumerate(options):
        row = 2 + i
        # SBA to position
        buffer.extend(build_sba(row, 0))
        # Start protected field
        buffer.extend(bytes([SF, 0xF0]))  # Protected, display-only attribute
        buffer.extend(translate_ascii_to_ebcdic(f"{label}: {desc}"))

    return bytes(buffer)

def build_sba(row: int, col: int) -> bytes:
    """Build SBA (Set Buffer Address) order for 12-bit addressing."""
    # 12-bit address encoding: high 6 bits in first byte, low 6 bits in second
    addr = (row * 80) + col  # Assuming 80 columns
    high = (addr >> 6) & 0x3F
    low = addr & 0x3F
    return bytes([SBA, high | 0x40, low | 0x40])  # 0x40 for telnet sync
```

- [ ] **Step 2: Add EW (Erase Write) order**

```python
EW = 0x0F

def build_erase_write() -> bytes:
    """Build EW order for full screen erase."""
    return bytes([EW])
```

- [ ] **Step 3: Test builder generates valid data stream**

```bash
python -c "
from mock_server.screen_builders import build_menu_screen
data = build_menu_screen('Test Menu', [('A', 'Option A'), ('B', 'Option B')])
print(f'Generated {len(data)} bytes')
print('First bytes:', hex(data[0]), hex(data[1]) if len(data) > 1 else '')
"
```

- [ ] **Step 4: Commit**

```bash
git add mock_server/screen_builders.py
git commit -m "feat(mock_server): add 3270 screen builders"
```

---

## Task 4: Create Echo and NegotiationFailure Scenarios

**Files:**
- Create: `mock_server/scenarios/echo.py`
- Create: `mock_server/scenarios/negotiation_failure.py`
- Modify: `mock_server/scenarios/__init__.py`

- [ ] **Step 1: Create echo.py**

```python
"""Echo server scenario - echoes received data."""

import asyncio
from pure3270.protocol.utils import IAC, WILL, TELOPT_EOR

class EchoServer(TN3270MockServer):
    """Simple echo server for protocol debugging."""

    async def handle_client(self, reader, writer):
        # Send WILL EOR
        writer.write(bytes([IAC, WILL, TELOPT_EOR]))
        await writer.drain()

        # Echo loop
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
```

- [ ] **Step 2: Create negotiation_failure.py**

```python
"""Negotiation failure scenario - refuses EOR."""

import asyncio
from pure3270.protocol.utils import IAC, WONT, TELOPT_EOR

class NegotiationFailureServer(TN3270MockServer):
    """Server that refuses EOR - tests error handling."""

    async def handle_client(self, reader, writer):
        writer.write(bytes([IAC, WONT, TELOPT_EOR]))
        await writer.drain()
        await asyncio.sleep(0.1)
        writer.close()
```

- [ ] **Step 3: Update scenarios/__init__.py**

```python
from mock_server.scenarios.echo import EchoServer
from mock_server.scenarios.negotiation_failure import NegotiationFailureServer

SCENARIOS: dict[str, Type[TN3270MockServer]] = {
    "echo": EchoServer,
    "negotiation_failure": NegotiationFailureServer,
}
```

- [ ] **Step 4: Test echo scenario**

```bash
python -c "
from mock_server.scenarios import SCENARIOS
print('Scenarios:', list(SCENARIOS.keys()))
s = SCENARIOS['echo']()
print('EchoServer created:', type(s).__name__)
"
```

- [ ] **Step 5: Commit**

```bash
git add mock_server/scenarios/echo.py mock_server/scenarios/negotiation_failure.py mock_server/scenarios/__init__.py
git commit -m "feat(mock_server): add echo and negotiation_failure scenarios"
```

---

## Task 5: Create MenuTN3270EServer (Current EnhancedTN3270MockServer Behavior)

**Files:**
- Create: `mock_server/scenarios/menu_tn3270e.py`
- Modify: `mock_server/scenarios/__init__.py`
- Modify: `mock_server/tn3270_mock_server.py` (make EnhancedTN3270MockServer an alias)

- [ ] **Step 1: Create menu_tn3270e.py**

```python
"""TN3270E menu server - full TN3270E negotiation with formatted menu."""

import asyncio
from pure3270.protocol.utils import (
    DO, IAC, SB, SE, WILL, TELOPT_EOR, TELOPT_TN3270E, TELOPT_TTYPE,
    TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS, TN3270E_IS, TN3270E_REQUEST,
    TN3270E_SEND, TTYPE_SEND, TN3270_DATA,
)
from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from pure3270.protocol.data_stream import SBA, SF
from pure3270.protocol.tn3270e_header import TN3270EHeader
from mock_server.tn3270_mock_server import TN3270MockServer

class MenuTN3270EServer(TN3270MockServer):
    """Menu server with full TN3270E negotiation.

    This is the primary test scenario - exercises full negotiation
    sequence and sends realistic 3270 data stream.
    """

    async def handle_client(self, reader, writer):
        # Implement full negotiation from EnhancedTN3270MockServer
        # (copy implementation from EnhancedTN3270MockServer.handle_client)
        # ...

        # After negotiation: send menu screen
        header = TN3270EHeader(
            data_type=TN3270_DATA,
            request_flag=0,
            response_flag=0,
            seq_number=1,
        ).to_bytes()

        menu_data = self.build_menu_stream()
        writer.write(header + menu_data)
        writer.write(bytes([IAC, TELOPT_EOR]))
        await writer.drain()

        # Keep alive
        try:
            while True:
                data = await asyncio.wait_for(reader.read(4096), timeout=30)
                if not data:
                    break
        except asyncio.TimeoutError:
            pass
```

- [ ] **Step 2: Update SCENARIOS in __init__.py**

```python
from mock_server.scenarios.menu_tn3270e import MenuTN3270EServer

SCENARIOS["menu_tn3270e"] = MenuTN3270EServer
SCENARIOS["enhanced"] = MenuTN3270EServer  # Backward compat
```

- [ ] **Step 3: Make EnhancedTN3270MockServer an alias**

In `tn3270_mock_server.py`, at the bottom:

```python
# Backward compatibility alias
EnhancedTN3270MockServer = MenuTN3270EServer
```

- [ ] **Step 4: Run existing test to verify**

```bash
python -m pytest tests/test_enhanced_mock_server.py -v
```

- [ ] **Step 5: Commit**

```bash
git add mock_server/scenarios/menu_tn3270e.py mock_server/scenarios/__init__.py mock_server/tn3270_mock_server.py
git commit -m "feat(mock_server): add MenuTN3270EServer as enhanced scenario"
```

---

## Task 6: Create Menu3270Server (TN3270 without E)

**Files:**
- Create: `mock_server/scenarios/menu_3270.py`
- Modify: `mock_server/scenarios/__init__.py`

- [ ] **Step 1: Create menu_3270.py**

```python
"""TN3270 (non-E) menu server - standard TN3270 negotiation."""

import asyncio
from pure3270.protocol.utils import (
    IAC, WILL, DO, SB, SE, TELOPT_EOR, TELOPT_TTYPE,
    TTYPE_SEND, TN3270_DATA,
)
from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from pure3270.protocol.data_stream import SBA, SF
from mock_server.tn3270_mock_server import TN3270MockServer

class Menu3270Server(TN3270MockServer):
    """Menu server using TN3270 (no E) protocol.

    Unlike TN3270E, this does not offer WILL TN3270E option.
    """

    async def handle_client(self, reader, writer):
        # 1. Offer TTYPE and EOR (no TN3270E)
        writer.write(bytes([IAC, WILL, TELOPT_TTYPE]))
        await writer.drain()
        writer.write(bytes([IAC, WILL, TELOPT_EOR]))
        await writer.drain()

        # 2. Request terminal type
        writer.write(bytes([IAC, SB, TELOPT_TTYPE, TTYPE_SEND, IAC, SE]))
        await writer.drain()

        # 3. Read client response
        try:
            term_resp = await asyncio.wait_for(
                reader.readuntil(bytes([IAC, SE])), timeout=1.5
            )
        except Exception:
            pass

        # 4. Send 3270 data stream (no TN3270E header)
        menu_data = self.build_menu_stream()
        writer.write(menu_data)
        writer.write(bytes([IAC, TELOPT_EOR]))
        await writer.drain()

        # Keep alive
        try:
            while True:
                data = await asyncio.wait_for(reader.read(4096), timeout=30)
                if not data:
                    break
        except asyncio.TimeoutError:
            pass
```

- [ ] **Step 2: Register in SCENARIOS**

```python
from mock_server.scenarios.menu_3270 import Menu3270Server
SCENARIOS["menu_3270"] = Menu3270Server
```

- [ ] **Step 3: Commit**

```bash
git add mock_server/scenarios/menu_3270.py mock_server/scenarios/__init__.py
git commit -m "feat(mock_server): add menu_3270 scenario"
```

---

## Task 7: Create MenuNVTServer (NVT Mode)

**Files:**
- Create: `mock_server/scenarios/menu_nvt.py`
- Modify: `mock_server/scenarios/__init__.py`

- [ ] **Step 1: Create menu_nvt.py**

```python
"""NVT mode menu server - plain TELNET without 3270."""

import asyncio
from pure3270.protocol.utils import (
    IAC, WILL, DO, TELOPT_EOR, TELOPT_BINARY,
)
from mock_server.tn3270_mock_server import TN3270MockServer

class MenuNVTServer(TN3270MockServer):
    """Menu server in NVT (character) mode.

    No 3270 negotiation - just plain TELNET with ASCII text.
    Useful for testing ASCII/VT100 fallback behavior.
    """

    async def handle_client(self, reader, writer):
        # Offer BINARY and EOR for NVT mode
        writer.write(bytes([IAC, WILL, TELOPT_BINARY]))
        await writer.drain()
        writer.write(bytes([IAC, WILL, TELOPT_EOR]))
        await writer.drain()

        # Send menu as plain ASCII text
        menu = "MAIN MENU\n"
        menu += "=========\n"
        menu += "A. Option A\n"
        menu += "B. Option B\n"
        menu += "C. Option C\n"
        menu += "\nSelect: "

        writer.write(menu.encode("ascii"))
        await writer.drain()

        # Echo input
        try:
            while True:
                data = await asyncio.wait_for(reader.read(1024), timeout=30)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except asyncio.TimeoutError:
            pass
```

- [ ] **Step 2: Register in SCENARIOS**

```python
SCENARIOS["menu_nvt"] = MenuNVTServer
```

- [ ] **Step 3: Commit**

```bash
git add mock_server/scenarios/menu_nvt.py mock_server/scenarios/__init__.py
git commit -m "feat(mock_server): add menu_nvt scenario"
```

---

## Task 8: Create MenuSSCP_LUServer

**Files:**
- Create: `mock_server/scenarios/menu_sscp_lu.py`
- Modify: `mock_server/scenarios/__init__.py`

- [ ] **Step 1: Create menu_sscp_lu.py**

```python
"""SSCP-LU mode menu server - TN3270E with SSCP-LU session."""

import asyncio
from pure3270.protocol.utils import (
    IAC, WILL, SB, SE, TELOPT_EOR, TELOPT_TN3270E, TN3270E_DEVICE_TYPE,
    TN3270E_FUNCTIONS, TN3270E_IS, TN3270_DATA,
)
from mock_server.tn3270_mock_server import TN3270MockServer

class MenuSSCP_LUServer(TN3270MockServer):
    """Menu server using TN3270E SSCP-LU mode.

    SSCP-LU is a sub-mode of TN3270E where the terminal behaves
    more like NVT line mode, gathering a line at a time.
    """

    # SSCP-LU data type would be 0x01 or similar in TN3270E header
    SSCP_LU_DATA = 0x02  # Need to verify correct constant

    async def handle_client(self, reader, writer):
        # Full TN3270E negotiation first
        writer.write(bytes([IAC, WILL, TELOPT_EOR]))
        writer.write(bytes([IAC, WILL, TELOPT_TN3270E]))
        await writer.drain()

        # Device-type negotiation with SSCP-LU indication
        # (implementation similar to MenuTN3270EServer)
        # ...

        # Send data with SSCP-LU data type
        # header = TN3270EHeader(data_type=self.SSCP_LU_DATA, ...)
        # ...
```

- [ ] **Step 2: Register in SCENARIOS**

```python
SCENARIOS["menu_sscp_lu"] = MenuSSCP_LUServer
```

- [ ] **Step 3: Commit**

```bash
git add mock_server/scenarios/menu_sscp_lu.py mock_server/scenarios/__init__.py
git commit -m "feat(mock_server): add menu_sscp_lu scenario"
```

---

## Task 9: Create ColorServer with Extended Attributes

**Files:**
- Create: `mock_server/scenarios/color.py`
- Modify: `mock_server/scenarios/__init__.py`

- [ ] **Step 1: Create color.py**

```python
"""Color display server - tests 3279 color and extended attributes."""

import asyncio
from pure3270.protocol.utils import (
    IAC, WILL, SB, SE, WILL, TELOPT_EOR, TELOPT_TN3270E, TN3270_DATA,
    TN3270E_DEVICE_TYPE, TN3270E_FUNCTIONS, TN3270E_IS,
)
from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from mock_server.tn3270_mock_server import TN3270MockServer

# Extended attributes
EA_COLOR = 0x41
EA_HIGHLIGHT = 0x42
EA_EABIT = 0x43

# Color values
COLOR_DEFAULT = 0x00
COLOR_RED = 0x01
COLOR_BLUE = 0x02
COLOR_GREEN = 0x03
COLOR_WHITE = 0x04

class ColorServer(TN3270MockServer):
    """Server that sends color/attribute display.

    Sends a screen demonstrating various 3279 color attributes
    and extended attribute types.
    """

    async def handle_client(self, reader, writer):
        # Full TN3270E negotiation
        # ...

        # Send color display screen
        # Uses SF with extended attributes:
        # - Field with color attribute
        # - Field with highlight attribute
        # - Field with EA_EABIT (extended highlighting)

        # Example:
        # SBA(row=0, col=0)
        # SF(0xF0 | 0x04)  # Protected + default color
        # text in default color
        # SBA(row=1, col=0)
        # SF(0xF0 | color_byte)  # With color attribute
        # ...
```

- [ ] **Step 2: Register in SCENARIOS**

```python
SCENARIOS["color"] = ColorServer
```

- [ ] **Step 3: Commit**

```bash
git add mock_server/scenarios/color.py mock_server/scenarios/__init__.py
git commit -m "feat(mock_server): add color scenario"
```

---

## Task 10: Create TN3270OnlyServer

**Files:**
- Create: `mock_server/scenarios/tn3270_only.py`
- Modify: `mock_server/scenarios/__init__.py`

- [ ] **Step 1: Create tn3270_only.py**

```python
"""TN3270-only server - refuses TN3270E, forces non-E negotiation."""

import asyncio
from pure3270.protocol.utils import (
    IAC, WILL, SB, SE, DO, TELOPT_EOR, TELOPT_TTYPE,
    TTYPE_SEND, TN3270_DATA,
)
from pure3270.emulation.ebcdic import translate_ascii_to_ebcdic
from mock_server.tn3270_mock_server import TN3270MockServer

class TN3270OnlyServer(TN3270MockServer):
    """Server that only supports TN3270, not TN3270E.

    This server explicitly does NOT offer WILL TN3270E,
    testing the client's fallback behavior.
    """

    async def handle_client(self, reader, writer):
        # Offer TTYPE and EOR only (no TN3270E)
        writer.write(bytes([IAC, WILL, TELOPT_TTYPE]))
        await writer.drain()
        writer.write(bytes([IAC, WILL, TELOPT_EOR]))
        await writer.drain()

        # Request terminal type
        writer.write(bytes([IAC, SB, TELOPT_TTYPE, TTYPE_SEND, IAC, SE]))
        await writer.drain()

        # Read response
        try:
            await asyncio.wait_for(reader.readuntil(bytes([IAC, SE])), timeout=1.5)
        except Exception:
            pass

        # Send 3270 data stream (no TN3270E header)
        # ...
```

- [ ] **Step 2: Register in SCENARIOS**

```python
SCENARIOS["tn3270_only"] = TN3270OnlyServer
```

- [ ] **Step 3: Commit**

```bash
git add mock_server/scenarios/tn3270_only.py mock_server/scenarios/__init__.py
git commit -m "feat(mock_server): add tn3270_only scenario"
```

---

## Task 11: Add TLS Support with Embedded Certs

**Files:**
- Create: `mock_server/tls_certs.py`
- Modify: `mock_server/tn3270_mock_server.py`

- [ ] **Step 1: Create tls_certs.py with self-signed cert**

```python
"""Embedded TLS certificates for testing."""

TLS_CERT = """-----BEGIN CERTIFICATE-----
MIIC5TCCAc2gAwIBAgIJANKjHJz5HG3kMA0GCSqGSIb3DQEBCwUAMBQxEjAQBgNV
BAMMCWxvY2FsaG9zdDAeFw0xOTEyMDEwODAwMDBaFw0xOTAyMTEwODAwMDBaMBQx
EjAQBgNVBAMMCWxvY2FsaG9zdDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoC
ggEBALBCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
-----END CERTIFICATE-----"""

TLS_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCwQCCCCCCCCCCC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
-----END PRIVATE KEY-----"""
```

- [ ] **Step 2: Add TLSMode to TN3270MockServer.handle_client**

In `TN3270MockServer`, add method `start_tls` that wraps socket with ssl.SSLContext using the embedded cert.

- [ ] **Step 3: Support TLS modes in server startup**

```python
async def _start_in_loop(self) -> None:
    if self.config.tls_mode == TLSMode.IMMEDIATE:
        # Wrap in TLS immediately
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.use_cert_chain_file(cert_path)  # or from tls_certs
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port, ssl=ctx
        )
    elif self.config.tls_mode == TLSMode.NEGOTIATED:
        # Start plain, upgrade later
        # ...
    else:
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
```

- [ ] **Step 4: Commit**

```bash
git add mock_server/tls_certs.py mock_server/tn3270_mock_server.py
git commit -m "feat(mock_server): add TLS support"
```

---

## Task 12: Add x3270 target Integration Helper

**Files:**
- Create: `mock_server/x3270_target.py`
- Modify: `mock_server/__init__.py`

- [ ] **Step 1: Create x3270_target.py**

```python
"""Helper for running x3270 target as subprocess."""

import subprocess
from pathlib import Path
from typing import Optional

def find_x3270_target() -> Optional[Path]:
    """Find x3270 target.py in Common/test/target."""
    # Check common locations
    locations = [
        Path("~/x3270/Common/test/target.py").expanduser(),
        Path("/usr/local/share/x3270/Common/test/target.py"),
        Path("Common/test/target.py"),  # relative to cwd
    ]
    for loc in locations:
        if loc.exists():
            return loc
    return None

def start_x3270_target(
    scenario: str = "menu-f",
    port: int = 8021,
    host: str = "127.0.0.1",
) -> subprocess.Popen:
    """Start x3270 target as subprocess.

    Returns the Popen object. Caller should call proc.terminate() when done.
    """
    target_path = find_x3270_target()
    if target_path is None:
        raise RuntimeError(
            "x3270 target.py not found. "
            "Clone https://github.com/wuzuf/x3270 or install x3270 package."
        )

    return subprocess.Popen(
        ["python3", str(target_path), "--type", scenario, "--port", str(port), "--address", host],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
```

- [ ] **Step 2: Export in __init__.py**

```python
from mock_server.x3270_target import start_x3270_target, find_x3270_target
```

- [ ] **Step 3: Commit**

```bash
git add mock_server/x3270_target.py mock_server/__init__.py
git commit -m "feat(mock_server): add x3270 target integration"
```

---

## Task 13: Update Tests and Verify All Scenarios Work

**Files:**
- Modify: `tests/test_enhanced_mock_server.py`
- Create: `tests/test_mock_scenarios.py`

- [ ] **Step 1: Create comprehensive scenario test**

```python
"""Test all mock server scenarios."""

import asyncio
import pytest
from mock_server.scenarios import SCENARIOS
from mock_server import TN3270MockServer
from pure3270 import Session

@pytest.mark.parametrize("scenario_name", list(SCENARIOS.keys()))
@pytest.mark.timeout(10)
def test_scenario_negotiates(scenario_name):
    """Verify each scenario starts and accepts connections."""
    config = ServerConfig(scenario=scenario_name)
    server = TN3270MockServer(config=config)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.start())

    try:
        s = Session()
        s.open(server.host, server.port)
        # Give time for negotiation
        import time
        time.sleep(0.5)
        s.close()
    finally:
        loop.run_until_complete(server.stop())
        loop.close()
```

- [ ] **Step 2: Run all scenario tests**

```bash
python -m pytest tests/test_mock_scenarios.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_mock_scenarios.py
git commit -m "test(mock_server): add scenario tests"
```

---

## Task 14: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/test_enhanced_mock_server.py tests/test_mock_scenarios.py -v
```

- [ ] **Step 2: Verify CLI works**

```bash
python -m mock_server.tn3270_mock_server --list
python -m mock_server.tn3270_mock_server --type echo --port 9999 &
sleep 1
python -c "import socket; s=socket.socket(); s.connect(('127.0.0.1', 9999)); print(s.recv(100))"
```

- [ ] **Step 3: Final lint check**

```bash
python -m black mock_server/
python -m flake8 mock_server/
python -m mypy mock_server/
```

---

## Implementation Order Summary

1. Task 1: Directory structure and re-exports
2. Task 2: Refactor with ServerConfig and CLI
3. Task 3: Screen builders
4. Task 4: Echo + negotiation_failure scenarios
5. Task 5: MenuTN3270EServer (core scenario)
6. Task 6: Menu3270Server
7. Task 7: MenuNVTServer
8. Task 8: MenuSSCP_LUServer
9. Task 9: ColorServer
10. Task 10: TN3270OnlyServer
11. Task 11: TLS support
12. Task 12: x3270 target integration
13. Task 13: Update tests
14. Task 14: Final verification
