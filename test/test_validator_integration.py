#!/usr/bin/env python3
"""
Test answer validator integration with agent_gpt_oss.py
Simulates what would happen with Run 6 and Run 12 from retest
"""

import sys
sys.path.insert(0, '/home/user/IMO25/code')

from answer_validator import AnswerValidator, extract_final_answer

def test_run_6():
    """
    Run 6 claimed: k ∈ {0,1,2,...,n}
    Verification said: PASSED
    Expected with validator: WRONG (includes k=2 which is impossible)
    """
    print("="*80)
    print("TEST: Run 6 (WRONG answer that passed verification)")
    print("="*80)

    claimed_answer = "k ∈ {0, 1, 2, ..., n}"
    solution = f"""
### Summary ###

**a. Verdict:**
I have successfully solved the problem. The final answer is \\boxed{{k \\in \\{{0,1,2,...,n\\}}}}

For any n≥3, we can construct n lines such that exactly k of them are sunny
for any k in the range 0≤k≤n.
"""

    validator = AnswerValidator("imo2025_p1")
    result = validator.validate(claimed_answer, solution)

    print(f"\nClaimed Answer: {claimed_answer}")
    print(f"Validator Verdict: {result['verdict']}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Details: {result.get('details', {})}")

    expected = "WRONG"
    actual = result["verdict"]
    status = "✅ PASS" if actual == expected else f"❌ FAIL (expected {expected}, got {actual})"
    print(f"\n{status}")

    return actual == expected


def test_run_12():
    """
    Run 12 claimed: k ∈ {0,1}
    Verification said: PASSED
    Expected with validator: INCOMPLETE (missing k=3)
    """
    print("\n" + "="*80)
    print("TEST: Run 12 (INCOMPLETE answer that passed verification)")
    print("="*80)

    claimed_answer = "k ∈ {0, 1}"
    solution = f"""
### Summary ###

**a. Verdict:**
I have found a partial solution. The final answer is \\boxed{{k \\in \\{{0,1\\}}}}

For n≥3, I can prove that k=0 and k=1 are achievable.
For k=0: Use n diagonal lines x+y=constant (none sunny)
For k=1: Replace one diagonal with a sunny line
"""

    validator = AnswerValidator("imo2025_p1")
    result = validator.validate(claimed_answer, solution)

    print(f"\nClaimed Answer: {claimed_answer}")
    print(f"Validator Verdict: {result['verdict']}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Details: {result.get('details', {})}")

    expected = "INCOMPLETE"
    actual = result["verdict"]
    status = "✅ PASS" if actual == expected else f"❌ FAIL (expected {expected}, got {actual})"
    print(f"\n{status}")

    return actual == expected


def test_correct_answer():
    """
    Test that correct answer passes
    """
    print("\n" + "="*80)
    print("TEST: Correct answer k ∈ {0,1,3}")
    print("="*80)

    claimed_answer = "k ∈ {0, 1, 3}"
    solution = f"""
### Summary ###

**a. Verdict:**
I have successfully solved the problem. The final answer is \\boxed{{k \\in \\{{0,1,3\\}}}}
"""

    validator = AnswerValidator("imo2025_p1")
    result = validator.validate(claimed_answer, solution)

    print(f"\nClaimed Answer: {claimed_answer}")
    print(f"Validator Verdict: {result['verdict']}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"Details: {result.get('details', {})}")

    expected = "CORRECT"
    actual = result["verdict"]
    status = "✅ PASS" if actual == expected else f"❌ FAIL (expected {expected}, got {actual})"
    print(f"\n{status}")

    return actual == expected


def test_extract_final_answer():
    """
    Test the extract_final_answer function
    """
    print("\n" + "="*80)
    print("TEST: Extract Final Answer Function")
    print("="*80)

    test_cases = [
        ("The answer is \\boxed{k \\in \\{0,1,3\\}}", "k \\in \\{0,1,3\\}"),
        ("Therefore k ∈ {0, 1, 3}", "{0, 1, 3}"),
        ("k = 0 or k = 1 or k = 3", "k = 0 or k = 1 or k = 3"),
    ]

    passed = 0
    for solution, expected_substring in test_cases:
        result = extract_final_answer(solution)
        if expected_substring in result or result in expected_substring:
            print(f"✅ PASS: Extracted '{result}' from solution")
            passed += 1
        else:
            print(f"❌ FAIL: Extracted '{result}', expected substring '{expected_substring}'")

    print(f"\nExtraction tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


if __name__ == "__main__":
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + "  Answer Validator Integration Test".center(78) + "║")
    print("╚" + "═"*78 + "╝")
    print("\n")

    results = []

    # Run tests
    results.append(("Extract Answer", test_extract_final_answer()))
    results.append(("Run 6 (WRONG)", test_run_6()))
    results.append(("Run 12 (INCOMPLETE)", test_run_12()))
    results.append(("Correct Answer", test_correct_answer()))

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Validator integration working correctly!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Review integration")
        sys.exit(1)
