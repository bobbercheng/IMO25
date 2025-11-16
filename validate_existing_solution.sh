#!/bin/bash
# Validation Script: Test existing low/low solution with high reasoning verification
#
# Purpose: Determine if your successful low/low solution is truly correct
#          by verifying it with high reasoning effort
#
# Usage: ./validate_existing_solution.sh [memory_file] [log_file]
#
# Expected outcomes:
#   - Passes quickly → Solution is truly correct!
#   - Fails → Low reasoning was too lenient, need more iterations

set -e

# Configuration
MEMORY_FILE="${1:-run_log_gpt_oss/memory_low_success.json}"
LOG_FILE="${2:-validate_high_verification.log}"
PROBLEM_FILE="problems/imo01.txt"

echo "========================================="
echo "Validation Test: Resume with High Verification"
echo "========================================="
echo ""
echo "Purpose: Validate if low/low solution passes high reasoning verification"
echo ""
echo "Configuration:"
echo "  Problem: $PROBLEM_FILE"
echo "  Memory: $MEMORY_FILE"
echo "  Log: $LOG_FILE"
echo "  Solution reasoning: low (for any new iterations)"
echo "  Verification reasoning: high (RIGOROUS checking)"
echo ""

# Check if memory file exists
if [ ! -f "$MEMORY_FILE" ]; then
    echo "ERROR: Memory file not found: $MEMORY_FILE"
    echo ""
    echo "If you don't have a memory file, you can:"
    echo "  1. Extract the solution from your log file"
    echo "  2. Create a memory file manually"
    echo "  3. Or run a fresh test with asymmetric reasoning"
    echo ""
    echo "For fresh test, run:"
    echo "  ./run_asymmetric_fresh.sh"
    exit 1
fi

# Check if problem file exists
if [ ! -f "$PROBLEM_FILE" ]; then
    echo "ERROR: Problem file not found: $PROBLEM_FILE"
    echo "Please update PROBLEM_FILE in this script"
    exit 1
fi

echo "Starting validation test..."
echo "This will:"
echo "  1. Load existing solution from memory"
echo "  2. Verify with HIGH reasoning (rigorous)"
echo "  3. If fails: Generate corrections with LOW reasoning"
echo "  4. Verify corrections with HIGH reasoning"
echo "  5. Repeat until 5 consecutive HIGH reasoning passes"
echo ""
echo "Expected time: 1-2 hours"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to start..."
sleep 5

# Run the validation
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
    --memory "$MEMORY_FILE" \
    --resume \
    --verification-reasoning high \
    --solution-reasoning low \
    --log "$LOG_FILE" \
    --max_runs 1

echo ""
echo "========================================="
echo "Validation Complete!"
echo "========================================="
echo ""
echo "Check the results in: $LOG_FILE"
echo ""
echo "To monitor in real-time (in another terminal):"
echo "  python monitor_agent_progress.py $LOG_FILE --follow --interval 60"
echo ""
echo "To analyze results:"
echo "  python monitor_agent_progress.py $LOG_FILE --once"
echo ""
