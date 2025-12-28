#!/bin/bash
# P0 Ablation Test Script
# Tests the impact of individual P0 features on RLAC performance
# Usage: ./test_p0_ablation.sh <problem_file> [max_rounds]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROBLEM_FILE="${1:-problems/imo01.txt}"
MAX_ROUNDS="${2:-10}"
OUTPUT_DIR="ablation_results_$(date +%Y%m%d_%H%M%S)"
RLAC_MAX_ROUNDS=${MAX_ROUNDS}
RLAC_ROBUST_THRESHOLD=3
RLAC_SOL_REASONING="low"
RLAC_CRITIC_REASONING="medium"
RLAC_VERIFY_EVERY_N_ROUNDS=2
RLAC_VERIFY_START_ROUND=0

# Ensure temperature=0 for all tests
export RLAC_DISABLE_ADAPTIVE_TEMPERATURE=true

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}P0 ABLATION TEST SUITE${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Problem: ${PROBLEM_FILE}"
echo -e "Max rounds: ${MAX_ROUNDS}"
echo -e "Output directory: ${OUTPUT_DIR}"
echo -e "Temperature: 0.0 (deterministic, adaptive disabled)"
echo -e "${BLUE}========================================${NC}\n"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Test configurations
# Format: "test_name|description|env_vars"
declare -a TESTS=(
    "baseline|All P0 features enabled|"
    "no_format_validation|Format validation disabled|RLAC_DISABLE_P0_FORMAT_VALIDATION=true"
    "no_near_success_protection|Near-success protection disabled|RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION=true"
    "no_answer_lock|Answer lock disabled|RLAC_DISABLE_P0_ANSWER_LOCK=true"
    "no_adaptive_temp|Adaptive temperature disabled (redundant)|RLAC_DISABLE_ADAPTIVE_TEMPERATURE=true"
    "all_disabled|All P0 features disabled|RLAC_DISABLE_P0_FORMAT_VALIDATION=true RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION=true RLAC_DISABLE_P0_ANSWER_LOCK=true"
)

# Function to run a single test
run_test() {
    local test_name="$1"
    local description="$2"
    local env_vars="$3"

    echo -e "\n${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Running: ${test_name}${NC}"
    echo -e "${YELLOW}${description}${NC}"
    echo -e "${YELLOW}========================================${NC}\n"

    local log_file="${OUTPUT_DIR}/${test_name}.log"
    local memory_file="${OUTPUT_DIR}/${test_name}_memory.json"
    local start_time=$(date +%s)

    # Set environment variables
    export RLAC_MAX_ROUNDS=${RLAC_MAX_ROUNDS}
    export RLAC_ROBUST_THRESHOLD=${RLAC_ROBUST_THRESHOLD}
    export RLAC_SOL_REASONING=${RLAC_SOL_REASONING}
    export RLAC_CRITIC_REASONING=${RLAC_CRITIC_REASONING}
    export RLAC_VERIFY_EVERY_N_ROUNDS=${RLAC_VERIFY_EVERY_N_ROUNDS}
    export RLAC_VERIFY_START_ROUND=${RLAC_VERIFY_START_ROUND}

    # Always disable adaptive temperature for fair comparison
    export RLAC_DISABLE_ADAPTIVE_TEMPERATURE=true

    # Set test-specific environment variables
    if [ -n "$env_vars" ]; then
        eval "export $env_vars"
    fi

    # Run RLAC
    echo "Command: python code/agent_gpt_oss.py \"${PROBLEM_FILE}\" --use-rlac --log \"${log_file}\" --memory \"${memory_file}\""

    if python code/agent_gpt_oss.py "${PROBLEM_FILE}" \
        --use-rlac \
        --log "${log_file}" \
        --memory "${memory_file}" 2>&1 | tee -a "${log_file}"; then

        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        echo -e "\n${GREEN}✓ Test completed in ${duration}s${NC}"

        # Extract result summary
        local result_summary="${OUTPUT_DIR}/${test_name}_summary.txt"
        echo "Test: ${test_name}" > "${result_summary}"
        echo "Description: ${description}" >> "${result_summary}"
        echo "Duration: ${duration}s" >> "${result_summary}"
        echo "Environment: ${env_vars}" >> "${result_summary}"
        echo "" >> "${result_summary}"

        # Extract key metrics from log
        grep -E "(ROBUST|BROKEN|SUSPICIOUS|Final Answer|P0-v2)" "${log_file}" | tail -20 >> "${result_summary}" || true

        # Check for success
        if grep -q "consecutive ROBUST" "${log_file}"; then
            echo -e "${GREEN}SUCCESS: Solution passed adversarial testing${NC}" >> "${result_summary}"
        else
            echo -e "${RED}FAILED: Solution did not achieve robust threshold${NC}" >> "${result_summary}"
        fi
    else
        echo -e "\n${RED}✗ Test failed or timed out${NC}"
    fi

    # Unset test-specific environment variables
    if [ -n "$env_vars" ]; then
        for var in $env_vars; do
            unset "${var%%=*}"
        done
    fi
}

# Run all tests
test_count=0
for test_config in "${TESTS[@]}"; do
    IFS='|' read -r test_name description env_vars <<< "$test_config"
    run_test "$test_name" "$description" "$env_vars"
    test_count=$((test_count + 1))

    # Brief pause between tests
    echo -e "\nPausing 3s before next test...\n"
    sleep 3
done

# Generate comparison report
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}GENERATING COMPARISON REPORT${NC}"
echo -e "${BLUE}========================================${NC}\n"

REPORT_FILE="${OUTPUT_DIR}/ablation_report.md"

cat > "${REPORT_FILE}" << 'EOF'
# P0 Ablation Test Report

## Executive Summary

This report analyzes the impact of individual P0 features on RLAC performance.

**Test Configuration:**
- Problem: PROBLEM_FILE_PLACEHOLDER
- Max Rounds: MAX_ROUNDS_PLACEHOLDER
- Temperature: 0.0 (deterministic)
- Adaptive Temperature: Disabled for all tests
- Solution Reasoning: low
- Critic Reasoning: medium
- Verification: Every 2 rounds starting from round 0

## P0 Features Tested

1. **Format Validation** (`RLAC_DISABLE_P0_FORMAT_VALIDATION`)
   - Catches extraction bugs before calling verifier
   - Prevents silent failures with empty solutions

2. **Near-Success Protection** (`RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION`)
   - Enhanced grace failure at 2/3 ROBUST
   - History-aware protection at 1/3 ROBUST with total_robust_count >= 2
   - Strong history protection at total_robust_count >= 3

3. **Answer Lock** (`RLAC_DISABLE_P0_ANSWER_LOCK`)
   - Locks answer after 2 consecutive ROBUST verdicts
   - Prevents answer oscillation near success
   - Auto-disabled during P5 reconsideration

4. **Adaptive Temperature** (`RLAC_DISABLE_ADAPTIVE_TEMPERATURE`)
   - Increases temperature to 0.7 when stuck
   - Disabled for all tests to ensure deterministic comparison

## Test Results

EOF

# Replace placeholders
sed -i "s|PROBLEM_FILE_PLACEHOLDER|${PROBLEM_FILE}|g" "${REPORT_FILE}"
sed -i "s|MAX_ROUNDS_PLACEHOLDER|${MAX_ROUNDS}|g" "${REPORT_FILE}"

# Add individual test results
for test_config in "${TESTS[@]}"; do
    IFS='|' read -r test_name description env_vars <<< "$test_config"

    echo "### ${test_name}" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
    echo "**Description:** ${description}" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"

    if [ -f "${OUTPUT_DIR}/${test_name}_summary.txt" ]; then
        echo '```' >> "${REPORT_FILE}"
        cat "${OUTPUT_DIR}/${test_name}_summary.txt" >> "${REPORT_FILE}"
        echo '```' >> "${REPORT_FILE}"
    else
        echo "**Status:** Test did not complete" >> "${REPORT_FILE}"
    fi

    echo "" >> "${REPORT_FILE}"
done

# Add analysis section
cat >> "${REPORT_FILE}" << 'EOF'

## Analysis

### Success Rate by Configuration

| Configuration | Success | Duration | Notes |
|--------------|---------|----------|-------|
EOF

# Extract success data for each test
for test_config in "${TESTS[@]}"; do
    IFS='|' read -r test_name description env_vars <<< "$test_config"

    if [ -f "${OUTPUT_DIR}/${test_name}_summary.txt" ]; then
        duration=$(grep "Duration:" "${OUTPUT_DIR}/${test_name}_summary.txt" | cut -d' ' -f2 || echo "N/A")

        if grep -q "SUCCESS" "${OUTPUT_DIR}/${test_name}_summary.txt"; then
            success="✅ Yes"
        else
            success="❌ No"
        fi

        echo "| ${test_name} | ${success} | ${duration} | ${description} |" >> "${REPORT_FILE}"
    fi
done

cat >> "${REPORT_FILE}" << 'EOF'

### Key Findings

Compare the baseline (all P0 features enabled) with:
1. Individual feature ablations - which single feature has the most impact?
2. Full ablation (all disabled) - what's the cumulative impact?

**Interpretation Guide:**
- If baseline succeeds but ablation fails → Feature is critical
- If both succeed but ablation takes longer → Feature improves efficiency
- If both fail → Problem may be too hard for current configuration
- If ablation succeeds but baseline fails → Unexpected result, investigate further

### Recommendations

Based on the ablation results:

1. **Critical Features** (baseline passes, ablation fails):
   - These features should ALWAYS be enabled

2. **Efficiency Features** (both pass, ablation slower):
   - These features improve performance but aren't strictly necessary

3. **Neutral Features** (no significant difference):
   - These features may need refinement or may be problem-specific

### Next Steps

1. Review logs for critical failures to understand why features matter
2. Run ablation on multiple problems to validate findings
3. Consider feature interactions (some features may depend on others)
4. Test with different problem types (FIND vs PROVE)

EOF

echo -e "${GREEN}Report generated: ${REPORT_FILE}${NC}\n"
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ABLATION TEST COMPLETE${NC}"
echo -e "${BLUE}========================================${NC}\n"
echo -e "Results directory: ${OUTPUT_DIR}"
echo -e "Report: ${REPORT_FILE}"
echo -e "\nTo view the report:"
echo -e "  cat ${REPORT_FILE}"
echo -e "\nTo analyze logs:"
echo -e "  grep 'P0-v2' ${OUTPUT_DIR}/*.log"
echo -e "  grep 'ROBUST\\|BROKEN\\|SUSPICIOUS' ${OUTPUT_DIR}/*.log"
