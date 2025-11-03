# Migration Guide: From p3270 to Native P3270Client

## Overview

pure3270 provides a native `P3270Client` class that serves as a direct drop-in replacement for `p3270.P3270Client`. This provides a cleaner, more reliable solution with no external dependencies.

## Migration Options

### Option 1: Direct Replacement (Recommended)

**Before (using p3270):**
```python
from p3270 import P3270Client

client = P3270Client(hostName='localhost', hostPort='23')
client.connect()
client.sendText("username")
client.sendEnter()
screen = client.getScreen()
client.disconnect()
```

**After (using pure3270 native client):**
```python
from pure3270 import P3270Client  # Only change needed!

client = P3270Client(hostName='localhost', hostPort='23')
client.connect()
client.sendText("username")
client.sendEnter()
screen = client.getScreen()
client.disconnect()
```

### Option 2: Alias for Gradual Migration

```python
# During transition period
from pure3270 import P3270Client as Pure3270Client
from p3270 import P3270Client as OriginalP3270Client

# Use Pure3270Client for new code
client = Pure3270Client(hostName='localhost')

# Keep existing p3270 code unchanged during testing
legacy_client = OriginalP3270Client(hostName='localhost')
```

### Option 3: Replacement in Existing Projects

For projects currently using patching:

**Before:**
```python
import pure3270
pure3270.enable_replacement()  # Monkey-patching

import p3270
client = p3270.P3270Client()  # Uses pure3270 under the hood
```

**After:**
```python
from pure3270 import P3270Client  # Direct import

client = P3270Client()  # Native pure3270 implementation
```

## Benefits of Native P3270Client

### ✅ Advantages
- **No monkey-patching required**: Cleaner, more maintainable code
- **No s3270 binary dependency**: Pure Python implementation
- **No subprocess overhead**: Better performance
- **Identical API**: 100% compatible with p3270.P3270Client
- **Better error handling**: Native Python exceptions
- **Easier testing**: No complex patching setup needed
- **Simpler deployment**: Fewer dependencies to manage

### 📊 API Compatibility

The native P3270Client implements **all 47 methods** from p3270.P3270Client:

| Category | Methods |
|----------|---------|
| **Connection** | `connect()`, `disconnect()`, `endSession()`, `isConnected()` |
| **Text I/O** | `sendText()`, `getScreen()`, `printScreen()`, `readTextAtPosition()`, `readTextArea()` |
| **Keyboard** | `sendEnter()`, `sendTab()`, `sendBackTab()`, `sendBackSpace()`, `sendHome()`, `sendKeys()` |
| **Function Keys** | `sendPF()`, `sendPA()` |
| **Cursor** | `moveTo()`, `moveCursorUp()`, `moveCursorDown()`, `moveCursorLeft()`, `moveCursorRight()`, `moveToFirstInputField()` |
| **Screen Ops** | `clearScreen()`, `saveScreen()`, `foundTextAtPosition()`, `trySendTextToField()` |
| **Field Ops** | `delChar()`, `delField()`, `delWord()`, `eraseChar()` |
| **Wait Functions** | `waitFor3270Mode()`, `waitForCursorAt()`, `waitForField()`, `waitForOutput()`, `waitForStringAt()`, etc. |
| **Utilities** | `makeArgs()`, `numOfInstances` |

### 🔧 s3270 Command Compatibility

The native client handles all s3270 commands:

```python
client = P3270Client()
client.send("String(Hello)")      # Text input
client.send("Enter")              # Key press
client.send("PF(1)")             # Function key
client.send("MoveCursor(5,10)")   # Cursor movement
client.send("Connect(B:hostname)") # Connection
client.send("Ascii(0,0,10)")     # Screen reading
```

## Testing Your Migration

Use the provided test script to validate compatibility:

```bash
# Test native P3270Client
python test_native_p3270.py

# Demo native functionality
python example_native_p3270.py
```

## Performance Comparison

| Aspect | p3270 + patching | Native P3270Client |
|--------|------------------|-------------------|
| **Startup** | Slow (subprocess + patching) | Fast (direct import) |
| **Memory** | Higher (subprocess overhead) | Lower (pure Python) |
| **Reliability** | Complex (patching can fail) | Simple (native code) |
| **Dependencies** | s3270 binary required | No external dependencies |
| **Debugging** | Difficult (multi-process) | Easy (single process) |

## Rollback Plan

If you need to rollback to the old patching approach:

```python
# Fallback to patching (not recommended for new projects)
import pure3270
pure3270.enable_replacement()

import p3270
client = p3270.P3270Client()
```

## Recommendation

**For all new projects**: Use `from pure3270 import P3270Client` directly.

**For existing projects**: Migrate incrementally by replacing imports and testing thoroughly.

The native P3270Client provides the same functionality with better performance, reliability, and maintainability.
