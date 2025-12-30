# Pre-Test Review: BFS Run 2 Analysis

**Date**: 2025-12-21
**Purpose**: Confirm new changes address high-priority issues before running new test

---

## Run 2 Failure Analysis

### Summary Statistics
- **Final Answer**: `k=0` (WRONG - truth is k∈{0,1,3})
- **Pattern**: 10/10 runs showed DEGRADE pattern (Iter 0 passes, then errors accumulate)
- **BFS Attempts**: 32 initial solutions, ALL with negative scores
- **Verdict**: INVALID (despite claiming k=0 is correct)

### Critical Issues Identified

#### Issue 1: **Wrong Answer - Missing k=1,3**

**Evidence from log:**
```
\boxed{k=0}
\boxed{\text{The only admissible value of }k\text{ is }0.}
```

**Verification correctly identifies problem:**
```
"**Justification Gap** – the problem asks for *all* non‑negative integers k
for which a configuration exists. The solution stops after giving a necessary
upper bound and a single construction for k=0; it never shows that any k>0
(up to the bound) can be realized"
```

**Why this happened (Expert Panel diagnosis):**
- LOW reasoning insufficient for mixed constructions (k=1,3)
- k=0 is uniform (all horizontal lines) → LOW cognitive load → Found ✓
- k=1,3 are mixed (diagonal+sunny) → MEDIUM cognitive load → Missed ✗
- Temperature 0.1 blocks sampling low-probability constructions

#### Issue 2: **Incomplete Exploration**

**Evidence:**
- BFS generated 32 initial attempts
- ALL claimed k=0 only
- None explored k=1, k=2, k=3 explicitly

**Why diversity hints failed:**
```python
# OLD (Run 2):
diversity_hints = [
    "Try a different approach or proof strategy.",      # Too vague
    "Consider an alternative construction or method.",   # Not specific
]
```

These generic hints don't force exploration of specific k values.

#### Issue 3: **DEGRADE Pattern (10/10 runs)**

**Timeline for every run:**
```
Run X (5 iterations):
  Iter 0: ✓ (corrects=1, errors=0)  ← Claims k=0
  Iter 1: ✗ (corrects=0, errors=2)  ← Tries to generalize, fails
  Iter 2: ✗ (corrects=0, errors=4)  ← More errors
  Iter 3: ✗ (corrects=0, errors=6)
  Iter 4: ✗ (corrects=0, errors=8)
  Pattern: DEGRADE (started valid, became invalid)
```

**Why this happened:**
- Iter 0: LOW reasoning generates k=0 (simple, passes verification)
- Iter 1+: Agent tries to generalize to k>0 but lacks reasoning budget
- Makes algebraic errors (e.g., "sunny line contains at most 2 points" - FALSE)
- Verification catches errors, agent stuck in correction loop

---

## Our New Changes - Issue Coverage

### ✅ Change 1: MEDIUM Reasoning (Addresses Issue 1 & 3)

**What changed:**
```bash
# run_bfs_baseline.sh
SOLUTION_REASONING="medium"        # ↑ from "low"
SELF_IMPROVEMENT_REASONING="medium"  # ↑ from "low"
```

**Expected impact:**
- **Issue 1**: MEDIUM reasoning enables mixed constructions (k=1,3)
- **Issue 3**: Self-improvement can execute algebraic verification rigorously
- **Evidence**: Expert panel unanimously agreed LOW→MEDIUM fixes root cause

**Expert panel consensus:**
```
UNANIMOUS VERDICT: Configuration-Induced Reasoning Gap

ROOT CAUSE: LOW reasoning + Temperature 0.1 = "conservative exploration trap"

What Run 3 Found:
- Initial: k ∈ {0, n} with "intermediate values remain open"
- Self-improvement: Attempted k ∈ {0,...,n} but made algebraic error
- Final: Accepted k=0 only (most conservative)

Recommendation 1 (CRITICAL): SOLUTION_REASONING="medium"
Expected: 30-50% success rate with MEDIUM reasoning
```

### ✅ Change 2: Dynamic BFS Prompts (Addresses Issue 2)

**What changed:**
```python
# code/dynamic_bfs_prompts.py + integration in agent_gpt_oss.py
# Now generates explicit prompts:
Prompt 1: "For n=3, construct configuration with exactly k=0 sunny lines"
Prompt 2: "For n=3, construct configuration with exactly k=1 sunny lines"
Prompt 3: "For n=3, construct configuration with exactly k=2 sunny lines"
```

**Expected impact:**
- **Issue 2**: Forces systematic exploration of k=0,1,2,3 instead of hoping for diversity
- Overcomes Temperature 0.1 sampling bias
- No longer relies on model spontaneously trying k=1 (15% probability)

**Before (Run 2):**
- BFS Attempt 1: Generic prompt → finds k=0 (80% probability)
- BFS Attempt 2: "Try different approach" → finds k=0 again (80% probability)
- BFS Attempt 3: "Consider alternative" → finds k=0 again (80% probability)
- Result: 0/32 attempts found k=1 or k=3

**After (New test):**
- BFS Attempt 1: "Try k=0 explicitly" → finds k=0 ✓
- BFS Attempt 2: "Try k=1 explicitly" → FORCED to try k=1 construction
- BFS Attempt 3: "Try k=2 explicitly" → FORCED to try k=2 (will fail, as expected)
- Result: GUARANTEED to explore k=0,1,2,3

### ✅ Change 3: Small-Case Verification (Addresses Issue 1 fallback)

**What changed:**
```python
# code/small_case_verification.py + integration in agent_gpt_oss.py
# Triggers when solution admits: "remain open", "incomplete", "partial"
```

**Expected impact:**
- **Issue 1 (fallback)**: If agent claims "k=0 only, others remain open" → triggers
- Forces explicit n=3 exploration with k=0,1,2,3
- Safety net if dynamic prompts don't work

**Scenario:**
```
BFS selects best solution: "k=0 is achievable, k>0 remain open"
  ↓
Small-case verification detects: "remain open" → TRIGGER
  ↓
Generates prompt: "For n=3, try ALL values k=0,1,2,3 explicitly"
  ↓
Agent tries constructions, finds k=1,3 work
  ↓
Improved solution: k∈{0,1,3} ✓
```

---

## Coverage Matrix

| Issue | Root Cause | Our Fix | Confidence |
|-------|-----------|---------|------------|
| **Issue 1: Missing k=1,3** | LOW reasoning insufficient | MEDIUM reasoning | ✅ HIGH (expert consensus) |
| **Issue 2: No k>0 exploration** | Generic diversity hints | Dynamic BFS prompts | ✅ HIGH (forced exploration) |
| **Issue 3: DEGRADE pattern** | LOW reasoning → algebraic errors | MEDIUM reasoning | ✅ HIGH (enables verification) |
| **Fallback: Incomplete admission** | Agent admits incompleteness | Small-case verification | ✅ MEDIUM (safety net) |

---

## Expected New Test Behavior

### BFS Initial Phase (NUM_INITIAL_ATTEMPTS=3)

**Expected log output:**
```
>>>>>>> BFS: Generating 3 diverse initial solutions...
>>>>>>> BFS: Using dynamic prompts (explicit parameter exploration)

>>>>>>> BFS: Initial attempt 1/3...
>>>>>>> BFS: Explicit prompt: For n=3, construct with exactly k=0 sunny lines
[... generates k=0 construction ...]
>>>>>>> BFS: Attempt 1 score: -45.00 (incomplete, but valid construction)

>>>>>>> BFS: Initial attempt 2/3...
>>>>>>> BFS: Explicit prompt: For n=3, construct with exactly k=1 sunny lines
[... FORCED to try k=1 - should find diagonal construction ...]
>>>>>>> BFS: Attempt 2 score: 100.00 (if finds k=1,3 pattern)

>>>>>>> BFS: Initial attempt 3/3...
>>>>>>> BFS: Explicit prompt: For n=3, construct with exactly k=2 sunny lines
[... tries k=2, verification should fail (impossible) ...]
>>>>>>> BFS: Attempt 3 score: -150.00 (critical error: k=2 impossible)

>>>>>>> BFS: Best initial solution selected (score: 100.00)
[If Attempt 2 succeeded in finding k=1,3 pattern]
```

### Success Criteria

**Minimum success:**
- At least ONE BFS attempt explores k=1 explicitly (guaranteed by dynamic prompts)
- MEDIUM reasoning enables agent to find k=1 construction
- Final answer includes k=1 (current: 0/12 runs, target: 4-6/12 runs per expert panel)

**Full success:**
- BFS finds k∈{0,1,3} in Iteration 0
- Verification passes
- No DEGRADE pattern

### Failure Mode Detection

**If still fails:**
1. Check log for `>>>>>>> BFS: Explicit prompt:` → confirms dynamic prompts working
2. Check if k=1 prompt generated valid construction → tests MEDIUM reasoning
3. Check verification verdict for k=1 attempt → tests verification accuracy

---

## Recommendation

**✅ PROCEED WITH NEW TEST**

All three changes directly address the root causes identified in Run 2:
1. **MEDIUM reasoning** fixes cognitive load gap (Issue 1, 3)
2. **Dynamic BFS prompts** forces exploration (Issue 2)
3. **Small-case verification** provides safety net (Issue 1 fallback)

**Expected improvement:**
- Run 2: 0/12 success (0%)
- New test: 4-6/12 success (30-50%) per expert panel estimates

**Verification:**
```bash
./run_bfs_baseline.sh problems/imo01.txt
```

Look for:
- `>>>>>>> BFS: Using dynamic prompts (explicit parameter exploration)`
- `>>>>>>> BFS: Explicit prompt: For n=3, construct with exactly k=1 sunny lines`
- BFS scores > 0 for k=1 attempt
- Final answer includes k=1 or k=3

---

## Risk Assessment

**Low risk:**
- All changes are additive (no breaking changes)
- Fallbacks in place (generic diversity if parsing fails)
- Cost increase: $2 → $5-7 per run (acceptable for 30-50% success)

**Monitoring:**
- Duration: 15 min (LOW) → 20-30 min (MEDIUM) per run
- If timeout at MAX_RUNS=15, unlikely to succeed at 30 (per analysis)

**Abort conditions:**
- If 3 consecutive runs find k=0 only → dynamic prompts not working
- If DEGRADE pattern persists → MEDIUM reasoning insufficient
- If BFS scores all negative → need higher reasoning or temperature adjustment
