#!/bin/bash
# Run all agentRAG tests and generate report

set -e

echo "============================================================"
echo "  agentRAG Test Suite Runner"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0

# 1. Unit Tests
echo "📦 Running Unit Tests..."
echo "-----------------------------------------------------------"
if pytest -q --tb=short > /tmp/pytest_output.txt 2>&1; then
    UNIT_PASSED=$(grep -oP '\d+(?= passed)' /tmp/pytest_output.txt || echo "0")
    UNIT_SKIPPED=$(grep -oP '\d+(?= skipped)' /tmp/pytest_output.txt || echo "0")
    TOTAL_PASSED=$((TOTAL_PASSED + UNIT_PASSED))
    TOTAL_SKIPPED=$((TOTAL_SKIPPED + UNIT_SKIPPED))
    echo -e "${GREEN}✓ Unit Tests: $UNIT_PASSED passed, $UNIT_SKIPPED skipped${NC}"
else
    UNIT_FAILED=$(grep -oP '\d+(?= failed)' /tmp/pytest_output.txt || echo "0")
    TOTAL_FAILED=$((TOTAL_FAILED + UNIT_FAILED))
    echo -e "${RED}✗ Unit Tests: $UNIT_FAILED failed${NC}"
    cat /tmp/pytest_output.txt
fi
echo ""

# 2. Integration Tests
echo "🔗 Running Integration Tests..."
echo "-----------------------------------------------------------"
if python scripts/test_mcp_integration.py > /tmp/integration_output.txt 2>&1; then
    INTEGRATION_PASSED=3
    TOTAL_PASSED=$((TOTAL_PASSED + INTEGRATION_PASSED))
    echo -e "${GREEN}✓ Integration Tests: $INTEGRATION_PASSED passed${NC}"
else
    INTEGRATION_FAILED=3
    TOTAL_FAILED=$((TOTAL_FAILED + INTEGRATION_FAILED))
    echo -e "${RED}✗ Integration Tests failed${NC}"
    cat /tmp/integration_output.txt
fi
echo ""

# 3. Scenario Tests
echo "🎯 Running Scenario Tests..."
echo "-----------------------------------------------------------"
if python scripts/test_scenarios.py > /tmp/scenario_output.txt 2>&1; then
    SCENARIO_PASSED=$(grep -oP '✓ Passed: \K\d+' /tmp/scenario_output.txt || echo "0")
    TOTAL_PASSED=$((TOTAL_PASSED + SCENARIO_PASSED))
    echo -e "${GREEN}✓ Scenario Tests: $SCENARIO_PASSED passed${NC}"
else
    SCENARIO_FAILED=$(grep -oP '✗ Failed: \K\d+' /tmp/scenario_output.txt || echo "0")
    TOTAL_FAILED=$((TOTAL_FAILED + SCENARIO_FAILED))
    echo -e "${RED}✗ Scenario Tests: $SCENARIO_FAILED failed${NC}"
    cat /tmp/scenario_output.txt
fi
echo ""

# Summary
echo "============================================================"
echo "  Test Summary"
echo "============================================================"
TOTAL_TESTS=$((TOTAL_PASSED + TOTAL_FAILED + TOTAL_SKIPPED))
SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($TOTAL_PASSED / $TOTAL_TESTS) * 100}")

echo ""
echo "Total Tests:   $TOTAL_TESTS"
echo -e "${GREEN}Passed:        $TOTAL_PASSED${NC}"
if [ $TOTAL_FAILED -gt 0 ]; then
    echo -e "${RED}Failed:        $TOTAL_FAILED${NC}"
else
    echo "Failed:        $TOTAL_FAILED"
fi
if [ $TOTAL_SKIPPED -gt 0 ]; then
    echo -e "${YELLOW}Skipped:       $TOTAL_SKIPPED${NC}"
fi
echo ""
echo "Success Rate:  $SUCCESS_RATE%"
echo ""

# Final status
if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    echo ""
    echo "See docs/TEST_REPORT.md for detailed results."
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed${NC}"
    exit 1
fi
