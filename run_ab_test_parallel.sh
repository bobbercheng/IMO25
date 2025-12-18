#!/bin/bash
#
# Advanced A/B Testing Script with GNU Parallel Support (Fastest)
#
# This version uses GNU parallel for optimal performance.
# If gnu parallel is not installed, it falls back to the bash-based parallel implementation.
#
# Usage:
#   ./run_ab_test_parallel.sh problems/imo01.txt [output_dir] [runs_per_group] [parallel_jobs]
#
# Example:
#   ./run_ab_test_parallel.sh problems/imo01.txt ab_test_p1 20 5
#

set -e

PROBLEM=$1
OUTPUT_DIR=${2:-"ab_test_results"}
RUNS_PER_GROUP=${3:-5}
PARALLEL_JOBS=${4:-3}

if [ -z "$PROBLEM" ]; then
    echo "Usage: $0 <problem_file> [output_dir] [runs_per_group] [parallel_jobs]"
    echo ""
    echo "Example:"
    echo "  $0 problems/imo01.txt ab_test_p1 20 5"
    exit 1
fi

if [ ! -f "$PROBLEM" ]; then
    echo "Error: Problem file not found: $PROBLEM"
    exit 1
fi

mkdir -p "$OUTPUT_DIR/control" "$OUTPUT_DIR/treatment"

echo "========================================================================"
echo "A/B TEST: Prescriptive Feedback (GNU Parallel)"
echo "========================================================================"
echo "Problem:          $PROBLEM"
echo "Output Directory: $OUTPUT_DIR"
echo "Runs per Group:   $RUNS_PER_GROUP"
echo "Parallel Jobs:    $PARALLEL_JOBS"
echo "Total Runs:       $((RUNS_PER_GROUP * 2))"
echo ""

# Check if GNU parallel is available
if command -v parallel &> /dev/null; then
    echo "Using GNU parallel for optimal performance"
    echo ""

    START_TIME=$(date +%s)

    # Control group
    echo "=== CONTROL GROUP ==="
    seq 1 $RUNS_PER_GROUP | parallel -j $PARALLEL_JOBS "
        DISABLE_PRESCRIPTIVE_FEEDBACK=1 \
        python code/agent_gpt_oss.py '$PROBLEM' \
            --num-initial-attempts 3 \
            --solution-reasoning low \
            --verification-reasoning medium \
            --log '$OUTPUT_DIR/control/run_{}.log' \
            --memory '$OUTPUT_DIR/control/run_{}.json' \
            > '$OUTPUT_DIR/control/run_{}_stdout.txt' 2>&1

        if grep -q 'Found a correct solution' '$OUTPUT_DIR/control/run_{}.log' 2>/dev/null; then
            echo '  [control] Run {}: ✅ SUCCESS'
        else
            echo '  [control] Run {}: ❌ FAILED'
        fi
    "

    echo ""

    # Treatment group
    echo "=== TREATMENT GROUP ==="
    seq 1 $RUNS_PER_GROUP | parallel -j $PARALLEL_JOBS "
        python code/agent_gpt_oss.py '$PROBLEM' \
            --num-initial-attempts 3 \
            --solution-reasoning low \
            --verification-reasoning medium \
            --log '$OUTPUT_DIR/treatment/run_{}.log' \
            --memory '$OUTPUT_DIR/treatment/run_{}.json' \
            > '$OUTPUT_DIR/treatment/run_{}_stdout.txt' 2>&1

        if grep -q 'Found a correct solution' '$OUTPUT_DIR/treatment/run_{}.log' 2>/dev/null; then
            echo '  [treatment] Run {}: ✅ SUCCESS'
        else
            echo '  [treatment] Run {}: ❌ FAILED'
        fi
    "

    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    ELAPSED_MIN=$((ELAPSED / 60))
    ELAPSED_SEC=$((ELAPSED % 60))

    echo ""
    echo "========================================================================"
    echo "A/B TEST COMPLETE"
    echo "========================================================================"
    echo "Results saved to: $OUTPUT_DIR/"
    echo "Total runtime:    ${ELAPSED_MIN}m ${ELAPSED_SEC}s"
    echo ""
    echo "Run analysis:"
    echo "  python analyze_ab_test.py $OUTPUT_DIR"
    echo ""

else
    echo "GNU parallel not found. Install with:"
    echo "  brew install parallel        # macOS"
    echo "  apt-get install parallel     # Ubuntu/Debian"
    echo "  yum install parallel         # RedHat/CentOS"
    echo ""
    echo "Falling back to bash-based parallel execution..."
    echo ""

    # Fall back to the bash version
    exec ./run_ab_test.sh "$PROBLEM" "$OUTPUT_DIR" "$RUNS_PER_GROUP" "$PARALLEL_JOBS"
fi
