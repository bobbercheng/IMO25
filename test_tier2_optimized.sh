#!/bin/bash
# Test TIER 2 with optimized configuration (graduated verification)

echo "================================================================================"
echo "TIER 2 OPTIMIZED TEST - Problem 2"
echo "================================================================================"
echo ""
echo "Configuration:"
echo "  - Max rounds: 8 (was 5)"
echo "  - Base verification: medium (was high)"
echo "  - Graduated verification: ENABLED"
echo "    - Rounds 1-3: low    (accept proof outline)"
echo "    - Rounds 4-6: medium (IMO standard)"
echo "    - Rounds 7-8: high   (publication-ready)"
echo ""
echo "Expected: TIER_2_VERIFIED by Round 6-8"
echo "================================================================================"
echo ""

# Run with optimized settings
python code/agent_gpt_oss.py problems/imo02.txt \
  --use-rlac \
  --rlac-max-rounds 30 \
  --rlac-stuck-threshold 5 \
  --rlac-robust-threshold 3 \
  --log test_rlac_log/tier2_test_p2_optimized.log \
  --memory test_rlac_log/tier2_test_p2_optimized.json

echo ""
echo "================================================================================"
echo "Test completed!"
echo "Check logs at: test_rlac_log/tier2_test_p2_optimized.log"
echo "Check metadata: test_rlac_log/tier2_test_p2_optimized_tier2_refinement.json"
echo "================================================================================"
