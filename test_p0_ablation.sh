#!/bin/bash
# P0 Ablation Test Script
# Tests the impact of individual P0 features on BFS performance
# Usage: ./test_p0_ablation.sh <problem_file> [num_runs]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROBLEM_FILE="${1:-problems/imo01.txt}"
NUM_RUNS="${2:-12}"  # Number of BFS runs per configuration
OUTPUT_DIR="ablation_results_$(date +%Y%m%d_%H%M%S)"

# BFS configuration
SOLUTION_REASONING="medium"
VERIFICATION_REASONING="high"
SELF_IMPROVEMENT_REASONING="medium"
NUM_INITIAL_ATTEMPTS=3
MAX_RUNS=15

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}P0 ABLATION TEST SUITE (BFS)${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Problem: ${PROBLEM_FILE}"
echo -e "Runs per config: ${NUM_RUNS}"
echo -e "Output directory: ${OUTPUT_DIR}"
echo -e "Strategy: BFS with ${NUM_INITIAL_ATTEMPTS} initial attempts"
echo -e "Max iterations: ${MAX_RUNS}"
echo -e "${BLUE}========================================${NC}\n"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Test configurations
# Format: "test_name|description|env_vars"
# Note: P0 features are primarily for RLAC, but we test to ensure no interference with BFS
declare -a TESTS=(
    "baseline|All P0 features enabled (baseline)|"
    "no_format_validation|Format validation disabled|RLAC_DISABLE_P0_FORMAT_VALIDATION=true"
    "no_near_success_protection|Near-success protection disabled|RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION=true"
    "no_answer_lock|Answer lock disabled|RLAC_DISABLE_P0_ANSWER_LOCK=true"
    "all_disabled|All P0 features disabled|RLAC_DISABLE_P0_FORMAT_VALIDATION=true RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION=true RLAC_DISABLE_P0_ANSWER_LOCK=true"
)

# Function to run a single BFS test configuration
run_test() {
    local test_name="$1"
    local description="$2"
    local env_vars="$3"

    echo -e "\n${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Running: ${test_name}${NC}"
    echo -e "${YELLOW}${description}${NC}"
    echo -e "${YELLOW}Running ${NUM_RUNS} BFS iterations...${NC}"
    echo -e "${YELLOW}========================================${NC}\n"

    local config_dir="${OUTPUT_DIR}/${test_name}"
    mkdir -p "${config_dir}"

    local start_time=$(date +%s)
    local success_count=0
    local total_iterations=0
    local total_duration=0

    # Set test-specific environment variables
    if [ -n "$env_vars" ]; then
        eval "export $env_vars"
    fi

    # Run N BFS tests for this configuration
    for run_num in $(seq 1 ${NUM_RUNS}); do
        local log_file="${config_dir}/bfs_run${run_num}.log"
        local memory_file="${config_dir}/bfs_run${run_num}.json"

        echo -e "${BLUE}[${test_name}] Run ${run_num}/${NUM_RUNS}${NC}"

        local run_start=$(date +%s)

        # Run BFS agent (no --use-rlac, use --num-initial-attempts for BFS)
        if python code/agent_gpt_oss.py "${PROBLEM_FILE}" \
            --log "${log_file}" \
            --memory "${memory_file}" \
            --num-initial-attempts ${NUM_INITIAL_ATTEMPTS} \
            --max_runs ${MAX_RUNS} \
            --solution-reasoning "${SOLUTION_REASONING}" \
            --verification-reasoning "${VERIFICATION_REASONING}" \
            --self-improvement-reasoning "${SELF_IMPROVEMENT_REASONING}" \
            2>&1 | tee -a "${log_file}" > /dev/null; then

            # Check for success
            if grep -q "Correct solution found (first success)" "${log_file}" 2>/dev/null; then
                ((success_count++))
                echo -e "${GREEN}✓ Run ${run_num}: SUCCESS${NC}"
            else
                echo -e "${RED}✗ Run ${run_num}: FAILED${NC}"
            fi

            # Extract iteration count
            local iterations=$(grep "Iteration [0-9]" "${log_file}" | tail -1 | sed -n 's/.*Iteration \([0-9][0-9]*\).*/\1/p' || echo "0")
            if [ -z "$iterations" ]; then iterations="0"; fi
            total_iterations=$((total_iterations + iterations))
        else
            echo -e "${RED}✗ Run ${run_num}: ERROR${NC}"
        fi

        local run_end=$(date +%s)
        local run_duration=$((run_end - run_start))
        total_duration=$((total_duration + run_duration))

        echo "  Duration: ${run_duration}s, Iterations: ${iterations}"

        # Brief pause between runs
        sleep 1
    done

    local end_time=$(date +%s)
    local total_time=$((end_time - start_time))

    # Calculate statistics
    local success_rate=0
    if [ ${NUM_RUNS} -gt 0 ]; then
        success_rate=$((success_count * 100 / NUM_RUNS))
    fi

    local avg_iterations=0
    if [ ${NUM_RUNS} -gt 0 ]; then
        avg_iterations=$((total_iterations / NUM_RUNS))
    fi

    local avg_duration=0
    if [ ${NUM_RUNS} -gt 0 ]; then
        avg_duration=$((total_duration / NUM_RUNS))
    fi

    echo -e "\n${GREEN}✓ Configuration completed in ${total_time}s${NC}"
    echo -e "  Success rate: ${success_count}/${NUM_RUNS} (${success_rate}%)"
    echo -e "  Avg iterations: ${avg_iterations}"
    echo -e "  Avg duration: ${avg_duration}s"

    # Save summary
    local result_summary="${OUTPUT_DIR}/${test_name}_summary.txt"
    cat > "${result_summary}" << EOF
Test: ${test_name}
Description: ${description}
Environment: ${env_vars}

Results:
  Total runs: ${NUM_RUNS}
  Successes: ${success_count}
  Failures: $((NUM_RUNS - success_count))
  Success rate: ${success_rate}%
  Average iterations: ${avg_iterations}
  Average duration: ${avg_duration}s
  Total time: ${total_time}s
EOF

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
# P0 Ablation Test Report (BFS)

## Executive Summary

This report analyzes the impact of individual P0 features on BFS performance.

**Test Configuration:**
- Problem: PROBLEM_FILE_PLACEHOLDER
- Runs per config: NUM_RUNS_PLACEHOLDER
- Strategy: Best-First Search (BFS)
- Initial attempts: 3
- Max iterations: 15
- Solution Reasoning: medium
- Verification Reasoning: high
- Self-Improvement Reasoning: medium

## P0 Features Tested

**Note:** P0 features were designed for RLAC, but we test them with BFS to ensure:
1. No interference with BFS exploration
2. Potential benefits for iterative refinement
3. Baseline comparison for future RLAC ablation

1. **Format Validation** (`RLAC_DISABLE_P0_FORMAT_VALIDATION`)
   - Catches extraction bugs before calling verifier
   - Prevents silent failures with empty solutions

2. **Near-Success Protection** (`RLAC_DISABLE_P0_NEAR_SUCCESS_PROTECTION`)
   - Enhanced grace failure at 2/3 ROBUST (RLAC-specific)
   - May affect BFS verification feedback loop

3. **Answer Lock** (`RLAC_DISABLE_P0_ANSWER_LOCK`)
   - Locks answer after 2 consecutive ROBUST verdicts (RLAC-specific)
   - May prevent answer changes during BFS refinement

## Test Results

EOF

# Replace placeholders
sed -i "s|PROBLEM_FILE_PLACEHOLDER|${PROBLEM_FILE}|g" "${REPORT_FILE}"
sed -i "s|NUM_RUNS_PLACEHOLDER|${NUM_RUNS}|g" "${REPORT_FILE}"

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

| Configuration | Success Rate | Avg Iterations | Avg Duration | Notes |
|--------------|--------------|----------------|--------------|-------|
EOF

# Extract success data for each test
for test_config in "${TESTS[@]}"; do
    IFS='|' read -r test_name description env_vars <<< "$test_config"

    if [ -f "${OUTPUT_DIR}/${test_name}_summary.txt" ]; then
        success_rate=$(grep "Success rate:" "${OUTPUT_DIR}/${test_name}_summary.txt" | sed -n 's/.*Success rate: \([0-9]*\)%.*/\1/p' || echo "N/A")
        avg_iterations=$(grep "Average iterations:" "${OUTPUT_DIR}/${test_name}_summary.txt" | sed -n 's/.*Average iterations: \([0-9]*\).*/\1/p' || echo "N/A")
        avg_duration=$(grep "Average duration:" "${OUTPUT_DIR}/${test_name}_summary.txt" | sed -n 's/.*Average duration: \([0-9]*\)s.*/\1/p' || echo "N/A")

        # Add checkmark/cross for success rate
        if [ "$success_rate" != "N/A" ] && [ "$success_rate" -ge 70 ]; then
            display_rate="✅ ${success_rate}%"
        elif [ "$success_rate" != "N/A" ] && [ "$success_rate" -ge 40 ]; then
            display_rate="⚠️ ${success_rate}%"
        elif [ "$success_rate" != "N/A" ]; then
            display_rate="❌ ${success_rate}%"
        else
            display_rate="N/A"
        fi

        echo "| ${test_name} | ${display_rate} | ${avg_iterations} | ${avg_duration}s | ${description} |" >> "${REPORT_FILE}"
    fi
done

cat >> "${REPORT_FILE}" << 'EOF'

### Key Findings

Compare the baseline (all P0 features enabled) with:
1. Individual feature ablations - which single feature has the most impact?
2. Full ablation (all disabled) - what's the cumulative impact?

**Interpretation Guide (for BFS):**
- **Success rate difference ≥20%** → Feature has MAJOR impact
- **Success rate difference 10-20%** → Feature has MODERATE impact
- **Success rate difference <10%** → Feature has MINIMAL impact
- **Baseline worse than ablation** → Feature may interfere with BFS

**Expected Impact:**
Since P0 features were designed for RLAC:
- **Format validation**: Should help BFS (catches bugs early)
- **Near-success protection**: May not affect BFS (RLAC-specific logic)
- **Answer lock**: May HURT BFS (prevents exploration)

### Recommendations

Based on the ablation results:

1. **Critical Features** (≥20% success rate drop when disabled):
   - These features should ALWAYS be enabled for BFS

2. **Beneficial Features** (10-20% success rate drop when disabled):
   - These features improve performance, recommended for production

3. **Neutral Features** (<10% difference):
   - These features may be RLAC-specific, safe to disable for BFS

4. **Harmful Features** (success rate increases when disabled):
   - These features should be DISABLED for BFS (interference detected)

### Next Steps

1. **If format_validation is critical**: Keep enabled, document benefit
2. **If answer_lock hurts BFS**: Add flag to disable for BFS mode
3. **If near_success_protection is neutral**: RLAC-specific, no BFS impact
4. Run ablation on multiple problems (imo02-imo05) to validate findings
5. Test with different problem types (FIND vs PROVE) for context extraction

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
echo -e "  grep 'Correct solution found' ${OUTPUT_DIR}/*/*.log | wc -l"
echo -e "  grep 'Iteration' ${OUTPUT_DIR}/*/*.log | tail -20"
echo -e "\nTo compare success rates:"
echo -e "  for dir in ${OUTPUT_DIR}/*/; do echo \"\$dir: \$(grep -l 'Correct solution found' \$dir/*.log | wc -l)/${NUM_RUNS}\"; done"
