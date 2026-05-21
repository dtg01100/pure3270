# Mock Server Expansion Design

## Status

Draft - awaiting implementation planning

## Overview

Expand `mock_server/tn3270_mock_server.py` into a comprehensive TN3270 test server framework with multiple scenario types, TLS support, and optional x3270 `target` integration.

## Motivation

The current `EnhancedTN3270MockServer` implements a single negotiation-heavy scenario. Testing requires scenarios that exercise:
- Different TN3270/TN3270E modes
- NVT fallback behavior
- Error/negotiation failure paths
- Color and extended attributes
- TLS connections
- Realistic 3270 data streams

x3270's `target` provides multiple named scenarios; we replicate this pattern with pure Python async.

## Architecture

### Base Class: `TN3270MockServer`

Retains current structure with scenario callable pattern, enhanced with:

```python
@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 0  # auto
    scenario: str = "enhanced"  # scenario name
    terminal_type: str = "IBM-3278-2-E"
    lu_name: str = "LUNAME01"
    functions_mode: str = "send"  # "send" | "request"
    tls_mode: str = "none"  # "none" | "immediate" | "negotiated"
```

### Scenario Registry

Scenarios are async callables registered in a dict:

```python
SCENARIOS: dict[str, type[TN3270MockServer]] = {
    "echo": EchoServer,
    "negotiation_failure": NegotiationFailureServer,
    "menu_nvt": MenuNVTServer,
    "menu_3270": Menu3270Server,
    "menu_tn3270e": MenuTN3270EServer,
    "menu_sscp_lu": MenuSSCPUIServer,
    "color": ColorServer,
    "tn3270_only": TN3270OnlyServer,
}
```

### Scenario Classes

Each scenario extends `TN3270MockServer` with overridden `handle_client`.

#### EchoServer
- Sends WILL EOR
- Echoes back any data received
- Use for: Protocol debugging, connection verification

#### NegotiationFailureServer
- Sends IAC WONT EOR immediately
- Closes connection
- Use for: Error path testing

#### MenuNVTServer
- Sends WILL EOR, DO TTYPE
- Sends text menu over NVT (no 3270 data stream)
- Use for: NVT mode testing, ASCII handling

#### Menu3270Server
- Standard TN3270 negotiation (no E)
- Sends formatted 3270 menu screen
- Use for: Basic TN3270 testing

#### MenuTN3270EServer
- Full TN3270E negotiation
- Sends formatted 3270 menu via TN3270E
- Use for: TN3270E protocol testing

#### MenuSSCP_LUServer
- TN3270E with SSCP-LU mode negotiation
- Sends menu in SSCP-LU mode
- Use for: SSCP-LU-specific behavior

#### ColorServer
- Full TN3270E negotiation
- Sends 3279 color display with:
  - Extended attributes ( EA_EABIT | EA_COLOR | EA_HIGHLIGHT)
  - Multiple color values
  - F1/F2/F3 key handling simulation
- Use for: Color and EA testing

#### TN3270OnlyServer
- TN3270 (no E) negotiation only
- No TN3270E option offered
- Use for: Non-E fallback testing

### TLS Support

Modes:
- `none`: Plain TCP
- `immediate`: TLS required from connection start
- `negotiated`: Start plain, send DO STARTTLS after 2s timeout

Embedded self-signed cert for testing:
```python
TLS_CERT = """-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----"""
TLS_KEY = """-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----"""
```

### Realistic 3270 Data Streams

Menu screens use structured 3270 data:

```python
def build_menu_screen(fields: list[MenuField]) -> bytes:
    """Build a formatted 3270 menu screen.

    Each MenuField: (row, col, label, is_protected, attr_byte)
    """
    # WCC + SBA + SF + label repeated
    # Properly encoded 12-bit buffer addresses
    # EBCDIC text
```

### CLI Interface

```bash
python -m mock_server.tn3270_mock_server --type menu_tn3270e --port 8021
python -m mock_server.tn3270_mock_server --type color --tls negotiated
python -m mock_server.tn3270_mock_server --list-scenarios
```

### x3270 target Integration (Optional)

```python
def start_x3270_target(
    scenario: str = "menu-f",
    port: int = 8021
) -> subprocess.Popen:
    """Start x3270 target as subprocess for comparison testing."""
    # Requires x3270 source in Common/test/target
    # Or target binary on PATH
```

This allows:
- Running pure3270 against both mock server and x3270 target
- Trace comparison between implementations
- Verifying pure3270 behavior matches reference

## File Structure

```
mock_server/
  __init__.py           # Re-exports
  tn3270_mock_server.py # Main expanded module
  tls_certs.py          # Embedded certs
  scenarios/
    __init__.py
    echo.py
    menu_nvt.py
    menu_3270.py
    menu_tn3270e.py
    menu_sscp_lu.py
    color.py
    negotiation_failure.py
    tn3270_only.py
```

## Backwards Compatibility

- `TN3270MockServer(scenario=callable)` still works
- `EnhancedTN3270MockServer` becomes alias for `MenuTN3270EServer`
- Existing test imports unchanged

## Testing Requirements

- Each scenario tested with `Session` connectivity
- TLS modes tested with SSL context
- s3270 connectivity test where binary available
- x3270 target comparison (when available)

## Implementation Order

1. Refactor base class with config dataclass and scenario registry
2. Implement core scenarios (echo, negotiation_failure, menu_3270, menu_tn3270e)
3. Add menu screen builders with realistic 3270 data streams
4. Add NVT and SSCP-LU scenarios
5. Add Color scenario with EA
6. Add TLS support with embedded certs
7. Add CLI interface
8. Add x3270 target integration helper
9. Add comprehensive tests
