# CRITICAL FIX: Ground Truth Leakage in Answer Validation

**Date**: 2025-12-23
**Status**: ✅ FIXED (commit 4f50919)
**Severity**: CRITICAL - Invalidates all previous test results

---

## The Problem

**User discovered**: Answer validator was **injecting ground truth into LLM feedback**.

### Example from bfs_run1_20251222_213001.log:

```json
{
    "role": "user",
    "content": "Below is the bug report...

    **ANSWER INCOMPLETE**

    Your answer is correct but incomplete.
    Missing: {0, 1, 3}    ← LITERALLY TELLS THE ANSWER!
    ..."
}
```

### Impact

```
Contaminated runs: 12/12 (100%)
Valid runs: 0/12 (0%)
```

**ALL results from bfs_validation_test are INVALID**:
- ❌ Reported "33.3% success" is meaningless
- ❌ LLM didn't solve the problem - it copied leaked answers
- ❌ "Failed runs lost the answer" - they saw it, tried to rewrite it, mangled it
- ❌ Cannot compare to expert predictions (contaminated data)

---

## Ground Truth Leakage Locations (ALL REMOVED)

### 1. WRONG/OVERGENERALIZED Verdict (Lines 1350-1356)

**BEFORE** (LEAKED):
```python
bug_report = f"**ANSWER VALIDATION FAILED**\n\n" + \
            f"Verdict: {answer_result['verdict']}\n" + \
            f"Claimed answer: {claimed_ans}\n" + \
            f"Correct answer: {correct_ans}\n\n" + \  # ← LEAKS GROUND TRUTH
            f"Reason: {details.get('reason')}\n\n" + \
            bug_report
```

### 2. CORRECT Verdict (Lines 1366-1375)

**BEFORE** (LEAKED):
```python
bug_report = f"**ANSWER IS CORRECT**\n\n" + \
            f"Your final answer matches the ground truth: {details.get('correct')}\n" + \  # ← LEAKS
            f"However, the proof verification found issues (see below).\n\n" + \
            bug_report
```

### 3. INCOMPLETE Verdict (Lines 1377-1388)

**BEFORE** (LEAKED):
```python
bug_report = f"**ANSWER INCOMPLETE**\n\n" + \
            f"Your answer is correct but incomplete.\n" + \
            f"Missing: {missing}\n\n" + \  # ← TELLS WHAT'S MISSING!
            bug_report
```

### 4. PRE-VERIFICATION ENFORCEMENT (Lines 1366-1399)

**BEFORE** (LEAKED):
```python
targeted_prompt = """**PRE-VERIFICATION ENFORCEMENT**

✅ Your final answer is CORRECT!  # ← TELLS LLM IT'S CORRECT!

However, your proof lacks explicit point-by-point verification...
"""
bug_report = targeted_prompt + bug_report
```

---

## The Fix

### New Architecture: Measurement-Only Validation

```
┌─────────────────────────────────────────────────────────┐
│ DURING SOLVING (No Ground Truth!)                      │
├─────────────────────────────────────────────────────────┤
│ 1. LLM generates solution                              │
│ 2. Proof verifier checks logical validity → good/bad  │
│ 3. If bad: feedback on LOGICAL errors only            │
│ 4. If good + agent believes complete → STOP           │
│                                                         │
│ ❌ NO ANSWER VALIDATION IN THE LOOP!                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ AFTER COMPLETION (Offline Measurement)                 │
├─────────────────────────────────────────────────────────┤
│ 1. Extract final answer from solution                  │
│ 2. Compare to ground truth (offline)                   │
│ 3. Record: CORRECT / INCOMPLETE / WRONG                │
│ 4. Compute success rate for experiment                 │
│                                                         │
│ ✅ Results logged but NEVER fed back to LLM            │
└─────────────────────────────────────────────────────────┘
```

### Code Changes (commit 4f50919)

**1. agent_gpt_oss.py (lines 1310-1369)**

```python
# ANSWER VALIDATION (2025-12-23 FIX):
# Run validation for MEASUREMENT ONLY - DO NOT feed results back to LLM
answer_is_correct = False  # Track for "Correct solution found" marker only

try:
    from answer_validator import AnswerValidator, extract_final_answer

    validator = AnswerValidator(problem_id)
    claimed_answer = extract_final_answer(solution)

    if claimed_answer:
        answer_result = validator.validate(claimed_answer, solution)

        # CRITICAL: Only use for internal tracking, NOT for bug_report feedback
        if answer_result["verdict"] == "CORRECT":
            answer_is_correct = True
        else:
            answer_is_correct = False

        # DO NOT modify bug_report based on answer validation
        # DO NOT override verification verdict (o) based on answer
        # Let the LLM self-discover the answer without hints
```

**2. validate_runs_offline.py (NEW)**

Offline validation script that:
- ✅ Extracts final answer from completed logs
- ✅ Compares to ground truth (no LLM feedback)
- ✅ Generates validation_results.json
- ✅ Computes true success rate

**Usage**:
```bash
python validate_runs_offline.py bfs_validation_test/
```

---

## Why This Is The Only Correct Approach

### Alternative Approaches Considered (All Rejected)

❌ **"Give generic feedback without ground truth"**
```python
bug_report = "Your answer is incomplete. Test k=0,1,2,3,... systematically"
```
**Problem**: Still reveals answer is not {0,1,3}, enables hill-climbing

❌ **"Only tell them INCOMPLETE/WRONG, no details"**
```python
bug_report = "INCOMPLETE"
```
**Problem**: Signals they haven't found {0,1,3} yet, guides search

❌ **"Stop when correct but don't tell them"**
**Problem**: Stopping behavior itself is a signal

### Why CoT Verification is Sufficient

✅ **Proof verification checks**: "Is the REASONING logically sound?"
- Doesn't reveal the answer
- Tests mathematical rigor
- Catches logical errors
- Sufficient for quality control

✅ **LLM self-assessment**: "I have found a complete solution"
- Agent's own judgment
- No external hints
- Pure reasoning ability

**Correct criterion for success**:
```bash
# Agent's belief (during solving):
grep "Correct solution found (first success)" logs/*.log

# Offline validation (after completion):
python validate_runs_offline.py logs/
```

---

## Impact Assessment

### Previous "Results" (ALL INVALID)

| Test | Reported | Actual Status |
|------|----------|---------------|
| N=12 BFS MEDIUM | 33.3% success (4/12) | ❌ CONTAMINATED |
| N=5 validation | 60% success (3/5) | ❌ CONTAMINATED |
| "83.3% CORRECT verdicts" | 10/12 runs | ❌ CONTAMINATED |

**All analysis based on these results is worthless**:
- ❌ Expert panel analysis
- ❌ Comparison to predictions (30-50%)
- ❌ Statistical significance tests
- ❌ Cost-effectiveness calculations
- ❌ Recommendations for N=100

### What We Actually Know

```
True success rate: UNKNOWN
Need clean test without ground truth leakage
```

---

## Next Steps

### 1. Clean Re-Run of N=12 Test

**Configuration**:
- Use fixed agent (commit 4f50919)
- BFS with MEDIUM reasoning
- NO answer validation in feedback loop
- Offline validation only

**Command**:
```bash
MAX_PARALLEL=12 ./run_bfs_baseline.sh problems/imo01.txt bfs_validation_clean
```

**Post-processing**:
```bash
python validate_runs_offline.py bfs_validation_clean/
```

### 2. Validation of Fix

**Verify**:
1. ✅ No "Missing: {0, 1, 3}" in logs
2. ✅ No "Your answer is CORRECT" in correction prompts
3. ✅ No ground truth in bug_report
4. ✅ Only proof verification feedback (logical errors)

**Check logs**:
```bash
grep -i "missing.*{0.*1.*3}" bfs_validation_clean/*.log  # Should be 0
grep -i "correct answer" bfs_validation_clean/*.log       # Should be 0
grep -i "ground truth" bfs_validation_clean/*.log         # Should be 0
```

### 3. Decision Point

**If clean test shows**:
- ✅ **>30% success**: Proceed to N=100
- ⚠️  **20-30% success**: Consider prompt improvements first
- ❌ **<20% success**: Fundamental issues, need different approach

### 4. Only Then: N=100 Test

**DO NOT run N=100 until**:
- ✅ Clean N=12 test completed
- ✅ Ground truth leakage verified absent
- ✅ True success rate measured
- ✅ Cost-benefit analysis based on CLEAN data

---

## Lessons Learned

### 1. Any Feedback from Ground Truth is Contamination

Even seemingly "safe" feedback leaks information:
- "Your answer is incomplete" → signals it's not {0,1,3}
- Stopping when correct → reveals correctness
- Generic hints → enables hill-climbing

**Only safe approach**: NO ground truth in feedback loop, period.

### 2. Metrics Must Be Trustworthy

```
'verification good': 12/12 (100%) ← Measures proof quality
'Correct solution found': 4/12 (33.3%) ← Agent's belief
Validator (offline): TBD ← Actual correctness
```

Using wrong metric leads to invalid conclusions.

### 3. Contamination is Invisible Without Scrutiny

**What hid the problem**:
- "verification good" showed 100% success
- Logs showed CORRECT verdicts appearing
- Agent produced k∈{0,1,3} in output

**What revealed it**:
- User examined actual correction prompts
- Found "Missing: {0, 1, 3}" literally in feedback
- Realized LLM was copying, not solving

**Takeaway**: Always inspect the actual prompts, not just outcomes.

---

## Verification Checklist

Before using agent for ANY test:

- [ ] Read correction prompt examples from logs
- [ ] Verify NO ground truth in bug_report
- [ ] Verify NO answer validation results in feedback
- [ ] Verify ONLY proof verification feedback present
- [ ] Test with `grep -i "ground truth\|correct answer\|missing.*{" logs/*.log`
- [ ] Confirm offline validation script works
- [ ] Document what feedback IS provided (only logical errors)

---

## Status

✅ **Fix Applied**: commit 4f50919
✅ **Offline Validator**: validate_runs_offline.py created
⏳ **Clean Test**: Pending (need to re-run N=12)
⏳ **True Success Rate**: Unknown (need clean data)

**Recommendation**: Re-run N=12 BFS MEDIUM test with fixed agent, then measure true success rate offline.

---

**Generated**: 2025-12-23
**Author**: Claude (based on user's critical observation)
**Status**: URGENT - All previous test data is contaminated
