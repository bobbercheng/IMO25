#!/usr/bin/env python3
"""
Diagnostic test for GPT-5 (o3) verification failures

This script tests the exact same test cases that gpt-oss-120b passed
but GPT-5 is failing on, to identify the root cause.
"""

import os
import sys
import json
import time

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Import test data
from test_data import get_test_data, IMO01_PROBLEM

# Import agent_oai functions
from agent_oai import verify_solution, extract_detailed_solution, build_request_payload


def test_extraction():
    """Test if extraction works on all test cases"""
    print("="*80)
    print("EXTRACTION DIAGNOSTICS")
    print("="*80)

    test_data = get_test_data()
    for num in sorted(test_data.keys()):
        test = test_data[num]
        solution = test['solution']
        extracted = extract_detailed_solution(solution)

        print(f"\nTest {num}: {test['test_name'][:50]}")
        print(f"  Solution length: {len(solution)} chars")
        print(f"  Extracted length: {len(extracted)} chars")

        if len(extracted) == 0:
            print(f"  ⚠️  WARNING: Empty extraction!")
            print(f"  This will cause GPT-5 to receive empty solution")
            # Show why it's empty
            has_marker = 'Detailed Solution' in solution
            print(f"  Has 'Detailed Solution' marker: {has_marker}")
        else:
            print(f"  ✓ Extraction OK")
            print(f"  Preview: {extracted[:80]}...")

    print("\n" + "="*80)


def test_single_verification(test_number=6):
    """Test verification on a single test case with detailed logging"""
    print("="*80)
    print(f"VERIFICATION DIAGNOSTIC - Test {test_number}")
    print("="*80)

    test_data = get_test_data()
    test = test_data.get(test_number)

    if not test:
        print(f"ERROR: Test {test_number} not found")
        return

    print(f"Test name: {test['test_name']}")
    print(f"Expected verdict: {test['expected_verdict']}")
    print(f"Solution length: {len(test['solution'])} chars")

    # Extract solution
    extracted = extract_detailed_solution(test['solution'])
    print(f"Extracted length: {len(extracted)} chars")

    if len(extracted) == 0:
        print("\n⚠️  CRITICAL: Extraction returned empty string!")
        print("This is the root cause of 'Please provide the statement to evaluate.'")
        print("\nProposed fix: Use full solution if marker not found")
        return

    print("\nCalling verify_solution()...")
    start_time = time.time()

    try:
        bug_report, verdict = verify_solution(
            IMO01_PROBLEM,
            test['solution'],
            verbose=True
        )

        elapsed = time.time() - start_time

        print(f"\n{'─'*80}")
        print("RESULT:")
        print(f"  Verdict: {verdict}")
        print(f"  Expected: {test['expected_verdict']}")
        print(f"  Elapsed: {elapsed:.1f}s")
        print(f"  Bug report length: {len(bug_report)} chars")
        print(f"\nBug report preview:")
        print(bug_report[:500])

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n✗ ERROR: {str(e)}")
        print(f"Elapsed: {elapsed:.1f}s")

        import traceback
        traceback.print_exc()


def compare_extraction_methods():
    """Compare GPT-5's extraction vs gpt-oss-120b's extraction"""
    print("="*80)
    print("EXTRACTION METHOD COMPARISON")
    print("="*80)

    def extract_gpt5_style(solution):
        """Agent_oai.py style - returns empty if marker not found"""
        idx = solution.find('Detailed Solution')
        if idx == -1:
            return ''
        return solution[idx + len('Detailed Solution'):].strip()

    def extract_gpt_oss_style(solution):
        """Agent_gpt_oss.py style - returns full solution if marker not found (BUGFIX)"""
        idx = solution.find('Detailed Solution')
        if idx == -1:
            # BUGFIX: Return full solution instead of empty string
            if len(solution) > 100:  # Sanity check
                return solution
            else:
                return ''
        return solution[idx + len('Detailed Solution'):].strip()

    test_data = get_test_data()

    print(f"\n{'Test':<6} {'GPT-5 Style':<15} {'GPT-OSS Style':<15} {'Issue?':<10}")
    print("─"*80)

    for num in sorted(test_data.keys()):
        test = test_data[num]
        sol = test['solution']

        gpt5_len = len(extract_gpt5_style(sol))
        gpt_oss_len = len(extract_gpt_oss_style(sol))

        has_issue = "⚠️  YES" if gpt5_len == 0 else "✓ No"

        print(f"{num:<6} {gpt5_len:<15} {gpt_oss_len:<15} {has_issue:<10}")

    print("\n" + "="*80)
    print("CONCLUSION:")
    print("  GPT-5 returns empty string when marker not found")
    print("  GPT-OSS returns full solution when marker not found (BUGFIX)")
    print("  This explains why GPT-5 fails on Test 6 but gpt-oss succeeds")
    print("="*80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Diagnose GPT-5 verification failures')
    parser.add_argument('--extraction', action='store_true', help='Test extraction on all cases')
    parser.add_argument('--compare', action='store_true', help='Compare extraction methods')
    parser.add_argument('--verify', type=int, help='Run verification on specific test number')
    parser.add_argument('--all', action='store_true', help='Run all diagnostics')

    args = parser.parse_args()

    if args.all or not any([args.extraction, args.compare, args.verify]):
        print("\nRunning all diagnostics...\n")
        test_extraction()
        print("\n")
        compare_extraction_methods()
        print("\n")
        test_single_verification(6)
    else:
        if args.extraction:
            test_extraction()
        if args.compare:
            compare_extraction_methods()
        if args.verify:
            test_single_verification(args.verify)
