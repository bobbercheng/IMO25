# OpenAI Critical Analysis: Are We Building a House of Cards?

**Analyst:** Senior OpenAI Engineer
**Date:** 2026-01-06
**Persona:** High talent density, fast-paced, ship-it mentality
**Mission:** Challenge assumptions, find failure modes, determine if this can SHIP

---

## TL;DR: YES, this is a house of cards. Here's why:

| Question | Answer | Implications |
|----------|--------|--------------|
| **The real bug?** | Model uses n+2m-**2** instead of n+2m-**3** | We don't know WHY |
| **Band-aid vs fix?** | 100% band-aid | P0+P1 prevent consequences, don't fix cause |
| **Dependency hell?** | Ground truth + BFS best attempt | 2 dependencies, both must work perfectly |
| **Can it ship?** | **NO** | Only works when we already know the answer |

---

## 1. The Real Bug: WHY n+2m-2 instead of n+2m-3?

### What We Know

**The Formula Error:**
```
Ground Truth:  M(n) = n + 2√n - 3 = 2112  ✓ CORRECT
Model Output:  M(n) = n + 2√n - 2 = 2113  ✗ OFF BY +1
```

**Mathematical Root Cause** (from expert analysis):
- **Fooling set overcounting**: Model adds k+(k-1) = 2k-1 cells beyond L, should add 2k-2
- **Asymmetry bug**: Uses BOTH full k column blocks AND (k-1) row blocks → double counts 1 boundary
- **Missing insight**: Dilworth's theorem boundary conditions require -3, not -2

### What We DON'T Know

**CRITICAL UNKNOWNS:**
1. **WHY does the model make this specific error?**
   - Is it a training bias toward simpler formulas (2k-2 vs 2k-3)?
   - Is it a systematic counting bug in how LLMs handle boundary conditions?
   - Is it problem-specific or does it happen on other grid optimization problems?

2. **HOW OFTEN does this happen?**
   - We've seen this bug on Problem 6 (IMO 2025)
   - Does it happen on all Dilworth-type problems?
   - Does it happen on other counting/combinatorics problems?

3. **CAN the model generate the correct formula if prompted differently?**
   - Would "check your boundary conditions" catch this?
   - Would "verify for small cases (n=9)" expose the +1 error?
   - Would better verification prompts fix this without ground truth?

### Ship-It Question: Do we understand this bug well enough to fix it generally?

**Answer: NO.**

We're treating symptoms (wrong answer) without understanding the disease (why the systematic +1 error).

---

## 2. Band-Aid vs Fix: What P0+P1 Actually Do

### P0: Answer Validation in Proof Mode

**Code Location:** `init_explorations()` lines 3216-3234

**What it does:**
```python
if ground_truth_answer is not None and solution:
    solution_answer = solution.get('final_answer')
    if solution_answer != ground_truth_answer:
        print("[PROOF MODE VIOLATION] Answer mismatch detected!")
        return p1, None, error_msg, "no"  # REJECT SOLUTION
```

**Translation:** "If you don't give me the right answer, I'll reject your solution and try again."

**Is this a fix?**
- ✅ Prevents accepting wrong answers when ground truth is known
- ❌ Doesn't fix WHY the model got the wrong answer
- ❌ Doesn't work on NEW problems (no ground truth)
- ❌ Doesn't teach the model what it did wrong

**Verdict:** This is a **validator**, not a **fix**. Band-aid.

### P1: Answer Lock Mechanism

**Code Location:** BFS selection (7442-7448), correction loop (7646-7668)

**What it does:**
```python
# After BFS selects best solution:
locked_answer = best_solution.get('final_answer')

# During correction iterations:
if corrected_answer != locked_answer:
    print("[ANSWER LOCK VIOLATION] Correction changed the answer!")
    solution = previous_solution  # REJECT CORRECTION
```

**Translation:** "Once BFS finds an answer, don't let verification 'correct' it to something else."

**Is this a fix?**
- ✅ Prevents 2112 → 2113 drift during post-BFS corrections
- ❌ Doesn't fix WHY verification thought 2112 needed correction
- ❌ Assumes BFS found the RIGHT answer (big assumption!)
- ❌ If BFS locks WRONG answer, we're stuck with it forever

**Verdict:** This is a **safety rail**, not a **fix**. Band-aid.

---

## 3. Dependency Hell: What Can Go Wrong?

### Dependency Chain

```
P0+P1 Success = Ground Truth ∧ BFS Finds Correct Answer
```

**Failure Mode Analysis:**

| Scenario | P0 Behavior | P1 Behavior | Outcome |
|----------|-------------|-------------|---------|
| ✅ BFS finds 2112 | Accept (matches GT) | Lock 2112 | **SUCCESS** |
| ❌ BFS finds 2113 | Reject (doesn't match GT) | Lock 2113 anyway | **FAIL (locked wrong answer)** |
| ❌ BFS finds 4048 | Reject (doesn't match GT) | Lock 4048 anyway | **FAIL (completely wrong)** |
| ❌ No ground truth | P0 disabled | P1 disabled | **UNPROTECTED** |

### Critical Dependency #1: Ground Truth Availability

**When we have it:**
- P0 validates answers ✓
- Can reject wrong attempts ✓

**When we DON'T have it (production):**
- P0 is completely disabled
- Model can output 2113 instead of 2112
- No validation catches the +1 error
- **System behavior fundamentally different between test and prod**

**Ship-It Question:** Can we ship a system that behaves differently with/without ground truth?

**Answer: NO.** This is test-only scaffolding, not production-ready validation.

### Critical Dependency #2: BFS Finds Correct Answer FIRST

**The Assumption:**
From `BFS_FIXED_TEST_KNOWLEDGE_GRAPH.md`:
> "Expert consensus: BFS generates correct answers (100% success)"

**Reality Check:**
- **Test 1 (proof_2112.log):** BFS without proof mode → 5/5 attempts got **4048** (completely wrong)
- **Test 2 (test_proof_2112_fixed.log):** BFS with proof mode → 5/5 attempts got **2112** (correct)
- **Test 3 (test_proof_2112_lock.log):** Unknown - need to check

**What if BFS generates 5 wrong answers?**
1. P0 rejects all 5 (none match ground truth)
2. P1 locks... what? First attempt? Last attempt?
3. System either fails or locks a wrong answer

**Ship-It Question:** What's the fallback when BFS fails to find correct answer?

**Answer: UNCLEAR.** Code doesn't handle "all BFS attempts rejected" scenario.

---

## 4. Challenging Assumptions

### Assumption #1: "Prove 2112" is easier than "Find the answer"

**Evidence FOR:**
- Test 2 with `--ground-truth-answer 2112`: BFS got 2112 (100% success)
- Test 1 without ground truth: BFS got 4048 (0% success)
- Suggests proof mode helps focus the search

**Evidence AGAINST:**
- Model still doesn't understand WHY 2112 is correct (just knows it's the target)
- Verification still tried to "correct" 2112 → 2113 (verification doesn't trust the proof)
- If model truly understood 2112, verification wouldn't challenge it

**Critical Question:** Is the model LEARNING the correct formula, or just OPTIMIZING toward a known target?

**Hypothesis:** Proof mode is a different kind of search:
- **Find mode:** Search formula space → often lands on n+2m-2 (wrong)
- **Prove mode:** Search proof space for target 2112 → back-calculates m=45, forces formula to match
- **Neither mode fixes the underlying +1 counting bug**

### Assumption #2: BFS diversity creates robust solutions

**Evidence FOR:**
- BFS generates 5 different attempts with different methods
- Best attempt selected by verification score
- Diversity should explore alternative formulas

**Evidence AGAINST:**
- Without proof mode: All 5 attempts → same formula (2N-2 = 4048)
- With proof mode: All 5 attempts → target formula (N+2√N-3 = 2112)
- **BFS creates diversity in PROOF TECHNIQUES, not FORMULAS**

**Reality:** The model has strong priors:
- Training bias toward certain formulas (2N-2 is common in grid problems)
- Dilworth's theorem is complex, not in common training patterns
- BFS diversity doesn't overcome formula bias without explicit guidance

### Assumption #3: P0+P1 prevent answer drift

**What they prevent:**
- ✅ Accepting solutions with wrong final_answer (when GT known)
- ✅ Post-BFS corrections changing the answer

**What they DON'T prevent:**
- ❌ BFS generating wrong answers in first place
- ❌ Model deriving wrong formula
- ❌ Verification having bad judgment about what needs correction
- ❌ The +1 counting bug

**Analogy:** This is like adding airbags to a car with faulty brakes. Airbags help AFTER the crash, but don't prevent the crash.

---

## 5. Failure Modes: What If...?

### Failure Mode #1: BFS Generates 5 Wrong Answers

**Scenario:**
```bash
python code/agent_gpt_oss.py problems/imo_new.txt \
  --ground-truth-answer 1337 \
  --num-initial-attempts 5
```

**BFS Results:**
- Attempt 1: 1338 (off by +1) → P0 rejects ❌
- Attempt 2: 1336 (off by -1) → P0 rejects ❌
- Attempt 3: 1338 (off by +1) → P0 rejects ❌
- Attempt 4: 1340 (completely wrong) → P0 rejects ❌
- Attempt 5: 1338 (off by +1) → P0 rejects ❌

**What happens next?**
- All attempts rejected
- `best_solution = None`?
- Does system fall back to single-path mode?
- Does P1 try to lock `None`?

**CODE AUDIT NEEDED:** Check handling of "all BFS attempts failed validation"

### Failure Mode #2: P1 Locks Wrong Answer

**Scenario:**
```bash
# BFS without ground truth (production mode)
python code/agent_gpt_oss.py problems/imo_new.txt \
  --num-initial-attempts 5
```

**BFS Results:**
- Attempt 1: 1338 (score: 150.00) ← **BEST**
- Attempt 2: 1336 (score: 96.26)
- Attempt 3: 1338 (score: 150.00)
- Attempt 4: 1340 (score: -16.46)
- Attempt 5: 1337 (score: 96.26) ← **CORRECT**

**What P1 does:**
```python
locked_answer = best_solution.get('final_answer')  # = 1338
```

**Result:** Answer locked to 1338 (wrong), attempt 5's correct answer (1337) is ignored.

**Root Cause:** P1 locks based on VERIFICATION SCORE, not CORRECTNESS.

### Failure Mode #3: New Problem Without Ground Truth

**Production Scenario:**
```bash
# Solving a NEW problem (no ground truth available)
python code/agent_gpt_oss.py problems/new_imo.txt \
  --num-initial-attempts 5
```

**What happens:**
- P0 disabled (no ground truth to validate against) ❌
- Model generates answer using same biased formula (n+2m-2) ❌
- Gets 2113 instead of 2112 ❌
- Verification passes it (doesn't know it's wrong) ❌
- P1 locks the wrong answer ❌
- **System produces wrong answer with high confidence**

**CRITICAL:** P0+P1 provide ZERO protection on new problems.

---

## 6. Can We Make "Find Mode" as Good as "Prove Mode"?

### The Performance Gap

| Mode | Config | Success Rate | Notes |
|------|--------|--------------|-------|
| **Find mode** | No GT | 0% (got 4048) | Model searches formula space freely |
| **Prove mode** | GT=2112 | 100% (got 2112) | Model constrained to prove target |

**Why is prove mode better?**

**Hypothesis 1: Reduces search space**
- Find mode: ∞ possible formulas to explore
- Prove mode: 1 specific target to prove
- Constraint helps model focus

**Hypothesis 2: Better verification**
- Find mode: Verify "is this formula correct?"
- Prove mode: Verify "does this proof show target is correct?"
- Proof verification is easier (checking vs. discovering)

**Hypothesis 3: Removes formula bias**
- Find mode: Model defaults to familiar formulas (2N-2)
- Prove mode: Model forced to derive target (N+2√N-3)
- Constraint overrides training bias

### Can We Get Prove-Mode Benefits Without Ground Truth?

**Idea 1: Self-consistency checking**
```
1. Generate solution with formula F
2. Test formula F on small cases (n=9, n=16, n=25)
3. If F fails on small cases, reject and regenerate
4. Lock answer only if passes small-case validation
```

**Problems:**
- Requires constructing/verifying small cases (non-trivial)
- May not catch subtle +1 errors (2112 vs 2113 both "reasonable")
- Adds significant latency

**Idea 2: Multi-model voting**
```
1. Generate 5 BFS attempts
2. Extract all unique answers
3. Take majority vote or median
4. Lock most common answer
```

**Problems:**
- If all 5 converge to wrong answer (4048), voting doesn't help
- Requires odd number of attempts for majority
- Doesn't fix underlying formula bug

**Idea 3: Verification challenges the answer**
```
1. Generate solution with answer A
2. Verification actively tries to disprove A
3. Generate alternative construction with answer A'
4. If A ≠ A', flag conflict and regenerate
```

**Problems:**
- Verification already supposed to do this (but doesn't)
- Requires verification to be adversarial (current is cooperative)
- May create oscillation (A → A' → A → ...)

**VERDICT:** No obvious way to get prove-mode benefits without ground truth.

---

## 7. Ship-It Test: Can We Ship This to Solve NEW Problems?

### The Ultimate Question

**Can we deploy this system to solve IMO problems where we DON'T know the answer?**

### Deployment Checklist

| Requirement | Status | Blocker |
|-------------|--------|---------|
| ✅ **Works without ground truth** | ❌ FAIL | P0 disabled, no validation |
| ✅ **Catches formula errors** | ❌ FAIL | +1 bug not detected |
| ✅ **Verification reliable** | ❌ FAIL | Tried to "correct" 2112→2113 |
| ✅ **BFS finds correct answers** | ❌ FAIL | Got 4048 without proof mode |
| ✅ **Handles all BFS rejected** | ⚠️ UNKNOWN | Need code audit |
| ✅ **Prevents locking wrong answer** | ❌ FAIL | Locks based on score, not correctness |
| ✅ **Production = test behavior** | ❌ FAIL | Completely different (GT vs no GT) |

**Blockers: 5 FAIL, 1 UNKNOWN, 0 PASS**

### Ship-It Decision

**Recommendation: DO NOT SHIP**

**Reasons:**
1. **Ground truth dependency:** System only works when we already know the answer
2. **Formula bug unfixed:** Still generates n+2m-2 instead of n+2m-3
3. **Verification unreliable:** Thought correct answer needed "correction"
4. **BFS not robust:** Without proof mode, converges to wrong formula
5. **Test-prod divergence:** Fundamentally different behavior in production

**This is research scaffolding, not a production system.**

---

## 8. What SHOULD We Do Instead?

### Strategy A: Fix the Root Cause (HIGH EFFORT, HIGH IMPACT)

**Goal:** Make model generate correct formula without ground truth

**Approach:**
1. **Analyze the +1 bug systematically**
   - Run on multiple Dilworth-type problems
   - Identify common failure pattern
   - Determine if it's boundary conditions, counting, or something else

2. **Improve prompting for boundary conditions**
   - Add explicit "check boundary conditions" step
   - Force verification of edge cases (m=1, m=2)
   - Require explicit counting of boundary blocks

3. **Better verification**
   - Train verification to catch off-by-one errors
   - Require small-case testing (n=9, n=16, n=25)
   - Flag "suspiciously simple" formulas as needing extra scrutiny

**Timeline:** 2-4 weeks
**Success Metric:** Solve Problem 6 WITHOUT ground truth, get 2112

### Strategy B: Make Proof Mode Work Better (MEDIUM EFFORT, MEDIUM IMPACT)

**Goal:** Improve proof mode so BFS reliably finds correct answer

**Approach:**
1. **Fix proof mode prompt engineering**
   - Current prompt may be too weak
   - Add "the answer is EXACTLY {GT}, prove no other value works"
   - Require construction + impossibility proof for GT±1

2. **Make BFS prompts problem-aware**
   - Detect MINIMIZE vs FIND ALL vs PROVE problems correctly
   - Generate prompts that guide toward different formulas
   - Test small cases to identify formula pattern

3. **Add small-case validation DURING BFS**
   - Before accepting any BFS attempt, test on n=9
   - Reject formulas that fail small-case tests
   - Only lock answers that pass validation

**Timeline:** 1-2 weeks
**Success Metric:** Proof mode gets 2112 reliably (>90% of runs)

### Strategy C: Accept Current Limitations (LOW EFFORT, LOW IMPACT)

**Goal:** Document what the system CAN and CANNOT do

**Approach:**
1. **Clearly document dependencies**
   - P0+P1 only work with ground truth
   - Production mode has no validation
   - BFS may lock wrong answers

2. **Add failure handling**
   - Detect "all BFS attempts rejected"
   - Fall back to single-path or RLAC
   - Log warning when locking unvalidated answer

3. **Use only for validation tasks**
   - Don't deploy to solve NEW problems
   - Use for verifying known solutions
   - Use for testing/benchmarking only

**Timeline:** 2-3 days
**Success Metric:** System fails gracefully, clear documentation

---

## 9. Executive Summary: The House of Cards

### Is this a house of cards? **YES.**

**Card 1:** Ground truth must be provided
- Remove this → P0 validation collapses

**Card 2:** BFS must find correct answer first
- Remove this → P1 locks wrong answer

**Card 3:** Verification must not challenge correct answer
- Remove this → 2112 drifts to 2113

**Card 4:** Model must not have systematic formula bias
- Remove this → Converges to 4048 (or 2113)

**All 4 cards must stay standing. Remove any one → system fails.**

### The Real Bug

**We're not fixing WHY the model uses n+2m-2 instead of n+2m-3.**

We're just:
- Rejecting solutions that don't match ground truth (P0)
- Preventing corrections from changing answers (P1)

Neither fix addresses:
- The systematic +1 counting error
- The training bias toward simpler formulas
- The verification system thinking correct proofs need correction

### Can This Ship?

**NO.**

- ❌ Requires ground truth (only works on KNOWN problems)
- ❌ Different behavior in test vs production
- ❌ BFS not robust without proof mode
- ❌ May lock wrong answers based on verification score
- ❌ Underlying formula bug unfixed

**This is test scaffolding to study the bug, not a production fix.**

### What Would Actually Fix This?

**Option 1 (proper fix):** Make model generate correct formula
- Improve prompting for boundary conditions
- Better verification catches +1 errors
- Small-case validation before accepting formulas
- Timeline: 2-4 weeks

**Option 2 (pragmatic):** Make proof mode robust
- Fix prompt engineering
- Problem-aware BFS prompts
- Small-case validation during BFS
- Timeline: 1-2 weeks

**Option 3 (minimal):** Document limitations
- P0+P1 are test-only features
- Don't use on production/new problems
- Add failure handling
- Timeline: 2-3 days

---

## 10. Recommendation: Fast Follow

**IMMEDIATE (TODAY):**
1. ✅ Keep P0+P1 for testing/benchmarking
2. ✅ Add failure handling for "all BFS rejected"
3. ✅ Document ground truth dependency clearly
4. ⚠️ DO NOT deploy to solve new problems

**SHORT TERM (THIS WEEK):**
1. Test formula bug on other Dilworth problems
2. Identify if +1 error is systematic
3. Implement small-case validation in BFS
4. Improve verification prompts for boundary conditions

**MEDIUM TERM (NEXT SPRINT):**
1. Fix verification reliability (don't challenge correct answers)
2. Make BFS prompts problem-aware
3. Add production fallback when ground truth unavailable
4. Run ablation: which fixes actually help?

**SHIP WHEN:**
- System solves Problem 6 WITHOUT ground truth and gets 2112
- Verification doesn't try to "correct" right answers
- BFS generates diverse FORMULAS, not just diverse proofs
- All BFS rejection handled gracefully

**ESTIMATED SHIP DATE:** 2-4 weeks (assuming Strategy A or B)

---

**VERDICT:** This is valuable research scaffolding that reveals the bug, but it's NOT ready to ship. We need to fix the root cause (formula generation), not just the symptoms (wrong answers).

The good news: We now understand the bug. The bad news: We haven't actually fixed it yet.

**Let's build the foundation properly before adding more floors to this house of cards.**
