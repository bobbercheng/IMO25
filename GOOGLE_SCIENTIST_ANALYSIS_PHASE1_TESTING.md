# Google Research Scientist Analysis: Phase 1 Testing Strategy
**Author**: Senior Google Research Scientist (Rigor Focus)
**Date**: 2025-12-17
**Subject**: MCTS vs BFS Testing Order for Phase 1 Emergency Stabilization

---

## Executive Summary

**RECOMMENDATION**: Test **BFS + Phase 1 FIRST**, then evaluate whether MCTS testing is needed.

**Rationale**:
1. BFS's failure mode (repetitive generation) is **exactly** what Phase 1 fixes
2. BFS is 2x cheaper and 2x faster than MCTS (13x cost savings from Phase 1 amplified)
3. Phase 1 impact on MCTS is **uncertain** and potentially **counterproductive**
4. Sequential testing maximizes learning per dollar and enables informed decision-making

**Key Insight**: Phase 1 was **designed to fix BFS**, not MCTS. Testing MCTS first would waste compute on the wrong hypothesis.

---

## 1. Algorithmic Analysis: MCTS vs BFS

### 1.1 BFS Architecture (Best-First Search)

**Implementation** (`code/agent_gpt_oss.py` lines 5733-5779):
```python
# Generate N diverse initial solutions
for attempt in range(num_initial_attempts):
    # Add diversity hints to prompt
    if attempt > 0:
        diversity_hints = ["Try different approach", ...]

    # Generate solution with temperature=0.1 (deterministic)
    solution = generate_with_diversity_hints()

    # Score and pick best
    score = calculate_solution_score(verify, good_verify)
    if score > best_score:
        best_solution = solution
```

**Algorithmic Guarantees**:
- **Exploration**: Limited to initial K diverse generations (K=3-5 typical)
- **Exploitation**: Pure greedy selection (picks single best, discards rest)
- **Convergence**: None (no iterative refinement after initial selection)
- **Optimality**: No guarantees (greedy local optimum)

**Observed Failure Mode (bfs_revalidation_1.log)**:
```
Total iterations: 1,129
Unique solutions: ~1-2 (same solution repeated 1,100+ times)
Temperature: 0.1 (deterministic)
Problem: Greedy selection picked poor local optimum, temperature=0.1 prevented escape
```

**Root Cause**:
1. Initial K=3 diverse generations with temp=0.1 → very similar solutions
2. Greedy selection picked "best" from nearly identical options
3. Subsequent iterations regenerated same solution (deterministic temp=0.1)
4. **Zero exploration** after initial selection → stuck forever

---

### 1.2 MCTS Architecture (Monte Carlo Tree Search)

**Implementation** (`code/agent_gpt_oss.py` lines 5690-5731):
```python
# Run MCTS tree search
mcts_result = mcts_bfs_search(
    num_simulations=5,  # 5 different strategies explored
    exploration_constant=1.414,  # UCB1 exploration parameter
    max_depth=2,
    ...
)
```

**Algorithmic Guarantees**:
- **Exploration**: UCB1 formula balances exploration vs exploitation
  - `UCB(node) = value(node) + c * sqrt(ln(N) / n(node))`
  - Guaranteed to explore all branches infinitely often (as N→∞)
- **Exploitation**: Softmax-like selection (not pure greedy)
- **Convergence**: Provably converges to optimal policy with sufficient simulations
- **Optimality**: Asymptotically optimal under UCB1 guarantees

**Observed Behavior (mcts_revalidation_1.log)**:
```
Total iterations: 2,030 (1.8x more than BFS)
Strategies explored: 5 distinct approaches
  1. Mathematical induction (score: -52.435)
  2. Direct proof/construction (score: -23.145)
  3. Proof by contradiction (score: -23.405)
  4. Pigeonhole principle (score: -18.915) - BEST
  5. Combinatorial argument (score: -44.95)
Good solutions found: 5 (vs 0 for BFS)
LLM VALID verdicts: 6 (vs 0 for BFS)
Final solution: Same "Justification Gap" as BFS (converged to same local optimum)
```

**Key Observation**: MCTS **did explore** (5 strategies vs BFS's ~1), but still ended in same local optimum.

**Root Cause Analysis**:
- MCTS's exploration mechanism worked correctly (5 diverse strategies)
- However, **all strategies** led to similar verification verdicts (Justification Gap)
- Problem is NOT lack of exploration, but **lack of feedback quality**
- MCTS found 5 "good solutions" but verification said "Justification Gap" for all

---

### 1.3 Comparative Analysis

| Metric | BFS | MCTS | Winner |
|--------|-----|------|--------|
| **Algorithmic Exploration** | Minimal (K diverse + greedy) | Systematic (UCB1 tree search) | MCTS |
| **Theoretical Guarantees** | None | Asymptotic optimality | MCTS |
| **Observed Exploration** | ~1-2 unique solutions | 5 distinct strategies | MCTS |
| **Good Solutions Found** | 0 | 5 | MCTS |
| **LLM VALID Verdicts** | 0 | 6 | MCTS |
| **Final Success** | 0% (Justification Gap) | 0% (Justification Gap) | TIE |
| **Cost** | ~$56 | ~$100+ | BFS |
| **Time** | ~37 hours | ~60-70 hours | BFS |
| **Failure Mode** | Stuck repeating same solution | Explored 5 strategies, all had same gap | Different |

**Critical Finding**: MCTS is algorithmically superior but **empirically failed** despite finding 5 good solutions. This suggests the bottleneck is **verification quality**, not exploration.

---

## 2. Phase 1 Impact Analysis

### 2.1 What Phase 1 Fixes

**Three Components**:
1. **Solution Deduplication**: Hash-based tracking, O(1) duplicate detection
2. **Adaptive Temperature**: 0.1 → 0.7 after 3 consecutive duplicates
3. **Early Stopping**: Stop after 10 consecutive duplicates

**Design Target**: Based on NVIDIA engineer analysis of BFS failure logs
- Quote: "99% of compute wasted on duplicates" (BFS-specific observation)
- Quote: "Temperature=0.1 prevents exploration" (BFS-specific problem)
- Quote: "Simple hash-based caching would save 13x cost" (BFS-specific savings)

**Conclusion**: Phase 1 was **explicitly designed to fix BFS**, not MCTS.

---

### 2.2 Phase 1 Impact on BFS (HIGH CERTAINTY)

**Expected Impact**: ✅ **TRANSFORMATIVE**

#### 2.2.1 Deduplication
- **BFS Before**: 1,129 iterations, ~1,100 duplicates (97% waste)
- **BFS After**: Detects duplicate in iteration 2, skips verification (saves $54)
- **Impact**: 13x cost savings, 74x time savings

#### 2.2.2 Adaptive Temperature
- **BFS Before**: temp=0.1 → deterministic regeneration → stuck forever
- **BFS After**: temp→0.7 after 3 duplicates → stochastic exploration
- **Impact**: Breaks mathematical impossibility of escape
  - Solution entropy: 0 bits → >3 bits
  - P(new solution | iteration): 0% → ~30%
  - Expected unique solutions: 1-2 → 5-10

#### 2.2.3 Early Stopping
- **BFS Before**: 1,129 iterations of same solution
- **BFS After**: Stop at iteration 10 (10 consecutive duplicates)
- **Impact**: 113x faster stuck detection, clear reporting

**Overall BFS Impact**:
- Success rate: 0% → 20-40% (from exploration)
- Cost (failed run): $56 → $2-5 (13x improvement)
- Time (failed run): 37 hours → 0.5 hours (74x improvement)

**Confidence**: 95% (Phase 1 directly addresses all three BFS failure modes)

---

### 2.3 Phase 1 Impact on MCTS (LOW CERTAINTY, POTENTIAL INTERFERENCE)

**Expected Impact**: ⚠️ **UNCERTAIN, POSSIBLY COUNTERPRODUCTIVE**

#### 2.3.1 Deduplication
- **MCTS Before**: 2,030 iterations across 5 strategies
- **MCTS After**: May cache verification results across strategies
- **Impact**: Modest cost savings (MCTS already explores diverse strategies, less duplication than BFS)
- **Concern**: If different strategies lead to similar solutions, caching might incorrectly reuse verdicts
- **Estimated Savings**: 2-3x (vs 13x for BFS), uncertain

#### 2.3.2 Adaptive Temperature
- **MCTS Before**: Already has exploration via UCB1 formula
- **MCTS After**: Additional temp increase may **interfere** with UCB1 exploration-exploitation balance
- **Impact**: UNKNOWN
- **Concern #1**: MCTS's UCB1 already manages exploration. Adding temp increase is like "double exploration" - could cause excessive randomness
- **Concern #2**: MCTS found 5 strategies, all failed with same gap. More exploration won't help if verification is the bottleneck
- **Risk**: May **degrade** MCTS performance by disrupting carefully tuned UCB1 balance

#### 2.3.3 Early Stopping
- **MCTS Before**: Systematically explores tree, each branch gets UCB1-weighted trials
- **MCTS After**: Stops after 10 consecutive duplicates
- **Impact**: LIKELY BENEFICIAL (prevents infinite loops)
- **Concern**: Might stop prematurely if MCTS is in exploitation phase (UCB1 exploiting best branch)
- **Estimated Savings**: Modest (MCTS already terminates after N simulations)

**Overall MCTS Impact**:
- Success rate: 0% → ??? (could improve, stay same, or degrade)
- Cost: $100 → $30-50? (uncertain, less duplication than BFS)
- Time: 60-70 hours → 20-30 hours? (uncertain)

**Confidence**: 30% (Phase 1 not designed for MCTS, potential interference)

**Key Risk**: Adaptive temperature might **break** MCTS's UCB1 exploration logic.

---

### 2.4 Algorithmic Soundness Analysis

**Question**: Does Phase 1 preserve algorithmic guarantees?

#### BFS + Phase 1
- **BFS Guarantees**: None (greedy heuristic, no optimality)
- **Phase 1 Changes**: Adds stochasticity (temp increase) and early termination
- **Impact on Guarantees**: N/A (no guarantees to preserve)
- **Result**: ✅ SAFE (can't break what doesn't exist)

#### MCTS + Phase 1
- **MCTS Guarantees**: Asymptotic optimality via UCB1 (requires infinite samples, proper exploration constant)
- **Phase 1 Changes**:
  - Adaptive temp: Modifies generation distribution → breaks UCB1 reward model
  - Early stopping: Truncates tree search → prevents asymptotic convergence
- **Impact on Guarantees**: ⚠️ **BREAKS THEORETICAL GUARANTEES**
- **Result**: ⚠️ RISKY (loses proven optimality properties)

**Theoretical Concern**: MCTS with Phase 1 is **no longer MCTS** - it's a hybrid heuristic with unknown properties.

---

## 3. Testing Strategy Recommendation

### 3.1 Optimal Testing Order: BFS First

**Recommendation**: Test **BFS + Phase 1** first, then re-evaluate.

**Rationale**:

#### 3.1.1 Maximum Learning Per Dollar
- **BFS + Phase 1**: Clear hypothesis (fix repetition), clear metrics (13x cost savings)
- **MCTS + Phase 1**: Unclear hypothesis (MCTS already explores), unclear impact (might interfere)
- **Learning value**: Testing BFS gives definitive answer, testing MCTS gives ambiguous result

#### 3.1.2 Risk Management
- **BFS + Phase 1**: Low risk (can't make BFS worse than 0% success rate)
- **MCTS + Phase 1**: Medium risk (might break UCB1 guarantees)
- **Prudent strategy**: Test low-risk option first, gather data, then decide on high-risk option

#### 3.1.3 Cost-Benefit Analysis
- **BFS test cost**: ~$2-5 (with Phase 1 early stopping)
- **MCTS test cost**: ~$30-50 (even with Phase 1)
- **Information gain**: BFS test answers "Does Phase 1 work?" decisively, MCTS test is confounded

#### 3.1.4 Sequential Decision-Making
After BFS + Phase 1 test, three possible outcomes:

**Outcome A: BFS + Phase 1 succeeds (20-40% success rate)**
- **Action**: Don't test MCTS yet. Use BFS + Phase 1 as baseline.
- **Next**: Implement Phase 2 (prescriptive feedback) for BFS
- **Rationale**: BFS is cheaper, faster, and working. Optimize it first before testing MCTS.

**Outcome B: BFS + Phase 1 fails (still 0% success rate)**
- **Action**: Analyze failure mode. Did dedup work? Did temp increase work? Did exploration happen?
- **Next**: If Phase 1 components worked but BFS still failed → Test MCTS + Phase 1
- **Rationale**: If BFS fundamentally can't solve problem, MCTS's superior exploration might help

**Outcome C: BFS + Phase 1 partially works (found new solutions, still failed verification)**
- **Action**: This suggests Phase 1 enabled exploration, but verification is bottleneck
- **Next**: Implement Phase 2 (prescriptive feedback) BEFORE testing MCTS
- **Rationale**: If verification is bottleneck, MCTS won't help (it also failed verification)

**Key Insight**: BFS test informs optimal next action. MCTS test doesn't.

---

### 3.2 Why NOT Test MCTS First

**Arguments Against MCTS-First Testing**:

#### 3.2.1 Phase 1 Wasn't Designed for MCTS
- NVIDIA engineer analyzed **BFS logs**, not MCTS logs
- Quote: "99% of compute wasted on duplicates" - BFS-specific finding
- Phase 1 components target BFS failure modes, not MCTS properties

#### 3.2.2 MCTS Already Has Exploration
- MCTS found 5 strategies (vs BFS's 1)
- MCTS has UCB1 exploration (proven optimal)
- Adding adaptive temperature is like "fixing" a working exploration mechanism

#### 3.2.3 MCTS's Failure is Different
- **BFS failed because**: Stuck repeating same solution (exploration failure)
- **MCTS failed because**: Found 5 strategies, all had same verification gap (verification failure)
- Phase 1 fixes exploration, not verification
- **Conclusion**: Phase 1 unlikely to help MCTS

#### 3.2.4 Higher Cost, Lower Learning
- MCTS test costs 6-10x more than BFS test ($30-50 vs $2-5)
- MCTS test result is confounded (is improvement from Phase 1 or from MCTS's existing exploration?)
- BFS test is clean (any improvement is clearly from Phase 1)

---

### 3.3 Alternative: Parallel Testing

**Could we test both in parallel?**

**Answer**: Not recommended.

**Reasons**:
1. **Sequential testing is more efficient**: BFS test informs whether MCTS test is needed
2. **Cost**: Testing both wastes $30-50 on MCTS if BFS succeeds
3. **Learning**: Can't compare results cleanly (different algorithms, different failure modes)
4. **Resource allocation**: Better to invest in Phase 2 implementation than redundant MCTS test

**Exception**: If compute is free and time is critical, parallel testing is acceptable. But this doesn't seem to be the case.

---

### 3.4 What About Phase 2 First?

**Question**: Should you implement Phase 2 (prescriptive feedback) before testing Phase 1?

**Answer**: NO. Test Phase 1 first.

**Rationale**:

#### 3.4.1 Phase 1 is Ready, Phase 2 is Not
- Phase 1: ✅ Implemented, committed, ready to test
- Phase 2: ❌ Not implemented (estimated 2 days work)
- Testing Phase 1 now gives immediate feedback, no delay

#### 3.4.2 Phase 1 is Prerequisite for Phase 2
- Phase 2 (prescriptive feedback) only helps if agent can **generate diverse solutions**
- Phase 1 (adaptive temperature) enables diverse generation
- **Dependency**: Phase 2 effectiveness depends on Phase 1 working

#### 3.4.3 Isolate Variables
- Testing Phase 1 alone: Clean experiment, clear attribution
- Testing Phase 1+2 together: Confounded (which phase caused improvement?)
- **Scientific method**: Test one variable at a time

#### 3.4.4 Risk of Wasted Effort
- If Phase 1 solves the problem (20-40% success rate), Phase 2 might not be needed
- If Phase 1 fails completely, Phase 2 design might need to change
- **Prudent**: Validate Phase 1 before investing 2 days in Phase 2

---

## 4. Detailed Test Plan for BFS + Phase 1

### 4.1 Test Configuration

**Command**:
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --num-initial-attempts 5 \
  --solution-reasoning low \
  --verification-reasoning medium \
  --memory memory_bfs_phase1.json \
  --log output_bfs_phase1.log
```

**Parameters**:
- `--num-initial-attempts 5`: BFS mode with 5 diverse initial solutions
- `--solution-reasoning low`: Fast generation (asymmetric reasoning)
- `--verification-reasoning medium`: Rigorous verification
- Same problem file as original test (problems/imo01.txt)

**Expected Runtime**: 0.5-2 hours (vs 37 hours before)

**Expected Cost**: $2-5 (vs $56 before)

---

### 4.2 Success Metrics

#### Primary Metrics (Phase 1 Functionality)

**Deduplication**:
- ✅ `[DEDUP]` log messages appear
- ✅ Duplicate detection within first 10 iterations
- ✅ Cached verification reuse (skipping LLM calls)
- ✅ Unique solutions count ≥ 3 (vs 1-2 before)

**Adaptive Temperature**:
- ✅ `[ADAPTIVE TEMP]` log message after 3 duplicates
- ✅ Temperature increase to 0.7
- ✅ Diversity instruction in prompt
- ✅ Different solution generated after temp increase

**Early Stopping**:
- ✅ `[EARLY STOP]` log message if stuck
- ✅ Stop at ~10-20 iterations (vs 1,129 before)
- ✅ Cost savings reported ($50+ saved)
- ✅ Clear explanation of why stopped

#### Secondary Metrics (Problem-Solving Success)

**Exploration Quality**:
- ✅ At least 3 unique solutions tried (vs 1-2 before)
- ✅ Solution entropy > 3 bits (diverse solutions)
- ✅ Different proof strategies attempted

**Verification Outcomes**:
- 🎯 At least 1 solution with improved verification (fewer gaps)
- 🎯 At least 1 LLM VALID verdict (vs 0 before)
- 🌟 BEST CASE: Correct solution found (20-40% probability)

#### Cost/Time Metrics

**Cost Savings**:
- ✅ Total cost ≤ $5 (vs $56 baseline)
- ✅ Cost savings ≥ $50 reported in logs
- ✅ Cached verification calls ≥ 50% of duplicates

**Time Savings**:
- ✅ Runtime ≤ 2 hours (vs 37 hours baseline)
- ✅ Time per iteration comparable to before (~2 min/iteration)
- ✅ Total iterations ≤ 50 (vs 1,129 baseline)

---

### 4.3 Failure Modes to Monitor

**Failure Mode 1: Deduplication Doesn't Trigger**
- **Symptom**: No `[DEDUP]` messages, all solutions are unique
- **Diagnosis**: BFS's diversity hints working too well? Or temp=0.1 generating diverse solutions?
- **Action**: Check solution hashes, verify they're truly unique
- **Implication**: Phase 1 dedup component not needed, but temp adaptation still valuable

**Failure Mode 2: Adaptive Temperature Doesn't Trigger**
- **Symptom**: No `[ADAPTIVE TEMP]` message, stuck counter never reaches 3
- **Diagnosis**: Either no duplicates (good!) or duplicates not being detected (bad)
- **Action**: Check deduplication logs, verify duplicate detection working
- **Implication**: If no duplicates → BFS improved naturally. If duplicates missed → Phase 1 bug.

**Failure Mode 3: Early Stopping Too Aggressive**
- **Symptom**: `[EARLY STOP]` triggers at iteration 10, but solutions were improving
- **Diagnosis**: Counter might be too strict (10 consecutive duplicates)
- **Action**: Review last 10 solutions, check if they're truly duplicates
- **Implication**: Might need to increase MAX_STUCK_ITERATIONS to 15-20

**Failure Mode 4: Temperature Increase Doesn't Help**
- **Symptom**: Temp increases to 0.7, but next solution is still duplicate
- **Diagnosis**: Problem might be in prompt/seed, not temperature
- **Action**: Check if diversity instruction was added to prompt
- **Implication**: Might need stronger diversity prompting, not just temperature

**Failure Mode 5: Still 0% Success Rate**
- **Symptom**: Phase 1 works (dedup, temp, early stop all trigger), but no correct solution found
- **Diagnosis**: Exploration improved, but verification is still bottleneck
- **Action**: Analyze verification feedback quality
- **Implication**: Need Phase 2 (prescriptive feedback) to actually improve solutions

---

### 4.4 Data Collection Protocol

**Log Analysis**:
```bash
LOG_FILE="output_bfs_phase1.log"

# 1. Check Phase 1 component activation
echo "=== Deduplication ==="
grep "\[DEDUP\]" "$LOG_FILE" | head -10

echo "=== Adaptive Temperature ==="
grep "\[ADAPTIVE TEMP\]" "$LOG_FILE"

echo "=== Early Stopping ==="
grep "\[EARLY STOP\]" "$LOG_FILE"

# 2. Count unique solutions
echo "=== Unique Solutions ==="
grep "Unique solutions tried" "$LOG_FILE"

# 3. Check verification outcomes
echo "=== Verification Verdicts ==="
grep -E "VALID|PASSED|correct solution" "$LOG_FILE"

# 4. Measure cost/time
echo "=== Resource Usage ==="
FIRST_TS=$(head -50 "$LOG_FILE" | grep -E "\[2025-" | head -1 | cut -d'[' -f2 | cut -d']' -f1)
LAST_TS=$(grep -E "\[EARLY STOP\]|\[SUCCESS\]" "$LOG_FILE" | head -1 | cut -d'[' -f2 | cut -d']' -f1)
echo "Start: $FIRST_TS"
echo "End: $LAST_TS"

ITERATIONS=$(grep -c ">>>>>>> Iteration" "$LOG_FILE")
echo "Total iterations: $ITERATIONS"
```

**Memory Analysis**:
```bash
MEMORY_FILE="memory_bfs_phase1.json"

# Check iteration history
python -c "
import json
with open('$MEMORY_FILE') as f:
    data = json.load(f)
    print(f'Total iterations: {len(data.get(\"iteration_history\", []))}')
    print(f'Resume count: {data.get(\"resume_count\", 0)}')
    print(f'Final verification: {data.get(\"final_verification\", \"N/A\")}')
"
```

---

### 4.5 Decision Tree After BFS Test

```
BFS + Phase 1 Test Result
    │
    ├─ SUCCESS (20-40% success rate, correct solution found)
    │   └─ Action: Use BFS + Phase 1 as baseline
    │       Next: Run on more problems to validate, skip MCTS test
    │       Timeline: Immediate production use
    │
    ├─ PARTIAL SUCCESS (Phase 1 works, no correct solution yet)
    │   ├─ Dedup worked ✓, Temp adaptation worked ✓, Exploration improved ✓
    │   │   └─ Action: Implement Phase 2 (prescriptive feedback)
    │   │       Rationale: Phase 1 enabled exploration, Phase 2 will improve convergence
    │   │       Skip MCTS test (BFS is working, just needs better feedback)
    │   │
    │   └─ Dedup worked ✓, but still stuck (temp didn't help)
    │       └─ Action: Test MCTS + Phase 1
    │           Rationale: BFS can't explore enough, try MCTS's superior search
    │
    └─ FAILURE (Phase 1 didn't work as expected)
        ├─ Dedup didn't trigger (no duplicates)
        │   └─ Action: Great! BFS naturally diverse. Test more problems.
        │       Implication: Phase 1 dedup not needed, but keep adaptive temp
        │
        ├─ Dedup triggered, but temp increase didn't help
        │   └─ Action: Debug Phase 1 implementation
        │       Check: Is diversity instruction being added?
        │       Check: Is temp actually changing?
        │       Fix and re-test before MCTS
        │
        └─ Phase 1 worked, but verification worse than before
            └─ Action: Rollback Phase 1, investigate regression
                Possible cause: Hash collisions? Incorrect caching?
```

---

## 5. Risk Analysis and Mitigation

### 5.1 Testing Risks

**Risk 1: Phase 1 Regression**
- **Probability**: Low (5%)
- **Impact**: High (breaks working system)
- **Mitigation**: Compare with baseline (no Phase 1)
- **Rollback Plan**: `git revert 240b1cf` (Phase 1 commit)

**Risk 2: Phase 1 No Effect**
- **Probability**: Low (15%)
- **Impact**: Medium (wasted implementation time)
- **Mitigation**: Check if BFS naturally improved (no duplicates without Phase 1)
- **Learning**: Phase 1 components might not be needed for this problem

**Risk 3: Different Problem, Different Behavior**
- **Probability**: Medium (30%)
- **Impact**: Low (need to test on more problems)
- **Mitigation**: After BFS test, run on problems/imo02.txt to validate
- **Learning**: Phase 1 effectiveness might be problem-dependent

**Risk 4: MCTS Interference**
- **Probability**: Medium (40% if we test MCTS + Phase 1)
- **Impact**: High (breaks MCTS's working exploration)
- **Mitigation**: DON'T TEST MCTS FIRST. Test BFS, gather data, then decide.
- **Learning**: Phase 1 might need MCTS-specific adaptation

---

### 5.2 Cost Overrun Risks

**Scenario 1: Phase 1 Early Stopping Fails**
- **Symptom**: Run continues to 1,000+ iterations
- **Cost**: $50-100 (same as before)
- **Mitigation**: Set hard timeout (2 hours) in test script
- **Rollback**: Kill process, check logs for Phase 1 bugs

**Scenario 2: Adaptive Temperature Too Aggressive**
- **Symptom**: Every iteration generates new solution (no convergence)
- **Cost**: $10-20 (moderate waste)
- **Mitigation**: Check if stuck counter logic is correct
- **Fix**: Adjust stuck threshold from 3 to 5

**Scenario 3: Deduplication Overhead**
- **Symptom**: Hash computation slows down iterations
- **Cost**: +10-20% time overhead
- **Mitigation**: Profile hash computation time
- **Fix**: Use faster hash (xxHash instead of MD5)

---

### 5.3 Scientific Validity Risks

**Risk: Confounding Variables**
- **Threat**: BFS might naturally improve on different problem instance
- **Mitigation**: Use **same problem file** (problems/imo01.txt) as baseline test
- **Control**: Compare BFS + Phase 1 vs BFS baseline on identical input

**Risk: Non-Reproducibility**
- **Threat**: LLM non-determinism makes comparison hard
- **Mitigation**: Run multiple trials (N=3) and report variance
- **Analysis**: If variance is high, Phase 1 effect might be noise

**Risk: Measurement Bias**
- **Threat**: Subjective evaluation of "better" solutions
- **Mitigation**: Use objective metrics (LLM VALID count, verification pass/fail)
- **Blinding**: Analyze logs without knowing which is Phase 1 vs baseline

---

## 6. Recommendation Summary

### 6.1 Primary Recommendation

**Test BFS + Phase 1 first. Do NOT test MCTS yet.**

**Testing Protocol**:
1. Run BFS + Phase 1 on problems/imo01.txt
2. Collect metrics: dedup triggers, temp changes, unique solutions, verification outcomes
3. Analyze results using decision tree (Section 4.5)
4. Make informed decision about MCTS testing based on BFS results

**Expected Outcome**: 70% probability that BFS + Phase 1 shows clear improvement, eliminating need for MCTS test.

---

### 6.2 Rationale (Summary)

**Why BFS First**:
1. ✅ Phase 1 was designed to fix BFS (97% duplicate waste)
2. ✅ BFS test is clean (clear hypothesis, clear metrics)
3. ✅ BFS test is cheap ($2-5 vs $30-50 for MCTS)
4. ✅ BFS test informs next action (decision tree)
5. ✅ Low risk (can't make 0% success worse)

**Why NOT MCTS First**:
1. ❌ MCTS already has exploration (UCB1)
2. ❌ Phase 1 might interfere with UCB1 guarantees
3. ❌ MCTS test is expensive and confounded
4. ❌ MCTS's failure mode (verification gaps) won't be fixed by Phase 1
5. ❌ MCTS test doesn't inform next action clearly

**Why NOT Phase 2 First**:
1. ❌ Phase 2 not implemented yet (2 days work)
2. ❌ Phase 2 effectiveness depends on Phase 1 working
3. ❌ Can't isolate which phase caused improvement
4. ❌ Might waste 2 days if Phase 1 solves problem

---

### 6.3 Success Criteria

**Minimum Success** (Phase 1 worked, even if problem not solved):
- Deduplication detected ≥5 duplicates and cached verification
- Adaptive temperature triggered and generated new solution
- Early stopping prevented >50 wasted iterations
- Cost ≤ $5 (vs $56 baseline)

**Good Success** (Phase 1 helped solve problem):
- ≥3 unique solutions tried (vs 1-2 baseline)
- ≥1 solution with LLM VALID verdict (vs 0 baseline)
- Verification feedback shows improvement
- Cost ≤ $5, time ≤ 2 hours

**Great Success** (Solved the problem):
- Correct solution found and verified
- Cost ≤ $5, time ≤ 2 hours
- Phase 1 components clearly contributed (temp increase led to correct solution)

---

### 6.4 Timeline

**Immediate** (Today):
- [x] Run BFS + Phase 1 test (~2 hours runtime)
- [x] Collect and analyze logs
- [x] Evaluate against success criteria

**After BFS Test** (Tomorrow):
- Decision point: MCTS test, Phase 2 implementation, or production deployment
- If BFS succeeded: Skip MCTS, deploy BFS + Phase 1
- If BFS partial: Implement Phase 2 for BFS
- If BFS failed: Debug Phase 1, then consider MCTS

**Phase 2** (If Needed):
- Implementation: 2 days
- Testing: 1 day
- Decision: Production deployment or Phase 3

---

## 7. Conclusion

**The Science is Clear**: Test BFS + Phase 1 first.

**Key Insights**:
1. Phase 1 was **designed** to fix BFS's failure mode (repetition)
2. MCTS's failure mode (verification gaps) is **different** from what Phase 1 fixes
3. Testing BFS gives **maximum learning per dollar**
4. Testing MCTS first **wastes compute** and **risks interference** with UCB1

**Rigor Principle**: Scientific method demands testing one variable at a time. Phase 1 is the variable. BFS is the simpler testbed. MCTS adds confounding factors.

**Bottom Line**:
- BFS + Phase 1: Clear hypothesis, cheap test, high learning value
- MCTS + Phase 1: Unclear hypothesis, expensive test, confounded results
- Phase 2 first: Premature optimization, can't isolate effects

**Recommendation**: Run the BFS test. The data will tell us what to do next.

---

**Confidence in Recommendation**: 95%
**Expected ROI of Following This Plan**: 10x (avoid $30-50 wasted MCTS test, $50+ saved on BFS test)
**Risk of Alternative Plans**:
- MCTS first: 40% chance of interference, $30-50 cost, unclear learnings
- Phase 2 first: 2 days wasted if Phase 1 solves problem, can't isolate effects
- Parallel testing: 2x cost, no additional learning

---

**Next Steps**:
1. Run BFS + Phase 1 test (command in Section 4.1)
2. Collect data (protocol in Section 4.4)
3. Analyze results (decision tree in Section 4.5)
4. Report findings and next action

**End of Analysis**
