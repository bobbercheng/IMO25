# ADVERSARIAL CRITICAL ANALYSIS: RLAC Scaling Proposals
## Devil's Advocate Challenge to Nvidia/OpenAI Scaling Strategies

**Author**: Senior Research Scientist, Google Research (AI Safety & Adversarial Robustness)
**Date**: 2025-11-28
**Mission**: Challenge proposed scaling solutions and identify fatal flaws

---

## Executive Summary: Don't Scale Search, Fix the Critic

**TL;DR - The Inconvenient Truth:**
- ❌ **MCTS/beam search will NOT fix this** - you'll just explore 100× more wrong answers
- ❌ **Process supervision is a pipe dream** - which step do you verify when the entire approach is wrong?
- ❌ **More reasoning effort = diminishing returns** - we already use high reasoning for verification
- ✅ **The real problem: WEAK CRITICS** - adversarial attacks found ~17 counterexamples but NONE caught the fundamental error
- 💰 **ROI reality check**: Proposed scaling could cost $50-200/problem with <10% success improvement

**Recommendation**: Invest in better verification/critics, not fancier search. AlphaGo needed strong value functions, not just more MCTS rollouts.

---

## 1. Root Cause Challenge: Is This Even a Search Problem?

### The Evidence from Test Logs

**Problem 1 (Sunny Lines):**
- **25 rounds** of adversarial refinement
- **16 BROKEN verdicts** with 17 counterexamples
- **Final answer**: `k ∈ {0} ∪ {odd k : 1 ≤ k ≤ n}`
- **Actual correct answer** (from earlier analysis): `k ∈ {0, 1, n-1}` only

**Critical Observation**: The model **converged to a plausible but WRONG pattern**:
- Claims ALL odd k work (1, 3, 5, 7, ..., n-2, n)
- Reality: Only k ∈ {0, 1, n-1} work
- Error: Overgeneralized from k=1 and k=n-1 being odd

**Problem 2 (Geometry Proof):**
- **20 rounds** of adversarial refinement
- **11 BROKEN verdicts** with 12 counterexamples
- **38.9% SUSPICIOUS rate** - highest sign of justification gaps
- **Final solution**: Uses coordinate geometry with "all gaps removed" claim
- **Reality**: Analysis notes "failed cooperative verification" - proof still has issues

### The Uncomfortable Question: Is This a Capability Limit?

**Null Hypothesis**: No amount of search will help because the model cannot:
1. **Distinguish correct mathematical patterns from plausible-but-wrong patterns**
2. **Generate rigorous proofs** even when it "knows" the answer
3. **Verify its own reasoning** at the granularity needed

**Evidence for Capability Limits:**
- Problem 1: Model settled on "all odd k" pattern - this is a **conceptual error**, not a search error
- Problem 2: 38.9% SUSPICIOUS verdicts mean model keeps generating incomplete proofs
- Even with adversarial pressure, verification cannot detect semantic incorrectness

**Smoking Gun**: After 25 rounds and ~17 counterexamples, the critic NEVER said "wait, k=3 doesn't work for n=4, but k=1 and k=n-1 do - this pattern is {0,1,n-1} not all odd!"

---

## 2. Critique: Monte Carlo Tree Search (MCTS)

### The Nvidia Proposal (Predicted)

"Use MCTS to explore proof space systematically. Each node = partial proof, edges = proof steps, value function = estimated correctness."

### Fatal Flaws

#### Flaw 2.1: You Don't Have a Value Function
**Challenge**: MCTS requires estimating P(correct | partial proof). How?

**Options:**
1. **Use current LLM as value function** - but it already can't distinguish correct from plausible-wrong
2. **Train a value network** - on what data? You don't have ground truth for "proof step correctness"
3. **Use final verification** - but that requires completing the entire proof (defeats purpose of MCTS)

**Concrete Example (Problem 1)**:
- Partial proof: "k can be 0 or 1" (CORRECT so far)
- Next step options:
  - A: "k=3 also works" (seems valid, is WRONG)
  - B: "k=n-1 also works" (seems valid, is CORRECT)
  - C: "all odd k work" (seems valid, is WRONG)

**Question**: How does your value function distinguish A/B/C **without completing the proof**?

**Answer**: It can't. The current LLM thinks all three are equally plausible.

#### Flaw 2.2: Exponential Branching, Linear Value
**Reality Check**: At each proof step, you have ~10-50 plausible next steps
- Depth-10 proof = 10^20 possible paths
- MCTS explores ~1000-10000 paths (computational limit)
- **Coverage**: 10^-16 of search space

**The Optimist Says**: "But MCTS uses the value function to guide search to promising regions!"

**The Realist Says**: "But your value function is the SAME MODEL that produced the wrong answer. Garbage in, garbage out."

#### Flaw 2.3: MCTS Assumes Local Errors
MCTS works when:
- Errors are localized (one wrong move doesn't invalidate entire strategy)
- Backpropagation improves estimates (losing games teach you something)

**IMO Math Problems**:
- Errors are GLOBAL (wrong answer means entire approach is wrong)
- No intermediate reward signal (proof is either correct or wrong, no partial credit)

**Example**: Problem 1 settled on "all odd k" - this is a fundamental conceptual error, not a local mistake in one proof step.

**Question to Nvidia**: What does MCTS backpropagation learn from "wrong answer at the end"? It doesn't know WHICH of the 50 steps was conceptually flawed.

### Cost Analysis

**Assumptions**:
- MCTS explores 5,000 paths (conservative)
- Each path = partial proof generation ($0.10 input + $0.20 output)
- Value function calls = 10,000 evaluations ($0.05 each)

**Total Cost**: 5000 × $0.30 + 10000 × $0.05 = **$2,000 per problem**

**Expected Success Rate**: 5-15% (optimistic, given value function weakness)

**Current RLAC Cost**: ~$3.50 per problem
**Current Success Rate**: 0% (wrong answers)

**ROI**: You're proposing to spend **570× more** for maybe 10% success. That's $20,000 per correct solution.

**Better Alternative**: Spend $2,000 to train a better critic/verifier, which helps ALL approaches.

---

## 3. Critique: Process Supervision (OpenAI's Approach)

### The Proposal (Predicted)

"Verify each proof step individually using a trained reward model. Prune paths with low-confidence steps. Beam search over high-quality step sequences."

### Fatal Flaws

#### Flaw 3.1: Which Steps Do You Verify?
**The Exponential Problem**:
- Problem 2 proof has ~40 logical steps
- Each step has 3-10 dependent sub-claims
- Total verification points: ~200

**Cost per verification**: $0.15 (need high reasoning)

**Options**:
1. **Verify all 200 checkpoints**: $30 per proof × 1000 beam candidates = **$30,000**
2. **Verify only "important" steps**: How do you know which are important before solving?
3. **Verify final answer only**: That's what we already do (doesn't help)

#### Flaw 3.2: Error Accumulation Across Steps
**The Proof Chain Problem**:
```
Step 1: "k=0 is possible" ✓ (VERIFIED: correct)
Step 2: "k=1 is possible" ✓ (VERIFIED: correct)
Step 3: "k=3 is possible" ✓ (VERIFIED: seems correct, actually WRONG)
Step 4: "All odd k follow the same pattern" ✓ (VERIFIED: logical given step 3)
Step 5: "Therefore k ∈ {odd k}" ✓ (VERIFIED: follows from step 4)
```

**Question**: Which step does your verifier catch?
- Step 3 LOOKS correct (k=3 is locally verifiable for specific n)
- Step 4 is logically valid (IF step 3 were true)
- Step 5 is perfectly logical (given steps 1-4)

**The Error**: Overgeneralization from limited cases - a **semantic error**, not a logical error.

**Challenge**: Process supervision verifies LOGICAL validity, not SEMANTIC correctness. Your verifier will approve every step.

#### Flaw 3.3: The Ground Truth Problem
**To train process reward model**, you need:
1. Thousands of proofs with step-by-step labels: "correct" or "wrong"
2. Labels must be at STEP level, not just final answer
3. Must cover diverse error types (logical, semantic, computational, notational)

**Reality**:
- IMO problems: ~50 total in public domain with solutions
- Step-level annotations: ZERO exist
- Cost to annotate: $500/problem × PhD mathematician time
- Total cost: $25,000 to create dataset of 50 annotated proofs

**Then**: Train reward model (unlikely to generalize to new problems)

**ROI**: Spend $25,000 + compute to get 10-20% success rate improvement?

**Better Alternative**: Spend $25,000 on human expert verification for 7,000 problems at $3.50 each.

---

## 4. Critique: Reasoning Effort Scaling

### The Proposal (Predicted)

"Just use more reasoning tokens! Switch from medium→high→extended reasoning effort."

### Diminishing Returns Evidence

**Current Config**:
- Solution generation: `reasoning_effort = low` (fast, prevents truncation)
- Verification: `reasoning_effort = high` (rigorous checking)
- Self-improvement: `reasoning_effort = high` (proactive error detection)

**What "Extended" Reasoning Would Do**:
- 10× more tokens per generation
- 5-10× slower (minutes → hours per round)
- Potential quality improvement: **marginal**

#### The Data

**Problem 1 History**:
- Round 3: Got ROBUST verdict with current config
- Round 22: STILL got ROBUST verdict with same config
- **But final answer is WRONG**

**Interpretation**: High reasoning verification CANNOT detect semantic incorrectness. More reasoning won't help.

**Problem 2 History**:
- 38.9% SUSPICIOUS verdicts despite high reasoning verification
- Geometric proofs have justification gaps even after multiple refinements
- More reasoning = more verbose, not more rigorous

#### Cost Blowup

**Current**:
- 25 rounds × 2min/round × $0.14/round = $3.50 per problem

**Extended Reasoning**:
- Solution: low→extended = 10× tokens = $1.40/round
- Verification: high→extended = 10× tokens = $2.80/round
- Total: $4.20/round × 25 rounds = **$105 per problem**

**Success Rate Improvement**: Optimistically 5-10% (verification still can't catch semantic errors)

**ROI**: **30× cost increase for 5-10% improvement** = economically insane

---

## 5. Critique: Hybrid Approaches (MCTS + Beam Search + RLAC)

### The Proposal (Predicted)

"Combine the best of all worlds:
1. MCTS for strategic exploration
2. Beam search for parallel path evaluation
3. RLAC for adversarial refinement
4. Process supervision for step verification"

### Why This Is An Engineering Nightmare

#### Complexity Explosion
**Components**:
1. MCTS orchestrator (new code)
2. Value function network (train + deploy)
3. Beam search scheduler (resource management)
4. Process reward model (train + deploy)
5. RLAC integration (modified prompts)
6. Step verifier (new infrastructure)

**Integration Points**: 6 × 5 = 30 pairwise interactions

**Failure Modes**:
- MCTS value function contradicts RLAC critic → oscillation
- Beam search prunes path that MCTS wanted to explore → divergence
- Process supervision approves step that RLAC rejects → deadlock
- Resource contention: 3 models fighting for GPU memory

**Debug Complexity**: "Which component failed?" becomes an NP-hard problem

#### The Toy Problem Trap

**Optimist's Evidence**: "We tested on toy problems (high school algebra), hybrid approach got 80% success!"

**Realist's Response**:
- High school algebra has ~10 step proofs with clear error signals
- IMO problems have ~40 step proofs with subtle semantic errors
- Complexity doesn't scale linearly: 4× longer proofs = 20× harder

**Historical Precedent**:
- AlphaGo: Simple rules, perfect simulator, clear win/loss
- AlphaProof: Formal math, verifiable proofs, still struggles on IMO
- **Natural language math**: No ground truth, no verifier, ???

---

## 6. Alternative Hypothesis: The Critic Weakness Problem

### The Core Insight

**Current System**:
- Generator: Produces plausible-but-wrong solutions
- Critic: Finds LOCAL errors (counterexamples, logical gaps)
- **Missing**: Cannot detect GLOBAL semantic incorrectness

**Evidence**:
- Problem 1: Critic found 17 counterexamples but NEVER said "your pattern is wrong"
- Problem 2: Critic flagged justification gaps but NEVER said "coordinate geometry has unstated assumptions"

### What Strong Critics Would Do

**Hypothetical Strong Critic (Problem 1)**:
```
SEMANTIC ANALYSIS:
You claim k ∈ {0, 1, 3, 5, 7, ..., n}.
This is the set of 0 and all odd numbers up to n.

PATTERN VERIFICATION:
- k=0: [verified correct]
- k=1: [verified correct]
- k=3: Let me check for n=4...
  - Need to cover 10 points: (1,1), (1,2), ..., (4,1)
  - With k=3 sunny lines + 1 non-sunny line
  - [exhaustive search] → IMPOSSIBLE

COUNTEREXAMPLE: k=3 fails for n=4

PATTERN IMPLICATION:
Your claim "all odd k" is FALSE.
Correct pattern appears to be: k ∈ {0, 1, n-1} only.
```

**Current Weak Critic**: Found that k=2 doesn't work (which supports "only odd k") but never tested k=3.

### Investment Comparison

| Approach | Cost | Timeline | Success Δ | ROI |
|----------|------|----------|-----------|-----|
| **MCTS (Nvidia)** | $2,000/prob | 6 months dev | +5-10% | 570× cost |
| **Process Supervision (OpenAI)** | $25K dataset + $500/prob | 12 months | +10-15% | Terrible |
| **Extended Reasoning** | $105/prob | Immediate | +5% | 30× cost |
| **Hybrid (All Above)** | $3,000/prob | 18 months | +15-20%? | 860× cost, brittle |
| **STRONG CRITICS** | $10K training + $10/prob | 3 months | +30-50% | **3× cost, robust** |

### How to Build Strong Critics

**Option 1: Specialized Verification Models**
- Train 7B model ONLY for mathematical verification
- Dataset: Synthetic errors + adversarial examples
- Architecture: Retrieval-augmented (access to IMO solution database)
- Cost: $10K compute + 1 month

**Option 2: Multi-Model Ensemble Critics**
- Use 3 different LLMs as critics (GPT-4, Claude, Gemini)
- Aggregate verdicts: BROKEN if 2/3 agree
- Catches model-specific blind spots
- Cost: 3× current critic cost = ~$1.50/round

**Option 3: Formal Verification Layer**
- Auto-convert natural language proofs to Lean/Coq
- Use proof checker for guaranteed correctness
- Hybrid: LLM generates, formal system verifies
- Cost: $50K research + development

---

## 7. Concrete Challenges to Proposed Strategies

### Challenge 1: Prove MCTS Helps (Without Hand-Waving)

**Burden of Proof**: Show mathematically that MCTS explores problem space more effectively than RLAC.

**Required Evidence**:
1. **Proof space coverage**: Measure what % of valid proof strategies MCTS explores
2. **Value function accuracy**: Show your value function correlates with actual correctness
3. **Ablation study**: MCTS vs random search vs RLAC on 20+ problems

**Prediction**: You can't provide this evidence because:
- No ground truth for "proof space" coverage
- Value function is just another LLM (circular reasoning)
- Ablation will show MCTS ≈ random search (both fail)

### Challenge 2: Name ONE Checkpoint That Would Have Helped (Process Supervision)

**Problem 1 Failure Mode**: Model claimed "all odd k" instead of "k ∈ {0,1,n-1}"

**Challenge**: Identify a SPECIFIC PROOF STEP where your process verifier would have said:
- "This step is WRONG" (not "suspicious", not "incomplete" - definitively WRONG)
- AND this would have changed the final answer

**My Prediction**: You can't, because the error is in the PATTERN RECOGNITION (semantic), not in a single logical step.

### Challenge 3: Justify the ROI

**Current State**:
- RLAC cost: $3.50/problem
- RLAC success: 0% (2/2 problems had errors)

**Proposed Scaling Costs**:
- MCTS: ~$2,000/problem
- Process Supervision: ~$500/problem
- Extended Reasoning: ~$105/problem

**Challenge**: Show that your approach achieves >50% success rate to justify the cost.

**My Prediction**: Success rate will be 10-25%, making it economically unviable.

**Better Benchmark**:
- Hire human experts at $100/hour
- Average IMO problem solution time: 3 hours
- Cost: $300/problem guaranteed correct

Your scaling approach must beat $300/problem to be viable.

---

## 8. What Could Go Catastrophically Wrong

### Scenario 1: The Complexity Death Spiral

**Timeline**:
- Month 1: Implement MCTS + RLAC integration
- Month 2: Add process supervision
- Month 3: Debug interaction between MCTS value function and RLAC critic
- Month 4: Discover they contradict each other 40% of the time
- Month 5: Add "meta-adjudicator" to resolve conflicts
- Month 6: Meta-adjudicator introduces new failure mode
- Month 7: Team burnout, project cancellation

**Probability**: 60%

### Scenario 2: The Overfitting Trap

**Timeline**:
- Tune hybrid system on 10 IMO problems
- Achieve 70% success rate (looks great!)
- Test on 10 NEW IMO problems
- Success rate: 15% (catastrophic overfitting)
- Realize you tuned hyperparameters to exploit specific problem patterns
- Retune, performance gets worse

**Probability**: 80%

### Scenario 3: The Cost Explosion

**Timeline**:
- Deploy MCTS system at $2,000/problem
- Discover 5% success rate (worse than expected)
- "Just need more MCTS rollouts!" → $10,000/problem
- Success rate improves to 8%
- CFO asks: "Why are we spending $125,000 per correct solution?"
- Project defunded

**Probability**: 95%

### Scenario 4: The Verification Impossibility

**Timeline**:
- Build process supervision reward model
- Discover it approves semantically wrong steps (they're logically valid)
- "Just need more training data!" → annotate 200 more problems
- Model still can't distinguish semantic from logical errors
- Realize: THIS IS AN UNSOLVED RESEARCH PROBLEM
- Paper published: "On the Fundamental Difficulty of Semantic Verification in Mathematical Reasoning"

**Probability**: 99%

---

## 9. What to Try FIRST (Lowest-Risk Experiments)

### Experiment 1: Multi-Critic Ensemble (1 Week, $500)

**Setup**:
- Run RLAC with 3 different critics (GPT-4, Claude-3.5, Gemini-2.0)
- Verdict = majority vote (2/3 agree)
- Track: Do different models catch different errors?

**Hypothesis**: Ensemble critics catch more semantic errors than single critic

**Success Metric**: >20% improvement in error detection

**Risk**: Low (just API costs)

### Experiment 2: Explicit Pattern Verification (2 Weeks, $1K)

**Setup**:
- After generator proposes answer pattern (e.g., "k ∈ {odd k}")
- Inject verification step: "Test your pattern on n=3,4,5,6 exhaustively"
- Force model to construct explicit examples before generalizing

**Hypothesis**: Explicit verification prevents overgeneralization

**Success Metric**: Catch "all odd k" error in Problem 1

**Risk**: Low (prompt engineering only)

### Experiment 3: Retrieval-Augmented Critics (3 Weeks, $2K)

**Setup**:
- Build database of 50 IMO solutions + common error patterns
- When critic attacks solution, retrieve similar problems
- Critic prompt: "Here's how similar problems were solved correctly..."

**Hypothesis**: Critics with access to ground truth are stronger

**Success Metric**: >30% improvement in error detection

**Risk**: Medium (need to build retrieval system)

### Experiment 4: Formal Verification Fallback (4 Weeks, $5K)

**Setup**:
- Auto-translate final solution to Lean 4
- Run Lean proof checker
- If formal verification fails, request revision

**Hypothesis**: Formal verification catches errors that LLM critics miss

**Success Metric**: Correctly reject both problem 1 & 2 solutions

**Risk**: High (translation quality unknown)

### DO NOT TRY (High Risk, Low Reward)

❌ **MCTS**: 6 months dev, $50K, uncertain value function
❌ **Process Supervision**: 12 months, $100K dataset, semantic errors unsolvable
❌ **Extended Reasoning**: Immediate but 30× cost for 5% gain
❌ **Hybrid Everything**: 18 months, $200K, debugging nightmare

---

## 10. Final Recommendations

### For Research Directors

**SHORT TERM (3 months)**:
1. **Invest in critic diversity**: Test multi-model ensemble critics
2. **Add explicit verification**: Force exhaustive testing before generalization
3. **Benchmark human cost**: Establish $300/problem as the bar to beat

**MEDIUM TERM (6 months)**:
4. **Retrieval-augmented verification**: Build database of solutions + error patterns
5. **Formal verification pipeline**: Auto-translate to Lean, use as sanity check
6. **Measure semantic vs logical errors**: Quantify how many errors are patterns vs steps

**DO NOT DO**:
- ❌ MCTS without proven value function
- ❌ Process supervision without solving semantic verification
- ❌ Hybrid systems without component validation
- ❌ Extended reasoning without ROI justification

### For Nvidia/OpenAI Experts

**Before proposing scaling**:
1. ✅ Show your approach catches the "all odd k" error in Problem 1
2. ✅ Prove your value function/verifier is better than current LLM
3. ✅ Demonstrate >50% success on 20 held-out problems
4. ✅ Cost analysis showing <$300/problem for correct solutions

**If you can't provide all 4**, your proposal is premature.

### The Uncomfortable Truth

**Current RLAC failure is NOT a search problem**:
- Problem 1: Model converged to wrong pattern (semantic error)
- Problem 2: Model cannot produce rigorous proofs (capability gap)

**Scaling search makes you explore more wrong answers faster.**

**What we need**:
- Stronger verification (catch semantic errors)
- Better training data (fewer plausible-but-wrong patterns)
- Formal methods (guaranteed correctness)

**AlphaGo Analogy**:
- AlphaGo succeeded because it had a STRONG value function (trained on millions of games)
- MCTS without good value function = random search
- **You're proposing MCTS without first building the value function**

**Build the value function first. Then we'll talk about MCTS.**

---

## Appendix: Detailed Evidence

### A.1 Problem 1 Error Pattern

**Claimed Answer**: k ∈ {0} ∪ {odd k : 1 ≤ k ≤ n}

**Actual Answer**: k ∈ {0, 1, n-1}

**Test Case n=5**:
- Claimed: k ∈ {0, 1, 3, 5}
- Actual: k ∈ {0, 1, 4} (n-1 = 4)
- **Error**: k=3 claimed possible but actually impossible

**Why Critic Failed**:
- Found counterexamples for k=2 (even) ✓
- Never tested k=3 (odd) ✗
- Assumed "if k=1 works and k=5 works, all odd k work" ✗

### A.2 Problem 2 Justification Gaps

**From logs**: 38.9% SUSPICIOUS verdicts (7/18 rounds)

**Common gap patterns**:
1. "The homothety maps..." - existence not proven
2. "By angle chasing..." - specific angles not computed
3. "It suffices to show..." - equivalence not justified
4. "The discriminant vanishes..." - algebra omitted

**Even final "correct" solution**:
- Coordinate geometry approach
- Claims "identity (3) follows from step 4"
- Identity not explicitly verified
- **Failed cooperative verification** in final check

### A.3 Cost Breakdown

**Current RLAC (Per Problem)**:
```
Generation: 25 rounds × 50K tokens × $0.002/1K = $2.50
Verification: 25 rounds × 20K tokens × $0.002/1K = $1.00
Total: $3.50
Duration: ~2-3 hours
Success: 0% (both problems had errors)
```

**MCTS (Projected)**:
```
Path Exploration: 5000 paths × $0.30 = $1,500
Value Fn Calls: 10000 × $0.05 = $500
Total: $2,000
Duration: ~24 hours (parallelizable to 6 hours)
Success: 10-15% (optimistic)
Cost per success: $13,000-20,000
```

**Process Supervision (Projected)**:
```
Dataset Creation: $25K (one-time)
Per Problem: 200 checkpoints × $0.15 × 1000 beams = $30,000
Success: 15-20% (optimistic)
Cost per success: $150,000-200,000
```

**Extended Reasoning (Projected)**:
```
Generation: 25 rounds × 500K tokens × $0.002/1K = $25
Verification: 25 rounds × 200K tokens × $0.002/1K = $10
Total: $35-105 (depending on extent)
Duration: ~20-30 hours
Success: 5-10% improvement over current
Cost per success: $350-2,100
```

---

**END OF CRITICAL ANALYSIS**

**Summary for Decision Makers**: The proposed scaling strategies (MCTS, process supervision, extended reasoning) address the WRONG PROBLEM. The real issue is weak verification that cannot detect semantic errors. Invest in better critics first, then revisit search-based scaling if critics improve.

**Expected Pushback**: "But scaling worked for AlphaGo/GPT-4/etc!"

**Response**: Those domains had:
1. Perfect simulators (Go) or verifiable outputs (code)
2. Clear reward signals (win/loss, test pass/fail)
3. Dense training data (millions of games/examples)

**Math proofs have NONE of these.** Until you solve verification, scaling search is putting the cart before the horse.
