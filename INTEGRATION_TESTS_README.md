# Pure3270 Integration Testing

This document explains how to use the automated integration testing framework for Pure3270, with a focus on testing **screen content reading during navigation operations**.

## Overview

The integration testing framework provides comprehensive automated tests that verify Pure3270 can:

1. **Connect to real TN3270 servers** (using Hercules emulator in Docker)
2. **Read screen content during navigation** (text, fields, cursor positions)
3. **Navigate based on screen content analysis**
4. **Handle errors by reading screen messages**
5. **Perform complete automation cycles** (connect → login → navigate → enter data → logout)

## Running Integration Tests

### Prerequisites

1. Docker installed and configured
2. Python 3.8+
3. Required test dependencies:
   ```bash
   pip install pytest pytest-asyncio docker
   ```

### Running All Integration Tests

```bash
# Run all integration tests with Hercules TN3270 server
python -m pytest test_hercules_integration.py --integration -v
```

### Running Specific Test Suites

```bash
# Run only connection tests
python -m pytest test_hercules_integration.py::TestHerculesConnection --integration -v

# Run only screen content reading tests
python -m pytest test_hercules_integration.py::TestScreenContentReading --integration -v

# Run only navigation method tests
python -m pytest test_hercules_integration.py::TestNavigationMethods --integration -v

# Run only text search tests
python -m pytest test_hercules_integration.py::TestTextSearchAndAnalysis --integration -v

# Run only error handling tests
python -m pytest test_hercules_integration.py::TestErrorHandling --integration -v
```

## Screen Content Reading Capabilities Tested

### 1. Full Screen Text Retrieval
```python
# Get complete screen as readable text
screen_text = session.screen_buffer.to_text()
print(f"Screen content: {repr(screen_text)}")
```

### 2. Field Content Extraction
```python
# Get all fields on screen
fields = session.screen_buffer.fields
for field in fields:
    print(f"Field: Protected={field.protected}, Numeric={field.numeric}")
    print(f"  Position: {field.start} to {field.end}")
```

### 3. Text Search and Pattern Matching
```python
# Search for specific content
screen_text = session.screen_buffer.to_text()
if 'MENU' in screen_text.upper():
    print("Menu screen detected")

# Find menu options automatically
lines = screen_text.split('\n')
for line in lines:
    if line.strip().startswith(('1.', '2.', '3.')):
        print(f"Menu option found: {line.strip()}")
```

### 4. Cursor Position Tracking
```python
# Get current cursor position
cursor_row, cursor_col = session.screen_buffer.get_position()
print(f"Cursor at: Row {cursor_row}, Column {cursor_col}")

# Move cursor and verify
await session.move_cursor(4, 16)
new_row, new_col = session.screen_buffer.get_position()
assert new_row == 4 and new_col == 16
```

### 5. Screen Structure Analysis
```python
# Get screen dimensions
rows = session.screen_buffer.rows
cols = session.screen_buffer.cols
print(f"Screen size: {rows}×{cols}")

# Analyze screen buffer
buffer_size = len(session.screen_buffer.buffer)
print(f"Buffer size: {buffer_size} bytes")
```

## Navigation with Screen Content Reading

The integration tests verify that Pure3270 can perform navigation decisions based on real screen content:

### Adaptive Menu Navigation
```python
async def adaptive_menu_navigation(session):
    """Navigate menus by reading available options."""
    # Read current screen
    screen_text = session.screen_buffer.to_text()
    lines = screen_text.split('\n')
    
    # Find menu options automatically
    for line in lines:
        if line.strip().startswith(('1.', '2.', '3.', '4.')):
            option_number = line.strip().split('.')[0]
            await session.insert_text(option_number)
            await session.enter()
            return True
    return False
```

### Intelligent Field Filling
```python
async def intelligent_field_filling(session, data_dict):
    """Fill fields by reading their labels."""
    # Get screen text
    screen_text = session.screen_buffer.to_text()
    lines = screen_text.split('\n')
    
    # Find fields by looking for labels
    for i, line in enumerate(lines[:-1]):
        if 'NAME:' in line.upper():
            # Field is typically on next line
            await session.move_cursor(i + 1, 24)
            await session.insert_text(data_dict.get('name', ''))
```

### Error Detection and Recovery
```python
async def error_detective_navigation(session):
    """Handle errors by reading screen messages."""
    # Perform some operation
    await session.enter()
    
    # Check for errors
    screen_text = session.screen_buffer.to_text().upper()
    if 'ERROR' in screen_text or 'INVALID' in screen_text:
        print("Error detected, taking corrective action")
        await session.enter()  # Often clears error messages
        return False
    return True
```

## Test Categories

### Unit Tests (No External Dependencies)
- **Method Existence**: Verify all navigation methods exist and are callable
- **Interface Completeness**: Check that all expected APIs are available
- **Error Handling**: Test graceful failure modes

### Integration Tests (With Hercules Server)
- **Real Connection**: Test actual TN3270 connection and communication
- **Screen Content Reading**: Verify screen text and field extraction
- **Navigation Operations**: Test all navigation methods with real server
- **Error Scenarios**: Validate error detection and recovery

## Docker-Based Testing Environment

The tests automatically:

1. **Start Hercules TN3270 Server**: Launches mainframe emulator in Docker container
2. **Wait for Service Availability**: Polls until TN3270 service is ready
3. **Run All Tests**: Execute comprehensive integration tests
4. **Cleanup Resources**: Stop and remove Docker container

## Continuous Integration

The integration tests can be run in CI/CD pipelines:

```yaml
# GitHub Actions example
name: Integration Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    - name: Install dependencies
      run: |
        pip install pytest pytest-asyncio docker
        pip install -e .
    - name: Start Docker
      uses: docker/setup-docker-action@v1
    - name: Run integration tests
      run: |
        python -m pytest test_hercules_integration.py --integration -v
```

## Key Benefits

✅ **Real Server Testing**: Tests against actual Hercules TN3270 server  
✅ **Complete Coverage**: All screen reading and navigation capabilities  
✅ **Automated Setup**: Docker-based environment with automatic cleanup  
✅ **Flexible Execution**: Can run with or without real server  
✅ **Robust Error Handling**: Validates graceful failure modes  
✅ **Continuous Integration Ready**: Works in automated testing pipelines  

## Conclusion

The Pure3270 integration testing framework provides comprehensive automated testing for:

- **Screen Content Reading**: Full text retrieval, field extraction, cursor tracking
- **Navigation Operations**: All 3270 navigation methods available and tested
- **Content-Driven Automation**: Making navigation decisions based on screen content
- **Error Handling**: Robust error detection and recovery by reading screen messages
- **Real Integration Testing**: Complete end-to-end testing with actual TN3270 server

This ensures that Pure3270 can reliably read screen content during navigation operations and make intelligent automation decisions based on that content.