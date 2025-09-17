# Archived Old CI Scripts

This directory contains CI and test scripts that were made redundant by the modernized CI system implemented in September 2025.

## Replaced By

The functionality of these scripts has been consolidated into:
- **`ci.sh`** - Main shell entry point for all CI operations
- **`run_full_ci.py`** - Comprehensive Python CI runner matching GitHub Actions
- **`local_ci.py`** - Python wrapper with common presets
- **`quick_test.py`** - Fast smoke test (kept in root)
- **GitHub Actions workflows** - Cloud-based CI/CD

## Archived Scripts

### Comprehensive Test Runners (Redundant)
- **`run_all_tests.py`** - Old comprehensive test runner with custom timeout/memory management
- **`run_working_tests.py`** - Focused on "working tests" subset
- **`comprehensive_test.py`** - Another comprehensive test implementation
- **`comprehensive_integration_test.py`** - Yet another integration test variant
- **`release_test.py`** - Release validation testing

### CI-Specific Scripts (Redundant)
- **`ci_test.py`** - Old CI test script with memory limiting
- **`run_static_analysis.py`** - Static analysis runner (mypy, pylint, bandit)

### Integration Test Scripts (Redundant)
- **`integration_test.py`** - Basic integration tests, replaced by `tests/test_integration.py`

### Broken/Experimental Scripts
- **`run_capture.py`** - Network capture script with missing dependencies
- **`run_capture_fixed.py`** - Fixed version of capture script with missing dependencies
- **`send_device_type_and_capture.py`** - Protocol capture script with missing dependencies

These scripts depend on `BindImageMockServer` which was never implemented.

## Migration Notes

1. **Test Coverage**: All test functionality has been migrated to the proper `tests/` directory structure with pytest
2. **Static Analysis**: Now handled by `run_full_ci.py` with better tool integration
3. **Memory/Timeout Management**: Improved implementation in the new CI system
4. **GitHub Actions Parity**: New system exactly matches cloud CI workflows

## Date Archived
September 17, 2025

## Safe to Delete
These files can be safely deleted in the future - they are preserved here only for historical reference.
