#!/bin/bash
# RLAC Quick Test Script
#
# This script runs a quick test of the RLAC implementation on a sample problem.
# It demonstrates the basic usage and validates that all components are working.
#
# RLAC Configuration Guide:
# -------------------------
# --solution-reasoning: Controls solution generation speed/quality (low=fast, high=thorough)
# --rlac-critic-reasoning: Controls adversarial attack rigor (medium recommended for balance)
# --self-improvement-reasoning: Controls self-improvement step quality
# --rlac-max-rounds: Maximum adversarial rounds before timeout
# --rlac-robust-threshold: Consecutive ROBUST verdicts needed for success
# --rlac-stuck-threshold: Consecutive failures before declaring stuck
# --rlac-max-regeneration: Maximum regeneration attempts when stuck
#
# Recommended configurations:
# - Quick test: low solution, medium critic, 10 rounds (this script)
# - Thorough test: low solution, high critic, 20 rounds
# - Fast iteration: low solution, low critic, 8 rounds
# - Hard problems: low solution, high critic, 25 rounds, stuck-threshold=5
#
# P0-P3 Bug Fixes (2024):
# -------------------------
# P0: Near-success protection - 2/3 ROBUST decrements instead of resetting
# P1: Counterexample verification - validates counterexamples before defense
# P2: Answer lock - locks answer after 2 consecutive ROBUST verdicts
# P3: Truncation detection - downgrades BROKEN on short/truncated responses
#
# Run unit tests: python code/test_rlac_bug_fixes.py

echo "=========================================="
echo "RLAC Implementation Test"
echo "=========================================="
echo ""

# Configuration (adjustable)
PROBLEM_FILE="${1:-problems/imo01.txt}"
LOG_FILE="${2:-test_rlac_output.log}"
MEMORY_FILE="${3:-test_rlac_memory.json}"

# RLAC parameters (can be adjusted for different scenarios)
MAX_ROUNDS="${RLAC_MAX_ROUNDS:-15}"           # Increased from 10 for hard problems
ROBUST_THRESHOLD="${RLAC_ROBUST_THRESHOLD:-3}"
STUCK_THRESHOLD="${RLAC_STUCK_THRESHOLD:-4}"   # Increased from 3 for more patience
MAX_REGENERATION="${RLAC_MAX_REGEN:-4}"        # Increased from 3
SOLUTION_REASONING="${RLAC_SOL_REASONING:-low}"
CRITIC_REASONING="${RLAC_CRITIC_REASONING:-medium}"
SELF_IMPROVE_REASONING="${RLAC_SELF_REASONING:-medium}"

# Check if problem file exists
if [ ! -f "$PROBLEM_FILE" ]; then
    echo "ERROR: Problem file not found: $PROBLEM_FILE"
    echo "Please create a test problem file or update PROBLEM_FILE variable"
    exit 1
fi

echo "Configuration:"
echo "  Problem file: $PROBLEM_FILE"
echo "  Log file: $LOG_FILE"
echo "  Memory file: $MEMORY_FILE"
echo ""

echo "Running RLAC test..."
echo "This will run with:"
echo "  - RLAC mode enabled"
echo "  - Max $MAX_ROUNDS rounds (env: RLAC_MAX_ROUNDS)"
echo "  - Robust threshold: $ROBUST_THRESHOLD (consecutive passes needed)"
echo "  - Stuck threshold: $STUCK_THRESHOLD (failures before strategy shift)"
echo "  - Max regeneration: $MAX_REGENERATION attempts"
echo "  - Solution reasoning: $SOLUTION_REASONING (fast generation)"
echo "  - Critic reasoning: $CRITIC_REASONING (attack rigor)"
echo "  - Self-improvement reasoning: $SELF_IMPROVE_REASONING (refinement)"
echo ""
echo "P0-P3 fixes enabled:"
echo "  - P0: Near-success protection (2/3 ROBUST grace failure)"
echo "  - P1: Counterexample verification before defense"
echo "  - P2: Answer lock after 2 consecutive ROBUST"
echo "  - P3: Truncation detection for short responses"
echo ""

# Run the RLAC agent
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
    --use-rlac \
    --rlac-max-rounds "$MAX_ROUNDS" \
    --rlac-robust-threshold "$ROBUST_THRESHOLD" \
    --rlac-stuck-threshold "$STUCK_THRESHOLD" \
    --solution-reasoning "$SOLUTION_REASONING" \
    --rlac-critic-reasoning "$CRITIC_REASONING" \
    --self-improvement-reasoning "$SELF_IMPROVE_REASONING" \
    --rlac-max-regeneration "$MAX_REGENERATION" \
    --log "$LOG_FILE" \
    --memory "$MEMORY_FILE" \
    --max_runs 1

EXIT_CODE=$?

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "Exit code: $EXIT_CODE"
echo ""

# Check for output files
echo "Generated files:"
ls -lh test_rlac_* 2>/dev/null || echo "  No output files found"

echo ""
echo "To view the log:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To analyze attack history:"
echo "  cat ${MEMORY_FILE/.json/_rlac_history.json} | jq '.metrics'"
echo ""
echo "To check for success:"
echo "  grep 'RLAC SUCCESS' $LOG_FILE"
echo ""
echo "To check for failure:"
echo "  grep 'RLAC FAILURE\\|RLAC TIMEOUT' $LOG_FILE"
echo ""
echo "To check P0-P3 fix activity:"
echo "  grep 'RLAC PROTECTION\\|RLAC P1\\|RLAC LOCK\\|RLAC TRUNCATION' $LOG_FILE"
echo ""

# For hard problems, suggest increasing parameters
if [ $EXIT_CODE -ne 0 ]; then
    echo "=========================================="
    echo "Tip: For hard problems, try increasing parameters:"
    echo "  RLAC_MAX_ROUNDS=25 RLAC_STUCK_THRESHOLD=5 ./test_rlac.sh"
    echo "=========================================="
fi

exit $EXIT_CODE
