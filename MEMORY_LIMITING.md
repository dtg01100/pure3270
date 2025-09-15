# Memory Limiting in Tests

This document explains how to limit memory usage in tests for the pure3270 project.

## Overview

Memory limiting is useful for:
1. Preventing tests from consuming excessive memory
2. Detecting memory leaks in code
3. Ensuring the application behaves correctly under memory constraints

## Implementation

The memory limiting functionality is implemented using Python's `resource` module, which is available on Unix-like systems (Linux, macOS).

The implementation is located in `tests/conftest.py` and provides pytest fixtures that can be used in tests.

## Available Fixtures

### memory_limit_500mb
Limits the memory to 500MB for the duration of the test.

### memory_limit_100mb
Limits the memory to 100MB for the duration of the test.

## Usage

### Using Fixtures in Tests

To use memory limiting in a test, simply add the fixture as a parameter:

```python
def test_my_function(memory_limit_500mb):
    # This test will be limited to 500MB of memory
    result = my_function()
    assert result is not None
```

### Platform Compatibility

Memory limiting only works on Linux systems. On other platforms, the fixtures will have no effect.

Tests that should only run with memory limiting can be marked with:

```python
@pytest.mark.skipif(platform.system() != 'Linux', reason="Memory limiting only supported on Linux")
def test_needs_memory_limiting():
    # Test code here
    pass
```

## Test Modifications

We have modified all existing test files to use memory limiting:

1. **Pytest-based tests** - Added `memory_limit_500mb` fixture to all test functions and classes
2. **Unittest-based tests** - Added memory limiting in the `setUp` method using the `set_memory_limit` function
3. **Script-based tests** - Added memory limiting at the beginning of the script using the `set_memory_limit` function

All 49 test files in the project now use memory limits:
- 30 files in the `tests/` directory (using pytest fixtures)
- 19 files in the root directory (using direct resource limiting)

These limits were chosen based on the expected memory usage of each test suite:
- 500MB is sufficient for most unit tests while still providing protection against excessive memory usage
- 100MB is used for performance tests to ensure they remain memory-efficient

## Manual Memory Limiting

For more fine-grained control, you can manually set memory limits within a test:

```python
import resource
import platform

def test_manual_memory_limiting():
    if platform.system() == 'Linux':
        # Save original limits
        original_limit = resource.getrlimit(resource.RLIMIT_AS)
        
        try:
            # Set a limit of 50MB
            max_memory_bytes = 50 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
            
            # Test code here
            # If memory usage exceeds 50MB, a MemoryError will be raised
            
        finally:
            # Restore original limits
            try:
                resource.setrlimit(resource.RLIMIT_AS, original_limit)
            except ValueError:
                # Ignore if we can't restore (may happen if we don't have permission)
                pass
```

## Limitations

1. Memory limiting only works on Unix-like systems (Linux, macOS)
2. Memory limits apply to the entire process, not just the test
3. Setting memory limits requires appropriate system permissions
4. Exceeding memory limits raises `MemoryError` exceptions

## Example Test

See `tests/test_memory_limiting.py` for example usage of memory limiting fixtures.