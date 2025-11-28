# Executive Summary: RLAC Scaling Strategy

**TL;DR**: RLAC achieves format compliance but fails mathematical correctness. Implement **Beam Search with Empirical Verification** for 2.2× success rate improvement at 2.3× cost. Quick wins available in Week 1.

---

## The Problem

After P0+P1 fixes, RLAC successfully achieves:
- ✅ 3 consecutive ROBUST verdicts
- ✅ Format compliance (no truncation, valid structure)
- ❌ **Mathematical correctness FAILS**

### Test Results

**Problem 1 (Sunny Lines)**:
- Solution: `k=0 or k odd with 1≤k≤n` ❌
- Correct: `k∈{0,1,n-1}` ✓
- **Error**: Claimed ALL odd k work, but only k=1 and k=n-1 work

**Problem 2 (Geometry)**:
- Solution: Coordinate geometry proof ❌
- **Error**: Logical gaps in algebraic verification

### Root Cause

**The adversarial critic doesn't know the ground truth.**

It can only verify:
- ✅ Logical consistency ("Does the proof follow from premises?")
- ❌ Mathematical correctness ("Is the answer actually right?")

**For Problem 1**:
- Critic tested n=3,4,5 with k∈{0,1,3} → All VALID ✓
- Critic did NOT test that k=3 FAILS for n=5
- Critic only verified cases the solution CLAIMED work, not ALL possible cases

**Missing capability**: **Exhaustive empirical verification**

---

## Recommended Solution: Beam Search + Empirical Verification

### Why Beam Search?

1. **Maintains multiple candidate answers** simultaneously
2. **Empirical verification** prunes wrong answers early
3. **Parallelizable** (can run all candidates simultaneously)
4. **Simple to implement** (3-4 weeks)
5. **Best ROI**: 2.2× success for 2.3× cost

### Architecture

```
Problem: "Determine all k such that..."
         ↓
Generate 10 candidate answers:
  [1] k ∈ [0, n-2]
  [2] k = all odd
  [3] k ∈ {0, 1}
  [4] k ∈ {0, 1, n-1}  ← Correct!
  [5] k ∈ {0, 1, n-1, n}
  ... etc
         ↓
Quick empirical test (5 test cases each):
  [1] Score: 0.71
  [2] Score: 0.67
  [3] Score: 0.55
  [4] Score: 0.95  ← Highest!
  [5] Score: 0.82
         ↓
Keep top-5 (beam width = 5):
  [4] k ∈ {0, 1, n-1}
  [5] k ∈ {0, 1, n-1, n}
  [1] k ∈ [0, n-2]
  [2] k = all odd
  [3] k ∈ {0, 1}
         ↓
For each: Generate proof + RLAC refinement (10 rounds)
         ↓
Deep empirical verification (20 test cases)
         ↓
Select highest-scoring answer
         ↓
Output: k ∈ {0, 1, n-1} (Score: 0.95)
```

### Expected Results

| Metric | Current RLAC | Beam Search | Improvement |
|--------|-------------|-------------|-------------|
| Success Rate | 30% | 65% | +35% absolute, +117% relative |
| Cost per Problem | $12 | $28 | 2.3× |
| Cost per Success | $40 | $43 | 1.1× (acceptable) |
| Time | 15 min | 25 min | 1.7× |

**Key insight**: Even though cost per problem increases 2.3×, cost per SUCCESS only increases 1.1× because success rate more than doubles.

---

## Quick Wins (Week 1-2)

### Priority 1: Add Empirical Verification to Critic ⭐⭐⭐

**Impact**: +15-20% success rate
**Effort**: 1 week
**Cost**: $0 (engineering time only)

**What it does**:
- For "Determine all k" problems, systematically test ALL k values for small n
- Compare solution's claim vs. actual construction feasibility
- Report mismatches as COUNTEREXAMPLES

**Implementation**: See `IMPLEMENTATION_GUIDE.md`

**This alone would have caught Problem 1's error!**

### Priority 2: Increase Critic Reasoning Effort ⭐⭐

**Impact**: +5-10% success rate
**Effort**: 0 weeks (config change)
**Cost**: 3× per problem ($12 → $37)

**What to do**:
```bash
export RLAC_CRITIC_REASONING=high  # Was: medium
```

**Why it helps**:
- Longer thinking time enables deeper logical exploration
- Better pattern recognition
- More systematic case enumeration

### Priority 3: Exhaustive Boundary Testing ⭐⭐

**Impact**: +5% success rate
**Effort**: 0.5 weeks
**Cost**: $0

**What to do**:
- Test n=3,4,5,6,7,8,9,10 systematically (not just n=3,4,5)
- Cover more edge cases
- Catch patterns that only emerge for larger n

**Combined impact of Quick Wins**: 30% → 45% success rate in 1.5 weeks

---

## Scaling Roadmap

### Phase 1: Quick Wins (Weeks 1-2)
- ✅ Empirical verification in critic
- ✅ Higher reasoning effort
- ✅ Exhaustive boundary testing
- **Target**: 45% success rate

### Phase 2: Beam Search (Weeks 3-6)
- ✅ Beam search framework
- ✅ Construction verifiers for top problem classes
- ✅ Integration and testing
- **Target**: 65% success rate

### Phase 3: MCTS (Weeks 7-12)
- ✅ MCTS framework with UCB1 selection
- ✅ Answer space exploration
- ✅ Adaptive search
- **Target**: 70% success rate

### Phase 4: Formal Verification (Weeks 13-24)
- ✅ Lean 4 translation engine
- ✅ Gap extraction and feedback
- ✅ Hybrid RLAC+MCTS+Formal system
- **Target**: 85% success rate

---

## Cost-Benefit Summary

| Strategy | Success | Cost | Effort | Risk | ROI | Recommendation |
|----------|---------|------|--------|------|-----|----------------|
| **Quick Wins** | 45% | $37 | 1.5 wks | Low | ⭐⭐⭐ | **Do now** |
| **Beam Search** | 65% | $28 | 4 wks | Low | ⭐⭐⭐ | **Do month 1** |
| MCTS | 70% | $60 | 6 wks | Med | ⭐⭐ | Do month 2 |
| Hybrid | 85% | $40 | 12 wks | High | ⭐⭐⭐ | Do month 3 (goal) |

**Recommended priority**: Quick Wins → Beam Search → MCTS → Hybrid

---

## Specific Problem Analysis

### Problem 1: How Beam Search Would Have Caught This

**Current RLAC**:
```
Round 1-21: Try different constructions, all claim "k=all odd"
Round 22-24: Critic tests n=3,4,5 with k∈{0,1,3} → All work ✓
Verdict: ROBUST (wrong!)
```

**Beam Search**:
```
Step 1: Generate candidates
  [1] k=all odd
  [2] k∈{0,1,n-1}
  [3] k∈[0,n-2]

Step 2: Test n=5, try all k:
  [1] k=all odd
      k=0 ✓, k=1 ✓, k=2 ✗, k=3 ✗ ← FAILS!
      k=4 ✓, k=5 ✓
      Score: 4/6 = 0.67 → SUSPICIOUS

  [2] k∈{0,1,n-1}
      k=0 ✓, k=1 ✓, k=2 ✗, k=3 ✗, k=4 ✓, k=5 ✗
      Score: 4/6 = 0.67 (but correct on pattern)

  [3] k∈[0,n-2]
      k=0 ✓, k=1 ✓, k=2 ✗, k=3 ✗, k=4 ✗ ← FAILS!
      Score: 2/6 = 0.33 → PRUNE

Step 3: More testing reveals [2] is correct
```

**Key difference**: Beam Search tests ALL possible k, not just the ones the solution claims work.

### Problem 2: How Symbolic Verification Would Help

**Current RLAC**:
```
Solution claims: "discriminant β² - αγ = 0"
Critic checks: Algebraic steps look logical ✓
Verdict: ROBUST (but proof has gaps)
```

**Enhanced Critic with SymPy**:
```python
import sympy
# Extract symbolic expressions
disc = sympy.simplify(beta**2 - alpha*gamma)

if disc != 0:
    return "BROKEN: Discriminant not identically zero"
```

**This would catch**:
- Algebraic manipulation errors
- Missing conditions for identities
- Geometric degeneracies

---

## Action Items

### This Week
1. ✅ Read full analysis: `RLAC_SCALING_STRATEGY_ANALYSIS.md`
2. ✅ Review implementation guide: `IMPLEMENTATION_GUIDE.md`
3. ✅ Implement empirical verification in critic (Priority 1)
4. ✅ Test on Problem 1 and 2 to verify it catches errors

### Next 2 Weeks
1. ✅ Increase critic reasoning to HIGH
2. ✅ Add exhaustive boundary testing
3. ✅ Measure success rate improvement (target: 45%)

### Month 1
1. ✅ Implement Beam Search framework
2. ✅ Build construction verifiers for 3-5 problem classes
3. ✅ Achieve 60-65% success rate

### Month 2-3
1. ✅ Implement MCTS (if Beam Search successful)
2. ✅ Begin formal verification integration
3. ✅ Target 80-90% success rate

---

## Key Takeaways

1. **Root cause**: Adversarial critic lacks ground truth verification
2. **Solution**: Empirical testing of candidate answers
3. **Strategy**: Beam Search (best ROI) → MCTS → Hybrid
4. **Quick wins**: +15-20% success in 1 week (empirical verification)
5. **Long-term**: 2.8× success rate improvement with hybrid system

**Bottom line**: We can achieve IMO-level mathematical reasoning by combining adversarial refinement (RLAC) with systematic answer space search (Beam/MCTS) and formal verification. Start with quick wins, build progressively.

---

**Next Steps**: See `IMPLEMENTATION_GUIDE.md` for detailed code and instructions to implement Priority 1 (empirical verification) this week.
