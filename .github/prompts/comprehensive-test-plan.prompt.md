# Comprehensive Test Plan Generator

## Goal
Generate a comprehensive test plan for Pure3270 features, including unit tests, integration tests, property-based tests, and validation scenarios.

## Context
Pure3270 has 1,105+ tests covering protocol emulation, API compatibility, and integration scenarios. New features require comprehensive test coverage following project conventions.

## Test Categories

### 1. Unit Tests (`tests/unit/`)
- Isolated component testing
- Mock external dependencies
- Fast execution (<100ms per test)
- 100% code path coverage

### 2. Integration Tests (`tests/integration/`)
- Live host connections (pub400.com, etc.)
- Real TN3270 server interactions
- Mark with `@pytest.mark.integration`
- May flake due to network

### 3. Property-Based Tests (`tests/property/`)
- Hypothesis-driven testing
- Generate edge cases automatically
- Invariant validation
- Stateful testing for protocols

### 4. Protocol Validation Tests
- RFC compliance verification
- Byte-level accuracy
- Negotiation sequence validation
- Error handling

### 5. API Compatibility Tests
- p3270.P3270Client parity
- Drop-in replacement validation
- Method signature matching
- Behavior equivalence

## Steps

### 1. Analyze Feature Requirements
- Identify all code paths
- Map error conditions
- Define success criteria
- List edge cases

### 2. Design Test Structure
```python
tests/
+-- unit/
|   +-- test_[feature].py
+-- integration/
|   +-- test_[feature]_integration.py
+-- property/
|   +-- test_[feature]_properties.py
+-- [feature]_validation.py
```

### 3. Create Test Cases

#### Unit Test Template
```python
import pytest
from pure3270.[module] import [Component]

class Test[Component]:
    """Test [component] functionality."""

    def test_happy_path(self):
        """Test normal operation."""
        # Arrange
        # Act
        # Assert

    def test_edge_case_[description](self):
        """Test [specific edge case]."""
        # Arrange
        # Act
        # Assert

    def test_error_handling(self):
        """Test error conditions."""
        # Arrange
        # Act & Assert
        with pytest.raises(ExpectedError):
            # operation
```

#### Integration Test Template
```python
import pytest
from pure3270 import Session

@pytest.mark.integration
def test_[feature]_with_real_host():
    """Test [feature] against real TN3270 host."""
    with Session() as session:
        session.connect('pub400.com')
        # Test operations
        assert expected_result
```

#### Property-Based Test Template
```python
from hypothesis import given, strategies as st
from hypothesis.stateful import RuleBasedStateMachine

@given(st.data())
def test_[property](data):
    """Test [property] holds for all inputs."""
    # Arrange
    # Act
    # Assert invariant holds
```

### 4. Define Validation Scenarios
- Normal operation
- Boundary conditions
- Error states
- Race conditions
- Resource cleanup
- Concurrent access

### 5. Add Test Markers
```python
@pytest.mark.slow          # Long-running tests
@pytest.mark.integration   # Requires network
@pytest.mark.property      # Hypothesis tests
@pytest.mark.timeout(30)   # Timeout in seconds
```

## Output Format

```markdown
# Test Plan: [Feature Name]

## Overview
- **Feature**: [Description]
- **Priority**: [High/Medium/Low]
- **Estimated Tests**: [count]
- **Dependencies**: [list]

## Test Categories

### Unit Tests ([count] tests)
#### Test File: `tests/unit/test_[feature].py`

**Test Cases**:
1. `test_[scenario_1]` - [Description]
2. `test_[scenario_2]` - [Description]
3. `test_[error_condition]` - [Description]

**Code Paths**:
- [ ] Happy path
- [ ] Edge case 1
- [ ] Edge case 2
- [ ] Error handling
- [ ] Resource cleanup

### Integration Tests ([count] tests)
#### Test File: `tests/integration/test_[feature]_integration.py`

**Test Scenarios**:
1. `test_[feature]_pub400` - Test against pub400.com
2. `test_[feature]_secure` - Test with SSL/TLS
3. `test_[feature]_timeout` - Test timeout handling

**Hosts**:
- pub400.com (port 23)
- pub400.com (port 992, SSL)
- [Other hosts]

### Property-Based Tests ([count] tests)
#### Test File: `tests/property/test_[feature]_properties.py`

**Invariants**:
1. [Invariant 1] - Always holds
2. [Invariant 2] - State consistency
3. [Invariant 3] - Resource bounds

**Stateful Tests**:
- State machine: [description]
- Transitions: [list]
- Invariants: [list]

### Protocol Validation ([count] tests)
#### Test File: `tests/test_[feature]_protocol.py`

**RFC Compliance**:
- RFC [number] Section [X.Y]
- Test: [description]

**Byte-Level Validation**:
- Test: [specific byte sequences]
- Expected: [exact bytes]

## Implementation Plan

### Phase 1: Unit Tests
1. Create test file structure
2. Implement happy path tests
3. Add edge case tests
4. Implement error handling tests

### Phase 2: Integration Tests
1. Set up test fixtures
2. Implement live host tests
3. Add timeout/retry logic
4. Validate against multiple hosts

### Phase 3: Property Tests
1. Define invariants
2. Create Hypothesis strategies
3. Implement stateful tests
4. Run for extended period

### Phase 4: Validation
1. Run full test suite
2. Verify coverage
3. Check for flakiness
4. Document known issues

## Coverage Goals
- **Line Coverage**: >90%
- **Branch Coverage**: >85%
- **Path Coverage**: All critical paths
- **Edge Cases**: All identified

## Validation Commands
```bash
# Run unit tests
python -m pytest tests/unit/test_[feature].py -v

# Run integration tests
python -m pytest tests/integration/test_[feature]_integration.py -v

# Run property tests (extended)
python -m pytest tests/property/test_[feature]_properties.py --hypothesis-seed=0

# Check coverage
python -m pytest tests/ --cov=pure3270.[module] --cov-report=html

# Full validation
python run_all_tests.py
python run_full_ci.py
```

## Success Criteria
- [ ] All unit tests pass
- [ ] Integration tests pass (allowing for network flakiness)
- [ ] Property tests run without counterexamples
- [ ] Coverage goals met
- [ ] No flaky tests
- [ ] Documentation updated
- [ ] Linting passes (flake8, mypy)

## Risks & Mitigations
- **Network flakiness**: Mock where possible, retry logic
- **Test duration**: Mark slow tests, parallelize
- **False positives**: Add assertions, validate assumptions
- **Maintenance**: Keep tests simple, document intent
```

## Examples

### Example: TN3270E Header Processing

**User**:
```
Generate a test plan for TN3270E enhanced header validation
```

**Agent Response**:
```markdown
# Test Plan: TN3270E Enhanced Header Validation

## Overview
- **Feature**: TN3270E header parsing and validation
- **Priority**: High
- **Estimated Tests**: 25
- **Dependencies**: RFC 2355 compliance

## Test Categories

### Unit Tests (15 tests)
#### Test File: `tests/unit/test_tn3270e_header.py`

**Test Cases**:
1. `test_parse_data_header` - Parse standard DATA header
2. `test_parse_response_header` - Parse RESPONSE header
3. `test_parse_negative_response` - Parse negative response
4. `test_invalid_header_format` - Reject malformed headers
5. `test_missing_fields` - Handle missing optional fields
6. `test_extended_flags` - Parse extended flag combinations
7. `test_code_point_validation` - Validate TN3270E code points
8. `test_lu_name_parsing` - Parse LU name from header
9. `test_user_id_extraction` - Extract user ID from header
10. `test_code_page_handling` - Handle different code pages

[More test cases...]

### Integration Tests (5 tests)
#### Test File: `tests/integration/test_tn3270e_headers_integration.py`

**Test Scenarios**:
1. `test_headers_from_pub400` - Validate headers from pub400.com
2. `test_headers_with_ssl` - Test TN3270E over SSL
3. `test_error_responses` - Test server error responses
4. `test_printer_session_headers` - Printer session headers
5. `test_lu_lu_session_headers` - LU-LU session headers

[Continue with full plan...]
```

## Constraints

- **FOLLOW** Pure3270 test conventions
- **USE** pytest fixtures from `conftest.py`
- **MARK** integration tests appropriately
- **INCLUDE** both positive and negative tests
- **VALIDATE** with `quick_test.py` after implementation
- **ENSURE** linting passes (flake8, mypy)

## Related Prompts

- `/prompt rfc-compliance-review` - Review protocol compliance
- `/prompt create-implementation-plan` - Plan implementation
- `/chatmode tdd-green` - Write tests first
- `/chatmode tdd-red` - Make tests pass

---

**Usage**: `/prompt comprehensive-test-plan`
**Category**: Testing, Quality Assurance
**Expertise Level**: Intermediate to Advanced
