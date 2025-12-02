# TIER 2 Proof Problem Architecture Fix

**Date**: 2025-12-02
**Status**: ✅ Fixed and Validated
**Issue Type**: **ARCHITECTURAL LIMITATION** - Not a bug, but a design mismatch
**Root Cause**: Answer locking designed for computational problems, incompatible with proof problems

---

## Executive Summary

After fixing the nested braces bug, TIER 2 still failed with a **different error**:

```
[TIER 2 ERROR] Answer changed during refinement!
[TIER 2 ERROR]   Expected: A,B,E,F\text{ are concyclic}
[TIER 2 ERROR]   Got: \text{The required line is tangent to }(BEF).
```

**Expert Analysis** (OpenAI Engineer + Nvidia Scientist) revealed this is NOT a bug but an **architectural mismatch**:
- RLAC was designed for **computational problems** with discrete answers (e.g., "Find x = 42")
- Problem 2 is a **"prove that" problem** where the answer IS the proof itself
- Answer locking on intermediate boxed results creates false rejections during refinement

**Fix**: Disable answer locking for "prove that" problems, allowing TIER 2 to refine proofs without constraint.

**Result**: ✅ All tests passing, ready for end-to-end validation

---

## The Problem in Detail

### What Happened

**Problem 2 Statement:**
> **Prove that** the line through H parallel to AP is tangent to the circumcircle of triangle BEF.

**RLAC Behavior:**
1. Model solves using coordinate geometry
2. Boxes intermediate results: `\boxed{P=\Bigl(X_{c},...\Bigr)}`
3. Answer extraction grabs **first box** (P coordinates)
4. System locks this as the "answer" ❌

**TIER 2 Behavior:**
1. Refinement adds proof structure
2. May box lemmas: `\boxed{A,B,E,F\text{ are concyclic}}`
3. May box conclusion: `\boxed{\text{Line is tangent to }(BEF).}`
4. First box changes → extraction gets **different** result
5. Comparison fails → refinement rejected ❌

### Why This Is Wrong

**For "prove that" problems:**
- There is NO discrete answer to lock
- The answer IS the proof itself
- Boxed expressions are:
  - Intermediate formulas (e.g., coordinates)
  - Key lemmas (e.g., "these points are concyclic")
  - Emphasis markers (e.g., "this is the key insight")
  - **NOT** the final answer

**The locked "answer" is arbitrary** - it depends on which intermediate result happens to be boxed first.

---

## Expert Analysis Summary

### OpenAI Engineer's Findings

**Primary Issue:**
> "The `extract_boxed_answer()` function returns the FIRST `\boxed{}` expression. For proof problems with multiple boxes, this picks up an arbitrary intermediate result."

**Evidence from Logs:**
```
RLAC Solution (Problem 2):
- Box #1: P=\Bigl(X_{c},-\dfrac{X_{c}(r+x_{0})}{y_{0}}\Bigr)  ← LOCKED
- Box #2: H=\Bigl(X_{c},...)
- Conclusion (not boxed): "Line is tangent to circumcircle"

The actual answer is NOT boxed!
```

**Recommendation:**
- Disable answer locking for proof problems
- Allows TIER 2 to refactor proof structure freely

### Nvidia Scientist's Findings

**Mathematical Assessment:**
> "Problem asks to PROVE tangency, not compute coordinates. The locked answer (coordinates of P) doesn't answer the question."

**Key Insights:**
1. **Both answers are mathematically TRUE:**
   - "A,B,E,F are concyclic" (intermediate lemma)
   - "Line is tangent to (BEF)" (final conclusion)

2. **But they're DIFFERENT STEPS in the proof:**
   - RLAC locked a boxed intermediate formula
   - TIER 2 refinement extracts a different boxed statement
   - String comparison fails → false rejection

3. **Architectural Issue:**
   - RLAC designed for: "Find x" → `\boxed{x=42}` ✓
   - Doesn't fit: "Prove that" → Proof is the answer, not a boxed value

**Recommendation:**
- Disable answer lock for proof problems (short-term)
- Consider semantic matching for multi-step proofs (long-term)

### Areas of Agreement

Both experts **unanimously agreed**:
1. ✅ This is NOT a bug - it's an architectural limitation
2. ✅ The refinements are mathematically correct
3. ✅ Answer locking is fundamentally incompatible with proof problems
4. ✅ Short-term fix: Disable locking for "prove that" problems
5. ✅ Long-term: Need problem type classification + semantic matching

---

## The Fix

### Implementation

**File:** `code/tier2_refinement.py`

**Added function:**
```python
def is_proof_problem(problem_statement):
    """Detect if problem asks to prove something (not compute a value)."""
    if not problem_statement:
        return False

    problem_lower = problem_statement.lower()
    proof_indicators = [
        'prove that',
        'show that',
        'demonstrate that',
        'verify that',
        'establish that',
        'prove the',
    ]
    return any(indicator in problem_lower for indicator in proof_indicators)
```

**Updated function:**
```python
def extract_boxed_answer(solution, problem_statement=None):
    """
    Extract answer from \\boxed{...} for verification.
    For "prove that" problems, returns None to disable answer locking.
    """
    if not solution:
        return None

    # Disable answer locking for proof problems
    if problem_statement and is_proof_problem(problem_statement):
        return None  # ← Key change!

    # For computational problems, extract answer as before
    # ... (balanced brace parser)
```

**Updated call site (line 116):**
```python
# Pass problem_statement to enable proof detection
refined_answer = extract_boxed_answer(refined_solution, problem_statement)
```

### Why This Works

**For computational problems** (e.g., "Find x"):
- `is_proof_problem()` returns `False`
- Answer extraction proceeds normally
- Answer lock enforced ✓

**For proof problems** (e.g., "Prove that X"):
- `is_proof_problem()` returns `True`
- `extract_boxed_answer()` returns `None`
- Answer lock **disabled** ✓
- TIER 2 can refine proof structure freely ✓

**The check at line 118:**
```python
if refined_answer and refined_answer != locked_answer:
    reject_refinement()
```

With `refined_answer = None` and `locked_answer = None`:
- Condition is `False` (None is falsy)
- Refinement accepted regardless of boxed content ✓

---

## Validation

### Test Suite

Created `test_proof_problem_fix.py` with 3 comprehensive tests:

#### Test 1: Problem Type Detection

```
✓ PASS - Problem 2 (actual IMO prove-that problem)
✓ PASS - Computational problem (find value)
✓ PASS - Show that problem
✓ PASS - Demonstrate that problem
✓ PASS - Determine problem
```

All 5 problem types correctly classified ✓

#### Test 2: Answer Lock Behavior

```
Proof problem:
  Extracted answer: None
  Answer lock: DISABLED ✓

Computational problem:
  Extracted answer: 42
  Answer lock: ENABLED ✓
```

Lock behavior correct for both types ✓

#### Test 3: Problem 2 Specific Case

```
RLAC locked answer:     None
TIER 2 refined answer:  None
Comparison result:      MATCH
Would refinement pass?  YES ✓

✓✓ CORRECT: Answer locking is DISABLED for proof problems!
✓✓ Refinements can now proceed without false rejections!
```

Exact scenario from error logs now works ✓

### Overall Result

```
✓✓✓ ALL TESTS PASSED!
✓✓✓ Proof problem fix is working correctly!
```

---

## Impact Analysis

### What This Fixes

**Before:**
```
TIER 2 Round 1: Generate refinement with valid proof
                Extract answer: "A,B,E,F are concyclic"
                Locked answer: "P=(coordinates)"
                Comparison: MISMATCH
                Result: REJECTED ❌

TIER 2 Round 2-5: Same rejection pattern
Final: TIER_1_ONLY (max rounds exhausted)
```

**After:**
```
TIER 2 Round 1: Generate refinement with valid proof
                Extract answer: None (proof problem)
                Locked answer: None (proof problem)
                Comparison: MATCH (both None)
                Result: ACCEPTED ✓

TIER 2 continues: Verify → refine → verify...
Final: TIER_2_VERIFIED (if refinement fills gaps)
```

### Problems This Affects

**Proof problems** (will benefit from fix):
- Problem 2: "Prove that line is tangent..." ✓
- Problem 4: "Prove that..." (if present) ✓
- Problem 6: "Show that..." (if present) ✓

**Computational problems** (unchanged):
- Problem 1: "Find the number of..." (if present)
- Problem 3: "Determine all..." (if present)
- Problem 5: "Compute..." (if present)

---

## Bugs Fixed Summary

This is the **THIRD** TIER 2 bug fixed in this session:

### Bug #1: Parsing Bug (FIXED - 2025-12-02)
- **Issue**: Regex patterns didn't match markdown format
- **Fix**: Updated regex to handle `### List of Findings`, bold markers, multiple separators
- **Result**: 5/5 issues now parsed correctly

### Bug #2: Format Bug (FIXED - 2025-12-02)
- **Issue**: Refinements missing "### Detailed Solution ###" marker
- **Fix**: Updated refinement prompt to explicitly request marker
- **Result**: Refinements now pass format extraction

### Bug #3: Nested Braces Bug (FIXED - 2025-12-02)
- **Issue**: Regex pattern `[^}]+` stopped at first `}`, truncating nested LaTeX
- **Fix**: Balanced brace parser with depth counter
- **Result**: Complex LaTeX expressions extracted correctly

### Bug #4: Proof Problem Architecture (FIXED - 2025-12-02) ← **THIS FIX**
- **Issue**: Answer locking incompatible with "prove that" problems
- **Fix**: Disable answer lock for proof problems
- **Result**: TIER 2 can refine proofs without false rejections

---

## Next Steps

### Immediate: Re-run Problem 2

With **ALL FOUR** bugs now fixed:

```bash
python code/agent_gpt_oss.py problems/imo02.txt \
  --use-rlac \
  --rlac-max-rounds 30 \
  --rlac-stuck-threshold 5 \
  --rlac-robust-threshold 3 \
  --log test_rlac_log/tier2_test_p2_all_fixes.log \
  --memory test_rlac_log/tier2_test_p2_all_fixes.json
```

**Expected Outcome:**
1. ✅ RLAC achieves TIER 1 (answer correct)
2. ✅ TIER 2 begins refinement
3. ✅ Parsing extracts 5 issues correctly
4. ✅ Format marker present in refinements
5. ✅ Nested braces extracted correctly
6. ✅ **Answer lock disabled** (proof problem)
7. ✅ Refinements accepted and applied
8. 🎯 **TIER 2 VERIFIED** (if refinement fills gaps)

### Long-Term Enhancements

**From expert recommendations:**

1. **Semantic Answer Matching** (Nvidia Scientist)
   - Use LLM to check if two answers are mathematically equivalent
   - E.g., "line is tangent" vs "distance equals radius"

2. **Problem Type Classification** (Both experts)
   - COMPUTATIONAL: Find/Compute/Determine
   - PROOF: Prove/Show/Demonstrate
   - EXISTENTIAL: Does there exist/Find all
   - Different extraction logic for each type

3. **Multi-Answer Extraction** (OpenAI Engineer)
   - Extract ALL boxed expressions, not just first
   - Rank by relevance to problem statement
   - Allow any of them to match during comparison

---

## Files Changed

### Code Changes
- `code/tier2_refinement.py` (lines 313-393):
  - Added `is_proof_problem()` function
  - Updated `extract_boxed_answer()` to detect proof problems
  - Updated call site to pass `problem_statement`

### Test Files
- `test_proof_problem_fix.py` (NEW):
  - 3 comprehensive test scenarios
  - Validates proof detection and lock behavior
  - Tests actual Problem 2 case

### Documentation
- `TIER2_PROOF_PROBLEM_FIX.md` (THIS FILE):
  - Complete architectural analysis
  - Expert findings and debate
  - Before/after behavior
  - Validation results

---

## Commit Message

```
Fix TIER 2 proof problem architecture issue - disable answer lock

ARCHITECTURAL ISSUE: Answer locking was designed for computational problems
("Find x") but is incompatible with proof problems ("Prove that X").

For proof problems:
- The answer IS the proof itself, not a boxed expression
- Boxed expressions are intermediate formulas/lemmas
- Locking on arbitrary intermediate results creates false rejections

Impact: TIER 2 exhausted all 5 rounds rejecting valid refinements because:
- RLAC locked: P=(coordinates)  [first box encountered]
- TIER 2 refined: A,B,E,F are concyclic  [different first box]
- Comparison failed → refinement rejected

Root cause (identified by dual-expert analysis):
- OpenAI Engineer: "First vs last box extraction issue"
- Nvidia Scientist: "Proof problems don't have discrete answers"
- Both agreed: Disable locking for proof problems

Fix: Add is_proof_problem() detection
- Detects "prove that", "show that", etc. in problem statement
- Returns None (disables lock) for proof problems
- Preserves locking for computational problems

Validation:
- All 5 test cases passing
- Problem 2 specific case validated
- Answer lock correctly disabled for proofs
- Answer lock correctly enabled for computations

Expert consensus: This is a design evolution, not a bug fix.
The system needs problem-type awareness for different mathematical tasks.

Files:
- code/tier2_refinement.py: Add proof problem detection
- test_proof_problem_fix.py: Comprehensive test suite
- TIER2_PROOF_PROBLEM_FIX.md: Complete analysis
```

---

**Last Updated**: 2025-12-02
**Status**: ✅ Fixed, validated, and documented
**Next**: Commit and re-run Problem 2 for end-to-end validation
**All 4 TIER 2 bugs now resolved** 🎉
