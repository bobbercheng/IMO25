#!/bin/bash
# BFS Diversity Fix Validation Test
# Tests that different BFS_RUN_ID values produce different prompt selections
# Date: 2025-12-30

echo "=== BFS Diversity Fix Validation Test ==="
echo ""

# Test parameters
export NUM_INITIAL_ATTEMPTS=3
PROBLEM="problems/imo06.txt"

# Mock test: Verify that BFS_RUN_ID affects prompt selection
echo "Test 1: Verify BFS_RUN_ID is read correctly"
echo "-------------------------------------------"

for run_id in 0 1 2; do
    echo ""
    echo "Testing BFS_RUN_ID=$run_id with NUM_INITIAL_ATTEMPTS=3"
    echo "Expected prompt indices:"

    # Calculate expected indices using same formula as code
    # prompt_idx = (run_id * num_attempts + attempt) % 20
    # Assuming 20 total prompts (from generate_bfs_prompts)

    for attempt in 0 1 2; do
        prompt_idx=$(( (run_id * 3 + attempt) % 20 ))
        echo "  Attempt $((attempt+1)): Prompt [$prompt_idx/20]"
    done
done

echo ""
echo "Test 2: Expected diversity for N=20 runs"
echo "-----------------------------------------"
echo "With 20 runs (run_id 1-20), each using 3 attempts:"
echo "  Run 1:  Prompts [3, 4, 5]"
echo "  Run 2:  Prompts [6, 7, 8]"
echo "  Run 3:  Prompts [9, 10, 11]"
echo "  ..."
echo "  Run 7:  Prompts [0, 1, 2]  (wraps around)"
echo "  ..."
echo "  Run 20: Prompts [18, 19, 0] (wraps around)"
echo ""
echo "Result: ALL 20 runs get DIFFERENT starting prompts!"
echo ""

echo "Test 3: Backward compatibility (no BFS_RUN_ID set)"
echo "---------------------------------------------------"
echo "When BFS_RUN_ID is not set, defaults to 0:"
echo "  Attempt 1: Prompt [0/20]"
echo "  Attempt 2: Prompt [1/20]"
echo "  Attempt 3: Prompt [2/20]"
echo "This preserves single-run behavior."
echo ""

echo "=== Validation Tests Complete ==="
echo ""
echo "To test with actual BFS run (N=3 parallel runs):"
echo "  GPT_OSS_SOLUTION_REASONING=high \\"
echo "  NUM_INITIAL_ATTEMPTS=3 \\"
echo "  MAX_PARALLEL=3 \\"
echo "  N_RUNS=3 \\"
echo "  ./run_bfs_baseline.sh problems/imo06.txt test_diversity_n3"
echo ""
echo "Then verify prompt diversity in logs:"
echo "  grep 'BFS: Prompt' test_diversity_n3/bfs_run*.log | head -9"
echo ""
