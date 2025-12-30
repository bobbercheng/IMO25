# Fix Proposal: Test 4 False Positive (Missing Constructions)

**Issue:** Verification system incorrectly accepts Test 4 (incomplete proof claiming "construction exists" without explicit equations)

**Impact:** 33% false positive rate (1/3 FAIL cases incorrectly accepted)

**Status:** Blocks Solution 2 deployment (validation criterion: FP <3%)

---

## Problem Analysis

### Test 4 Solution Text

```markdown
For k=0, we can use non-sunny lines (verticals, horizontals, or slope -1).
Construction exists using vertical lines.

For k=1, we can use 1 sunny line with (n-1) non-sunny lines.
Construction exists.

For k=3, construction exists using three sunny lines.

For k≥4, impossible because sunny lines cover at most one point per column.

**Final Answer:** k ∈ {0, 1, 3}
```

### Why This Should FAIL

**Missing:**
- k=0: Doesn't specify which vertical lines (x=1? x=2? all of them?)
- k=1: No equation for the sunny line (what's the slope? intercept?)
- k=3: No equations for the three sunny lines

**Expected classification:** CRITICAL_ERROR - Missing constructions
**Actual classification:** Likely JUSTIFICATION_GAP (due to correct answer override)

### Root Cause

The verification system follows this logic:

1. **Level 1:** Answer k∈{0,1,3} is CORRECT ✅
2. **Level 2:** Method (case analysis) is VALID ✅
3. **Level 3:** Should detect missing constructions → likely classifies as JUSTIFICATION_GAP (not CRITICAL_ERROR)
4. **Policy override** (`verification_schema.py` line 173-176):
   ```python
   if verdict_obj["answer_correctness"] in ["CORRECT", "INCOMPLETE"]:
       has_critical_error = any(issue["type"] == "CRITICAL_ERROR" for issue in issues)
       if not has_critical_error:
           return verdict_obj, "yes"  # Override FAIL → PASS
   ```

**Problem:** Missing constructions are classified as JUSTIFICATION_GAP instead of CRITICAL_ERROR, so policy override accepts the proof.

---

## Proposed Fixes

### Fix 1: Add Construction Completeness Guidance to Prompt ⭐ RECOMMENDED

**File:** `code/agent_oai.py`
**Location:** After Level 3 implementation (line ~285-295)

**Current text:**
```markdown
**LEVEL 3 IMPLEMENTATION: Presentation Quality**
*   Now that answer is correct (Level 1 ✓) and reasoning is valid (Level 2 ✓), examine presentation details.
*   Classify issues into two categories:

    **Justification Gap (acceptable):**
    *   Imprecise wording that doesn't affect logic
    *   Missing intermediate algebraic steps that would be straightforward to fill in
    *   Incomplete verification of constructions when construction logic is sound
    *   Typos in intermediate steps that don't propagate to final answer

    **Critical Error (unacceptable):**
    *   Demonstrably wrong intermediate calculations that invalidate logic chain
    *   Circular reasoning or logical fallacies
    *   Construction that produces wrong output when tested
```

**Proposed addition:**
```markdown
**LEVEL 3 IMPLEMENTATION: Presentation Quality**
*   Now that answer is correct (Level 1 ✓) and reasoning is valid (Level 2 ✓), examine presentation details.
*   Classify issues into two categories:

    **Justification Gap (acceptable):**
    *   Imprecise wording that doesn't affect logic (e.g., "must be vertical" vs "can be taken as vertical")
    *   Missing intermediate algebraic steps that would be straightforward to fill in
    *   Incomplete verification of constructions when construction logic is sound
    *   Typos in intermediate steps that don't propagate to final answer

    **Critical Error (unacceptable):**
    *   Demonstrably wrong intermediate calculations that invalidate logic chain
    *   Circular reasoning or logical fallacies
    *   Construction that produces wrong output when tested
    *   **IMPORTANT: Missing constructions for FIND problems:** If the problem asks to "determine all k"
        and the solution claims "construction exists" without providing explicit equations, this is a
        CRITICAL_ERROR (not a justification gap). The solution must show at least one explicit construction
        for each claimed value.

*   **Construction Completeness Rule for FIND Problems:**
    If the solution claims a value works (e.g., "k=1 is possible"), it must provide at least one explicit
    construction showing:
    - For line problems: Explicit equations (e.g., "y = 2x + 1" or "x = 3")
    - For set problems: Explicit elements
    - For configuration problems: Explicit arrangement

    **Examples:**
    - ❌ "Construction exists using vertical lines" → CRITICAL_ERROR (no equations)
    - ✅ "Use vertical lines x=1, x=2, ..., x=n" → JUSTIFICATION_GAP (equations provided, verification optional)
    - ❌ "For k=3, construction exists using three sunny lines" → CRITICAL_ERROR (no equations)
    - ✅ "For k=3, use L1: y=2x, L2: y=-x+5, L3: y=x-1" → Acceptable

*   **Quality Decision:** Only Justification Gaps → PASS, Any Critical Errors in logic chain → FAIL.
```

**Impact:**
- Explicitly guides LLM to classify missing constructions as CRITICAL_ERROR
- Provides clear examples of acceptable vs unacceptable construction descriptions
- Should fix Test 4 false positive without affecting other tests

**Testing:** Re-run shadow mode, expect Test 4 to correctly FAIL

---

### Fix 2: Add Few-Shot Example for Missing Constructions

**File:** `code/agent_oai.py`
**Location:** After Example 3 (line ~390)

**Proposed new Example 4:**
```markdown
---

**Example 4: Missing Construction (Critical Error)**
*This example shows a solution that claims constructions exist without providing them.*

Problem: "Determine all k such that n lines with exactly k sunny lines cover all required points."

Solution excerpt: "For k=0, construction exists using vertical lines. For k=1, we can use 1 sunny line with (n-1) non-sunny lines. Construction exists. For k=3, construction exists using three sunny lines. Final answer: k∈{0,1,3}."

**Applying the Decision Rule:**
1. Check final answer: k∈{0,1,3} ✓ CORRECT
2. Check constructions: Claims "exists" but no explicit equations ✗
3. Decision: Missing constructions → Classify as **Critical Error**

**Correct Classification:**
*   **Location:** "For k=1, we can use 1 sunny line with (n-1) non-sunny lines. Construction exists."
    *   **Issue:** Critical Error (severity 9) - The solution claims a construction exists but does not provide an explicit equation for the sunny line. For FIND problems, constructions must be shown, not just claimed. This is different from a justification gap (which would be incomplete verification of a provided construction). Here, the construction itself is missing.

**Key Distinction:**
- JUSTIFICATION_GAP: Construction shown but not fully verified (e.g., "Use line y=2x. Points covered by inspection.")
- CRITICAL_ERROR: Construction not shown at all (e.g., "Construction exists.")

---
```

**Update meta-instruction to reference 4 examples:**
```markdown
When you encounter a pattern matching Example 1, 2, 3, or 4 above:
```

**Impact:**
- Provides explicit calibration for missing construction pattern
- Distinguishes between "construction provided but not verified" (GAP) vs "construction not provided" (ERROR)
- Should improve few-shot learning for this edge case

**Trade-off:**
- Increases prompt length (back to 4 examples, vs our optimization to 3)
- May increase token usage by ~800-1000 tokens
- Worth it if it fixes 33% FP rate

---

### Fix 3: Tighten Policy Override Logic (ALTERNATIVE)

**File:** `code/verification_schema.py`
**Location:** `interpret_verdict()` function (line 162-180)

**Current code:**
```python
if verdict_obj["verdict"] == "FAIL":
    if verdict_obj["answer_correctness"] in ["CORRECT", "INCOMPLETE"]:
        issues = verdict_obj.get("issues", [])
        if issues:
            has_critical_error = any(
                issue["type"] == "CRITICAL_ERROR" for issue in issues
            )
            if not has_critical_error:
                # All issues are gaps, answer is correct/incomplete → PASS
                print("[VERDICT OVERRIDE] Answer correct/incomplete with only justification gaps → PASS")
                return verdict_obj, "yes"
```

**Proposed change:**
```python
if verdict_obj["verdict"] == "FAIL":
    if verdict_obj["answer_correctness"] in ["CORRECT", "INCOMPLETE"]:
        issues = verdict_obj.get("issues", [])
        if issues:
            has_critical_error = any(
                issue["type"] == "CRITICAL_ERROR" for issue in issues
            )
            # NEW: Check if any gaps are severity 8+ (should be errors, not gaps)
            has_high_severity_gap = any(
                issue["type"] == "JUSTIFICATION_GAP" and issue.get("severity", 0) >= 8
                for issue in issues
            )
            if not has_critical_error and not has_high_severity_gap:
                # All issues are low-severity gaps, answer is correct → PASS
                print("[VERDICT OVERRIDE] Answer correct with only low-severity justification gaps → PASS")
                return verdict_obj, "yes"
```

**Rationale:**
- Severity 8-10 should be reserved for CRITICAL_ERRORs
- If a JUSTIFICATION_GAP has severity 8+, it's likely misclassified
- Add safety check: don't override if high-severity gaps present

**Impact:**
- Defensive programming against misclassification
- Doesn't fix root cause (prompt should classify correctly)
- Useful as fallback if LLM sometimes misclassifies errors as gaps

---

## Recommended Implementation Strategy

### Phase 1: Prompt Fix (Fix 1) ⭐

**Why start here:**
- Root cause fix (teaches LLM to classify correctly)
- No code changes to `verification_schema.py`
- Preserves 3-example optimization (just adds clarification text)

**Implementation:**
1. Add construction completeness guidance to Level 3 description
2. Add explicit examples and decision rules
3. Re-run shadow mode validation
4. Expected: Test 4 correctly classified as CRITICAL_ERROR → FAIL

**If Test 4 still passes:** Proceed to Phase 2

### Phase 2: Few-Shot Example (Fix 2)

**Why second:**
- Reinforces prompt guidance with concrete example
- Provides explicit calibration for edge case
- Trade-off: +1 example (+800 tokens) but fixes 33% FP

**Implementation:**
1. Add Example 4 (missing construction pattern)
2. Update meta-instruction to reference 4 examples
3. Re-run shadow mode validation
4. Expected: Test 4 correctly FAIL

**If Test 4 still passes:** Proceed to Phase 3

### Phase 3: Policy Override Safety (Fix 3)

**Why last resort:**
- Defensive fix (not root cause)
- Useful if LLM inconsistently classifies
- Adds safety net for high-severity gaps

**Implementation:**
1. Modify `interpret_verdict()` to check gap severity
2. Add logging for high-severity gap detection
3. Re-run shadow mode validation

---

## Testing Plan

### Test 1: After Fix 1 (Prompt Guidance)
```bash
python code/test_shadow_mode_validation.py --test 4 --verbose
```

**Expected output:**
- Baseline (HIGH): FAIL
- Optimized (MEDIUM): FAIL
- Agreement: ✅ YES
- Accuracy: ✅ ✅ (both correct)

### Test 2: Full Shadow Mode
```bash
python code/test_shadow_mode_validation.py --output week2_results_fixed.json
```

**Expected results:**
- Agreement rate: 100% (6/6)
- FP rate: 0% (0/3)
- FN rate: 0% (0/3)
- Accuracy: 100% (6/6)
- Validation decision: ✅ SUCCESS

### Test 3: Regression Check

**Verify other tests still work correctly:**
- Test 1-2 (complete proofs): Still PASS
- Test 3 (trial-and-error): Still FAIL
- Test 5 (wrong answer): Still FAIL
- Test 6 (justification gaps): Still PASS

**Critical:** Test 6 should still PASS (don't over-correct)
- Test 6 provides constructions but with gaps in verification
- This is different from Test 4 (no constructions at all)

---

## Success Criteria

### Validation Metrics (After Fix)

| Metric | Current | Target | Expected After Fix |
|--------|---------|--------|-------------------|
| Agreement Rate | 100% | ≥95% | 100% |
| FP Rate | 33.33% | <3% | **0%** |
| FN Rate | 0% | <2% | 0% |
| Accuracy | 83.33% | - | **100%** |
| Latency (optimized) | 13.5s | - | ~13.5s (unchanged) |

### Deployment Criteria

After implementing fixes and re-validating:
- ✅ Agreement ≥95% (currently 100%)
- ✅ FP <3% (fix should achieve 0%)
- ✅ FN <2% (currently 0%)
- ✅ No regression on Tests 1-3, 5-6

**Decision:** Deploy Solution 2 to production

---

## Alternative: Modify Test 4 Ground Truth (NOT RECOMMENDED)

**Argument:** "Construction exists" might be acceptable for FIND problems if the method is sound

**Counter-argument:**
1. IMO grading standards require explicit constructions
2. "Construction exists" without showing is trial-and-error in disguise
3. Accepting this creates loophole for incomplete proofs
4. Policy should be: correct answer + valid method + **explicit constructions**

**Recommendation:** Keep Test 4 expected verdict as FAIL, fix verification to correctly reject

---

## Timeline

**Phase 1 (Recommended):**
- Implementation: 30 minutes (add prompt guidance)
- Testing: 15 minutes (re-run shadow mode)
- Total: **45 minutes**

**If Phase 1 insufficient:**
- Phase 2: +1 hour (add few-shot example)
- Phase 3: +1 hour (modify policy override)

**Expected total:** 45 minutes to 2.5 hours

**Deployment:** Immediate upon validation success (FP <3%)
