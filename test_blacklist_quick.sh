#!/bin/bash
# Quick validation test for solution blacklist implementation
# Tests with N=3 runs to verify blacklist diversity mechanism

set -e

echo "================================================================"
echo "BLACKLIST IMPLEMENTATION - QUICK VALIDATION TEST"
echo "================================================================"
echo ""

# Configuration
PROBLEM_FILE="problems/imo06.txt"
TEST_DIR="test_blacklist_quick"
NUM_RUNS=3

# Clean slate
echo "Step 1: Clean slate"
echo "-------------------"
rm -rf blacklists/imo06_blacklist.json
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
echo "✓ Removed old blacklist and test directory"
echo ""

# Run BFS baseline with N=3
echo "Step 2: Run BFS baseline (N=$NUM_RUNS)"
echo "---------------------------------------"
echo "This will take ~10-15 minutes..."
echo ""

GPT_OSS_SOLUTION_REASONING=high \
NUM_INITIAL_ATTEMPTS=5 \
N_RUNS=$NUM_RUNS \
./run_bfs_baseline.sh "$PROBLEM_FILE" "$TEST_DIR"

echo ""
echo "Step 3: Analyze results"
echo "------------------------"

# Check if blacklist was created
if [ -f "blacklists/imo06_blacklist.json" ]; then
    echo "✓ Blacklist file created: blacklists/imo06_blacklist.json"
    echo ""
    echo "Blacklist contents:"
    cat blacklists/imo06_blacklist.json | python3 -m json.tool
    echo ""
else
    echo "✗ Blacklist file NOT created - INTEGRATION FAILED"
    exit 1
fi

# Count unique answers
echo "Unique answers found:"
grep -rh "\\\\boxed{" "$TEST_DIR"/*.log 2>/dev/null | \
    grep -o "\\\\boxed{[^}]*}" | \
    sort | uniq -c | sort -rn
echo ""

# Check for optimal solution (2112)
if grep -r "2112" "$TEST_DIR"/*.log > /dev/null 2>&1; then
    echo "✓ SUCCESS: Found optimal solution (2112) in at least one run!"
    echo ""
    echo "Runs that found 2112:"
    grep -l "2112" "$TEST_DIR"/*.log
else
    echo "⚠ WARNING: No run found optimal solution (2112)"
    echo "   This may still be acceptable if blacklist shows diversity"
fi
echo ""

# Check for diversity
echo "Diversity check:"
echo "----------------"
if [ -f "blacklists/imo06_blacklist.json" ]; then
    UNIQUE_ANSWERS=$(python3 -c "
import json
with open('blacklists/imo06_blacklist.json') as f:
    data = json.load(f)
    print(len(set(s['answer'] for s in data['solutions'])))
")

    echo "Unique answers in blacklist: $UNIQUE_ANSWERS of $NUM_RUNS runs"

    if [ "$UNIQUE_ANSWERS" -ge 2 ]; then
        echo "✓ DIVERSITY ACHIEVED: At least 2 different approaches tried"
    else
        echo "✗ DIVERSITY FAILED: All runs tried same approach"
        echo "   Blacklist may not be working correctly"
    fi
fi
echo ""

# Summary
echo "================================================================"
echo "TEST SUMMARY"
echo "================================================================"
echo ""
echo "Expected results:"
echo "  ✓ Blacklist file created with $NUM_RUNS entries"
echo "  ✓ At least 2 different answers attempted"
echo "  ✓ (Optimistic) At least 1 run finds 2112"
echo ""
echo "Baseline comparison:"
echo "  Before fix: 0/12 success, all tried 4048"
echo "  After fix: Should see diversity + potential success"
echo ""
echo "Next steps:"
echo "  - If test passes → Run full N=12 validation"
echo "  - If test fails → Debug blacklist integration"
echo ""
echo "Test directory: $TEST_DIR/"
echo "Blacklist file: blacklists/imo06_blacklist.json"
echo ""
