#!/bin/bash
# Test script for in-RLAC verification feature
# Tests that verification catches construction errors early in problem 1

set -e  # Exit on error

echo "=========================================="
echo "Testing In-RLAC Verification Feature"
echo "=========================================="
echo ""

# Configuration
PROBLEM_FILE="${1:-problems/imo01.txt}"
LOG_DIR="test_rlac_log"
TEST_NAME="inline_verification_test"

# Create log directory
mkdir -p "$LOG_DIR"

# Test timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/${TEST_NAME}_${TIMESTAMP}.log"
MEMORY_FILE="$LOG_DIR/${TEST_NAME}_${TIMESTAMP}.json"

echo "Problem: $PROBLEM_FILE"
echo "Log: $LOG_FILE"
echo "Memory: $MEMORY_FILE"
echo ""

# Configuration for verification
# P0-3 FIX: Reduced frequency to reduce overhead
# OLD: verify every 2 rounds starting at 0 → 6 verifications for 12 rounds
# NEW: verify every 4 rounds starting at 3 → ~3 verifications for 12 rounds
export RLAC_VERIFY_EVERY_N_ROUNDS=4
export RLAC_VERIFY_START_ROUND=3
export RLAC_DISABLE_INLINE_VERIFICATION=false

echo "Verification Configuration:"
echo "  - RLAC_VERIFY_EVERY_N_ROUNDS=$RLAC_VERIFY_EVERY_N_ROUNDS"
echo "  - RLAC_VERIFY_START_ROUND=$RLAC_VERIFY_START_ROUND"
echo "  - RLAC_DISABLE_INLINE_VERIFICATION=$RLAC_DISABLE_INLINE_VERIFICATION"
echo ""

echo "Running RLAC with in-RLAC verification..."
echo "=========================================="
echo ""

# Run RLAC with inline verification
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
  --use-rlac \
  --rlac-max-rounds 15 \
  --rlac-robust-threshold 3 \
  --rlac-stuck-threshold 4 \
  --solution-reasoning low \
  --rlac-critic-reasoning medium \
  --log "$LOG_FILE" \
  --memory "$MEMORY_FILE"

echo ""
echo "=========================================="
echo "Test completed!"
echo "=========================================="
echo ""

# Check if verification was used
echo "Checking if verification was used..."
if grep -q "VERIFICATION-BASED ATTACK" "$LOG_FILE"; then
    echo "✓ SUCCESS: Verification was used during RLAC rounds"

    # Count how many times verification was used
    VERIFY_COUNT=$(grep -c "VERIFICATION-BASED ATTACK" "$LOG_FILE" || true)
    echo "  Verification used $VERIFY_COUNT time(s)"

    # Check if critical errors were caught
    if grep -q "Critical Error" "$LOG_FILE"; then
        echo "✓ SUCCESS: Critical errors detected by verification"

        # Find which round detected the error
        FIRST_ERROR_ROUND=$(grep -B 5 "Critical Error" "$LOG_FILE" | grep "Round" | head -1 || echo "Unknown")
        echo "  First error detected in: $FIRST_ERROR_ROUND"
    else
        echo "  No critical errors detected (solution may be correct from start)"
    fi
else
    echo "⚠ WARNING: Verification was not used during RLAC"
    echo "  Check if verify_func is being passed correctly"
fi

echo ""
echo "Checking final status..."
FINAL_STATUS=$(grep "TIER.*FINAL" "$LOG_FILE" | tail -1 || echo "Status not found")
echo "$FINAL_STATUS"

echo ""
echo "Log file: $LOG_FILE"
echo "Memory file: $MEMORY_FILE"
echo ""
echo "To view detailed logs:"
echo "  cat $LOG_FILE | less"
echo ""
echo "To check verification usage:"
echo "  grep 'VERIFICATION-BASED ATTACK' $LOG_FILE"
echo ""
