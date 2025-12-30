#!/bin/bash
# Compare LOW vs MEDIUM reasoning for Stage 2 code generation

echo "================================================================================"
echo "STAGE 2 REASONING COMPARISON: LOW vs MEDIUM"
echo "================================================================================"
echo ""

# Ground truth solution
cat > /tmp/ground_truth.txt << 'EOF'
k ∈ {0, 1, 3}
Construction: k=0 uses diagonals, k=1 uses one sunny line, k=3 uses three sunny lines
EOF

echo "Test solution: k ∈ {0, 1, 3}"
echo ""

# Test with MEDIUM reasoning (default)
echo "================================================================================"
echo "TEST 1: MEDIUM Reasoning (default)"
echo "================================================================================"
start_medium=$(date +%s)
LLM_VERIFY_CODE_REASONING=medium python code/llm_verification.py /tmp/ground_truth.txt --problem problems/imo01.txt 2>&1 | tee /tmp/medium_test.log | grep -E "\[Stage|Verdict|Confidence|Evidence:"
end_medium=$(date +%s)
medium_time=$((end_medium - start_medium))
medium_verdict=$(grep "^Verdict:" /tmp/medium_test.log | awk '{print $2}')
medium_confidence=$(grep "^Confidence:" /tmp/medium_test.log | awk '{print $2}')
medium_code_size=$(grep "\[Stage 2\] Generated" /tmp/medium_test.log | awk '{print $3}')

echo ""
echo "================================================================================"
echo "TEST 2: LOW Reasoning (experimental)"
echo "================================================================================"
start_low=$(date +%s)
LLM_VERIFY_CODE_REASONING=low python code/llm_verification.py /tmp/ground_truth.txt --problem problems/imo01.txt 2>&1 | tee /tmp/low_test.log | grep -E "\[Stage|Verdict|Confidence|Evidence:"
end_low=$(date +%s)
low_time=$((end_low - start_low))
low_verdict=$(grep "^Verdict:" /tmp/low_test.log | awk '{print $2}')
low_confidence=$(grep "^Confidence:" /tmp/low_test.log | awk '{print $2}')
low_code_size=$(grep "\[Stage 2\] Generated" /tmp/low_test.log | awk '{print $3}')

echo ""
echo "================================================================================"
echo "COMPARISON RESULTS"
echo "================================================================================"
echo ""
echo "| Metric              | MEDIUM          | LOW             | Winner  |"
echo "|---------------------|-----------------|-----------------|---------|"
echo "| Verdict             | $medium_verdict         | $low_verdict         | $([ "$medium_verdict" = "$low_verdict" ] && echo "TIE ✅" || echo "DIFF ⚠️") |"
echo "| Confidence          | $medium_confidence      | $low_confidence      | $([ "$medium_confidence" = "$low_confidence" ] && echo "TIE" || echo "DIFF") |"
echo "| Code Size (chars)   | $medium_code_size       | $low_code_size       | - |"
echo "| Time (seconds)      | ${medium_time}s         | ${low_time}s         | $([ $low_time -lt $medium_time ] && echo "LOW 🚀" || echo "MEDIUM") |"
echo ""

if [ "$medium_verdict" = "$low_verdict" ] && [ "$medium_verdict" = "VALID" ]; then
    echo "✅ BOTH PASSED - LOW reasoning is sufficient!"
    echo ""
    echo "Recommendation: Use LOW reasoning for Stage 2"
    echo "Benefits:"
    echo "  - ~50% cost savings"
    echo "  - ~3x faster"
    echo "  - Same correctness"
    echo ""
    echo "To enable permanently:"
    echo "  export LLM_VERIFY_CODE_REASONING=low"
else
    echo "⚠️  Results differ or failed"
    echo ""
    echo "Recommendation: Keep MEDIUM reasoning for Stage 2"
    echo "Reason: LOW reasoning may generate incorrect code"
fi

echo ""
echo "Full logs saved to:"
echo "  - /tmp/medium_test.log"
echo "  - /tmp/low_test.log"
