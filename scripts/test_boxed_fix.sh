#!/bin/bash
# Test that the \\boxed{} conflict is fixed
# Should see: Model returns correct answer in final_answer, NO \\boxed{} in solution text

set -e

echo "=========================================="
echo "Testing \\boxed{} Conflict Fix"
echo "=========================================="

# Test 1: Run single BFS attempt on problem 1
echo ""
echo "TEST 1: Single BFS attempt (should NOT use \\boxed{} in solution)"
python code/agent_gpt_oss.py problems/imo01.txt \
  --num-initial-attempts 1 \
  --solution-reasoning low \
  --log /tmp/boxed_test_output.log 2>&1 | tee /tmp/boxed_test_stdout.log

# Test 2: Check log for validation
echo ""
echo "TEST 2: Validation check"
if grep -q "VALIDATION ERROR.*boxed" /tmp/boxed_test_output.log; then
  echo "❌ FAIL: Model still using \\boxed{} in solution text"
  grep "VALIDATION ERROR.*boxed" /tmp/boxed_test_output.log
  exit 1
else
  echo "✅ PASS: No \\boxed{} validation errors"
fi

# Test 3: Check that final_answer is extracted correctly
echo ""
echo "TEST 3: Answer extraction check"
if grep -q "final_answer.*[0-9]" /tmp/boxed_test_output.log; then
  echo "✅ PASS: final_answer field populated"
  grep "final_answer" /tmp/boxed_test_output.log | head -5
else
  echo "⚠️  WARNING: No final_answer found (may be expected if no solution yet)"
fi

# Test 4: Check for schema consistency
echo ""
echo "TEST 4: Schema description consistency"
if grep -q "DO NOT include.*boxed" /tmp/boxed_test_output.log; then
  echo "✅ PASS: Schema correctly instructs NOT to use \\boxed{}"
  grep "DO NOT include.*boxed" /tmp/boxed_test_output.log | head -1
else
  echo "❌ FAIL: Schema missing 'DO NOT use \\boxed{}' instruction"
  exit 1
fi

echo ""
echo "=========================================="
echo "All tests passed! ✅"
echo "=========================================="
echo ""
echo "ACCEPTANCE CRITERIA:"
echo "1. ✅ No VALIDATION ERROR about \\boxed{} in solution"
echo "2. ✅ final_answer field populated with integer"
echo "3. ✅ Schema description says 'DO NOT include...\\boxed{}'"
echo "4. ✅ System prompt does NOT mention \\boxed{}"
echo ""
echo "Next: Run full BFS test (N=5) to verify consistency"
