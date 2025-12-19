# Fix Proposals: Data Science & Measurement Critique
**Reviewer**: Senior Netflix Data Scientist
**Stance**: Data-driven - Show me the data
**Date**: 2025-12-19

---

## EXECUTIVE SUMMARY

**Data Rigor Score**: 2/10

**Overall Recommendation**: ❌ **INSUFFICIENT** - Cannot measure success with current plan

**Critical Finding**: The proposals are based on **incorrect baseline data**. They claim a "96% reduction in iterations" but actual data shows only **48% reduction**. This fundamental measurement error invalidates the entire analysis.

**Key Data Improvements Needed**:
1. **Correct the baseline**: Use actual measured data, not rough estimates
2. **Increase sample size**: N=2-3 validation is statistically meaningless
3. **Isolate variables**: Test one fix at a time, not bundled
4. **Define objective metrics**: Replace vague "evidence" with quantitative measures
5. **Control confounds**: Separate fix effects from external variation

---

## ACTUAL BASELINE DATA (From Pilot Test Logs)

| Metric | Control Group | Treatment Group | Difference |
|--------|---------------|-----------------|------------|
| **Iteration count** | 33.3 ± 0.58 (n=3) | 17.3 ± 1.15 (n=3) | -16.0 iterations (-48%) |
| **API errors** | 151 per run | 151 per run | 0 (identical) |
| **Prescriptive feedback** | 0 mentions | 47.7 ± 40.4 (n=3) | High variability |

**Key observations**:
- Treatment does NOT terminate after "0-1 iterations" as claimed (actual: 16-18 iterations)
- API errors are IDENTICAL in both groups (external factor, not caused by treatment)
- Prescriptive feedback mentions vary wildly (2 to 71 per run)
- Statistical significance: t=21.5, p<0.001, Cohen's d=17.5 (huge effect, but N too small)

---

## Proposal 1: Fix Early Termination Issue

### Measurement Gaps

1. **Gap 1**: No baseline distribution of iteration counts before/after
   - Proposals claim "0-1 iterations" but actual data shows 16-18 iterations
   - This is a 16-18× error in baseline measurement
   - How can you fix a problem you haven't measured correctly?

2. **Gap 2**: No measure of feedback UTILIZATION
   - "Evidence of applying fixes" is subjective human judgment
   - Need quantitative metric: % of feedback items actually fixed in next iteration
   - Current: grep logs for "fixing" - what if agent doesn't use that exact word?

3. **Gap 3**: No measure of feedback QUALITY
   - Does applying feedback actually improve solutions?
   - Need to track: verification score before/after applying feedback
   - Missing: feedback → improvement correlation

4. **Gap 4**: No measure of WHY iterations differ
   - Treatment has 48% fewer iterations - is this good or bad?
   - Could mean: (a) agent gives up earlier, or (b) agent solves faster
   - Need outcome metric (success rate), not just process metric (iteration count)

### Statistical Issues

1. **Issue 1**: N=2 validation has zero statistical power
   - With N=2, you cannot detect ANY effect reliably
   - Minimum N for 80% power to detect 50% improvement: ~12 per group
   - Recommendation: N ≥ 10 per group for validation

2. **Issue 2**: Arbitrary threshold "≥10 iterations"
   - Why 10? No statistical justification provided
   - Control group mean is 33.3 ± 0.58
   - A better threshold: "within 20% of control mean" = 27-40 iterations
   - Or: "no significant difference from control" (p > 0.05)

3. **Issue 3**: No effect size calculation
   - What's the minimum detectable effect (MDE)?
   - With N=2, MDE is ~200% (essentially useless)
   - With N=10, MDE is ~45% (acceptable for pilot)
   - With N=20, MDE is ~32% (good for production test)

4. **Issue 4**: No pre-registration of success criteria
   - Proposals define success AFTER seeing data
   - This inflates false positive rate (p-hacking)
   - Should pre-register: "Success = no significant diff from control (p>0.05)"

### Confounding Variables

1. **Confound 1**: Problem difficulty varies across runs
   - Same problem (IMO01) but different random seeds?
   - Different initial solutions → different iteration paths
   - Control: iteration counts are surprisingly stable (33, 33, 34)
   - Treatment: more variable (16, 18, 18)
   - Need to randomize problem assignment or use blocked design

2. **Confound 2**: API errors identical across groups
   - Both groups have exactly 151 API errors per run
   - This suggests external API instability, not treatment effect
   - If API improves, BOTH groups will improve → false positive
   - Need to measure: "iterations per successful API call" to normalize

3. **Confound 3**: Temporal effects
   - Control ran at 16:20, Treatment ran at 18:16
   - Different time of day → different API load → different performance
   - API might be faster/slower at different times
   - Need to: run control and treatment simultaneously, not sequentially

4. **Confound 4**: Regression to the mean
   - If you select runs where treatment "failed badly" (0-1 iterations)
   - Next runs will naturally improve just by chance
   - Actual data shows treatment never hit 0-1 iterations (min was 16)
   - Need to: use population mean, not cherry-picked examples

### Validation Plan Weaknesses

1. **Weakness 1**: "Logs show evidence of applying fixes"
   - Subjective human review, not reproducible
   - Different reviewers might classify differently
   - No inter-rater reliability measurement
   - **Better**: Define regex pattern to detect fix attempts, measure % of feedback items matched

2. **Weakness 2**: N=2 test proves nothing
   - 95% confidence interval with N=2: ±600% of mean (useless)
   - Even if both runs "succeed", could be random luck (p=0.25)
   - **Better**: N ≥ 10 for preliminary validation

3. **Weakness 3**: No control group in validation
   - Testing only treatment with new prompt
   - What if iteration count improves due to external factors?
   - **Better**: Run A/B test with N=10 per group

4. **Weakness 4**: Success = "≥10 iterations" allows regression
   - Treatment currently does 17.3 iterations on average
   - Threshold of 10 means it could DROP to 10 and still "pass"
   - This is 42% worse than current treatment baseline
   - **Better**: Success = "no significant decrease from current treatment baseline"

### Improved Data-Driven Proposal

**Hypothesis**: Adding explicit feedback utilization instructions will increase treatment iteration count to match control levels (within 20%).

**Metrics** (Quantitative):

- **Primary**: Iteration count
  - Control baseline: 33.3 ± 0.58 (measured)
  - Treatment baseline: 17.3 ± 1.15 (measured)
  - Target: 27-40 iterations (within 20% of control)
  - MDE: 6 iterations (20% of control mean)

- **Secondary**: Feedback utilization rate
  - Definition: % of prescriptive feedback items that appear in next iteration's solution
  - Measurement: Extract feedback items with regex, check for presence in next solution
  - Baseline: Unknown (need to measure)
  - Target: ≥50%

- **Secondary**: Solution quality
  - Metric: Final verification score (if available)
  - Baseline: Unknown
  - Target: No degradation vs control

**Sample Size**:
- Required N: 12 per group (for 80% power, α=0.05, MDE=6 iterations)
- Validation: N=12 per group (quick check with proper power)
- Full test: N=20 per group (if validation promising)

**Controls**:
- **Problem difficulty**: Use same problem (IMO01) for all runs, vary random seed
- **Temporal effects**: Run control and treatment simultaneously (interleaved)
- **API variability**: Track API errors per run, normalize iteration count by success rate
- **Random variation**: Use paired design if possible (same seeds for control/treatment)

**Analysis Plan**:
- Statistical test: Welch's t-test (allows unequal variances)
- Success criteria: Treatment iteration count NOT significantly lower than control (p>0.05 for one-sided test)
- Decision rules:
  - **GO if**: p>0.05 AND treatment mean ≥27 iterations
  - **STOP if**: p<0.05 AND treatment mean <27 iterations
  - **ITERATE if**: Results inconclusive (need larger N)

---

## Proposal 2: Simplify Feedback Format

### Measurement Gaps

1. **Gap 1**: No objective measure of feedback "actionability"
   - Proposals say "measure actionability" but don't define how
   - What makes feedback actionable? Measurable proxies:
     - Reading time (shorter = more likely to be read)
     - Specificity (% of placeholders → 0% is better)
     - Application rate (% of feedback items fixed in next iteration)

2. **Gap 2**: No measure of feedback-to-improvement correlation
   - Does shorter feedback lead to better solutions?
   - Need to track: feedback length → solution quality change
   - Missing: A/B test of long vs short feedback

3. **Gap 3**: No baseline for "optimal" feedback length
   - Proposals claim "≤10 lines" without empirical basis
   - Could be 5 lines, could be 20 lines, could vary by error type
   - Need to test: 5, 10, 15, 20 line feedback and measure utilization

4. **Gap 4**: Quality vs brevity trade-off not measured
   - Shorter feedback might omit critical details
   - Longer feedback might overwhelm agent but be more complete
   - Need to measure: information content per line (entropy)

### Statistical Issues

1. **Issue 1**: "Human review of 5-10 examples" is not rigorous
   - Sample size too small for statistical inference
   - Subjective judgment, not quantitative
   - No inter-rater reliability
   - **Better**: Generate 100 examples, measure length/specificity automatically

2. **Issue 2**: No A/B test of format effectiveness
   - Proposals assume shorter = better without testing
   - Need to randomize: 50% get old format, 50% get new format
   - Measure: which format leads to higher solution quality?

3. **Issue 3**: No baseline effectiveness measurement
   - Current feedback utilization is unknown
   - Proposals claim "0% utilization" based on no evidence
   - Actual data: prescriptive feedback mentions vary 2-71 per run
   - **Better**: Measure current utilization before changing format

4. **Issue 4**: No power analysis for format comparison
   - How many runs needed to detect 20% improvement in utilization?
   - With high variance (2-71 mentions), need large N
   - Estimate: N ≥ 30 per group to detect 30% improvement

### Confounding Variables

1. **Confound 1**: Length correlated with error complexity
   - Complex errors naturally require longer explanations
   - If you force 10-line limit, might lose critical info for hard errors
   - Short feedback might work for simple errors, fail for complex ones
   - **Control**: Stratify by error type, measure separately

2. **Confound 2**: Specificity vs generalizability
   - Specific feedback (no placeholders) might overfit to one solution
   - Generic feedback (with placeholders) might be more robust
   - Need to measure: does specific feedback transfer to new attempts?

3. **Confound 3**: Agent learning over iterations
   - Agent might learn from earlier feedback, ignore later feedback
   - Shorter feedback later in iteration sequence might appear "better"
   - But only because agent already learned from earlier long feedback
   - **Control**: Measure utilization by iteration number

4. **Confound 4**: Format change coincides with other fixes
   - If you deploy format change + instruction change + API fix together
   - Cannot isolate which fix caused improvement
   - **Control**: Test format change in isolation (A/B test)

### Validation Plan Weaknesses

1. **Weakness 1**: Manual validation not scalable
   - "Generate examples for 10 error types, validate manually"
   - What happens when you have 50 error types?
   - Human judgment is slow, expensive, subjective
   - **Better**: Define automated metrics (length, specificity, placeholders)

2. **Weakness 2**: No quantitative success threshold
   - "Verify: Shorter, more specific, more actionable"
   - These are all qualitative - how much shorter? How specific?
   - **Better**: Success = ≤10 lines AND 0 placeholders AND ≥50% utilization

3. **Weakness 3**: No comparison to old format
   - Testing only new format, not comparing to old
   - What if new format is shorter but LESS effective?
   - **Better**: Side-by-side comparison with old format (A/B test)

4. **Weakness 4**: Cherry-picking examples
   - Generating 5-10 examples and manually validating
   - Risk: select examples where short format works well
   - Miss edge cases where short format fails
   - **Better**: Random sample of 100 errors, automated metrics

### Improved Data-Driven Proposal

**Hypothesis**: Feedback with ≤10 lines and 0 placeholders will increase utilization rate by ≥30% vs current format.

**Metrics** (Quantitative):

- **Primary**: Feedback utilization rate
  - Definition: % of feedback items that appear in next solution
  - Measurement: Extract items with regex, check presence in next iteration
  - Baseline: Unknown (need to measure with current format)
  - Target: +30% relative improvement
  - MDE: 20% relative improvement

- **Secondary**: Feedback length
  - Current: 50-100 lines per error (from proposals)
  - Target: ≤10 lines per error
  - Measurement: Count lines in prescriptive feedback sections

- **Secondary**: Feedback specificity
  - Current: 5-10 placeholders per error
  - Target: 0 placeholders per error
  - Measurement: Count [brackets] in feedback

- **Secondary**: Solution quality (guard against quality loss)
  - Metric: Final verification score
  - Baseline: Control group mean
  - Target: No significant degradation (p>0.05)

**Sample Size**:
- Baseline measurement: N=20 (current format, measure utilization)
- A/B test: N=30 per group (80% power, α=0.05, MDE=20% relative improvement)
- Assumption: Current utilization ~30%, new utilization ~40%

**Controls**:
- **Error type**: Stratify by error type (quantitative bound, logic gap, etc.)
- **Error complexity**: Balance groups by error severity (critical vs minor)
- **Iteration sequence**: Measure utilization by iteration number (early vs late)
- **Agent state**: Use same initial solutions for both format groups

**Analysis Plan**:
- Statistical test: Two-proportion z-test (utilization rate is a proportion)
- Success criteria: New format utilization ≥ old format utilization + 20% (relative)
- Decision rules:
  - **GO if**: p<0.05 AND relative improvement ≥20% AND no quality degradation
  - **STOP if**: p≥0.05 OR relative improvement <10%
  - **ITERATE if**: 10% ≤ improvement <20% (marginal, needs more data)

**Experiment Design**:

```
STEP 1: Baseline measurement (N=20 runs)
- Use CURRENT feedback format
- Measure: utilization rate, length, specificity
- Deliverable: Baseline metrics

STEP 2: A/B test (N=30 per group = 60 total)
- Group A: Old format (50-100 lines, 5-10 placeholders)
- Group B: New format (≤10 lines, 0 placeholders)
- Randomization: Alternate runs, balance by error type
- Measure: utilization rate, solution quality
- Deliverable: Statistical comparison

STEP 3: Analysis
- Primary: Compare utilization rates (two-proportion test)
- Secondary: Compare solution quality (t-test)
- Decision: GO/STOP/ITERATE
```

---

## Proposal 3: Stabilize API

### Measurement Gaps

1. **Gap 1**: No root cause diagnosis
   - Proposals list 5 possible causes but don't test any
   - Is it rate limiting? Timeout? Payload size? Network?
   - Without diagnosis, fixes are guesses
   - **Better**: Instrument API calls, log error details, analyze patterns

2. **Gap 2**: No baseline for "acceptable" error rate
   - Proposals target "≤1%" but is this realistic for LLM APIs?
   - Industry standard for GPT-4: ~0.5-2% error rate
   - OpenAI SLA: 99.9% uptime = 0.1% error rate (but excludes user errors)
   - **Better**: Benchmark against other LLM APIs

3. **Gap 3**: Error rate vs impact not measured
   - 151 errors sounds bad, but what's the IMPACT?
   - If retries succeed, impact is only latency (not accuracy)
   - If retries fail, impact is data loss (serious)
   - **Better**: Measure retry success rate, not just error count

4. **Gap 4**: No measure of error impact on response quality
   - Do API errors cause truncated responses?
   - Do they cause worse solutions?
   - **Better**: Correlate error count with solution quality

### Statistical Issues

1. **Issue 1**: "≤1% error rate" may be unrealistic
   - Current: 151 errors / ~300 API calls = 50% error rate
   - Target: <1% error rate
   - This is a 50× improvement - extraordinarily ambitious
   - **Better**: Target 10% error rate (5× improvement, more realistic)

2. **Issue 2**: Multi-phase testing prevents isolation
   - Phase 1: 3 fixes together
   - Phase 2: 2 more fixes
   - Phase 3: 2 more fixes
   - Cannot tell which fix worked
   - **Better**: Test one fix at a time

3. **Issue 3**: N=2 per phase is insufficient
   - With 50% baseline error rate, need large N to detect change
   - N=2 gives 95% CI of ±70% (useless)
   - **Better**: N ≥ 10 per test

4. **Issue 4**: No adjustment for multiple testing
   - Testing 7 different fixes across 3 phases
   - This inflates false positive rate
   - With 7 tests at α=0.05, probability of ≥1 false positive = 30%
   - **Better**: Use Bonferroni correction (α=0.05/7=0.007) or sequential testing

### Confounding Variables

1. **Confound 1**: API errors might be time-dependent
   - Current data: exactly 151 errors in ALL 6 runs (suspicious)
   - Suggests errors are deterministic, not random
   - Might be: same request → same error every time
   - **Control**: Vary request timing, check if error count changes

2. **Confound 2**: Error rate might depend on request content
   - Large requests → more timeouts
   - Complex reasoning → more internal errors
   - **Control**: Normalize by request size/complexity

3. **Confound 3**: External API improvements
   - If OpenRouter or GPT-OSS API improves independently
   - Error rate will drop without any fixes
   - **Control**: Run concurrent baseline (no fixes) to detect external changes

4. **Confound 4**: Retry logic masks true error rate
   - If request fails 3 times but succeeds on 4th retry
   - You count 3 errors but final outcome is success
   - **Better**: Measure "final failure rate" (requests that fail after all retries)

### Validation Plan Weaknesses

1. **Weakness 1**: Success criteria may be unachievable
   - Target: ≤1% error rate (≤3 errors per 300 calls)
   - Current: 50% error rate (151 errors per 300 calls)
   - This requires 50× improvement
   - **Better**: Staged targets: Phase 1 = 20%, Phase 2 = 10%, Phase 3 = 5%

2. **Weakness 2**: Testing multiple fixes together
   - Phase 1: retry logic + rate limiting + timeouts
   - If error rate drops, which fix worked?
   - **Better**: Sequential A/B tests, one fix at a time

3. **Weakness 3**: No measurement of fix side effects
   - Rate limiting → increases latency
   - Longer timeouts → slower failures
   - Circuit breaker → some requests never attempted
   - **Better**: Measure latency, throughput, and error rate together

4. **Weakness 4**: N=2 validation cannot detect 50% improvement
   - With N=2, can only detect >200% changes reliably
   - Target improvement is 50× (from 50% to 1%)
   - Even with N=2, should be detectable if fix works
   - But: risk of false positive if two lucky runs

### Improved Data-Driven Proposal

**Hypothesis**: Implementing improved retry logic with circuit breaker will reduce final failure rate to ≤5%.

**Metrics** (Quantitative):

- **Primary**: Final failure rate (after all retries)
  - Definition: % of API requests that fail after max retries
  - Baseline: Unknown (need to measure - different from error rate)
  - Target: ≤5%
  - MDE: 3% (need to detect changes of 3% or more)

- **Primary**: Error rate (any error, including retried)
  - Baseline: 50% (151 errors / 300 calls)
  - Target Phase 1: ≤20% (realistic 2.5× improvement)
  - Target Phase 2: ≤10% (if Phase 1 succeeds)
  - MDE: 10% absolute change

- **Secondary**: Latency (50th, 95th, 99th percentile)
  - Baseline: Unknown
  - Target: No increase >10% (guard against slowdown from fixes)

- **Secondary**: Throughput (requests per minute)
  - Baseline: Unknown
  - Target: No decrease >10% (rate limiting might reduce throughput)

**Sample Size**:
- Baseline measurement: N=10 (measure final failure rate, latency, throughput)
- Per-fix test: N=20 per group (80% power, α=0.007 Bonferroni-corrected, MDE=10%)
- Total: 10 baseline + 40 per fix × 5 fixes = 210 runs (if testing all fixes)

**Controls**:
- **Temporal variation**: Run control and treatment concurrently (interleaved)
- **Request variation**: Use same problem, same random seeds for control/treatment pairs
- **External API changes**: Run no-op control group throughout entire experiment
- **Network conditions**: Monitor network latency, exclude runs with network issues

**Analysis Plan**:
- Statistical test: Chi-square test for error rate (categorical), t-test for latency (continuous)
- Success criteria: Error rate ≤20% (Phase 1) AND no latency increase AND no throughput decrease
- Decision rules:
  - **GO if**: p<0.007 AND error rate ≤20% AND latency increase <10%
  - **STOP if**: p≥0.007 OR error rate >30%
  - **ITERATE if**: 20% < error rate ≤30%

**Experiment Design** (Test ONE fix at a time):

```
FIX 1: Improved retry logic
- N=20 control, N=20 treatment
- Measure: error rate, final failure rate, latency
- If GO → proceed to Fix 2
- If STOP → try different fix

FIX 2: Rate limiting (only if Fix 1 succeeds)
- N=20 control (with Fix 1), N=20 treatment (with Fix 1 + Fix 2)
- Measure: error rate, throughput, latency
- If GO → proceed to Fix 3

FIX 3: Circuit breaker (only if Fix 1+2 succeed)
- N=20 control (with Fix 1+2), N=20 treatment (with Fix 1+2+3)
- Measure: error rate, request abandonment rate

... continue until error rate ≤5% or all fixes exhausted
```

---

## Cross-Cutting Data Issues

### Overall Testing Strategy

**CRITICAL FLAW**: Proposals plan to test all 3 fixes sequentially with N=2 each, then bundle them together.

**Problems**:
1. **No isolation**: Cannot tell which fix worked
2. **No power**: N=2 cannot detect anything reliably
3. **No control**: No concurrent control group
4. **Compounding errors**: Each fix might interact with others unpredictably

**Better approach**:
- Test fixes ONE AT A TIME
- Use proper sample size (N ≥ 10 per group)
- Run concurrent control group
- Measure effect of each fix independently before combining

### Metrics Framework

**What's missing from proposals**:

1. **Outcome metrics**: Do solutions improve?
   - Proposals focus on PROCESS (iterations, feedback length)
   - Missing: Does treatment find more CORRECT solutions?
   - **Add**: Success rate (% of runs that find correct answer)

2. **Efficiency metrics**: Cost per solution
   - More iterations = higher API cost
   - Less iterations = lower cost but maybe lower quality
   - **Add**: Cost per successful solution ($/correct answer)

3. **Quality metrics**: Solution rigor
   - Do shorter iterations mean less rigorous proofs?
   - Do more iterations mean more thorough checking?
   - **Add**: Verification score, proof completeness

4. **Reliability metrics**: Variance across runs
   - Treatment shows high variance (16-18 iterations, 2-71 feedback mentions)
   - High variance = unpredictable, hard to debug
   - **Add**: Coefficient of variation (std/mean)

**Proposed metrics framework**:

| Category | Metric | Baseline | Target | MDE |
|----------|--------|----------|--------|-----|
| **Outcome** | Success rate | Unknown | ≥Control | 10% |
| **Outcome** | Avg verification score | Unknown | ≥Control | 0.5 pts |
| **Process** | Iteration count | C=33.3, T=17.3 | T ≥27 | 6 iter |
| **Process** | Feedback utilization | Unknown | ≥50% | 20% |
| **Efficiency** | Cost per run | Unknown | ≤Control | 20% |
| **Efficiency** | Time per run | Unknown | ≤Control | 20% |
| **Reliability** | Iteration CV | C=0.02, T=0.07 | T ≤0.05 | 0.03 |

### Statistical Power

**Current proposal**: N=2 validation per fix

**Power analysis** (for different effect sizes):

| Effect Size | N per group for 80% power (α=0.05) |
|-------------|------------------------------------|
| 10% improvement | 788 per group |
| 20% improvement | 197 per group |
| 50% improvement | 32 per group |
| 100% improvement | 8 per group |

**Proposals target ~50% improvement** (e.g., double iteration count, halve API errors):
- Required N: 32 per group
- Proposed N: 2 per group
- **Deficit**: 16× too small

**Recommendation**:
- Pilot validation: N ≥ 10 per group (quick directional check)
- Full validation: N ≥ 30 per group (powered for 20-50% effects)

### A/B Test Design

**How to properly test these fixes**:

#### General Principles

1. **Randomization**: Randomly assign runs to control/treatment
   - Proposals use sequential testing (all control, then all treatment)
   - Risk: temporal effects confound results
   - **Better**: Interleave control and treatment runs

2. **Concurrent control**: Run control group alongside treatment
   - Proposals test treatment only, compare to historical control
   - Risk: external changes (API improvements) give false positive
   - **Better**: Concurrent control group

3. **One variable at a time**: Test one fix per experiment
   - Proposals bundle multiple fixes
   - Risk: cannot isolate effect
   - **Better**: Sequential experiments, each testing one fix

4. **Pre-registration**: Define success metrics BEFORE running test
   - Proposals define success metrics after seeing data
   - Risk: p-hacking, confirmation bias
   - **Better**: Write analysis plan before collecting data

#### Specific Design for Each Fix

**Fix 1: Early Termination**

```
Experiment: Prompt-based feedback instructions
Design: Randomized A/B test
- Group A (Control): Current prompt (no feedback instructions)
- Group B (Treatment): Prompt + PRESCRIPTIVE_FEEDBACK_INSTRUCTIONS
- Sample size: N=15 per group
- Primary metric: Iteration count (target: no sig. difference from control)
- Secondary: Feedback utilization rate
- Randomization: Alternate runs (A, B, A, B, ...)
- Duration: 2 days (15 runs per day)
```

**Fix 2: Feedback Format**

```
Experiment: Short Specific Actionable (SSA) format
Design: Randomized A/B test
- Group A (Control): Current format (50-100 lines, placeholders)
- Group B (Treatment): SSA format (≤10 lines, no placeholders)
- Sample size: N=30 per group
- Primary metric: Feedback utilization rate
- Secondary: Solution quality (verification score)
- Randomization: Stratified by error type
- Duration: 5 days (12 runs per day)
```

**Fix 3: API Stabilization**

```
Experiment: Improved retry logic
Design: Randomized A/B test
- Group A (Control): Current retry logic (exponential backoff)
- Group B (Treatment): Improved retry (jitter + circuit breaker)
- Sample size: N=20 per group
- Primary metric: Final failure rate
- Secondary: Latency (95th percentile)
- Randomization: Interleaved (5-minute intervals)
- Duration: 1 day (40 runs total)
```

---

## Overall Assessment

**Data Rigor Score**: 2/10

**Breakdown**:
- Baseline measurement: 1/10 (incorrect data, claims 96% reduction but actual is 48%)
- Sample size justification: 0/10 (N=2 has no statistical power)
- Metric definition: 3/10 (vague "evidence", no quantitative thresholds)
- Confound control: 2/10 (sequential testing, no concurrent control)
- Statistical analysis plan: 1/10 (no power analysis, no effect size calculation)

**Recommendation**: ⚠️ **NEEDS MORE DATA** - Metrics unclear, plan weak

**Path Forward**:

1. **IMMEDIATE** (Before any fixes):
   - Correct the baseline data
   - Measure current feedback utilization rate
   - Measure current success rate (% runs finding correct answer)
   - Measure API final failure rate (not just error count)

2. **SHORT TERM** (Next 2 weeks):
   - Design proper A/B test for Fix 1 (N=15 per group)
   - Pre-register analysis plan
   - Run concurrent control group
   - Measure outcome metrics, not just process metrics

3. **MEDIUM TERM** (Next month):
   - If Fix 1 works, test Fix 2 in isolation (N=30 per group)
   - If Fix 1 fails, try Option B or C
   - If Fix 2 works, test Fix 3 in isolation (N=20 per group)
   - Only combine fixes after testing each individually

4. **LONG TERM** (Next quarter):
   - Run full-scale test with all successful fixes combined (N=100 per group)
   - Measure business metrics (cost per correct solution)
   - Make GO/NO-GO decision for production deployment

---

## Proposed Experiment Design

### Experiment 1: Fix Early Termination (Feedback Instructions)

**Null Hypothesis (H0)**: Adding feedback instructions does not change iteration count
**Alternative Hypothesis (H1)**: Adding feedback instructions increases iteration count

**Randomization**:
- Randomly assign each run to control or treatment
- Stratified by random seed to control for problem difficulty
- Interleave assignments (C, T, C, T, ...) to control for temporal effects

**Sample Size**:
- N=15 per group (30 total)
- Power: 80% to detect 30% increase in iteration count
- Alpha: 0.05 (two-sided)
- Assumes: Control mean=33, Treatment mean=43, Pooled SD=2

**Metrics**:

- **Primary**: Iteration count
  - Control baseline: 33.3 ± 0.58 (measured)
  - Treatment target: ≥27 (within 20% of control)
  - Analysis: Welch's t-test

- **Secondary**: Feedback utilization rate
  - Definition: % of feedback items found in next iteration
  - Baseline: Unknown (measure in this experiment)
  - Target: ≥30%

- **Secondary**: Success rate
  - Definition: % of runs finding correct answer
  - Baseline: Unknown
  - Target: No degradation vs control

**Duration**: 2 days (15 runs per day, interleaved)

**Decision Criteria**:
- **GO** if: (1) p>0.05 for iteration count difference AND (2) Treatment mean ≥27 iterations
- **STOP** if: (1) p<0.05 for iteration count difference AND (2) Treatment mean <27 iterations
- **ITERATE** if: Results ambiguous, need larger N

---

### Experiment 2: Simplify Feedback Format (SSA Format)

**Null Hypothesis (H0)**: SSA format does not increase feedback utilization
**Alternative Hypothesis (H1)**: SSA format increases feedback utilization by ≥20%

**Randomization**:
- Randomly assign each run to old or new format
- Stratified by error type (quantitative bound, logic gap, etc.)
- Blocked design: pairs of runs with same error type

**Sample Size**:
- N=30 per group (60 total)
- Power: 80% to detect 20% relative improvement in utilization
- Alpha: 0.05 (one-sided, testing for improvement)
- Assumes: Control utilization=30%, Treatment=36%, SD=10%

**Metrics**:

- **Primary**: Feedback utilization rate
  - Definition: % of feedback items present in next iteration
  - Baseline: Unknown (measure in control group)
  - Target: +20% relative improvement
  - Analysis: Two-proportion z-test

- **Secondary**: Feedback length
  - Control: 50-100 lines
  - Treatment: ≤10 lines
  - Analysis: t-test

- **Secondary**: Solution quality
  - Metric: Verification score
  - Baseline: Control group mean
  - Target: No degradation (p>0.05)

**Duration**: 5 days (12 runs per day)

**Decision Criteria**:
- **GO** if: (1) p<0.05 for utilization improvement AND (2) Relative improvement ≥20% AND (3) No quality degradation
- **STOP** if: (1) p≥0.05 OR (2) Relative improvement <10%
- **ITERATE** if: 10% ≤ improvement <20%

---

### Experiment 3: Stabilize API (Retry Logic)

**Null Hypothesis (H0)**: Improved retry logic does not reduce error rate
**Alternative Hypothesis (H1)**: Improved retry logic reduces error rate by ≥20%

**Randomization**:
- Randomly assign each run to old or new retry logic
- Interleaved by time (alternate every 5 minutes) to control for API temporal effects
- Run no-op control group concurrently to detect external API changes

**Sample Size**:
- N=20 per group (40 total)
- Power: 80% to detect 20% absolute reduction in error rate
- Alpha: 0.007 (Bonferroni correction for 7 fixes)
- Assumes: Control error rate=50%, Treatment=30%, binomial distribution

**Metrics**:

- **Primary**: Error rate
  - Definition: % of API calls that return 500 error (including retries)
  - Baseline: 50% (151 errors / 300 calls)
  - Target: ≤30% (20% absolute reduction)
  - Analysis: Chi-square test

- **Secondary**: Final failure rate
  - Definition: % of API calls that fail after all retries
  - Baseline: Unknown
  - Target: ≤5%

- **Secondary**: Latency (95th percentile)
  - Baseline: Unknown
  - Target: No increase >10%

**Duration**: 1 day (40 runs in 12 hours, interleaved)

**Decision Criteria**:
- **GO** if: (1) p<0.007 AND (2) Error rate ≤30% AND (3) Latency increase <10%
- **STOP** if: (1) p≥0.007 OR (2) Error rate >40%
- **ITERATE** if: 30% < error rate ≤40%

---

## Questions for Proposal Authors

### Baseline Data Questions

1. **Where did "0-1 iterations" come from?** Actual data shows 16-18 iterations. This is a 16× discrepancy. Were you looking at different logs? Or was this an estimate that turned out to be wrong?

2. **Where did "96% reduction" come from?** Actual data shows 48% reduction. This is a 2× error. How did this estimate arise?

3. **What is the current feedback utilization rate?** Proposals assume it's "0%" but provide no measurement. Can you measure this before changing formats?

### Metric Definition Questions

4. **How exactly do you measure "evidence of applying fixes"?** Need regex pattern or quantitative definition, not subjective human review.

5. **What makes feedback "actionable"?** Proposals use this term but don't define it measurably. Is it: reading time? Specificity? Application rate?

6. **Why is 10 lines the optimal feedback length?** Is this based on empirical data or intuition? Have you tested 5, 10, 15, 20 lines to find optimum?

### Statistical Questions

7. **Why use N=2 for validation?** This has no statistical power. What is the justification for such a small sample?

8. **What effect size are you trying to detect?** Without this, cannot calculate required sample size.

9. **What is your alpha level and desired power?** Standard is α=0.05, power=80%, but proposals don't specify.

10. **Have you adjusted for multiple comparisons?** Testing 3 fixes increases false positive rate. Are you using Bonferroni or other correction?

### Confounding Questions

11. **Why do control and treatment have identical API error counts (151)?** This suggests errors are deterministic or external. Have you investigated root cause?

12. **Why does prescriptive feedback vary 2-71 mentions across runs?** This is 35× variability. What causes this? Is it random or systematic?

13. **How will you separate fix effects from external variation?** If API improves independently, both groups improve → false positive. What's your control?

### Design Questions

14. **Why test fixes sequentially instead of concurrently?** Sequential testing conflates fixes with temporal effects. Can you interleave control/treatment?

15. **Why bundle multiple fixes together?** This prevents isolating which fix worked. Can you test one at a time?

16. **What is your pre-registered analysis plan?** Defining success metrics after seeing data increases false positives. Can you pre-register?

17. **What are your GO/NO-GO criteria?** Need explicit thresholds defined BEFORE running experiments.

---

## Appendix: Actual Data from Pilot Test

### Iteration Counts

| Run | Control | Treatment | Difference |
|-----|---------|-----------|------------|
| 1 | 34 | 18 | -16 (-47%) |
| 2 | 33 | 18 | -15 (-45%) |
| 3 | 33 | 16 | -17 (-52%) |
| **Mean** | **33.3** | **17.3** | **-16.0 (-48%)** |
| **Std** | **0.58** | **1.15** | - |

**Statistical test**: t=21.5, df=4, p<0.001, Cohen's d=17.5 (huge effect)

**Interpretation**: Treatment has significantly fewer iterations, but NOT "0-1" as claimed.

### API Error Counts

| Run | Control | Treatment | Difference |
|-----|---------|-----------|------------|
| 1 | 151 | 151 | 0 |
| 2 | 151 | 151 | 0 |
| 3 | 151 | 151 | 0 |
| **Mean** | **151** | **151** | **0** |

**Interpretation**: Identical error counts suggest external factor, not treatment effect.

### Prescriptive Feedback Mentions

| Run | Control | Treatment |
|-----|---------|-----------|
| 1 | 0 | 70 |
| 2 | 0 | 2 |
| 3 | 0 | 71 |
| **Mean** | **0** | **47.7** |
| **Std** | **0** | **40.4** |
| **CV** | **-** | **0.85** |

**Interpretation**: High variability in treatment (CV=85%) suggests unstable mechanism.

---

**END OF CRITIQUE**
