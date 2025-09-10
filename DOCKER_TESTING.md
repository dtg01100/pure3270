# Docker-Based Integration Testing

This document describes how to set up Docker-based integration testing for pure3270 using various TN3270 server implementations.

## Available TN3270 Server Options

### 1. Hercules-Based Mainframe Emulators (Realistic Testing)
- `mainframed767/hercules` - Hercules System/370, ESA/390, and z/Architecture emulator that presents a TN3270 server interface
- `allardkrings/hercules` - Another Hercules mainframe emulator implementation with TN3270 support

### 2. Mock TN3270 Servers (Basic Testing)
- Custom mock servers that simulate basic TN3270 protocol behavior
- Useful for testing connection logic without complex server setup

## Understanding the Architecture

- **Hercules**: Mainframe emulator that acts as a TN3270 server
- **pure3270**: Client library that connects to TN3270 servers (replaces s3270)
- **s3270**: Traditional client-side utility suite for connecting to TN3270 servers
- **p3270**: Python wrapper around s3270 that pure3270 can patch to replace the subprocess calls

## Testing Approaches

### Option 1: Docker Compose (Recommended)
Use the provided docker-compose.test.yml for easy multi-container testing:

```bash
# Start all test services
docker-compose -f docker-compose.test.yml up -d

# Run integration tests
python refined_docker_integration_test.py

# Stop services
docker-compose -f docker-compose.test.yml down
```

### Option 2: Individual Container Testing
Test with specific containers:

```bash
# Test with Hercules TN3270 server
docker run -d -p 2324:23 --name hercules-test mainframed767/hercules:latest
python refined_docker_integration_test.py
docker rm -f hercules-test
```

### Option 3: Mock Server Testing
Use the built-in mock server for basic connectivity tests:

```bash
# Build and run mock server
docker build -t mock-tn3270 -f Dockerfile.mock-tn3270 .
docker run -d -p 2323:23 --name mock-test mock-tn3270
python refined_docker_integration_test.py
docker rm -f mock-test
```

## Test Implementation Details

The refined testing approach includes:

1. **Mock Server Testing**: Basic connectivity and error handling tests
2. **Docker Container Testing**: Realistic testing with actual TN3270 server implementations
3. **Graceful Error Handling**: Tests verify that pure3270 handles connection errors properly
4. **Resource Cleanup**: Automatic cleanup of Docker containers and network resources

## Running Tests

To run the comprehensive integration tests:

```bash
python refined_docker_integration_test.py
```

This will:
- Test with a mock TN3270 server (always available)
- Test with Hercules Docker container (if Docker is available)
- Provide detailed results for each test scenario

## Continuous Integration

The Docker-based tests can be easily integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Docker-based integration tests
  run: |
    docker-compose -f docker-compose.test.yml up -d
    python refined_docker_integration_test.py
    docker-compose -f docker-compose.test.yml down
```

This approach provides flexible, realistic integration testing without requiring access to external mainframe systems.