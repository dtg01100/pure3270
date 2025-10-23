# Pure3270 Connection Fix Summary

## Problem
Pure3270 was failing to connect to TN3270 servers that don't support TN3270E protocol extension. The connection would hang or fail with:
- `Invalid state transition: DISCONNECTED -> CONNECTED`
- `Max iterations (2000) reached; aborting negotiation`

## Root Cause
Two issues were identified:

### 1. Corrupted State Transition Code
The `_change_state` method in `/workspaces/pure3270/pure3270/protocol/tn3270_handler.py` had corrupted code where the validation check was incomplete:
```python
try:
        )  # Orphaned closing parenthesis with no opening
```

This should have been:
```python
try:
    if not self._validate_state_transition(current_state, new_state):
        raise StateTransitionError(
            f"Invalid state transition: {current_state} -> {new_state}"
        )
```

### 2. Negotiation Timeout Watchdog Too Aggressive
The iteration-based watchdog that prevents infinite loops was completing before the actual TN3270E negotiation timeout could trigger:
- Watchdog: 2000 iterations × 0ms sleep = instant completion
- Negotiation timeout: 2 seconds (step_timeout)
- Result: Watchdog aborted before natural timeout for non-TN3270E servers

## Solution

### Fix 1: Restored State Transition Validation (Line ~743)
```python
async def _change_state(self, new_state: str, reason: str) -> None:
    """Change state with validation and error handling."""
    async with self._state_lock:
        current_state = self._current_state

        try:
            if not self._validate_state_transition(current_state, new_state):
                raise StateTransitionError(
                    f"Invalid state transition: {current_state} -> {new_state}"
                )

            # Additional state-specific validation
            await self._validate_state_consistency(current_state, new_state)
```

### Fix 2: Adjusted Watchdog Timing (Line ~1797)
```python
# Iteration guard and diagnostic logging
# Allow enough iterations for the negotiation timeouts to work properly
# With 50ms sleep, 200 iterations = 10 seconds total
max_iterations = 200  # Increased to allow negotiation timeouts to trigger
log_interval_iterations = 100
iteration = 0

# In the loop:
await asyncio.sleep(0.05)  # 50ms sleep to reduce CPU usage while allowing timeouts to work
```

This gives the negotiation timeout (2 seconds for DEVICE-TYPE wait) enough time to complete before the watchdog aborts.

## Test Results

### Before Fix
```
ERROR:pure3270.protocol.tn3270_handler:Max iterations (2000) reached; aborting negotiation
pure3270.exceptions.ProtocolError: Protocol operation failed: Max iterations (2000) reached
```

### After Fix
```
WARNING:pure3270.protocol.negotiator:[NEGOTIATION] TN3270E negotiation timed out, falling back to basic TN3270 mode
INFO:pure3270.protocol.tn3270_handler:[HANDLER] Negotiation complete
WARNING:pure3270.protocol.tn3270_handler:[STATE] Entering TN3270_MODE without TN3270E negotiation - falling back to basic TN3270
```

Connection successful! Screen data received and commands work properly.

## Validation
Both test scripts now work identically:
- `examples/testing copy.py` - Using native p3270 library ✓
- `examples/testing.py` - Using pure3270 library ✓

Both successfully:
1. Connect to the server (66.189.134.90:2323)
2. Send username
3. Send password
4. Navigate menus
5. Sign off cleanly

## Files Modified
1. `/workspaces/pure3270/pure3270/protocol/tn3270_handler.py`
   - Line ~743: Fixed corrupted `_change_state` method
   - Line ~1797: Adjusted watchdog iteration limits
   - Line ~1809: Increased sleep interval from 0 to 50ms

## Next Steps
- Run full test suite to ensure no regressions
- Format and lint code
- Consider if watchdog parameters need environment-specific tuning
