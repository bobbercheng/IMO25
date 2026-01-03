# Verification Improvement Plan: Add Answer Validation

**Date**: 2025-12-20
**Priority**: CRITICAL - Fixes verification gaps identified by expert panel
**Goal**: Catch global answer errors, not just local proof errors

---

## Problem Statement

### Current Verification System (Flawed)

**What it DOES check:**
- ✅ Proof step validity (algebraic correctness, logical flow)
- ✅ Construction details (line equations, point coverage)
- ✅ Local errors (derivative mistakes, inequality failures)

**What it DOES NOT check:**
- ❌ **Answer correctness against ground truth**
- ❌ **Answer plausibility** (e.g., k ∈ {0,...,n} includes impossible values)
- ❌ **Answer consistency** (different runs produce different answers)

### Evidence of Failure

From expert panel analysis of diagnostic runs:

| Run | Answer Claimed | Verification Verdict | Actual Correctness |
|-----|---------------|---------------------|-------------------|
| Run 1 | k ∈ {0,...,n-2} | ❌ INVALID (Critical Errors) | ❌ WRONG |
| Run 2 | k ∈ {0,...,n-2} | ❌ INVALID (Critical Error) | ❌ WRONG |
| Run 3 | k = {0} only | ❌ INVALID (Critical Error) | ❌ WRONG |
| Run 4 | k ∈ {0,...,n} | ⚠️ **"Essentially Correct"** | ❌ **WRONG** |

**Critical Issue**: Run 4 passed verification despite claiming k=2,4,5,...,n are achievable when they're provably impossible.

---

## Solution: Two-Stage Verification

### Stage 1: Proof Verification (Current System)
- Checks mathematical rigor of proof steps
- Identifies logical fallacies, algebraic errors
- **Verdict**: VALID / JUSTIFICATION GAP / CRITICAL ERROR

### Stage 2: Answer Validation (NEW)
- Checks claimed answer against known constraints
- Tests answer on small cases (n=3, n=4, n=5)
- Compares to ground truth if available
- **Verdict**: CORRECT / PLAUSIBLE / SUSPICIOUS / WRONG

### Combined Verdict Logic

```python
def get_final_verdict(proof_verdict, answer_verdict):
    """
    Proof verification catches HOW you got there.
    Answer validation catches WHETHER you got there.
    """
    if answer_verdict == "WRONG":
        return "INVALID (Wrong Answer)"

    if answer_verdict == "SUSPICIOUS" and proof_verdict == "CRITICAL ERROR":
        return "INVALID (Both Proof and Answer Issues)"

    if proof_verdict == "VALID" and answer_verdict == "CORRECT":
        return "VERIFIED (Rigorous Proof + Correct Answer)"

    if proof_verdict == "JUSTIFICATION GAP" and answer_verdict == "PLAUSIBLE":
        return "ACCEPTABLE (Minor Gaps, Answer Seems OK)"

    # ... more combinations
```

---

## Implementation: Answer Validation System

### Method 1: Small-Case Exhaustive Testing (RECOMMENDED)

**Concept**: For small n, exhaustively test if claimed k values are achievable.

**Example for IMO Problem 1**:
```python
def validate_answer_small_cases(claimed_answer_set, n_test_cases=[3, 4, 5]):
    """
    For each n in test_cases, for each k in claimed answer:
      Try to construct n lines with exactly k sunny lines
      covering all required points.

    If construction fails for any (n, k) pair:
      Return SUSPICIOUS with counterexample
    """

    for n in n_test_cases:
        for k in claimed_answer_set:
            if k > n:
                continue  # Skip impossible k > n

            # Generate T_n = {(a,b) : a,b >= 1, a+b <= n+1}
            points = [(a, b) for a in range(1, n+1)
                            for b in range(1, n+1)
                            if a + b <= n+1]

            # Try to find n lines with exactly k sunny lines covering all points
            success = try_construct_lines(points, n_lines=n, k_sunny=k)

            if not success:
                return {
                    "verdict": "SUSPICIOUS",
                    "counterexample": f"n={n}, k={k} construction failed",
                    "details": f"Could not find {n} lines with {k} sunny covering {len(points)} points"
                }

    return {"verdict": "PLAUSIBLE", "small_cases": "passed"}
```

**Implementation location**: `code/answer_validator.py` (new file)

**Integration point**: After verification in `agent_gpt_oss.py` line ~1200

---

### Method 2: Ground Truth Lookup (When Available)

**Concept**: For known IMO problems, check against official solutions.

```python
GROUND_TRUTH = {
    "imo2025_p1": {
        "answer": {0, 1, 3},  # k ∈ {0, 1, 3} only
        "source": "IMO 2025 Official Solution",
        "confidence": "DEFINITIVE"
    },
    # Add more as we discover correct answers
}

def validate_against_ground_truth(problem_id, claimed_answer):
    """
    If ground truth exists, check claimed answer against it.
    """
    if problem_id not in GROUND_TRUTH:
        return {"verdict": "NO_GROUND_TRUTH"}

    truth = GROUND_TRUTH[problem_id]
    claimed_set = parse_answer_to_set(claimed_answer)

    if claimed_set == truth["answer"]:
        return {
            "verdict": "CORRECT",
            "source": truth["source"],
            "confidence": truth["confidence"]
        }

    # Check for subset/superset relationships
    if claimed_set.issubset(truth["answer"]):
        return {
            "verdict": "INCOMPLETE",
            "missing": truth["answer"] - claimed_set,
            "source": truth["source"]
        }

    if truth["answer"].issubset(claimed_set):
        return {
            "verdict": "OVERGENERALIZED",
            "extra": claimed_set - truth["answer"],
            "source": truth["source"]
        }

    return {
        "verdict": "WRONG",
        "correct_answer": truth["answer"],
        "claimed_answer": claimed_set,
        "source": truth["source"]
    }
```

**Implementation location**: `code/ground_truth.py` (new file)

---

### Method 3: Plausibility Heuristics

**Concept**: Catch obviously wrong answers without exhaustive testing.

```python
def check_answer_plausibility(claimed_answer, problem_type):
    """
    Sanity checks for different problem types.
    """
    issues = []

    # For IMO P1 (sunny lines problem):
    if problem_type == "imo2025_p1":
        # Parse answer (e.g., "k ∈ {0,1,...,n}")
        claimed_set = parse_answer_to_set(claimed_answer)

        # Heuristic 1: k should be bounded by n
        if any(k > 1000 for k in claimed_set):
            issues.append("Answer includes arbitrarily large k (unbounded)")

        # Heuristic 2: If answer is k ∈ {0,...,m}, check if m is reasonable
        if is_consecutive_sequence(claimed_set):
            max_k = max(claimed_set)
            if max_k >= 100:  # No IMO problem has such large answers
                issues.append(f"Consecutive sequence up to {max_k} seems implausibly large")

        # Heuristic 3: Check for gaps (e.g., {0,1,3} has gap at 2)
        if has_gaps(claimed_set):
            # This is actually EXPECTED for IMO P1! k=2 is impossible
            # But worth flagging for agent attention
            issues.append(f"Answer has gaps: {identify_gaps(claimed_set)}")

    if issues:
        return {"verdict": "NEEDS_REVIEW", "issues": issues}

    return {"verdict": "PLAUSIBLE"}
```

---

## Integration Plan

### Step 1: Create Answer Validation Module

**File**: `code/answer_validator.py`

```python
"""
Answer Validation System for IMO Solutions

Validates claimed answers against:
- Small-case exhaustive testing
- Ground truth (when available)
- Plausibility heuristics
"""

import re
from typing import Set, Dict, Any, List

class AnswerValidator:
    def __init__(self, problem_id: str):
        self.problem_id = problem_id
        self.ground_truth = self.load_ground_truth()

    def validate(self, claimed_answer: str, solution_text: str) -> Dict[str, Any]:
        """
        Main validation entry point.

        Returns:
            {
                "verdict": "CORRECT" | "PLAUSIBLE" | "SUSPICIOUS" | "WRONG",
                "confidence": 0.0-1.0,
                "details": {...}
            }
        """
        results = {}

        # Method 1: Ground truth check (highest confidence)
        if self.ground_truth:
            results["ground_truth"] = self.check_ground_truth(claimed_answer)
            if results["ground_truth"]["verdict"] in ["CORRECT", "WRONG"]:
                return results["ground_truth"]  # Definitive verdict

        # Method 2: Small-case testing (medium confidence)
        results["small_cases"] = self.test_small_cases(claimed_answer)
        if results["small_cases"]["verdict"] == "SUSPICIOUS":
            return results["small_cases"]  # Found counterexample

        # Method 3: Plausibility (low confidence)
        results["plausibility"] = self.check_plausibility(claimed_answer)

        # Combine verdicts
        return self.combine_verdicts(results)

    def check_ground_truth(self, claimed_answer: str) -> Dict:
        """Check against known correct answer."""
        # Implementation from Method 2 above
        pass

    def test_small_cases(self, claimed_answer: str) -> Dict:
        """Exhaustive testing on small n."""
        # Implementation from Method 1 above
        pass

    def check_plausibility(self, claimed_answer: str) -> Dict:
        """Sanity checks."""
        # Implementation from Method 3 above
        pass
```

---

### Step 2: Modify Verification in `agent_gpt_oss.py`

**Location**: Around line 1200 (after verification completion)

**Current code**:
```python
def verify_solution(solution_text, problem_statement, reasoning_effort=None):
    # ... existing verification code ...

    verdict = parse_verification_verdict(verification_response)

    return {
        "verdict": verdict,  # e.g., "VALID", "CRITICAL ERROR"
        "feedback": verification_response
    }
```

**Modified code**:
```python
from answer_validator import AnswerValidator

def verify_solution(solution_text, problem_statement, reasoning_effort=None, problem_id=None):
    # Stage 1: Proof verification (existing)
    proof_result = run_proof_verification(solution_text, problem_statement, reasoning_effort)

    # Stage 2: Answer validation (NEW)
    answer_result = None
    if problem_id:
        validator = AnswerValidator(problem_id)
        answer_result = validator.validate(
            claimed_answer=extract_final_answer(solution_text),
            solution_text=solution_text
        )

    # Combine verdicts
    combined = combine_verification_results(proof_result, answer_result)

    return {
        "proof_verification": proof_result,
        "answer_validation": answer_result,
        "final_verdict": combined["verdict"],
        "feedback": combined["feedback"]
    }
```

---

### Step 3: Update Verification Prompts

**Add to verification system prompt**:
```
### Answer Validation Instructions ###

After verifying the proof steps, you MUST also validate the final answer:

1. **Extract the claimed answer** from the solution
   - For "determine all k such that..." problems, identify the set of k values

2. **Check answer plausibility**:
   - Is the answer bounded? (e.g., k ≤ n for n-line problems)
   - Are there suspicious patterns? (e.g., k ∈ {0,1,...,1000})
   - Does the answer have gaps? (e.g., {0,1,3} - why not k=2?)

3. **Test on small cases** (if applicable):
   - For n=3, is each claimed k actually achievable?
   - For n=4, does the construction work?
   - If you find a counterexample, report it explicitly

4. **State answer verdict separately**:
   - "ANSWER: CORRECT" if you're confident it's right
   - "ANSWER: PLAUSIBLE" if it seems reasonable but unverified
   - "ANSWER: SUSPICIOUS (counterexample: ...)" if construction fails
   - "ANSWER: WRONG (correct answer is ...)" if you know the ground truth
```

---

## Testing Plan

### Phase 1: Validation on Historical Failures

Test the answer validator on the 4 diagnostic runs:

```bash
python code/test_answer_validator.py \
  --runs diagnostic_results/test1_control_*_20251219_163333.json
```

**Expected results**:
- Run 1: k ∈ {0,...,n-2} → VERDICT: WRONG (correct is {0,1,3})
- Run 2: k ∈ {0,...,n-2} → VERDICT: WRONG (correct is {0,1,3})
- Run 3: k = {0} → VERDICT: INCOMPLETE (missing k=1,3)
- Run 4: k ∈ {0,...,n} → VERDICT: OVERGENERALIZED (extra: {2,4,5,...,n})

**Success criterion**: All 4 runs flagged as incorrect ✅

---

### Phase 2: Integration Testing

Run a single BFS test with answer validation enabled:

```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --log test_validation.log \
  --memory test_validation.json \
  --problem-id imo2025_p1 \
  --enable-answer-validation
```

**Expected**: Verification includes both proof check AND answer check

---

### Phase 3: N=12 BFS Baseline

After validation confirmed working, run full baseline:

```bash
./run_bfs_baseline.sh
```

---

## Ground Truth Database

**File**: `code/ground_truth.py`

```python
GROUND_TRUTH = {
    "imo2025_p1": {
        "problem": "Sunny lines problem",
        "answer": {0, 1, 3},
        "source": "IMO 2025 Official Solution (verified by expert panel)",
        "last_updated": "2025-12-20",
        "notes": [
            "k=0: All n diagonals x+y=c (none sunny)",
            "k=1: Replace one diagonal with one sunny line",
            "k=2: IMPOSSIBLE - geometric constraints prevent coverage",
            "k=3: Novel construction with 3 specific sunny lines",
            "k≥4: IMPOSSIBLE - upper bound proof (boundary point argument)"
        ]
    },

    # Template for future problems
    # "imo2025_p2": {
    #     "problem": "...",
    #     "answer": ...,
    #     "source": "...",
    #     "last_updated": "...",
    #     "notes": [...]
    # }
}
```

---

## Success Metrics

### Metric 1: Catch Rate on Historical Failures
- **Target**: 100% of 10 historical failed runs flagged as incorrect
- **Current**: 0% (verification passed Run 4 despite wrong answer)
- **After fix**: Should flag all 10 as WRONG/SUSPICIOUS

### Metric 2: False Positive Rate
- **Target**: <5% (don't flag correct answers as wrong)
- **Test**: Run on known correct solutions
- **Mitigation**: Use "PLAUSIBLE" for uncertain cases, not "WRONG"

### Metric 3: Integration Success
- **Target**: BFS baseline runs complete without validator errors
- **Test**: N=12 baseline completes successfully
- **Metric**: 0 crashes, 12 valid verdicts

---

## Timeline

| Phase | Task | Duration | Owner |
|-------|------|----------|-------|
| 1 | Create `answer_validator.py` | 2 hours | Claude |
| 2 | Create `ground_truth.py` | 30 min | Claude |
| 3 | Integrate into `agent_gpt_oss.py` | 1 hour | Claude |
| 4 | Test on 4 diagnostic runs | 30 min | Claude |
| 5 | Integration test (1 BFS run) | 20 min | User |
| 6 | Create `run_bfs_baseline.sh` | 1 hour | Claude |
| 7 | Run N=12 BFS baseline | 3-4 hours | User |
| **Total** | | **~9 hours** | |

---

## Risk Mitigation

### Risk 1: Ground Truth Might Be Wrong
**Mitigation**:
- Use FOUR_FAILED_TESTS_ANALYSIS.md as source (expert panel verified)
- Add confidence levels to ground truth
- Allow override with `--ignore-ground-truth` flag

### Risk 2: Small-Case Testing Too Slow
**Mitigation**:
- Limit to n=3,4,5 (not n=100)
- Use heuristic construction, not brute force
- Cache results for common (n,k) pairs

### Risk 3: Answer Parsing Failures
**Mitigation**:
- Robust regex for "k ∈ {0,1,...,n}" formats
- Handle multiple answer formats (set notation, interval notation)
- Log parsing failures for manual review

---

## Expected Impact

### Before Fix (Diagnostic Runs):
- 4/4 runs produced wrong answers
- 1/4 runs passed verification despite wrong answer
- No feedback on answer incorrectness

### After Fix (BFS Baseline):
- Expect 8-12/12 runs to produce correct/plausible answers
- 0/12 runs should pass with wrong answer (validator catches it)
- Feedback: "Your answer k ∈ {0,...,n} is WRONG. Correct is k ∈ {0,1,3}."

---

**Priority**: CRITICAL
**Status**: Design complete, ready for implementation
**Next Step**: Implement `answer_validator.py`
