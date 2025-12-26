# Option 1 (Fast Fix) - Test Execution Plan

**Date:** 2025-12-26
**Status:** Ready for Testing
**Implementation:** Complete in `code/agent_gpt_oss.py`

---

## Changes Implemented

### File: `code/agent_gpt_oss.py` (lines 1456-1509)

**Change:** Moved construction verification from Level 3 (presentation) to Level 2 (validity) as a mandatory gate check.

**Key Updates:**

1. **New Section Added:** "CRITICAL LEVEL 2 ENHANCEMENT - Justification Completeness (MANDATORY GATE CHECK)"

2. **Strengthened Language:**
   - OLD: "should classify as CRITICAL_ERROR" (suggestive, Level 3)
   - NEW: "You MUST classify as INVALID_METHOD" (imperative, Level 2)

3. **Categorization Change:**
   - OLD: Construction issues were presentation problems (Level 3 - can pass with gaps)
   - NEW: Unjustified existence claims are INVALID METHODS (Level 2 - fail immediately)

4. **Explicit Examples:**
   ```
   INVALID METHODS (trigger Level 2 FAIL):
   ❌ "Construction exists" (zero details)
   ❌ "k=X works" (no equations, no strategy shown)
   ❌ "k=X is achievable" (no construction provided)

   VALID METHODS (proceed to Level 3):
   ✅ "Use lines x=1, x=2, ..., x=n" (explicit specification)
   ✅ "L: y = mx + b where..." (explicit equation)
   ✅ "Line through points (a,b) and (c,d)" (strategy with specific values)
   ```

---

## Test Execution Instructions

### Prerequisites

```bash
# Set OpenRouter API key
export OPENROUTER_API_KEY="sk-or-v1-..."

# Verify environment
python test_option_a_openrouter.py --help
```

### Test Run 1: Single Test (Quick Validation)

**Purpose:** Verify Option 1 fix works on Test 4 (the critical failure case)

```bash
python test_option_a_openrouter.py --test 4 --reasoning high
```

**Expected Results:**
- **Baseline (Before):** verdict="yes" (FALSE POSITIVE)
- **Option 1 (After):** verdict="no" (CORRECT - should catch missing construction)
- **Bug report should contain:** "INVALID METHOD" or "Level 2 FAIL" mention

**Success Criteria:** Test 4 verdict changes from "yes" to "no"

---

### Test Run 2: Full Test Suite (Complete Validation)

**Purpose:** Measure overall accuracy improvement

```bash
python test_option_a_openrouter.py --reasoning high
```

**Expected Results:**

| Metric | Baseline | Option 1 Target | Improvement |
|--------|----------|-----------------|-------------|
| Overall Accuracy | 66.7% (4/6) | **80-85%** (5/6) | +13-18pp |
| Test 1 | ✓ PASS | ✓ PASS | Maintain |
| Test 2 | ✗ FAIL (FN) | ? (May improve) | TBD |
| Test 3 | ✓ PASS | ✓ PASS | Maintain |
| Test 4 | ✗ FAIL (FP) | **✓ PASS** | **CRITICAL FIX** |
| Test 5 | ✓ PASS | ✓ PASS | Maintain |
| Test 6 | ✓ PASS | ✓ PASS | Maintain |

**Key Predictions:**

1. **Test 4 (Missing Constructions):**
   - Current: 0% accuracy (accepted "Construction exists" with no details)
   - Expected: 60-70% accuracy (correctly rejects unjustified existence claims)
   - Improvement: +60-70pp

2. **Test 2 (Alternative Success):**
   - Current: FALSE NEGATIVE (rejected valid proof due to over-strictness)
   - Possible: May still fail if model re-proves despite constraints
   - If passes: Bonus +17pp accuracy

3. **Overall Accuracy:**
   - Conservative: 5/6 = 83.3% (+16.6pp vs baseline)
   - Optimistic: 6/6 = 100% (+33.3pp vs baseline)

**False Positive Rate:**
- Baseline: 33.3% (1/3 FAIL tests incorrectly passed)
- Target: 0% (all FAIL tests correctly rejected)

---

### Test Run 3: Statistical Validation (Optional)

**Purpose:** Achieve statistical significance (Netflix requirement)

```bash
# Run 30 iterations per test (n=180 total)
for i in {1..30}; do
  echo "Iteration $i/30"
  python test_option_a_openrouter.py --reasoning high >> option1_validation.log
  sleep 5
done

# Analyze results
python analyze_option1_results.py option1_validation.log
```

**Statistical Requirements (Netflix Data Scientist):**
- **Minimum n:** 30 per test (n=180 total) for margin of error ±12pp
- **Proper power:** n=154 per test for 80% power to detect +15pp improvement
- **Current state:** n=6 has 2% power, ±37pp margin of error (statistically meaningless)

**Expected Validation:**
- With n=30: 95% CI will narrow from [22%, 96%] to [68%, 98%]
- Can confidently reject null hypothesis (no improvement)

---

## Expected Bug Report Changes

### Test 4 - Before (Baseline):

```
## Automated Checker Warnings

### Coverage
- ⚠️  Coverage claim without verification: Solution claims to cover 'all points'...
- ⚠️  Construction without coverage proof: Lines are constructed but coverage...

**Note:** Verification passed, but automated checkers detected potential issues.
```

**Verdict:** "yes" (PASS) - **WRONG**

---

### Test 4 - After (Option 1 Expected):

```
**Verification Verdict: FAIL**

**Confidence:** 95.0%

**Answer Correctness:** CORRECT

**Reasoning:** The solution gives the correct final answer k∈{0,1,3}, but fails
Level 2 (Method Validity) due to unjustified existence claims. The solution states
"Construction exists" for k=0, k=1, and k=3 without providing explicit constructions,
equations, or verification strategies. This is an INVALID METHOD.

**Issues Found (3):**

1. **[INVALID_METHOD]** (Severity: 9/10)
   - **Location:** For k=0: Construction exists using vertical lines.
   - **Description:** The statement "Construction exists" is unjustified. For FIND
     problems, claiming existence without providing the construction is an INVALID
     METHOD. Required: explicit list of vertical lines or systematic construction
     strategy.

2. **[INVALID_METHOD]** (Severity: 9/10)
   - **Location:** For k=1: Construction exists.
   - **Description:** Unjustified existence claim. Must provide: which sunny line
     to use, which non-sunny lines complement it, verification that all points covered.

3. **[INVALID_METHOD]** (Severity: 9/10)
   - **Location:** For k=3: Construction exists using three sunny lines.
   - **Description:** Unjustified existence claim. Must provide: equations of the
     three sunny lines, coverage verification showing all required points covered.
```

**Verdict:** "no" (FAIL) - **CORRECT**

**Key Difference:** Model now correctly identifies unjustified existence as INVALID
METHOD (Level 2 failure) instead of just warnings (Level 3 acceptable gaps).

---

## Performance Expectations

### Latency Analysis (Nvidia Engineer)

**Current Performance:**
- Test 1: 4.0s ✅ (within target)
- Test 2: 510s ❌ (5× too slow - model re-proving)
- Test 4: 212s ⚠️ (2× target but acceptable)
- Average: 204s
- P95: 315s (5× target of 60s)

**Option 1 Impact on Latency:**
- ✅ Test 4: May reduce from 212s → ~150s (less ambiguity → faster decision)
- ❌ Test 2: Likely still 400-500s (re-proving issue not addressed by Option 1)
- Average: 180-200s (modest 10-20% improvement)

**Recommendation:** If Test 2 remains >400s:
- Use MEDIUM reasoning instead of HIGH (3× faster, 85% accuracy)
- OR proceed to Option 2 (schema enforcement prevents re-proving)

---

## Success Criteria

### Minimum (Ship-blocking if not met):
- ✅ Test 4 accuracy: 0% → **>50%** (Option 1 fixes the critical FP bug)
- ✅ Overall accuracy: 66.7% → **≥80%** (acceptable for production)
- ✅ FP rate: 33.3% → **<20%** (acceptable false positive rate)

### Target (Proceed to Option 2 if met):
- 🎯 Test 4 accuracy: **60-70%**
- 🎯 Overall accuracy: **83-85%**
- 🎯 FP rate: **0-10%**

### Stretch (Skip Option 2 if met):
- 🚀 Test 4 accuracy: **≥80%**
- 🚀 Overall accuracy: **≥90%**
- 🚀 FP rate: **0%**

---

## Next Steps Based on Results

### If Option 1 Succeeds (Accuracy >80%):

**Week 2:** Implement Option 2 (Schema Enforcement)
- Add structured fields for construction tracking
- Programmatic validation in Python (not model-based)
- Target: 88-92% accuracy

**Timeline:** 3 days implementation + 2 days testing

---

### If Option 1 Fails (Accuracy <80%):

**Root Cause Analysis:**
1. Check Test 4 bug report - does it mention INVALID_METHOD?
2. If yes → Model understands but overrides (need schema enforcement)
3. If no → Model doesn't see constraint (increase visibility/repetition)

**Fallback Strategy:**
- Try MEDIUM reasoning (faster, may be more compliant)
- Proceed directly to Option 2 (schema enforcement)
- Consider teacher model (GPT-5) for hybrid approach

---

## Files to Monitor

### Test Results:
```
optionA_openrouter_test_YYYYMMDD_HHMMSS.json  # New results with Option 1
optionA_openrouter_test_20251226_154505.json  # Baseline (66.7% accuracy)
```

### Compare:
```bash
# Baseline
cat optionA_openrouter_test_20251226_154505.json | jq '.accuracy'
# 0.6666666666666666 (66.7%)

# Option 1
cat optionA_openrouter_test_*.json | jq '.accuracy'
# Expected: 0.80-0.85 (80-85%)
```

---

## Technical Notes

### Why This Should Work:

**Expert Consensus (xAI + Netflix + Nvidia + Google):**

1. **Google Scientist Formal Proof:**
   - Construction completeness is a **validity issue** (Level 2)
   - Hierarchical tree says: "Level 1 ✓ + Level 2 ✓ → MUST PASS Level 3"
   - Moving to Level 2 makes it a **gate check** (fail stops processing)

2. **xAI Engineer Analysis:**
   - System prompt (tree structure) > user prompt (constraints)
   - "MUST PASS" (imperative) > "should classify" (suggestive)
   - Solution: Use imperative in Level 2 gate check

3. **Constraint Strength Comparison:**
   - OLD: "should classify as CRITICAL_ERROR" (weak, Level 3)
   - NEW: "You MUST classify as INVALID_METHOD → FAIL Level 2" (strong, gate)

**Architectural Fix:**
```
BEFORE (Failed):
Level 1 (Answer): ✓ Correct
Level 2 (Methods): ✓ Valid (no check for construction)
Level 3 (Presentation): ⚠️ Constraint 7 warns about construction
Tree Rule: "L1 ✓ + L2 ✓ → MUST PASS" → OVERRIDES Level 3 warning → FALSE POSITIVE

AFTER (Option 1):
Level 1 (Answer): ✓ Correct
Level 2 (Methods): ✗ "Construction exists" is INVALID_METHOD → FAIL Level 2
Tree Rule: "L2 ✗ → STOP, return FAIL" → Processing stops → CORRECT REJECTION
```

---

## Commit Message (Ready to Use)

```
Option 1: Move construction verification to Level 2 gate check

Per 4-expert consensus (xAI + Netflix + Nvidia + Google), construction
completeness is a validity issue (Level 2), not a presentation issue (Level 3).

Changes:
- Added "CRITICAL LEVEL 2 ENHANCEMENT" section to verification constraints
- Categorized unjustified existence claims as "INVALID METHODS"
- Strengthened language from "should classify" to "You MUST classify"
- Made construction check a mandatory gate that fails Level 2

Expected Impact:
- Test 4 accuracy: 0% → 60-70% (fixes critical FP bug)
- Overall accuracy: 66.7% → 80-85% (+13-18pp)
- FP rate: 33.3% → 0-10% (-23-33pp)

File: code/agent_gpt_oss.py (lines 1456-1509)
```

---

**Status:** Ready for execution. Run test commands above to validate Option 1 implementation.
