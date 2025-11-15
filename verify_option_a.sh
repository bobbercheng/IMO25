#!/bin/bash
# Verification script for Option A changes

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║         Verifying Option A Changes to agent_gpt_oss.py           ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

SUCCESS=0
FAIL=0

# Check 1: Reasoning effort changed to "low"
echo "✓ Checking REASONING_EFFORT..."
if grep -q 'REASONING_EFFORT = os.getenv("GPT_OSS_REASONING_EFFORT", "low")' code/agent_gpt_oss.py; then
    echo "  ✅ PASS: reasoning_effort is set to 'low'"
    SUCCESS=$((SUCCESS + 1))
else
    echo "  ❌ FAIL: reasoning_effort is NOT set to 'low'"
    echo "  Current value:"
    grep "REASONING_EFFORT.*=" code/agent_gpt_oss.py
    FAIL=$((FAIL + 1))
fi
echo ""

# Check 2: Repetition penalty removed
echo "✓ Checking repetition_penalty removed..."
if grep -q '"repetition_penalty"' code/agent_gpt_oss.py; then
    echo "  ❌ FAIL: repetition_penalty still present in code"
    echo "  Found:"
    grep -n "repetition_penalty" code/agent_gpt_oss.py
    FAIL=$((FAIL + 1))
else
    echo "  ✅ PASS: repetition_penalty removed from code"
    SUCCESS=$((SUCCESS + 1))
fi
echo ""

# Check 3: Comment about removal exists
echo "✓ Checking explanatory comments..."
if grep -q "Option A improvement" code/agent_gpt_oss.py; then
    echo "  ✅ PASS: Explanatory comments present"
    SUCCESS=$((SUCCESS + 1))
else
    echo "  ⚠️  WARNING: Explanatory comments not found (optional)"
fi
echo ""

# Summary
echo "═══════════════════════════════════════════════════════════════════"
echo "VERIFICATION SUMMARY:"
echo "  ✅ Passed: $SUCCESS"
echo "  ❌ Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "🎉 SUCCESS! All Option A changes verified."
    echo ""
    echo "Ready to test! Run:"
    echo "  cd code"
    echo "  python agent_gpt_oss.py ../problems/imo01.txt --log ../test.log"
    echo ""
    exit 0
else
    echo "❌ VERIFICATION FAILED!"
    echo ""
    echo "Please check the changes manually or re-apply:"
    echo "  1. Set REASONING_EFFORT to 'low' (line ~49)"
    echo "  2. Remove repetition_penalty line (line ~150)"
    echo ""
    exit 1
fi
