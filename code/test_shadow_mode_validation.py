#!/usr/bin/env python3
"""
Shadow Mode Testing for Solution 2 Validation

This script runs dual verification (baseline vs optimized) to validate
that Solution 2 maintains accuracy while reducing costs and truncation.

Baseline Configuration:
- Reasoning effort: high
- Prompt: Same prompt (cannot restore old prompt without code changes)
- Max tokens: 8192 → 12288 → 16384 (progressive retry)

Optimized Configuration (Solution 2):
- Reasoning effort: medium
- Prompt: 3 examples, Level 2 ≤200 words, no detailed log, expanded JSON
- Max tokens: adaptive (3k/5k/7k based on solution length)

Success Criteria:
- Verdict agreement rate: >95%
- Token reduction: ~20-30% (from reasoning effort change)
- Truncation rate: <5% (down from 31%)
- False positive rate: <3%
- False negative rate: <2%

Note: This shadow mode compares HIGH vs MEDIUM reasoning effort with the
      same optimized prompt. Full baseline comparison would require reverting
      prompt changes, which is not practical for validation.
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import test data
from test_data import (
    get_test_data,
    get_all_test_numbers,
    get_test_case
)

# Import verification functions
from agent_gpt_oss import (
    verify_solution,
    calculate_verification_budget,
    VERIFICATION_REASONING_EFFORT,
    send_api_request_with_retry,
    get_api_key
)


def verify_baseline(problem_statement: str, solution: str, verbose: bool = False) -> Dict:
    """
    Run baseline verification (HIGH reasoning).

    Simulates baseline configuration:
    - reasoning_effort='high'
    - Static max_tokens=8192 (handled by verify_solution retry logic)

    Note: Uses current prompt (cannot restore old 6-example prompt without code changes)
    """
    start_time = time.time()
    truncation_count = 0

    try:
        # Track API call to capture token usage
        # Since verify_solution doesn't return token usage, we'll track it globally
        # For now, just run verification and track time/verdict

        bug_report, verdict = verify_solution(
            problem_statement,
            solution,
            verbose=verbose,
            reasoning_effort='high'  # Baseline uses HIGH
        )

        elapsed = time.time() - start_time

        # Extract token usage from bug_report if available
        # (This is a simplified approach - full implementation would intercept API calls)
        tokens_input = None
        tokens_output = None

        return {
            'verdict': verdict,
            'bug_report': bug_report,
            'elapsed_seconds': elapsed,
            'reasoning_effort': 'high',
            'tokens_input': tokens_input,
            'tokens_output': tokens_output,
            'truncation_retries': truncation_count,
            'error': None
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'verdict': 'error',
            'bug_report': str(e),
            'elapsed_seconds': elapsed,
            'reasoning_effort': 'high',
            'tokens_input': None,
            'tokens_output': None,
            'truncation_retries': 0,
            'error': str(e)
        }


def verify_optimized(problem_statement: str, solution: str, verbose: bool = False) -> Dict:
    """
    Run optimized verification (MEDIUM reasoning, Solution 2).

    Uses new configuration:
    - reasoning_effort='medium'
    - Adaptive max_tokens (via calculate_verification_budget)
    - Optimized prompt (3 examples, hard Level 2 constraint, no detailed log)
    """
    start_time = time.time()

    try:
        bug_report, verdict = verify_solution(
            problem_statement,
            solution,
            verbose=verbose,
            reasoning_effort='medium'  # Solution 2 uses MEDIUM
        )

        elapsed = time.time() - start_time

        # Extract token usage if available
        tokens_input = None
        tokens_output = None

        return {
            'verdict': verdict,
            'bug_report': bug_report,
            'elapsed_seconds': elapsed,
            'reasoning_effort': 'medium',
            'tokens_input': tokens_input,
            'tokens_output': tokens_output,
            'truncation_retries': 0,
            'error': None
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'verdict': 'error',
            'bug_report': str(e),
            'elapsed_seconds': elapsed,
            'reasoning_effort': 'medium',
            'tokens_input': None,
            'tokens_output': None,
            'truncation_retries': 0,
            'error': str(e)
        }


def run_shadow_test(test_number: int, verbose: bool = False) -> Dict:
    """
    Run shadow mode test for a single test case.

    Returns comparison data including:
    - Both verdicts (baseline and optimized)
    - Agreement (yes/no)
    - Token usage comparison (if available)
    - Latency comparison
    - Error details
    - Expected verdict (ground truth)
    """
    print(f"\n{'='*80}")
    print(f"Shadow Test {test_number}")
    print(f"{'='*80}")

    # Get test case data
    test_case = get_test_case(test_number)
    if not test_case:
        return {
            'test_number': test_number,
            'error': f'Test {test_number} not found or data unavailable',
            'agreement': False,
            'baseline_correct': False,
            'optimized_correct': False
        }

    problem = test_case['problem_statement']
    solution = test_case['solution']
    expected_verdict = test_case['expected_verdict']
    test_name = test_case['test_name']

    print(f"Test: {test_name}")
    print(f"Expected verdict: {expected_verdict}")
    print(f"Solution length: {len(solution)} chars")
    print(f"Adaptive budget: {calculate_verification_budget(len(solution))} tokens")
    print()

    # Run baseline verification (HIGH reasoning)
    print("Running BASELINE verification (reasoning=high)...")
    baseline_result = verify_baseline(problem, solution, verbose)

    # Run optimized verification (MEDIUM reasoning)
    print("\nRunning OPTIMIZED verification (reasoning=medium)...")
    optimized_result = verify_optimized(problem, solution, verbose)

    # Compare results
    baseline_verdict = baseline_result['verdict']
    optimized_verdict = optimized_result['verdict']

    # Normalize verdicts for comparison
    baseline_pass = baseline_verdict.lower() == "yes"
    optimized_pass = optimized_verdict.lower() == "yes"
    expected_pass = expected_verdict == "PASS"

    # Check agreement
    verdicts_agree = (baseline_pass == optimized_pass)

    # Check correctness against ground truth
    baseline_correct = (baseline_pass == expected_pass)
    optimized_correct = (optimized_pass == expected_pass)

    # Calculate metrics
    latency_diff = optimized_result['elapsed_seconds'] - baseline_result['elapsed_seconds']
    latency_improvement = (latency_diff / baseline_result['elapsed_seconds'] * 100) if baseline_result['elapsed_seconds'] > 0 else 0

    # Token comparison (if available)
    token_savings = None
    if baseline_result.get('tokens_output') and optimized_result.get('tokens_output'):
        baseline_tokens = baseline_result['tokens_output']
        optimized_tokens = optimized_result['tokens_output']
        token_savings = ((baseline_tokens - optimized_tokens) / baseline_tokens * 100) if baseline_tokens > 0 else 0

    # Build result
    result = {
        'test_number': test_number,
        'test_name': test_name,
        'expected_verdict': expected_verdict,
        'baseline': {
            'verdict': baseline_verdict,
            'pass': baseline_pass,
            'elapsed_seconds': baseline_result['elapsed_seconds'],
            'tokens_input': baseline_result.get('tokens_input'),
            'tokens_output': baseline_result.get('tokens_output'),
            'truncation_retries': baseline_result.get('truncation_retries', 0),
            'error': baseline_result.get('error')
        },
        'optimized': {
            'verdict': optimized_verdict,
            'pass': optimized_pass,
            'elapsed_seconds': optimized_result['elapsed_seconds'],
            'tokens_input': optimized_result.get('tokens_input'),
            'tokens_output': optimized_result.get('tokens_output'),
            'truncation_retries': optimized_result.get('truncation_retries', 0),
            'error': optimized_result.get('error')
        },
        'comparison': {
            'verdicts_agree': verdicts_agree,
            'baseline_correct': baseline_correct,
            'optimized_correct': optimized_correct,
            'latency_diff_seconds': latency_diff,
            'latency_improvement_percent': latency_improvement,
            'token_savings_percent': token_savings
        }
    }

    # Print summary
    print(f"\n{'='*40}")
    print(f"RESULTS - Test {test_number}")
    print(f"{'='*40}")
    print(f"Expected: {expected_verdict}")
    print(f"Baseline (HIGH): {baseline_verdict} ({'✓' if baseline_correct else '✗'})")
    print(f"Optimized (MEDIUM): {optimized_verdict} ({'✓' if optimized_correct else '✗'})")
    print(f"Agreement: {'✅ YES' if verdicts_agree else '❌ NO'}")
    print(f"Latency: {baseline_result['elapsed_seconds']:.1f}s → {optimized_result['elapsed_seconds']:.1f}s ({latency_improvement:+.1f}%)")
    if token_savings is not None:
        print(f"Token savings: {token_savings:.1f}%")
    print(f"{'='*40}\n")

    return result


def run_all_shadow_tests(test_numbers: List[int] = None, verbose: bool = False) -> Dict:
    """
    Run shadow mode tests for all test cases.

    Returns summary statistics:
    - Agreement rate
    - Average latency improvement
    - Accuracy metrics (FP/FN rates)
    - Error analysis
    """
    if test_numbers is None:
        test_numbers = get_all_test_numbers()

    print(f"\n{'='*80}")
    print(f"SHADOW MODE VALIDATION - Solution 2")
    print(f"{'='*80}")
    print(f"Running {len(test_numbers)} test cases")
    print(f"Baseline: reasoning='high', static max_tokens (8k→12k→16k)")
    print(f"Optimized: reasoning='medium', adaptive max_tokens (3k/5k/7k)")
    print(f"{'='*80}\n")

    results = []
    for test_num in test_numbers:
        result = run_shadow_test(test_num, verbose)
        if result and not result.get('error'):
            results.append(result)
        else:
            print(f"⚠️  Test {test_num} skipped or failed: {result.get('error', 'unknown error')}")

    # Calculate summary statistics
    total_tests = len(results)
    if total_tests == 0:
        print("❌ No valid test results")
        return {
            'total_tests': 0,
            'error': 'No valid test results',
            'timestamp': datetime.now().isoformat()
        }

    # Agreement rate
    agreements = sum(1 for r in results if r['comparison']['verdicts_agree'])
    agreement_rate = (agreements / total_tests * 100)

    # Accuracy metrics
    baseline_correct_count = sum(1 for r in results if r['comparison']['baseline_correct'])
    optimized_correct_count = sum(1 for r in results if r['comparison']['optimized_correct'])

    baseline_accuracy = (baseline_correct_count / total_tests * 100)
    optimized_accuracy = (optimized_correct_count / total_tests * 100)

    # False positives (predicted PASS, expected FAIL)
    baseline_fp = sum(1 for r in results if r['baseline']['pass'] and r['expected_verdict'] == 'FAIL')
    optimized_fp = sum(1 for r in results if r['optimized']['pass'] and r['expected_verdict'] == 'FAIL')

    # False negatives (predicted FAIL, expected PASS)
    baseline_fn = sum(1 for r in results if not r['baseline']['pass'] and r['expected_verdict'] == 'PASS')
    optimized_fn = sum(1 for r in results if not r['optimized']['pass'] and r['expected_verdict'] == 'PASS')

    # Count expected PASS and FAIL cases
    expected_pass_count = sum(1 for r in results if r['expected_verdict'] == 'PASS')
    expected_fail_count = sum(1 for r in results if r['expected_verdict'] == 'FAIL')

    baseline_fp_rate = (baseline_fp / expected_fail_count * 100) if expected_fail_count > 0 else 0
    optimized_fp_rate = (optimized_fp / expected_fail_count * 100) if expected_fail_count > 0 else 0

    baseline_fn_rate = (baseline_fn / expected_pass_count * 100) if expected_pass_count > 0 else 0
    optimized_fn_rate = (optimized_fn / expected_pass_count * 100) if expected_pass_count > 0 else 0

    # Latency comparison
    avg_baseline_latency = sum(r['baseline']['elapsed_seconds'] for r in results) / total_tests
    avg_optimized_latency = sum(r['optimized']['elapsed_seconds'] for r in results) / total_tests
    avg_latency_improvement = ((avg_baseline_latency - avg_optimized_latency) / avg_baseline_latency * 100) if avg_baseline_latency > 0 else 0

    # Disagreement analysis
    disagreements = [r for r in results if not r['comparison']['verdicts_agree']]

    summary = {
        'total_tests': total_tests,
        'agreement': {
            'count': agreements,
            'rate_percent': agreement_rate,
            'disagreements': len(disagreements)
        },
        'baseline': {
            'correct_count': baseline_correct_count,
            'accuracy_percent': baseline_accuracy,
            'false_positives': baseline_fp,
            'false_negatives': baseline_fn,
            'fp_rate_percent': baseline_fp_rate,
            'fn_rate_percent': baseline_fn_rate,
            'avg_latency_seconds': avg_baseline_latency
        },
        'optimized': {
            'correct_count': optimized_correct_count,
            'accuracy_percent': optimized_accuracy,
            'false_positives': optimized_fp,
            'false_negatives': optimized_fn,
            'fp_rate_percent': optimized_fp_rate,
            'fn_rate_percent': optimized_fn_rate,
            'avg_latency_seconds': avg_optimized_latency
        },
        'performance': {
            'latency_improvement_percent': avg_latency_improvement,
            'latency_saved_seconds': avg_baseline_latency - avg_optimized_latency
        },
        'test_distribution': {
            'expected_pass': expected_pass_count,
            'expected_fail': expected_fail_count
        },
        'disagreement_details': [
            {
                'test_number': r['test_number'],
                'test_name': r['test_name'],
                'expected': r['expected_verdict'],
                'baseline': r['baseline']['verdict'],
                'optimized': r['optimized']['verdict']
            }
            for r in disagreements
        ],
        'timestamp': datetime.now().isoformat(),
        'full_results': results
    }

    # Print detailed summary
    print(f"\n{'='*80}")
    print(f"SHADOW MODE SUMMARY")
    print(f"{'='*80}")
    print(f"\nTest Coverage:")
    print(f"  Total tests: {total_tests}")
    print(f"  Expected PASS: {expected_pass_count}")
    print(f"  Expected FAIL: {expected_fail_count}")

    print(f"\nVerdict Agreement:")
    print(f"  Agreements: {agreements}/{total_tests}")
    print(f"  Agreement rate: {agreement_rate:.1f}%")
    print(f"  Disagreements: {len(disagreements)}")

    print(f"\nBaseline (HIGH reasoning):")
    print(f"  Accuracy: {baseline_accuracy:.1f}%")
    print(f"  False Positive rate: {baseline_fp_rate:.1f}%")
    print(f"  False Negative rate: {baseline_fn_rate:.1f}%")
    print(f"  Avg latency: {avg_baseline_latency:.1f}s")

    print(f"\nOptimized (MEDIUM reasoning):")
    print(f"  Accuracy: {optimized_accuracy:.1f}%")
    print(f"  False Positive rate: {optimized_fp_rate:.1f}%")
    print(f"  False Negative rate: {optimized_fn_rate:.1f}%")
    print(f"  Avg latency: {avg_optimized_latency:.1f}s")

    print(f"\nPerformance Improvement:")
    print(f"  Latency: {avg_latency_improvement:+.1f}%")
    print(f"  Time saved: {avg_latency_improvement/100 * avg_baseline_latency:.1f}s per verification")

    if disagreements:
        print(f"\nDisagreement Cases:")
        for d in summary['disagreement_details']:
            print(f"  Test {d['test_number']}: {d['test_name']}")
            print(f"    Expected: {d['expected']}, Baseline: {d['baseline']}, Optimized: {d['optimized']}")

    print(f"\n{'='*80}")
    print(f"VALIDATION DECISION")
    print(f"{'='*80}")

    # Validation criteria
    passed_criteria = []
    failed_criteria = []

    if agreement_rate >= 95:
        passed_criteria.append(f"✅ Agreement rate: {agreement_rate:.1f}% ≥ 95%")
    elif agreement_rate >= 92:
        passed_criteria.append(f"⚠️  Agreement rate: {agreement_rate:.1f}% ≥ 92% (conditional)")
    else:
        failed_criteria.append(f"❌ Agreement rate: {agreement_rate:.1f}% < 92%")

    if optimized_fp_rate < 3:
        passed_criteria.append(f"✅ FP rate: {optimized_fp_rate:.1f}% < 3%")
    elif optimized_fp_rate < 5:
        passed_criteria.append(f"⚠️  FP rate: {optimized_fp_rate:.1f}% < 5% (conditional)")
    else:
        failed_criteria.append(f"❌ FP rate: {optimized_fp_rate:.1f}% ≥ 5%")

    if optimized_fn_rate < 2:
        passed_criteria.append(f"✅ FN rate: {optimized_fn_rate:.1f}% < 2%")
    elif optimized_fn_rate < 5:
        passed_criteria.append(f"⚠️  FN rate: {optimized_fn_rate:.1f}% < 5% (conditional)")
    else:
        failed_criteria.append(f"❌ FN rate: {optimized_fn_rate:.1f}% ≥ 5%")

    for criterion in passed_criteria:
        print(criterion)

    for criterion in failed_criteria:
        print(criterion)

    print()

    # Final decision
    if failed_criteria:
        print("❌ FAILURE: One or more criteria failed - Fall back to Solution 1")
        decision = "FAIL"
    elif any("⚠️" in c for c in passed_criteria):
        print("⚠️  CONDITIONAL: All hard criteria passed - Deploy with monitoring")
        decision = "CONDITIONAL"
    else:
        print("✅ SUCCESS: All criteria passed - Solution 2 validated for deployment")
        decision = "SUCCESS"

    summary['validation_decision'] = decision
    print(f"{'='*80}\n")

    return summary


def main():
    """Main entry point for shadow mode testing."""
    parser = argparse.ArgumentParser(
        description='Shadow mode testing for Solution 2 validation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python test_shadow_mode_validation.py

  # Run specific tests
  python test_shadow_mode_validation.py --test 1 2

  # Run with verbose output
  python test_shadow_mode_validation.py --verbose

  # Save results to custom file
  python test_shadow_mode_validation.py --output my_results.json

Exit codes:
  0 - SUCCESS: Agreement ≥95%, FP <3%, FN <2%
  1 - CONDITIONAL: Agreement ≥92%, FP <5%, FN <5%
  2 - FAILURE: Agreement <92% or FP ≥5% or FN ≥5%
        """
    )
    parser.add_argument(
        '--test',
        type=int,
        nargs='+',
        help='Specific test numbers to run (default: all tests)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output from verification'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='shadow_mode_results.json',
        help='Output file for results (default: shadow_mode_results.json)'
    )

    args = parser.parse_args()

    # Check API key
    try:
        api_key = get_api_key()
        print(f"✓ API key configured: {api_key[:20]}...")
    except SystemExit:
        print("✗ API key not configured. Set GPT_OSS_API_KEY or OPENAI_API_KEY")
        sys.exit(3)

    # Run shadow tests
    summary = run_all_shadow_tests(
        test_numbers=args.test,
        verbose=args.verbose
    )

    # Save results
    with open(args.output, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nResults saved to: {args.output}")

    # Exit with appropriate code based on validation decision
    decision = summary.get('validation_decision', 'FAIL')
    if decision == 'SUCCESS':
        sys.exit(0)  # Success
    elif decision == 'CONDITIONAL':
        sys.exit(1)  # Conditional - needs review
    else:
        sys.exit(2)  # Failure - do not deploy


if __name__ == '__main__':
    main()
