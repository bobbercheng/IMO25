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
#
# Recommended configurations:
# - Quick test: low solution, medium critic (this script)
# - Thorough test: low solution, high critic
# - Fast iteration: low solution, low critic

echo "=========================================="
echo "RLAC Implementation Test"
echo "=========================================="
echo ""

# Configuration
PROBLEM_FILE="problems/imo01.txt"
LOG_FILE="test_rlac_output.log"
MEMORY_FILE="test_rlac_memory.json"

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
echo "  - Max 10 rounds"
echo "  - Robust threshold: 3 (consecutive passes needed)"
echo "  - Stuck threshold: 3 (failures before strategy shift)"
echo "  - Solution reasoning: low (fast generation)"
echo "  - Critic reasoning: medium (balanced attack rigor)"
echo "  - Self-improvement reasoning: medium (balanced refinement)"
echo ""

# Run the RLAC agent
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
    --use-rlac \
    --rlac-max-rounds 10 \
    --rlac-robust-threshold 3 \
    --rlac-stuck-threshold 3 \
    --solution-reasoning low \
    --rlac-critic-reasoning medium \
    --self-improvement-reasoning medium \
    --rlac-max-regeneration 3 \
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

exit $EXIT_CODE
