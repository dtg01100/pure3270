# Pure3270 Warning Categorization System

The Pure3270 framework now includes a comprehensive warning categorization system that helps developers distinguish between different types of warnings, making debugging and production monitoring much more effective.

## Overview

Previously, all warnings in Pure3270 appeared the same, making it difficult for users to understand which issues required immediate attention versus those that were informational. The new system categorizes warnings into specific types with filtering capabilities.

## Warning Categories

### Protocol Warnings (Critical)
- **`PROTOCOL_NEGOTIATION`**: TN3270/TN3270E negotiation issues, handshake failures
- **`DATA_STREAM`**: Data parsing errors, format issues, stream corruption
- **`SNA_RESPONSE`**: SNA protocol response errors
- **`ADDRESSING`**: Screen addressing calculation errors
- **`PARSING`**: General parsing failures
- **`UNKNOWN_DATA`**: Unrecognized data formats

### Framework Warnings (Less Critical)
- **`CONFIGURATION`**: Invalid configuration values, missing settings
- **`DEPRECATION`**: Deprecated feature usage
- **`STYLE`**: Code style and formatting issues (disabled by default)

### Integration Warnings (External Systems)
- **`SSL_TLS`**: SSL/TLS certificate and encryption issues
- **`NETWORK`**: Network connectivity problems
- **`EXTERNAL_API`**: Third-party API integration issues

### Performance Warnings
- **`PERFORMANCE`**: Performance optimization opportunities
- **`TIMEOUT`**: Timeout-related issues
- **`RESOURCE_USAGE`**: Resource consumption warnings

### State Management Warnings
- **`STATE_MANAGEMENT`**: Invalid state transitions
- **`RECOVERY`**: Error recovery attempts
- **`VALIDATION`**: Validation failures

### Security Warnings
- **`SECURITY`**: Security-related warnings

### Specialized Warnings
- **`PRINTER`**: Printer emulation issues
- **`PRINTING`**: Print job problems
- **`FILE_TRANSFER`**: IND$FILE transfer issues

## Quick Start

### Basic Usage

```python
from pure3270.warnings import get_categorized_logger, WarningCategory

# Create a categorized logger
logger = get_categorized_logger('my_app')

# Log warnings with categories
logger.log_protocol_warning("TN3270E negotiation failed")
logger.log_configuration_warning("Invalid terminal type, using default")
logger.log_security_warning("SSL verification disabled")
```

### Environment-Specific Configuration

```python
from pure3270.warnings import setup_default_warning_filters

# For development (all warnings enabled)
setup_default_warning_filters("development")

# For production (only critical warnings)
setup_default_warning_filters("production")

# For protocol debugging (protocol warnings only)
setup_default_warning_filters("protocol_debug")
```

## Configuration Options

### Command Line Integration

```python
import argparse
from pure3270.warnings import add_warning_arguments, configure_warnings_from_args

# Add warning arguments to your argument parser
parser = argparse.ArgumentParser()
add_warning_arguments(parser)

# Configure based on parsed arguments
args = parser.parse_args()
filters = configure_warnings_from_args(args)
```

Command line options:
- `--warning-filters`: Choose from `development`, `production`, `protocol_debug`
- `--disable-warning-categories`: Disable specific categories
- `--enable-warning-categories`: Enable specific categories
- `--warning-level`: Set minimum logging level

### Programmatic Control

```python
from pure3270.warnings import get_warning_filters, WarningCategory

# Get global filters
filters = get_warning_filters()

# Disable specific categories
filters.disable_category(WarningCategory.STYLE)
filters.disable_category(WarningCategory.DEPRECATION)

# Set custom logging levels
filters.set_category_level(WarningCategory.PROTOCOL_NEGOTIATION, logging.ERROR)
filters.set_category_level(WarningCategory.SECURITY, logging.ERROR)

# Check if category is enabled
if filters.is_category_enabled(WarningCategory.NETWORK):
    # Handle network warnings
    pass
```

## Warning Message Format

### Before (Unclear)
```
WARNING:root:Invalid terminal type, using default
WARNING:root:Connection failed, retrying
WARNING:root:Protocol negotiation timeout
```

### After (Categorized)
```
[CONFIGURATION] Invalid terminal type, using default
[NETWORK] Connection failed, retrying
[PROTOCOL_NEGOTIATION] Protocol negotiation timeout
```

## Filter Presets

### Development Preset
- All categories enabled
- Style warnings disabled (not actionable)
- Useful for full visibility during development

### Production Preset
- Only critical categories enabled:
  - PROTOCOL_NEGOTIATION (set to ERROR level)
  - SECURITY (set to ERROR level)
  - STATE_MANAGEMENT
  - RECOVERY
- All verbose warnings disabled
- Minimal noise, maximum signal

### Protocol Debug Preset
- Protocol-related categories enabled:
  - PROTOCOL_NEGOTIATION
  - DATA_STREAM
  - SNA_RESPONSE
  - ADDRESSING
  - PARSING
  - UNKNOWN_DATA
- Framework categories disabled
- Perfect for debugging protocol issues

## Advanced Usage

### Custom Warning Categories

```python
from pure3270.warnings import CategorizedLogger, WarningCategory
import logging

# Create logger with custom filters
filters = get_warning_filters()
filters.enable_category(WarningCategory.CUSTOM_CATEGORY)

logger = logging.getLogger('custom')
cat_logger = CategorizedLogger(logger, filters)

# Use your custom category
cat_logger.warning(WarningCategory.CUSTOM_CATEGORY, "Custom warning message")
```

### Integration with Existing Code

Most Pure3270 modules now support categorized warnings. When available, they automatically use the new system:

```python
from pure3270.protocol.negotiator import Negotiator

# This will automatically use categorized warnings if available
negotiator = Negotiator(writer, parser, screen_buffer)
```

### Warning Statistics

```python
from pure3270.warnings import get_warning_statistics

stats = get_warning_statistics()
print(f"Total categories: {stats['total_categories']}")
print(f"Enabled: {stats['enabled_categories']}")
print(f"Disabled: {stats['disabled_categories']}")
```

## Migration Guide

### For Existing Applications

No changes required! The system is backward compatible. Existing `logger.warning()` calls continue to work normally.

### Opting Into Categorized Warnings

To get categorized warnings, update your logging calls:

```python
# Old way
logger.warning("Something went wrong")

# New way (if categorized logger available)
if hasattr(logger, 'log_protocol_warning'):
    logger.log_protocol_warning("Something went wrong")
else:
    logger.warning("Something went wrong")
```

## Best Practices

1. **Use Appropriate Categories**: Choose the most specific category for each warning
2. **Production Filtering**: Use production preset in production environments
3. **Protocol Debugging**: Use protocol preset when debugging protocol issues
4. **Custom Levels**: Set protocol and security warnings to ERROR in production
5. **Disable Non-Actionable**: Keep style and deprecation warnings disabled

## Examples

### Example 1: Basic Application Setup

```python
#!/usr/bin/env python3
import logging
from pure3270.warnings import setup_default_warning_filters, get_categorized_logger

# Configure for your environment
setup_default_warning_filters("development")  # or "production"

# Create logger
logger = get_categorized_logger('my_tn3270_app')

# Use categorized warnings
logger.log_protocol_warning("Server doesn't support TN3270E")
logger.log_configuration_warning("Invalid screen size, using 24x80")
```

### Example 2: Command Line Tool

```python
#!/usr/bin/env python3
import argparse
from pure3270.warnings import add_warning_arguments, configure_warnings_from_args

parser = argparse.ArgumentParser(description="TN3270 Client")
add_warning_arguments(parser)

args = parser.parse_args()
filters = configure_warnings_from_args(args)

# Now use the configured filters throughout your application
```

### Example 3: Protocol Debugging

```python
from pure3270.warnings import create_protocol_filter, CategorizedLogger
import logging

# Create protocol-focused logger
filters = create_protocol_filter()
logger = logging.getLogger('protocol_debug')
cat_logger = CategorizedLogger(logger, filters)

# Only protocol warnings will be shown
cat_logger.log_protocol_warning("Negotiation timeout")
cat_logger.log_data_stream_warning("Malformed data stream")
# These will be filtered out:
cat_logger.log_performance_warning("Slow connection")
cat_logger.log_configuration_warning("Using default config")
```

## Troubleshooting

### Warnings Not Categorized
- Check that warning categorization is imported: `from pure3270.warnings import *`
- Ensure the categorized logger is being used
- Verify filters are properly configured

### All Warnings Filtered Out
- Check which categories are enabled: `get_warning_statistics()`
- Verify log level is set appropriately
- Ensure filters aren't overly restrictive

### Categories Not Working
- Confirm warning categorization system is installed
- Check for import errors in the warnings module
- Verify Python version compatibility (3.7+)

## Performance Impact

The warning categorization system has minimal performance impact:
- **Memory**: ~50KB for all category definitions
- **CPU**: Negligible overhead per warning call
- **I/O**: Same as regular logging when warnings are enabled

## Compatibility

- **Python**: 3.7+
- **Pure3270**: All versions (backward compatible)
- **Logging**: Standard Python logging module

The system is designed to be completely backward compatible. Existing applications continue to work unchanged, while new applications can opt into the enhanced warning system.
