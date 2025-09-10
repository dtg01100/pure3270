# Docker-Based Integration Testing

This document describes how to set up Docker-based integration testing for pure3270 using Hercules as a TN3270 server.

## Available TN3270 Server Docker Images

Several Docker images can be used for testing pure3270 as they provide TN3270 server functionality:

### Hercules-Based Mainframe Emulators
1. `mainframed767/hercules` - Hercules System/370, ESA/390, and z/Architecture emulator that presents a TN3270 server interface
2. `allardkrings/hercules` - Another Hercules mainframe emulator implementation with TN3270 support

## Understanding the Architecture

- **Hercules**: Mainframe emulator that acts as a TN3270 server
- **pure3270**: Client library that connects to TN3270 servers (replaces s3270)
- **s3270**: Traditional client-side utility suite for connecting to TN3270 servers
- **p3270**: Python wrapper around s3270 that pure3270 can patch to replace the subprocess calls

## Testing with Docker Containers

To test pure3270 against a Docker-based TN3270 server:

1. Start the Hercules TN3270 server container:
   ```bash
   docker run -d -p 2323:23 --name test-hercules mainframed767/hercules
   ```

2. Run integration tests:
   ```bash
   python hercules_integration_test.py
   ```

3. Clean up:
   ```bash
   docker rm -f test-hercules
   ```

## Example Test Implementation

See `hercules_integration_test.py` for a complete example of how to:
- Start a Docker container with a Hercules TN3270 server
- Test connectivity to the server
- Run pure3270 tests against the server
- Clean up resources properly

This approach provides realistic integration testing without requiring access to external mainframe systems, using Hercules as the authentic TN3270 server implementation that pure3270 can connect to.