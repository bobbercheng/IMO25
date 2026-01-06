# Data Leakage Fix Report

**Date:** 2026-01-06
**Issue:** test_small_case_validation_v2.py contained subtle data leakage
**Severity:** Critical - defeats the purpose of validation testing
**Status:** FIXED in v2.1

---

## The Problem: Subtle Data Leakage

### Original Implementation (v2.0)

The test provided the LLM with a list of **candidate formulas** including the correct answer:

```python
candidate_formulas = [
    {"name": "n+2k-3", "formula": "n + 2*k - 3"},  # ← CORRECT ANSWER!
    {"name": "n+2k-2", "formula": "n + 2*k - 2"},
    {"name": "n+2k-1", "formula": "n + 2*k - 1"},
    {"name": "2n-2", "formula": "2*n - 2"},
    {"name": "2n-1", "formula": "2*n - 1"},
]
```

**Task given to LLM:**
> "Test each candidate formula against verified cases and pick the one that matches all."

### Why This Is Data Leakage

This is equivalent to giving the LLM a **multiple-choice test** where the correct answer is already provided:

```
Question: What is the formula for minimum tiles?
A) n+2k-3  ← Correct answer is in the list!
B) n+2k-2
C) n+2k-1
D) 2n-2
E) 2n-1

Task: Pick the one that matches n=4→5 and n=9→12
```

**The issue:**
- LLM doesn't need to DISCOVER the pattern
- LLM only needs to TEST given formulas
- Success rate measures "can LLM evaluate formulas" not "can LLM derive formulas"
- Circular reasoning: We're validating the formula using the formula itself (just hidden in candidate list)

### User's Insight

> "I think test_formula_hypothesis() in test_small_case_validation_v2.py is a kind of data leakage as it gives the final formula n+2k-3"

**Absolutely correct!** By including the correct formula in the candidate list, we're providing the answer, just less obviously than writing it directly.

---

## The Fix: Formula Derivation (v2.1)

### New Approach

**Remove candidate formulas entirely.** Instead, ask the LLM to:

1. **Analyze** the verified small cases to find patterns
2. **Derive** a general formula f(n,k) from the pattern
3. **Verify** the derived formula matches ALL cases
4. **Apply** the formula to n=2025

### Updated Prompt

**Before (v2.0) - Multiple Choice:**
```
CANDIDATE FORMULAS TO TEST:
- Candidate A: n+2k-3
- Candidate B: n+2k-2
- Candidate C: 2n-2

Test each against verified cases and pick the winner.
```

**After (v2.1) - Pattern Discovery:**
```
VERIFIED SMALL-CASE GROUND TRUTH:
For n=4, k=2: 5 tiles
For n=9, k=3: 12 tiles

YOUR TASK:
1. Study these verified cases carefully
2. Find a pattern and DERIVE a general formula f(n,k)
3. Verify your formula matches ALL verified cases
4. Apply formula to n=2025, k=45

Do NOT guess - derive from pattern analysis.
```

### Key Changes

**1. No candidate formulas given:**
```python
# REMOVED: candidate_formulas list
# NOW: LLM must discover pattern independently
```

**2. Still reject obvious wrong formulas (not data leakage):**
```python
# OK to reject obvious mistakes that DON'T reveal the answer
naive_wrong_formulas = [
    {"name": "2n-2", "formula": "2*n - 2"},   # Too simple
    {"name": "n+k", "formula": "n + k"},       # Too simple
]
```

This is NOT data leakage because:
- Rejecting 2n-2 doesn't tell you the answer is n+2k-3
- It only says "don't use the most naive formula"
- Analog: "The answer is not 1+1=2" doesn't reveal the answer to "3×7=?"

**3. Updated JSON response format:**
```json
{
  "pattern_analysis": "description of pattern found",
  "derived_formula": "formula discovered from pattern",
  "verification": [...],
  "all_cases_match": true,
  "final_answer": 2112
}
```

---

## Validation: Is This Still Data Leakage?

### Question 1: Is showing n=4→5 and n=9→12 data leakage?

**Answer: NO** - This is legitimate ground truth.

**Why it's OK:**
- We independently verified n=4→5 via exhaustive CP-SAT search (NO formula used!)
- We trust n=9→12 from official IMO solution (rigorously proven)
- These are **constraints** the formula must satisfy, not the formula itself
- Analog: "The function must pass through (0,0) and (1,1)" doesn't reveal f(x)=x

### Question 2: Is pre-rejecting 2n-2 data leakage?

**Answer: NO** - Rejecting wrong answers doesn't reveal the right answer.

**Why it's OK:**
- Saying "2n-2 is wrong" doesn't imply "n+2k-3 is right"
- There are infinitely many formulas that aren't 2n-2
- Helps LLM avoid trivial mistakes without revealing answer
- Analog: "The capital of France is NOT Berlin" doesn't reveal it's Paris

### Question 3: If LLM can't derive the formula, should we give hints?

**Answer: DEPENDS on the hint type.**

**OK hints (guide thinking without revealing answer):**
- "Consider how k relates to n" ✓
- "Look for a linear combination of n and k" ✓
- "Try formulas of the form n+ak+b" ✓

**NOT OK hints (reveal structure of answer):**
- "Try formulas with -3 constant term" ✗
- "The formula has coefficient 2 for k" ✗
- "It's n plus something involving 2k" ✗

---

## Testing the Fix

### Expected Behavior (v2.1)

**Scenario 1: LLM successfully derives formula**
```
Pattern analysis: "n=4,k=2→5 gives 5=4+2×2-3
                   n=9,k=3→12 gives 12=9+2×3-3
                   Pattern: n+2k-3"
Derived formula: "n+2k-3"
Verification: All cases match ✓
Final answer: 2112 ✓
Result: SUCCESS - Legitimate pattern discovery
```

**Scenario 2: LLM fails to find pattern**
```
Pattern analysis: "Could be n+2k-2 or n+2k-1..."
Derived formula: "n+2k-2"
Verification: n=4 gives 6, expected 5 ✗
Result: FAILURE - LLM couldn't derive correct pattern
```

**Scenario 3: LLM gets lucky guess**
```
Pattern analysis: "Trying random formulas..."
Derived formula: "n+2k-3"
Verification: All cases match ✓
Result: NEUTRAL - Right answer but questionable reasoning
```

### Success Metrics

**Before (v2.0):**
- Measured: "Can LLM evaluate formulas?"
- Not measured: "Can LLM discover formulas?"

**After (v2.1):**
- Measured: "Can LLM discover formulas from small cases?"
- This is the REAL test of mathematical reasoning!

---

## Comparison: Data Leakage Levels

| Approach | Data Leakage | What LLM Learns | Value |
|----------|--------------|-----------------|-------|
| **Direct formula** | ✗✗✗ Maximum | Nothing (answer given) | Zero |
| **Candidate list with answer** | ✗✗ High | Formula selection | Low |
| **Small cases + derivation** | ✓✓ Minimal | Pattern discovery | High |
| **No hints at all** | ✓✓✓ None | Pure discovery | Maximum |

**Our choice: "Small cases + derivation"**
- Minimal necessary data leakage (small cases only)
- Small cases are independently verified (n=4) or trusted (n=9)
- LLM must discover pattern, not select from list
- Balances rigor with practicality

---

## Production Implications

### For BFS Agent Integration

When integrating this validation approach into the BFS agent:

**DO:**
- ✓ Provide independently verified small cases (n=4→5)
- ✓ Ask LLM to derive formula from pattern
- ✓ Reject obvious wrong formulas (2n-2, n+k)
- ✓ Verify derived formula matches all cases

**DON'T:**
- ✗ Give candidate formula list including correct answer
- ✗ Provide hints that reveal formula structure (e.g., "-3 constant")
- ✗ Show formula derivation from official solution
- ✗ Use ground truth answer to validate intermediate steps

### Validation Philosophy

**Key principle:** The validator should know **constraints** (small cases), not the **solution** (formula).

**Analogy:**
- ✓ "The password must contain 8 characters and include a number" (constraint)
- ✗ "Try these passwords: password1, passw0rd, CorrectPassword123" (solution list)

---

## Lessons Learned

### 1. Subtle Data Leakage is Easy to Miss

Even when trying to avoid data leakage, we accidentally introduced it by providing a candidate list. **Always ask:** "Am I giving the answer in any form?"

### 2. Multiple-Choice ≠ Discovery

Testing formula selection is NOT the same as testing formula discovery. The latter is much harder and more valuable.

### 3. Ground Truth vs Answer

- **Ground truth:** Verified small-case results (n=4→5) ✓
- **Answer:** The formula itself (n+2k-3) ✗

Only provide ground truth, never the answer!

### 4. Validation Source Matters

Document where each verified case comes from:
- `n=4: "verified_independent_cp_sat"` - No circular dependency ✓
- `n=9: "trusted_imo_solution"` - Trusted but not independent ⚠️
- `n=16: "derived_from_formula"` - Circular dependency ✗

---

## Conclusion

**The fix successfully removes data leakage** by:
1. Removing candidate formula list (including correct answer)
2. Asking LLM to derive formula from pattern analysis
3. Only providing verified small-case constraints
4. Pre-rejecting obvious wrong formulas (without revealing answer)

**This creates a legitimate validation test** where:
- LLM must discover mathematical patterns independently
- Success measures true reasoning ability, not formula selection
- Validation is based on independently verified ground truth
- No circular dependency on the formula being validated

**User's feedback was exactly right** - the candidate formula list was indeed data leakage, and removing it makes the test significantly more rigorous and valuable.

---

**Version History:**
- v2.0 (2026-01-06 AM): Candidate formula list approach - LEAKY
- v2.1 (2026-01-06 PM): Formula derivation approach - FIXED

**Files changed:**
- `test_small_case_validation_v2.py`: Removed candidate formulas, updated to derivation mode
- `DATA_LEAKAGE_FIX_REPORT.md`: This document explaining the issue and fix
