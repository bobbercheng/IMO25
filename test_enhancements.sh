#!/bin/bash

# Test script for three major enhancements:
# 1. Optimized MCTS (8 sims, depth 3, hybrid strategies, exploration 1.6)
# 2. Best-of-N sampling
# 3. Proof Sketch Phase architecture

echo "========================================================================"
echo "Testing Three Major Enhancements for GPT-OSS Agent"
echo "========================================================================"
echo ""

PROBLEM_FILE="problems/imo_p1.txt"
LOG_DIR="test_enhancements_logs"

# Create log directory
mkdir -p "$LOG_DIR"

echo "Using problem file: $PROBLEM_FILE"
echo "Log directory: $LOG_DIR"
echo ""

# Test 1: Optimized MCTS with default settings (8 sims, depth 3, exploration 1.6)
echo "========================================================================"
echo "Test 1: Optimized MCTS (8 simulations, depth 3, exploration 1.6)"
echo "========================================================================"
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
    --use-mcts \
    --solution-reasoning low \
    --self-improvement-reasoning low \
    --verification-reasoning low \
    --log "$LOG_DIR/test1_optimized_mcts.log" \
    --memory "$LOG_DIR/test1_memory.json"

echo ""
echo "Test 1 complete. Log: $LOG_DIR/test1_optimized_mcts.log"
echo ""

# Test 2: MCTS with Best-of-N sampling (N=3)
echo "========================================================================"
echo "Test 2: MCTS + Best-of-N Sampling (N=3)"
echo "========================================================================"
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
    --use-mcts \
    --best-of-n 3 \
    --solution-reasoning low \
    --self-improvement-reasoning low \
    --verification-reasoning high \
    --log "$LOG_DIR/test2_best_of_n.log" \
    --memory "$LOG_DIR/test2_memory.json"

echo ""
echo "Test 2 complete. Log: $LOG_DIR/test2_best_of_n.log"
echo ""

# Test 3: Proof Sketch Phase architecture
echo "========================================================================"
echo "Test 3: Proof Sketch Phase Architecture"
echo "========================================================================"
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
    --use-proof-sketch \
    --solution-reasoning low \
    --verification-reasoning high \
    --log "$LOG_DIR/test3_proof_sketch.log" \
    --memory "$LOG_DIR/test3_memory.json"

echo ""
echo "Test 3 complete. Log: $LOG_DIR/test3_proof_sketch.log"
echo ""

# Test 4: Combined - MCTS + Best-of-N (optimal configuration)
echo "========================================================================"
echo "Test 4: MCTS + Best-of-N (Optimal Configuration)"
echo "========================================================================"
python code/agent_gpt_oss.py "$PROBLEM_FILE" \
    --use-mcts \
    --mcts-simulations 10 \
    --best-of-n 5 \
    --solution-reasoning low \
    --self-improvement-reasoning low \
    --verification-reasoning high \
    --log "$LOG_DIR/test4_combined.log" \
    --memory "$LOG_DIR/test4_memory.json"

echo ""
echo "Test 4 complete. Log: $LOG_DIR/test4_combined.log"
echo ""

# Summary
echo "========================================================================"
echo "All Tests Complete!"
echo "========================================================================"
echo ""
echo "Results:"
echo "  Test 1: $LOG_DIR/test1_optimized_mcts.log"
echo "  Test 2: $LOG_DIR/test2_best_of_n.log"
echo "  Test 3: $LOG_DIR/test3_proof_sketch.log"
echo "  Test 4: $LOG_DIR/test4_combined.log"
echo ""
echo "Check for 'Found a correct solution' in logs to see which tests succeeded"
echo ""
echo "MCTS trees saved as:"
echo "  $LOG_DIR/test1_memory_mcts_tree.json"
echo "  $LOG_DIR/test2_memory_mcts_tree.json"
echo "  $LOG_DIR/test4_memory_mcts_tree.json"
echo ""
