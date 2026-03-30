#!/bin/bash
# Quick validation script for pure3270
# Run this to verify the project actually works

set -e

echo "=========================================="
echo "  PURE3270 VALIDATION"
echo "  $(date)"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test and check result
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo -n "Testing: $test_name... "
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to run a test and show output
run_test_verbose() {
    local test_name="$1"
    local test_command="$2"

    echo ""
    echo "=========================================="
    echo "Testing: $test_name"
    echo "=========================================="
    if eval "$test_command"; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "Level 1: Core Functionality"
echo "----------------------------------------"

# Test 1: Quick smoke test
run_test_verbose "Quick Smoke Test" "python quick_test.py"

# Test 2: RFC 854 IAC escaping
run_test "RFC 854 IAC Escaping" \
    "python -m pytest tests/test_rfc854_iac_escaping.py -q"

# Test 3: RFC 854 Telnet commands
run_test "RFC 854 Telnet Commands" \
    "python -m pytest tests/test_rfc854_telnet_commands.py -q"

# Test 4: RFC 2355 keep-alive
run_test "RFC 2355 Keep-Alive" \
    "python -m pytest tests/test_rfc2355_keepalive.py -q"

# Test 5: Protocol tests
run_test "Protocol Tests" \
    "python -m pytest tests/test_protocol.py::TestDataStreamParser -q"

echo ""
echo "Level 2: Asset Verification"
echo "----------------------------------------"

# Test 6: Trace files exist
TRACE_COUNT=$(ls *.trc 2>/dev/null | wc -l)
if [ "$TRACE_COUNT" -gt 0 ]; then
    echo -e "Trace Files: ${GREEN}$TRACE_COUNT found${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Trace Files: ${RED}None found${NC}"
    ((TESTS_FAILED++))
fi

# Test 7: Test files exist
TEST_COUNT=$(ls tests/test_*.py 2>/dev/null | wc -l)
if [ "$TEST_COUNT" -gt 50 ]; then
    echo -e "Test Files: ${GREEN}$TEST_COUNT found${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Test Files: ${YELLOW}$TEST_COUNT found (expected 50+)${NC}"
fi

# Test 8: Example files exist
EXAMPLE_COUNT=$(ls examples/*.py 2>/dev/null | wc -l)
if [ "$EXAMPLE_COUNT" -gt 10 ]; then
    echo -e "Example Files: ${GREEN}$EXAMPLE_COUNT found${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Example Files: ${YELLOW}$EXAMPLE_COUNT found${NC}"
fi

echo ""
echo "Level 3: Sample Trace Analysis"
echo "----------------------------------------"

# Test 9: Analyze first trace file
FIRST_TRACE=$(ls *.trc 2>/dev/null | head -1)
if [ -n "$FIRST_TRACE" ]; then
    echo -n "Analyzing trace: $FIRST_TRACE... "
    python -c "
import sys
trace_file = '$FIRST_TRACE'
try:
    with open(trace_file, 'rb') as f:
        data = f.read()
        if len(data) > 0:
            print(f'✓ Read {len(data)} bytes')
            sys.exit(0)
        else:
            print('✗ Empty file')
            sys.exit(1)
except Exception as e:
    print(f'✗ Error: {e}')
    sys.exit(1)
" 2>&1
    if [ $? -eq 0 ]; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
else
    echo -e "Trace Analysis: ${YELLOW}No trace files available${NC}"
fi

echo ""
echo "Level 4: Test Collection"
echo "----------------------------------------"

# Test 10: Count available tests
echo -n "Collecting tests... "
TEST_SUMMARY=$(python -m pytest tests/ --collect-only -q 2>&1 | tail -1)
if echo "$TEST_SUMMARY" | grep -q "test"; then
    echo -e "${GREEN}$TEST_SUMMARY${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}Failed to collect tests${NC}"
    ((TESTS_FAILED++))
fi

echo ""
echo "=========================================="
echo "  VALIDATION SUMMARY"
echo "=========================================="
echo ""
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "  ✓ ALL VALIDATION CHECKS PASSED"
    echo "==========================================${NC}"
    echo ""
    echo "Pure3270 is working correctly!"
    echo ""
    echo "Next recommended steps:"
    echo "  1. Run: python examples/batch_trace_test.py"
    echo "  2. Run: python examples/automated_trace_test_suite.py"
    echo "  3. Test: python examples/example_pub400.py"
    exit 0
else
    echo -e "${RED}=========================================="
    echo "  ✗ SOME VALIDATION CHECKS FAILED"
    echo "==========================================${NC}"
    echo ""
    echo "Please review the failures above."
    echo "Common issues:"
    echo "  - Missing dependencies (run: pip install -e .)"
    echo "  - Python version (requires 3.10+)"
    echo "  - File permissions"
    exit 1
fi
