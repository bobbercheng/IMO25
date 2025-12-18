#!/bin/bash
#
# A/B Testing Script for Prescriptive Feedback
#
# Usage:
#   ./run_ab_test.sh problems/imo01.txt [output_dir] [runs_per_group]
#
# Example:
#   ./run_ab_test.sh problems/imo01.txt ab_test_p1 5
#

set -e  # Exit on error

PROBLEM=$1
OUTPUT_DIR=${2:-"ab_test_results"}
RUNS_PER_GROUP=${3:-5}

if [ -z "$PROBLEM" ]; then
    echo "Usage: $0 <problem_file> [output_dir] [runs_per_group]"
    echo ""
    echo "Example:"
    echo "  $0 problems/imo01.txt ab_test_p1 5"
    exit 1
fi

if [ ! -f "$PROBLEM" ]; then
    echo "Error: Problem file not found: $PROBLEM"
    exit 1
fi

mkdir -p "$OUTPUT_DIR/control" "$OUTPUT_DIR/treatment"

echo "========================================================================"
echo "A/B TEST: Prescriptive Feedback Impact"
echo "========================================================================"
echo "Problem:          $PROBLEM"
echo "Output Directory: $OUTPUT_DIR"
echo "Runs per Group:   $RUNS_PER_GROUP"
echo "Total Runs:       $((RUNS_PER_GROUP * 2))"
echo ""

# Control group (no prescriptive feedback)
echo "=== CONTROL GROUP (No Prescriptive Feedback) ==="
echo ""

for i in $(seq 1 $RUNS_PER_GROUP); do
    echo "Run $i/$RUNS_PER_GROUP..."

    DISABLE_PRESCRIPTIVE_FEEDBACK=1 \
    python code/agent_gpt_oss.py "$PROBLEM" \
        --num-initial-attempts 3 \
        --solution-reasoning low \
        --verification-reasoning medium \
        --log "$OUTPUT_DIR/control/run_${i}.log" \
        --memory "$OUTPUT_DIR/control/run_${i}.json" \
        > "$OUTPUT_DIR/control/run_${i}_stdout.txt" 2>&1

    # Extract success/failure
    if grep -q "Found a correct solution" "$OUTPUT_DIR/control/run_${i}.log" 2>/dev/null; then
        echo "  ✅ SUCCESS"
    else
        echo "  ❌ FAILED"
    fi
    echo ""
done

# Treatment group (with prescriptive feedback)
echo ""
echo "=== TREATMENT GROUP (With Prescriptive Feedback) ==="
echo ""

for i in $(seq 1 $RUNS_PER_GROUP); do
    echo "Run $i/$RUNS_PER_GROUP..."

    python code/agent_gpt_oss.py "$PROBLEM" \
        --num-initial-attempts 3 \
        --solution-reasoning low \
        --verification-reasoning medium \
        --log "$OUTPUT_DIR/treatment/run_${i}.log" \
        --memory "$OUTPUT_DIR/treatment/run_${i}.json" \
        > "$OUTPUT_DIR/treatment/run_${i}_stdout.txt" 2>&1

    if grep -q "Found a correct solution" "$OUTPUT_DIR/treatment/run_${i}.log" 2>/dev/null; then
        echo "  ✅ SUCCESS"
    else
        echo "  ❌ FAILED"
    fi
    echo ""
done

echo "========================================================================"
echo "A/B TEST COMPLETE"
echo "========================================================================"
echo "Results saved to: $OUTPUT_DIR/"
echo ""
echo "Run analysis:"
echo "  python analyze_ab_test.py $OUTPUT_DIR"
echo ""
