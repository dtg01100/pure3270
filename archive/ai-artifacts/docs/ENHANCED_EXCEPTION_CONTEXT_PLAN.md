# Enhanced Exception Context Plan for Pure3270

## 1. Current Exception Handling Patterns

After examining the Pure3270 codebase, I've identified the following current exception handling patterns:

### Exception Hierarchy
- **Base Exceptions**: Defined in `pure3270/protocol/exceptions.py`
  - `NegotiationError` - Raised on negotiation failure
  - `ProtocolError` - Raised on protocol errors
  - `ParseError` - Raised on parsing errors

- **Session Exceptions**: Defined in `pure3270/session.py`
  - `SessionError` - Base exception for session-related errors
  - `ConnectionError` - Raised when connection fails
  - `MacroError` - Raised during macro execution errors

### Current Context Patterns
- F-string formatted error messages with basic context:
  - `raise ConnectionError(f"Failed to connect to {self.host}:{self.port}")`
  - `raise ParseError(f"Unknown or unhandled 3270 order: 0x{order:02x}")`
  - `raise ValueError(f"PF key must be between 1 and 24, got {n}")`

- Logging with context:
  - `logger.error(f"Connection failed: {e}", exc_info=True)`
  - `logger.warning(f"Position out of bounds: ({row}, {col})"`

- Exception chaining in some places:
  - `raise MacroError(f"Failed to execute command '{command}': {e}")`

## 2. Valuable Additional Context Information

Based on the codebase analysis, the following additional context would be valuable:

### Connection/Session Context
- Host and port information
- Connection state (connected/disconnected)
- SSL/TLS status
- Session ID or identifier
- TN3270 mode status (TN3270 vs TN3270E)

### Operation Context
- Method/function name where error occurred
- Input parameters (safely sanitized)
- Current screen state information
- Current cursor position
- Timing information (duration of operation)

### Protocol Context
- Sequence numbers for TN3270E operations
- Data type being processed
- Negotiated functions and device types
- SNA session state

### Resource Context
- File paths for resource loading operations
- Resource names
- Buffer sizes and positions

## 3. Best Practices for Adding Context to Exceptions

### Exception Chaining
- Use `raise ... from ...` to preserve original exception context
- Chain exceptions when wrapping lower-level errors
- Maintain clear causality chain

### Contextual Exception Classes
- Create specific exception classes for different error domains
- Include context as attributes rather than just in messages
- Provide structured access to error details

### Safe Context Inclusion
- Avoid including sensitive data (passwords, credentials)
- Sanitize input parameters before including in messages
- Limit context size to prevent excessive memory usage

### Logging Best Practices
- Include `exc_info=True` for detailed stack traces
- Use structured logging when possible
- Log at appropriate levels (ERROR for failures, WARNING for recoverable issues)

## 4. Implementation Approaches for Backward Compatibility

### Approach 1: Enhanced Exception Classes
Create enhanced versions of existing exception classes that maintain the same inheritance hierarchy but include additional context:

```python
class EnhancedSessionError(SessionError):
    def __init__(self, message, context=None, original_exception=None):
        super().__init__(message)
        self.context = context or {}
        self.original_exception = original_exception
```

### Approach 2: Context-Aware Exception Raising
Modify exception raising to include context while maintaining the same exception types:

```python
# Instead of:
raise SessionError("Connection failed")

# Use:
raise SessionError(f"Connection failed to {host}:{port} after {attempts} attempts")
```

### Approach 3: Exception Wrapping Decorator
Create a decorator that automatically adds context to exceptions:

```python
@add_context(host="host", port="port")
def connect(self, host, port):
    # Connection logic
    pass
```

### Approach 4: Context Manager for Operations
Use context managers to automatically track operation context:

```python
with operation_context("connect", host=host, port=port):
    # Connection logic
    pass
```

## 5. Performance Considerations

### Memory Usage
- Context information should be minimal to avoid memory bloat
- Avoid storing large data structures in exception context
- Use lazy evaluation where possible

### String Formatting Overhead
- F-string formatting has minimal overhead
- Pre-formatting messages is acceptable
- Avoid expensive operations in exception paths

### Exception Creation Cost
- Exception creation is already expensive; context addition has minimal relative impact
- Focus on meaningful context rather than comprehensive data capture

### Logging Performance
- Structured logging may have slight overhead but provides better debugging
- Consider conditional logging for verbose context

## 6. Detailed Implementation Plan

### Phase 1: Enhanced Exception Classes

1. **Create Enhanced Exception Base Classes**
   - Enhance `SessionError`, `ProtocolError`, `NegotiationError`, `ParseError`
   - Add context dictionary attribute
   - Add original exception chaining support

2. **Update Exception Raising**
   - Modify all `raise` statements to include relevant context
   - Add connection/session context to connection-related exceptions
   - Add operation context to method-specific exceptions

### Phase 2: Context-Aware Logging

1. **Enhance Logging Statements**
   - Add structured context to existing log messages
   - Include `exc_info=True` for all error logs
   - Add operation context to warning messages

2. **Create Context Helper Functions**
   - Functions to extract safe context from objects
   - Functions to format context for logging

### Phase 3: Decorator-Based Context Addition

1. **Create Context Decorators**
   - `@with_connection_context` for connection-related methods
   - `@with_operation_context` for general operations
   - `@with_protocol_context` for protocol-specific operations

2. **Apply Decorators Selectively**
   - Apply to high-value methods first
   - Focus on user-facing APIs

### Phase 4: Documentation and Examples

1. **Update Documentation**
   - Document enhanced exception context
   - Provide examples of accessing context information

2. **Create Examples**
   - Show how to handle enhanced exceptions
   - Demonstrate context access patterns

## 7. Specific Implementation Examples

### Enhanced Exception Class Example

```python
class EnhancedSessionError(SessionError):
    """Enhanced session error with context information."""
    
    def __init__(self, message, context=None, original_exception=None):
        super().__init__(message)
        self.context = context or {}
        self.original_exception = original_exception
        
    def __str__(self):
        base_msg = super().__str__()
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base_msg} (Context: {context_str})"
        return base_msg
```

### Context-Aware Exception Raising Example

```python
# Before:
raise ConnectionError("Connection failed")

# After:
context = {
    'host': self.host,
    'port': self.port,
    'ssl': bool(self.ssl_context),
    'attempt': attempt_number
}
raise EnhancedConnectionError(
    f"Failed to connect to {self.host}:{self.port}",
    context=context,
    original_exception=e
) from e
```

### Decorator Implementation Example

```python
def with_connection_context(func):
    """Add connection context to exceptions raised by the decorated function."""
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except Exception as e:
            # Only enhance if it's not already an enhanced exception
            if not hasattr(e, 'context'):
                context = {
                    'host': getattr(self, 'host', None),
                    'port': getattr(self, 'port', None),
                    'connected': getattr(self, 'connected', None),
                    'function': func.__name__
                }
                # Create enhanced version of the exception
                enhanced_exception = type(f"Enhanced{e.__class__.__name__}", 
                                        (e.__class__,), {})(str(e))
                enhanced_exception.context = {k: v for k, v in context.items() if v is not None}
                enhanced_exception.original_exception = e
                raise enhanced_exception from e
            raise
    return wrapper
```

## 8. Backward Compatibility Strategy

### Maintaining Existing Exception Types
- All existing exception types will be preserved
- Enhanced exceptions will inherit from existing types
- No changes to exception hierarchy that would break existing catch blocks

### Gradual Enhancement
- Start with high-impact areas (connection, protocol negotiation)
- Gradually enhance other areas based on user feedback
- Maintain optional enhancement for performance-sensitive applications

### Safe Context Inclusion
- Context will only include safe, non-sensitive information
- No passwords, credentials, or private data will be included
- Context will be structured for easy programmatic access

## 9. Testing Strategy

### Unit Tests
- Test that enhanced exceptions maintain backward compatibility
- Verify context information is correctly included
- Ensure exception chaining works properly

### Integration Tests
- Test exception handling in real-world scenarios
- Verify logging includes appropriate context
- Confirm no performance regression

### Migration Tests
- Test that existing code continues to work unchanged
- Verify that exception handling patterns still function
- Confirm that logging output is improved but compatible

## 10. Performance Impact Mitigation

### Lazy Context Evaluation
- Only compute context when exception is actually raised
- Use properties or methods for expensive context computation
- Avoid pre-computing context for operations that rarely fail

### Memory Optimization
- Limit context size to prevent memory bloat
- Use weak references where appropriate
- Clear context after exception handling when safe to do so

### Conditional Enhancement
- Allow users to disable context enhancement for performance-critical applications
- Provide configuration options for context verbosity
- Consider environment-based defaults (development vs production)

This plan provides a comprehensive approach to enhancing exception context in Pure3270 while maintaining backward compatibility and considering performance implications. The phased implementation allows for gradual adoption and testing, ensuring that the enhancements provide real value without introducing breaking changes.