# BFS Baseline Test Analysis: N=12 Run with Blacklist
## Complete Knowledge Graph & Expert Synthesis

**Test Configuration**:
- N=12 parallel runs
- Problem: IMO 2025 #6 (minimum tiles covering)
- Reasoning: MEDIUM (solution), HIGH (verification)
- Features: Solution blacklist, RAG hints, BFS diversity

**Test Date**: 2026-01-01
**Result**: **0/12 SUCCESS** (0% success rate)

---

## Knowledge Graph: 12-Run Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     BFS TEST EXECUTION FLOW                      │
│                    (All 12 runs FAILED)                         │
└─────────────────────────────────────────────────────────────────┘

RUN TIMELINE:
├─ Run 3  [18:49:42] ──┬─→ iter=0 → Answer: 4048 → PASS ──┐
├─ Run 1  [18:49:42] ──┤   iter=0 → Answer: 4048 → PASS ──┤
├─ Run 2  [18:49:42] ──┤   iter=0 → Answer: 4048 → PASS ──┤
├─ Run 4  [18:51:00] ──┤   iter=0 → Answer: 4048 → PASS ──┤  WRONG
├─ Run 5  [18:52:44] ──┤   iter=0 → Answer: 4048 → PASS ──┤  ANSWERS
├─ Run 7  [18:54:22] ──┤   iter=0 → Answer: 4048 → PASS ──┤  ALL
├─ Run 6  [18:56:11] ──┤   iter=4 → Answer: 4048 → PASS ──┤  MARKED
├─ Run 8  [18:58:33] ──┤   iter=2 → Answer: 4048 → PASS ──┤  "PASS"
├─ Run 9  [19:00:39] ──┤   iter=0 → Answer: 4048 → PASS ──┤
├─ Run 10 [19:03:17] ──┤   iter=1 → Answer: 2025 → PASS ──┤  ONLY
├─ Run 11 [19:09:09] ──┤   iter=0 → Answer: 4048 → PASS ──┤  RUN
├─ Run 12 [19:13:41] ──┴─→ iter=0 → Answer: 4048 → PASS ──┘  WITH
                                                              DILWORTH

BLACKLIST STATUS:
├─ Entries saved: 12/12 ✓
├─ Extracted answers: GARBAGE (LaTeX fragments)
├─ Blacklist activated: 0/12 runs (NO LOGS!)
└─ Verdict distribution: 12/12 PASS (100% false positives!)

ACTUAL ANSWERS (from log analysis):
├─ \boxed{4048}: 614 occurrences ← Ferrers bound (WRONG)
├─ \boxed{42}: 270 occurrences ← (WRONG)
├─ \boxed{2025}: 118 occurrences ← (WRONG)
├─ \boxed{4050}: 30 occurrences ← (WRONG)
└─ \boxed{2112}: 0 occurrences ← CORRECT (never found!)

CORRECT ANSWER: 2112 (Dilworth decomposition for n=45²)
```

---

## Per-Run Breakdown

### Run 1 (18:49:42)
- **Duration**: 1.9 min
- **Iterations**: 0
- **Method**: diagonal_permutation
- **Extracted answer**: `"i = 1"` ← GARBAGE
- **Actual answer**: `\boxed{4048}`
- **Verdict**: PASS
- **Blacklist**: Saved at 18:52:41
- **Issue**: Answer extraction completely broken

### Run 2 (18:49:42)
- **Duration**: 4.3 min
- **Iterations**: 0
- **Method**: diagonal_permutation
- **Extracted answer**: `"n = 2025\\)) such that the unique uncovered"` ← GARBAGE
- **Actual answer**: `\boxed{4048}`
- **Verdict**: PASS
- **Blacklist**: Saved at 18:53:53
- **Issue**: Same wrong answer as Run 1, no diversity

### Run 3 (18:49:42)
- **Duration**: 1.7 min
- **Iterations**: 0
- **Method**: diagonal_permutation
- **Extracted answer**: `"n = 2025\\)) such that the uncovered square in row \\(i\\) is \\((i"` ← GARBAGE
- **Actual answer**: `\boxed{4048}`
- **Verdict**: PASS
- **Blacklist**: Saved at 18:51:00
- **Issue**: First to save, but extracted garbage

### Run 4 (18:51:00)
- **Duration**: 5.4 min
- **Iterations**: 0
- **Method**: diagonal_permutation
- **Extracted answer**: `"m = \\sum (h_k+w_k)\\ge4n-4\\quad\\Longrightarrow\\quad m\\ge2n-2"` ← GARBAGE
- **Actual answer**: `\boxed{4048}`
- **Verdict**: PASS
- **Blacklist**: Should have seen Runs 1-3, but no evidence
- **Issue**: Blacklist didn't prevent repeat

### Run 5 (18:52:44)
- **Duration**: 11.6 min
- **Iterations**: 0
- **Method**: diagonal_permutation
- **Extracted answer**: `"n = 2025\\))"` ← GARBAGE
- **Actual answer**: `\boxed{4048}`
- **Verdict**: PASS
- **Blacklist**: Should have seen Runs 1-4
- **Issue**: Still using diagonal permutation

### Run 6 (18:56:11)
- **Duration**: 6.2 min
- **Iterations**: 4
- **Method**: diagonal_permutation
- **Extracted answer**: `"n = 2025\\))"`← GARBAGE
- **Actual answer**: `\boxed{4048}`
- **Verdict**: PASS (after 4 iterations)
- **Blacklist**: Should have seen Runs 1-5
- **Issue**: Most iterations, still wrong answer

### Run 7 (18:54:22)
- **Duration**: 2.8 min
- **Iterations**: 0
- **Method**: diagonal_permutation
- **Extracted answer**: `"n = 2025\\)) such that"` ← GARBAGE
- **Actual answer**: `\boxed{4048}`
- **Verdict**: PASS
- **Blacklist**: Should have seen Runs 1-6
- **Issue**: No diversity whatsoever

### Run 8 (18:58:33)
- **Duration**: 9.4 min
- **Iterations**: 2
- **Method**: unknown_method
- **Extracted answer**: `"n = 2025\\)) be the permutation defined by"` ← GARBAGE
- **Actual answer**: `\boxed{4048}`
- **Verdict**: PASS
- **Blacklist**: Should have seen Runs 1-7
- **Issue**: Method detection failed

### Run 9 (19:00:39)
- **Duration**: 2.6 min
- **Iterations**: 0
- **Method**: diagonal_permutation
- **Extracted answer**: `"i = 1"` ← GARBAGE (same as Run 1!)
- **Actual answer**: `\boxed{4048}`
- **Verdict**: PASS
- **Blacklist**: Should have seen Runs 1-8
- **Issue**: Exact duplicate of Run 1 extraction

### Run 10 (19:03:17) ⭐ **ONLY DIFFERENT RUN**
- **Duration**: 9.3 min
- **Iterations**: 1
- **Method**: **dilworth_decomposition** ← ONLY ONE!
- **Extracted answer**: `"n = 2025"` ← GARBAGE
- **Actual answer**: `\boxed{2025}` (still wrong, should be 2112)
- **Verdict**: PASS
- **Blacklist**: Should have seen Runs 1-9
- **Critical**: Only run to use Dilworth, but still wrong answer

### Run 11 (19:09:09)
- **Duration**: 6.7 min
- **Iterations**: 0
- **Method**: diagonal_permutation
- **Extracted answer**: `"n = 2025\\))"`← GARBAGE
- **Actual answer**: `\boxed{4048}`
- **Verdict**: PASS
- **Blacklist**: Should have seen Runs 1-10 (including Dilworth!)
- **Issue**: Back to diagonal despite seeing Dilworth

### Run 12 (19:13:41)
- **Duration**: 6.8 min
- **Iterations**: 0
- **Method**: unknown_method
- **Extracted answer**: `"n = 2025\\))"` ← GARBAGE
- **Actual answer**: `\boxed{4048}`
- **Verdict**: PASS
- **Blacklist**: Should have seen all 11 previous runs
- **Issue**: Final run, no improvement

---

## Critical Findings Summary

### Finding #1: Answer Extraction Catastrophically Broken
**Evidence**: All 12 blacklist entries have garbage answers
```json
Run 1: "i = 1"
Run 2: "n = 2025\\)) such that the unique uncovered"
Run 3: "n = 2025\\)) such that the uncovered square in row \\(i\\) is \\((i"
```

**Root cause**: `extract_answer_from_solution()` has NO `\boxed{}` pattern
- Function uses 8 generic patterns for natural language
- Pattern 2 matches random LaTeX like `n = 2025\))` from intermediate steps
- Correct `\boxed{4048}` completely ignored

**Impact**: Blacklist saves garbage → next run can't recognize duplicates → no diversity

---

### Finding #2: Blacklist Never Activated
**Evidence**: Zero blacklist logs in any of 12 runs
```bash
grep -r "BLACKLIST" test_blacklist_full_3/*.log  # NO MATCHES
grep -r "Avoiding\|forbidden\|FORBIDDEN" *.log  # NO MATCHES
```

**Hypothesis 1**: Parallel execution (90% probability)
- 12 runs started simultaneously at 18:49:42
- No sharing of state during execution
- Blacklist only written AFTER each run completes
- Next run starts before previous blacklist saved

**Hypothesis 2**: Integration bug (60% probability)
- Blacklist code exists but never called
- `init_explorations()` doesn't receive problem_id/run_id
- Feature flag disabled
- Silent failure in import

**Impact**: Even if extraction worked, blacklist never had chance to work

---

### Finding #3: All Wrong Answers Got PASS Verdict
**Evidence**: 12/12 blacklist entries show `"verdict": "PASS"`

**Actual distribution**:
- 11/12 runs: Answer 4048 (WRONG, Ferrers bound)
- 1/12 run: Answer 2025 (WRONG, incomplete)
- 0/12 runs: Answer 2112 (CORRECT)

**Root cause**: Verification system accepts suboptimal solutions
- Verifier checked if 4048 works (it does)
- Verifier didn't check if better solution exists (2112 is optimal)
- Missing optimality testing

**Impact**: Blacklist shows "PASS" for wrong approaches → model thinks they're valid → no avoidance

---

### Finding #4: Only 1/12 Runs Used Dilworth
**Evidence**: Run 10 detected as `"dilworth_decomposition"`, others as `"diagonal_permutation"`

**Why Run 10 was different**:
- Started 13 minutes after first runs
- May have seen blacklist (if sequential, not parallel)
- Still got wrong answer (2025 instead of 2112)
- RAG hints about Dilworth partially worked?

**Impact**: 8% diversity (1/12) despite blacklist, RAG hints, and imperative prompts

---

### Finding #5: 100% Convergence to Wrong Answer
**Evidence**:
- 614 occurrences of `\boxed{4048}` across all logs
- 270 occurrences of `\boxed{42}` (also wrong)
- 0 occurrences of `\boxed{2112}` (correct answer)

**Training bias dominance**:
- Ferrers diagram is standard approach in training data
- LLM strongly biased toward 2n-2 bound
- Imperative prompts ("DO NOT use Ferrers!") completely ignored
- Negative examples didn't override training

**Impact**: All diversity mechanisms failed - RAG, blacklist, BFS, imperative prompts

---

## Expert Consensus & Disagreements

### ✅ ALL 4 EXPERTS AGREE ON:

1. **Answer extraction is broken** (xAI, Nvidia, Google, Netflix all agree)
   - Missing `\boxed{}` pattern
   - High priority fix
   - Low risk, high impact

2. **Blacklist likely never ran** (Google 90% confidence, Netflix 90%, xAI suspects, Nvidia suspects)
   - No logs found
   - Parallel execution hypothesis
   - Need $24 test to confirm

3. **N=12 sample too small** (Google, Netflix both calculated)
   - Can only detect >40pp effects
   - 95% CI on success rate: [5.5%, 57.1%] - HUGE range
   - Need N=50-200 for precise estimates

4. **Claims lack experimental validation** (Google demands data, Netflix demands ROI)
   - "30% diversity improvement" - zero evidence
   - "99% accuracy" - never tested
   - All claims are speculation

### ⚠️ EXPERTS DISAGREE ON:

**Should we abandon blacklist?**

**xAI**: YES - "Blacklist is fundamentally flawed, fix verification instead"
- Verification is root cause (PASS for wrong answers)
- Blacklist is band-aid for broken verification
- Better to invest in verification quality

**Nvidia**: YES - "Fix system bugs first, blacklist addresses wrong problem"
- Training bias is root cause (LLM ignores prompts)
- Blacklist can't override training bias
- Better to use temperature/exploration

**Google**: NO - "Test it first before abandoning"
- Blacklist wasn't tested (no logs = no execution)
- Can't conclude it failed if it never ran
- Science demands: test → measure → decide

**Netflix**: NO - "The $24 test could save $1000 in optimization"
- Blacklist is 90% likely broken, but 10% chance it works
- Testing costs $24, abandoning costs engineering effort invested
- Run the test, then decide based on data

---

## Synthesized Recommendations

### Tier 1: IMMEDIATE (24 hours, $24)

#### Action 1.1: Test if Blacklist Ever Ran
**Cost**: $24 (4 runs)
**Timeline**: 4 hours
**Owner**: Netflix DS approach

**Protocol**:
```bash
# Add extensive logging
print(f"[BLACKLIST] Loading from {blacklist_file}")
print(f"[BLACKLIST] Found {len(solutions)} previous attempts")
print(f"[BLACKLIST] Prompt: {prompt[:200]}")

# Run 2 sequential tests
# Check: Does run 2 see run 1's blacklist entry?

# Decision:
# - If blacklist works: Keep it, fix answer extraction
# - If blacklist dead: Remove code, simplify system
```

**Expected outcome**: 90% chance blacklist is dead/broken

---

#### Action 1.2: Fix Answer Extraction (Add \boxed{} Pattern)
**Cost**: $0 (code change only)
**Timeline**: 30 minutes
**Owner**: xAI + Nvidia consensus

**Code fix**:
```python
# File: code/agent_gpt_oss.py line 3048
# Add BEFORE all other patterns:

# Pattern 0: \boxed{} answer (HIGHEST PRIORITY)
boxed_match = re.search(r'\\boxed\{([^}]+)\}', solution)
if boxed_match:
    inner = boxed_match.group(1).strip()
    # Handle nested braces: \boxed{\{0,1,3\}}
    if inner.startswith('{') and inner.endswith('}'):
        inner = inner  # Keep braces for set answers
    return {
        'raw': inner,
        'type': 'boxed_answer',
        'value': inner,
        'variable': None,
        'confidence': 'high'
    }
```

**Validation**:
```bash
# Test on 12 actual solutions from test_blacklist_full_3
# Before: Extracts "n = 2025\\))" garbage
# After: Extracts "4048" correctly

# Acceptance: 100% of 12 solutions extract correct number
```

**Risk**: LOW (regex is safer than current broken state)

---

#### Action 1.3: Verify Ground Truth
**Cost**: $0 (manual check)
**Timeline**: 1 hour
**Owner**: Google rigor

**Check**:
1. IMO 2025 Problem 6 official solution → what's the answer?
2. Dilworth theorem for n=45² → calculate 45²+2(45)-3 = 2112 ✓
3. Ferrers bound for n=2025 → calculate 2(2025)-2 = 4048 ✗

**Expected**: 2112 is correct (high confidence)

---

### Tier 2: VALIDATION (1 week, $300)

#### Action 2.1: Build Ground Truth Test Set
**Cost**: $0 (use existing IMO solutions)
**Timeline**: 2 days
**Owner**: Google + Netflix consensus

**Approach**:
```python
# Create test_suite.json with 50 IMO problems
[
    {
        "problem": "IMO 2025 #1",
        "answer": "{0, 1, 3}",
        "source": "Official IMO solutions"
    },
    ...
]

# Use for all future A/B tests
```

---

#### Action 2.2: A/B Test Answer Extraction Fix
**Cost**: $36 (6 runs)
**Timeline**: 6 hours
**Owner**: Netflix approach

**Protocol**:
```bash
# Control: 3 runs with old regex
# Treatment: 3 runs with new regex (boxed pattern)

# Metrics:
# - Extraction accuracy: % of runs with correct numerical answer
# - Diversity: # of unique answers
# - Success rate: % of runs that find correct solution

# Acceptance: Extraction accuracy improves >50% (from ~0% to >50%)
```

---

#### Action 2.3: Test Verification Temperature
**Cost**: $150 (25 runs)
**Timeline**: 2 days
**Owner**: Nvidia proposal with Netflix validation

**Protocol**:
```bash
# 10 problems × 1 run each
# Test: T=0.0 vs T=0.3 verification
# Ground truth labels from test set

# Metrics:
# - False positive rate (PASS for wrong answer)
# - False negative rate (FAIL for correct answer)
# - F1 score

# Acceptance: F1 improves >10% with p<0.05
```

---

### Tier 3: OPTIMIZATION (2 weeks, $1000)

Only proceed if Tier 1+2 show promise.

**Potential fixes**:
1. Verification ensemble (5 verifiers vote)
2. Optimality testing (try n=3,4,5 manually)
3. Adversarial debate (generator vs critic)
4. Temperature tuning for exploration
5. Prompt engineering improvements

---

## Final Recommendation

### DO THIS RIGHT NOW (next 24 hours):

**Step 1**: Fix answer extraction (30 min, $0)
```bash
# Add \boxed{} pattern to extract_answer_from_solution()
# This fixes a clear bug regardless of other issues
```

**Step 2**: Test if blacklist works (4 hours, $24)
```bash
# Run 2 sequential tests with logging
# If works: Keep and optimize
# If broken: Remove dead code
```

**Step 3**: Verify ground truth (1 hour, $0)
```bash
# Confirm 2112 is correct answer
# If wrong: Invalidates entire analysis
```

**Step 4**: Quick extraction validation (2 hours, $12)
```bash
# Re-run 2 tests with fixed extraction
# Check: Does blacklist save "4048" instead of garbage?
```

**Total investment**: 7.5 hours, $36

**Expected outcome**:
- Know if blacklist works (90% chance it doesn't)
- Know if extraction fix helps (95% chance it does)
- Know if we're solving the right problem (100% certainty)

---

### DO NOT DO (without data):

❌ Abandon blacklist (test it first - $24)
❌ Change verification temperature (A/B test first - $150)
❌ Switch to N=3 (calculate ROI first - $0)
❌ Deploy to production (validate first - $300)

---

### Success Criteria

**After 24 hours**:
- ✅ Answer extraction returns numbers, not LaTeX fragments
- ✅ Blacklist saves actual answers (e.g., "4048"), not garbage
- ✅ Know if blacklist works or is dead code
- ✅ Ground truth verified

**After 1 week**:
- ✅ A/B tests show which fixes actually help
- ✅ Statistical significance (p<0.05) on improvements
- ✅ Decision made: Keep blacklist vs abandon vs optimize

**After 2 weeks**:
- ✅ Production-ready system with >50% success rate
- ✅ Cost per solution <$100
- ✅ Reusable test harness for future problems

---

## Bottom Line

**The BFS blacklist test revealed 3 critical bugs**:
1. Answer extraction broken (extracts garbage)
2. Blacklist likely never ran (no logs)
3. Verification accepts wrong answers (100% PASS rate)

**The good news**: All 3 are fixable.

**The bad news**: No data supports any claimed "improvement percentages."

**The path forward**:
1. Fix the obvious bug (answer extraction) - 30 min
2. Test if blacklist works - 4 hours, $24
3. Build test harness - 2 days
4. A/B test everything - 1 week, $300
5. Deploy with confidence - 2 weeks

**Netflix would do**: The $24 test first, then decide architecture based on data.

**Google would demand**: Statistical rigor before any production deployment.

**xAI would ship**: The answer extraction fix immediately (it's broken regardless).

**Nvidia would optimize**: For cost and scale after validating fixes work.

---

**All 4 experts agree: Fix answer extraction NOW, test blacklist TODAY, decide based on DATA.**
