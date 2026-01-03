# Statistical Analysis Report: Validation Test Results
**Date:** 2025-12-28  
**Analyst Role:** Senior Netflix Data Scientist  
**Sample Size:** N=30 iterations, 6 tests each (180 total observations)

---

## Executive Summary

**Key Finding:** Test 1 has a **statistically significant underperformance** (56.7% vs 90% expected, p < 0.000001). This is a **real systematic issue**, not random variation.

**Recommendation:** Run BFS baseline tests (Option B) immediately. Let baseline results guide whether to invest in fixing Test 1.

---

## STATISTICAL FINDINGS

### 1. Test Performance Overview

| Test | Pass | Fail | Accuracy | 95% CI |
|------|------|------|----------|--------|
| Test 1 | 17 | 13 | 56.7% | [39.2%, 72.6%] |
| Test 2 | 27 | 3 | 90.0% | [73.5%, 97.9%] |
| Test 3 | 30 | 0 | 100.0% | [88.4%, 100.0%] |
| Test 4 | 26 | 4 | 86.7% | [69.3%, 96.2%] |
| Test 5 | 28 | 2 | 93.3% | [77.9%, 99.2%] |
| Test 6 | 27 | 3 | 90.0% | [73.5%, 97.9%] |
| **Overall** | **155** | **25** | **86.1%** | [80.3%, 90.4%] |

### 2. Test 1 Failure Distribution: **SYSTEMATIC**

**Failure Iterations:** 3, 4, 7, 8, 13, 15, 18, 20, 21, 24, 25, 28, 29 (13/30)

**Pattern Analysis:**
- **Isolated failures:** 9/13 (69%) - Test 1 fails alone with no other test failures
- **Clustered failures:** 4/13 (31%) - Test 1 fails with other tests
- **Distribution:** Failures appear random across iterations, suggesting consistent verifier behavior rather than specific input sensitivity

**Conclusion:** Test 1 has a **systematic verification issue**, independent of iteration number or other test performance.

### 3. Cross-Test Correlations: **NEGLIGIBLE TO WEAK**

| Test Pair | Both Fail | T1 Only | Tn Only | Both Pass | Phi Coefficient | Interpretation |
|-----------|-----------|---------|---------|-----------|-----------------|----------------|
| T1 vs T2 | 0 | 13 | 3 | 14 | -0.291 | Weak negative |
| T1 vs T3 | 0 | 13 | 0 | 17 | undefined | Perfect independence |
| T1 vs T4 | 2 | 11 | 2 | 15 | +0.053 | Negligible |
| T1 vs T5 | 1 | 12 | 1 | 16 | +0.036 | Negligible |
| T1 vs T6 | 2 | 11 | 1 | 16 | +0.157 | Weak positive |

**Key Insights:**
- Test 1 and Test 2 **NEVER fail together** (0/30 iterations)
- Test 1 failures are **independent** of other test failures (phi < 0.3 for all pairs)
- Test 1 has a **unique failure mode** not shared with other tests

**Conclusion:** Test 1's problem is **isolated** to its specific test case, not a general verifier issue.

### 4. Statistical Significance: **HIGHLY SIGNIFICANT**

#### Chi-Square Test (Test 1 vs Others Combined)
```
Test 1:      17/30  = 56.7%
Others avg:  138/150 = 92.0%

Chi-square statistic: 23.23
P-value: 0.000001 (1.4 × 10⁻⁶)
Result: HIGHLY SIGNIFICANT ***
```

#### Fisher's Exact Test (Test 1 vs Test 2)
```
Test 1: 17/30 = 56.7%
Test 2: 27/30 = 90.0%

Odds ratio: 0.145 (Test 1 is 85% less likely to pass)
P-value: 0.007410
Result: SIGNIFICANT *
```

#### Binomial Test (Test 1 vs Expected 90% Baseline)
```
Observed: 17/30 = 56.7%
Expected: 27/30 = 90.0%
Difference: -33.3%

P-value: 0.0000023 (2.3 × 10⁻⁶)
Result: EXTREMELY SIGNIFICANT ***

Probability of observing ≤17 successes if true rate is 90%: 
  1 in 434,343 (this is NOT a random event)
```

**Conclusion:** Test 1's underperformance is **NOT due to chance**. The 95% confidence interval [39.2%, 72.6%] does NOT overlap with the 90% baseline, confirming a real systematic issue.

### 5. Power Analysis: **ADEQUATE FOR DECISION-MAKING**

#### What N=30 Can Detect (α=0.05, Power=0.80)

| Baseline | Minimum Detectable Difference | Detectable Range |
|----------|-------------------------------|------------------|
| 85% | ±18.3% | [66.7%, 103.3%] |
| 90% | ±15.3% | [74.7%, 105.3%] |
| 95% | ±11.1% | [83.9%, 106.1%] |

**Test 1's Performance:**
- Observed: 56.7% (33.3% below baseline)
- Required MDE: 15.3% at 90% baseline
- Actual difference: **2.2× larger than minimum detectable**

**Conclusion:** N=30 provides **more than adequate power** to detect Test 1's underperformance. More samples would NOT change the conclusion.

#### Sample Size for Smaller Effects

To detect differences from 90% baseline (α=0.05, Power=0.80):

| Target Difference | Required N | Current N=30 Status |
|-------------------|------------|---------------------|
| 5% (90% → 85%) | 685 | ✗ INSUFFICIENT (need 655 more) |
| 10% (90% → 80%) | 199 | ✗ INSUFFICIENT (need 169 more) |
| 15% (90% → 75%) | 100 | ✗ INSUFFICIENT (need 70 more) |

**Note:** For BFS baseline testing, N=12 can detect 20-30% differences with 80-85% power, which is adequate for initial screening.

---

## DATA-DRIVEN RECOMMENDATIONS

### Option A: Continue Improving Unit Test Accuracy (Fix Test 1)

#### Expected Gain
- **IF successful:** Improve overall accuracy from 86.1% → 91.7% (+5.6%)
- Prevent ~10 false negatives per 30 runs
- Better BFS baseline detection (fewer false rejections)
- More confident deployment decisions

#### Cost
- **Engineering time:** 2-4 hours
  - Analyze why Test 1 (bfs_run2) is being rejected
  - Investigate critical errors found: vertical line assumptions, coverage claims
  - Adjust verifier prompts/constraints
  - Re-run validation (30 iterations × 6 tests)
- **Compute cost:** $80-120 (30 iterations × $3-4 each)
- **Wall-clock time:** 30-36 hours (can run overnight)

#### Risk
- **HIGH:** May not find root cause
  - Proof might actually have subtle logical errors
  - Verifier might be correctly identifying issues
  - Test 1's isolated failure pattern suggests deep issue
- **MEDIUM:** Changes might affect other tests
  - Currently 90%+ accurate tests could regress
  - Requires full re-validation
- **LOW:** Validation might reveal new failure modes

#### Confidence
**40-60% (LOW-MEDIUM)** that we can improve Test 1
- **Why low:** Test 1 failures are systematic and isolated
- Test 1 consistently finds "critical errors" in the proof
- Independent of other tests → suggests verifier is working as designed
- May require changing ground truth, not verifier

---

### Option B: Run BFS Baseline Tests (Problem 1, N=12)

#### Expected Gain
- **Clean baseline data** for BFS performance without RLAC
- **Enables comparison:** Does RLAC actually improve success rate?
- **Validates framework:** P0 ablation scripts work correctly
- **Informs strategy:**
  - If BFS > 60% → P0 features may not be needed, skip Test 1 fixes
  - If BFS 20-60% → Need better verification (fix Test 1)
  - If BFS < 20% → Focus on P0 features, Test 1 less critical

#### Cost
- **Compute cost:** $36 (12 runs × $3 each)
- **Wall-clock time:** 12-18 hours (can run overnight)
- **Engineering time:** 30 minutes (script already exists: `run_bfs_baseline.sh`)

#### Statistical Power (N=12)
| Comparison | Power | Interpretation |
|------------|-------|----------------|
| 10% vs 40% | 90% | EXCELLENT |
| 20% vs 50% | 85% | GOOD |
| 30% vs 60% | 80% | ADEQUATE |
| 40% vs 50% | 35% | INADEQUATE |

**Adequate for:** Detecting whether BFS is "good enough" (>50%) vs "needs help" (<30%)

#### Risk
- **LOW:** Worst case is inconclusive results (40-60% range)
- **LOW:** No changes to production code
- **MEDIUM:** If results in 40-60% range, need more samples (N=30)

#### Confidence
**80-90% (HIGH)** that it provides useful data
- **Why high:** Either way, we learn about baseline performance
- Required for any deployment decision
- Independent of Test 1 accuracy issues

---

### Option C: Run BFS Baseline Tests (Problem 2, N=12)

#### Expected Gain
- Same as Option B, but for a different problem
- **Cross-validation** of approach across problem types
- Tests generalizability of P0 features
- If results differ from Problem 1 → suggests problem-specific tuning needed

#### Cost
- **IDENTICAL to Option B:** $36, 12-18 hours, 30 min engineering

#### Strategic Value
- **LOWER** than Option B initially (need Problem 1 baseline first)
- **HIGHER** after we have Problem 1 baseline (enables comparison)
- **Best as follow-up** to Option B

#### Risk
- **SAME as Option B**

#### Confidence
**80-90% (HIGH)** for providing useful data
- **Best timing:** After Option B completes

---

## FINAL RECOMMENDATION

### **Option B: Run BFS Baseline Tests (Problem 1, N=12)**

#### Rationale (Data-Driven)

1. **Test 1 improvement has low confidence (40-60%)**
   - Systematic isolated failures suggest deep issue
   - May require changing ground truth, not verifier
   - High cost ($80-120, 30-36 hours) for uncertain gain

2. **BFS baseline data is REQUIRED regardless of Test 1**
   - Need baseline for any deployment decision
   - Informs whether Test 1 accuracy matters
   - Independent of verification quality

3. **BFS test has high confidence (80-90%) for useful data**
   - Low cost ($36, 12-18 hours)
   - Low risk (no code changes)
   - Clear decision criteria

4. **Statistical power is adequate for screening**
   - N=12 detects 20-30% differences with 80-85% power
   - Sufficient to distinguish "good enough" from "needs help"
   - Can follow up with N=30 if results in 40-60% range

#### Decision Criteria After BFS Baseline

```
IF BFS success rate > 60%:
  → SKIP Test 1 fixes (not deployment-critical)
  → Move to production testing
  → Test 1's 56.7% accuracy is acceptable for screening

IF BFS success rate 20-60%:
  → Investigate Test 1 (need better verification)
  → Run Option C (Problem 2 baseline)
  → Consider N=30 for both problems

IF BFS success rate < 20%:
  → Test 1 accuracy matters less (BFS clearly needs help)
  → Focus on P0 feature validation
  → Full P0 ablation testing (N=30)
```

### Confidence Level: **HIGH (85%)**

**Why high confidence:**
- BFS baseline is required for deployment regardless of Test 1
- Low cost and risk compared to Test 1 fixes
- Results directly inform next steps
- Statistical power adequate for decision-making
- Existing script ready to use (`run_bfs_baseline.sh`)

---

## Implementation Plan

### Immediate Action (Next 24 Hours)
```bash
# Run BFS baseline test for Problem 1
./run_bfs_baseline.sh problems/imo01.txt bfs_baseline_p1_results

# Monitor progress (in separate terminal)
watch -n 5 'ls -lh bfs_baseline_p1_results/*.log | tail -12'

# Check success rate after completion
grep -l 'Correct solution found (first success)' bfs_baseline_p1_results/*.log | wc -l
```

### Day 2: Analyze BFS Results
```bash
# Extract success rate
python analyze_bfs_baseline.py bfs_baseline_p1_results

# Compare to Test 1 failures
# If BFS > 60%: Test 1's 56.7% is acceptable
# If BFS < 60%: Test 1 needs investigation
```

### Day 3-4: Based on BFS Results
- **If BFS > 60%:** Move to production testing
- **If BFS 20-60%:** Investigate Test 1, run Problem 2 baseline
- **If BFS < 20%:** Focus on P0 feature validation

### Day 5-6: Full P0 Ablation Testing (if needed)
```bash
# Run N=30 for final validation
./test_p0_ablation.sh problems/imo01.txt 30
```

### Day 7: Final Deployment Decision

---

## Appendix: Detailed Test 1 Failure Analysis

### Test 1 Description
- **Test name:** "Complete Proof (bfs_run2 - Real Success)"
- **Expected:** PASS
- **Actual:** FAIL in 13/30 iterations (56.7%)

### Common Failure Reasons (from iteration 3 analysis)
1. **Critical Error (Severity 9/10):** Incorrect assertion that non-sunny line must be vertical
   - "The claim that the non-sunny line covering the remaining point in column x=n-2 must be vertical is false; a horizontal or slope -1 line could also cover that point."
   
2. **Critical Error (Severity 8/10):** Unjustified assumption about vertical lines
   - "The argument assumes that any column with more than k points must be covered by a vertical line, which is not justified; horizontal or slope -1 non-sunny lines could also cover points."

### Implications
- Test 1 may be **correctly identifying real logical gaps** in the proof
- Fixing this may require:
  - Changing the ground truth proof (bfs_run2)
  - OR relaxing verifier constraints (but this could introduce false positives)
- **Alternative interpretation:** Test 1's stricter standards might be unnecessary for BFS baseline testing

---

## Appendix: Statistical Methods

### Tests Used
1. **Chi-square test:** Overall difference between Test 1 and others
2. **Fisher's exact test:** Pairwise comparison (Test 1 vs Test 2)
3. **Binomial test:** Test 1 vs expected 90% baseline
4. **Wilson score interval:** 95% confidence intervals for proportions
5. **Phi coefficient:** Correlation for binary variables

### Power Analysis Formula
```
n = [(z_α × √(2p̄(1-p̄)) + z_β × √(p₁(1-p₁) + p₂(1-p₂))) / (p₁ - p₂)]²

Where:
  z_α = 1.96 (two-tailed, α=0.05)
  z_β = 0.84 (power=0.80)
  p̄ = (p₁ + p₂) / 2 (pooled proportion)
```

### Confidence Interval (Wilson Score)
```
CI = (p̂ + z²/2n ± z√(p̂(1-p̂)/n + z²/4n²)) / (1 + z²/n)

Where:
  p̂ = observed proportion
  z = 1.96 (95% confidence)
  n = sample size
```

---

**Report Generated:** 2025-12-28  
**Analyst:** Claude (Senior Netflix Data Scientist persona)  
**Next Review:** After BFS baseline results (24-48 hours)
