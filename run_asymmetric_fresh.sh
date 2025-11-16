#!/bin/bash
# Fresh Start with Asymmetric Reasoning
#
# Purpose: Start a new problem with optimal asymmetric reasoning settings
#          - LOW reasoning for generation (fast, no truncation)
#          - HIGH reasoning for verification (rigorous, catches errors)
#
# Usage: ./run_asymmetric_fresh.sh [problem_file] [memory_file] [log_file]

set -e

# Configuration
PROBLEM_FILE="${1:-problems/imo01.txt}"
MEMORY_FILE="${2:-memory_asymmetric_$(date +%Y%m%d_%H%M%S).json}"
LOG_FILE="${3:-asymmetric_$(date +%Y%m%d_%H%M%S).log}"

echo "========================================="
echo "Fresh Start: Asymmetric Reasoning"
echo "========================================="
echo ""
echo "Optimal configuration for IMO problems:"
echo "  - Solution generation: LOW reasoning (prevents truncation)"
echo "  - Verification: HIGH reasoning (rigorous checking)"
echo "  - Best of both worlds!"
echo ""
echo "Configuration:"
echo "  Problem: $PROBLEM_FILE"
echo "  Memory: $MEMORY_FILE"
echo "  Log: $LOG_FILE"
echo ""

# Check if problem file exists
if [ ! -f "$PROBLEM_FILE" ]; then
    echo "ERROR: Problem file not found: $PROBLEM_FILE"
    exit 1
fi

echo "Expected behavior:"
echo "  - Fast iterations (LOW generation)"
echo "  - No truncation (LOW generation)"
echo "  - Rigorous verification (HIGH verification)"
echo "  - Iterations: 20-30 (estimated)"
echo "  - Time: 2-3 hours (estimated)"
echo "  - Success rate: 50-70% (predicted)"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to start..."
sleep 5

# Run with asymmetric reasoning
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
    --solution-reasoning low \
    --verification-reasoning high \
    --memory "$MEMORY_FILE" \
    --log "$LOG_FILE" \
    --max_runs 1

echo ""
echo "========================================="
echo "Run Complete!"
echo "========================================="
echo ""
echo "Results:"
echo "  Log: $LOG_FILE"
echo "  Memory: $MEMORY_FILE"
echo ""
echo "To analyze results:"
echo "  python monitor_agent_progress.py $LOG_FILE --once"
echo ""
