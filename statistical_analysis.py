#!/usr/bin/env python3
"""
Statistical Analysis: Option A vs Baseline
Netflix Data Science Rigor - A/B Test Evaluation
"""

import numpy as np
from scipy import stats
from scipy.stats import binom, norm, beta
import json

# ============================================================================
# DATA
# ============================================================================

# Baseline (Option 1 original, n=30 iterations x 6 tests = 180 total tests)
baseline_total = 180
baseline_successes = 154
baseline_p = baseline_successes / baseline_total  # 0.8556

# Per-test baseline rates
baseline_per_test = {
    1: (17, 30),  # 56.7%
    2: (28, 30),  # 93.3%
    3: (29, 30),  # 96.7%
    4: (26, 30),  # 86.7%
    5: (30, 30),  # 100%
    6: (24, 30),  # 80.0%
}

# Option A (n=6, one test per type)
option_a_total = 6
option_a_successes = 4
option_a_p = option_a_successes / option_a_total  # 0.6667

# Per-test Option A results
option_a_per_test = {
    1: (0, 1),  # 0% - FAILED (expected PASS)
    2: (1, 1),  # 100% - PASSED
    3: (1, 1),  # 100% - correctly detected failure
    4: (1, 1),  # 100% - correctly detected failure
    5: (1, 1),  # 100% - correctly detected failure
    6: (0, 1),  # 0% - FAILED (expected PASS)
}

print("=" * 80)
print("STATISTICAL ANALYSIS: OPTION A vs BASELINE")
print("Netflix Data Science Rigor - A/B Test Evaluation")
print("=" * 80)
print()

# ============================================================================
# 1. OVERALL STATISTICAL SIGNIFICANCE
# ============================================================================

print("1. OVERALL STATISTICAL SIGNIFICANCE")
print("-" * 80)

print(f"\nBaseline: {baseline_successes}/{baseline_total} = {baseline_p:.4f} (85.6%)")
print(f"Option A: {option_a_successes}/{option_a_total} = {option_a_p:.4f} (66.7%)")
print(f"Difference: {option_a_p - baseline_p:.4f} ({(option_a_p - baseline_p)*100:.1f} percentage points)")

# Two-proportion z-test
# H0: p_A = p_baseline (no difference)
# H1: p_A < p_baseline (regression)

# Pooled proportion for z-test
pooled_p = (baseline_successes + option_a_successes) / (baseline_total + option_a_total)
se_pooled = np.sqrt(pooled_p * (1 - pooled_p) * (1/baseline_total + 1/option_a_total))
z_score = (option_a_p - baseline_p) / se_pooled
p_value = stats.norm.cdf(z_score)  # One-tailed test (left tail)

print(f"\n[Two-Proportion Z-Test]")
print(f"  H0: p_A = p_baseline = {baseline_p:.4f}")
print(f"  H1: p_A < p_baseline (regression)")
print(f"  Pooled p: {pooled_p:.4f}")
print(f"  Z-score: {z_score:.4f}")
print(f"  p-value (one-tailed): {p_value:.4f}")

if p_value < 0.05:
    print(f"  ✗ REJECT H0 at α=0.05 (statistically significant regression)")
else:
    print(f"  ✓ FAIL TO REJECT H0 at α=0.05 (not statistically significant)")

# Exact binomial test (more appropriate for small n)
# Given baseline p=0.856, what's P(4 or fewer successes in 6 trials)?
binomial_p_value = binom.cdf(option_a_successes, option_a_total, baseline_p)

print(f"\n[Exact Binomial Test - More Appropriate for n=6]")
print(f"  Given baseline p={baseline_p:.4f}, what's P(X ≤ {option_a_successes} | n={option_a_total})?")
print(f"  p-value: {binomial_p_value:.4f}")

if binomial_p_value < 0.05:
    print(f"  ✗ REJECT H0 at α=0.05 (statistically significant regression)")
else:
    print(f"  ✓ FAIL TO REJECT H0 at α=0.05 (not statistically significant)")

print(f"\n[Interpretation]")
if binomial_p_value < 0.05:
    print(f"  The observed 66.7% (4/6) is statistically significantly worse than the")
    print(f"  baseline 85.6% at the 5% significance level. This is unlikely to be")
    print(f"  due to random chance alone.")
else:
    print(f"  The observed 66.7% (4/6) is NOT statistically significantly different")
    print(f"  from baseline 85.6% at the 5% level. With n=6, there's insufficient")
    print(f"  evidence to conclude Option A is worse. This could be bad luck.")

# ============================================================================
# 2. CONFIDENCE INTERVALS & SAMPLE SIZE
# ============================================================================

print("\n\n2. CONFIDENCE INTERVALS & SAMPLE SIZE ANALYSIS")
print("-" * 80)

# Wilson score interval (better for small n and proportions near 0 or 1)
def wilson_ci(successes, n, confidence=0.95):
    """Wilson score confidence interval"""
    z = stats.norm.ppf((1 + confidence) / 2)
    p_hat = successes / n
    denominator = 1 + z**2 / n
    center = (p_hat + z**2 / (2*n)) / denominator
    margin = z * np.sqrt((p_hat * (1 - p_hat) / n + z**2 / (4*n**2))) / denominator
    return center - margin, center + margin

# Baseline CI
baseline_ci_lower, baseline_ci_upper = wilson_ci(baseline_successes, baseline_total)
print(f"\nBaseline 95% CI (n={baseline_total}):")
print(f"  {baseline_p:.4f} [{baseline_ci_lower:.4f}, {baseline_ci_upper:.4f}]")
print(f"  Width: {baseline_ci_upper - baseline_ci_lower:.4f}")

# Option A CI
option_a_ci_lower, option_a_ci_upper = wilson_ci(option_a_successes, option_a_total)
print(f"\nOption A 95% CI (n={option_a_total}):")
print(f"  {option_a_p:.4f} [{option_a_ci_lower:.4f}, {option_a_ci_upper:.4f}]")
print(f"  Width: {option_a_ci_upper - option_a_ci_lower:.4f}")

print(f"\n[Key Insight]")
print(f"  The Option A CI [{option_a_ci_lower:.3f}, {option_a_ci_upper:.3f}] is VERY WIDE")
print(f"  due to n=6. The true accuracy could be anywhere from {option_a_ci_lower*100:.1f}% to {option_a_ci_upper*100:.1f}%.")
print(f"  The baseline point estimate ({baseline_p:.3f}) FALLS WITHIN the Option A CI,")
print(f"  which is why we can't conclusively say Option A is worse.")

# Sample size calculation
# How many samples needed to detect difference with 80% power at α=0.05?
def sample_size_two_proportions(p1, p2, alpha=0.05, power=0.80):
    """Sample size for two-proportion test"""
    z_alpha = stats.norm.ppf(1 - alpha)
    z_beta = stats.norm.ppf(power)
    p_bar = (p1 + p2) / 2
    n = ((z_alpha * np.sqrt(2 * p_bar * (1 - p_bar)) +
          z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2)))**2) / ((p1 - p2)**2)
    return int(np.ceil(n))

# If true difference is 85.6% vs 66.7%
n_needed = sample_size_two_proportions(baseline_p, option_a_p)
print(f"\n[Sample Size Calculation]")
print(f"  To detect difference between {baseline_p:.3f} and {option_a_p:.3f}")
print(f"  with 80% power at α=0.05 (two-tailed):")
print(f"  n = {n_needed} per group")
print(f"  Total tests needed: {n_needed * 2}")

# For more conservative estimate (detect 10 percentage point difference)
conservative_p = baseline_p - 0.10
n_needed_conservative = sample_size_two_proportions(baseline_p, conservative_p)
print(f"\n  To detect 10pp difference ({baseline_p:.3f} vs {conservative_p:.3f}):")
print(f"  n = {n_needed_conservative} per group")

# ============================================================================
# 3. TEST-SPECIFIC ANALYSIS
# ============================================================================

print("\n\n3. TEST-SPECIFIC ANALYSIS")
print("-" * 80)

print("\n[Critical Failures: Tests 1 and 6]")
print()

for test_num in [1, 6]:
    baseline_succ, baseline_n = baseline_per_test[test_num]
    option_a_succ, option_a_n = option_a_per_test[test_num]
    baseline_test_p = baseline_succ / baseline_n

    print(f"Test {test_num}:")
    print(f"  Baseline: {baseline_succ}/{baseline_n} = {baseline_test_p:.3f} ({baseline_test_p*100:.1f}%)")
    print(f"  Option A: {option_a_succ}/{option_a_n} = {option_a_succ/option_a_n:.3f} ({option_a_succ/option_a_n*100:.1f}%)")

    # Probability of 0/1 given baseline rate
    p_zero_of_one = binom.pmf(0, 1, baseline_test_p)
    p_zero_or_worse = binom.cdf(0, 1, baseline_test_p)

    print(f"  P(0/1 | p={baseline_test_p:.3f}) = {p_zero_of_one:.4f} ({p_zero_of_one*100:.2f}%)")
    print(f"  P(≤0/1 | p={baseline_test_p:.3f}) = {p_zero_or_worse:.4f} ({p_zero_or_worse*100:.2f}%)")

    if test_num == 1:
        print(f"  → {p_zero_of_one*100:.1f}% chance of seeing 0/1 by random chance")
        print(f"  → NOT surprising given baseline was already only 56.7%")
    else:  # test_num == 6
        print(f"  → {p_zero_of_one*100:.1f}% chance of seeing 0/1 by random chance")
        print(f"  → Moderately surprising, but not impossible")
    print()

# Joint probability
p_both_failures = (1 - baseline_per_test[1][0]/baseline_per_test[1][1]) * \
                  (1 - baseline_per_test[6][0]/baseline_per_test[6][1])
print(f"[Joint Probability]")
print(f"  P(Test 1 fails AND Test 6 fails | baseline rates)")
print(f"  = P(Test 1 fails) × P(Test 6 fails)")
print(f"  = {(1-baseline_per_test[1][0]/baseline_per_test[1][1]):.4f} × {(1-baseline_per_test[6][0]/baseline_per_test[6][1]):.4f}")
print(f"  = {p_both_failures:.4f} ({p_both_failures*100:.2f}%)")
print(f"  → {p_both_failures*100:.1f}% chance of BOTH failing in a single run")
print(f"  → This is reasonably likely! About 1 in {int(1/p_both_failures)} runs")

# ============================================================================
# 4. BAYESIAN ANALYSIS (Posterior Belief Update)
# ============================================================================

print("\n\n4. BAYESIAN POSTERIOR ANALYSIS")
print("-" * 80)

# Prior: Use baseline as Beta(α, β) with mean = baseline_p
# Choose α, β such that mean = baseline_p and reasonable variance
# Using method of moments from baseline data
alpha_prior = baseline_successes + 1
beta_prior = baseline_total - baseline_successes + 1

# Posterior after observing Option A data
alpha_post = alpha_prior + option_a_successes
beta_post = beta_prior + (option_a_total - option_a_successes)

# Posterior statistics
post_mean = alpha_post / (alpha_post + beta_post)
post_mode = (alpha_post - 1) / (alpha_post + beta_post - 2) if alpha_post > 1 and beta_post > 1 else None
post_ci = beta.ppf([0.025, 0.975], alpha_post, beta_post)

print(f"\n[Prior Distribution] Beta({alpha_prior}, {beta_prior})")
print(f"  Based on baseline data: {baseline_successes}/{baseline_total}")
print(f"  Prior mean: {alpha_prior/(alpha_prior + beta_prior):.4f}")

print(f"\n[Likelihood] Observed {option_a_successes}/{option_a_total} in Option A")

print(f"\n[Posterior Distribution] Beta({alpha_post}, {beta_post})")
print(f"  Posterior mean: {post_mean:.4f} ({post_mean*100:.1f}%)")
if post_mode:
    print(f"  Posterior mode: {post_mode:.4f} ({post_mode*100:.1f}%)")
print(f"  Posterior 95% CI: [{post_ci[0]:.4f}, {post_ci[1]:.4f}]")

# Probability that Option A is worse than baseline
p_worse = beta.cdf(baseline_p, alpha_post, beta_post)
print(f"\n[Probability of Regression]")
print(f"  P(p_A < {baseline_p:.4f} | data) = {p_worse:.4f} ({p_worse*100:.1f}%)")

if p_worse > 0.95:
    print(f"  ✗ VERY LIKELY Option A is worse ({p_worse*100:.0f}% confident)")
elif p_worse > 0.80:
    print(f"  ⚠ LIKELY Option A is worse ({p_worse*100:.0f}% confident)")
elif p_worse > 0.50:
    print(f"  ? MODERATELY LIKELY Option A is worse ({p_worse*100:.0f}% confident)")
else:
    print(f"  ✓ NOT LIKELY Option A is worse ({p_worse*100:.0f}% confident)")

# ============================================================================
# 5. DECISION RECOMMENDATION
# ============================================================================

print("\n\n5. DECISION RECOMMENDATION")
print("=" * 80)

print("\n[Expected Value Analysis]")
print()

# Decision tree
print("Option A: Run full n=30 validation")
print(f"  Cost: ~{30 * 188 / 60:.0f} minutes (30 runs × 3.1 min/run)")
print(f"  Outcome if truly worse (p={p_worse:.2f}):")
print(f"    - Confirm regression, avoid deployment")
print(f"    - Value: High (prevent bad deployment)")
print(f"  Outcome if not worse (p={1-p_worse:.2f}):")
print(f"    - Learn Option A is actually good")
print(f"    - Value: High (gain confidence in deployment)")
print(f"  Expected value: HIGH (informative either way)")
print()

print("Option B: Revert immediately")
print(f"  Cost: 0 minutes")
print(f"  Risk: If Option A is actually good ({(1-p_worse)*100:.0f}% chance),")
print(f"        we miss out on potential improvement")
print(f"  Value: LOW (no new information)")
print()

print("Option C: Fix obvious issues, then retest n=30")
print(f"  Cost: Development time + {30 * 188 / 60:.0f} minutes validation")
print(f"  Value: HIGHEST if fixes address root cause")
print(f"  Requires: Understanding WHY Test 1 and 6 failed")
print()

print("[RECOMMENDATION]")
print("=" * 80)
print()
print("🎯 PRIMARY RECOMMENDATION: Option C (Fix then validate)")
print()
print("RATIONALE:")
print("  1. Statistical Evidence:")
print(f"     - p-value = {binomial_p_value:.3f} (NOT significant at α=0.05)")
print(f"     - Bayesian P(regression) = {p_worse:.2f} (moderate, not definitive)")
print(f"     - 95% CI [{option_a_ci_lower:.3f}, {option_a_ci_upper:.3f}] includes baseline")
print()
print("  2. Root Cause Analysis:")
print("     - Test 1 failed (0/1) but baseline was already weak (56.7%)")
print("     - Test 6 failed (0/1) with ~20% chance by random variation")
print("     - Both failures together: 8.6% probability (plausible)")
print()
print("  3. Economic Decision:")
print("     - Running n=30 will cost ~90 minutes")
print("     - High information value regardless of outcome")
print("     - BUT: If we can identify WHY tests failed, fix first")
print()
print("CONCRETE ACTION PLAN:")
print("  Step 1: Investigate Test 1 and Test 6 failure modes")
print("         - Review bug reports from failed tests")
print("         - Identify if text constraint caused specific issues")
print()
print("  Step 2: If root cause found → Fix → Retest n=30")
print("         If no root cause → Run n=30 as-is to gather data")
print()
print("  Step 3: After n=30, decision rule:")
print("         - If accuracy ≥ 80%: Deploy Option A")
print("         - If accuracy < 75%: Revert to baseline")
print("         - If 75-80%: Borderline, need deeper analysis")
print()

# ============================================================================
# 6. HYPOTHESIS TESTING SUMMARY
# ============================================================================

print("\n\n6. HYPOTHESIS TESTING SUMMARY")
print("=" * 80)

print(f"\nH0: Option A accuracy = {baseline_p:.3f} (no change from baseline)")
print(f"H1: Option A accuracy < {baseline_p:.3f} (regression)")
print()
print(f"Observed: {option_a_successes}/{option_a_total} = {option_a_p:.3f}")
print()
print(f"P(X ≤ {option_a_successes} | n={option_a_total}, p={baseline_p:.3f}) = {binomial_p_value:.4f}")
print()

if binomial_p_value < 0.05:
    print(f"✗ REJECT H0 (p={binomial_p_value:.4f} < 0.05)")
    print(f"  Conclusion: Statistically significant regression")
else:
    print(f"✓ FAIL TO REJECT H0 (p={binomial_p_value:.4f} ≥ 0.05)")
    print(f"  Conclusion: Insufficient evidence to claim regression")
    print(f"  Interpretation: Could be bad luck OR small effect OR no effect")

print()
print("=" * 80)
print("FINAL VERDICT: INSUFFICIENT DATA - INVESTIGATE & RETEST")
print("=" * 80)

# Save results to JSON
results = {
    "baseline": {
        "n": baseline_total,
        "successes": baseline_successes,
        "accuracy": baseline_p,
        "ci_95": {"lower": baseline_ci_lower, "upper": baseline_ci_upper}
    },
    "option_a": {
        "n": option_a_total,
        "successes": option_a_successes,
        "accuracy": option_a_p,
        "ci_95": {"lower": option_a_ci_lower, "upper": option_a_ci_upper}
    },
    "statistical_tests": {
        "z_test": {"z_score": float(z_score), "p_value": float(p_value)},
        "binomial_test": {"p_value": float(binomial_p_value)},
        "significant_at_0.05": bool(binomial_p_value < 0.05)
    },
    "bayesian": {
        "posterior_mean": post_mean,
        "posterior_ci_95": {"lower": post_ci[0], "upper": post_ci[1]},
        "p_regression": p_worse
    },
    "sample_size": {
        "detect_current_diff": n_needed,
        "detect_10pp_diff": n_needed_conservative
    },
    "recommendation": "Fix issues if identifiable, then run n=30 validation",
    "verdict": "INSUFFICIENT_DATA"
}

with open('/home/user/IMO25/statistical_analysis_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n✓ Results saved to: /home/user/IMO25/statistical_analysis_results.json")
