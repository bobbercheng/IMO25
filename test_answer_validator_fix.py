#!/usr/bin/env python3
"""
Test script to validate answer_validator.py fix on N=5 logs

This script:
1. Tests the regex fix with actual LaTeX formats from logs
2. Reprocesses N=5 log files with fixed parser
3. Shows before/after comparison
4. Computes TRUE success rate
"""

import sys
import re
import json
from pathlib import Path

# Add code directory to path
sys.path.insert(0, str(Path(__file__).parent / 'code'))

from answer_validator import extract_final_answer, parse_answer_to_set, AnswerValidator

# Ground truth for IMO 2025 Problem 1
GROUND_TRUTH = {0, 1, 3}

def test_regex_fix():
    """Test that the regex fix handles LaTeX formats correctly"""
    print("="*80)
    print("UNIT TESTS: Regex Fix Validation")
    print("="*80)

    test_cases = [
        # LaTeX escaped braces (what LLMs generate)
        (r"\{0,\;1,\;3\}", {0, 1, 3}, "LaTeX escaped braces"),
        (r"\{0, 1, 3\}", {0, 1, 3}, "LaTeX escaped with spaces"),
        (r"\{0,1,3\}", {0, 1, 3}, "LaTeX escaped no spaces"),

        # Plain text (what we hoped for)
        (r"{0,1,3}", {0, 1, 3}, "Plain braces"),
        (r"{0, 1, 3}", {0, 1, 3}, "Plain with spaces"),

        # Mixed formats
        (r"k \in \{0,\;1,\;3\}", {0, 1, 3}, "k ∈ LaTeX set"),
        (r"k={0,1,3}", {0, 1, 3}, "k = set"),

        # Incomplete answers
        (r"\{0,1\}", {0, 1}, "Missing k=3"),
        (r"{0}", {0}, "Only k=0"),

        # From actual boxed answers
        (r"\boxed{\{0,\;1,\;3\}}", {0, 1, 3}, "Full boxed LaTeX"),
    ]

    passed = 0
    failed = 0

    for input_text, expected, description in test_cases:
        # Test extraction from boxed
        if r"\boxed" in input_text:
            extracted = extract_final_answer(input_text)
            parsed = parse_answer_to_set(extracted)
        else:
            parsed = parse_answer_to_set(input_text)

        if parsed == expected:
            print(f"✅ PASS: {description}")
            print(f"   Input:  {input_text}")
            print(f"   Parsed: {parsed}")
            passed += 1
        else:
            print(f"❌ FAIL: {description}")
            print(f"   Input:    {input_text}")
            print(f"   Expected: {expected}")
            print(f"   Got:      {parsed}")
            failed += 1

    print(f"\nUnit Test Results: {passed} passed, {failed} failed")
    return failed == 0


def extract_final_answer_from_log(log_path):
    """Extract final solution and answer from log file"""
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Find all "Corrected solution:" blocks
    pattern = r'Corrected solution:\s*\n"([^"]{500,}?)"\s*\n'
    matches = list(re.finditer(pattern, content, re.DOTALL))

    if not matches:
        return None, None

    # Get the last solution (final iteration)
    last_solution = matches[-1].group(1)

    # Extract answer using our fixed function
    claimed_answer = extract_final_answer(last_solution)

    return last_solution[:1000], claimed_answer  # Truncate solution for display


def reprocess_n5_logs():
    """Reprocess N=5 logs with fixed parser"""
    print("\n" + "="*80)
    print("REPROCESSING N=5 LOGS WITH FIXED PARSER")
    print("="*80)

    log_dir = Path('bfs_validation_n5')
    log_files = sorted(log_dir.glob('bfs_run*_20251222_194747.log'),
                      key=lambda x: int(re.search(r'run(\d+)_', str(x)).group(1)))

    results = []
    validator = AnswerValidator("imo2025_p1")

    for log_file in log_files:
        run_num = int(re.search(r'run(\d+)_', str(log_file)).group(1))

        solution, claimed_answer = extract_final_answer_from_log(str(log_file))

        if not claimed_answer:
            result = {
                'run': run_num,
                'extracted': None,
                'parsed': set(),
                'verdict': 'NO_ANSWER',
                'correct': False
            }
        else:
            parsed = parse_answer_to_set(claimed_answer)

            # Validate against ground truth
            if parsed == GROUND_TRUTH:
                verdict = 'CORRECT'
                correct = True
            elif parsed.issubset(GROUND_TRUTH) and len(parsed) > 0:
                verdict = 'INCOMPLETE'
                correct = False
            elif any(x not in GROUND_TRUTH for x in parsed if isinstance(x, int)):
                verdict = 'WRONG'
                correct = False
            else:
                verdict = 'UNPARSEABLE'
                correct = False

            result = {
                'run': run_num,
                'extracted': claimed_answer[:100],
                'parsed': parsed,
                'verdict': verdict,
                'correct': correct
            }

        results.append(result)

    # Print results table
    print("\nRun | Extracted Answer | Parsed Set | Verdict | Correct?")
    print("-" * 80)

    for r in results:
        extracted_display = (r['extracted'][:40] + '...') if r['extracted'] else 'N/A'
        parsed_display = str(r['parsed']) if r['parsed'] else 'set()'
        correct_icon = '✅' if r['correct'] else '❌'

        print(f"{r['run']:>3} | {extracted_display:<40} | {parsed_display:<12} | {r['verdict']:<10} | {correct_icon}")

    # Summary statistics
    total = len(results)
    correct_count = sum(1 for r in results if r['correct'])
    incomplete_count = sum(1 for r in results if r['verdict'] == 'INCOMPLETE')
    wrong_count = sum(1 for r in results if r['verdict'] == 'WRONG')

    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)

    print(f"\nTotal runs: {total}")
    print(f"CORRECT answers: {correct_count}/{total} ({correct_count/total*100:.1f}%)")
    print(f"INCOMPLETE answers: {incomplete_count}/{total}")
    print(f"WRONG answers: {wrong_count}/{total}")

    print(f"\n{'='*80}")
    print("COMPARISON: MEASURED vs ACTUAL")
    print("="*80)

    print("\n| Metric | Original (Buggy) | Fixed Parser | Difference |")
    print("|--------|-----------------|--------------|------------|")
    print(f"| Success Rate | 0/5 (0.0%) | {correct_count}/5 ({correct_count/total*100:.1f}%) | +{correct_count/total*100:.1f} pp |")
    print(f"| CORRECT Detected | 0 | {correct_count} | +{correct_count} |")

    if correct_count >= 2:
        print("\n✅ VALIDATION SUCCESSFUL!")
        print(f"   True success rate is {correct_count/total*100:.1f}%, NOT 0%")
        print("   The regex bug caused 100% false negative rate")
        print("\n   Recommendation: Continue to N=100 test with fixed parser")
    elif correct_count == 1:
        print("\n⚠️  PARTIAL SUCCESS")
        print(f"   Found {correct_count} correct answer (20%)")
        print("   Better than 0% but below 40% expectation")
    else:
        print("\n❌ NO IMPROVEMENT")
        print("   Fix did not find any correct answers")
        print("   Problem may be deeper than extraction bug")

    return results


def detailed_analysis_run1():
    """Detailed analysis of Run 1 (known to have correct answer)"""
    print("\n" + "="*80)
    print("DETAILED ANALYSIS: Run 1")
    print("="*80)

    log_path = 'bfs_validation_n5/bfs_run1_20251222_194747.log'

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Find the final boxed answer
    boxed_matches = list(re.finditer(r'\\boxed\{([^}]+\}?)\}', content))

    if boxed_matches:
        print(f"\nFound {len(boxed_matches)} boxed answers in log")

        # Show last 3
        print("\nLast 3 boxed answers:")
        for i, match in enumerate(boxed_matches[-3:], len(boxed_matches)-2):
            raw = match.group(0)
            print(f"\n  [{i}] Raw: {raw[:80]}")

            # Test extraction
            extracted = extract_final_answer(raw)
            parsed = parse_answer_to_set(extracted)

            print(f"      Extracted: {extracted[:60]}")
            print(f"      Parsed: {parsed}")
            print(f"      Correct? {'✅ YES' if parsed == GROUND_TRUTH else '❌ NO'}")

    # Also check the JSON file
    json_path = log_path.replace('.log', '.json')
    if Path(json_path).exists():
        with open(json_path, 'r') as f:
            data = json.load(f)

        if 'solution' in data:
            print("\n" + "-"*80)
            print("From JSON file:")
            solution = data['solution']

            extracted = extract_final_answer(solution)
            parsed = parse_answer_to_set(extracted)

            print(f"  Extracted: {extracted[:80]}")
            print(f"  Parsed: {parsed}")
            print(f"  Correct? {'✅ YES' if parsed == GROUND_TRUTH else '❌ NO'}")


def main():
    """Main test execution"""
    print("\n" + "="*80)
    print("ANSWER VALIDATOR FIX VALIDATION")
    print("Testing fix for LaTeX escaped braces bug")
    print("="*80)

    # Test 1: Unit tests
    unit_tests_passed = test_regex_fix()

    if not unit_tests_passed:
        print("\n❌ Unit tests FAILED - fix may not be working correctly")
        return False

    # Test 2: Detailed analysis of Run 1
    detailed_analysis_run1()

    # Test 3: Reprocess all N=5 logs
    results = reprocess_n5_logs()

    # Final verdict
    correct_count = sum(1 for r in results if r['correct'])

    print("\n" + "="*80)
    print("FINAL VERDICT")
    print("="*80)

    if correct_count >= 2:
        print(f"\n✅ SUCCESS: Fix validated - {correct_count}/5 runs have CORRECT answers")
        print("\nKey Findings:")
        print(f"  • True success rate: {correct_count}/5 ({correct_count/5*100:.1f}%)")
        print("  • Measured success rate (before fix): 0/5 (0%)")
        print(f"  • Measurement error: {correct_count/5*100:.1f} percentage points")
        print("\nConclusion:")
        print("  The regex bug caused complete measurement failure.")
        print("  The agent WAS finding correct answers.")
        print("  Recent changes did NOT make things worse.")
        print("\nRecommendation:")
        print("  ✅ Apply this fix permanently")
        print("  ✅ Add unit tests to prevent regression")
        print("  ✅ Proceed to N=100 test with confidence")
        return True
    else:
        print(f"\n⚠️  Unexpected: Only {correct_count}/5 correct answers found")
        print("\nThis doesn't match the expected pattern from log inspection.")
        print("Further investigation needed.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
