# Project Brief

Pure3270 is a pure Python implementation of a TN3270 terminal emulator library. The project aims to provide a drop-in replacement for the s3270 binary dependency used in p3270 setups, offering both standalone Session/AsyncSession classes and monkey-patching capabilities for seamless integration.

## Core Requirements
- Full TN3270/TN3270E protocol support
- EBCDIC ↔ ASCII translation
- Screen buffer management with field handling
- Async and sync session APIs
- Monkey patching for p3270 compatibility
- ASCII/VT100 fallback mode
- Comprehensive test coverage

## Goals
- Zero runtime dependencies (Python standard library only)
- High performance and reliability
- RFC compliance for TN3270 protocols
- Easy integration and usage
- Robust error handling and logging

## Scope
- Terminal emulation for mainframe connections
- Protocol negotiation and data stream parsing
- Session management and macro execution
- SSL/TLS support for secure connections
