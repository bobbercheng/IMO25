#!/usr/bin/env python3
"""
Statistical analysis of BFS baseline test results.
Compares 20251220 (old) vs 20251221 (new) runs.
"""

import json
import re
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple
import math

def extract_boxed_answer(text: str) -> str:
    """Extract answer from \boxed{} format."""
    if not text:
        return "NO_ANSWER"

    # Find all \boxed{...} patterns
    matches = re.findall(r'\\boxed\{([^}]+)\}', text)
    if matches:
        return matches[-1].strip()  # Return last boxed answer
    return "NO_ANSWER"

def classify_answer_pattern(answer: str) -> str:
    """Classify answer into pattern categories."""
    if answer == "NO_ANSWER":
        return "NO_ANSWER"

    # Normalize the answer
    norm = answer.lower().strip()

    # Pattern matching for the correct answer: k ∈ {0,1}
    if ("k=0" in norm or "0" in norm) and ("k=1" in norm or "1" in norm) and "2" not in norm:
        if "{0,1}" in norm or "{0, 1}" in norm or "k\\in" in norm:
            return "CORRECT: k∈{0,1}"
        else:
            return "LIKELY_CORRECT: 0 and 1"
    elif "k=0" in norm and "k=1" not in norm and "1" not in norm:
        return "WRONG: k=0 only"
    elif "k=1" in norm and "k=0" not in norm and "0" not in norm:
        return "WRONG: k=1 only"
    else:
        return f"OTHER: {answer[:50]}"

def extract_verdict(verify_text: str) -> str:
    """Extract verification verdict."""
    if not verify_text:
        return "NO_VERIFICATION"

    # Look for verdict patterns
    if "**invalid**" in verify_text.lower():
        return "INVALID"
    elif "**valid**" in verify_text.lower():
        return "VALID"
    elif "critical error" in verify_text.lower():
        return "CRITICAL_ERROR"
    elif "justification gap" in verify_text.lower():
        return "JUSTIFICATION_GAP"
    else:
        return "UNCLEAR"

def analyze_run(json_path: Path) -> Dict:
    """Extract metrics from a single run."""
    with open(json_path, 'r') as f:
        data = json.load(f)

    solution = data.get('solution', '')
    verify = data.get('verify', '')

    answer = extract_boxed_answer(solution)
    pattern = classify_answer_pattern(answer)
    verdict = extract_verdict(verify)

    # Success determination
    is_success = (
        pattern.startswith("CORRECT:") or
        pattern.startswith("LIKELY_CORRECT:")
    ) and verdict not in ["CRITICAL_ERROR", "INVALID"]

    return {
        'run_id': json_path.stem,
        'answer': answer,
        'pattern': pattern,
        'verdict': verdict,
        'success': is_success,
        'iterations': data.get('current_iteration', 0),
        'total_iterations': data.get('total_iterations_across_resumes', 0),
        'resume_count': data.get('resume_count', 0),
        'solution_reasoning': data.get('solution_reasoning', 'unknown'),
        'verification_reasoning': data.get('verification_reasoning', 'unknown'),
    }

def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate Wilson score confidence interval."""
    if total == 0:
        return (0.0, 0.0)

    p = successes / total
    z = 1.96  # 95% confidence

    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) / total + z**2 / (4 * total**2))) / denominator

    return (max(0, center - margin), min(1, center + margin))

def analyze_dataset(json_files: List[Path], dataset_name: str) -> Dict:
    """Analyze a complete dataset."""
    results = [analyze_run(f) for f in sorted(json_files)]

    # Extract metrics
    successes = sum(1 for r in results if r['success'])
    total = len(results)
    success_rate = successes / total if total > 0 else 0

    # Confidence interval
    ci_low, ci_high = wilson_score_interval(successes, total)

    # Pattern distribution
    patterns = Counter(r['pattern'] for r in results)
    verdicts = Counter(r['verdict'] for r in results)

    # Iteration stats
    iterations = [r['total_iterations'] for r in results]
    avg_iterations = sum(iterations) / len(iterations) if iterations else 0

    return {
        'name': dataset_name,
        'total_runs': total,
        'successes': successes,
        'success_rate': success_rate,
        'ci_95': (ci_low, ci_high),
        'patterns': patterns,
        'verdicts': verdicts,
        'avg_iterations': avg_iterations,
        'results': results,
    }

def compare_datasets(old_data: Dict, new_data: Dict):
    """Statistical comparison between old and new datasets."""
    print("\n" + "="*80)
    print("STATISTICAL ANALYSIS: BFS BASELINE TEST RESULTS")
    print("="*80)

    # Section 1: Success Rate Comparison
    print("\n### 1. SUCCESS RATE ANALYSIS")
    print("-" * 80)

    old_rate = old_data['success_rate']
    new_rate = new_data['success_rate']
    old_ci = old_data['ci_95']
    new_ci = new_data['ci_95']

    print(f"\n**Old Baseline (20251220):**")
    print(f"  - N = {old_data['total_runs']}")
    print(f"  - Successes: {old_data['successes']}/{old_data['total_runs']}")
    print(f"  - Success Rate: {old_rate*100:.1f}%")
    print(f"  - 95% CI: [{old_ci[0]*100:.1f}%, {old_ci[1]*100:.1f}%]")

    print(f"\n**New Baseline (20251221):**")
    print(f"  - N = {new_data['total_runs']}")
    print(f"  - Successes: {new_data['successes']}/{new_data['total_runs']}")
    print(f"  - Success Rate: {new_rate*100:.1f}%")
    print(f"  - 95% CI: [{new_ci[0]*100:.1f}%, {new_ci[1]*100:.1f}%]")

    # Absolute and relative improvement
    abs_improvement = (new_rate - old_rate) * 100
    print(f"\n**Improvement:**")
    print(f"  - Absolute: {abs_improvement:+.1f} percentage points")
    if old_rate > 0:
        rel_improvement = ((new_rate - old_rate) / old_rate) * 100
        print(f"  - Relative: {rel_improvement:+.1f}% change")

    # Statistical significance (Fisher's exact test approximation)
    # For small samples, check if CIs overlap
    ci_overlap = not (old_ci[1] < new_ci[0] or new_ci[1] < old_ci[0])
    print(f"\n**Statistical Significance:**")
    print(f"  - 95% CIs overlap: {ci_overlap}")
    if ci_overlap:
        print(f"  - Conclusion: NOT statistically significant (p > 0.05)")
        print(f"  - Interpretation: Cannot reject null hypothesis (no real difference)")
    else:
        print(f"  - Conclusion: Statistically significant (p < 0.05)")
        print(f"  - Interpretation: Strong evidence of real improvement")

    # Section 2: Answer Pattern Distribution
    print("\n\n### 2. ANSWER PATTERN DISTRIBUTION")
    print("-" * 80)

    print("\n**Old Baseline (20251220):**")
    for pattern, count in old_data['patterns'].most_common():
        pct = (count / old_data['total_runs']) * 100
        print(f"  - {pattern}: {count}/{old_data['total_runs']} ({pct:.1f}%)")

    print("\n**New Baseline (20251221):**")
    for pattern, count in new_data['patterns'].most_common():
        pct = (count / new_data['total_runs']) * 100
        print(f"  - {pattern}: {count}/{new_data['total_runs']} ({pct:.1f}%)")

    # Pattern shift analysis
    print("\n**Pattern Shift Analysis:**")
    all_patterns = set(old_data['patterns'].keys()) | set(new_data['patterns'].keys())
    for pattern in sorted(all_patterns):
        old_count = old_data['patterns'].get(pattern, 0)
        new_count = new_data['patterns'].get(pattern, 0)
        delta = new_count - old_count
        if delta != 0:
            print(f"  - {pattern}: {old_count} → {new_count} ({delta:+d})")

    # Section 3: Verification Verdict Distribution
    print("\n\n### 3. VERIFICATION VERDICT DISTRIBUTION")
    print("-" * 80)

    print("\n**Old Baseline (20251220):**")
    for verdict, count in old_data['verdicts'].most_common():
        pct = (count / old_data['total_runs']) * 100
        print(f"  - {verdict}: {count}/{old_data['total_runs']} ({pct:.1f}%)")

    print("\n**New Baseline (20251221):**")
    for verdict, count in new_data['verdicts'].most_common():
        pct = (count / new_data['total_runs']) * 100
        print(f"  - {verdict}: {count}/{new_data['total_runs']} ({pct:.1f}%)")

    # Section 4: Variance Analysis
    print("\n\n### 4. VARIANCE ANALYSIS")
    print("-" * 80)

    # Check if failures are consistent (same wrong answer) or random (different answers)
    old_failures = [r for r in old_data['results'] if not r['success']]
    new_failures = [r for r in new_data['results'] if not r['success']]

    old_failure_patterns = Counter(r['pattern'] for r in old_failures)
    new_failure_patterns = Counter(r['pattern'] for r in new_failures)

    print("\n**Old Baseline Failure Patterns:**")
    if old_failures:
        for pattern, count in old_failure_patterns.most_common():
            pct = (count / len(old_failures)) * 100
            print(f"  - {pattern}: {count}/{len(old_failures)} ({pct:.1f}%)")

        # Calculate entropy (measure of randomness)
        old_entropy = -sum((c/len(old_failures)) * math.log2(c/len(old_failures))
                          for c in old_failure_patterns.values())
        print(f"\n  - Entropy: {old_entropy:.2f} bits")
        print(f"  - Interpretation: {'High variance (random failures)' if old_entropy > 1.5 else 'Low variance (consistent failure)'}")
    else:
        print("  - No failures!")

    print("\n**New Baseline Failure Patterns:**")
    if new_failures:
        for pattern, count in new_failure_patterns.most_common():
            pct = (count / len(new_failures)) * 100
            print(f"  - {pattern}: {count}/{len(new_failures)} ({pct:.1f}%)")

        new_entropy = -sum((c/len(new_failures)) * math.log2(c/len(new_failures))
                          for c in new_failure_patterns.values())
        print(f"\n  - Entropy: {new_entropy:.2f} bits")
        print(f"  - Interpretation: {'High variance (random failures)' if new_entropy > 1.5 else 'Low variance (consistent failure)'}")
    else:
        print("  - No failures!")

    # Section 5: Sample Size Analysis
    print("\n\n### 5. SAMPLE SIZE ADEQUACY")
    print("-" * 80)

    # Calculate required sample size for different target success rates
    target_rates = [0.30, 0.40, 0.50]  # 30%, 40%, 50%
    margin_of_error = 0.15  # ±15%
    confidence = 0.95
    z = 1.96

    print(f"\n**Sample Size Needed for ±{margin_of_error*100:.0f}% margin of error (95% CI):**")
    for target_rate in target_rates:
        # n = (z^2 * p * (1-p)) / E^2
        n_required = math.ceil((z**2 * target_rate * (1 - target_rate)) / (margin_of_error**2))
        print(f"  - Target success rate {target_rate*100:.0f}%: N ≥ {n_required}")

    current_n = new_data['total_runs']
    print(f"\n**Current sample size: N = {current_n}**")

    if new_rate > 0:
        # Calculate margin of error with current sample
        current_margin = z * math.sqrt((new_rate * (1 - new_rate)) / current_n)
        print(f"  - Current margin of error: ±{current_margin*100:.1f}%")
        print(f"  - Current 95% CI: [{new_rate*100:.1f}% ± {current_margin*100:.1f}%]")

        # Recommended additional runs
        optimal_n = math.ceil((z**2 * new_rate * (1 - new_rate)) / (margin_of_error**2))
        additional_runs = max(0, optimal_n - current_n)
        print(f"\n  - Recommended total sample size: N = {optimal_n}")
        print(f"  - Additional runs needed: {additional_runs}")
    else:
        print(f"  - Current success rate is 0% - need more runs to establish baseline")

    # Section 6: Decision Recommendations
    print("\n\n### 6. DATA-DRIVEN RECOMMENDATIONS")
    print("-" * 80)

    print("\n**A. Continue vs Stop Decision:**")
    if new_rate >= 0.30:
        print(f"  ✓ SUCCESS RATE ≥ 30% → CONTINUE testing")
        print(f"    - Current rate ({new_rate*100:.1f}%) meets minimum target")
        print(f"    - Run {additional_runs} more iterations for statistical power")
    elif new_rate > 0:
        print(f"  ⚠ SUCCESS RATE {new_rate*100:.1f}% < 30% → CONDITIONAL CONTINUE")
        print(f"    - Some success observed, but below target")
        print(f"    - Recommendation: Run 6 more trials, then re-evaluate")
        print(f"    - If success rate stays < 20% after 18 total runs → STOP and debug")
    else:
        print(f"  ✗ SUCCESS RATE = 0% → STOP and debug")
        print(f"    - No successful runs in {current_n} attempts")
        print(f"    - Probability of 0/{current_n} by chance if true rate ≥ 30%: {(0.7**current_n)*100:.2f}%")
        print(f"    - Strong evidence of systematic failure")

    print("\n**B. Most Likely Root Cause:**")
    if new_rate == 0:
        # Analyze the specific failure patterns
        if all(r['verdict'] == 'CRITICAL_ERROR' for r in new_failures):
            print(f"  - Systematic error in verification logic")
            print(f"  - All {len(new_failures)} runs produce CRITICAL_ERROR verdict")
            print(f"  - Likely issue: Verification catches legitimate error in solution")
        else:
            print(f"  - Mixed failure modes - verification working but solutions wrong")
    elif new_rate < 0.20:
        print(f"  - High false positive rate in verification")
        print(f"  - Answer patterns look correct but fail verification")
    else:
        print(f"  - Verification working, but stochastic variation expected")

    # Section 7: Detailed Run-by-Run Table
    print("\n\n### 7. RUN-BY-RUN RESULTS (NEW BASELINE)")
    print("-" * 80)
    print(f"\n{'Run':<15} {'Pattern':<30} {'Verdict':<20} {'Success':<8} {'Iters':<6}")
    print("-" * 80)
    for r in new_data['results']:
        run_id = r['run_id'].replace('bfs_run', '').replace('_20251221_111204', '')
        pattern_short = r['pattern'][:29]
        verdict_short = r['verdict'][:19]
        success_mark = "✓" if r['success'] else "✗"
        print(f"{run_id:<15} {pattern_short:<30} {verdict_short:<20} {success_mark:<8} {r['total_iterations']:<6}")

def main():
    base_dir = Path("/home/user/IMO25/bfs_baseline_results")

    # Old baseline (20251220)
    old_json_files = sorted(base_dir.glob("old/bfs_run*_20251220_*.json"))

    # New baseline (20251221)
    new_json_files = sorted(base_dir.glob("bfs_run*_20251221_111204.json"))

    print(f"Found {len(old_json_files)} old baseline files")
    print(f"Found {len(new_json_files)} new baseline files")

    # Analyze both datasets
    old_data = analyze_dataset(old_json_files, "Old Baseline (20251220)")
    new_data = analyze_dataset(new_json_files, "New Baseline (20251221)")

    # Compare and generate report
    compare_datasets(old_data, new_data)

    print("\n" + "="*80)
    print("END OF ANALYSIS")
    print("="*80)

if __name__ == "__main__":
    main()
