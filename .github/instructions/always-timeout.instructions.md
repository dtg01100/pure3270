---
applyTo: '**'
---

# Always Wrap Commands in Timeout

To prevent operations from hanging indefinitely, always wrap shell commands in a timeout mechanism. This ensures that long-running or unresponsive commands do not block the development workflow.

## Example Usage
Use `timeout` with a reasonable duration (e.g., 30 seconds) for network-dependent commands:
