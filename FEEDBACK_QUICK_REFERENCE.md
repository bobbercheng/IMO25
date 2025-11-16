# Feedback Mechanisms Quick Reference

**TL;DR**: High verification feedback is too sophisticated for low generation to act on. Here are 10 novel approaches to bridge the gap.

---

## The Problem in One Picture

```
┌─────────────────────────────────────────────────────────────┐
│  HIGH VERIFICATION (sophisticated reasoning)                 │
│  "The construction in Lemma 4 requires parity analysis      │
│   which is inconsistently applied across cases..."          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ FEEDBACK GAP
                 │ (Cannot understand/act)
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  LOW GENERATION (simple reasoning)                          │
│  "I don't understand what to fix. Let me try again..."      │
│  [Makes same error 29 iterations later]                     │
└─────────────────────────────────────────────────────────────┘
```

## The Solution: Feedback Translation Layer

Build a TRANSLATOR between high-reasoning verification and low-reasoning generation.

---

## Top 5 Approaches (by ROI)

### 1. Structured JSON Feedback (⭐⭐⭐⭐⭐)

**One sentence**: Convert prose feedback to machine-parsable JSON with error locations, types, and exact fixes.

**Why it works**: Low-reasoning LLMs excel at structured tasks and pattern-matching.

**Example**:
```json
{
  "errors": [{
    "id": "E1",
    "location": "Lemma 4, case a=n-1",
    "type": "LOGIC",
    "severity": 85,
    "current_claim": "point (n-1,1) lies on ℓ_s",
    "correct_version": "point (n-1,1) lies on ℓ_s when n is even, on ℓ_d when n is odd",
    "fix_template": "Split into two cases based on parity of n"
  }],
  "priority_fixes": ["E1", "E3"]
}
```

**Implementation time**: 4-6 hours
**Expected impact**: 60-70% improvement

---

### 2. Top-N Prioritization (⭐⭐⭐⭐⭐)

**One sentence**: Instead of giving all 10+ errors, give only the TOP 3 MOST CRITICAL to fix first.

**Why it works**: Reduces cognitive load, prevents overwhelming the generator, allows incremental progress.

**Example**:
```
Your solution has 12 issues total. Fix these TOP 3 FIRST:

PRIORITY #1: Lemma 1 bound (CRITICAL - blocks 5 other errors)
PRIORITY #2: Construction gap in case a=n-2
PRIORITY #3: Algebra error in slope calculation

Fix ONLY these 3. We'll address remaining issues after re-verification.
```

**Implementation time**: 2-3 hours
**Expected impact**: 50-60% improvement

---

### 3. Example-Based Feedback (⭐⭐⭐⭐)

**One sentence**: Show a concrete worked example of the correct approach instead of abstract description.

**Why it works**: Few-shot learning > zero-shot. Concrete examples bypass need for abstract reasoning.

**Example**:
```
Your claim: "For a=n-1, point (n-1,1) lies on ℓ_s"

WRONG? Let's check with n=5:
- ℓ_s = {y = x - 3}
- Point (4,1): Does 1 = 4-3? YES ✓

So your claim IS correct! But you need to PROVE it.

CORRECT APPROACH (for n=5):
"For a=4, b=1: substitute into y=x-3: 1 = 4-3 ✓"

Now add this same verification to your solution for general n.
```

**Implementation time**: 6-8 hours (includes building example library)
**Expected impact**: 50-55% improvement

---

### 4. Progressive Scoring (⭐⭐⭐⭐)

**One sentence**: Score solutions 0-100 and accept at 85+ threshold instead of requiring 100% perfection.

**Why it works**: Avoids binary cliff, measures incremental progress, accepts "good enough" solutions.

**Example**:
```
SOLUTION SCORE: 78/100

✓ Formatting: 10/10
✓ Structure: 14/15
✓ Lemmas Stated: 15/15
✗ Lemmas Proved: 18/25  ← FOCUS HERE
✗ Construction: 14/20   ← AND HERE
✓ Final Answer: 15/15

THRESHOLD: 85/100
STATUS: NEEDS IMPROVEMENT (7 points away)

Fix Lemmas Proved and Construction to pass.
```

**Implementation time**: 3-4 hours
**Expected impact**: 40-50% improvement

---

### 5. Diff-Based Feedback (⭐⭐⭐⭐)

**One sentence**: Show exact before/after diffs like code review.

**Why it works**: Crystal clear what to change, familiar format, directly actionable.

**Example**:
```diff
Lemma 4, Case a=n-1, b=1:

- The point (n-1,1) lies on ℓ_s because it satisfies the progression.
+ The point (n-1,1) lies on ℓ_s when n is even, and on ℓ_d when n is odd.
+ Proof: For even n, substitute into y = x-(n-2): 1 = (n-1)-(n-2) = 1 ✓
+ For odd n, we have (n-1)+1 = n, which lies on diagonal x+y=n+1.
```

**Implementation time**: 2-3 hours
**Expected impact**: 55-65% improvement

---

## Other Promising Approaches

### 6. Socratic Dialogue (⭐⭐⭐⭐ but expensive)

Multi-turn conversation between verifier and generator.

**Pros**: Extremely effective (70-80% improvement)
**Cons**: 3-5× API cost (use only when stuck)

### 7. Feedback Chains (⭐⭐⭐)

Show error dependencies and fix order.

**Impact**: 45-55% improvement
**Time**: 5-6 hours

### 8. Meta-Feedback (⭐⭐⭐)

Verify generator understood feedback before attempting fix.

**Impact**: 35-45% improvement
**Time**: 4-5 hours

### 9. Visual Feedback (⭐⭐⭐ for geometry)

ASCII diagrams showing what's wrong.

**Impact**: 50% for geometry, 10% for other types
**Time**: 10-12 hours

### 10. Human-in-the-Loop (⭐⭐⭐⭐⭐ backstop)

Request human hint when stuck >3 iterations.

**Impact**: Near 100% with minimal human time
**Time**: 2-3 hours to implement

---

## Combination Strategies

### Strategy A: Fast Fixes
```
JSON + Top-3 + Diff
├─ Structured errors
├─ Prioritized list
└─ Exact changes needed
```
**Use case**: Many small errors, want quick incremental progress

### Strategy B: Deep Learning
```
Examples + Socratic + Meta-feedback
├─ Show worked problems
├─ Guide to understanding
└─ Verify comprehension
```
**Use case**: Conceptual errors requiring deeper understanding

### Strategy C: Production Robust
```
Progressive Scoring + Chains + Human Backstop
├─ Track 0-100 progress
├─ Fix in dependency order
└─ Human unsticks hard cases
```
**Use case**: Need reliable system for arbitrary problems

---

## Quick Experiments (Tonight)

### Experiment 1: JSON Format (2 hours)
```python
# Take failed asymmetric test
# Convert prose feedback → JSON
# Feed to generator
# Measure: Fix quality improvement
```
**Hypothesis**: 2× better corrections

### Experiment 2: Top-3 (1 hour)
```python
# Extract all 10+ errors from log
# Score by impact, take top 3
# Give ONLY top 3 to generator
# Measure: How many auto-resolve?
```
**Hypothesis**: Fixing 3 root causes resolves 5-7 others

### Experiment 3: Examples (3 hours)
```python
# Take one error (e.g., parity gap)
# Create worked example for n=5
# Give example + "generalize" prompt
# Measure: Fix quality vs abstract feedback
```
**Hypothesis**: 70% better fix with concrete example

---

## Decision Tree: Which Approach to Use?

```
How many errors?
├─ 1-3 errors
│   └─ Use: Diff-based feedback
│       (Simple, direct, actionable)
│
├─ 4-7 errors
│   └─ Use: JSON + Top-3 Prioritization
│       (Structured, focused, incremental)
│
├─ 8+ errors
│   └─ Use: Progressive Scoring + Chains
│       (Track progress, fix dependencies)
│
└─ Stuck >3 iterations with same error
    └─ Use: Socratic Dialogue or Human-in-the-Loop
        (Deep intervention needed)

What type of error?
├─ Conceptual/Logic errors
│   └─ Use: Example-based feedback
│       (Show worked similar problem)
│
├─ Algebra/Calculation errors
│   └─ Use: Diff-based feedback
│       (Show exact correction)
│
├─ Construction gaps
│   └─ Use: Visual feedback (if geometry)
│       (Diagram showing gap)
│
└─ Proof structure issues
    └─ Use: JSON + Template
        (Structured fix with scaffolding)
```

---

## Implementation Priority

### Week 1 (6 hours)
1. ✅ Top-N Prioritization (2 hrs)
2. ✅ JSON Structured Feedback (4 hrs)

**Deliverable**: Test on failed asymmetric case
**Expected**: 50-70% improvement

### Week 2 (8 hours)
3. ✅ Diff-Based Feedback (2 hrs)
4. ✅ Progressive Scoring (3 hrs)
5. ✅ Example Library (initial) (3 hrs)

**Deliverable**: Full feedback translation pipeline
**Expected**: Additional 20-30% improvement

### Week 3 (15 hours)
6. ✅ Feedback Chains (5 hrs)
7. ✅ Socratic Dialogue (10 hrs)

**Deliverable**: Robust system for hard cases
**Expected**: Handle 80%+ problems

### Week 4+
8. ✅ Human-in-the-Loop (always available)

**Deliverable**: Production-ready system with backstop

---

## Success Metrics

Track these for each approach:

1. **Fix Accuracy** - % of errors correctly fixed after one iteration
2. **Iterations to Success** - How many cycles needed
3. **Cost per Success** - Total API cost
4. **False Positive Rate** - Accepted solutions that are wrong
5. **False Negative Rate** - Rejected solutions that are correct
6. **Stuck Rate** - % of problems stuck >10 iterations

**Current baseline (asymmetric low/high)**:
- Fix Accuracy: ~30%
- Iterations to Success: FAILED (29 iterations, 6 errors remaining)
- Stuck Rate: 100%

**Target after improvements**:
- Fix Accuracy: >80%
- Iterations to Success: <15
- Stuck Rate: <10%

---

## Key Takeaway

**The asymmetric approach (low gen / high verify) is CORRECT.**

**The problem is NOT the approach—it's the FEEDBACK MECHANISM.**

High verification speaks "PhD-level mathematics."
Low generation speaks "undergraduate-level mathematics."

**We need a TRANSLATOR.**

The best translator:
1. **Structures** the feedback (JSON, not prose)
2. **Simplifies** the feedback (Top-3, not 10+)
3. **Concretizes** the feedback (Examples, not abstractions)
4. **Visualizes** the feedback (Diffs, not descriptions)

Implement these four principles → Bridge the gap → Success.

---

**Next Action**: Run Experiment 1 (JSON format) on the failed asymmetric test case.

**Files**:
- Full analysis: `/home/user/IMO25/FEEDBACK_MECHANISMS_BRAINSTORM.md`
- This reference: `/home/user/IMO25/FEEDBACK_QUICK_REFERENCE.md`
