#!/usr/bin/env python3
"""
Shadow Mode Testing for Solution 2 Validation

This script runs dual verification (baseline vs optimized) to validate
that Solution 2 maintains accuracy while reducing costs and truncation.

Baseline Configuration:
- Reasoning effort: high
- Prompt: 6 examples, no hard Level 2 constraint, detailed verification log
- Max tokens: 8192 → 12288 → 16384 (progressive retry)

Optimized Configuration (Solution 2):
- Reasoning effort: medium
- Prompt: 3 examples, Level 2 ≤200 words, no detailed log, expanded JSON
- Max tokens: adaptive (3k/5k/7k based on solution length)

Success Criteria:
- Verdict agreement rate: >95%
- Token reduction: ~64% (predicted)
- Truncation rate: <5% (down from 31%)
- False positive rate: <3%
- False negative rate: <2%
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, List, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import test cases
from test_option_b_full_solution_validation import (
    TEST_FUNCTIONS,
    PROBLEM_STATEMENT
)

# Import verification functions
from agent_gpt_oss import (
    verify_solution,
    calculate_verification_budget,
    VERIFICATION_REASONING_EFFORT
)


def verify_baseline(problem_statement: str, solution: str, verbose: bool = False) -> Dict:
    """
    Run baseline verification (pre-Solution 2).

    Simulates old configuration:
    - reasoning_effort='high'
    - Static max_tokens=8192 (handled by verify_solution retry logic)

    Note: Cannot restore old prompt without code changes, so this uses
    current prompt with high reasoning for comparison.
    """
    start_time = time.time()

    try:
        bug_report, verdict = verify_solution(
            problem_statement,
            solution,
            verbose=verbose,
            reasoning_effort='high'  # Baseline uses HIGH
        )

        elapsed = time.time() - start_time

        return {
            'verdict': verdict,
            'bug_report': bug_report,
            'elapsed_seconds': elapsed,
            'reasoning_effort': 'high',
            'error': None
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'verdict': 'error',
            'bug_report': str(e),
            'elapsed_seconds': elapsed,
            'reasoning_effort': 'high',
            'error': str(e)
        }


def verify_optimized(problem_statement: str, solution: str, verbose: bool = False) -> Dict:
    """
    Run optimized verification (Solution 2).

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

        return {
            'verdict': verdict,
            'bug_report': bug_report,
            'elapsed_seconds': elapsed,
            'reasoning_effort': 'medium',
            'error': None
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'verdict': 'error',
            'bug_report': str(e),
            'elapsed_seconds': elapsed,
            'reasoning_effort': 'medium',
            'error': str(e)
        }


def run_shadow_test(test_number: int, verbose: bool = False) -> Dict:
    """
    Run shadow mode test for a single test case.

    Returns comparison data including:
    - Both verdicts
    - Agreement (yes/no)
    - Token usage (if available)
    - Latency comparison
    - Error details
    """
    print(f"\n{'='*80}")
    print(f"Shadow Test {test_number}")
    print(f"{'='*80}")

    # Get test function
    if test_number not in TEST_FUNCTIONS:
        return {
            'test_number': test_number,
            'error': f'Test {test_number} not found',
            'agreement': False
        }

    test_func = TEST_FUNCTIONS[test_number]

    # Extract solution from test function
    # Test functions are parameterized, so we need to call them
    try:
        # Call test function to get solution
        # Most test functions don't actually need to run verification,
        # we just need the solution text
        import inspect
        source = inspect.getsource(test_func)

        # Extract solution from source (quick hack for shadow mode)
        # Better approach: refactor test functions to return (problem, solution, expected_verdict)
        if 'SOLUTION =' in source or 'solution =' in source:
            # Parse solution from source
            # For now, call the test and capture the solution
            # This is a temporary approach
            pass
    except Exception as e:
        print(f"[WARNING] Could not extract solution from test function: {e}")
        return {
            'test_number': test_number,
            'error': str(e),
            'agreement': False
        }

    # TODO: This is a stub - need to refactor test_option_b_full_solution_validation.py
    # to separate test data (problem, solution, expected_verdict) from test execution

    print("[SHADOW MODE] This is a template - requires test data refactoring")
    print("[SHADOW MODE] Next step: Extract solutions from test_option_b_full_solution_validation.py")

    return {
        'test_number': test_number,
        'error': 'Template script - needs test data extraction',
        'agreement': None
    }


def run_all_shadow_tests(test_numbers: List[int] = None, verbose: bool = False) -> Dict:
    """
    Run shadow mode tests for all test cases.

    Returns summary statistics:
    - Agreement rate
    - Average token reduction
    - Truncation rate comparison
    - Latency comparison
    """
    if test_numbers is None:
        test_numbers = sorted(TEST_FUNCTIONS.keys())

    print(f"\n{'='*80}")
    print(f"SHADOW MODE VALIDATION - Solution 2")
    print(f"{'='*80}")
    print(f"Running {len(test_numbers)} test cases")
    print(f"Baseline: reasoning='high', static max_tokens")
    print(f"Optimized: reasoning='medium', adaptive max_tokens")
    print(f"{'='*80}\n")

    results = []
    for test_num in test_numbers:
        result = run_shadow_test(test_num, verbose)
        results.append(result)

    # Calculate summary statistics
    total_tests = len(results)
    agreements = sum(1 for r in results if r.get('agreement') is True)
    disagreements = sum(1 for r in results if r.get('agreement') is False)
    errors = sum(1 for r in results if r.get('error') is not None)

    agreement_rate = (agreements / total_tests * 100) if total_tests > 0 else 0

    summary = {
        'total_tests': total_tests,
        'agreements': agreements,
        'disagreements': disagreements,
        'errors': errors,
        'agreement_rate': agreement_rate,
        'timestamp': datetime.now().isoformat(),
        'results': results
    }

    # Print summary
    print(f"\n{'='*80}")
    print(f"SHADOW MODE SUMMARY")
    print(f"{'='*80}")
    print(f"Total tests: {total_tests}")
    print(f"Agreements: {agreements}")
    print(f"Disagreements: {disagreements}")
    print(f"Errors: {errors}")
    print(f"Agreement rate: {agreement_rate:.1f}%")
    print(f"{'='*80}\n")

    # Validation criteria
    if agreement_rate >= 95:
        print("✅ SUCCESS: Agreement rate ≥95% - Solution 2 validated")
    elif agreement_rate >= 92:
        print("⚠️  CONDITIONAL: Agreement rate 92-95% - Deploy with monitoring")
    else:
        print("❌ FAILURE: Agreement rate <92% - Fall back to Solution 1")

    return summary


def main():
    """Main entry point for shadow mode testing."""
    parser = argparse.ArgumentParser(
        description='Shadow mode testing for Solution 2 validation'
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
        help='Enable verbose output'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='shadow_mode_results.json',
        help='Output file for results (default: shadow_mode_results.json)'
    )

    args = parser.parse_args()

    # Run shadow tests
    summary = run_all_shadow_tests(
        test_numbers=args.test,
        verbose=args.verbose
    )

    # Save results
    with open(args.output, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nResults saved to: {args.output}")

    # Exit with appropriate code
    if summary['agreement_rate'] >= 95:
        sys.exit(0)  # Success
    elif summary['agreement_rate'] >= 92:
        sys.exit(1)  # Conditional - needs review
    else:
        sys.exit(2)  # Failure - do not deploy


if __name__ == '__main__':
    # TODO: Before running, need to refactor test_option_b_full_solution_validation.py
    # to separate test data from test execution
    print("[SHADOW MODE] Template created successfully")
    print("[SHADOW MODE] Next steps:")
    print("1. Extract test solutions from test_option_b_full_solution_validation.py")
    print("2. Create TEST_DATA dictionary with (problem, solution, expected_verdict)")
    print("3. Implement full dual verification comparison")
    print("4. Add token usage tracking and latency comparison")
    print("\nTo complete implementation, refactor test data structure first.")

    # For now, just show the template is ready
    # main()
