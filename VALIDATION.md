# Pure3270 Validation Guide

This document describes the comprehensive validation system for Pure3270, designed to ensure protocol compliance, emulation accuracy, and performance without requiring external network access.

## Overview

Pure3270's validation system consists of multiple independent approaches that work together to provide thorough testing:

- **Terminal Model Validation**: Tests all supported IBM 3270 terminal configurations
- **Protocol State Machine Testing**: Validates TN3270 handler state transitions
- **Synthetic Data Stream Testing**: Generates and parses valid TN3270 data streams
- **Screen Buffer Regression Testing**: Tests screen buffer operations and rendering
- **Trace Replay Testing**: Validates against real s3270 trace files
- **Performance Benchmarking**: Measures performance of core operations
- **Integration Testing**: Combines multiple validation approaches

## Quick Start

### Run All Validation
```bash
# Run the complete offline validation suite
python tools/run_offline_validation.py
```

### Run Individual Components
```bash
# Terminal model tests (68 parameterized tests)
python -m pytest tests/test_terminal_models.py -v

# Protocol state machine tests
python tests/test_protocol_state_machine.py

# Synthetic data generation and testing
python tools/synthetic_data_generator.py generate test_data 10
python tools/synthetic_data_generator.py test test_data/synthetic_test_cases.json

# Screen buffer regression testing
python tools/screen_buffer_regression_test.py generate test_output 5
python tools/screen_buffer_regression_test.py run test_output

# Performance benchmarking
python tools/performance_benchmark.py

# Trace replay testing
python tools/test_trace_replay.py tests/data/traces/target.trc
```

## Validation Components

### 1. Terminal Model Validation

Tests all 13 IBM 3270 terminal models with different screen sizes and capabilities:

- 3278-2/3/4/5 (24x80, 32x80, 43x80, 27x132)
- 3279-2/3/4/5 (Color variants)
- 3179-2 (17x132)
- 3270PC variants (G, GA, GX)
- DYNAMIC (Runtime-configurable)

**Files**: `tests/test_terminal_models.py`

### 2. Protocol State Machine Testing

Validates TN3270 handler state transitions, history tracking, and concurrent safety.

**Files**: `tests/test_protocol_state_machine.py`

### 3. Synthetic Data Stream Testing

Generates valid TN3270 data streams with various protocol orders and tests parsing:

- Write Control Character (WCC)
- Set Buffer Address (SBA)
- Start Field (SF)
- Set Attribute (SA)
- Repeat to Address (RA)
- Insert Cursor (IC)
- Start Field Extended (SFE)

**Files**: `tools/synthetic_data_generator.py`

### 4. Screen Buffer Regression Testing

Automated regression testing for screen buffer operations:

- Text writing and cursor movement
- Field attribute handling
- Protected/unprotected field logic
- Screen clearing and positioning

**Files**: `tools/screen_buffer_regression_test.py`

### 5. Trace Replay Testing

Validates Pure3270 against real s3270 trace files captured from actual TN3270 sessions.

**Files**: `tools/trace_replay_server.py`, `tools/test_trace_replay.py`

### 6. Performance Benchmarking

Measures performance of core operations:

- Screen buffer write/read operations
- Data stream parsing
- Addressing calculations

**Files**: `tools/performance_benchmark.py`

### 7. Integration Testing

Combines multiple validation approaches in comprehensive test suites.

**Files**: `tests/test_integration_validation.py`

## CI/CD Integration

Offline validation is automatically run in CI/CD pipelines:

```yaml
- name: Run offline validation
  run: |
    python tools/run_offline_validation.py
```

This ensures all changes are validated before merging.

## Adding New Validation

### For New Features

1. **Identify validation needs**: Determine which validation approaches apply to your feature
2. **Add unit tests**: Create pytest tests in `tests/`
3. **Add integration tests**: Update `tests/test_integration_validation.py` if needed
4. **Update offline validation**: Modify `tools/run_offline_validation.py` to include new tests
5. **Document**: Update this guide with new validation procedures

### For Protocol Changes

1. **Update synthetic data generation**: Add new protocol orders to `synthetic_data_generator.py`
2. **Add trace files**: Include new s3270 traces in `tests/data/traces/`
3. **Update benchmarks**: Modify performance tests to cover new operations
4. **Validate compliance**: Ensure all existing validation still passes

## Troubleshooting

### Validation Failures

- **Terminal model tests fail**: Check screen buffer implementation for the failing model
- **Synthetic data parsing fails**: Verify TN3270 handler correctly processes the data stream
- **Trace replay mismatches**: Compare Pure3270 behavior with s3270 expectations
- **Performance regressions**: Identify bottlenecks in the failing benchmark

### Common Issues

- **Import errors**: Ensure `pure3270` is properly installed (`pip install -e .`)
- **Timeout errors**: Some validation tests may take time; increase timeouts if needed
- **Memory issues**: Large synthetic data sets may require more memory

## Contributing

When contributing validation improvements:

1. Follow existing patterns in the codebase
2. Add comprehensive error handling
3. Include clear documentation and examples
4. Update this guide with new procedures
5. Ensure all validation passes before submitting PRs

## Related Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - General contribution guidelines
- [CI_CD.md](CI_CD.md) - CI/CD pipeline documentation
- [API_COMPATIBILITY_AUDIT.md](API_COMPATIBILITY_AUDIT.md) - API compatibility testing
- [TRACE_RESEARCH_SUMMARY.md](TRACE_RESEARCH_SUMMARY.md) - Trace analysis research
