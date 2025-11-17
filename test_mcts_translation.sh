#!/bin/bash
# Test script for MCTS-enhanced BFS and Translation Layer features
# Usage: ./test_mcts_translation.sh

set -e  # Exit on error

echo "======================================================================"
echo "MCTS-Enhanced BFS and Translation Layer Test Suite"
echo "======================================================================"
echo ""

# Configuration
PROBLEM_FILE="problems/imo01.txt"
LOG_DIR="test_logs_mcts_translation"
mkdir -p "$LOG_DIR"

echo "Test environment setup:"
echo "  Problem file: $PROBLEM_FILE"
echo "  Log directory: $LOG_DIR"
echo "  Timestamp: $(date)"
echo ""

# Test 1: Standard BFS (baseline)
echo "======================================================================"
echo "Test 1: Standard BFS (Low/Low/Low, 3 attempts) - BASELINE"
echo "======================================================================"
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
  --solution-reasoning low \
  --self-improvement-reasoning low \
  --verification-reasoning low \
  --num-initial-attempts 3 \
  --memory "$LOG_DIR/test1_bfs_low.json" \
  --log "$LOG_DIR/test1_bfs_low.log" \
  --max_runs 1

echo ""
echo "Test 1 complete. Check $LOG_DIR/test1_bfs_low.log for results."
echo ""
sleep 2

# Test 2: Translation Layer with Asymmetric Reasoning
echo "======================================================================"
echo "Test 2: Translation Layer (Low/High/High with translation)"
echo "======================================================================"
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
  --solution-reasoning low \
  --self-improvement-reasoning high \
  --verification-reasoning high \
  --use-translation \
  --num-initial-attempts 3 \
  --memory "$LOG_DIR/test2_translation.json" \
  --log "$LOG_DIR/test2_translation.log" \
  --max_runs 1

echo ""
echo "Test 2 complete. Check $LOG_DIR/test2_translation.log for results."
echo "Look for [TRANSLATION] markers to see translation process."
echo ""
sleep 2

# Test 3: MCTS-guided exploration (Low reasoning)
echo "======================================================================"
echo "Test 3: MCTS-guided exploration (Low/Low/Low, 5 simulations)"
echo "======================================================================"
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
  --solution-reasoning low \
  --self-improvement-reasoning low \
  --verification-reasoning low \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --memory "$LOG_DIR/test3_mcts_low.json" \
  --log "$LOG_DIR/test3_mcts_low.log" \
  --max_runs 1

echo ""
echo "Test 3 complete. Check $LOG_DIR/test3_mcts_low.log for results."
echo "MCTS tree saved to $LOG_DIR/test3_mcts_low_mcts_tree.json"
echo ""
sleep 2

# Test 4: MCTS with Medium reasoning
echo "======================================================================"
echo "Test 4: MCTS-guided exploration (Medium/Medium/Medium, 5 simulations)"
echo "======================================================================"
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
  --solution-reasoning medium \
  --self-improvement-reasoning medium \
  --verification-reasoning medium \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --memory "$LOG_DIR/test4_mcts_medium.json" \
  --log "$LOG_DIR/test4_mcts_medium.log" \
  --max_runs 1

echo ""
echo "Test 4 complete. Check $LOG_DIR/test4_mcts_medium.log for results."
echo "MCTS tree saved to $LOG_DIR/test4_mcts_medium_mcts_tree.json"
echo ""
sleep 2

# Test 5: MCTS + Translation Layer (Combined)
echo "======================================================================"
echo "Test 5: MCTS + Translation (Low gen, High ver, 5 simulations)"
echo "======================================================================"
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
  --solution-reasoning low \
  --self-improvement-reasoning high \
  --verification-reasoning high \
  --use-mcts \
  --use-translation \
  --mcts-simulations 5 \
  --mcts-exploration 1.414 \
  --memory "$LOG_DIR/test5_mcts_translation.json" \
  --log "$LOG_DIR/test5_mcts_translation.log" \
  --max_runs 1

echo ""
echo "Test 5 complete. Check $LOG_DIR/test5_mcts_translation.log for results."
echo "This combines MCTS strategy exploration with translation layer."
echo ""
sleep 2

# Test 6: Higher MCTS exploration (more exploration vs exploitation)
echo "======================================================================"
echo "Test 6: MCTS with higher exploration (exploration=2.0)"
echo "======================================================================"
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
  --solution-reasoning medium \
  --self-improvement-reasoning medium \
  --verification-reasoning medium \
  --use-mcts \
  --mcts-simulations 5 \
  --mcts-exploration 2.0 \
  --memory "$LOG_DIR/test6_mcts_explore.json" \
  --log "$LOG_DIR/test6_mcts_explore.log" \
  --max_runs 1

echo ""
echo "Test 6 complete. Check $LOG_DIR/test6_mcts_explore.log for results."
echo ""

# Summary
echo ""
echo "======================================================================"
echo "TEST SUITE COMPLETE"
echo "======================================================================"
echo ""
echo "Results summary:"
echo "  Test 1 (Baseline BFS):       $LOG_DIR/test1_bfs_low.log"
echo "  Test 2 (Translation):        $LOG_DIR/test2_translation.log"
echo "  Test 3 (MCTS Low):           $LOG_DIR/test3_mcts_low.log"
echo "  Test 4 (MCTS Medium):        $LOG_DIR/test4_mcts_medium.log"
echo "  Test 5 (MCTS+Translation):   $LOG_DIR/test5_mcts_translation.log"
echo "  Test 6 (MCTS High Explore):  $LOG_DIR/test6_mcts_explore.log"
echo ""
echo "To analyze results, look for:"
echo "  - 'Found a correct solution' messages"
echo "  - [MCTS] markers for MCTS exploration process"
echo "  - [TRANSLATION] markers for translation layer activity"
echo "  - Final iteration counts and scores"
echo ""
echo "MCTS trees saved with *_mcts_tree.json suffix"
echo ""
echo "======================================================================"
