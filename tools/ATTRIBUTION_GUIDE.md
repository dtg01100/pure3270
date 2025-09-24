# Attribution Comment Scaffolding Guide

This guide provides comprehensive instructions for using Pure3270's attribution comment scaffolding system. The system ensures consistent, legally compliant attribution for all third-party code, inspiration, and compatibility implementations.

## Overview

The attribution scaffolding system consists of:

- **Templates** (`tools/attribution_templates.py`): Standardized comment formats
- **Generator Tool** (`tools/generate_attribution.py`): Interactive and CLI tool for creating attributions
- **Validation Tests** (`tests/test_attribution_validation.py`): Ensures compliance with standards
- **This Guide**: Usage instructions and examples

## Quick Start

### Using the Interactive Generator

The easiest way to create attribution comments is using the interactive generator:

```bash
python tools/generate_attribution.py --interactive
```

This will guide you through the process step-by-step with prompts for all required information.

### Using Command-Line Options

For automated workflows, you can specify all parameters directly:

```bash
python tools/generate_attribution.py --type module \
    --source "IBM s3270/x3270" \
    --url "https://github.com/rhacker/x3270" \
    --license "BSD-3-Clause" \
    --description "TN3270 protocol implementation based on s3270"
```

## Attribution Types

### 1. Module-Level Attribution

Use for entire files that contain ported or inspired code.

**When to use:**
- Porting entire modules from third-party sources
- Files with significant inspiration from other projects
- Protocol implementations based on reference implementations

**Example:**
```python
ATTRIBUTION NOTICE
==================================================
This module contains code ported from or inspired by: IBM s3270/x3270
Source: https://github.com/rhacker/x3270
    Licensed under BSD-3-Clause

DESCRIPTION
----------------
TN3270 protocol implementation based on s3270

COMPATIBILITY
----------------
Compatible with s3270 command interface

ATTRIBUTION REQUIREMENTS
------------------------------
This attribution must be maintained when this code is modified or
redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
Last updated: 2025-09-23
```

**Generation:**
```bash
python tools/generate_attribution.py --type module \
    --source "IBM s3270/x3270" \
    --url "https://github.com/rhacker/x3270" \
    --license "BSD-3-Clause" \
    --description "TN3270 protocol implementation based on s3270" \
    --compatibility "Compatible with s3270 command interface"
```

### 2. Function/Method Attribution

Use for specific functions or methods that are ported from third-party sources.

**When to use:**
- Individual functions ported from other implementations
- Methods with specific algorithmic implementations
- Utility functions from external libraries

**Example:**
```python
def encode_ebcdic(data: bytes) -> bytes:
    """
    Ported from ebcdic package (https://pypi.org/project/ebcdic/)

    EBCDIC encoding functionality for 3270 data streams

    Licensed under MIT License

    Compatibility: Maintains compatibility with standard library
    """
    # Function implementation here
    pass
```

**Generation:**
```bash
python tools/generate_attribution.py --type function \
    --source "ebcdic package" \
    --url "https://pypi.org/project/ebcdic/" \
    --license "MIT License" \
    --description "EBCDIC encoding functionality for 3270 data streams" \
    --function-name "encode_ebcdic" \
    --compatibility "Maintains compatibility with standard library"
```

### 3. Class Attribution

Use for classes that are ported or heavily inspired by third-party implementations.

**When to use:**
- Data structure classes from other projects
- Protocol handler classes
- Emulation layer classes

**Example:**
```python
class TN3270ProtocolHandler:
    """
    Ported from IBM s3270/x3270 (https://github.com/rhacker/x3270)

    TN3270 protocol handling and negotiation

    Integration Layer: Protocol
    Compatibility: Maintains compatibility with original implementation

    Licensed under BSD-3-Clause
    """
    # Class implementation here
    pass
```

**Generation:**
```bash
python tools/generate_attribution.py --type class \
    --source "IBM s3270/x3270" \
    --url "https://github.com/rhacker/x3270" \
    --license "BSD-3-Clause" \
    --description "TN3270 protocol handling and negotiation" \
    --class-name "TN3270ProtocolHandler" \
    --integration-layer "Protocol"
```

### 4. Protocol Implementation Attribution

Use for protocol implementations that follow specific RFCs and reference implementations.

**When to use:**
- TN3270/TN3270E protocol implementations
- Telnet option negotiation
- 3270 data stream processing

**Example:**
```python
def negotiate_tn3270e_options():
    """
    Protocol implementation ported from IBM s3270/x3270 (https://github.com/rhacker/x3270)

    Implements TN3270E protocol according to:
    RFC 1576, RFC 2355

    Enhanced TN3270 protocol with printer session support

    Compatibility: Full compatibility with s3270 TN3270E implementation
    Licensed under BSD-3-Clause
    """
    # Protocol implementation here
    pass
```

**Generation:**
```bash
python tools/generate_attribution.py --type protocol \
    --source "IBM s3270/x3270" \
    --url "https://github.com/rhacker/x3270" \
    --license "BSD-3-Clause" \
    --protocol-name "TN3270E" \
    --rfc-numbers "RFC 1576" "RFC 2355" \
    --description "Enhanced TN3270 protocol with printer session support"
```

### 5. s3270 Compatibility Attribution

Use for code that maintains compatibility with IBM s3270/x3270 terminal emulator.

**When to use:**
- Command implementations matching s3270 interface
- Behavioral compatibility with s3270
- Protocol handling that matches s3270 behavior

**Example:**
```python
def execute_command(command: str):
    """
    s3270/x3270 Compatibility Implementation

    This Command Implementation maintains compatibility with IBM s3270/x3270 terminal emulator.

    Compatible Commands/Features:
    String, Ascii, Ebcdic, Enter, PF(1-24)

    Implements s3270-compatible command interface for 3270 terminal operations

    Integration Layer: Session
    Source: https://github.com/rhacker/x3270
    License: BSD-3-Clause
    """
    # Command implementation here
    pass
```

**Generation:**
```bash
python tools/generate_attribution.py --type s3270 \
    --component-type "Command Implementation" \
    --s3270-commands "String" "Ascii" "Ebcdic" "Enter" "PF(1-24)" \
    --description "Implements s3270-compatible command interface for 3270 terminal operations"
```

### 6. EBCDIC Codec Attribution

Use for EBCDIC encoding/decoding implementations.

**When to use:**
- Custom EBCDIC codecs
- Enhanced encoding support beyond standard library
- International character set support

**Example:**
```python
def encode_cp037_extended(data: str) -> bytes:
    """
    EBCDIC Codec Implementation

    Implements EBCDIC-CP037 encoding/decoding for 3270 data streams.

    Enhanced EBCDIC codec with international character support

    Fallback: Falls back to standard library CP037 codec when not available
    Integration Layer: Emulation
    License: MIT (when using ebcdic package) / PSF (standard library fallback)
    """
    # Codec implementation here
    pass
```

**Generation:**
```bash
python tools/generate_attribution.py --type ebcdic \
    --codec-name "EBCDIC-CP037" \
    --description "Enhanced EBCDIC codec with international character support" \
    --fallback-behavior "Falls back to standard library CP037 codec when not available"
```

## Common Attribution Patterns

### s3270 Protocol Implementation

For TN3270/TN3270E protocol implementations:

```bash
python tools/generate_attribution.py --type protocol \
    --source "IBM s3270/x3270" \
    --url "https://github.com/rhacker/x3270" \
    --license "BSD-3-Clause" \
    --protocol-name "TN3270E" \
    --rfc-numbers "RFC 1576" "RFC 2355" \
    --description "TN3270E protocol implementation with printer session support"
```

### Python Standard Library Usage

For code that uses Python standard library functionality:

```bash
python tools/generate_attribution.py --type function \
    --source "Python Standard Library" \
    --url "https://docs.python.org/3/library/" \
    --license "Python Software Foundation License (PSFL)" \
    --description "Uses asyncio for asynchronous I/O operations" \
    --function-name "async_connect"
```

### Optional Dependency Attribution

For optional dependencies like the `ebcdic` package:

```bash
python tools/generate_attribution.py --type module \
    --source "ebcdic Python Package" \
    --url "https://pypi.org/project/ebcdic/" \
    --license "MIT License" \
    --description "Enhanced EBCDIC encoding/decoding capabilities" \
    --compatibility "Falls back to standard library when not available"
```

## THIRD_PARTY_NOTICES.md Integration

When adding new third-party dependencies, you must also update `THIRD_PARTY_NOTICES.md`:

```bash
python tools/generate_attribution.py --type notice \
    --source-name "New Package" \
    --source-url "https://example.com/package" \
    --license "MIT License" \
    --license-text "Complete license text here..." \
    --description "Description of the package and its usage" \
    --components "module1.py" "module2.py" \
    --integration-layer "Emulation" \
    --modifications "Adapted for async compatibility" \
    --compatibility "Maintains API compatibility" \
    --optional
```

## Validation and Testing

### Running Attribution Tests

Validate your attribution comments:

```bash
python -m pytest tests/test_attribution_validation.py -v
```

### Manual Validation

You can also validate attribution comments manually:

```python
from tests.test_attribution_validation import AttributionValidator

validator = AttributionValidator()
result = validator.validate_module_attribution(your_attribution_text)

if result['valid']:
    print("Attribution is valid!")
else:
    print("Issues found:")
    for issue in result['issues']:
        print(f"- {issue}")
```

## Best Practices

### 1. Be Specific

Always be specific about what was ported or adapted:

```python
# Good
description = "TN3270E printer session negotiation logic"

# Bad
description = "Some protocol stuff"
```

### 2. Include Compatibility Information

Always document compatibility implications:

```python
compatibility_notes = "Compatible with s3270 command interface and maintains behavioral compatibility"
```

### 3. Reference RFCs for Protocol Code

For protocol implementations, always reference the relevant RFCs:

```python
rfc_references = ["RFC 1576", "RFC 2355"]
```

### 4. Document Integration Points

Clearly document where the code integrates into Pure3270's architecture:

```python
integration_points = ["Protocol layer", "Data stream processing", "Emulation layer"]
```

### 5. Use Standard License Names

Use the exact license names as they appear in `THIRD_PARTY_NOTICES.md`:

- "BSD-3-Clause" (not "BSD")
- "MIT License" (not "MIT")
- "Python Software Foundation License (PSFL)"

### 6. Keep Attribution Current

Update attribution comments when:
- Modifying the ported code
- Changing compatibility behavior
- Updating to new versions of the source

## Troubleshooting

### Common Issues

1. **Missing Required Fields**
   - Always provide source name, URL, license, and description
   - Use the interactive mode if unsure about required fields

2. **License Compatibility**
   - Ensure the license is compatible with Pure3270's MIT license
   - Check `THIRD_PARTY_NOTICES.md` for compatible licenses

3. **URL Format Issues**
   - URLs must include `http://` or `https://`
   - Use valid domain names or IP addresses

4. **RFC Format Issues**
   - Use format "RFC 1234" (not "1234" or "rfc-1234")

### Getting Help

If you need help with attribution:

1. **Interactive Mode**: Use `--interactive` for guided assistance
2. **Examples**: Look at existing attribution in the codebase
3. **Documentation**: Check `THIRD_PARTY_NOTICES.md` and `PORTING_GUIDELINES.md`
4. **Tests**: Run the validation tests to check your work

## Integration with Development Workflow

### Pre-commit Hooks

You can integrate attribution validation into your pre-commit hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: attribution-validation
        name: Validate Attribution Comments
        entry: python tools/generate_attribution.py --validate
        language: system
        files: \.(py)$
```

### CI/CD Integration

Add attribution validation to your CI pipeline:

```yaml
# GitHub Actions example
- name: Validate Attribution Comments
  run: |
    python -m pytest tests/test_attribution_validation.py -v
    python tools/generate_attribution.py --validate-all
```

## Examples from the Codebase

### Example 1: Protocol Implementation

```python
# In pure3270/protocol/tn3270e.py
ATTRIBUTION NOTICE
==================================================
This module contains code ported from or inspired by: IBM s3270/x3270
Source: https://github.com/rhacker/x3270
    Licensed under BSD-3-Clause

DESCRIPTION
----------------
TN3270E protocol implementation with printer session support

COMPATIBILITY
----------------
Compatible with s3270 TN3270E negotiation and data stream processing

RFC REFERENCES
----------------
- RFC 1576 (TN3270)
- RFC 2355 (TN3270E)

ATTRIBUTION REQUIREMENTS
------------------------------
This attribution must be maintained when this code is modified or
redistributed. See THIRD_PARTY_NOTICES.md for complete license text.
Last updated: 2025-09-23
```

### Example 2: Function Attribution

```python
def parse_ebcdic_data(data: bytes) -> Dict[str, Any]:
    """
    Ported from ebcdic package (https://pypi.org/project/ebcdic/)

    EBCDIC data stream parsing for 3270 terminal emulation

    Licensed under MIT License

    Compatibility: Maintains compatibility with standard library codecs
    Fallback: Uses CP037 when ebcdic package is not available
    """
    # Implementation here
    pass
```

### Example 3: s3270 Compatibility

```python
class S3270CommandInterface:
    """
    s3270/x3270 Compatibility Implementation

    This Command Implementation maintains compatibility with IBM s3270/x3270 terminal emulator.

    Compatible Commands/Features:
    String, Ascii, Ebcdic, Enter, PF(1-24), PA(1-3), Clear, Home

    Implements s3270-compatible command interface for 3270 terminal operations

    Integration Layer: Session
    Source: https://github.com/rhacker/x3270
    License: BSD-3-Clause
    """
    # Implementation here
    pass
```

## Summary

The attribution scaffolding system ensures that:

1. **Legal Compliance**: All third-party code is properly attributed
2. **Consistency**: Attribution follows standardized formats
3. **Maintainability**: Attribution is easy to update and validate
4. **Documentation**: Integration with existing documentation systems
5. **Contributor-Friendly**: Easy-to-use tools for generating attributions

By following this guide, contributors can ensure that their code maintains proper attribution while integrating seamlessly with Pure3270's architecture and legal requirements.
