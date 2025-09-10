# Docker-Based Integration Testing

This document describes how to set up Docker-based integration testing for pure3270.

## Available TN3270 Server Docker Images

Several Docker images can be used for testing pure3270:

### Hercules-Based Mainframe Emulators
1. `mainframed767/hercules` - Hercules System/370, ESA/390, and z/Architecture emulator
2. `allardkrings/hercules` - Another Hercules mainframe emulator implementation

### Building Your Own TN3270 Server

You can build a custom TN3270 server using the provided Dockerfile.s3270:

```bash
# Build the image
docker build -t pure3270-test-server -f Dockerfile.s3270 .

# Run the container
docker run -d -p 2323:23 --name test-tn3270-server pure3270-test-server
```

## Testing with Docker Containers

To test pure3270 against a Docker-based TN3270 server:

1. Start the TN3270 server container:
   ```bash
   docker run -d -p 2323:23 --name test-server mainframed767/hercules
   ```

2. Run integration tests:
   ```bash
   python hercules_integration_test.py
   ```

3. Clean up:
   ```bash
   docker rm -f test-server
   ```

## Example Test Implementation

See `hercules_integration_test.py` for a complete example of how to:
- Start a Docker container with a TN3270 server
- Test connectivity to the server
- Run pure3270 tests against the server
- Clean up resources properly

This approach provides realistic integration testing without requiring access to external mainframe systems.