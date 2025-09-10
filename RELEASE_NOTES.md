# Pure3270 v0.2.0 Release Notes

## Overview

This release marks a significant milestone in the development of Pure3270, with the completion of all high and medium priority features. The library now provides comprehensive 3270 terminal emulation with full compatibility with the s3270 terminal emulator.

## Major Features

### Complete s3270 Compatibility
- Implemented all missing s3270 actions: Compose(), Cookie(), Expect(), Fail()
- Added full AID support for all PA (1-3) and PF (1-24) keys
- Enhanced field attribute handling beyond basic protection/numeric
- Improved field modification tracking for RMF/RMA commands

### Async Refactor
- Complete async refactor with AsyncSession supporting connect, macro execution, and managed context
- Exports in pure3270/__init__.py for Session, AsyncSession, and enable_replacement
- Enhanced tests with edge cases for async operations

### Protocol Enhancements
- Complete TN3270E protocol enhancements with printer session support
- SCS-CTL-CODES support for printer sessions
- PRINT-EOJ handling for printer jobs
- Resource definition support (xrdb format)

### Macro Execution
- Advanced macro execution with conditional branching and variable substitution
- Implementation of all s3270 actions including navigation, text conversion, and session control
- Support for LoadResource commands in macro execution

## Technical Improvements

### Architecture
- Improved code quality with comprehensive documentation updates
- Fixed field detection logic in screen_buffer.py to properly handle field boundaries
- Added missing is_printer_session property to TN3270Handler for printer session detection
- All 328 tests now passing with comprehensive coverage

### Performance
- Code formatted with black and passes flake8 checks
- Performance benchmarking with pytest-benchmark
- Efficient byte handling using bytearray and struct for EBCDIC and protocol streams

## API Changes

### Breaking Changes
- None

### New Features
- AsyncSession class for non-blocking operations
- enable_replacement() function for zero-configuration opt-in patching
- Comprehensive s3270-compatible CLI interface
- Standalone usage without p3270 dependency

### Improvements
- Enhanced error handling with custom inline exceptions
- Structured logging with configurable levels
- Better context manager support for session lifecycle management

## Testing
- 328 tests passing with comprehensive coverage
- Edge case testing for async operations
- Protocol handling verification
- Patching mechanism validation

## Documentation
- Comprehensive API documentation
- Updated architecture documentation
- New examples for patching, standalone usage, and end-to-end scenarios
- Migration guide from s3270/p3270

## Contributors
Thanks to all contributors who helped make this release possible.