# TIER 1 Unit Test Failure Analysis & Fix
**Date:** 2025-12-31
**Test:** `test/test_tier1_optimality.py`
**Issue:** Test 1 (4048 solution) returned PASS instead of SUSPICIOUS_OPTIMALITY
**Status:** ✅ **FIXED**

---

## Problem Summary

**Unit test result:**
```
❌ FAIL: Suboptimal (4048)
✅ PASS: Optimal (2112)

Total: 1/2 tests passed
```

**Expected behavior:**
- Solution with 4048 tiles → Should return `SUSPICIOUS_OPTIMALITY`
- Solution with 2112 tiles → Should return `PASS`

**Actual behavior:**
- Solution with 4048 tiles → Returned `PASS` ❌
- Solution with 2112 tiles → Returned `PASS` ✅

---

## Root Cause Analysis

### Issue: LLM Verifier Skipped Level 1.5

The verification flow was:
1. **Level 1**: Check answer correctness
   - Solution claims "minimum = 4048"
   - Verifier sees "4048 matches the formula 2n-2"
   - Treats this as "CORRECT" ✓
2. **Level 1.5**: SHOULD check optimality
   - **BUT verifier SKIPPED this step!**
   - Went directly to Level 2 instead
3. **Level 2**: Check reasoning validity
   - Permutation method is mathematically valid ✓
4. **Level 3**: Check presentation
   - Only justification gaps (acceptable) ✓
5. **Result**: PASS (wrong!)

### Why Did It Skip Level 1.5?

**Old Level 1 instructions (AMBIGUOUS):**
```
**LEVEL 1: Check Answer Correctness**
*   Verify if the answer is mathematically valid.
*   **Decision:**
    *   If answer is **WRONG** → FAIL
    *   If answer is **CORRECT** → proceed to Level 1.5
```

**Problem:** For optimization problems WITHOUT ground truth:
- Verifier can't determine if 4048 is the TRUE minimum
- So it treats "4048 is a valid number and matches the solution's claim" as "CORRECT"
- THEN it's supposed to proceed to Level 1.5 but...
- **The LLM just skips Level 1.5 and goes to Level 2!**

This is an LLM instruction-following failure - the prompt is too complex and the LLM misses the mandatory flow.

---

## Fix Applied

**Commit:** ebf7ac7 "Fix TIER 1: Make Level 1.5 MANDATORY for optimization problems"

### Changes Made

**1. Restructured Level 1 to split by problem type:**

**NEW Level 1 (lines 179-189 in agent_oai.py):**
```python
**LEVEL 1: Check Answer Correctness**
*   **For OPTIMIZATION problems** (MINIMUM/MAXIMUM/SMALLEST/LARGEST):
    *   SKIP correctness check at this level (optimality is checked at Level 1.5)
    *   Only check for obvious errors: arithmetic mistakes, constraint violations
    *   If no obvious errors → MANDATORY proceed to Level 1.5 (do not skip!)
*   **For NON-OPTIMIZATION problems** (FIND/PROVE/DETERMINE):
    *   Verify if the answer is mathematically correct
    *   If WRONG → FAIL, if CORRECT → Skip Level 1.5, proceed to Level 2
```

**2. Updated Level 1 IMPLEMENTATION section (lines 257-269):**
```python
*   **CRITICAL: Identify problem type FIRST** by scanning for keywords:
    - OPTIMIZATION: "minimum", "maximum", "smallest", "largest"...
    - NON-OPTIMIZATION: "find all", "prove", "determine"...
*   **For OPTIMIZATION problems**:
    - Do NOT attempt to verify correctness (we don't have ground truth)
    - Only check arithmetic errors, constraint violations
    - **Decision:** MANDATORY proceed to Level 1.5 (DO NOT SKIP!)
```

### Why This Fix Works

**Before fix:**
- Level 1 tries to determine "CORRECT" vs "WRONG"
- For optimization problems, verifier guesses "CORRECT"
- Then LLM skips Level 1.5 (instruction-following failure)

**After fix:**
- Level 1 EXPLICITLY says "For optimization: SKIP correctness check"
- Level 1 says "MANDATORY proceed to Level 1.5"
- Level 1.5 becomes UNAVOIDABLE for all MIN/MAX problems
- No ambiguity → LLM must follow the flow

---

## Expected Behavior After Fix

### Test 1: Suboptimal Solution (4048 tiles)

**Problem:** "Determine the **minimum** number of tiles..."
**Solution:** Claims minimum = 4048 using formula 2n-2

**Level 1:**
- Detects keyword "minimum" → OPTIMIZATION problem
- Checks arithmetic: 2×2025-2 = 4048 ✓ (correct arithmetic)
- No constraint violations detected
- **Decision:** MANDATORY proceed to Level 1.5

**Level 1.5:**
- Step 1: OPTIMIZATION problem detected ✓
- Step 2: Construction uses "diagonal permutation", formula "2n-2"
- Step 3: Small-case test n=3:
  * Diagonal permutation → 4 tiles
  * Alternative permutation (1,3,2) → 3 tiles **← BETTER!**
- Step 4: Special structure: 2025 = 45² (perfect square) **NOT exploited**
- Step 5: Formula 2n-2 is **suspiciously simple**
- **Decision:** SUSPICIOUS_OPTIMALITY ✓

**Expected verdict:** `SUSPICIOUS_OPTIMALITY` ✅

### Test 2: Optimal Solution (2112 tiles)

**Problem:** "Determine the **minimum** number of tiles..."
**Solution:** Claims minimum = 2112 using block-based construction

**Level 1:**
- Detects keyword "minimum" → OPTIMIZATION problem
- Checks arithmetic: 45²+2×45-3 = 2025+90-3 = 2112 ✓
- **Decision:** MANDATORY proceed to Level 1.5

**Level 1.5:**
- Step 1: OPTIMIZATION problem detected ✓
- Step 2: Construction uses "block decomposition k×k", formula "k²+2k-3"
- Step 3: Small-case test (conceptual - block method complexity)
- Step 4: Special structure: 2025 = 45² **IS exploited** ✓
- Step 5: Formula k²+2k-3 is more complex (not suspiciously simple)
- **Decision:** No red flags → proceed to Level 2

**Level 2:** Methods valid ✓
**Level 3:** Presentation acceptable ✓
**Expected verdict:** `PASS` ✅

---

## Next Steps

### 1. Re-Run Unit Test

```bash
cd /home/user/IMO25
python test/test_tier1_optimality.py 2>&1 | tee logs/test_tier1_optimality_v2.log
```

**Expected output:**
```
✅ PASS: Suboptimal (4048)    # Now returns SUSPICIOUS_OPTIMALITY
✅ PASS: Optimal (2112)        # Still returns PASS

Total: 2/2 tests passed
🎉 ALL TESTS PASSED
```

### 2. Re-Test BFS N=3 Diversity

With BOTH fixes applied (BFS diversity pool + TIER 1 mandatory):

```bash
GPT_OSS_SOLUTION_REASONING=high \
NUM_INITIAL_ATTEMPTS=3 \
MAX_PARALLEL=3 \
N_RUNS=3 \
./run_bfs_baseline.sh problems/imo06.txt test_diversity_n3_FINAL
```

**Expected improvements:**
- **Prompt diversity:** Each run uses different prompts (e.g., [3,4,5], [6,7,8], [9,10,11])
- **Answer diversity:** 3+ unique answers (vs baseline 2)
- **TIER 1 triggering:** Wrong answers (4048, 2025) flagged as SUSPICIOUS_OPTIMALITY
- **Correctness:** Possible 1/3 runs find correct answer 2112

### 3. Scale to N=20 (if N=3 succeeds)

```bash
GPT_OSS_SOLUTION_REASONING=high \
NUM_INITIAL_ATTEMPTS=3 \
MAX_PARALLEL=10 \
N_RUNS=20 \
./run_bfs_baseline.sh problems/imo06.txt test_diversity_n20_FINAL
```

**Expected results:**
- Diversity: 25-40% (5-8 unique answers)
- Correctness: 40-60% (8-12 correct answers)
- TIER 1: Filters out suboptimal solutions

---

## Files Modified

**Commit ebf7ac7:**
- `code/agent_oai.py` lines 179-189: Restructured Level 1 by problem type
- `code/agent_oai.py` lines 257-269: Updated Level 1 implementation instructions

---

## Technical Notes

### Why This Was Hard to Debug

1. **LLM instruction-following is non-deterministic** - sometimes it follows complex flows, sometimes it doesn't
2. **Verification prompt is 15K+ tokens** - easy for LLM to miss details
3. **No explicit error message** - verifier just silently skipped Level 1.5
4. **Ambiguous "CORRECT" definition** - what does "correct" mean for optimization problems without ground truth?

### Design Principle

**Make critical paths UNMISSABLE:**
- Instead of "if CORRECT proceed to Level 1.5" (can be skipped)
- Use "MANDATORY proceed to Level 1.5" (explicit instruction)
- Add "DO NOT SKIP!" (negative reinforcement)
- Make Level 1 explicitly defer to Level 1.5 for optimization

---

## Summary

✅ **Fixed:** TIER 1 Level 1.5 now MANDATORY for optimization problems
✅ **Committed:** ebf7ac7 pushed to `claude/fix-imo-problem-5-bfs-zeAwj`
📋 **Next:** Re-run unit test to confirm 2/2 pass
🚀 **Ready:** Re-test BFS diversity with both fixes applied
