#!/bin/bash
# Phase 0: Diagnostic Tests for A/B Test Fix (PARALLEL EXECUTION)
# Purpose: Identify root cause of early termination and low feedback utilization
# Expected duration: 2-4 hours wall-clock time with parallel execution

set -e  # Exit on error

PROBLEM="problems/imo01.txt"
OUTPUT_DIR="diagnostic_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAX_PARALLEL=${MAX_PARALLEL:-6}  # Max parallel jobs (default: 6 for all tests at once)
PIDS=()  # Array to track background job PIDs

# Create output directory
mkdir -p "$OUTPUT_DIR"

# ANSI color codes for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Clean up old memory files from previous runs to prevent resume loops
# (Keep old logs for reference, but remove .json to force fresh runs)
if [ -d "$OUTPUT_DIR" ]; then
    old_json_count=$(ls "$OUTPUT_DIR"/*.json 2>/dev/null | wc -l)
    if [ "$old_json_count" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Found $old_json_count old .json memory files from previous runs${NC}"
        echo "   Removing to prevent resume loops with stuck states (resume_count=59)..."
        rm -f "$OUTPUT_DIR"/*.json
        echo -e "${GREEN}   ✓ Cleaned up old memory files${NC}"
        echo ""
    fi
fi

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}Phase 0: A/B Test Diagnostics (PARALLEL)${NC}"
echo -e "${BLUE}==========================================${NC}"
echo "Problem: $PROBLEM"
echo "Output directory: $OUTPUT_DIR"
echo "Timestamp: $TIMESTAMP"
echo "Max parallel jobs: $MAX_PARALLEL"
echo ""

# Function to wait for a job slot to become available
wait_for_slot() {
    while [ ${#PIDS[@]} -ge $MAX_PARALLEL ]; do
        # Check which jobs are still running
        local new_pids=()
        for pid in "${PIDS[@]}"; do
            if kill -0 $pid 2>/dev/null; then
                # Job still running
                new_pids+=($pid)
            fi
        done
        PIDS=("${new_pids[@]}")

        # If still at capacity, wait a bit
        if [ ${#PIDS[@]} -ge $MAX_PARALLEL ]; then
            sleep 1
        fi
    done
}

# Function to run a single diagnostic test in background
run_test_async() {
    local test_name=$1
    local config=$2
    local run_num=$3
    local desc=$4

    # Wait for a slot if at capacity
    wait_for_slot

    local log_file="$OUTPUT_DIR/${test_name}_run${run_num}_${TIMESTAMP}.log"
    local json_file="$OUTPUT_DIR/${test_name}_run${run_num}_${TIMESTAMP}.json"
    local progress_file="$OUTPUT_DIR/.${test_name}_run${run_num}.progress"

    # Create progress file to track status
    echo "RUNNING" > "$progress_file"

    (
        echo "[$(date +%H:%M:%S)] START: $desc (Run $run_num)" >> "$progress_file"

        # Run the test
        if eval "$config python code/agent_gpt_oss.py $PROBLEM --log $log_file --memory $json_file" 2>&1 | tee -a "$progress_file" > /dev/null; then
            echo "[$(date +%H:%M:%S)] SUCCESS: $desc (Run $run_num)" >> "$progress_file"
            echo "SUCCESS" > "$progress_file"
        else
            echo "[$(date +%H:%M:%S)] FAILED: $desc (Run $run_num)" >> "$progress_file"
            echo "FAILED" > "$progress_file"
        fi
    ) &

    local new_pid=$!
    PIDS+=($new_pid)
    echo -e "${GREEN}[STARTED]${NC} $desc (Run $run_num) - PID: $new_pid - Slot: ${#PIDS[@]}/$MAX_PARALLEL - Log: $log_file"
}

# Function to wait for all jobs and show progress
wait_for_all_jobs() {
    local desc=$1
    echo ""
    echo -e "${YELLOW}Waiting for $desc to complete...${NC}"
    echo "Active jobs: ${#PIDS[@]}"

    # Monitor progress
    while true; do
        sleep 5

        # Clean up completed jobs from PIDS array
        local new_pids=()
        for pid in "${PIDS[@]}"; do
            if kill -0 $pid 2>/dev/null; then
                new_pids+=($pid)
            fi
        done
        PIDS=("${new_pids[@]}")

        # Count job statuses
        local completed=0
        local failed=0
        local running=0

        for progress_file in "$OUTPUT_DIR"/.*.progress; do
            if [ -f "$progress_file" ]; then
                status=$(head -n 1 "$progress_file")
                if [ "$status" = "SUCCESS" ]; then
                    ((completed++))
                elif [ "$status" = "FAILED" ]; then
                    ((failed++))
                elif [ "$status" = "RUNNING" ]; then
                    ((running++))
                fi
            fi
        done

        total=$((completed + failed + running))

        # Print progress
        echo -ne "\r[$(date +%H:%M:%S)] Progress: $completed completed, $running running, $failed failed | Active PIDs: ${#PIDS[@]}"

        # Check if all done
        if [ ${#PIDS[@]} -eq 0 ] && [ $total -gt 0 ]; then
            echo ""
            break
        fi
    done

    echo -e "${GREEN}All jobs completed!${NC}"
    echo ""

    # Show summary
    if [ $failed -gt 0 ]; then
        echo -e "${RED}WARNING: $failed jobs failed${NC}"
        echo "Check individual log files in $OUTPUT_DIR for details"
    fi
}

# Function to check if code variant is ready
check_variant_ready() {
    local variant=$1
    local env_var=$2

    if [ -z "${!env_var}" ]; then
        echo -e "${YELLOW}⚠️  SKIPPED: $variant (Set $env_var=1 to enable)${NC}"
        return 1
    fi
    return 0
}

# =============================================================================
# DIAGNOSTIC TEST 1: Isolate Feedback Content
# =============================================================================

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}TEST 1: Isolate Feedback Content${NC}"
echo -e "${BLUE}==========================================${NC}"
echo "Hypothesis: Detailed prescriptive content causes termination"
echo ""
echo "Control: Normal prescriptive feedback (full templates)"
echo "Treatment: Empty prescriptive feedback (placeholder only)"
echo ""

# Test 1 - Control (always run)
echo -e "${GREEN}Starting Test 1 Control runs (N=2)...${NC}"
run_test_async "test1_control_full_feedback" "" 1 "Test1-Control-Full"
run_test_async "test1_control_full_feedback" "" 2 "Test1-Control-Full"

# Test 1 - Treatment (conditional on code modification)
if check_variant_ready "Test 1 Treatment" "TEST1_TREATMENT_READY"; then
    echo -e "${GREEN}Starting Test 1 Treatment runs (N=2)...${NC}"
    run_test_async "test1_treatment_empty_feedback" "PRESCRIPTIVE_FEEDBACK_MODE=empty" 1 "Test1-Treatment-Empty"
    run_test_async "test1_treatment_empty_feedback" "PRESCRIPTIVE_FEEDBACK_MODE=empty" 2 "Test1-Treatment-Empty"
else
    echo ""
    echo "To enable Test 1 Treatment:"
    echo "1. Modify prescriptive_feedback.py to check PRESCRIPTIVE_FEEDBACK_MODE env var"
    echo "2. If PRESCRIPTIVE_FEEDBACK_MODE=empty, return short placeholder"
    echo "3. Set TEST1_TREATMENT_READY=1 and re-run"
    echo ""
fi

# =============================================================================
# DIAGNOSTIC TEST 2: Isolate Feedback Length
# =============================================================================

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}TEST 2: Isolate Feedback Length${NC}"
echo -e "${BLUE}==========================================${NC}"
echo "Hypothesis: Long feedback overwhelms agent"
echo ""
echo "Control: Uses Test 1 Control results (87-line templates)"
echo "Treatment: Short feedback (10-15 lines)"
echo ""

# Test 2 - Treatment (conditional on code modification)
if check_variant_ready "Test 2 Treatment" "TEST2_TREATMENT_READY"; then
    echo -e "${GREEN}Starting Test 2 Treatment runs (N=2)...${NC}"
    run_test_async "test2_treatment_short_feedback" "PRESCRIPTIVE_FEEDBACK_MODE=short" 1 "Test2-Treatment-Short"
    run_test_async "test2_treatment_short_feedback" "PRESCRIPTIVE_FEEDBACK_MODE=short" 2 "Test2-Treatment-Short"
else
    echo ""
    echo "To enable Test 2 Treatment:"
    echo "1. Modify prescriptive_feedback.py to check PRESCRIPTIVE_FEEDBACK_MODE env var"
    echo "2. If PRESCRIPTIVE_FEEDBACK_MODE=short, return simplified 10-15 line templates"
    echo "3. Set TEST2_TREATMENT_READY=1 and re-run"
    echo ""
fi

# =============================================================================
# DIAGNOSTIC TEST 3: Instrument Feedback Utilization
# =============================================================================

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}TEST 3: Instrument Utilization${NC}"
echo -e "${BLUE}==========================================${NC}"
echo "Hypothesis: Agent doesn't read feedback"
echo ""
echo "Implementation: Add diagnostic logging to track feedback flow"
echo ""

# Test 3 - Instrumented runs (conditional on code modification)
if check_variant_ready "Test 3 Instrumentation" "TEST3_INSTRUMENTED_READY"; then
    echo -e "${GREEN}Starting Test 3 Instrumented runs (N=2)...${NC}"
    run_test_async "test3_instrumented" "DIAGNOSTIC_LOGGING=1" 1 "Test3-Instrumented"
    run_test_async "test3_instrumented" "DIAGNOSTIC_LOGGING=1" 2 "Test3-Instrumented"
else
    echo ""
    echo "To enable Test 3:"
    echo "1. Add diagnostic logging to agent_gpt_oss.py (see code snippet below)"
    echo "2. Set TEST3_INSTRUMENTED_READY=1 and re-run"
    echo ""
    echo "Code to add (around line 1259):"
    echo ""
    cat << 'EOF'
if os.environ.get('DIAGNOSTIC_LOGGING') == '1':
    logger.info(f"[DIAGNOSTIC] Prescriptive feedback received: {len(bug_report)} chars")
    logger.info(f"[DIAGNOSTIC] Feedback preview: {bug_report[:200]}")

    # Later, after creating next iteration prompt:
    feedback_referenced = ("prescriptive" in next_prompt.lower() or
                          "fix" in next_prompt.lower() or
                          "repair" in next_prompt.lower())
    logger.info(f"[DIAGNOSTIC] Feedback referenced in next iteration: {feedback_referenced}")
EOF
    echo ""
fi

# =============================================================================
# Wait for all jobs to complete
# =============================================================================

if [ ${#PIDS[@]} -gt 0 ]; then
    wait_for_all_jobs "all diagnostic tests"

    # Cleanup progress files
    rm -f "$OUTPUT_DIR"/.*.progress

    # Show completion summary
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}DIAGNOSTIC TESTS COMPLETED${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo ""

    # Count completed tests
    control_count=$(ls "$OUTPUT_DIR"/test1_control_*.log 2>/dev/null | wc -l)
    test1_treatment_count=$(ls "$OUTPUT_DIR"/test1_treatment_*.log 2>/dev/null | wc -l)
    test2_treatment_count=$(ls "$OUTPUT_DIR"/test2_treatment_*.log 2>/dev/null | wc -l)
    test3_count=$(ls "$OUTPUT_DIR"/test3_*.log 2>/dev/null | wc -l)

    echo "Test 1 Control: $control_count runs"
    echo "Test 1 Treatment: $test1_treatment_count runs"
    echo "Test 2 Treatment: $test2_treatment_count runs"
    echo "Test 3 Instrumented: $test3_count runs"
    echo ""

    total_runs=$((control_count + test1_treatment_count + test2_treatment_count + test3_count))

    if [ $total_runs -ge 2 ]; then
        echo -e "${GREEN}✓ Enough data collected to run analysis${NC}"
        echo ""
        echo "Next step: Analyze results"
        echo "  python analyze_diagnostic_results.py $OUTPUT_DIR"
        echo ""
    else
        echo -e "${YELLOW}⚠️  Need at least 2 runs to analyze results${NC}"
        echo "  Enable treatment variants and re-run"
    fi
else
    echo -e "${YELLOW}No tests were run. Enable variants by setting environment variables:${NC}"
    echo ""
    echo "  TEST1_TREATMENT_READY=1  # After modifying code for empty feedback"
    echo "  TEST2_TREATMENT_READY=1  # After modifying code for short feedback"
    echo "  TEST3_INSTRUMENTED_READY=1  # After adding diagnostic logging"
    echo ""
    echo "Then re-run: ./run_diagnostic_tests.sh"
    echo ""
fi

# =============================================================================
# QUICK ANALYSIS (if control runs completed)
# =============================================================================

if [ $control_count -ge 2 ]; then
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}QUICK ANALYSIS: Test 1 Control (Current Run)${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo ""
    echo -e "${YELLOW}Note: Only analyzing logs from current timestamp: $TIMESTAMP${NC}"
    echo ""

    # Only analyze logs from current run (matching timestamp)
    for log in "$OUTPUT_DIR"/test1_control_*_${TIMESTAMP}.log; do
        if [ -f "$log" ]; then
            basename=$(basename "$log")
            resume_count=$(grep -c "Resuming from memory" "$log" 2>/dev/null || echo "0")
            # macOS-compatible iteration extraction (no -P flag)
            iterations=$(grep "Iteration [0-9]" "$log" | tail -1 | sed -n 's/.*Iteration \([0-9][0-9]*\).*/\1/p' || echo "0")
            if [ -z "$iterations" ]; then iterations="0"; fi
            lines=$(wc -l < "$log")

            echo "File: $basename"
            echo "  Resume count: $resume_count"
            echo "  Final iteration: $iterations"
            echo "  Log lines: $lines"
            echo ""
        fi
    done

    # Calculate average (only for current timestamp)
    current_logs=$(ls "$OUTPUT_DIR"/test1_control_*_${TIMESTAMP}.log 2>/dev/null)
    if [ -n "$current_logs" ]; then
        total_resumes=$(grep -ch "Resuming from memory" $current_logs 2>/dev/null | awk '{s+=$1} END {print s}')
        current_count=$(echo "$current_logs" | wc -l)
        avg_resumes=$(echo "scale=1; $total_resumes / $current_count" | bc 2>/dev/null || echo "$total_resumes")

        echo -e "${GREEN}Baseline (Control) Average Resume Count: $avg_resumes${NC}"
        echo ""
        echo "Compare treatment variants to this baseline to measure improvement."
    else
        echo -e "${YELLOW}No logs from current run found yet.${NC}"
    fi
    echo ""
fi

# =============================================================================
# USAGE EXAMPLES
# =============================================================================

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}USAGE EXAMPLES${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

echo "Run all tests in parallel (after code modifications):"
echo "  TEST1_TREATMENT_READY=1 TEST2_TREATMENT_READY=1 TEST3_INSTRUMENTED_READY=1 ./run_diagnostic_tests.sh"
echo ""

echo "Run only specific tests:"
echo "  TEST1_TREATMENT_READY=1 ./run_diagnostic_tests.sh  # Only Test 1"
echo "  TEST2_TREATMENT_READY=1 ./run_diagnostic_tests.sh  # Only Test 2"
echo ""

echo "Limit parallel jobs (useful for low-memory systems):"
echo "  MAX_PARALLEL=2 TEST1_TREATMENT_READY=1 ./run_diagnostic_tests.sh"
echo ""

echo "Example with 1 job at a time (sequential):"
echo "  MAX_PARALLEL=1 ./run_diagnostic_tests.sh"
echo ""

echo "Monitor progress in real-time:"
echo "  watch -n 5 'ls -lh $OUTPUT_DIR/*.log | tail -10'"
echo ""

echo -e "${BLUE}==========================================${NC}"
echo ""
