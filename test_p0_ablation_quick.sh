#!/bin/bash
# P0 Ablation Quick Test Script
# Runs a fast ablation test with reduced runs for validation
# Usage: ./test_p0_ablation_quick.sh <problem_file>

set -e

PROBLEM_FILE="${1:-problems/imo01.txt}"
NUM_RUNS=3  # Quick test with only 3 BFS runs per config

echo "========================================="
echo "P0 ABLATION QUICK TEST (BFS)"
echo "========================================="
echo "Running ablation test with ${NUM_RUNS} runs per config"
echo "This is a QUICK test for validation only"
echo "Each config will run ${NUM_RUNS} BFS iterations"
echo ""

./test_p0_ablation.sh "${PROBLEM_FILE}" ${NUM_RUNS}
