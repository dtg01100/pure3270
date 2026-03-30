# Integration Tests

This directory contains integration tests that verify `pure3270` functionality against real mainframe environments and reference implementations.

## Requirements

### Hercules MVS Integration (`test_hercules.py`)

These tests verify behavior against a running MVS 3.8j mainframe system emulated via Hercules.

**Requirements:**
1.  **Hercules/MVS**: A running instance of Hercules with MVS 3.8j TK4- (or compatible) listening on `localhost:3270`.
    *   This is typically provided via a Docker container (e.g., `docker run -p 3270:3270 -d adrian/hercules-mvs`).
2.  **s3270**: The `s3270` binary from the x3270 suite must be installed and available in the system PATH (`/usr/bin/s3270`).
    *   This is used as a reference implementation to validate screen content.

**Running the tests:**

To run these tests, you must explicitly select the `hercules` marker:

```bash
pytest -m hercules tests/integration/test_hercules.py
```

If the requirements are not met, the tests will fail with connection errors or file not found errors.
