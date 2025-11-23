# RLAC Feedback Loop Analysis - Quick Summary

## The Problem (from the log)

Generator starts with: **k ∈ {0,1,2,...,n}** (correct answer)
↓ Gets attacked by Critic with counterexamples proving k=1, k=2 work
↓ Generator now claims: **k ∈ {0,n}** ONLY (wrong answer!)

**The signal from Critic to Generator is NOT being acted upon.**

---

## 5-Point Failure Analysis

### 1. Counterexample Clarity ✓ PASS
- Critic IS providing clear counterexamples
- Critic IS explicitly showing k=1, k=2 are achievable
- Grade: **A+**

### 2. Signal vs Noise ✗ CRITICAL FAIL
The Critic says "here's a counterexample" but NOT "change your answer to X"
- Missing: "Your answer k∈{0,n} is WRONG"
- Missing: "Your new answer must be k∈{0,1,...,n}"
- Generator receives **criticism** not **correction directives**

### 3. Parsing & Understanding ✗ CRITICAL FAIL
Code in `agent_rlac.py` lines 203-216 just reports flaws:
```python
formatted.append(f"Counterexample: {flaw.counterexample}")
```

**Missing:**
- No explicit mapping from "counterexample proves k=1" to "answer must include k=1"
- The Flaw dataclass doesn't track "what the answer should change to"
- Generator has to infer 4+ levels: see flaw → understand meaning → infer answer → change code

### 4. Defense vs Acceptance ✗ MAJOR FAIL
Code in `agent_rlac.py` lines 541-543:
```python
if (all(f.severity == 'minor' for f in criticism.flaws) and iteration >= 5):
    return success_with_minor_flaws
```

**The Problem:** System only checks if flaws are "minor", NOT if answer is correct
- Generator can ignore counterexamples and just "defend" the wrong answer
- System accepts it as long as flaws aren't critical
- **No enforcement that answer matches counterexample evidence**

### 5. Termination Conditions ✗ STRUCTURAL FAIL
System has no mechanism to force answer change:
```python
# Missing:
if extracted_answer != evidence_from_counterexamples:
    raise AnswerMismatchError("Answer doesn't match proven evidence")
```

The system terminates on "ROBUST verdict" but allows Generator to defend WRONG answers.

---

## Root Cause

**Criticism without correction directives.**

The system tells Generator "your answer is wrong" but not "change it to X"
→ Generator doesn't know what answer to produce
→ Generator keeps defending the old answer
→ System accepts it as "defended"

---

## The Core Fix (5 Changes)

### Fix 1: Enriched Flaw Format
Add to Flaw dataclass:
```python
answer_correction: str  # "Change from {0,n} to {0,1,...,n}"
answer_requirement: str  # "Answer must include k=1"
```

### Fix 2: Extract Final Answer
New function to extract answer from solution:
```python
extracted_answer = extract_final_answer(solution)  # returns {0,1,2,...,n}
```

### Fix 3: Validate Answer Against Evidence
New validation:
```python
validate_answer_against_counterexamples(solution, counterexamples)
# Raises error if answer doesn't include proven k values
```

### Fix 4: Enhanced Revision Prompt
Tell Generator explicitly:
```
Your previous answer: k ∈ {0,n}
Counterexample proves: k=1 is achievable
REQUIRED NEW ANSWER: k ∈ {0,1,...,n}
This is NOT OPTIONAL.
```

### Fix 5: Acceptance Enforcement
Check answer correctness before acceptance:
```python
if extracted_answer != evidence_based_answer:
    REJECT  # Don't accept wrong answers
```

---

## Implementation Locations

| Component | File | Lines | What to Change |
|-----------|------|-------|-----------------|
| Flaw format | agent_rlac.py | 21-30 | Add answer_correction field |
| Formatting | agent_rlac.py | 203-216 | Include directives in output |
| Revision prompt | agent_rlac.py | 115-176 | Add explicit requirements |
| Acceptance | agent_rlac.py | 478-559 | Validate answer vs evidence |
| New functions | - | - | extract_final_answer(), validate_answer_against_counterexamples() |

---

## Why This Matters

Current system:
```
Critic: "k=1 is achievable"
Generator: *writes more defense notes*
System: "Flaws are still critical, continue..."
Generator: *keeps claiming {0,n}*
```

Fixed system:
```
Critic: "k=1 is achievable → answer must include k=1"
Generator: *updates answer to {0,1,...,n}*
System: *validates answer matches evidence*
System: "Accepted ✓"
```

---

## Bottom Line

**The counterexample signal IS clear.** The problem is converting that signal into an answer update.

The system needs to:
1. Translate counterexamples → answer requirements
2. Extract and verify final answers
3. Enforce consistency between answer and evidence
4. Reject solutions that contradict their own counterexamples

**Without this, the feedback loop remains broken.**

See `RLAC_FEEDBACK_LOOP_ANALYSIS.md` for detailed analysis with code examples.
