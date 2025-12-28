#!/bin/bash
# P0 Ablation Quick Test Script
# Runs a fast ablation test with reduced rounds for validation
# Usage: ./test_p0_ablation_quick.sh <problem_file>

set -e

PROBLEM_FILE="${1:-problems/imo01.txt}"
MAX_ROUNDS=3  # Quick test with only 3 rounds

echo "========================================="
echo "P0 ABLATION QUICK TEST"
echo "========================================="
echo "Running ablation test with ${MAX_ROUNDS} rounds"
echo "This is a QUICK test for validation only"
echo ""

./test_p0_ablation.sh "${PROBLEM_FILE}" ${MAX_ROUNDS}
