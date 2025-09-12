# Product Context

## Why This Project Exists
Mainframe integration is essential for many enterprise applications, but traditional TN3270 terminal emulators like s3270 introduce binary dependencies that complicate deployment, maintenance, and cross-platform compatibility. Pure3270 addresses this by providing a complete, pure Python implementation of the TN3270/TN3270E protocol, eliminating the need for external binaries.

## Problems Solved
- **Dependency Management**: Removes s3270 binary dependency, simplifying deployment and reducing compatibility issues
- **Cross-Platform Compatibility**: Pure Python works consistently across Windows, Linux, and macOS
- **Integration Complexity**: Provides both standalone APIs and monkey-patching for existing p3270 codebases
- **Protocol Compliance**: Implements RFC-compliant TN3270E with proper negotiation and data handling
- **Fallback Support**: Includes ASCII/VT100 mode for systems that don't support full 3270 emulation

## User Experience Goals
- **Seamless Integration**: Drop-in replacement for p3270 with minimal code changes
- **Intuitive APIs**: Simple Session/AsyncSession classes for direct usage
- **Robust Error Handling**: Clear error messages and graceful failure modes
- **Performance**: Efficient parsing and low latency for interactive sessions
- **Comprehensive Documentation**: Clear examples and API reference for easy adoption

## Target Users
- Python developers integrating with mainframe systems
- DevOps teams deploying applications with TN3270 requirements
- Organizations modernizing legacy mainframe interfaces
- Testing and automation frameworks needing TN3270 simulation
