# Summary of Changes for p3270 Patching Improvements

## Overview
This PR makes several important improvements to how pure3270 handles p3270 patching:

1. Added p3270 as a test dependency
2. Fixed p3270 version detection to work with the actual installed version
3. Created proper integration tests that test with the real p3270 package
4. Updated documentation to reflect the correct version

## Detailed Changes

### 1. Dependency Management
- Added `p3270 >= 0.1.6` to the test dependencies in `pyproject.toml`

### 2. Version Detection Fix
- Updated `get_p3270_version()` in `pure3270/emulation/ebcdic.py` to properly detect the p3270 version using `importlib.metadata`
- The function now correctly returns "0.1.6" for the currently installed version
- Added fallback mechanism for older Python versions

### 3. Patching Logic Updates
- Modified `pure3270/patching/patching.py` to use the proper version detection
- Updated the default expected version from "0.3.0" to "0.1.6" to match the actual installed version
- Fixed version compatibility checking to work with the actual p3270 package

### 4. New Integration Tests
- Created `tests/test_patching_integration.py` with comprehensive tests that actually use the real p3270 package
- Tests include:
  - Real p3270 patching functionality
  - Version detection accuracy
  - Version checking with both strict and non-strict modes
  - Proper unpatching functionality

### 5. Test Updates
- Updated existing tests in `tests/test_patching.py` and `tests/test_patching_advanced.py` to reflect the new version
- Fixed a recursion issue in one of the mock tests
- Added proper imports for sys module where needed

### 6. Documentation Updates
- Updated README.md to reflect the correct p3270 version (0.1.6 instead of 0.3.0)

## Verification
- All patching tests pass (43/43)
- Integration tests with real p3270 package pass
- Manual verification script confirms patching works correctly
- Version detection works accurately

## Impact
These changes ensure that:
1. pure3270 can properly detect and work with the actual installed version of p3270
2. Integration tests actually test with the real package, not just mocks
3. The patching functionality is more robust and reliable
4. Users get accurate information about version compatibility