# Option A OpenRouter Testing - Detailed Analysis

**Date:** 2025-12-26
**Model:** openrouter/openai/gpt-oss-120b (HIGH reasoning)
**Constraints:** Option A (7 critical guidelines) ENABLED

---

## Executive Summary

❌ **Option A constraints did NOT improve verification accuracy**

**Results:**
- **Accuracy:** 66.7% (4/6 correct)
- **False Positive Rate:** 33.3% (1/3 FAIL tests)
- **False Negative Rate:** 33.3% (1/3 PASS tests)
- **Average Output:** 920 chars (~230 tokens) ✅ Well under limit

**Comparison to Baseline:**
- **Option 1 (MEDIUM, no constraints):** 78.3% accuracy
- **Option A (HIGH + constraints):** 66.7% accuracy
- **Difference:** **-11.6pp (WORSE!)**

---

## Per-Test Breakdown

### ✅ Test 1: Complete Proof (bfs_run2) - CORRECT

**Result:** PASS (expected PASS) ✓
**Time:** 4.0s
**Bug Report:** 378 chars

**Analysis:**
- Model correctly accepted complete, valid proof
- Very short output (constraints working for output length)
- Only minor warning about coverage verification
- **Verdict: Constraints working as intended**

---

### ❌ Test 2: Complete Proof (bfs_run8) - FALSE NEGATIVE

**Result:** FAIL (expected PASS) ✗
**Time:** 510.3s (very slow - model struggled)
**Bug Report:** 1703 chars

**Critical Error Found by Model:**
> "The statement that *only* the three lines y=x, y=-2x+5, and y=-½x+5/2 can attain the maximal number of points... is false. For any odd k the lines y=x and y=-2x+(k+2) both achieve the bound... Consequently the claim that exactly three lines achieve the bound is incorrect, and the deduction that k must be at most 3 based on this claim is not logically sound."

**Analysis:**
- Model found subtle error in intermediate reasoning about uniqueness
- **Answer is CORRECT (k∈{0,1,3})**
- But model rejected due to flawed intermediate claim
- **Problem:** Constraints 2-4 failed to prevent over-analysis
  - Constraint 2: "Evaluate, Don't Re-Prove" - ignored
  - Constraint 4: "Trust Valid Methods" - ignored
- Model re-proved uniqueness claim and found flaw
- **This is being OVER-STRICT despite constraints**

**Root Cause:** gpt-oss-120b may not follow constraints as strictly as expected, or hierarchical decision tree overrides constraint guidance.

---

### ✅ Test 3: Missing k=2 Proof - CORRECT

**Result:** FAIL (expected FAIL) ✓
**Time:** 7.1s
**Bug Report:** 1066 chars

**Critical Error Found:**
> "The impossibility claim for k=2 is based solely on trial-and-error ('I tried many constructions and couldn't find one'), which is not a valid mathematical argument."

**Analysis:**
- Correctly identified trial-and-error as invalid method
- **Level 2 checking working properly**
- Constraint 2 working: didn't try to re-prove k=2 impossibility
- **Verdict: Constraints working correctly**

---

### ❌ Test 4: Missing Explicit Constructions - FALSE POSITIVE (CRITICAL!)

**Result:** PASS (expected FAIL) ✗
**Time:** 212.3s
**Bug Report:** 849 chars

**What Model Said:**
- Gave WARNINGS: "Construction without coverage proof"
- Gave WARNINGS: "Coverage claim without verification"
- **But verdict: PASS** ✗

**Solution Text (Test 4):**
```
For k=0, we can use non-sunny lines (verticals, horizontals, or slope -1).
Construction exists using vertical lines.

For k=1, we can use 1 sunny line with (n-1) non-sunny lines.
Construction exists.

For k=3, construction exists using three sunny lines.
```

**What Should Have Happened per Constraint 7:**
> "If the problem asks to 'find' or 'determine' values, and the solution claims 'k=X is achievable/possible':
> - ✅ PASS: Solution provides EXPLICIT construction with specific values/coordinates/equations
> - ❌ FAIL: Solution only states existence without showing concrete construction
>   Example: 'k=3 is possible' or 'k=3 exists' (no explicit construction shown)
> - Abstract existence proofs WITHOUT explicit examples should be classified as CRITICAL_ERROR"

**Analysis:**
- **CONSTRAINT 7 COMPLETELY FAILED**
- Solution says "Construction exists" with ZERO details
- This is exactly the pattern Constraint 7 was designed to catch
- Model gave warnings but still passed
- **100% FALSE POSITIVE on the exact case Constraint 7 targets**

**Why It Failed:**
1. Model treats constraints as "guidance" not "enforcement"
2. Structured JSON output may prioritize verdict over constraints
3. Hierarchical decision tree's "Level 3 gaps acceptable" may override Constraint 7
4. gpt-oss-120b may interpret constraints differently than o3

---

### ✅ Test 5: Wrong Answer - CORRECT

**Result:** FAIL (expected FAIL) ✓
**Time:** 315.9s
**Bug Report:** 1147 chars

**Critical Error Found:**
> "The solution claims k=2 is achievable... but that construction fails to cover three required points... Hence k=2 is impossible, making the final answer wrong."

**Analysis:**
- Correctly identified wrong answer
- Correctly verified construction failure
- HIGH reasoning working for answer verification
- **Verdict: Answer checking working properly**

---

### ✅ Test 6: Justification Gap - CORRECT

**Result:** PASS (expected PASS) ✓
**Time:** 172.8s
**Bug Report:** 378 chars

**Analysis:**
- Correctly accepted proof with minor justification gaps
- Short output (constraints working)
- Level 3 "gaps acceptable" policy working
- **Verdict: Constraints working as intended**

---

## Aggregate Analysis

### Performance Metrics

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| **Overall Accuracy** | 66.7% | 88-92% | ❌ FAIL (-21-25pp) |
| **False Positive Rate** | 33.3% | 5-10% | ❌ FAIL (3× worse) |
| **False Negative Rate** | 33.3% | 5-8% | ❌ FAIL (4-7× worse) |
| **Output Length** | ~230 tokens | <2000 tokens | ✅ PASS |
| **Test 4 Accuracy** | 0% | 60-70% | ❌ FAIL (100% FP) |
| **Test 5 Accuracy** | 100% | ≥95% | ✅ PASS |

### Per-Category Results

**PASS Tests (should accept):**
- Test 1: ✅ PASS (correct)
- Test 2: ❌ FAIL (false negative - over-strict)
- Test 6: ✅ PASS (correct)
- **Result:** 2/3 correct (66.7%)
- **FN Rate:** 33.3%

**FAIL Tests (should reject):**
- Test 3: ✅ FAIL (correct)
- Test 4: ❌ PASS (false positive - constraint 7 failed)
- Test 5: ✅ FAIL (correct)
- **Result:** 2/3 correct (66.7%)
- **FP Rate:** 33.3%

---

## Comparison to Baseline

### vs Option 1 (MEDIUM reasoning, no constraints)

| Test | Option 1 (MEDIUM) | Option A (HIGH + constraints) | Change |
|------|-------------------|-------------------------------|---------|
| **Overall** | 78.3% | 66.7% | **-11.6pp** ❌ |
| Test 1 | 40-85% | 100% (1/1) | +15-60pp ✓ |
| Test 2 | 95-100% | 0% (0/1) | -95-100pp ❌ |
| Test 3 | 95-100% | 100% (1/1) | 0-5pp ≈ |
| Test 4 | 30-35% (65-70% FP) | 0% (100% FP) | **-30-35pp** ❌ |
| Test 5 | 70-100% | 100% (1/1) | 0-30pp ✓ |
| Test 6 | 55-80% | 100% (1/1) | +20-45pp ✓ |

**Key Finding:** Option A constraints made performance WORSE overall, despite improving some individual tests.

---

## Root Cause Analysis

### Why Constraint 7 Failed (Test 4)

**Constraint 7 Text:**
```
7. Construction Verification (for FIND/DETERMINE problems):
   - If solution claims "k=X is achievable/possible":
     - ✅ PASS: Explicit construction with values/coordinates/equations
     - ❌ FAIL: Only states existence without construction
   - Abstract existence proofs WITHOUT explicit examples should be
     classified as CRITICAL_ERROR for FIND problems
```

**What Happened:**
1. Solution said "Construction exists" (exact negative example pattern)
2. Model generated warnings: "Construction without coverage proof"
3. **But verdict: PASS** (should be FAIL)

**Possible Reasons:**

1. **Constraint Interpretation:**
   - Model treats constraints as "suggestions" not "requirements"
   - Warnings generated but don't trigger FAIL verdict
   - May need stronger enforcement language

2. **Hierarchical Decision Tree Override:**
   - System prompt has hierarchical decision tree
   - Level 3 says "gaps are acceptable"
   - Tree may override constraint enforcement

3. **Structured JSON Output:**
   - Uses structured schema for verdict
   - Schema may prioritize Level 1-2 gates over Constraint 7
   - Constraint 7 is Level 3 (presentation), which tree says is acceptable

4. **Model-Specific Behavior:**
   - gpt-oss-120b may interpret constraints differently than o3
   - May need model-specific constraint tuning

---

### Why Over-Strict on Test 2 (False Negative)

**Constraints 2-4 Text:**
```
2. Evaluate, Don't Re-Prove: Don't re-prove from scratch
3. No Manual Case Testing: Don't re-enumerate cases
4. Trust Valid Methods: Accept valid methods + correct answer
```

**What Happened:**
1. Solution used valid methods (case analysis, counting)
2. Answer was CORRECT (k∈{0,1,3})
3. But model re-proved intermediate uniqueness claim
4. Found subtle error in reasoning
5. **Rejected despite constraints saying to trust valid methods**

**Why:**
- Model's rigorous verification instinct overrode constraint guidance
- HIGH reasoning may naturally tend toward deep analysis
- Constraints not strong enough to prevent re-proving
- Hierarchical tree allows Level 3 analysis even with correct answer

---

## Key Findings

### 1. Output Length: ✅ SUCCESS

- **Average:** 920 chars (~230 tokens)
- **Target:** <2000 tokens
- **Result:** 88% reduction ✓
- **Constraint 1 working perfectly**

### 2. Construction Verification: ❌ CRITICAL FAILURE

- **Test 4 designed specifically for Constraint 7**
- **Result:** 100% FALSE POSITIVE
- **Constraint 7 completely ineffective**
- **Worse than baseline (30-35% → 0% accuracy)**

### 3. Over-Analysis Prevention: ❌ PARTIAL FAILURE

- **Test 2 shows constraints 2-4 insufficient**
- Model still re-proves intermediate claims
- HIGH reasoning tendency overrides constraint guidance

### 4. Answer Verification: ✅ SUCCESS

- **Test 5 correctly caught wrong answer**
- HIGH reasoning effective for correctness checking
- 100% accuracy on wrong answer detection

### 5. Gap Tolerance: ✅ SUCCESS

- **Tests 1, 6 correctly accepted with minor gaps**
- Level 3 "gaps acceptable" working
- Not being overly strict on presentation

---

## Conclusions

### Performance vs Expectations

**Expected (Option A with o3):**
- Accuracy: 88-92%
- Test 4: 60-70% (from 30-35%)
- FP Rate: 5-10%

**Actual (OpenRouter gpt-oss-120b):**
- Accuracy: 66.7% ❌
- Test 4: 0% (from 30-35%) ❌
- FP Rate: 33.3% ❌

**Verdict: Option A constraints did NOT work as intended on gpt-oss-120b**

---

### Why Constraints Failed

1. **Model Behavior Difference:**
   - gpt-oss-120b interprets constraints as guidance, not enforcement
   - Generates warnings but doesn't enforce FAIL verdicts
   - Different from expected o3 behavior

2. **Hierarchical Tree Dominance:**
   - Decision tree's "Level 3 gaps acceptable" overrides Constraint 7
   - Construction completeness treated as Level 3 (presentation)
   - Should be Level 1 or Level 2 (gate check)

3. **Insufficient Constraint Strength:**
   - Current phrasing allows model discretion
   - Need stronger "MUST" language for enforcement
   - Need explicit verdict requirements, not just guidance

4. **Structured Output Schema:**
   - JSON schema may not align with constraint enforcement
   - Warnings vs verdicts separation
   - Schema needs constraint violation → FAIL mapping

---

## Recommendations

### For Production Deployment: ❌ DO NOT DEPLOY

**Reasons:**
1. Accuracy (66.7%) below minimum threshold (85%)
2. FP rate (33.3%) 3× worse than target (5-10%)
3. Test 4 has 100% FP (critical construction verification failure)
4. Performance worse than baseline Option 1 (78.3%)

**Verdict: NOT READY FOR PRODUCTION**

---

### Next Steps

#### Option 1: Fix Constraint Implementation for gpt-oss-120b

**Changes Needed:**
1. Move construction verification to Level 1 or Level 2 (make it a gate check)
2. Strengthen constraint language: "You MUST classify as FAIL" instead of "should be"
3. Map constraint violations directly to verdict in schema
4. Remove "warnings" mechanism - violations = FAIL

**Effort:** 1-2 days
**Expected Impact:** +20-30pp accuracy
**Risk:** May increase FN rate if too strict

#### Option 2: Test with Different OpenRouter Model

**Try:**
- `anthropic/claude-3.5-sonnet` (better instruction following)
- `openai/gpt-4-turbo` (more consistent with constraints)

**Effort:** 2 hours
**Expected Impact:** Unknown
**Risk:** May have different failure modes

#### Option 3: Wait for OpenAI o3 API Access ✅ RECOMMENDED

**Rationale:**
- Original Option A implementation in `agent_oai.py` ready
- Designed specifically for o3 behavior
- Expected 88-92% accuracy (validated in analysis)
- No adaptation/tuning needed
- gpt-oss-120b results suggest model-specific tuning required

**Timeline:** Ready to test when o3 API available
**Risk:** Low (original design target)

---

## Technical Lessons Learned

1. **Constraints are model-specific:**
   - What works for o3 may not work for gpt-oss-120b
   - Need model-specific validation before deployment

2. **Guidance vs Enforcement:**
   - Current constraints are "guidance"
   - Need explicit enforcement mechanisms for some models
   - Schema design affects constraint adherence

3. **Hierarchical vs Flat Rules:**
   - Hierarchical decision tree can override flat constraints
   - Need alignment between tree and constraints
   - Construction completeness should be gate check, not Level 3

4. **Output Length Success:**
   - Token limits work well across models
   - Clear, measurable constraints are effective
   - Behavioral constraints (like "trust valid methods") harder to enforce

---

## Files for Reference

- Test Results: `optionA_openrouter_test_20251226_154505.json`
- Implementation: `code/agent_gpt_oss.py` (lines 1456-1491)
- Test Script: `test_option_a_openrouter.py`

---

**Status:** Testing complete, Option A constraints NOT effective on gpt-oss-120b
**Recommendation:** Wait for OpenAI o3 API to test original Option A implementation
**Alternative:** Redesign constraints specifically for gpt-oss-120b behavior
