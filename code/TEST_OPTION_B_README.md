# Option B: Full Solution Validation - Test Suite

## Overview

This test suite validates **Option B: Full Solution Validation** - the approach that validates complete proofs instead of just final answers.

**Key principle:** We validate the PROOF is complete, then accept the answer as a logical consequence.

---

## Test File

**File:** `code/test_option_b_full_solution_validation.py`

**Purpose:** Validate that the verification system correctly identifies:
- ✅ Complete proofs → Verification PASSES
- ❌ Incomplete proofs → Verification FAILS
- ❌ Wrong proofs → Verification FAILS

---

## Test Cases

### Test 1: Complete Proof (Real Success - bfs_run2)

**Source:** `bfs_no_answer_validation/bfs_run2_20251223_000814.json`

**Content:** Real successful solution from production test

**Why it should PASS:**
- Complete impossibility proof for k=2 (column counting argument)
- Explicit constructions for k=0, k=1, k=3 with algebraic verification
- Upper bound proof for k≥4
- IMO-level rigorous proof

**Expected result:** Verification PASSES

---

### Test 2: Complete Proof (Alternative Success - bfs_run8)

**Source:** `bfs_no_answer_validation/bfs_run8_20251223_000814.json`

**Content:** Another real successful solution (different approach)

**Why it should PASS:**
- Complete proof using alternative method
- All constructions and impossibility proofs present

**Expected result:** Verification PASSES

---

### Test 3: Incomplete - Missing k=2 Impossibility Proof

**Content:** Synthetic solution with constructions for k=0,1,3 but:
```
k=2: I tried many constructions and couldn't find one. Therefore k=2 doesn't work.
```

**Why it should FAIL:**
- No rigorous impossibility proof for k=2
- Just "couldn't find" is not acceptable at IMO level

**Expected result:** Verification FAILS with keywords: "impossibility", "k=2", "justification"

---

### Test 4: Incomplete - Missing Explicit Constructions

**Content:** Claims constructions exist but doesn't show them:
```
For k=0, construction exists using vertical lines.
For k=1, construction exists.
For k=3, construction exists using three sunny lines.
```

**Why it should FAIL:**
- No explicit line equations provided
- No algebraic verification of coverage

**Expected result:** Verification FAILS with keywords: "construction", "explicit", "justification"

---

### Test 5: Wrong Proof - Incorrect Answer

**Content:** Claims k=2 works (wrong answer) with flawed construction

**Why it should FAIL:**
- k=2 is impossible (ground truth is k ∈ {0,1,3})
- Construction claim is flawed

**Expected result:** Verification FAILS with keywords: "error", "incorrect", "k=2"

---

### Test 6: Justification Gap (Correct Answer)

**Content:** Has correct answer k ∈ {0,1,3} but lacks rigor:
```
All constructions work by the pigeonhole principle and coverage analysis.
```

**Why it should FAIL:**
- Handwaves over proofs
- No explicit constructions shown
- Appeals to "principles" without showing details

**Expected result:** Verification FAILS with keywords: "justification", "gap", "explicit"

---

## How to Run Tests

### Prerequisites

**API Configuration:**
```bash
# Option 1: GPT-OSS local server
export GPT_OSS_API_URL=http://localhost:4000/v1/chat/completions
export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
export GPT_OSS_API_KEY=your_key

# Option 2: OpenAI API
export OPENAI_API_KEY=your_openai_key
```

**Required files:**
- `bfs_no_answer_validation/bfs_run2_20251223_000814.json` (successful run)
- `bfs_no_answer_validation/bfs_run8_20251223_000814.json` (successful run)

---

### Run Full Test Suite

```bash
python code/test_option_b_full_solution_validation.py
```

**Expected output:**
```
================================================================================
OPTION B: FULL SOLUTION VALIDATION - UNIT TESTS
================================================================================

Validating that verification correctly identifies:
  ✓ Complete proofs → PASS
  ✗ Incomplete proofs → FAIL
  ✗ Wrong proofs → FAIL

✓ API key configured: sk-...

================================================================================
Running Test: Test 1: Complete Proof (bfs_run2 - Real Success)
================================================================================
Expected: PASS
...

================================================================================
TEST SUMMARY
================================================================================

✅ PASS | Test 1: Complete Proof (bfs_run2 - Real Success)
  Expected: PASS
  Got: PASS

✅ PASS | Test 2: Complete Proof (bfs_run8 - Alternative Success)
  Expected: PASS
  Got: PASS

✅ PASS | Test 3: Incomplete - Missing k=2 impossibility proof
  Expected: FAIL
  Got: FAIL
  Keyword checks:
    ✓ impossibility: True
    ✓ k=2: True
    ✓ justification: True

✅ PASS | Test 4: Incomplete - Missing explicit constructions
  Expected: FAIL
  Got: FAIL
  Keyword checks:
    ✓ construction: True
    ✓ explicit: True
    ✓ justification: True

✅ PASS | Test 5: Wrong Proof - Incorrect answer (includes k=2)
  Expected: FAIL
  Got: FAIL
  Keyword checks:
    ✓ error: True
    ✓ incorrect: True
    ✓ k=2: True

✅ PASS | Test 6: Proof with Justification Gap
  Expected: FAIL
  Got: FAIL
  Keyword checks:
    ✓ justification: True
    ✓ gap: True
    ✓ explicit: True

================================================================================
RESULTS: 6/6 tests passed (100.0%)
================================================================================

✅ ALL TESTS PASSED

Option B (Full Solution Validation) is working correctly!
  ✓ Complete proofs are accepted
  ✓ Incomplete proofs are rejected
  ✓ Wrong proofs are rejected

System is production-ready for problems with/without ground truth.
```

---

## Interpretation of Results

### Success Criteria

**6/6 tests passed:**
- ✅ Both real successful solutions (bfs_run2, bfs_run8) pass verification
- ✅ All 4 incomplete/wrong solutions fail verification
- ✅ Verification identifies specific gaps in failed solutions

**Conclusion:** Option B is working correctly. The system can validate proofs without relying on ground truth.

---

### Partial Success

**4-5/6 tests passed:**
- If Test 1 or Test 2 fail: Verification may be too strict (rejects valid proofs)
- If Tests 3-6 pass (when they should fail): Verification too lenient (accepts weak proofs)

**Action:** Review `verification_system_prompt` and adjust rigor level.

---

### Failure

**<4 tests passed:**
- Verification system not working as expected
- Review API configuration
- Check if verification prompts are being used correctly

---

## What This Validates

### 1. Ground Truth Independence

**Tests 1-2 validate:** System accepts complete proofs even without checking ground truth.

**Evidence:** If both tests pass, verification alone is sufficient to validate IMO-level proofs.

---

### 2. Proof Quality Detection

**Tests 3-6 validate:** System rejects incomplete/weak proofs.

**Evidence:** If these fail as expected, verification is rigorous and catches gaps.

---

### 3. Production Readiness

**All tests passing validates:**
- ✅ System works for problems with ground truth (IMO01)
- ✅ System works for problems without ground truth (IMO02, future problems)
- ✅ No false positives (weak proofs rejected)
- ✅ No false negatives (complete proofs accepted)

---

## Next Steps After Testing

### If All Tests Pass

1. **Run production test on IMO02** (no ground truth in database)
   ```bash
   python code/agent_gpt_oss.py problems/imo02.txt --log test_imo02.log
   ```

2. **Validate success detection message**
   - Should see: "✅ VERIFICATION PASSED (NO GROUND TRUTH)"
   - Should NOT see: "✅ CORRECT SOLUTION FOUND (HIGH CONFIDENCE)"

3. **Run parallel test on IMO02**
   ```bash
   MAX_PARALLEL=12 ./run_bfs_baseline.sh problems/imo02.txt bfs_imo02_option_b
   ```

4. **Compare results**
   - IMO01 success rate: ~17% (2/12 in bfs_no_answer_validation)
   - IMO02 should have similar rate (complete proofs are equally rare)

---

### If Tests Fail

1. **Review verification_system_prompt** (code/agent_oai.py)
   - Check if Section 4 (Completeness) is enforced
   - Check if Section 5 (Construction Verification) is enforced

2. **Check API configuration**
   - Verify correct model is being used
   - Check reasoning effort (should be "medium" or "high" for tests)

3. **Review individual test failures**
   - If Test 1/2 fail: Verification too strict
   - If Test 3-6 pass: Verification too lenient

---

## Comparison with Option A

### Option A Test Results (Abandoned)

**File:** `code/test_verification_construction_requirements.py`

**Results:** 1/6 tests passed (16.7%)

**Why it failed:**
- Tried to validate answers by checking for construction mentions
- Verification is fuzzy - can't distinguish claim quality
- Test 5 PASSED when it should fail (accepted claim without construction)

---

### Option B Test Results (Current)

**File:** `code/test_option_b_full_solution_validation.py`

**Expected results:** 6/6 tests pass (100.0%)

**Why it works:**
- Validates complete proofs (not just answers)
- Uses real successful solutions as gold standard
- Tests proof quality, not claim existence

---

## Documentation

**Related files:**
- `OPTION_A_FUNDAMENTAL_LIMITATION.md` - Why Option A failed
- `OPTION_B_FULL_SOLUTION_VALIDATION.md` - How Option B works
- `TEST_FAILURE_ANALYSIS_AND_FIX.md` - Bug fixes for Option A tests

**Key insight:**
> Ground truth is for confidence measurement, not validation.
> Trust the proof, accept the answer.
