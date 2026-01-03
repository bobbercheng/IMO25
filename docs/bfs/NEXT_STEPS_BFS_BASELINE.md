# Next Steps: BFS Baseline with Answer Validation

**Date**: 2025-12-20
**Status**: Ready to Execute
**Goal**: Run N=12 BFS baseline with improved verification (answer validation)

---

## What We've Built

### ✅ Completed

1. **Answer Validation System** (`code/answer_validator.py`)
   - Catches global answer errors (not just proof errors)
   - Tests against ground truth for IMO Problem 1: k ∈ {0,1,3}
   - Validates parametric answers like k ∈ {0,...,n}
   - **Tested**: All 4 test cases pass ✅

2. **BFS Baseline Script** (`run_bfs_baseline.sh`)
   - Configured for N=12 runs
   - Uses BFS (proven 100% success in historical test)
   - Parallel execution (MAX_PARALLEL=6)
   - Expected: 3-4 hours total, $24-36 cost

3. **Verification Improvement Plan** (`VERIFICATION_IMPROVEMENT_PLAN.md`)
   - Two-stage verification: proof + answer
   - Implementation guide with code samples
   - Testing strategy and success metrics

---

## Next: Integrate Answer Validation

### Option A: Quick Integration (Recommended for Testing)

**Add answer validation as POST-VERIFICATION step**

**File**: `code/agent_gpt_oss.py`
**Location**: After verification completes (around line 1200-1220)

**Code to add**:
```python
# After verification
from answer_validator import AnswerValidator

# Extract problem ID from problem file path
problem_id = None
if "imo01" in problem_file:
    problem_id = "imo2025_p1"

# Validate answer
if problem_id:
    validator = AnswerValidator(problem_id)
    answer_text = extract_final_answer(solution_text)  # Uses regex to find answer
    answer_result = validator.validate(answer_text, solution_text)

    # Log answer validation result
    logger.info(f"[ANSWER VALIDATION] Verdict: {answer_result['verdict']}")
    logger.info(f"[ANSWER VALIDATION] Confidence: {answer_result['confidence']}")
    logger.info(f"[ANSWER VALIDATION] Details: {answer_result['details']}")

    # Append to verification feedback
    if answer_result['verdict'] in ['WRONG', 'OVERGENERALIZED', 'INCOMPLETE']:
        feedback_addition = f"""

### ANSWER VALIDATION ALERT ###

Your claimed answer appears to be {answer_result['verdict']}:
{answer_result['details']}

Please revise your answer based on this validation check.
"""
        verification_feedback += feedback_addition
```

---

### Option B: Full Integration (After Testing)

Follow the complete integration plan in `VERIFICATION_IMPROVEMENT_PLAN.md`:
- Modify `verify_solution()` function
- Update verification prompts
- Add answer extraction utilities
- Create combined verdict logic

**Timeline**: 2-3 hours implementation + testing

---

## Recommended Path: Quick Start

### Step 1: Test Answer Validator on Diagnostic Runs (5 min)

```bash
# Test on Run 4 (claimed k ∈ {0,...,n}, should be flagged as WRONG)
python -c "
from code.answer_validator import AnswerValidator
import json

# Load Run 4 result
with open('diagnostic_results/test1_control_full_feedback_run4_20251219_163333.json') as f:
    data = json.load(f)

# Extract solution
solution = data.get('solution', '')

# Validate
validator = AnswerValidator('imo2025_p1')
from code.answer_validator import extract_final_answer
answer = extract_final_answer(solution)
result = validator.validate(answer, solution)

print(f'Answer: {answer[:100]}')
print(f'Verdict: {result[\"verdict\"]}')
print(f'Details: {result[\"details\"]}')
"
```

**Expected output**:
```
Verdict: WRONG
Details: Answer claims k ∈ {0,...,n} but correct is {0,1,3}
```

---

### Step 2: Run 1-2 Pilot BFS Tests (30-40 min)

**Test without answer validation first** (baseline):
```bash
# Run 2 pilot tests
python code/agent_gpt_oss.py problems/imo01.txt \
  --log pilot_bfs_1.log \
  --memory pilot_bfs_1.json \
  --solution-reasoning low \
  --verification-reasoning medium \
  --self-improvement-reasoning low \
  --max_runs 30 &

python code/agent_gpt_oss.py problems/imo01.txt \
  --log pilot_bfs_2.log \
  --memory pilot_bfs_2.json \
  --solution-reasoning low \
  --verification-reasoning medium \
  --self-improvement-reasoning low \
  --max_runs 30 &

# Wait for completion (~15-20 min each)
wait

# Check results
grep -i "verification good\|final answer" pilot_bfs_*.log
```

---

### Step 3: Full N=12 BFS Baseline (3-4 hours)

**Once pilot tests look good, run full baseline**:

```bash
# Run all 12 tests in parallel (6 at a time)
MAX_PARALLEL=6 ./run_bfs_baseline.sh

# Monitor progress
watch -n 10 'tail -20 bfs_baseline_results/*.log | grep -i "iteration\|verification"'
```

**What to expect**:
- Duration: 3-4 hours total (15-20 min per run, 6 parallel)
- Cost: ~$24-36 total ($2-3 per run)
- Success rate: 67-100% (8-12/12 based on historical BFS 100% success)
- Logs: 12 files in `bfs_baseline_results/`

---

### Step 4: Analyze Results (30 min)

```bash
# Quick analysis
cd bfs_baseline_results

# Count successes
echo "Success count:"
grep -l "verification good" *.log | wc -l

# Extract final answers
echo -e "\n=== Final Answers ==="
for log in *.log; do
    echo "File: $(basename $log)"
    grep -A2 "final answer\|\\boxed" "$log" | tail -3
    echo ""
done

# Check for answer validation (if integrated)
echo -e "\n=== Answer Validation Results ==="
grep "ANSWER VALIDATION" *.log | grep "Verdict:"
```

---

## Expected Outcomes

### Scenario A: High Success (8-12/12 runs succeed)
- **Interpretation**: BFS is effective for IMO Problem 1
- **Next step**: Deploy BFS as production solution for FIND problems
- **Decision**: No need for A/B test - BFS clearly superior to RLAC (0% vs 67-100%)

### Scenario B: Medium Success (4-7/12 runs succeed)
- **Interpretation**: BFS has ~50% success rate (better than RLAC 0%)
- **Next step**: Investigate what makes successful runs different
- **Decision**: Possible to run A/B test (N=12 BFS vs N=12 RLAC LOW)

### Scenario C: Low Success (0-3/12 runs succeed)
- **Interpretation**: BFS not as effective as historical data suggested
- **Next step**: Review answer validation - is it too strict?
- **Decision**: Investigate why historical BFS (1/1) doesn't replicate

---

## Statistical Analysis Plan

After N=12 BFS baseline completes:

### Comparison to RLAC Diagnostic Runs

| Metric | RLAC Control (N=4) | BFS Baseline (N=12) | Comparison |
|--------|-------------------|---------------------|------------|
| **Success Rate** | 0% (0/4) | ? / 12 | Need ≥4/12 (33%) for improvement |
| **Duration** | 255 min | ? min | Expect ~15-20 min (17× faster) |
| **Cost** | $25-30 | ? | Expect $2-3 (12× cheaper) |
| **Answer Quality** | 3 different wrong answers | ? | Expect more consistency |

### Statistical Test

**Hypothesis**: BFS success rate > RLAC success rate

**Test**: Fisher's exact test
- RLAC: 0/4 success (0%)
- BFS: X/12 success

**Significance thresholds**:
- If X ≥ 3: p < 0.05 (significant improvement)
- If X ≥ 4: p < 0.01 (highly significant)
- If X ≥ 8: p < 0.001 (extremely significant)

---

## Risk Mitigation

### Risk 1: BFS Doesn't Replicate Historical Success
**Likelihood**: Medium (historical N=1 is small sample)
**Impact**: High (would invalidate BFS recommendation)
**Mitigation**:
- Run N=12 to get reliable estimate
- If <4/12 succeed, investigate why
- Check if answer validation is overly strict

### Risk 2: Answer Validator Rejects Correct Answers
**Likelihood**: Low (tested on 4 known cases)
**Impact**: High (false negatives in validation)
**Mitigation**:
- Review all "WRONG" verdicts manually
- Check if parametric answers {0,...,⌊n/2⌋} should be accepted
- Adjust ground truth if IMO official solution differs

### Risk 3: BFS Takes Longer Than Expected
**Likelihood**: Medium (15 min historical → maybe 30-60 min in practice)
**Impact**: Low (still faster than RLAC 255 min)
**Mitigation**:
- Monitor first 2-3 runs
- If >60 min, check for stuck patterns
- Adjust MAX_RUNS if needed

---

## Go/No-Go Decision Criteria

### ✅ GO: Proceed with Full N=12 BFS Baseline

**Conditions**:
- [x] Answer validator tested and working (4/4 test cases pass)
- [x] BFS script created and executable
- [ ] 1-2 pilot BFS runs complete successfully (15-20 min each)
- [ ] User confirms budget for 12 runs (~$24-36 total)
- [ ] User confirms 3-4 hour timeline acceptable

### 🛑 STOP: Do Not Proceed

**Conditions**:
- [ ] Pilot BFS runs fail (both 0/2)
- [ ] Pilot runs take >60 min each (6× slower than expected)
- [ ] Answer validator has high false positive rate
- [ ] Budget or timeline unacceptable

---

## Timeline Summary

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| 1 | Answer validator implementation | 2 hours | ✅ DONE |
| 2 | BFS script creation | 1 hour | ✅ DONE |
| 3 | Test validator on diagnostic runs | 5 min | ⏳ NEXT |
| 4 | Run 2 pilot BFS tests | 30-40 min | ⏳ PENDING |
| 5 | Review pilot results | 10 min | ⏳ PENDING |
| 6 | **GO/NO-GO decision** | - | ⏳ PENDING |
| 7 | Run full N=12 BFS baseline | 3-4 hours | ⏳ PENDING |
| 8 | Analyze N=12 results | 30 min | ⏳ PENDING |
| 9 | Statistical comparison to RLAC | 15 min | ⏳ PENDING |
| **Total** | | **~6-8 hours** | |

---

## Ready to Start?

**Immediate next step**: Run 1-2 pilot BFS tests

```bash
# Quick pilot test (no integration needed yet)
python code/agent_gpt_oss.py problems/imo01.txt \
  --log pilot_bfs_1.log \
  --memory pilot_bfs_1.json \
  --solution-reasoning low \
  --verification-reasoning medium \
  --self-improvement-reasoning low \
  --max_runs 30
```

**Expected**: Completes in 15-20 min with "verification good = YES"

---

**Questions before proceeding?**
1. Should we integrate answer validation before or after pilot tests?
2. What's your budget limit for N=12 baseline?
3. Do you want to review pilot results before full baseline?

**Recommended**: Run 2 pilots first, then decide on full N=12.
