#!/bin/bash
#
# BFS Baseline Test Script (N=12)
# Purpose: Establish BFS baseline for IMO Problem 1 with answer validation
# Expected: 8-12/12 success rate, 15-20 min per run, $2-3 per run
#
# Historical BFS performance:
#   - N=1 run: 15 min, $2, SUCCESS (found k ∈ {0,...,⌊n/2⌋})
#   - Expected for N=12: ~3 hours total, ~$24-36 total
#

set -euo pipefail

# Configuration
PROBLEM="${1:-problems/imo01.txt}"
OUTPUT_DIR="${2:-bfs_baseline_results}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAX_PARALLEL=${MAX_PARALLEL:-6}  # Run 6 in parallel for faster completion
N_RUNS=12

# BFS configuration (from historical success)
SOLUTION_REASONING="low"         # BFS uses low reasoning (fast exploration)
VERIFICATION_REASONING="medium"   # Medium for balance (not high like diagnostic)
SELF_IMPROVEMENT_REASONING="low"  # BFS doesn't need heavy self-improvement
NUM_INITIAL_ATTEMPTS=3           # Generate 3 initial solution attempts (BFS exploration)

# Agent configuration
MAX_RUNS=30  # BFS typically finds answer in 10-15 iterations

PIDS=()  # Array to track background job PIDs

# Create output directory
mkdir -p "$OUTPUT_DIR"

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}BFS Baseline Test (N=12)${NC}"
echo -e "${BLUE}==========================================${NC}"
echo "Problem: $PROBLEM"
echo "Output directory: $OUTPUT_DIR"
echo "Timestamp: $TIMESTAMP"
echo "Max parallel jobs: $MAX_PARALLEL"
echo ""
echo "BFS Configuration:"
echo "  Solution reasoning: $SOLUTION_REASONING"
echo "  Verification reasoning: $VERIFICATION_REASONING"
echo "  Self-improvement reasoning: $SELF_IMPROVEMENT_REASONING"
echo "  Initial attempts: $NUM_INITIAL_ATTEMPTS"
echo "  Max iterations: $MAX_RUNS"
echo ""
echo "Expected performance:"
echo "  Duration: 15-20 min per run"
echo "  Cost: \$2-3 per run"
echo "  Success rate: 67-100% (8-12/12)"
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

# Function to run a single BFS test in background
run_bfs_async() {
    local run_num=$1

    # Wait for a slot if at capacity
    wait_for_slot

    local log_file="$OUTPUT_DIR/bfs_run${run_num}_${TIMESTAMP}.log"
    local json_file="$OUTPUT_DIR/bfs_run${run_num}_${TIMESTAMP}.json"
    local progress_file="$OUTPUT_DIR/.bfs_run${run_num}.progress"

    # Create progress file to track status
    echo "RUNNING" > "$progress_file"

    (
        echo "[$(date +%H:%M:%S)] START: BFS Run $run_num" >> "$progress_file"

        # Run BFS agent
        if python code/agent_gpt_oss.py "$PROBLEM" \
            --log "$log_file" \
            --memory "$json_file" \
            --num-initial-attempts $NUM_INITIAL_ATTEMPTS \
            --max_runs $MAX_RUNS \
            --solution-reasoning "$SOLUTION_REASONING" \
            --verification-reasoning "$VERIFICATION_REASONING" \
            --self-improvement-reasoning "$SELF_IMPROVEMENT_REASONING" \
            2>&1 | tee -a "$progress_file" > /dev/null; then
            echo "[$(date +%H:%M:%S)] SUCCESS: BFS Run $run_num" >> "$progress_file"
            echo "SUCCESS" > "$progress_file"
        else
            echo "[$(date +%H:%M:%S)] FAILED: BFS Run $run_num" >> "$progress_file"
            echo "FAILED" > "$progress_file"
        fi
    ) &

    local new_pid=$!
    PIDS+=($new_pid)
    echo -e "${GREEN}[STARTED]${NC} BFS Run $run_num - PID: $new_pid - Slot: ${#PIDS[@]}/$MAX_PARALLEL - Log: $log_file"
}

# Function to wait for all jobs and show progress
wait_for_all_jobs() {
    echo ""
    echo -e "${YELLOW}Waiting for all BFS tests to complete...${NC}"
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

        for progress_file in "$OUTPUT_DIR"/.bfs_run*.progress; do
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

        # Print progress
        echo -ne "\r[$(date +%H:%M:%S)] Progress: $completed completed, $running running, $failed failed | Active PIDs: ${#PIDS[@]}"

        # Check if all done
        if [ ${#PIDS[@]} -eq 0 ] && [ $((completed + failed)) -ge $N_RUNS ]; then
            echo ""
            break
        fi
    done

    echo -e "${GREEN}All BFS tests completed!${NC}"
    echo ""

    # Show summary
    if [ $failed -gt 0 ]; then
        echo -e "${RED}WARNING: $failed tests failed${NC}"
        echo "Check individual log files in $OUTPUT_DIR for details"
    fi
}

# =============================================================================
# MAIN: Run N=12 BFS Baseline Tests
# =============================================================================

echo -e "${GREEN}Starting N=$N_RUNS BFS baseline runs...${NC}"
echo ""

for run_num in $(seq 1 $N_RUNS); do
    run_bfs_async $run_num
    sleep 0.5  # Small delay to avoid API rate limits
done

# Wait for all tests to complete
if [ ${#PIDS[@]} -gt 0 ]; then
    wait_for_all_jobs

    # Cleanup progress files
    rm -f "$OUTPUT_DIR"/.bfs_run*.progress

    # Show completion summary
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}BFS BASELINE TESTS COMPLETED${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo ""

    # Count completed tests
    run_count=$(ls "$OUTPUT_DIR"/bfs_run*_${TIMESTAMP}.log 2>/dev/null | wc -l)

    echo "Total runs: $run_count"
    echo ""

    if [ $run_count -ge 12 ]; then
        echo -e "${GREEN}✓ All 12 baseline runs completed${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Analyze results: python analyze_bfs_baseline.py $OUTPUT_DIR"
        echo "  2. Check success rate: grep -l 'verification good' $OUTPUT_DIR/*.log | wc -l"
        echo "  3. Compare to RLAC baseline (diagnostic_results/)"
        echo ""
    else
        echo -e "${YELLOW}⚠️  Only $run_count runs completed (expected 12)${NC}"
        echo "  Check for errors in log files"
    fi
else
    echo -e "${YELLOW}No tests were run.${NC}"
fi

# =============================================================================
# QUICK ANALYSIS: Extract key metrics from current run
# =============================================================================

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}QUICK ANALYSIS: BFS Baseline${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Only analyze logs from current timestamp
current_logs=$(ls "$OUTPUT_DIR"/bfs_run*_${TIMESTAMP}.log 2>/dev/null | head -12)

if [ -n "$current_logs" ]; then
    success_count=0
    total_duration=0
    total_iterations=0
    run_count=0

    for log in $current_logs; do
        basename=$(basename "$log")

        # Check for success
        if grep -q "verification good" "$log" 2>/dev/null; then
            ((success_count++))
        fi

        # Extract duration (from timestamps)
        start_time=$(grep -m1 "^\[" "$log" | sed -n 's/^\[\([0-9:-]*\)\].*/\1/p' || echo "")
        end_time=$(grep "^\[" "$log" | tail -1 | sed -n 's/^\[\([0-9:-]*\)\].*/\1/p' || echo "")

        # Extract iteration count (macOS-compatible)
        iterations=$(grep "Iteration [0-9]" "$log" | tail -1 | sed -n 's/.*Iteration \([0-9][0-9]*\).*/\1/p' || echo "0")
        if [ -z "$iterations" ]; then iterations="0"; fi

        lines=$(wc -l < "$log")

        echo "File: $basename"
        echo "  Iterations: $iterations"
        echo "  Log lines: $lines"

        if grep -q "verification good" "$log" 2>/dev/null; then
            echo "  Status: ✅ SUCCESS"
        else
            echo "  Status: ❌ FAILED"
        fi
        echo ""

        ((run_count++))
        total_iterations=$((total_iterations + iterations))
    done

    # Calculate averages
    if [ $run_count -gt 0 ]; then
        avg_iterations=$((total_iterations / run_count))
        success_rate=$((success_count * 100 / run_count))

        echo -e "${GREEN}=== SUMMARY ===${NC}"
        echo "Runs completed: $run_count/12"
        echo "Success rate: $success_count/$run_count ($success_rate%)"
        echo "Average iterations: $avg_iterations"
        echo ""

        # Compare to historical baseline
        echo -e "${BLUE}=== COMPARISON TO HISTORICAL DATA ===${NC}"
        echo "Historical BFS LOW (N=1): 100% success, 15 min, $2"
        echo "Current BFS (N=$run_count): $success_rate% success, $avg_iterations iterations"
        echo ""

        if [ $success_rate -ge 67 ]; then
            echo -e "${GREEN}✅ SUCCESS RATE MEETS EXPECTATIONS (≥67%)${NC}"
        elif [ $success_rate -ge 50 ]; then
            echo -e "${YELLOW}⚠️  SUCCESS RATE ACCEPTABLE (≥50%) but below target${NC}"
        else
            echo -e "${RED}❌ SUCCESS RATE BELOW EXPECTATIONS (<50%)${NC}"
        fi
        echo ""
    fi
else
    echo -e "${YELLOW}No logs from current run found yet.${NC}"
fi

# =============================================================================
# USAGE EXAMPLES
# =============================================================================

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}USAGE EXAMPLES${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

echo "Run with custom parallel limit:"
echo "  MAX_PARALLEL=4 ./run_bfs_baseline.sh"
echo ""

echo "Run for different problem:"
echo "  ./run_bfs_baseline.sh problems/imo02.txt bfs_p2_results"
echo ""

echo "Monitor progress in real-time:"
echo "  watch -n 5 'ls -lh $OUTPUT_DIR/*.log | tail -12'"
echo ""

echo "Check success rate:"
echo "  grep -l 'verification good' $OUTPUT_DIR/bfs_run*_${TIMESTAMP}.log | wc -l"
echo ""

echo "Analyze results:"
echo "  python analyze_bfs_baseline.py $OUTPUT_DIR"
echo ""

echo -e "${BLUE}==========================================${NC}"
echo ""
