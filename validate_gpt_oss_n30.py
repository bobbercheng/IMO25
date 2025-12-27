#!/usr/bin/env python3
"""
Statistical Validation for gpt-oss-120b Option 1 (n=30)

Runs 30 iterations of the 6-test suite to achieve statistical significance.

Current state (n=6):
- Accuracy: 100% (6/6)
- 95% CI: [54%, 100%] - Too wide for deployment

Target (n=30):
- If 100%: 95% CI: [88%, 100%] - Acceptable for deployment
- If 90%: 95% CI: [73%, 98%] - Investigate failures
- If 80%: 95% CI: [61%, 92%] - At threshold, proceed with caution
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
ITERATIONS = 30
REASONING_EFFORT = "high"
RESULTS_DIR = Path("validation_results_n30")
SLEEP_BETWEEN_ITERATIONS = 5  # seconds, avoid rate limiting

# Ensure results directory exists
RESULTS_DIR.mkdir(exist_ok=True)

print("="*80)
print("GPT-OSS-120B STATISTICAL VALIDATION (n=30)")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Iterations: {ITERATIONS}")
print(f"Reasoning: {REASONING_EFFORT}")
print(f"Results dir: {RESULTS_DIR}")
print("="*80)

# Check API key
if not os.getenv("OPENROUTER_API_KEY") and not os.getenv("GPT_OSS_API_KEY"):
    print("\n❌ ERROR: No API key found")
    print("Set one of: OPENROUTER_API_KEY or GPT_OSS_API_KEY")
    sys.exit(1)

# Run iterations
results = []
start_time = time.time()

for iteration in range(1, ITERATIONS + 1):
    print(f"\n{'='*80}")
    print(f"ITERATION {iteration}/{ITERATIONS}")
    print(f"{'='*80}")

    iter_start = time.time()

    # Run test
    result_file = RESULTS_DIR / f"iteration_{iteration:02d}.json"

    try:
        cmd = [
            "python",
            "test_option_a_openrouter.py",
            "--reasoning", REASONING_EFFORT,
            "--quiet"  # Suppress verbose output
        ]

        # Run test
        subprocess.run(cmd, check=True)

        # Find most recent result file
        latest_result = max(Path(".").glob("optionA_openrouter_test_*.json"), key=lambda p: p.stat().st_mtime)

        # Move to results directory
        latest_result.rename(result_file)

        # Load and display summary
        with open(result_file) as f:
            data = json.load(f)

        accuracy = data.get('accuracy', 0)
        matches = data.get('matches', 0)
        total = data.get('total_tests', 6)
        elapsed = time.time() - iter_start

        print(f"\n✓ Iteration {iteration} complete:")
        print(f"  Accuracy: {accuracy*100:.1f}% ({matches}/{total})")
        print(f"  Elapsed: {elapsed:.1f}s")

        results.append(data)

        # Brief pause to avoid rate limiting
        if iteration < ITERATIONS:
            print(f"\nWaiting {SLEEP_BETWEEN_ITERATIONS}s...")
            time.sleep(SLEEP_BETWEEN_ITERATIONS)

    except Exception as e:
        print(f"\n✗ Iteration {iteration} FAILED: {e}")
        # Save error info
        with open(result_file, 'w') as f:
            json.dump({
                'iteration': iteration,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)

total_elapsed = time.time() - start_time

print(f"\n{'='*80}")
print("ALL ITERATIONS COMPLETE")
print(f"{'='*80}")
print(f"Total time: {total_elapsed/60:.1f} minutes")

# Aggregate results
print(f"\n{'='*80}")
print("STATISTICAL ANALYSIS")
print(f"{'='*80}")

# Calculate aggregate statistics
total_tests = sum(r.get('total_tests', 0) for r in results if 'total_tests' in r)
total_matches = sum(r.get('matches', 0) for r in results if 'matches' in r)
completed_iterations = len([r for r in results if 'total_tests' in r])

if total_tests > 0:
    accuracy = total_matches / total_tests

    # Wilson score confidence interval
    import numpy as np

    def wilson_ci(successes, trials, confidence=0.95):
        """Calculate Wilson score confidence interval"""
        if trials == 0:
            return (0, 0)

        p = successes / trials
        z = 1.96 if confidence == 0.95 else 2.576  # 95% or 99%

        denominator = 1 + z**2 / trials
        centre_adjusted_probability = (p + z**2 / (2 * trials)) / denominator
        adjusted_standard_error = np.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / denominator

        lower = max(0, centre_adjusted_probability - z * adjusted_standard_error)
        upper = min(1, centre_adjusted_probability + z * adjusted_standard_error)

        return (lower, upper)

    ci_lower, ci_upper = wilson_ci(total_matches, total_tests, 0.95)
    margin = (ci_upper - ci_lower) / 2

    print(f"\n📊 Aggregate Results:")
    print(f"  Total iterations: {ITERATIONS}")
    print(f"  Completed: {completed_iterations}")
    print(f"  Total tests: {total_tests}")
    print(f"  Total matches: {total_matches}")
    print(f"\n  Overall Accuracy: {accuracy*100:.1f}%")
    print(f"  95% CI: [{ci_lower*100:.1f}%, {ci_upper*100:.1f}%]")
    print(f"  Margin of error: ±{margin*100:.1f}pp")

    # Decision criteria
    print(f"\n📋 Deployment Decision:")
    if ci_lower >= 0.80:
        print("  ✅ READY FOR PRODUCTION")
        print(f"     Lower bound ({ci_lower*100:.1f}%) exceeds 80% threshold")
    elif ci_lower >= 0.70:
        print("  ⚠️  MARGINAL - INVESTIGATE FAILURES")
        print(f"     Lower bound ({ci_lower*100:.1f}%) between 70-80%")
    else:
        print("  ❌ DO NOT DEPLOY")
        print(f"     Lower bound ({ci_lower*100:.1f}%) below 70%")

    # Per-test breakdown
    print(f"\n📊 Per-Test Accuracy:")

    test_stats = {i: {'pass': 0, 'fail': 0, 'error': 0} for i in range(1, 7)}

    for r in results:
        if 'results' in r:
            for test in r['results']:
                test_num = test.get('test_number')
                if test_num:
                    if test.get('error'):
                        test_stats[test_num]['error'] += 1
                    elif test.get('match'):
                        test_stats[test_num]['pass'] += 1
                    else:
                        test_stats[test_num]['fail'] += 1

    for test_num in range(1, 7):
        stats = test_stats[test_num]
        total = stats['pass'] + stats['fail'] + stats['error']
        if total > 0:
            acc = stats['pass'] / total
            print(f"  Test {test_num}: {acc*100:5.1f}% ({stats['pass']}/{total}) - "
                  f"Pass: {stats['pass']}, Fail: {stats['fail']}, Error: {stats['error']}")

    # Identify problematic tests
    print(f"\n⚠️  Tests with <90% accuracy:")
    for test_num in range(1, 7):
        stats = test_stats[test_num]
        total = stats['pass'] + stats['fail'] + stats['error']
        if total > 0:
            acc = stats['pass'] / total
            if acc < 0.90:
                print(f"  Test {test_num}: {acc*100:.1f}% - "
                      f"{stats['fail']} failures, {stats['error']} errors")

    # Save summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'iterations': ITERATIONS,
        'completed': completed_iterations,
        'total_tests': total_tests,
        'total_matches': total_matches,
        'accuracy': accuracy,
        'confidence_interval_95': {
            'lower': ci_lower,
            'upper': ci_upper,
            'margin': margin
        },
        'per_test_stats': {
            f'test_{i}': test_stats[i] for i in range(1, 7)
        },
        'deployment_ready': ci_lower >= 0.80,
        'results_files': [str(f) for f in sorted(RESULTS_DIR.glob("iteration_*.json"))]
    }

    summary_file = RESULTS_DIR / 'validation_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n📄 Summary saved to: {summary_file}")

else:
    print("\n❌ No valid results to analyze")

print(f"\n{'='*80}")
print("VALIDATION COMPLETE")
print(f"{'='*80}")
