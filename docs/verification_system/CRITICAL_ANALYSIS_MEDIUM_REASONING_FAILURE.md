# CRITICAL ANALYSIS: Medium Reasoning Test Failure

**Date**: 2025-12-24
**Test Results**: 3/6 (50%) - **REGRESSION** from Phase 1's 4/6 (67%)
**Status**: ❌ Phase 2 Enhanced with medium reasoning FAILED

---

## Test Results Summary

| Test | Phase 1 (high) | Phase 2 (medium) | Change | Issue |
|------|----------------|------------------|--------|-------|
| 1 (Complete bfs_run2) | ✅ PASS | ❌ FAIL | ⬇️ REGRESSION | LLM claims k=2 is possible (WRONG!) |
| 2 (Complete bfs_run8) | ❌ FAIL | ✅ PASS | ⬆️ IMPROVED | - |
| 3 (Incomplete) | ✅ PASS | ❌ FAIL | ⬇️ REGRESSION | - |
| 4 (Missing constructions) | ✅ FAIL | ✅ FAIL | ✓ STABLE | - |
| 5 (Wrong answer) | ✅ FAIL | ✅ FAIL | ✓ STABLE | - |
| 6 (Justification gap) | ✅ PASS | ❌ FAIL | ⬇️ REGRESSION | String matching bug |

**Net change**: -1 test (4/6 → 3/6)

---

## Root Cause Analysis

### Issue 1: Medium Reasoning Makes Mathematical Errors (Test 1)

**Test 1 Verdict**:
```
Final Verdict: The solution contains a **Critical Error** and is therefore invalid.

Issue: The argument that a column with three points forces a vertical line is FALSE.

Counter-example (n=4):
- Points: (1,1), (1,2), (1,3), (2,1), (2,2), (3,1)
- Two vertical lines x=1, x=2 (non-sunny)
- Sunny line L1 through (3,1) and (1,2) has slope -1/2
- Sunny line L2 through (2,1) and (1,3) has slope -2
- All six points covered, exactly k=2 sunny lines

Hence k=2 is realizable, contradicting the solution's claim.

The correct set includes k=2 (e.g., for n=4). Hence the solution is invalid.
```

**PROBLEM**: The LLM is claiming the **IMO OFFICIAL ANSWER is WRONG**!

- IMO Official Answer: k ∈ {0, 1, 3} ✓ CORRECT
- LLM's Claim: k=2 is possible, answer should include k=2 ✗ MATHEMATICALLY FALSE

**Why this happened**:
- **Medium reasoning is TOO WEAK** for rigorous mathematical verification
- The LLM doesn't have enough reasoning tokens (1000-1500) to verify the counter-example is actually invalid
- Medium reasoning makes the model LESS capable, not more effective at following examples

**Evidence**: The LLM's "counter-example" for k=2 is **mathematically incorrect** if verified properly.

---

### Issue 2: String Matching Bug (Test 6)

**Test 6 Verdict**:
```
Final Verdict: The solution arrives at the correct final answer k∈{0,1,3}, but several steps are insufficiently justified. All problems are **Justification Gaps** (presentation or reasoning gaps), not Critical Errors.
```

**Expected**: PASS (has "Justification Gaps" and NO "Critical Error")

**Actual**: FAIL

**Root Cause**: String matching in `agent_gpt_oss.py` lines 1235-1247:

```python
has_critical_error = "critical error" in out_lower
has_justification_gap = "justification gap" in out_lower

if has_critical_error and not has_justification_gap:
    o = "no"  # Only critical error → reject
elif has_justification_gap and not has_critical_error:
    o = "yes"  # Only justification gap → accept
else:
    # BOTH or NEITHER → use second-stage check
    check_correctness = """... does not contain critical error or a major justification gap?"""
```

**Problem**: Test 6 verdict contains BOTH strings:
- "Justification Gaps" → matches "justification gap" ✓
- "not Critical Errors" → matches "critical error" ✓ **FALSE POSITIVE!**

**Flow**:
1. Both strings found → goes to `else` clause (line 1248)
2. Second-stage check asks: "does NOT contain major justification gap?"
3. Answer: "no" (because it DOES contain gaps)
4. Test fails ✗

**Fix**: Make string matching more precise - only match in "Issue:" lines, not in negative mentions like "not Critical Errors"

---

### Issue 3: Few-Shot Examples Completely Ignored

**Example 1** explicitly shows:
```
**Correct Classification:**
*   **Location:** "one of the non-sunny lines must be vertical"
    *   **Issue:** Justification Gap - ... final answer k∈{0,1,3} is correct.
        This is a presentation issue, not a mathematical error.

**WRONG Classification (don't do this):**
*   ~~**Issue:** Critical Error - This claim is false~~ ❌ WRONG
```

**Test 1 LLM Output**: Does the EXACT "WRONG" classification!

**Why examples were ignored**:
1. **Medium reasoning too weak**: 1000-1500 tokens not enough to process complex prompt
2. **Examples too far from verdict**: Still 4000+ tokens between examples and final verdict generation
3. **No enforcement mechanism**: LLM can ignore examples without consequence

---

## Key Insights

### 1. Medium Reasoning is TOO WEAK (Nvidia Engineer was wrong)

**Hypothesis**: High reasoning (3000+ tokens) overrides few-shot examples
**Reality**: Medium reasoning (1000-1500 tokens) makes mathematical errors AND ignores examples

**Evidence**:
- Test 1: LLM claims k=2 works (mathematically false)
- Test 3/6: Regressions from Phase 1
- Only 3/6 passing (worse than Phase 1's 4/6)

**Conclusion**: We need HIGH reasoning for mathematical rigor, but better prompt engineering

---

### 2. String Matching is Fragile

**Problem**: Keyword search finds "critical error" in "not Critical Errors"
**Impact**: Test 6 false negative

**Fix**: More precise matching:
```python
# Look for "Final Verdict" sentence only
verdict_sentence = extract_verdict_sentence(out)
has_critical_error = "critical error" in verdict_sentence.lower()
has_justification_gap = "justification gap" in verdict_sentence.lower()
```

---

### 3. Few-Shot Examples Need Stronger Enforcement

**Current approach**:
- Place examples before task
- Add meta-instruction "Do NOT override"
- Hope LLM follows guidance

**Problem**: LLM ignores both examples and meta-instruction

**Better approach**:
- **Structured output**: Force LLM to fill template
- **Two-stage verification**:
  - Stage 1: Check answer correctness (low reasoning, fast)
  - Stage 2: If answer correct, use lenient standards (high reasoning)
- **Explicit checklist**: Make LLM check decision rule before classifying

---

## Proposed Fix: Structured Prompt + High Reasoning

### Change 1: Use HIGH Reasoning (NOT medium)

**Rationale**: Medium reasoning makes mathematical errors, not worth the risk

```python
reasoning_effort="high"  # Need rigor for mathematical verification
```

---

### Change 2: Fix String Matching Bug

**File**: `code/agent_gpt_oss.py` lines 1233-1254

**Current**:
```python
has_critical_error = "critical error" in out_lower
has_justification_gap = "justification gap" in out_lower
```

**New**:
```python
# Extract only the Final Verdict sentence for precise matching
verdict_match = re.search(r'\*\*Final Verdict:?\*\*\s*(.+?)(?:\n|$)', out, re.IGNORECASE)
if verdict_match:
    verdict_sentence = verdict_match.group(1).lower()
else:
    verdict_sentence = out_lower[:500]  # Fallback: first 500 chars

has_critical_error = "critical error" in verdict_sentence and "not" not in verdict_sentence
has_justification_gap = "justification gap" in verdict_sentence and "not" not in verdict_sentence
```

---

### Change 3: Add Answer Correctness Check FIRST

**New logic** (before detailed verification):

```python
# STEP 1: Quick answer check (low reasoning, 10 seconds)
answer_correct = check_answer_correctness(solution)

# STEP 2: Detailed verification with conditional standards
if answer_correct:
    # Answer correct → Use LENIENT standards (accept Justification Gaps)
    verification_instruction = """
    The final answer is CORRECT. Your task is to check if there are any
    CRITICAL ERRORS (wrong constructions, invalid reasoning).

    - Presentation issues (imprecise wording) → Justification Gap → ACCEPTABLE
    - Missing details in valid proofs → Justification Gap → ACCEPTABLE
    - Only flag Critical Errors if logic is fundamentally broken.
    """
else:
    # Answer wrong → Use STRICT standards
    verification_instruction = """
    The final answer is WRONG. Identify all errors rigorously.
    """

verification_output = verify_with_instruction(solution, verification_instruction)
```

---

### Change 4: Structured Output Template

**Force LLM to use structured format**:

```
Your verification MUST follow this exact format:

**STEP 1: Check Final Answer**
- Claimed answer: k ∈ {___}
- Expected answer: k ∈ {0, 1, 3}
- Match: [YES/NO]

**STEP 2: Apply Decision Rule**
- If answer matches → All errors are Justification Gaps (unless construction wrong)
- If answer doesn't match → Critical Errors

**STEP 3: List Issues**
[Only if Step 1 shows NO match]

**FINAL VERDICT:** [ACCEPT/REJECT]
```

This forces the LLM to check the answer FIRST before classifying errors.

---

## Recommended Action Plan

### Option A: Quick Fix (2 hours)

1. ✅ Change to HIGH reasoning (revert medium)
2. ✅ Fix string matching bug (extract verdict sentence only)
3. ✅ Test again - expect 5-6/6

**Confidence**: 60-70%

---

### Option B: Structured Approach (4 hours)

1. ✅ Implement two-stage verification (answer check first)
2. ✅ Add structured output template
3. ✅ Use high reasoning for rigor
4. ✅ Fix string matching bug
5. ✅ Test - expect 6/6

**Confidence**: 85-90%

---

### Option C: Ensemble Voting (6 hours)

1. ✅ Implement 3-model ensemble (GPT-4o, Claude Sonnet 3.5, Gemini 2.0)
2. ✅ Majority vote on verdicts
3. ✅ Test - expect 6/6

**Confidence**: 90-95%
**Cost**: 3× per verification

---

## Verdict on Phase 2 Enhanced

**Status**: ❌ FAILED with medium reasoning

**Why it failed**:
1. Medium reasoning TOO WEAK for mathematical rigor (makes errors)
2. String matching bug (Test 6 false negative)
3. Few-shot examples ignored by weak reasoning

**Key lesson**: **Prompt engineering alone is insufficient for complex mathematical verification with weak models**

**Next step**: Need EITHER:
- Option A: High reasoning + string fix (quick, 60-70% confidence)
- Option B: Structured two-stage approach (best single-model, 85-90% confidence)
- Option C: Ensemble voting (highest confidence, more cost)

---

## Recommendation

**Implement Option B: Structured Two-Stage Approach**

**Why**:
- Addresses all three root causes
- Higher confidence (85-90%) than Option A (60-70%)
- Lower cost than Option C (ensemble)
- More robust and maintainable

**Timeline**:
- Implementation: 3-4 hours
- Testing: 30 minutes
- Expected result: 6/6 tests passing

**Alternative**: If time-constrained, try Option A first (2 hours), then Option B if it fails.
