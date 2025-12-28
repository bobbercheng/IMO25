# Data Leakage Analysis: "k∈{0,1,3} ✓ CORRECT" Source Investigation

## Executive Summary

**Finding:** The verification system leaks the ground truth answer for Problem 5 through hardcoded few-shot examples in the verification prompt.

**Impact:** The cooperative verifier knows the correct answer is `k∈{0,1,3}` before evaluating any solution, potentially biasing verification towards accepting solutions with this answer.

**Severity:** HIGH - This invalidates verification results for Problem 5 and explains the inflated success rates.

---

## Root Cause Analysis

### 1. Source Location

**File:** `code/agent_oai.py`
**Lines:** 368-460
**Variable:** `verification_examples`

The data leakage occurs in three places within the few-shot calibration examples:

```python
# Line 384 (Example 1):
1. Check final answer: k∈{0,1,3} ✓ CORRECT

# Line 406 (Example 2):
1. Check final answer: k∈{0,1,3} ✓ CORRECT

# Line 424 (Example 3):
1. Check final answer: k∈{0,1,3} ✓ CORRECT
```

### 2. Propagation Path

```
agent_oai.py (lines 368-460)
    ↓ defines verification_examples
    ↓
agent_gpt_oss.py (line 42)
    ↓ imports verification_examples
    ↓
agent_gpt_oss.py (line 1609)
    ↓ injects into verification prompt
    ↓
Verification API call
    ↓ sends to model with ground truth
```

### 3. Example Context

The examples are designed as few-shot calibration for the verification system:

**Example 1 (Line 381-394):**
```
Problem: "Determine all k such that n lines with exactly k sunny lines cover all required points."

Solution excerpt: "Column x=n-2 has 3 points, so one of the non-sunny lines **must be vertical**.
Therefore k=2 is impossible. Final answer: k∈{0,1,3}."

**Applying the Decision Rule:**
1. Check final answer: k∈{0,1,3} ✓ CORRECT  ← DATA LEAKAGE
2. Check constructions: Valid constructions provided for k=0,1,3 ✓
3. Decision: Answer correct → Classify as **Justification Gap**
```

**Example 2 (Line 401-412):**
```
Problem: "Determine all k..."

Solution excerpt: "For k=2, I tried many constructions and couldn't find one.
Therefore k=2 doesn't work. Final answer: k∈{0,1,3}."

**Applying the Decision Rule:**
1. Check final answer: k∈{0,1,3} ✓ CORRECT  ← DATA LEAKAGE
2. Check impossibility reasoning: "I tried and failed" ✗ INVALID (falls under EXCEPTION)
3. Decision: Invalid reasoning → Classify as **Critical Error**
```

**Example 3 (Line 419-434):**
```
Problem: "Determine all k such that n lines with exactly k sunny lines cover all required points."

Solution excerpt: "If k≤2 then column x=n-2 (which contains three points) cannot be covered
solely by sunny lines; consequently one of the non-sunny lines must be vertical and must be
the line x=n-2. Now consider k≥4: Since a sunny line can meet each column in at most one point,
having k≥4 would force at least four columns to rely on sunny lines. Because the three rightmost
columns already force the use of a vertical line for column n-2, we would run out of vertical lines.
Final answer: k∈{0,1,3}."

**Applying the Decision Rule:**
1. Check final answer: k∈{0,1,3} ✓ CORRECT  ← DATA LEAKAGE
2. Check reasoning method: Case analysis (k≤2 vs k≥4), counting arguments ✓ VALID mathematical tools
3. Check context-dependent claim: "columns force vertical line" is TRUE for k≤2 case but
   stated without explicit scope in k≥4 analysis
```

---

## Impact Assessment

### Affected Components

1. **agent_oai.py** - OpenAI GPT-5 agent (defines the leaky examples)
2. **agent_gpt_oss.py** - GPT-OSS agent with RLAC mode (imports and uses the examples)
3. **All verification calls** - Both standard verification and in-RLAC cooperative verification

### Bias Mechanism

The verification prompt structure is:
```
{verification_system_prompt}      ← General instructions (no leakage)
{problem_statement}                ← Problem 5 description
{solution_to_verify}               ← Candidate solution
{verification_examples}            ← FEW-SHOT EXAMPLES WITH k∈{0,1,3} ✓ CORRECT ← LEAKAGE!
{verification_remider}             ← Final instructions
```

When the verifier processes this prompt, it sees:
1. Three examples showing `k∈{0,1,3}` marked as `✓ CORRECT`
2. The same problem type ("Determine all k such that n lines with exactly k sunny lines...")
3. This primes the model to expect `k∈{0,1,3}` as the correct answer

### Consequences

1. **Answer Bias:** Verifier may be more lenient with solutions claiming `k∈{0,1,3}`
2. **False Positives:** Wrong solutions with correct answer may pass verification
3. **Invalidated Results:** All n=30 validation results are suspect
4. **Test Failure Explanation:** This explains why Option A tests had high PASS rates despite quality issues

---

## Removal Strategy

### Option 1: Generic Examples (Recommended)

Replace Problem 5-specific examples with generic mathematical verification examples:

```python
verification_examples = """

---

## CRITICAL: Few-Shot Calibration Examples (2025-12-28 Fix)

**These examples show you how to apply the decision rule above. Study them carefully before verifying the solution.**

**Example 1: Justification Gap (NOT Critical Error)**

Problem: "Find all prime numbers p such that p² + 2 is also prime."

Solution excerpt: "For p=3, we have p²+2=11 which is prime. For p>3, we have p≡1 or 2 (mod 3),
so p²≡1 (mod 3), thus p²+2≡0 (mod 3), making it divisible by 3 and >3, hence composite.
Final answer: p=3."

**Applying the Decision Rule:**
1. Check final answer: p=3 ✓ CORRECT
2. Check reasoning method: Modular arithmetic, case analysis ✓ VALID
3. Check presentation: Missing explicit check for p=2 → Justification Gap
4. Decision: Answer correct + method valid → PASS

**Example 2: Critical Error (truly invalid)**

Problem: "Prove that √2 is irrational."

Solution excerpt: "I tried to express √2 as p/q for many fractions and couldn't find one.
Therefore √2 is irrational."

**Applying the Decision Rule:**
1. Check final answer: √2 is irrational ✓ CORRECT
2. Check reasoning method: "I tried and failed" ✗ INVALID (not a proof method)
3. Decision: Invalid reasoning → FAIL

**Example 3: Context-Dependent Claim (Justification Gap)**

Problem: "Prove that the sum of two odd integers is even."

Solution excerpt: "Let a and b be odd integers. Then a=2k+1 and b=2m+1 for integers k,m.
Therefore a+b=2k+2m+2=2(k+m+1), which is even. Since k+m+1 is clearly an integer, the sum is even."

**Applying the Decision Rule:**
1. Check final answer: Sum is even ✓ CORRECT
2. Check reasoning method: Algebraic manipulation ✓ VALID
3. Check presentation: "k+m+1 is clearly an integer" lacks explicit justification → Justification Gap
4. Decision: Answer correct + method valid → PASS

---
"""
```

### Option 2: Remove Examples Entirely

Simply set `verification_examples = ""` and rely on the hierarchical decision tree in `verification_system_prompt`.

### Option 3: Problem-Agnostic Template

Create examples with placeholder variables that don't leak specific answers:
```
Check final answer: [ANSWER] ✓ CORRECT/WRONG
```

---

## Recommended Fix

**Immediate Action:**
1. Replace `verification_examples` in `code/agent_oai.py` with generic examples (Option 1)
2. Re-run the n=30 validation with clean prompts
3. Re-test Option A with fixed verification

**Verification:**
```bash
# Check that the fix removes the leakage
grep -n "k∈{0,1,3}" code/agent_oai.py
# Should return NO results after fix

# Check imports are still working
grep -n "verification_examples" code/agent_gpt_oss.py
# Should show import and usage, but content will be clean
```

---

## Related Files to Update

1. **Primary:** `code/agent_oai.py` (lines 368-460)
2. **Secondary:** `code/agent_gpt_oss.py` (imports from agent_oai, no changes needed)
3. **Verification:** All `validation_results_n30/*.log` files are contaminated

---

## Testing Plan

After implementing the fix:

1. **Unit Test:** Verify no problem-specific answers in verification prompts
2. **Integration Test:** Run 5 RLAC iterations with clean verification
3. **Comparison Test:** Compare results before/after fix to quantify impact
4. **Documentation:** Update CLAUDE.md with fix notes

---

## Conclusion

The data leakage is **100% confirmed** and located in `code/agent_oai.py:368-460`. The fix is straightforward: replace problem-specific examples with generic mathematical examples. This will enable proper testing of Option 2 (cooperative verification) without bias.

**User Preference:** Option 2 (cooperative verification) once data leakage is resolved ✓

**Next Steps:**
1. Apply fix to `code/agent_oai.py`
2. Re-test Option A with clean verification
3. Proceed with Option 2 implementation
