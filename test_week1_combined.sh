#!/bin/bash
# Test Week 1 Priorities (Combined): All Three Feedback Improvements
#
# This script tests all three Week 1 priority implementations together:
#   Priority 1: High reasoning self-improvement (proactive error detection)
#   Priority 2: Top-3 error prioritization (reduces cognitive load)
#   Priority 3: Structured JSON feedback (machine-readable format)
#
# Expected combined impact:
#   - Success rate: 0% → 50-65% (baseline asymmetric → Week 1)
#   - Iterations: 29+ (fail) → 12-15 (success)
#   - Cost: -40% reduction
#   - Feedback actionability: +60-70%

set -e

PROBLEM_FILE="${1:-problems/imo01.txt}"
MEMORY_FILE="memory_week1_combined_$(date +%Y%m%d_%H%M%S).json"
LOG_FILE="test_week1_combined_$(date +%Y%m%d_%H%M%S).log"

echo "========================================="
echo "Testing: Week 1 Combined (Priorities 1-3)"
echo "========================================="
echo ""
echo "Implementing ALL three feedback improvements:"
echo ""
echo "Priority 1: High Reasoning Self-Improvement"
echo "  - Uses HIGH reasoning for self-improvement step"
echo "  - Proactive error detection (catches errors BEFORE verification)"
echo "  - Expected impact: +25% success rate, -37% cost"
echo ""
echo "Priority 2: Top-3 Error Prioritization"
echo "  - Shows only top 3 most critical errors"
echo "  - Reduces cognitive load, enables incremental fixes"
echo "  - Expected impact: +50-60% effectiveness"
echo ""
echo "Priority 3: Structured JSON Feedback"
echo "  - Machine-readable error format"
echo "  - Clear location/error/fix structure"
echo "  - Expected impact: +60-70% LLM comprehension"
echo ""
echo "Configuration:"
echo "  Problem: $PROBLEM_FILE"
echo "  Memory: $MEMORY_FILE"
echo "  Log: $LOG_FILE"
echo ""
echo "Reasoning levels:"
echo "  Solution generation: LOW (prevents truncation)"
echo "  Self-improvement: HIGH (proactive error detection)"
echo "  Verification: HIGH (rigorous checking)"
echo ""
echo "Feedback settings:"
echo "  Top-N errors: 3 (show only top 3 critical errors)"
echo "  Format: JSON (structured, machine-readable)"
echo ""
echo "Expected outcomes:"
echo "  - Self-improvement catches 80% of errors BEFORE verification"
echo "  - Feedback shows only 3 most critical errors with clear priorities"
echo "  - JSON format enables precise error localization and fixes"
echo "  - Combined effect: 50-65% success rate (vs 0% baseline)"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to start..."
sleep 5

# Run with all three Week 1 priorities enabled
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
    --solution-reasoning low \
    --self-improvement-reasoning high \
    --verification-reasoning high \
    --feedback-top-n 3 \
    --feedback-format json \
    --memory "$MEMORY_FILE" \
    --log "$LOG_FILE" \
    --max_runs 1

echo ""
echo "========================================="
echo "Test Complete!"
echo "========================================="
echo ""
echo "Results:"
echo "  Log: $LOG_FILE"
echo "  Memory: $MEMORY_FILE"
echo ""
echo "To analyze results:"
echo ""
echo "  # Check Priority 1 (High reasoning self-improvement):"
echo "  grep 'Using high reasoning for self-improvement' $LOG_FILE"
echo ""
echo "  # Check Priority 2 (Top-3 prioritization):"
echo "  grep 'Showing TOP 3 CRITICAL errors' $LOG_FILE"
echo ""
echo "  # Check Priority 3 (JSON feedback):"
echo "  grep -A10 '\"status\":' $LOG_FILE | head -20"
echo ""
echo "  # Count total verification failures (should be ~50% fewer):"
echo "  grep -c 'failed' $LOG_FILE || echo '0'"
echo ""
echo "  # Check final success:"
echo "  grep 'Correct solution found' $LOG_FILE && echo 'SUCCESS!' || echo 'Still iterating...'"
echo ""
echo "Expected improvements vs baseline (asymmetric failure):"
echo "  - Success rate: 0% → 50-65%"
echo "  - Iterations: 29+ (fail) → 12-15"
echo "  - Cost per solution: -40%"
echo "  - Feedback actionability: +60-70%"
echo ""
