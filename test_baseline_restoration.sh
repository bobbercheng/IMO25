#!/bin/bash

# Test script to verify baseline restoration after Priority 1 & 2 fixes
# Expected: 31-minute success (restore Test 3 baseline performance)

echo "========================================================================"
echo "Baseline Restoration Test"
echo "========================================================================"
echo ""
echo "Configuration:"
echo "  - MCTS: 5 simulations (baseline)"
echo "  - Exploration: 1.414 (sqrt(2), baseline)"
echo "  - Max depth: 2 (baseline)"
echo "  - Reasoning: Low/Low/Low (proven config)"
echo "  - Verification safeguards: ENABLED (10 min timeout, 3 max attempts)"
echo ""
echo "Expected results:"
echo "  - Duration: ~31 minutes (baseline performance)"
echo "  - Success: Find correct solution k ∈ {0,1} or k ∈ {0,1,...,n}"
echo "  - No hangs: Safeguards prevent verification deadlocks"
echo ""

PROBLEM_FILE="problems/imo01.txt"
LOG_DIR="test_baseline_logs"
LOG_FILE="$LOG_DIR/baseline_restoration.log"
MEMORY_FILE="$LOG_DIR/baseline_memory.json"

# Create log directory
mkdir -p "$LOG_DIR"

echo "Starting baseline test at $(date)"
echo "Log: $LOG_FILE"
echo ""

# Test baseline with Low/Low/Low reasoning (proven configuration)
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
    --use-mcts \
    --mcts-simulations 5 \
    --mcts-exploration 1.414 \
    --solution-reasoning low \
    --self-improvement-reasoning low \
    --verification-reasoning low \
    --verification-timeout 600 \
    --verification-max-attempts 3 \
    --log "$LOG_FILE" \
    --memory "$MEMORY_FILE"

EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "Test Complete at $(date)"
echo "========================================================================"
echo ""
echo "Exit code: $EXIT_CODE"
echo "Log file: $LOG_FILE"
echo "Memory file: $MEMORY_FILE"
echo "MCTS tree: $LOG_DIR/baseline_memory_mcts_tree.json"
echo ""

# Check for success
if grep -q "Found a correct solution" "$LOG_FILE"; then
    echo "✓ SUCCESS: Correct solution found!"
    echo ""
    echo "Extracting duration..."
    START_TIME=$(grep -m1 "Starting fresh" "$LOG_FILE" | grep -oP '\[\K[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}')
    END_TIME=$(grep "Found a correct solution" "$LOG_FILE" | grep -oP '\[\K[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}' | tail -1)

    if [ -n "$START_TIME" ] && [ -n "$END_TIME" ]; then
        echo "Start: $START_TIME"
        echo "End:   $END_TIME"

        # Calculate duration
        START_SEC=$(date -d "$START_TIME" +%s 2>/dev/null)
        END_SEC=$(date -d "$END_TIME" +%s 2>/dev/null)

        if [ -n "$START_SEC" ] && [ -n "$END_SEC" ]; then
            DURATION=$((END_SEC - START_SEC))
            MINUTES=$((DURATION / 60))
            SECONDS=$((DURATION % 60))
            echo "Duration: ${MINUTES}m ${SECONDS}s"
            echo ""

            # Compare to baseline
            BASELINE_MIN=31
            if [ $MINUTES -le 40 ]; then
                echo "✓ PERFORMANCE RESTORED: $MINUTES min (baseline: $BASELINE_MIN min)"
                echo "  Within acceptable range (< 40 min)"
            elif [ $MINUTES -le 60 ]; then
                echo "⚠️  SLOWER THAN BASELINE: $MINUTES min (baseline: $BASELINE_MIN min)"
                echo "  But within 1 hour, acceptable"
            else
                echo "❌ PERFORMANCE DEGRADED: $MINUTES min (baseline: $BASELINE_MIN min)"
                echo "  Significantly slower than baseline!"
            fi
        fi
    fi
    echo ""
else
    echo "❌ FAILURE: No correct solution found"
    echo ""

    # Check for timeouts/hangs
    if grep -q "VERIFICATION SAFEGUARD.*TIMEOUT" "$LOG_FILE"; then
        echo "⚠️  Verification timeouts detected (safeguards working)"
    fi

    if grep -q "STUCK DETECTION.*Stuck pattern detected" "$LOG_FILE"; then
        echo "⚠️  Stuck pattern detected"
    fi

    echo "Check log file for details: $LOG_FILE"
fi

echo ""
echo "========================================================================"
