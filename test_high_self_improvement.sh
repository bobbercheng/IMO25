#!/bin/bash
# Test High Reasoning Self-Improvement (Priority 1)
#
# This script tests the newly implemented high reasoning self-improvement feature.
# Expected behavior:
#   - Solution generation: LOW reasoning (fast, no truncation)
#   - Self-improvement: HIGH reasoning (proactive error detection)
#   - Verification: HIGH reasoning (rigorous checking)
#
# Expected improvements vs baseline:
#   - Success rate: +25% (60% → 75%)
#   - Iterations: -41% (17 → 10)
#   - Cost: -37% ($4.30 savings per solution)

set -e

PROBLEM_FILE="${1:-problems/imo01.txt}"
MEMORY_FILE="memory_high_self_improve_$(date +%Y%m%d_%H%M%S).json"
LOG_FILE="test_high_self_improve_$(date +%Y%m%d_%H%M%S).log"

echo "========================================="
echo "Testing: High Reasoning Self-Improvement"
echo "========================================="
echo ""
echo "Feature: Priority 1 from Week 1 implementation plan"
echo "Implements: Proactive error detection (high reasoning self-improvement)"
echo ""
echo "Configuration:"
echo "  Problem: $PROBLEM_FILE"
echo "  Memory: $MEMORY_FILE"
echo "  Log: $LOG_FILE"
echo ""
echo "Reasoning levels:"
echo "  Solution generation: LOW (prevents truncation)"
echo "  Self-improvement: HIGH (catches errors proactively)"
echo "  Verification: HIGH (rigorous checking)"
echo ""
echo "Expected behavior:"
echo "  - Self-improvement catches 80% of errors BEFORE verification"
echo "  - Reduces correction iterations by ~7 per problem"
echo "  - Saves $4.30 per successful solution (37% cost reduction)"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to start..."
sleep 5

# Run with high reasoning self-improvement
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
    --solution-reasoning low \
    --self-improvement-reasoning high \
    --verification-reasoning high \
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
echo "  # Check if self-improvement is using high reasoning:"
echo "  grep 'Using high reasoning for self-improvement' $LOG_FILE"
echo ""
echo "  # Count verification failures (should be ~50% fewer):"
echo "  grep -c 'Critical Errors' $LOG_FILE || echo '0'"
echo ""
echo "  # Check final success:"
echo "  grep 'Correct solution found' $LOG_FILE && echo 'SUCCESS!' || echo 'Still iterating...'"
echo ""
