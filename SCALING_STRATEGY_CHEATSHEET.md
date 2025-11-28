# RLAC Scaling Strategy - Quick Reference Cheat Sheet

---

## The Problem in One Sentence

**RLAC achieves 3 consecutive ROBUST verdicts but the math is WRONG because the critic can't verify ground truth.**

---

## Root Cause

```
┌─────────────────────────────────────────────────────────────┐
│ Adversarial Critic Can Check:                              │
│   ✅ "Is the proof logically consistent?"                   │
│   ✅ "Do the steps follow from each other?"                 │
│   ✅ "Are there obvious algebraic errors?"                  │
│                                                             │
│ Adversarial Critic CANNOT Check:                           │
│   ❌ "Is the answer actually correct?"                      │
│   ❌ "Does this construction work for ALL cases?"           │
│   ❌ "Is this the COMPLETE set of solutions?"               │
└─────────────────────────────────────────────────────────────┘
```

**Example**: Problem 1
- Solution claims: "k=0 or k odd" ✅ (logic is consistent)
- Correct answer: "k∈{0,1,n-1}" ❌ (but critic doesn't know this)
- Critic tested n=3,4,5 with k∈{0,1,3} → All WORK ✓
- Critic DIDN'T test k=3 at n=5 → Would FAIL ✗

---

## The Solution

**Add empirical verification**: Systematically test ALL possible values, not just the ones the solution claims.

```
┌────────────────────────────────────────────────────────────────┐
│ Current RLAC:                                                  │
│   1. Generate answer                                           │
│   2. Generate proof                                            │
│   3. Critic checks: "Is the proof logic sound?" → Yes          │
│   4. Declare ROBUST ✓ (but wrong!)                             │
│                                                                │
│ Enhanced RLAC:                                                 │
│   1. Generate answer                                           │
│   2. Generate proof                                            │
│   3. Critic checks logic → Yes                                 │
│   4. **NEW: Empirical test ALL k for n=3,4,5,6,7,8**          │
│      - k=3 at n=5: Answer says YES, construction FAILS → ✗    │
│   5. Declare BROKEN, send back for revision                    │
└────────────────────────────────────────────────────────────────┘
```

---

## Quick Wins (This Week)

| Priority | Action | Impact | Effort | Cost |
|----------|--------|--------|--------|------|
| **1** | Add empirical verification | +15-20% | 1 week | $0 |
| **2** | Set critic reasoning=HIGH | +5-10% | 0 weeks | 3× |
| **3** | Test n=3-10 (not just 3-5) | +5% | 0.5 weeks | $0 |
| **TOTAL** | All quick wins | **+25-35%** | **1.5 weeks** | **3× cost** |

**Outcome**: 30% → 45% success rate in 1.5 weeks

---

## Scaling Strategies Comparison

| Strategy | Success | Cost | Effort | Risk | When |
|----------|---------|------|--------|------|------|
| **Quick Wins** | 45% | $37 | 1.5w | ⬇️ Low | **Now** |
| **Beam Search** | 65% | $28 | 4w | ⬇️ Low | Month 1 |
| **MCTS** | 70% | $60 | 6w | ⬛ Med | Month 2 |
| **Hybrid** | 85% | $40 | 12w | ⬆️ High | Month 3 |

**Best ROI**: Beam Search (2.2× success for 2.3× cost)

---

## Strategy Deep Dive

### Strategy 1: Quick Wins (Enhanced RLAC)

```
Problem → Answer → Proof → Adversarial Critic
                              ↓
                    ┌─────────────────────┐
                    │ 1. Logic checking   │
                    │ 2. Empirical tests  │ ← NEW
                    │ 3. Boundary sweep   │ ← ENHANCED
                    │ 4. Higher reasoning │ ← CONFIG
                    └─────────────────────┘
                              ↓
                     BROKEN / ROBUST?
```

**Pros**: Easiest, builds on existing code
**Cons**: Still single-threaded, slower to converge

---

### Strategy 2: Beam Search ⭐ (Recommended)

```
Problem → Generate 10 candidates
            ↓
    [1]  [2]  [3]  [4]  [5]  [6]  [7]  [8]  [9]  [10]
     ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓
   Test each with 5 quick cases
     ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓    ↓
   0.4  0.7  0.5  0.95 0.8  0.3  0.6  0.5  0.4  0.2
                    ↑
                  BEST!
            ↓
    Keep top 5 (beam width = 5)
            ↓
    [4]  [2]  [5]  [7]  [3]
     ↓    ↓    ↓    ↓    ↓
   RLAC 10 rounds each (parallel)
     ↓    ↓    ↓    ↓    ↓
  Deep verify with 20 cases
     ↓    ↓    ↓    ↓    ↓
   0.95 0.82 0.78 0.65 0.60
    ↓
  SELECT [4] as final answer
```

**Pros**: Simple, parallelizable, best ROI
**Cons**: Less adaptive than MCTS

---

### Strategy 3: MCTS

```
                    Root (Unknown answer)
                         ↓
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
   "k∈[0,n-2]"      "k=all odd"      "k∈{0,1}"
    Score: 0.4       Score: 0.67      Score: 0.55
        ↓                ↓ (UCB1 selects)
                    Expand based on failures:
                    k=3 fails at n=5 → exclude k=3?
                         ↓
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
   "k∈{0,1,n-1}"   "k=prime"        "k∈{1,3}"
    Score: 0.95      Score: 0.30      Score: 0.45
        ↑ BEST!
     Select for proof
```

**Pros**: Most adaptive, learns from failures
**Cons**: More complex, harder to parallelize

---

### Strategy 4: Hybrid (Long-term Goal)

```
MCTS (answer search)
    ↓
Top 3 answers
    ↓
┌───┴───────────────────┐
↓           ↓           ↓
RLAC       RLAC       RLAC
proof 1    proof 2    proof 3
↓           ↓           ↓
Formal     Formal     Formal
Verify     Verify     Verify
(Lean 4)   (Lean 4)   (Lean 4)
↓           ↓           ↓
PASS       FAIL       FAIL
↓
Final answer (formally verified!)
```

**Pros**: Gold standard, highest success rate
**Cons**: Complex, requires Lean 4 expertise

---

## Decision Tree

```
START: What's your priority?
    ↓
┌───┴──────────────────────────────┐
↓                                  ↓
Need results THIS WEEK?         Have 1+ months?
    ↓                                  ↓
Quick Wins                      ┌──────┴──────┐
(45% success, 1.5w)             ↓             ↓
    ↓                      Best ROI?      Best success?
DONE                            ↓             ↓
                          Beam Search    Hybrid
                          (65%, 4w)    (85%, 12w)
                                ↓             ↓
                             DONE         DONE
```

---

## Cost Analysis

### Current RLAC
- **Per problem**: $12
- **Success rate**: 30%
- **Cost per success**: $40
- **Time**: 15 min

### After Quick Wins
- **Per problem**: $37 (3× higher)
- **Success rate**: 45%
- **Cost per success**: $82 (2× higher)
- **Time**: 25 min

### After Beam Search
- **Per problem**: $28 (2.3× higher)
- **Success rate**: 65%
- **Cost per success**: $43 (1.1× higher) ← BEST!
- **Time**: 25 min (parallel)

### After Hybrid
- **Per problem**: $40 (3.3× higher)
- **Success rate**: 85%
- **Cost per success**: $47 (1.2× higher)
- **Time**: 40 min

**Key insight**: Cost per SUCCESS remains similar, but total attempts needed decreases dramatically!

---

## Implementation Checklist

### Week 1: Empirical Verification
- [ ] Create `code/empirical_verifier.py`
- [ ] Implement `SunnyLinesVerifier` class
- [ ] Add `extract_answer()` and `can_construct()` methods
- [ ] Test on Problem 1 wrong solution (should catch error)
- [ ] Integrate with `adversarial_critic.py`
- [ ] Run RLAC with empirical verification enabled
- [ ] Measure success rate improvement

### Week 2: Higher Reasoning + Boundary Testing
- [ ] Set `RLAC_CRITIC_REASONING=high`
- [ ] Update adversarial prompt for n=3-10 testing
- [ ] Test on multiple problems
- [ ] Measure combined improvement (target: 45%)

### Weeks 3-6: Beam Search
- [ ] Design beam search framework
- [ ] Implement candidate generation
- [ ] Implement quick scoring (5 test cases)
- [ ] Implement beam pruning
- [ ] Integrate with RLAC proof generation
- [ ] Add deep verification (20 test cases)
- [ ] Test on 10+ problems
- [ ] Measure success rate (target: 65%)

### Weeks 7-12: MCTS
- [ ] Design MCTS tree structure
- [ ] Implement UCB1 selection
- [ ] Implement expansion operators
- [ ] Implement simulation (RLAC + empirical)
- [ ] Implement backpropagation
- [ ] Test on 10+ problems
- [ ] Measure success rate (target: 70%)

### Weeks 13-24: Formal Verification
- [ ] Set up Lean 4 environment
- [ ] Implement natural language → Lean translator
- [ ] Implement proof checker integration
- [ ] Implement gap extraction from errors
- [ ] Integrate with MCTS+RLAC
- [ ] Test on simple problems first
- [ ] Expand to complex problems
- [ ] Measure success rate (target: 85%)

---

## Files Created

| File | Purpose |
|------|---------|
| `RLAC_SCALING_STRATEGY_ANALYSIS.md` | Full 10,000-word analysis |
| `EXECUTIVE_SUMMARY_RLAC_SCALING.md` | 5-minute read summary |
| `IMPLEMENTATION_GUIDE.md` | Step-by-step code instructions |
| `SCALING_STRATEGY_CHEATSHEET.md` | This quick reference |

---

## Key Metrics to Track

### Success Metrics
- ✅ Success rate (% of problems solved correctly)
- ✅ Cost per problem
- ✅ Cost per success
- ✅ Time per problem
- ✅ False positive rate (ROBUST but wrong)

### Debugging Metrics
- Empirical verification score distribution
- Counterexample detection rate
- Average rounds to convergence
- Answer space coverage (for MCTS/Beam)

### Quality Metrics
- Proof quality (logical soundness)
- Answer completeness (for FIND problems)
- Formal verification success rate (if implemented)

---

## Quick Reference Commands

```bash
# Set high reasoning
export RLAC_CRITIC_REASONING=high

# Run with empirical verification
python code/agent_gpt_oss.py problems/imo01.txt \
  --use-rlac \
  --log output.log \
  --memory memory.json

# Test empirical verifier standalone
python test_empirical_verification.py

# Run beam search (after implementation)
python code/beam_search.py problems/imo01.txt \
  --beam-width 5 \
  --log output.log

# Run MCTS (after implementation)
python code/mcts_search.py problems/imo01.txt \
  --iterations 100 \
  --log output.log
```

---

## Common Pitfalls

1. **❌ Testing only claimed values**
   - Solution says "k=odd" → Test k=1,3,5
   - ✅ Instead: Test ALL k=0,1,2,3,4,5,... for each n

2. **❌ Using insufficient test cases**
   - Testing only n=3,4,5
   - ✅ Instead: Test n=3,4,5,6,7,8,9,10

3. **❌ Accepting ROBUST too early**
   - 1 ROBUST round → DONE
   - ✅ Instead: Require 3 consecutive ROBUST + empirical score > 0.9

4. **❌ Ignoring empirical failures**
   - "Empirical score 0.67, but logic is sound, so ROBUST"
   - ✅ Instead: Empirical score < 0.8 → BROKEN regardless of logic

5. **❌ Not building construction verifiers**
   - "Can't verify, so skip empirical testing"
   - ✅ Instead: Invest 2 weeks to build verifier library

---

## Success Stories (Projected)

### Week 1: First Empirical Verification Success
```
Problem: Sunny Lines
Without empirical: 25 rounds → ROBUST (wrong answer)
With empirical: 8 rounds → BROKEN (caught k=3 at n=5)
            → 12 rounds → ROBUST (correct answer!)
Result: ✅ CORRECT in fewer rounds
```

### Week 6: First Beam Search Success
```
Problem: Complex characterization
RLAC alone: Never converges (stuck in local optimum)
Beam search: Explores 5 candidates simultaneously
           → Finds correct answer in candidate #3
           → RLAC refines proof
Result: ✅ CORRECT (would have failed with RLAC alone)
```

### Week 12: First MCTS Success
```
Problem: Subtle pattern (k ∈ {0,1,n-1})
Initial guess: "k ∈ [0,n-2]" (score: 0.4)
MCTS iteration 5: Fails at n=5,k=2 → Refine
MCTS iteration 12: Tries "k ∈ {0,1,n-1}" (score: 0.95)
Result: ✅ CORRECT via adaptive search
```

---

## When to Use Each Strategy

| Situation | Recommended Strategy | Why |
|-----------|---------------------|-----|
| Need results NOW | Quick Wins | Fastest (1.5 weeks) |
| Limited budget | Quick Wins | Lowest absolute cost |
| Best ROI | Beam Search | 2.2× success for 2.3× cost |
| Complex search space | MCTS | Adaptive, learns from failures |
| Need gold standard | Hybrid | Formal verification guarantees |
| Production system | Hybrid | 85% success rate |

---

## Final Recommendations

### This Week
1. **Implement empirical verification** (Priority 1)
2. **Set critic reasoning to HIGH** (Priority 2)
3. **Test on Problem 1** to verify it catches the error

### Next Month
1. **Implement Beam Search** (highest ROI)
2. **Build construction verifier library** (enables all strategies)
3. **Target 60-65% success rate**

### Long-term (3 months)
1. **Add MCTS** if Beam Search successful
2. **Begin formal verification** integration
3. **Target 80-90% success rate** (research-grade system)

---

**Start with Quick Wins today. See `IMPLEMENTATION_GUIDE.md` for detailed code.**

**Questions? See full analysis in `RLAC_SCALING_STRATEGY_ANALYSIS.md`**
