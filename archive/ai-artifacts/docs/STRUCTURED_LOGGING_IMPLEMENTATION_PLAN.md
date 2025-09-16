# Structured Logging Implementation Plan for Pure3270

## Current Logging Practices Analysis

Based on my analysis of the Pure3270 codebase, here are the current logging practices:

1. **Standard Python Logging**: The project uses Python's built-in `logging` module with named loggers (`logger = logging.getLogger(__name__)`) in each module.

2. **Basic Configuration**: Logging is configured through `logging.basicConfig()` in the main `__init__.py` file with configurable levels.

3. **Log Usage**: Logs are used throughout the codebase with different levels (DEBUG, INFO, WARNING, ERROR) to track connection status, protocol negotiation, data transmission, and error conditions.

4. **No Structured Logging**: Currently, all logs are traditional string-based messages without structured data.

## Benefits of Structured Logging

Structured logging offers several advantages over traditional string-based logging:

1. **Better Searchability**: Fields can be queried individually (e.g., find all logs for a specific connection or user)
2. **Easier Parsing**: No need for regex pattern matching to extract information
3. **Consistent Schema**: Standardized fields across different log entries
4. **Enhanced Analysis**: Can perform aggregations, correlations, and complex queries
5. **Automation Friendly**: Tools can easily process structured logs for monitoring and alerting

## Approaches to Structured Logging

### JSON Format Approach
JSON-formatted logs store data in key-value pairs within a JSON object, making them easily parseable by log aggregation systems.

### Key-Value Pairs Approach
Another structured approach uses key-value pairs in a flat format that's human-readable but still machine-parseable.

## Implementation Plan

### 1. Create a Custom Structured Formatter

First, we'll create a custom JSON formatter that extends Python's logging formatter:

```python
# pure3270/logging/structured_formatter.py
import json
import logging
from datetime import datetime

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        # Get the default fields
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'pathname': record.pathname,
            'lineno': record.lineno,
            'function': record.funcName
        }

        # Add any extra fields provided in the log record
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno',
                              'pathname', 'filename', 'module', 'lineno',
                              'funcName', 'created', 'msecs', 'relativeCreated',
                              'thread', 'threadName', 'processName', 'process',
                              'getMessage', 'exc_info', 'exc_text', 'stack_info',
                              'message']:
                    log_data[key] = value

        return json.dumps(log_data)
```

### 2. Update Logging Configuration

We'll modify the `setup_logging` function in `pure3270/__init__.py` to support structured logging:

```python
# pure3270/__init__.py
def setup_logging(level="INFO", structured=False):
    """
    Setup basic logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Whether to use structured (JSON) logging
    """
    if structured:
        from .logging.structured_formatter import StructuredFormatter
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logging.basicConfig(level=getattr(logging, level.upper()), handlers=[handler])
    else:
        logging.basicConfig(level=getattr(logging, level.upper()))
```

### 3. Update Existing Log Statements

We'll update existing log statements to include structured data where appropriate. For example:

```python
# Before
logger.debug(f"Creating new TN3270Handler")

# After
logger.debug("Creating new TN3270Handler", extra={
    'handler_id': id(self),
    'host': self.host,
    'port': self.port
})
```

### 4. Add Contextual Logging

We'll enhance logging with contextual information such as session IDs, connection states, and operation details:

```python
# Example: Adding session context
logger.info("Session connected", extra={
    'session_id': session_id,
    'host': host,
    'port': port,
    'mode': 'TN3270E' if tn3270e_mode else 'TN3270',
    'lu_name': lu_name
})
```

### 5. Performance Considerations

To maintain performance:

1. Use `isEnabledFor()` checks before expensive logging operations
2. Cache `isEnabledFor()` results in performance-critical sections
3. Disable unneeded metadata collection:
   - Set `logging._srcfile = None` to avoid calling `sys._getframe()`
   - Set `logging.logThreads = False` to disable threading information
   - Set `logging.logProcesses = False` to disable process ID collection

### 6. Integration with Existing Infrastructure

The implementation will:

1. Maintain backward compatibility with existing string-based logging
2. Allow users to choose between structured and traditional logging via configuration
3. Follow the existing pattern of using named loggers (`logging.getLogger(__name__)`)
4. Preserve existing log levels and filtering capabilities

## Tools for Consuming Structured Logs

For consuming and analyzing the structured logs, we recommend:

1. **ELK Stack** (Elasticsearch, Logstash, Kibana) for storage, processing, and visualization
2. **Fluentd** for log collection and forwarding
3. **Graylog** for centralized log management
4. **Splunk** for enterprise log analysis

For development and lightweight usage, the built-in Python logging with JSON formatters will suffice.

## Implementation Steps

1. **Create the structured logging module** with custom formatters
2. **Update the logging configuration** to support structured logging option
3. **Enhance existing log statements** with structured data where appropriate
4. **Add documentation** on how to enable and use structured logging
5. **Provide examples** of structured logging usage
6. **Test performance impact** and optimize as needed

## Example Usage

After implementation, users will be able to enable structured logging:

```python
import pure3270
pure3270.setup_logging(level="DEBUG", structured=True)

# Logs will now be output in JSON format with structured data
```

Example structured log output:
```json
{
  "timestamp": "2023-10-10T14:23:05.123456",
  "level": "INFO",
  "logger": "pure3270.session",
  "message": "Session connected successfully",
  "pathname": "/var/mnt/Disk2/projects/pure3270/pure3270/session.py",
  "lineno": 125,
  "function": "connect",
  "session_id": "sess_12345",
  "host": "example.com",
  "port": 23,
  "mode": "TN3270E"
}
```

This structured logging implementation will provide better observability and debugging capabilities for Pure3270 while maintaining backward compatibility with existing logging practices.
