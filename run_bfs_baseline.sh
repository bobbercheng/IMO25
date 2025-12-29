#!/bin/bash
#
# BFS Baseline Test Script (N=12) - UPDATED CONFIGURATION
# Purpose: Test BFS with MEDIUM reasoning after expert panel analysis
# Configuration: MEDIUM reasoning, temperature 0.1, MAX_RUNS=15
#
# CRITICAL FIX (2025-12-23):
#   - Removed answer validation from feedback loop (was leaking ground truth)
#   - Success criterion: "Correct solution found (first success)" (agent's judgment)
#   - Post-hoc validation: Use validate_runs_offline.py for ground truth comparison
#
# Expert Panel Findings (RUN3_EXPERT_PANEL_SYNTHESIS.md):
#   - Previous config (LOW reasoning): 0/12 success, only found k=0
#   - Root cause: LOW reasoning insufficient for mixed constructions (k=1,3)
#   - Recommendation: MEDIUM reasoning + temperature 0.35
#
# Expected Performance (MEDIUM reasoning):
#   - Success rate: 30-50% (4-6/12 runs) per expert estimates
#   - Duration: 20-30 min per run (vs 15 min with LOW, vs 730 min with LOW failed)
#   - Cost: $5-7 per run (3.5× higher than LOW, but ENABLES success)
#   - Iterations: 5-15 if successful (vs 29.6 avg with LOW failing)
#   - Total cost: ~$60-84 for N=12 (vs previous INFINITE cost for 0% success)
#

set -euo pipefail

# Configuration
PROBLEM="${1:-problems/imo01.txt}"
OUTPUT_DIR="${2:-bfs_baseline_results}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAX_PARALLEL=${MAX_PARALLEL:-6}  # Run 6 in parallel for faster completion
N_RUNS=${N_RUNS:-12} # Active jobs number, default 12

# BFS configuration (UPDATED per expert panel recommendations)
# Expert panel analysis (RUN3_EXPERT_PANEL_SYNTHESIS.md):
#   - LOW reasoning insufficient for mixed constructions (k=1,3)
#   - Need MEDIUM reasoning to execute algebraic verification
#   - Expected: 30-50% success rate, 5-15 iterations if successful
SOLUTION_REASONING="medium"        # ↑ from "low" - enables mixed constructions
VERIFICATION_REASONING="high"      # ↑ from "medium" - catch semantic errors (Runs 1-6 review)
SELF_IMPROVEMENT_REASONING="medium"  # ↑ from "low" - enables rigorous exploration
NUM_INITIAL_ATTEMPTS=3            # Generate 3 initial solution attempts (BFS exploration)

# Agent configuration
# REDUCED from 30 to 15: MEDIUM reasoning should find answer within 15 iterations
# Historical BFS: 10-15 iterations at 100% success
# If failing at iteration 15, unlikely to succeed at 30
MAX_RUNS=15

PIDS=()  # Array to track background job PIDs
JOB_NUMS=()  # Parallel array: JOB_NUMS[i] corresponds to PIDS[i]

# Helper function to get job number for a PID (bash 3.x compatible)
get_job_num_for_pid() {
    local target_pid=$1
    local i
    for i in "${!PIDS[@]}"; do
        if [ "${PIDS[$i]}" = "$target_pid" ]; then
            echo "${JOB_NUMS[$i]}"
            return 0
        fi
    done
    echo "unknown"
}

# Helper function to remove PID from tracking arrays
remove_pid_from_tracking() {
    local target_pid=$1
    local new_pids=()
    local new_job_nums=()
    local i
    for i in "${!PIDS[@]}"; do
        if [ "${PIDS[$i]}" != "$target_pid" ]; then
            new_pids+=("${PIDS[$i]}")
            new_job_nums+=("${JOB_NUMS[$i]}")
        fi
    done
    # Use ${arr[@]+"${arr[@]}"} to handle empty arrays with set -u
    PIDS=(${new_pids[@]+"${new_pids[@]}"})
    JOB_NUMS=(${new_job_nums[@]+"${new_job_nums[@]}"})
}

# Create output directory
mkdir -p "$OUTPUT_DIR"

# FIX (2025-12-23): Validate sufficient disk space before starting N=100 test
# Estimated space needed: ~71MB for logs + ~20MB temp files = ~100MB total
available_space=$(df -k "$OUTPUT_DIR" | tail -1 | awk '{print $4}')
required_space=102400  # 100MB in KB
if [ "$available_space" -lt "$required_space" ]; then
    echo -e "${RED}ERROR: Insufficient disk space${NC}"
    echo "  Available: $(($available_space / 1024))MB"
    echo "  Required:  $(($required_space / 1024))MB"
    echo "  Please free up space before running the test"
    exit 1
fi
echo "Disk space check: $(($available_space / 1024))MB available (OK)"
echo ""

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
echo "Expected performance (MEDIUM reasoning):"
echo "  Duration: 20-30 min per run (vs 15 min with LOW)"
echo "  Cost: \$5-7 per run (vs \$2 with LOW, 3.5× higher)"
echo "  Success rate: 30-50% (4-6/12) per expert panel estimates"
echo "  Note: Temperature hardcoded to 0.1 (expert recommends 0.35 for better exploration)"
echo ""

# Function to report job completion
report_job_completion() {
    local pid=$1
    local job_num=$(get_job_num_for_pid $pid)
    local progress_file="$OUTPUT_DIR/.bfs_run${job_num}.progress"

    if [ -f "$progress_file" ]; then
        local status=$(head -n 1 "$progress_file")
        if [ "$status" = "SUCCESS" ]; then
            echo -e "${GREEN}[COMPLETED]${NC} Job $job_num (PID $pid) - SUCCESS"
        elif [ "$status" = "FAILED" ]; then
            echo -e "${RED}[COMPLETED]${NC} Job $job_num (PID $pid) - FAILED"
        else
            echo -e "${YELLOW}[COMPLETED]${NC} Job $job_num (PID $pid) - Unknown status"
        fi
    else
        echo -e "${YELLOW}[COMPLETED]${NC} Job $job_num (PID $pid) - No progress file"
    fi

    # Clean up the mapping
    remove_pid_from_tracking $pid
}

# Function to wait for a job slot to become available
wait_for_slot() {
    while [ ${#PIDS[@]} -ge $MAX_PARALLEL ]; do
        # Check which jobs are still running
        local new_pids=()
        for pid in "${PIDS[@]}"; do
            if kill -0 $pid 2>/dev/null; then
                # Job still running
                new_pids+=($pid)
            else
                # Job completed - report it
                report_job_completion $pid
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
        # FIX (2025-12-23): Removed "> /dev/null" which was discarding all output
        # All output now goes to both progress_file (via tee) and log_file (via --log)
        if python code/agent_gpt_oss.py "$PROBLEM" \
            --log "$log_file" \
            --memory "$json_file" \
            --num-initial-attempts $NUM_INITIAL_ATTEMPTS \
            --max_runs $MAX_RUNS \
            --solution-reasoning "$SOLUTION_REASONING" \
            --verification-reasoning "$VERIFICATION_REASONING" \
            --self-improvement-reasoning "$SELF_IMPROVEMENT_REASONING" \
            2>&1 | tee -a "$progress_file"; then
            echo "[$(date +%H:%M:%S)] SUCCESS: BFS Run $run_num" >> "$progress_file"
            echo "SUCCESS" > "$progress_file"
        else
            echo "[$(date +%H:%M:%S)] FAILED: BFS Run $run_num" >> "$progress_file"
            echo "FAILED" > "$progress_file"
        fi
    ) &

    local new_pid=$!
    PIDS+=($new_pid)
    JOB_NUMS+=($run_num)  # Map PID to job number for completion reporting (parallel array)
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

        # Clean up completed jobs from PIDS array and report completions
        local new_pids=()
        for pid in "${PIDS[@]}"; do
            if kill -0 $pid 2>/dev/null; then
                new_pids+=($pid)
            else
                # Job completed - report it
                report_job_completion $pid
            fi
        done
        # Handle empty array with set -u (unbound variable error)
        PIDS=("${new_pids[@]+"${new_pids[@]}"}")

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
if [ "${#PIDS[@]}" -gt 0 ] 2>/dev/null || [ $N_RUNS -gt 0 ]; then
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
        echo "  2. Check success rate: grep -l '\"verdict\": *\"PASS\"' $OUTPUT_DIR/*.log | wc -l"
        echo "  3. Offline validation: python validate_runs_offline.py $OUTPUT_DIR"
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

        # Check for success (agent's own judgment via verification verdict)
        # FIXED (2025-12-28): Check for actual success indicators in GPT-OSS agent logs
        # Primary criterion: Final verification verdict = PASS
        # Secondary criterion: Correct answer {0,1,3} (exact match, not superset)
        # Note: We rely on verification PASS as the primary success indicator since
        # the agent's verification system should validate the correctness
        if tail -1000 "$log" 2>/dev/null | grep -q '"verdict": *"PASS"'; then
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

        # FIXED (2025-12-28): Check for actual success indicators
        # Check last 1000 lines for final verification verdict
        if tail -1000 "$log" 2>/dev/null | grep -q '"verdict": *"PASS"'; then
            echo "  Status: ✅ SUCCESS (verification PASS)"
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

        # Compare to baselines
        echo -e "${BLUE}=== COMPARISON TO BASELINES ===${NC}"
        echo "Historical BFS LOW (N=1): 100% success, 15 min, \$2/run"
        echo "Previous BFS LOW (N=12): 0% success, 730 min/run, \$20-30/run"
        echo "Current BFS MEDIUM (N=$run_count): $success_rate% success, $avg_iterations avg iterations"
        echo ""

        # Updated success criteria based on expert panel estimates
        if [ $success_rate -ge 30 ]; then
            echo -e "${GREEN}✅ SUCCESS RATE MEETS EXPECTATIONS (≥30%)${NC}"
            echo "Expert panel predicted 30-50% with MEDIUM reasoning - CONFIRMED"
        elif [ $success_rate -ge 10 ]; then
            echo -e "${YELLOW}⚠️  SOME SUCCESS (≥10%) but below expert predictions${NC}"
            echo "Consider: Add explicit k=1,3 prompts, increase temperature to 0.35"
        else
            echo -e "${RED}❌ SUCCESS RATE BELOW EXPECTATIONS (<10%)${NC}"
            echo "MEDIUM reasoning may still be insufficient. Consider HIGH reasoning or prompt engineering."
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

echo "Check success rate (agent's judgment):"
echo "  grep -l '\"verdict\": *\"PASS\"' $OUTPUT_DIR/bfs_run*_${TIMESTAMP}.log | wc -l"
echo ""

echo "Offline validation (ground truth comparison):"
echo "  python validate_runs_offline.py $OUTPUT_DIR"
echo ""

echo "Analyze results:"
echo "  python analyze_bfs_baseline.py $OUTPUT_DIR"
echo ""

echo -e "${BLUE}==========================================${NC}"
echo ""
