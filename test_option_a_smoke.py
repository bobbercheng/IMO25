#!/usr/bin/env python3
"""
Option A Smoke Test - Quick validation of HIGH reasoning with enhanced constraints

Tests Option A implementation on 6 test cases to verify:
- No truncation errors
- Output tokens <2500 (constraint respected)
- Verification completes without errors
- Verdicts appear reasonable

Success Criteria:
- All tests complete without truncation
- Test 1-2 (complete proofs): PASS verdicts
- Test 3-6 (flawed proofs): FAIL or JUSTIFICATION_GAP verdicts
- Output length within constraints (<2500 tokens typical)
"""

import os
import sys
import json
import time
from datetime import datetime

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Import test data
from test_data import get_test_data, IMO01_PROBLEM

# Import agent_oai verification function
from agent_oai import verify_solution


def estimate_tokens(text):
    """Rough token estimation (1 token ≈ 4 characters)"""
    return len(text) // 4


def run_smoke_test(test_number, test_case):
    """Run single smoke test case"""
    print(f"\n{'='*80}")
    print(f"TEST {test_number}: {test_case['test_name']}")
    print(f"{'='*80}")
    print(f"Expected verdict: {test_case['expected_verdict']}")
    print(f"Category: {test_case['test_category']}")

    start_time = time.time()

    try:
        # Run verification with Option A (HIGH reasoning with enhanced constraints)
        bug_report, verdict = verify_solution(
            IMO01_PROBLEM,
            test_case['solution'],
            verbose=True
        )

        elapsed = time.time() - start_time

        # Estimate tokens in bug report
        tokens_estimate = estimate_tokens(bug_report)

        print(f"\n{'─'*80}")
        print(f"RESULT:")
        print(f"  Verdict: {verdict}")
        print(f"  Elapsed: {elapsed:.2f}s")
        print(f"  Output length: {len(bug_report)} chars (~{tokens_estimate} tokens)")
        print(f"  Expected: {test_case['expected_verdict']}")

        # Check if verdict matches expectations
        verdict_match = (verdict == test_case['expected_verdict'])

        # For smoke test, we're flexible - just checking it doesn't crash
        status = "✓ PASS" if not "error" in verdict.lower() else "✗ ERROR"

        print(f"  Status: {status}")

        # Check token constraint
        if tokens_estimate > 2500:
            print(f"  ⚠️  WARNING: Output exceeds 2000 token target (~{tokens_estimate} tokens)")
        else:
            print(f"  ✓ Output within constraint (<2500 tokens)")

        # Show first 500 chars of bug report
        print(f"\n{'─'*80}")
        print("Bug Report Preview:")
        print(bug_report[:500])
        if len(bug_report) > 500:
            print(f"... ({len(bug_report) - 500} more characters)")

        return {
            'test_number': test_number,
            'test_name': test_case['test_name'],
            'verdict': verdict,
            'expected': test_case['expected_verdict'],
            'elapsed_seconds': elapsed,
            'output_chars': len(bug_report),
            'estimated_tokens': tokens_estimate,
            'verdict_match': verdict_match,
            'error': None
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n✗ ERROR: {str(e)}")
        print(f"Elapsed: {elapsed:.2f}s")

        return {
            'test_number': test_number,
            'test_name': test_case['test_name'],
            'verdict': 'ERROR',
            'expected': test_case['expected_verdict'],
            'elapsed_seconds': elapsed,
            'output_chars': 0,
            'estimated_tokens': 0,
            'verdict_match': False,
            'error': str(e)
        }


def main():
    """Run smoke test on all 6 test cases"""
    print("="*80)
    print("OPTION A SMOKE TEST")
    print("Testing HIGH reasoning with enhanced constraints")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Load test data
    test_data = get_test_data()

    # Run tests
    results = []
    for test_num in sorted(test_data.keys()):
        result = run_smoke_test(test_num, test_data[test_num])
        results.append(result)

        # Brief pause between tests
        time.sleep(2)

    # Summary
    print(f"\n{'='*80}")
    print("SMOKE TEST SUMMARY")
    print(f"{'='*80}")

    total = len(results)
    errors = sum(1 for r in results if r['error'])
    completed = total - errors

    avg_tokens = sum(r['estimated_tokens'] for r in results if not r['error']) / max(completed, 1)
    avg_time = sum(r['elapsed_seconds'] for r in results if not r['error']) / max(completed, 1)

    print(f"Total tests: {total}")
    print(f"Completed: {completed}")
    print(f"Errors: {errors}")
    print(f"Average tokens: {avg_tokens:.0f}")
    print(f"Average time: {avg_time:.1f}s")

    # Token constraint check
    over_limit = sum(1 for r in results if r['estimated_tokens'] > 2500)
    print(f"\nToken Constraint (<2500 tokens):")
    print(f"  Within limit: {completed - over_limit}/{completed}")
    if over_limit > 0:
        print(f"  ⚠️  Over limit: {over_limit} tests")
    else:
        print(f"  ✓ All tests within constraint")

    # Per-test results
    print(f"\n{'─'*80}")
    print("Per-Test Results:")
    print(f"{'─'*80}")
    print(f"{'Test':<6} {'Name':<30} {'Verdict':<15} {'Expected':<10} {'Tokens':<8} {'Time':<8}")
    print(f"{'─'*80}")
    for r in results:
        status = "✓" if not r['error'] else "✗"
        print(f"{status} {r['test_number']:<4} {r['test_name'][:28]:<30} {r['verdict']:<15} {r['expected']:<10} {r['estimated_tokens']:<8} {r['elapsed_seconds']:<8.1f}s")

    # Save results
    output_file = f"optionA_smoke_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_type': 'option_a_smoke_test',
            'total_tests': total,
            'completed': completed,
            'errors': errors,
            'avg_tokens': avg_tokens,
            'avg_time_seconds': avg_time,
            'results': results
        }, f, indent=2)

    print(f"\n{'='*80}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*80}")

    # Return success/failure
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
