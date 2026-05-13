# Integration Tests

This directory contains integration tests that verify `pure3270` functionality against real mainframe environments and reference implementations.

## Requirements

### Hercules MVS Integration (`test_hercules.py`)

These tests verify behavior against a running MVS 3.8j mainframe system emulated via Hercules.

**Requirements:**
1.  **Hercules/MVS**: A running instance of Hercules with MVS 3.8j TK4- (or compatible) listening on `localhost:3270`.
    *   Provided via Docker: `rattydave/docker-ubuntu-hercules-mvs`
    *   Start with: `docker run -d --name hercules-mvs -p 3270:3270 -p 3271:3271 rattydave/docker-ubuntu-hercules-mvs`
    *   Or use docker-compose from the project root: `docker compose up -d hercules-mvs`
    *   Allow ~30 seconds for the MVS system to boot before running tests.
2.  **s3270**: The `s3270` binary from the x3270 suite must be installed and available in the system PATH (`/usr/bin/s3270`).
    *   This is used as a reference implementation to validate screen content.

**Running the tests:**

To run these tests, you must explicitly select the `hercules` marker:

```bash
pytest -m hercules tests/integration/test_hercules.py
```

If the requirements are not met, the tests will fail with connection errors or file not found errors.

**Known issues:**
- `test_initial_screen_matches_s3270` and `test_tso_login_matches_s3270` are marked xfail. pure3270 now correctly receives the Hercules initial "About" screen, but the comparison requires adjusting the s3270 reference capture sequence (e.g., using `Wait(Input)` instead of Enter to get the raw about screen).
- `test_s3270_enter_key` may occasionally time out depending on Hercules s3270 state.
