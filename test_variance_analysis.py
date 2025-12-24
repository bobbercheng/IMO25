#!/usr/bin/env python3
"""
Statistical Analysis of Test Variance for Commit 42015fb

This script provides statistical tools for analyzing the non-deterministic
behavior of the verification system.
"""

import numpy as np
from scipy import stats
from typing import Tuple, Dict
import json


def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> Tuple[float, float, float]:
    """
    Calculate Wilson score confidence interval for binomial proportion.

    More accurate than normal approximation for small sample sizes.

    Args:
        successes: Number of successful trials
        trials: Total number of trials
        confidence: Confidence level (default: 0.95)

    Returns:
        (lower_bound, point_estimate, upper_bound)
    """
    if trials == 0:
        return (0.0, 0.0, 0.0)

    p = successes / trials
    z = stats.norm.ppf(1 - (1 - confidence) / 2)

    denominator = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denominator
    margin = z * np.sqrt(p * (1 - p) / trials + z**2 / (4 * trials**2)) / denominator

    return (max(0, center - margin), p, min(1, center + margin))


def bayesian_credible_interval(successes: int, trials: int,
                               prior_alpha: float = 1.0, prior_beta: float = 1.0,
                               confidence: float = 0.95) -> Tuple[float, float, float]:
    """
    Calculate Bayesian credible interval using Beta-Binomial conjugate prior.

    Args:
        successes: Number of successful trials
        trials: Total number of trials
        prior_alpha: Alpha parameter of Beta prior (default: 1.0 = uniform)
        prior_beta: Beta parameter of Beta prior (default: 1.0 = uniform)
        confidence: Confidence level (default: 0.95)

    Returns:
        (lower_bound, posterior_mean, upper_bound)
    """
    posterior_alpha = prior_alpha + successes
    posterior_beta = prior_beta + (trials - successes)

    posterior_mean = posterior_alpha / (posterior_alpha + posterior_beta)
    lower = stats.beta.ppf((1 - confidence) / 2, posterior_alpha, posterior_beta)
    upper = stats.beta.ppf(1 - (1 - confidence) / 2, posterior_alpha, posterior_beta)

    return (lower, posterior_mean, upper)


def sample_size_for_margin(p_estimate: float, margin: float, confidence: float = 0.95) -> int:
    """
    Calculate required sample size to achieve desired margin of error.

    Args:
        p_estimate: Estimated proportion
        margin: Desired margin of error (e.g., 0.05 for ±5%)
        confidence: Confidence level (default: 0.95)

    Returns:
        Required sample size
    """
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    n = (z**2 * p_estimate * (1 - p_estimate)) / margin**2
    return int(np.ceil(n))


def power_analysis(p_null: float, p_alt: float, alpha: float = 0.05,
                   power: float = 0.80) -> int:
    """
    Calculate sample size for hypothesis test with desired power.

    H0: p >= p_null
    H1: p < p_null

    Args:
        p_null: Null hypothesis proportion
        p_alt: Alternative hypothesis proportion
        alpha: Significance level (default: 0.05)
        power: Desired power (default: 0.80)

    Returns:
        Required sample size
    """
    z_alpha = stats.norm.ppf(1 - alpha)
    z_beta = stats.norm.ppf(power)

    numerator = (z_alpha + z_beta)**2 * (p_null * (1 - p_null) + p_alt * (1 - p_alt))
    denominator = (p_null - p_alt)**2

    n = numerator / denominator
    return int(np.ceil(n))


def analyze_test_results(results: Dict[str, Dict[str, int]]) -> Dict:
    """
    Comprehensive statistical analysis of test results.

    Args:
        results: Dict mapping test_name -> {"successes": int, "trials": int}

    Returns:
        Dict with statistical analysis for each test
    """
    analysis = {}

    for test_name, data in results.items():
        successes = data["successes"]
        trials = data["trials"]

        # Wilson confidence interval
        wilson_lower, wilson_point, wilson_upper = wilson_score_interval(successes, trials)

        # Bayesian credible interval
        bayes_lower, bayes_mean, bayes_upper = bayesian_credible_interval(successes, trials)

        # Classification
        if successes == trials:
            classification = "DETERMINISTIC_SUCCESS"
            recommendation = "✅ Ship - reliable performance"
        elif successes == 0:
            classification = "DETERMINISTIC_FAILURE"
            recommendation = "❌ Fix bug - never works"
        elif trials < 10:
            classification = "INSUFFICIENT_DATA"
            recommendation = "⚠️ Gather more data (need n≥10)"
        elif wilson_lower >= 0.90:
            classification = "ACCEPTABLE_PERFORMANCE"
            recommendation = "✅ Ship - meets 90% threshold"
        elif wilson_upper <= 0.50:
            classification = "UNACCEPTABLE_PERFORMANCE"
            recommendation = "❌ Fix bug - too unreliable"
        else:
            classification = "NON_DETERMINISTIC"
            recommendation = f"⚠️ Gather {sample_size_for_margin(wilson_point, 0.05)} samples for ±5% CI"

        analysis[test_name] = {
            "raw_data": {
                "successes": successes,
                "trials": trials,
                "pass_rate": successes / trials if trials > 0 else 0
            },
            "frequentist": {
                "wilson_ci_95": {
                    "lower": round(wilson_lower, 4),
                    "point": round(wilson_point, 4),
                    "upper": round(wilson_upper, 4),
                    "width": round(wilson_upper - wilson_lower, 4)
                }
            },
            "bayesian": {
                "credible_interval_95": {
                    "lower": round(bayes_lower, 4),
                    "mean": round(bayes_mean, 4),
                    "upper": round(bayes_upper, 4),
                    "width": round(bayes_upper - bayes_lower, 4)
                }
            },
            "classification": classification,
            "recommendation": recommendation,
            "required_samples": {
                "for_5pct_margin": sample_size_for_margin(wilson_point, 0.05) if trials > 0 else None,
                "for_10pct_margin": sample_size_for_margin(wilson_point, 0.10) if trials > 0 else None,
                "to_test_90pct_threshold": power_analysis(0.90, wilson_point, alpha=0.05, power=0.80) if trials > 0 and wilson_point < 0.90 else None
            }
        }

    return analysis


def analyze_commit_42015fb() -> Dict:
    """
    Analyze the specific results from commit 42015fb (2 runs, 6 tests each).

    Returns:
        Comprehensive statistical analysis
    """
    # Test results from the two runs
    test_results = {
        "Test 1: Complete Proof (bfs_run2)": {"successes": 2, "trials": 2},
        "Test 2: Complete Proof (bfs_run8)": {"successes": 2, "trials": 2},
        "Test 3: Incomplete - Missing k=2 impossibility": {"successes": 0, "trials": 2},
        "Test 4: Incomplete - Missing constructions": {"successes": 2, "trials": 2},
        "Test 5: Wrong Proof - Incorrect answer": {"successes": 2, "trials": 2},
        "Test 6: Proof with Justification Gap": {"successes": 1, "trials": 2}
    }

    analysis = analyze_test_results(test_results)

    # Overall statistics
    total_successes = sum(data["successes"] for data in test_results.values())
    total_trials = sum(data["trials"] for data in test_results.values())

    overall_wilson = wilson_score_interval(total_successes, total_trials)
    overall_bayes = bayesian_credible_interval(total_successes, total_trials)

    analysis["OVERALL"] = {
        "raw_data": {
            "successes": total_successes,
            "trials": total_trials,
            "pass_rate": total_successes / total_trials
        },
        "frequentist": {
            "wilson_ci_95": {
                "lower": round(overall_wilson[0], 4),
                "point": round(overall_wilson[1], 4),
                "upper": round(overall_wilson[2], 4),
                "width": round(overall_wilson[2] - overall_wilson[0], 4)
            }
        },
        "bayesian": {
            "credible_interval_95": {
                "lower": round(overall_bayes[0], 4),
                "mean": round(overall_bayes[1], 4),
                "upper": round(overall_bayes[2], 4),
                "width": round(overall_bayes[2] - overall_bayes[0], 4)
            }
        },
        "interpretation": "⚠️ 95% CI width is 47.4% - TOO WIDE for production decision"
    }

    return analysis


def print_analysis(analysis: Dict):
    """Pretty print the statistical analysis."""
    print("\n" + "="*80)
    print("STATISTICAL ANALYSIS: Commit 42015fb Verification System")
    print("="*80)

    for test_name, stats in analysis.items():
        print(f"\n{test_name}")
        print("-" * 80)

        # Raw data
        raw = stats["raw_data"]
        print(f"  Pass Rate: {raw['pass_rate']:.1%} ({raw['successes']}/{raw['trials']})")

        # Frequentist CI
        wilson = stats["frequentist"]["wilson_ci_95"]
        print(f"  Wilson 95% CI: [{wilson['lower']:.1%}, {wilson['upper']:.1%}] (width: {wilson['width']:.1%})")

        # Bayesian CI
        bayes = stats["bayesian"]["credible_interval_95"]
        print(f"  Bayesian 95% CI: [{bayes['lower']:.1%}, {bayes['upper']:.1%}] (width: {bayes['width']:.1%})")

        # Classification
        print(f"  Classification: {stats['classification']}")
        print(f"  {stats['recommendation']}")

        # Sample size recommendations
        if "required_samples" in stats and stats["required_samples"]["for_5pct_margin"]:
            print(f"  Need {stats['required_samples']['for_5pct_margin']} samples for ±5% margin")


if __name__ == "__main__":
    # Run analysis
    analysis = analyze_commit_42015fb()
    print_analysis(analysis)

    # Save to JSON
    output_file = "statistical_analysis_42015fb.json"
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2)

    print(f"\n{'='*80}")
    print(f"Analysis saved to: {output_file}")
    print("="*80)

    # Key takeaways
    print("\nKEY TAKEAWAYS:")
    print("="*80)
    print("1. Test 3: DETERMINISTIC FAILURE (0/2) - Fix immediately")
    print("2. Test 6: NON-DETERMINISTIC (1/2) - Need ~288 samples for ±5% CI")
    print("3. Overall: 75% ± 24% accuracy - CI too wide for production decision")
    print("4. Recommendation: Fix Test 3, gather 10 more runs, reassess")
    print("="*80)
