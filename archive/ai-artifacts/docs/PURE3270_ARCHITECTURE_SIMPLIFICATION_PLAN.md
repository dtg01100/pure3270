# Pure3270 Architecture Simplification Plan

This document outlines a comprehensive architecture plan for simplifying the Pure3270 library while maintaining full compatibility with existing interfaces and integrations.

## 1. Overall Architecture Changes

### 1.1 Current Architecture Issues
- Heavy coupling between Session and AsyncSession classes
- Complex inheritance hierarchy with many methods
- Extensive duplication of functionality between sync and async interfaces
- Overlapping responsibilities between protocol handling and session management

### 1.2 Proposed Simplified Architecture

```
Pure3270 Simplified Architecture
├── Core Session Layer
│   ├── Session (synchronous facade)
│   └── AsyncSession (primary implementation)
├── Protocol Layer
│   ├── TN3270Handler (connection and protocol handling)
│   ├── DataStreamParser (incoming data processing)
│   └── DataStreamSender (outgoing command construction)
├── Emulation Layer
│   ├── ScreenBuffer (screen state management)
│   └── EBCDIC Codec (character encoding)
├── Integration Layer
│   ├── MonkeyPatchManager (p3270 compatibility)
│   └── S3270Wrapper (s3270 interface compatibility)
└── Printer Support (modular component)
    ├── PrinterSession
    └── PrinterJob
```

### 1.3 Key Simplification Principles
1. **Single Source of Truth**: One primary implementation (AsyncSession) with synchronous wrapper
2. **Clear Separation of Concerns**: Distinct layers for protocol, emulation, and integration
3. **Minimal Interface**: Reduce public API surface while maintaining compatibility
4. **Modular Components**: Isolate printer functionality and patching mechanisms
5. **Consistent Error Handling**: Unified exception hierarchy

## 2. Session/AsyncSession Refactoring Approach

### 2.1 Consolidate Session Implementation
The current implementation has significant duplication between Session and AsyncSession. The refactoring will:

1. **Make AsyncSession the Primary Implementation**
   - Move all core functionality to AsyncSession
   - Session becomes a thin synchronous wrapper using `asyncio.run()`

2. **Reduce Method Count**
   - Identify and eliminate duplicate or redundant methods
   - Consolidate similar operations (e.g., various cursor movement methods)
   - Create unified interfaces for common operations

3. **Simplify Method Signatures**
   - Standardize parameter naming and ordering
   - Reduce optional parameters where possible
   - Improve documentation consistency

### 2.2 Refactored Class Structure

```python
# Before: Multiple similar methods
class AsyncSession:
    async def move_cursor(self, row: int, col: int) -> None: ...
    async def move_cursor1(self, row: int, col: int) -> None: ...
    async def left(self) -> None: ...
    async def right(self) -> None: ...
    # ... many more similar methods

# After: Unified navigation interface
class AsyncSession:
    async def move_cursor(self, row: int, col: int, relative: bool = False) -> None: ...
    async def move_direction(self, direction: str, count: int = 1) -> None: ...
```

### 2.3 Backward Compatibility Strategy
- Maintain all existing method names as aliases
- Deprecate methods with warnings in documentation
- Provide migration guide for new simplified interfaces

## 3. Printer Functionality Modularization

### 3.1 Current State
Printer functionality is embedded within the protocol layer but not well-isolated.

### 3.2 Proposed Modularization
1. **Separate Printer Module**: Move printer functionality to dedicated module
2. **Optional Dependency**: Make printer support optionally importable
3. **Clean Interface**: Provide clear API for printer session management

### 3.3 Implementation Plan
```python
# pure3270/printer/__init__.py
from .session import PrinterSession
from .job import PrinterJob

# Usage
from pure3270.printer import PrinterSession
```

### 3.4 Benefits
- Reduced core library size for users not needing printer support
- Clearer separation of concerns
- Easier maintenance and testing of printer functionality

## 4. Code Modernization Strategy

### 4.1 Python Version Alignment
- Maintain Python 3.8+ support as specified
- Use modern Python features where available:
  - Walrus operator (:=) for cleaner assignments
  - Better type hinting with `typing_extensions`
  - Context manager improvements

### 4.2 Code Structure Improvements
1. **Consistent Naming Conventions**
   - Use snake_case consistently
   - Align with PEP 8 standards
   - Meaningful variable and function names

2. **Reduced Complexity**
   - Break down large methods into smaller, focused functions
   - Eliminate deeply nested conditionals
   - Apply single responsibility principle

3. **Improved Documentation**
   - Add comprehensive docstrings
   - Include usage examples
   - Create API reference documentation

### 4.3 Performance Optimizations
1. **Efficient Data Structures**
   - Use appropriate data structures for screen buffer
   - Optimize field management algorithms
   - Reduce memory allocations

2. **Asyncio Best Practices**
   - Proper exception handling in async contexts
   - Efficient I/O operations
   - Resource cleanup with context managers

## 5. Navigation Method Implementation

### 5.1 Current Navigation Capabilities
Based on the analysis, Pure3270 already implements a comprehensive set of navigation methods:

#### 5.1.1 Cursor Movement
- Absolute positioning: `move_cursor()`, `move_cursor1()`
- Relative movement: `left()`, `right()`, `up()`, `down()`
- Special positions: `home()`, `end()`, `field_end()`

#### 5.1.2 Page Navigation
- `page_up()`, `page_down()`

#### 5.1.3 Field Operations
- `tab()`, `backtab()`
- `erase_input()`, `erase_eof()`
- `delete_field()`, `insert_text()`

#### 5.1.4 AID Functions
- `enter()`, `clear()`
- `pf()`, `pa()`

### 5.2 Simplified Navigation Interface
The refactored navigation will provide:

1. **Unified Movement API**
   ```python
   async def move(self, direction: str, count: int = 1) -> None:
       """Move cursor in specified direction."""

   async def position(self, row: int, col: int, relative: bool = False) -> None:
       """Position cursor at specified coordinates."""
   ```

2. **Action Consolidation**
   ```python
   async def action(self, command: str, *args, **kwargs) -> None:
       """Execute navigation action."""
   ```

### 5.3 Compatibility Layer
Maintain all existing method names as wrappers to the simplified interface:
```python
async def left(self) -> None:
    """Move cursor left one position."""
    return await self.move("left")
```

## 6. Backward Compatibility Preservation

### 6.1 Compatibility Requirements
1. **API Compatibility**: All existing method signatures must continue working
2. **Behavioral Compatibility**: Same output for same inputs
3. **Integration Compatibility**: p3270 patching must continue functioning
4. **Exception Compatibility**: Same exception types and messages

### 6.2 Implementation Strategies

#### 6.2.1 Method Aliases
```python
# Maintain deprecated methods as aliases
def moveCursorUp(self) -> None:  # For p3270 compatibility
    return self.up()
```

#### 6.2.2 Deprecation Warnings
```python
import warnings

def deprecated_method(self) -> None:
    warnings.warn(
        "deprecated_method is deprecated, use new_method instead",
        DeprecationWarning,
        stacklevel=2
    )
    return self.new_method()
```

#### 6.3 Testing Strategy
1. **Regression Testing**: Ensure all existing functionality works
2. **Integration Testing**: Verify p3270 patching still works
3. **Performance Testing**: Confirm no performance degradation
4. **Compatibility Testing**: Test with various p3270 versions

## 7. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
1. Refactor Session/AsyncSession core implementation
2. Consolidate navigation methods
3. Create simplified interface layer

### Phase 2: Modularization (Weeks 3-4)
1. Extract printer functionality to separate module
2. Refactor protocol layer for better separation
3. Optimize data structures and algorithms

### Phase 3: Integration (Weeks 5-6)
1. Update patching mechanism for new structure
2. Maintain all backward compatibility
3. Comprehensive testing and validation

### Phase 4: Documentation (Week 7)
1. Update all documentation
2. Create migration guide
3. Add examples and tutorials

## 8. Risk Mitigation

### 8.1 Compatibility Risks
- **Risk**: Breaking changes to existing integrations
- **Mitigation**: Comprehensive testing with real p3270 usage scenarios

### 8.2 Performance Risks
- **Risk**: Performance degradation from refactoring
- **Mitigation**: Benchmark before and after changes

### 8.3 Feature Loss Risks
- **Risk**: Accidental removal of functionality
- **Mitigation**: Detailed feature mapping and testing

## 9. Success Metrics

1. **Code Quality**: 20% reduction in code complexity metrics
2. **Performance**: Maintained or improved response times
3. **Compatibility**: 100% backward compatibility with existing code
4. **Maintainability**: 30% reduction in duplicated code
5. **Documentation**: 100% API documentation coverage

## 10. Conclusion

This architecture simplification plan aims to make Pure3270 more maintainable and efficient while preserving full compatibility with existing users and integrations. By focusing on clear separation of concerns, reducing duplication, and maintaining backward compatibility, we can create a more robust and developer-friendly library that continues to serve its purpose as a pure Python 3270 emulator.
