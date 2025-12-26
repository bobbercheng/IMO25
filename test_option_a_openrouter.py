#!/usr/bin/env python3
"""
Option A Constraint Testing with OpenRouter

Tests whether Option A style verification constraints improve accuracy
when used with OpenRouter's openai/gpt-oss-120b model.

Comparison:
- WITH constraints: Uses Option A constraints added to agent_gpt_oss.py
- WITHOUT constraints: Temporarily disable constraints for baseline

Test Cases: Test 1-6 from test_data.py
Model: openai/gpt-oss-120b via OpenRouter
Reasoning: HIGH effort to match Option A approach
"""

import os
import sys

# CRITICAL: Configure OpenRouter BEFORE importing agent_gpt_oss
# (agent_gpt_oss reads API_URL at module import time)
def configure_openrouter_env():
    """Configure environment variables BEFORE module imports"""
    # Check for OpenRouter API key
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("GPT_OSS_API_KEY")
    if not api_key:
        print("ERROR: No API key found")
        print("Please set one of:")
        print("  export OPENROUTER_API_KEY='sk-or-v1-...'")
        print("  export GPT_OSS_API_KEY='sk-or-v1-...'")
        sys.exit(1)

    # Set GPT_OSS configuration for OpenRouter
    os.environ["GPT_OSS_API_KEY"] = api_key
    os.environ["GPT_OSS_API_URL"] = "https://openrouter.ai/api/v1/chat/completions"
    os.environ["GPT_OSS_MODEL_NAME"] = "openrouter/openai/gpt-oss-120b"

    return api_key

# Configure BEFORE imports
api_key = configure_openrouter_env()

import json
import time
from datetime import datetime
from typing import Dict, List

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Import test data
from test_data import get_test_data, IMO01_PROBLEM

# Import agent_gpt_oss functions (AFTER environment is configured)
from agent_gpt_oss import verify_solution


def show_configuration():
    """Show current configuration"""
    print("="*80)
    print("OPENROUTER CONFIGURATION")
    print("="*80)
    print(f"API URL: {os.environ['GPT_OSS_API_URL']}")
    print(f"Model: {os.environ['GPT_OSS_MODEL_NAME']}")
    print(f"API Key: {api_key[:20]}... (truncated)")
    print("="*80)
    print()


def test_with_constraints(test_number: int, test_case: Dict, reasoning_effort: str = "high") -> Dict:
    """Test verification WITH Option A constraints (current implementation)"""
    print(f"\n{'='*80}")
    print(f"TEST {test_number} WITH CONSTRAINTS: {test_case['test_name']}")
    print(f"{'='*80}")
    print(f"Expected verdict: {test_case['expected_verdict']}")
    print(f"Reasoning effort: {reasoning_effort}")

    start_time = time.time()

    try:
        bug_report, verdict = verify_solution(
            IMO01_PROBLEM,
            test_case['solution'],
            verbose=True,
            reasoning_effort=reasoning_effort
        )

        elapsed = time.time() - start_time

        # Interpret verdict (agent_gpt_oss returns "yes"/"no")
        passed = (verdict == "yes")

        print(f"\n{'─'*80}")
        print(f"RESULT WITH CONSTRAINTS:")
        print(f"  Verdict: {verdict} ({'PASS' if passed else 'FAIL'})")
        print(f"  Expected: {test_case['expected_verdict']}")
        print(f"  Match: {'✓' if (passed and test_case['expected_verdict']=='PASS') or (not passed and test_case['expected_verdict']=='FAIL') else '✗'}")
        print(f"  Elapsed: {elapsed:.2f}s")
        print(f"  Bug report length: {len(bug_report)} chars")
        print(f"\nBug Report Preview:")
        print(bug_report[:500])
        if len(bug_report) > 500:
            print(f"... ({len(bug_report) - 500} more characters)")

        return {
            'test_number': test_number,
            'test_name': test_case['test_name'],
            'verdict': verdict,
            'passed': passed,
            'expected': test_case['expected_verdict'],
            'match': (passed and test_case['expected_verdict']=='PASS') or (not passed and test_case['expected_verdict']=='FAIL'),
            'elapsed_seconds': elapsed,
            'bug_report': bug_report,
            'bug_report_length': len(bug_report),
            'error': None
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n✗ ERROR: {str(e)}")
        print(f"Elapsed: {elapsed:.2f}s")

        import traceback
        traceback.print_exc()

        return {
            'test_number': test_number,
            'test_name': test_case['test_name'],
            'verdict': 'ERROR',
            'passed': False,
            'expected': test_case['expected_verdict'],
            'match': False,
            'elapsed_seconds': elapsed,
            'bug_report': '',
            'bug_report_length': 0,
            'error': str(e)
        }


def run_all_tests(reasoning_effort: str = "high"):
    """Run all test cases with Option A constraints"""
    print("="*80)
    print("OPTION A CONSTRAINT TESTING WITH OPENROUTER")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print(f"\nTesting WITH Option A constraints")
    print(f"Reasoning effort: {reasoning_effort}")
    print(f"Model: openai/gpt-oss-120b via OpenRouter")
    print()

    # Show configuration
    show_configuration()

    # Load test data
    test_data = get_test_data()

    # Run tests
    results = []
    for test_num in sorted(test_data.keys()):
        result = test_with_constraints(test_num, test_data[test_num], reasoning_effort)
        results.append(result)

        # Brief pause between tests
        time.sleep(2)

    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY - WITH OPTION A CONSTRAINTS")
    print(f"{'='*80}")

    total = len(results)
    errors = sum(1 for r in results if r['error'])
    completed = total - errors
    matches = sum(1 for r in results if r['match'] and not r['error'])

    print(f"Total tests: {total}")
    print(f"Completed: {completed}")
    print(f"Errors: {errors}")
    print(f"Verdict matches: {matches}/{completed} ({100*matches/max(completed,1):.1f}%)")

    if completed > 0:
        avg_time = sum(r['elapsed_seconds'] for r in results if not r['error']) / completed
        avg_length = sum(r['bug_report_length'] for r in results if not r['error']) / completed
        print(f"Average time: {avg_time:.1f}s")
        print(f"Average bug report length: {avg_length:.0f} chars (~{avg_length/4:.0f} tokens)")

    # Per-test breakdown
    print(f"\n{'─'*80}")
    print("Per-Test Results:")
    print(f"{'─'*80}")
    print(f"{'Test':<6} {'Name':<30} {'Verdict':<10} {'Expected':<10} {'Match':<6} {'Time':<8}")
    print(f"{'─'*80}")
    for r in results:
        status = "✓" if r['match'] and not r['error'] else "✗"
        verdict = "PASS" if r['passed'] else "FAIL"
        if r['error']:
            verdict = "ERROR"
        print(f"{status} {r['test_number']:<4} {r['test_name'][:28]:<30} {verdict:<10} {r['expected']:<10} {str(r['match']):<6} {r['elapsed_seconds']:<8.1f}s")

    # Per-category breakdown
    print(f"\n{'─'*80}")
    print("Per-Category Analysis:")
    print(f"{'─'*80}")

    # Group by expected verdict
    pass_tests = [r for r in results if r['expected'] == 'PASS']
    fail_tests = [r for r in results if r['expected'] == 'FAIL']

    if pass_tests:
        pass_correct = sum(1 for r in pass_tests if r['match'] and not r['error'])
        print(f"PASS tests (should accept): {pass_correct}/{len(pass_tests)} correct ({100*pass_correct/len(pass_tests):.1f}%)")
        # False negatives: marked as FAIL but should be PASS
        fn_rate = (len(pass_tests) - pass_correct) / len(pass_tests) if len(pass_tests) > 0 else 0
        print(f"  False Negative rate: {100*fn_rate:.1f}%")

    if fail_tests:
        fail_correct = sum(1 for r in fail_tests if r['match'] and not r['error'])
        print(f"FAIL tests (should reject): {fail_correct}/{len(fail_tests)} correct ({100*fail_correct/len(fail_tests):.1f}%)")
        # False positives: marked as PASS but should be FAIL
        fp_rate = (len(fail_tests) - fail_correct) / len(fail_tests) if len(fail_tests) > 0 else 0
        print(f"  False Positive rate: {100*fp_rate:.1f}%")

    # Save results
    output_file = f"optionA_openrouter_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_type': 'option_a_openrouter',
            'model': 'openrouter/openai/gpt-oss-120b',
            'reasoning_effort': reasoning_effort,
            'constraints': 'enabled',
            'total_tests': total,
            'completed': completed,
            'errors': errors,
            'matches': matches,
            'accuracy': matches / max(completed, 1),
            'avg_time_seconds': avg_time if completed > 0 else 0,
            'results': results
        }, f, indent=2)

    print(f"\n{'='*80}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*80}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test Option A constraints with OpenRouter')
    parser.add_argument('--reasoning', default='high', choices=['low', 'medium', 'high'],
                       help='Reasoning effort level (default: high to match Option A)')
    parser.add_argument('--test', type=int, help='Run single test number only')

    args = parser.parse_args()

    if args.test:
        # Run single test
        show_configuration()
        test_data = get_test_data()
        if args.test in test_data:
            result = test_with_constraints(args.test, test_data[args.test], args.reasoning)
            print(f"\nTest {args.test} complete")
            sys.exit(0 if result['match'] else 1)
        else:
            print(f"ERROR: Test {args.test} not found")
            print(f"Available tests: {sorted(test_data.keys())}")
            sys.exit(1)
    else:
        # Run all tests
        results = run_all_tests(args.reasoning)
        sys.exit(0)
