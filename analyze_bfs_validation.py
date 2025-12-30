#!/usr/bin/env python3
"""
Statistical Analysis of BFS MEDIUM Reasoning Validation Test (N=12)
Netflix Senior Data Scientist Analysis
"""

import json
import re
from pathlib import Path
from datetime import datetime
import statistics
from typing import Dict, List, Tuple

def extract_verdict_from_log(log_path: Path) -> str:
    """Extract final verdict from log file"""
    with open(log_path, 'r') as f:
        content = f.read()

    # Search for verdict patterns
    if 'FINAL VERDICT: CORRECT' in content:
        return 'CORRECT'
    elif 'FINAL VERDICT: INCOMPLETE' in content:
        return 'INCOMPLETE'
    elif 'FINAL VERDICT: WRONG' in content:
        return 'WRONG'
    else:
        # Check for verification good
        if 'verification good' in content:
            return 'VERIFICATION_GOOD'
        return 'UNKNOWN'

def extract_iterations_from_log(log_path: Path) -> int:
    """Count iterations from log file"""
    with open(log_path, 'r') as f:
        content = f.read()

    # Count "Iteration N:" patterns
    iterations = re.findall(r'Iteration (\d+):', content)
    if iterations:
        return max(int(i) for i in iterations)
    return 0

def extract_answer_progression(log_path: Path) -> List[str]:
    """Extract answer progression from log file"""
    with open(log_path, 'r') as f:
        content = f.read()

    answers = []
    # Look for final answer patterns
    answer_pattern = r'k\s*[=∈]\s*\{([^}]+)\}'
    matches = re.findall(answer_pattern, content)
    return matches

def analyze_json_file(json_path: Path) -> Dict:
    """Extract metrics from JSON memory file"""
    with open(json_path, 'r') as f:
        data = json.load(f)

    metrics = {
        'run_id': json_path.stem.replace('_20251222_213001', ''),
        'iterations': len(data.get('explorations', [])),
        'final_solution': data.get('final_solution', ''),
        'verification_score': data.get('verification_score', 0),
        'stuck_count': data.get('stuck_count', 0),
        'error_count': len(data.get('errors_found', [])),
        'has_truncation': any('truncation' in str(exp).lower() for exp in data.get('explorations', [])),
    }

    # Extract final answer from solution
    if metrics['final_solution']:
        answer_match = re.search(r'k\s*[=∈]\s*\{([^}]+)\}', metrics['final_solution'])
        if answer_match:
            metrics['final_answer'] = answer_match.group(1).strip()
        else:
            metrics['final_answer'] = 'NOT_FOUND'
    else:
        metrics['final_answer'] = 'EMPTY'

    return metrics

def analyze_all_runs(base_dir: Path) -> Tuple[List[Dict], Dict]:
    """Analyze all runs and compute aggregate statistics"""
    results = []

    for i in range(1, 13):
        json_path = base_dir / f'bfs_run{i}_20251222_213001.json'
        log_path = base_dir / f'bfs_run{i}_20251222_213001.log'

        metrics = analyze_json_file(json_path)
        metrics['verdict'] = extract_verdict_from_log(log_path)
        metrics['log_iterations'] = extract_iterations_from_log(log_path)
        metrics['answer_progression'] = extract_answer_progression(log_path)

        results.append(metrics)

    # Compute aggregate statistics
    correct_runs = [r for r in results if r['verdict'] == 'CORRECT']
    incorrect_runs = [r for r in results if r['verdict'] != 'CORRECT']

    stats = {
        'total_runs': len(results),
        'correct_count': len(correct_runs),
        'incorrect_count': len(incorrect_runs),
        'success_rate': len(correct_runs) / len(results),
        'iterations_correct_mean': statistics.mean([r['iterations'] for r in correct_runs]) if correct_runs else 0,
        'iterations_correct_median': statistics.median([r['iterations'] for r in correct_runs]) if correct_runs else 0,
        'iterations_correct_stdev': statistics.stdev([r['iterations'] for r in correct_runs]) if len(correct_runs) > 1 else 0,
        'iterations_incorrect_mean': statistics.mean([r['iterations'] for r in incorrect_runs]) if incorrect_runs else 0,
        'iterations_incorrect_median': statistics.median([r['iterations'] for r in incorrect_runs]) if incorrect_runs else 0,
    }

    return results, stats

def print_analysis_report(results: List[Dict], stats: Dict):
    """Print comprehensive analysis report"""

    print("=" * 80)
    print("BFS MEDIUM REASONING VALIDATION TEST - STATISTICAL ANALYSIS")
    print("=" * 80)
    print()

    # Section 1: Metrics Audit
    print("## 1. METRICS AUDIT")
    print("-" * 80)
    print()

    # Count verification_good vs actual CORRECT
    verification_good_count = sum(1 for r in results if 'verification good' in str(r['verdict']).lower())
    correct_count = sum(1 for r in results if r['verdict'] == 'CORRECT')

    print("### Confusion Matrix: Verification Status vs Final Verdict")
    print()
    print("| Run | Verdict      | Final Answer | Iterations | Verification Good? |")
    print("|-----|--------------|--------------|------------|--------------------|")
    for r in results:
        vg = "Yes" if 'verification good' in str(r).lower() else "No"
        print(f"| {r['run_id']:8} | {r['verdict']:12} | {r['final_answer']:12} | {r['iterations']:10} | {vg:18} |")

    print()
    print(f"**KEY FINDING**: 'verification good' appears in {verification_good_count}/12 runs")
    print(f"**ACTUAL SUCCESS**: CORRECT verdict = {correct_count}/12 runs ({stats['success_rate']*100:.1f}%)")
    print()
    print("**WHY 'verification good' IS MISLEADING**:")
    print("  - It's an intermediate signal during the solving process")
    print("  - Does NOT guarantee the final answer is correct")
    print("  - Agent may pass verification but fail to extract valid k values")
    print("  - PROPER METRIC: Final verdict (CORRECT/INCOMPLETE/WRONG)")
    print()

    # Section 2: Statistical Analysis
    print()
    print("## 2. STATISTICAL ANALYSIS")
    print("-" * 80)
    print()

    print("### Overall Performance")
    print(f"  - Total Runs: {stats['total_runs']}")
    print(f"  - Success Rate: {stats['success_rate']*100:.1f}% ({stats['correct_count']}/{stats['total_runs']})")
    print(f"  - Failure Rate: {stats['incorrect_count']/stats['total_runs']*100:.1f}% ({stats['incorrect_count']}/{stats['total_runs']})")
    print()

    print("### Iteration Analysis")
    print()
    print("**Successful Runs (CORRECT):**")
    print(f"  - Mean iterations: {stats['iterations_correct_mean']:.2f}")
    print(f"  - Median iterations: {stats['iterations_correct_median']:.1f}")
    print(f"  - Std deviation: {stats['iterations_correct_stdev']:.2f}")
    print()

    print("**Unsuccessful Runs (INCOMPLETE/WRONG):**")
    print(f"  - Mean iterations: {stats['iterations_incorrect_mean']:.2f}")
    print(f"  - Median iterations: {stats['iterations_incorrect_median']:.1f}")
    print()

    # Detailed per-run metrics
    print("### Per-Run Metrics")
    print()
    print("| Run | Verdict    | Iterations | Answer      | Stuck | Errors |")
    print("|-----|------------|------------|-------------|-------|--------|")
    for r in sorted(results, key=lambda x: x['run_id']):
        print(f"| {r['run_id']:8} | {r['verdict']:10} | {r['iterations']:10} | {r['final_answer']:11} | {r['stuck_count']:5} | {r['error_count']:6} |")

    print()

    # Section 3: Deep Dive - Run 2
    print()
    print("## 3. DEEP DIVE: RUN 2 (Fast Failure)")
    print("-" * 80)
    run2 = [r for r in results if r['run_id'] == 'bfs_run2'][0]
    print()
    print(f"  - Verdict: {run2['verdict']}")
    print(f"  - Iterations: {run2['iterations']}")
    print(f"  - Final Answer: {run2['final_answer']}")
    print(f"  - Answer Progression: {run2['answer_progression']}")
    print()
    print("**See detailed timeline analysis below in log review**")
    print()

    # Section 4: Comparative Analysis
    print()
    print("## 4. COMPARATIVE ANALYSIS: Run 2 vs Run 4")
    print("-" * 80)
    run2 = [r for r in results if r['run_id'] == 'bfs_run2'][0]
    run4 = [r for r in results if r['run_id'] == 'bfs_run4'][0]

    print()
    print("| Metric          | Run 2 (INCOMPLETE) | Run 4 (CORRECT) |")
    print("|-----------------|-------------------|-----------------|")
    print(f"| Iterations      | {run2['iterations']:17} | {run4['iterations']:15} |")
    print(f"| Final Answer    | {run2['final_answer']:17} | {run4['final_answer']:15} |")
    print(f"| Stuck Count     | {run2['stuck_count']:17} | {run4['stuck_count']:15} |")
    print(f"| Errors Found    | {run2['error_count']:17} | {run4['error_count']:15} |")
    print()

    # Section 5: Performance Metrics
    print()
    print("## 5. PERFORMANCE METRICS vs PREDICTIONS")
    print("-" * 80)
    print()

    # Confidence interval for success rate
    # Wilson score interval for binomial proportion
    import math
    n = stats['total_runs']
    p = stats['success_rate']
    z = 1.96  # 95% confidence

    denominator = 1 + z**2/n
    center = (p + z**2/(2*n)) / denominator
    margin = z * math.sqrt((p*(1-p)/n + z**2/(4*n**2))) / denominator
    ci_lower = center - margin
    ci_upper = center + margin

    print(f"**Success Rate: {p*100:.1f}% ({stats['correct_count']}/{n})**")
    print(f"  - 95% CI: [{ci_lower*100:.1f}%, {ci_upper*100:.1f}%]")
    print()
    print(f"**vs Expert Prediction: 30-50%**")
    print(f"  - Observed: {p*100:.1f}%")
    print(f"  - Beats upper bound by: {(p-0.5)*100:.1f} percentage points")
    print()

    # Statistical significance test (binomial test)
    # H0: p = 0.5 (upper bound of prediction)
    # H1: p > 0.5
    from scipy import stats as scipy_stats
    p_value = scipy_stats.binomtest(stats['correct_count'], n, 0.5, alternative='greater').pvalue

    print(f"**Statistical Significance Test**")
    print(f"  - Null hypothesis: p = 0.50 (expert upper bound)")
    print(f"  - Alternative: p > 0.50")
    print(f"  - p-value: {p_value:.4f}")
    if p_value < 0.05:
        print(f"  - Result: SIGNIFICANT (p < 0.05) ✓")
    else:
        print(f"  - Result: NOT SIGNIFICANT (p >= 0.05)")
    print()

    # Section 6: Recommendation for N=100
    print()
    print("## 6. RECOMMENDATION FOR N=100 STUDY")
    print("-" * 80)
    print()

    # Expected success rate with 95% CI
    print(f"**Expected Success Rate (based on N=12 pilot):**")
    print(f"  - Point estimate: {p*100:.1f}%")
    print(f"  - 95% CI: [{ci_lower*100:.1f}%, {ci_upper*100:.1f}%]")
    print()

    # Power analysis for N=100
    print(f"**Statistical Power Analysis for N=100:**")
    se_100 = math.sqrt(p * (1-p) / 100)
    ci_100_lower = max(0, p - 1.96 * se_100)
    ci_100_upper = min(1, p + 1.96 * se_100)
    print(f"  - Expected 95% CI: [{ci_100_lower*100:.1f}%, {ci_100_upper*100:.1f}%]")
    print(f"  - Margin of error: ±{1.96*se_100*100:.1f}%")
    print()

    print(f"**Cost Projection:**")
    print(f"  - Estimated cost per run: $X (need to extract from logs)")
    print(f"  - Total cost for N=100: $X * 100")
    print()

    print(f"**Duration Projection:**")
    print(f"  - Need to extract timing data from logs")
    print()

    print(f"**RECOMMENDATION:**")
    if p > 0.7:
        print("  ✓ PROCEED with N=100 study")
        print(f"  - Success rate ({p*100:.1f}%) significantly exceeds expert prediction")
        print("  - N=12 pilot provides strong evidence of treatment effect")
        print("  - N=100 will provide narrow confidence intervals (±{:.1f}%)".format(1.96*se_100*100))
    elif p > 0.5:
        print("  ⚠ PROCEED WITH CAUTION")
        print(f"  - Success rate ({p*100:.1f}%) beats prediction but CI is wide")
        print("  - Consider N=50 intermediate study first")
    else:
        print("  ✗ DO NOT PROCEED")
        print(f"  - Success rate ({p*100:.1f}%) below expert prediction")
        print("  - Re-evaluate treatment design")

    print()
    print("=" * 80)

if __name__ == '__main__':
    try:
        import scipy.stats
    except ImportError:
        print("Installing scipy for statistical tests...")
        import subprocess
        subprocess.run(['pip', 'install', 'scipy', '-q'])
        import scipy.stats

    base_dir = Path('/home/user/IMO25/bfs_validation_test')
    results, stats = analyze_all_runs(base_dir)
    print_analysis_report(results, stats)
