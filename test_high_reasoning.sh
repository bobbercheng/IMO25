#!/bin/bash
# High Reasoning Validation Test
# Tests that high reasoning effort can achieve "verification good" status
# Based on Phase 1.5 comprehensive analysis showing low/medium reasoning is insufficient

set -e  # Exit on error

echo "=========================================="
echo "High Reasoning Validation Test"
echo "=========================================="
echo ""
echo "HYPOTHESIS: High reasoning throughout RLAC will achieve 'verification good'"
echo "CONTEXT: Phase 0→1→1.5 all failed with 0% verification using low/medium reasoning"
echo "ROOT CAUSE: Low/medium reasoning structurally insufficient for IMO-level proof rigor"
echo ""
echo "Expected Results:"
echo "  - Cost: \$50-75 per problem (10-15× current)"
echo "  - Time: 4-6 hours (8-12× current ~40min)"
echo "  - Verification success: 80-90% (vs 0% with low/medium)"
echo "  - Cost per success: \$59-88 (vs \$∞ with low/medium)"
echo ""

# Configuration
PROBLEM_FILE="${1:-problems/imo01.txt}"
LOG_DIR="test_rlac_log"
TEST_NAME="high_reasoning_test"

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

# HIGH REASONING CONFIGURATION
# This is the CRITICAL change: Use high reasoning throughout instead of low/medium
export RLAC_SOL_REASONING=high           # Generator uses high reasoning (was: low)
export RLAC_CRITIC_REASONING=high        # Critic uses high reasoning (was: medium)
export RLAC_VERIFY_REASONING=high        # Verification uses high reasoning (already was high)

# RLAC parameters (keep similar to Phase 1.5 for comparison)
export RLAC_MAX_ROUNDS=20                # Increase from 15 to give high reasoning more time
export RLAC_ROBUST_THRESHOLD=3           # Same as Phase 1.5
export RLAC_STUCK_THRESHOLD=4            # Same as Phase 1.5

# Phase 1.5 enhancements (keep active)
export RLAC_ACCEPT_SUSPICIOUS_THRESHOLD=3  # Quick Win #1 threshold
export RLAC_SUSPICIOUS_LOOKBACK=4          # Quick Win #1 lookback
export RLAC_ANSWER_STABILITY_WINDOW=3      # Enhancement 1: Answer stability

# Verification configuration (keep active for comprehensive checking)
export RLAC_VERIFY_EVERY_N_ROUNDS=2      # Run verification every 2 rounds
export RLAC_VERIFY_START_ROUND=0         # Start verification from round 0
export RLAC_DISABLE_INLINE_VERIFICATION=false

echo "=========================================="
echo "HIGH REASONING CONFIGURATION:"
echo "=========================================="
echo "  Solution Reasoning:      HIGH (was: low)"
echo "  Critic Reasoning:        HIGH (was: medium)"
echo "  Verification Reasoning:  HIGH (unchanged)"
echo ""
echo "RLAC Parameters:"
echo "  - RLAC_MAX_ROUNDS=$RLAC_MAX_ROUNDS (was: 15)"
echo "  - RLAC_ROBUST_THRESHOLD=$RLAC_ROBUST_THRESHOLD"
echo "  - RLAC_STUCK_THRESHOLD=$RLAC_STUCK_THRESHOLD"
echo ""
echo "Phase 1.5 Enhancements (ACTIVE):"
echo "  - RLAC_ACCEPT_SUSPICIOUS_THRESHOLD=$RLAC_ACCEPT_SUSPICIOUS_THRESHOLD"
echo "  - RLAC_SUSPICIOUS_LOOKBACK=$RLAC_SUSPICIOUS_LOOKBACK"
echo "  - RLAC_ANSWER_STABILITY_WINDOW=$RLAC_ANSWER_STABILITY_WINDOW"
echo ""
echo "Verification Configuration:"
echo "  - RLAC_VERIFY_EVERY_N_ROUNDS=$RLAC_VERIFY_EVERY_N_ROUNDS"
echo "  - RLAC_VERIFY_START_ROUND=$RLAC_VERIFY_START_ROUND"
echo "  - RLAC_DISABLE_INLINE_VERIFICATION=$RLAC_DISABLE_INLINE_VERIFICATION"
echo ""
echo "=========================================="
echo ""

START_TIME=$(date +%s)
echo "Start time: $(date)"
echo "Running RLAC with HIGH reasoning throughout..."
echo "=========================================="
echo ""

# Run RLAC with HIGH reasoning configuration
# Key change: Using command-line flags to override default reasoning levels
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
  --use-rlac \
  --rlac-max-rounds $RLAC_MAX_ROUNDS \
  --rlac-robust-threshold $RLAC_ROBUST_THRESHOLD \
  --rlac-stuck-threshold $RLAC_STUCK_THRESHOLD \
  --solution-reasoning high \
  --rlac-critic-reasoning high \
  --verification-reasoning high \
  --log "$LOG_FILE" \
  --memory "$MEMORY_FILE"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
DURATION_MIN=$((DURATION / 60))
DURATION_SEC=$((DURATION % 60))

echo ""
echo "=========================================="
echo "Test completed!"
echo "=========================================="
echo ""
echo "End time: $(date)"
echo "Duration: ${DURATION_MIN}m ${DURATION_SEC}s ($(echo "scale=1; $DURATION / 60" | bc) minutes)"
echo ""

# Analysis and validation
echo "=========================================="
echo "Analyzing Results..."
echo "=========================================="
echo ""

# Check if verification was used
echo "1. Checking if verification was used during RLAC..."
if grep -q "VERIFICATION-BASED ATTACK" "$LOG_FILE"; then
    VERIFY_COUNT=$(grep -c "VERIFICATION-BASED ATTACK" "$LOG_FILE" || true)
    echo "✓ SUCCESS: Verification was used $VERIFY_COUNT time(s)"
else
    echo "⚠ WARNING: Verification was not used during RLAC"
fi
echo ""

# Check for Enhancement 1 (Answer Stability)
echo "2. Checking Enhancement 1 (Answer Stability)..."
if grep -q "ENHANCEMENT 1.*ANSWER STABILITY" "$LOG_FILE"; then
    STABILITY_COUNT=$(grep -c "ENHANCEMENT 1.*ANSWER STABILITY" "$LOG_FILE" || true)
    echo "✓ Enhancement 1 activated $STABILITY_COUNT time(s)"

    # Check if answer was stable
    if grep -q "Stability: ✓ STABLE" "$LOG_FILE"; then
        echo "✓ Answer achieved STABLE status"
    else
        echo "⚠ Answer remained UNSTABLE"
    fi
else
    echo "- Enhancement 1 not triggered (may have exited via other path)"
fi
echo ""

# Check for Enhancement 2 (Verification Feedback)
echo "3. Checking Enhancement 2 (Verification Feedback)..."
if grep -q "ENHANCEMENT 2.*VERIFICATION FEEDBACK" "$LOG_FILE"; then
    FEEDBACK_COUNT=$(grep -c "ENHANCEMENT 2.*VERIFICATION FEEDBACK" "$LOG_FILE" || true)
    echo "✓ Enhancement 2 activated $FEEDBACK_COUNT time(s)"
else
    echo "- Enhancement 2 not triggered (verification may have passed)"
fi
echo ""

# Count verdict types
echo "4. Verdict Distribution:"
ROBUST_COUNT=$(grep -c "Verdict: ROBUST" "$LOG_FILE" || echo "0")
SUSPICIOUS_COUNT=$(grep -c "Verdict: SUSPICIOUS" "$LOG_FILE" || echo "0")
BROKEN_COUNT=$(grep -c "Verdict: BROKEN" "$LOG_FILE" || echo "0")
TOTAL_VERDICTS=$((ROBUST_COUNT + SUSPICIOUS_COUNT + BROKEN_COUNT))

if [ $TOTAL_VERDICTS -gt 0 ]; then
    ROBUST_PCT=$(echo "scale=1; $ROBUST_COUNT * 100 / $TOTAL_VERDICTS" | bc)
    SUSPICIOUS_PCT=$(echo "scale=1; $SUSPICIOUS_COUNT * 100 / $TOTAL_VERDICTS" | bc)
    BROKEN_PCT=$(echo "scale=1; $BROKEN_COUNT * 100 / $TOTAL_VERDICTS" | bc)

    echo "  - ROBUST:     $ROBUST_COUNT ($ROBUST_PCT%)"
    echo "  - SUSPICIOUS: $SUSPICIOUS_COUNT ($SUSPICIOUS_PCT%)"
    echo "  - BROKEN:     $BROKEN_COUNT ($BROKEN_PCT%)"
    echo "  - Total rounds: $TOTAL_VERDICTS"
else
    echo "  - No verdicts found (check log file)"
fi
echo ""

# Check final tier status
echo "5. Final Tier Status:"
FINAL_TIER=$(grep "TIER.*FINAL\|tier_status" "$LOG_FILE" | tail -1 || echo "Not found")
echo "  $FINAL_TIER"
echo ""

# THE CRITICAL CHECK: Verification Good Status
echo "=========================================="
echo "6. *** VERIFICATION GOOD STATUS *** (CRITICAL)"
echo "=========================================="

# Check multiple patterns for verification success
VERIFICATION_GOOD="UNKNOWN"

if grep -q "Is verification good.*yes" "$LOG_FILE"; then
    VERIFICATION_GOOD="YES"
    echo "✓✓✓ SUCCESS: Verification good = YES ✓✓✓"
elif grep -q "Is verification good.*no" "$LOG_FILE"; then
    VERIFICATION_GOOD="NO"
    echo "✗✗✗ FAILURE: Verification good = NO ✗✗✗"
elif grep -q "verification.*passed" "$LOG_FILE"; then
    VERIFICATION_GOOD="YES (inferred)"
    echo "✓✓✓ SUCCESS: Verification passed ✓✓✓"
else
    echo "⚠ WARNING: Verification status unclear (check log manually)"
fi
echo ""

# Extract final verification feedback
echo "7. Final Verification Feedback:"
FINAL_VERIFY=$(grep -A10 "Final verification\|SUSPICIOUS CONVERGENCE.*Running final verification" "$LOG_FILE" | tail -10 || echo "Not found")
echo "$FINAL_VERIFY"
echo ""

# Comparison to Phase 1.5 baseline
echo "=========================================="
echo "Comparison to Phase 1.5 Baseline:"
echo "=========================================="
echo ""
echo "Phase 1.5 (Low/Medium Reasoning):"
echo "  - Duration: 40-62 min"
echo "  - Rounds: 14-15"
echo "  - ROBUST rate: 7-13%"
echo "  - Verification good: NO (0/2 = 0%)"
echo "  - Answer consistency: 0% (different answers each run)"
echo "  - Cost: ~\$5 per run"
echo ""
echo "This Test (High Reasoning):"
echo "  - Duration: ${DURATION_MIN}m ${DURATION_SEC}s"
echo "  - Rounds: $TOTAL_VERDICTS"
echo "  - ROBUST rate: $ROBUST_PCT%"
echo "  - Verification good: $VERIFICATION_GOOD"
echo "  - Cost: ~\$50-75 (estimated)"
echo ""

# Hypothesis validation
echo "=========================================="
echo "HYPOTHESIS VALIDATION:"
echo "=========================================="
echo ""
echo "Hypothesis: High reasoning achieves 'verification good' with 80-90% probability"
echo ""

if [ "$VERIFICATION_GOOD" = "YES" ] || [ "$VERIFICATION_GOOD" = "YES (inferred)" ]; then
    echo "✓✓✓ HYPOTHESIS CONFIRMED ✓✓✓"
    echo ""
    echo "High reasoning successfully achieved verification good status!"
    echo "This validates that the root cause was reasoning insufficiency."
    echo ""
    echo "Key Insights:"
    echo "  1. Process improvements (Phase 1.5) failed because they didn't address capability"
    echo "  2. High reasoning CAN generate IMO-level rigorous proofs"
    echo "  3. Cost per success: \$50-75 (vs \$∞ with low/medium)"
    echo ""
    echo "Recommendation: Deploy high reasoning for hard problems like Problem 1"

elif [ "$VERIFICATION_GOOD" = "NO" ]; then
    echo "✗✗✗ HYPOTHESIS REJECTED ✗✗✗"
    echo ""
    echo "High reasoning also failed to achieve verification good."
    echo "This suggests the root cause is deeper than reasoning effort."
    echo ""
    echo "Possible explanations:"
    echo "  1. Problem 1 is fundamentally too hard for RLAC approach"
    echo "  2. Verification standards are too strict for any RLAC output"
    echo "  3. Additional mechanisms needed beyond high reasoning"
    echo ""
    echo "Next steps:"
    echo "  - Review final verification feedback in detail"
    echo "  - Check if errors are different from low/medium reasoning"
    echo "  - Consider alternative approaches (e.g., formal proof verification)"

else
    echo "⚠ INCONCLUSIVE ⚠"
    echo ""
    echo "Could not determine verification status from logs."
    echo "Please review the log file manually."
fi
echo ""

# Summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""
echo "Test Name: High Reasoning Validation"
echo "Problem: $PROBLEM_FILE"
echo "Duration: ${DURATION_MIN}m ${DURATION_SEC}s (expected: 4-6 hours)"
echo "Rounds: $TOTAL_VERDICTS (max: $RLAC_MAX_ROUNDS)"
echo "Verification Good: $VERIFICATION_GOOD"
echo ""
echo "Log file: $LOG_FILE"
echo "Memory file: $MEMORY_FILE"
echo ""
echo "To view detailed logs:"
echo "  cat $LOG_FILE | less"
echo ""
echo "To check verification status:"
echo "  grep -i 'verification good' $LOG_FILE"
echo ""
echo "To extract final answer:"
echo "  grep -A5 'Final answer\\|boxed' $LOG_FILE | tail -10"
echo ""
