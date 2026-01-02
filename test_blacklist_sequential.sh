#!/bin/bash
# Quick test: Does blacklist work in SEQUENTIAL mode?
# Tests N=3 runs one-at-a-time to verify state sharing

set -e

echo "========================================================================"
echo "BLACKLIST SEQUENTIAL TEST - Does it actually run?"
echo "========================================================================"
echo ""
echo "Goal: Verify blacklist works when runs execute sequentially"
echo "Expected: Run 2 logs 'Loaded 1 blacklisted solution from run1'"
echo "Expected: Run 3 logs 'Loaded 2 blacklisted solutions'"
echo ""

# Configuration
PROBLEM_FILE="problems/imo06.txt"
TEST_DIR="test_blacklist_sequential"
NUM_RUNS=3

# Clean slate
echo "Step 1: Clean slate"
echo "-------------------"
rm -rf blacklists/imo06_blacklist.json
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
echo "✓ Removed old blacklist and test directory"
echo ""

# Run sequentially (MAX_PARALLEL=1)
echo "Step 2: Run N=$NUM_RUNS sequentially (MAX_PARALLEL=1)"
echo "--------------------------------------------------------"
echo "This will take ~15-20 minutes..."
echo ""

GPT_OSS_SOLUTION_REASONING=high \
NUM_INITIAL_ATTEMPTS=5 \
N_RUNS=$NUM_RUNS \
MAX_PARALLEL=1 \
./run_bfs_baseline.sh "$PROBLEM_FILE" "$TEST_DIR"

echo ""
echo "Step 3: Check blacklist logs"
echo "----------------------------"

# Check if blacklist was loaded in runs 2 and 3
echo ""
echo "Checking for blacklist load messages:"
echo ""

for i in {1..3}; do
    echo "Run $i:"
    grep -i "blacklist\|FORBIDDEN\|already explored" "$TEST_DIR"/*.log 2>/dev/null | head -5 || echo "  (no blacklist logs found)"
    echo ""
done

# Analyze blacklist file
if [ -f "blacklists/imo06_blacklist.json" ]; then
    echo "✓ Blacklist file exists: blacklists/imo06_blacklist.json"
    echo ""
    echo "Blacklist contents:"
    cat blacklists/imo06_blacklist.json | python3 -m json.tool
    echo ""

    # Count unique answers
    UNIQUE_ANSWERS=$(python3 -c "
import json
with open('blacklists/imo06_blacklist.json') as f:
    data = json.load(f)
    print(len(set(s['answer'] for s in data['solutions'])))
")

    echo "Unique answers in blacklist: $UNIQUE_ANSWERS of $NUM_RUNS runs"
else
    echo "✗ Blacklist file NOT created"
fi

echo ""
echo "Step 4: Analysis"
echo "----------------"
echo ""

# Check if any run found 2112
if grep -r "2112" "$TEST_DIR"/*.log > /dev/null 2>&1; then
    echo "✓ SUCCESS: At least one run found optimal answer (2112)!"
    echo ""
    echo "Runs that found 2112:"
    grep -l "2112" "$TEST_DIR"/*.log
else
    echo "✗ No run found optimal answer (2112)"
fi

echo ""

# Check for diversity
if grep -rh "\\\\boxed{" "$TEST_DIR"/*.log 2>/dev/null | \
    grep -o "\\\\boxed{[^}]*}" | \
    sort | uniq | wc -l | grep -q "[2-9]"; then
    echo "✓ DIVERSITY: Multiple different answers attempted"
else
    echo "✗ NO DIVERSITY: All runs tried same answer"
fi

echo ""
echo "========================================================================"
echo "CRITICAL CHECKS"
echo "========================================================================"
echo ""

# Check 1: Did blacklist actually run?
if grep -r "FORBIDDEN\|already explored\|blacklisted" "$TEST_DIR"/*.log > /dev/null 2>&1; then
    echo "✓ CHECK 1 PASS: Blacklist prompts appeared in logs"
    echo "   This means blacklist integration is working!"
else
    echo "✗ CHECK 1 FAIL: No blacklist prompts found in logs"
    echo "   This means blacklist never ran despite being created"
    echo "   Possible causes:"
    echo "   - Blacklist loading happens but prompts not injected"
    echo "   - Parallel execution race condition (even with MAX_PARALLEL=1)"
    echo "   - Integration bug in agent code"
fi

echo ""

# Check 2: Did runs see previous solutions?
RUN2_SAW_RUN1=$(grep -l "FORBIDDEN.*run1\|already explored.*run1" "$TEST_DIR"/*run2*.log 2>/dev/null | wc -l)
RUN3_SAW_RUN2=$(grep -l "FORBIDDEN.*run2\|already explored.*run2" "$TEST_DIR"/*run3*.log 2>/dev/null | wc -l)

if [ "$RUN2_SAW_RUN1" -gt 0 ]; then
    echo "✓ CHECK 2a PASS: Run 2 saw Run 1's solution"
else
    echo "✗ CHECK 2a FAIL: Run 2 did NOT see Run 1's solution"
fi

if [ "$RUN3_SAW_RUN2" -gt 0 ]; then
    echo "✓ CHECK 2b PASS: Run 3 saw Run 2's solution"
else
    echo "✗ CHECK 2b FAIL: Run 3 did NOT see Run 2's solution"
fi

echo ""

# Check 3: Answer extraction quality
if [ -f "blacklists/imo06_blacklist.json" ]; then
    GARBAGE_ANSWERS=$(python3 -c "
import json
import re
with open('blacklists/imo06_blacklist.json') as f:
    data = json.load(f)
    # Count answers that look like LaTeX fragments (contain \\\\)
    garbage = sum(1 for s in data['solutions'] if '\\\\' in s['answer'] or 'n =' in s['answer'])
    print(garbage)
")

    if [ "$GARBAGE_ANSWERS" -gt 0 ]; then
        echo "✗ CHECK 3 FAIL: $GARBAGE_ANSWERS/$NUM_RUNS answers are garbage"
        echo "   Answer extraction bug confirmed (regex missing \\boxed{} pattern)"
    else
        echo "✓ CHECK 3 PASS: All answers extracted cleanly"
    fi
fi

echo ""
echo "========================================================================"
echo "SUMMARY"
echo "========================================================================"
echo ""
echo "Test directory: $TEST_DIR/"
echo "Blacklist file: blacklists/imo06_blacklist.json"
echo ""
echo "Next steps based on results:"
echo ""
echo "IF CHECK 1 PASS (blacklist prompts appeared):"
echo "  → Blacklist works! Fix answer extraction (add \\boxed{} pattern)"
echo "  → Then run N=12 test to see if diversity improves"
echo ""
echo "IF CHECK 1 FAIL (no blacklist prompts):"
echo "  → Blacklist integration broken despite unit tests passing"
echo "  → Debug: Why does blacklist not inject prompts?"
echo "  → May need to check init_explorations() in agent code"
echo ""
echo "IF CHECK 3 FAIL (garbage answers):"
echo "  → Fix answer extraction FIRST (30 min, \$0)"
echo "  → Then re-test blacklist effectiveness"
echo ""
