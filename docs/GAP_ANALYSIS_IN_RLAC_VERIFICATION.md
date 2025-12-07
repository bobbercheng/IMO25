# Gap Analysis: In-RLAC Verification Expectations vs Reality

**Date:** 2025-12-07
**Test:** `inline_verification_test_20251207_104731`
**Problem:** problems/imo01.txt (FIND problem)

---

## Critical Discovery: Verification Worked But Returned Wrong Verdicts

### Expected Behavior

From our implementation in `code/adversarial_critic.py` (lines 169-177):

```python
if "critical error" in bug_report_lower:
    verdict = "BROKEN"          # ← Expected for critical errors
    severity = "CRITICAL"
    penalty = 100
```

### Actual Behavior

From test logs - ALL verification-based attacks returned **SUSPICIOUS** instead of **BROKEN**:

```json
{
  "verdict": "SUSPICIOUS",      // ← Should have been BROKEN!
  "critical_flaws": [
    "**Final Verdict:** ... contains **Critical Errors** ..."
  ],
  "verification_used": true
}
```

---

## The Bug: Case-Sensitive String Matching

### Root Cause

**Location:** `code/adversarial_critic.py` line 170

```python
if "critical error" in bug_report_lower:  # ← Checks for lowercase
```

**But verification output uses:**
```
"**Final Verdict:** ... contains **Critical Errors** ..."
          ^                              ^
    Markdown bold                  Plural form!
```

**After `.lower()`:**
```
"... contains **critical errors** ..."
```

### The Mismatch

Our code checks for: `"critical error"` (singular)
Verification returns: `"critical errors"` (plural) or `"a critical error"`

**Result:** String match FAILS → Falls through to else clause → Returns SUSPICIOUS

---

## Evidence from Logs

### Round 0 Verification Output:

```
[VERIFICATION-BASED ATTACK]

**Final Verdict:** The solution is **invalid** because it contains
**Critical Errors** that break the logical chain
                ^^^^^^^^^^^^^^
```

### Our Code's Check:

```python
bug_report_lower = bug_report.lower()
# bug_report_lower contains: "... contains **critical errors** ..."

if "critical error" in bug_report_lower:  # FALSE! (singular vs plural)
    verdict = "BROKEN"
elif "justification gap" in bug_report_lower or "gap" in bug_report_lower:
    verdict = "SUSPICIOUS"  # ← Falls through here
```

### Result:

All 5 verification-based attacks (rounds 0, 2, 4, 6, 8) returned SUSPICIOUS instead of BROKEN.

---

## Impact Analysis

### Impact #1: Weaker Feedback Signal

**Expected:**
- Critical Error → BROKEN verdict → Generator treats as severe failure
- Generator immediately revises approach

**Actual:**
- Critical Error → SUSPICIOUS verdict → Generator treats as moderate concern
- Generator makes incremental changes instead of major revision

**Evidence:**
From Round 0 to Round 5 progression:
- Round 0: SUSPICIOUS (should have been BROKEN)
- Round 1: SUSPICIOUS (prompt-based)
- Round 2: SUSPICIOUS (verification, should have been BROKEN)
- Round 3: (not in history)
- Round 4: SUSPICIOUS (verification, should have been BROKEN)
- Round 5: ROBUST (first success after 5 rounds!)

**If verification had returned BROKEN:** Generator might have fixed errors in 2-3 rounds instead of 5.

---

### Impact #2: Still Achieved Correct Answer

**Despite the bug:**
- ✅ In-RLAC verification DID run (5 times)
- ✅ Critical errors WERE caught and reported
- ✅ Generator eventually found correct answer: `k ∈ {0,1,...,⌊(n-1)/2⌋}`
- ✅ Final status: TIER_1_ONLY (answer correct)

**The bug slowed convergence but didn't prevent success.**

---

### Impact #3: SymPy Missing Dependency

**Secondary issue found:**

```
[SEMANTIC CHECK] SymPy failed: No module named 'sympy'
```

**Impact:**
- Semantic equivalence checking falls back to pattern matching
- Pattern matching works for this problem (no false rejections)
- But could cause issues with complex mathematical expressions

**Location:** `code/tier2_refinement.py` line 1053

**Status:** Non-critical (fallback works), but should install SymPy

---

## Comparison: Expected vs Actual Timeline

### Expected Timeline (with correct verdict mapping):

```
Round 0: Verification finds Critical Error → BROKEN
         Generator: "My construction is fundamentally wrong, revise completely"
Round 1: Major revision with new approach
Round 2: Verification checks new approach → Minor gaps → SUSPICIOUS or ROBUST
Round 3-4: Refinement based on feedback → ROBUST × 3 → SUCCESS
```

**Expected total:** 4-5 rounds

### Actual Timeline (with bug):

```
Round 0: Verification finds Critical Error → SUSPICIOUS (bug!)
         Generator: "Some issues, let me refine"
Round 1: Prompt-based attack → SUSPICIOUS
         Generator: "Still issues, incremental fix"
Round 2: Verification finds Critical Error → SUSPICIOUS (bug!)
         Generator: "Hmm, let me try different construction"
Round 3: (data missing)
Round 4: Verification finds Critical Error → SUSPICIOUS (bug!)
         Generator: "Getting closer, another iteration"
Round 5: Prompt-based attack → ROBUST!
         Generator: "First success!"
Rounds 6-8: Verification finds gaps → SUSPICIOUS (expected)
Round 9: ROBUST × 3 → SUCCESS
```

**Actual total:** 9 rounds (80% slower than expected)

---

## The Fix

### Fix #1: Update String Matching (CRITICAL)

**File:** `code/adversarial_critic.py` line 170

**Current:**
```python
if "critical error" in bug_report_lower:
    verdict = "BROKEN"
```

**Fixed:**
```python
if ("critical error" in bug_report_lower or
    "critical errors" in bug_report_lower):
    verdict = "BROKEN"
```

**Better fix (more robust):**
```python
if "critical" in bug_report_lower and "error" in bug_report_lower:
    verdict = "BROKEN"
```

**Best fix (regex for flexibility):**
```python
import re
if re.search(r'\bcritical\s+errors?\b', bug_report_lower):
    verdict = "BROKEN"
```

---

### Fix #2: Install SymPy (MEDIUM)

**Add to requirements.txt:**
```
sympy>=1.12
```

**Or install manually:**
```bash
pip install sympy
```

**Impact:** Improves semantic answer equivalence checking in TIER 2

---

### Fix #3: Improve Error Messaging (LOW)

**File:** `code/tier2_refinement.py` line 1066

**Current:**
```python
print(f"[SEMANTIC CHECK] SymPy failed: {e}")
```

**Improved:**
```python
print(f"[SEMANTIC CHECK] SymPy unavailable (optional dependency): {e}")
print(f"[SEMANTIC CHECK] Install with: pip install sympy")
print(f"[SEMANTIC CHECK] Falling back to pattern matching...")
```

---

## Expected Results After Fixes

### With Fix #1 Applied:

**Problem 1 test (re-run):**
```
Round 0: Verification finds Critical Error → BROKEN ✓
         Generator: Major revision
Round 1: Verification checks → Justification Gap → SUSPICIOUS ✓
Round 2: Prompt attack → ROBUST
Round 3: ROBUST × 3 → SUCCESS after 3 rounds

Total time: ~15-20 minutes (vs 37 minutes in buggy version)
Efficiency: 2× faster
```

### With Fix #2 Applied:

**TIER 2 refinement:**
- SymPy semantic checking works
- No false answer-change rejections
- TIER 2 more likely to succeed

---

## Additional Gap: Verification Logging

**Issue:** Hard to distinguish in-RLAC verification from final verification in logs

**Current logging:**
```
[ADVERSARIAL CRITIC] Running cooperative verification...
```

**Both in-RLAC and post-RLAC use same message!**

**Improvement:**
```python
if should_verify:
    self._log(f"[IN-RLAC VERIFICATION] Round {round_num}/{max_rounds}")
    self._log(f"[IN-RLAC VERIFICATION] Running cooperative verification...")
```

**Impact:** Better observability for debugging

---

## Summary

### Gaps Identified:

1. **CRITICAL:** String matching for "critical error" failed due to plural form
   - Expected: BROKEN verdicts for critical errors
   - Actual: SUSPICIOUS verdicts
   - Impact: 80% slower convergence (9 rounds vs 5 expected)

2. **MEDIUM:** SymPy dependency missing
   - Expected: Semantic equivalence checking with SymPy
   - Actual: Fallback to pattern matching
   - Impact: Minimal (pattern matching worked)

3. **LOW:** Logging doesn't distinguish in-RLAC from post-RLAC verification
   - Expected: Clear markers for debugging
   - Actual: Same log message for both
   - Impact: Observability issue only

### Success Despite Bugs:

✅ In-RLAC verification **DID** run (5 times as configured)
✅ Critical errors **WERE** caught and reported
✅ Generator **DID** converge to correct answer
✅ Final status: **TIER_1_ONLY** (answer verified)

**The implementation works but is suboptimal due to verdict mapping bug.**

---

## Recommendations

### Priority 0: Fix Critical Error Matching (30 minutes)

```python
# code/adversarial_critic.py line 170
if re.search(r'\bcritical\s+errors?\b', bug_report_lower):
    verdict = "BROKEN"
```

**Expected improvement:** 40-50% faster convergence on FIND problems

### Priority 1: Install SymPy (5 minutes)

```bash
pip install sympy
```

**Expected improvement:** Better TIER 2 semantic checking

### Priority 2: Improve Logging (15 minutes)

Add `[IN-RLAC VERIFICATION]` prefix to in-RLAC verification logs

**Expected improvement:** Better debugging and analysis

---

## Test Plan

1. **Apply Fix #1** (critical error matching)
2. **Re-run test:** `./test_inline_verification.sh problems/imo01.txt`
3. **Verify:**
   - Round 0 should show BROKEN verdict (not SUSPICIOUS)
   - Convergence in 4-6 rounds (not 9)
   - Total time: 20-25 minutes (not 37)
4. **Test on problem 2** to ensure no regression

---

## Conclusion

**In-RLAC verification feature is working** but has a critical bug in verdict mapping.

**Root cause:** Case-sensitive string matching didn't account for:
- Plural forms ("critical errors" vs "critical error")
- Singular forms with articles ("a critical error")
- Markdown formatting in verification output

**Fix:** Use regex pattern matching: `r'\bcritical\s+errors?\b'`

**Expected impact:** 40-50% faster convergence to "verification good" status
