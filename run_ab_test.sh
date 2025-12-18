#!/bin/bash
#
# A/B Testing Script for Prescriptive Feedback (with Parallel Execution)
#
# Usage:
#   ./run_ab_test.sh problems/imo01.txt [output_dir] [runs_per_group] [parallel_jobs]
#
# Example:
#   ./run_ab_test.sh problems/imo01.txt ab_test_p1 10 5
#   (Runs 10 control + 10 treatment with 5 concurrent jobs)
#

set -e  # Exit on error

PROBLEM=$1
OUTPUT_DIR=${2:-"ab_test_results"}
RUNS_PER_GROUP=${3:-5}
PARALLEL_JOBS=${4:-3}

if [ -z "$PROBLEM" ]; then
    echo "Usage: $0 <problem_file> [output_dir] [runs_per_group] [parallel_jobs]"
    echo ""
    echo "Arguments:"
    echo "  problem_file    - Problem file to test (required)"
    echo "  output_dir      - Output directory (default: ab_test_results)"
    echo "  runs_per_group  - Number of runs per group (default: 5)"
    echo "  parallel_jobs   - Concurrent jobs (default: 3)"
    echo ""
    echo "Example:"
    echo "  $0 problems/imo01.txt ab_test_p1 10 5"
    echo "  (Runs 10 control + 10 treatment with 5 concurrent jobs)"
    exit 1
fi

if [ ! -f "$PROBLEM" ]; then
    echo "Error: Problem file not found: $PROBLEM"
    exit 1
fi

mkdir -p "$OUTPUT_DIR/control" "$OUTPUT_DIR/treatment"

echo "========================================================================"
echo "A/B TEST: Prescriptive Feedback Impact (Parallel Execution)"
echo "========================================================================"
echo "Problem:          $PROBLEM"
echo "Output Directory: $OUTPUT_DIR"
echo "Runs per Group:   $RUNS_PER_GROUP"
echo "Parallel Jobs:    $PARALLEL_JOBS"
echo "Total Runs:       $((RUNS_PER_GROUP * 2))"
echo ""

# Function to run a single test
run_test() {
    local group=$1
    local run_num=$2
    local output_dir=$3
    local problem=$4

    if [ "$group" = "control" ]; then
        DISABLE_PRESCRIPTIVE_FEEDBACK=1 \
        python code/agent_gpt_oss.py "$problem" \
            --num-initial-attempts 3 \
            --solution-reasoning low \
            --verification-reasoning medium \
            --log "$output_dir/run_${run_num}.log" \
            --memory "$output_dir/run_${run_num}.json" \
            > "$output_dir/run_${run_num}_stdout.txt" 2>&1
    else
        python code/agent_gpt_oss.py "$problem" \
            --num-initial-attempts 3 \
            --solution-reasoning low \
            --verification-reasoning medium \
            --log "$output_dir/run_${run_num}.log" \
            --memory "$output_dir/run_${run_num}.json" \
            > "$output_dir/run_${run_num}_stdout.txt" 2>&1
    fi

    # Check success/failure
    local status="❌ FAILED"
    if grep -q "Found a correct solution" "$output_dir/run_${run_num}.log" 2>/dev/null; then
        status="✅ SUCCESS"
    fi

    echo "  [$group] Run $run_num: $status"
}

export -f run_test

# Function to run group with parallel execution
run_group_parallel() {
    local group_name=$1
    local group_dir=$2
    local runs=$3
    local max_parallel=$4

    echo "=== $group_name ==="
    echo ""

    local running_jobs=0
    local pids=()

    for i in $(seq 1 $runs); do
        # Wait if we've hit the parallel limit
        while [ $running_jobs -ge $max_parallel ]; do
            # Check if any background job has finished
            for pid in "${pids[@]}"; do
                if ! kill -0 $pid 2>/dev/null; then
                    # Job finished, decrement counter
                    running_jobs=$((running_jobs - 1))
                    # Remove from pids array
                    pids=("${pids[@]/$pid}")
                fi
            done
            sleep 1
        done

        # Start new job in background
        (run_test "$group_name" "$i" "$group_dir" "$PROBLEM") &
        local new_pid=$!
        pids+=($new_pid)
        running_jobs=$((running_jobs + 1))

        # Small delay to avoid overwhelming the system
        sleep 0.5
    done

    # Wait for all remaining jobs to complete
    echo ""
    echo "  Waiting for remaining jobs to complete..."
    wait
    echo ""
}

# Get start time
START_TIME=$(date +%s)

# Control group (no prescriptive feedback)
run_group_parallel "CONTROL GROUP (No Prescriptive Feedback)" \
    "$OUTPUT_DIR/control" \
    "$RUNS_PER_GROUP" \
    "$PARALLEL_JOBS"

echo ""

# Treatment group (with prescriptive feedback)
run_group_parallel "TREATMENT GROUP (With Prescriptive Feedback)" \
    "$OUTPUT_DIR/treatment" \
    "$RUNS_PER_GROUP" \
    "$PARALLEL_JOBS"

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))

echo "========================================================================"
echo "A/B TEST COMPLETE"
echo "========================================================================"
echo "Results saved to: $OUTPUT_DIR/"
echo "Total runtime:    ${ELAPSED_MIN}m ${ELAPSED_SEC}s"
echo ""
echo "Run analysis:"
echo "  python analyze_ab_test.py $OUTPUT_DIR"
echo ""
