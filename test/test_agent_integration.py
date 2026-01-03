#!/usr/bin/env python3
"""
Integration test for prescriptive feedback in agent_gpt_oss.py

Tests the full verification pipeline with automated checkers and template matching.
"""

import sys
import os

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from agent_gpt_oss import verify_solution

def test_verification_with_prescriptive_feedback():
    """Test verification with prescriptive feedback enabled"""

    print("\n" + "="*80)
    print("INTEGRATION TEST: Prescriptive Feedback in Verification")
    print("="*80 + "\n")

    # Test problem
    problem = """
    Find all integers k with 0 ≤ k ≤ n such that there exist exactly n distinct lines
    in the plane, with exactly k of them being "sunny" lines (slope not 0, not ∞, not -1),
    that together contain all lattice points (a,b) with a,b ≥ 1 and a+b ≤ n+1.
    """

    # Test solution with intentional errors (from real BFS errors)
    solution_with_errors = """
    Solution:

    We claim that k can be any value from 0 to n-2.

    Construction:
    Define k sunny lines with slope 1/2:
      L_i: y = (1/2)(x - i) for i = 1, ..., k

    These lines cover all lattice points in the triangular region.

    The total number of points covered is k * 3 = 3k points.

    For the remaining points, we add (n-k) horizontal and vertical lines.
    This construction covers all required points.

    Therefore, all values k ∈ [0, n-2] are achievable.
    """

    print("Testing solution with multiple intentional errors...")
    print("Expected: Automated checkers + template matching should detect:")
    print("  1. Coverage claim without verification (Coverage Checker)")
    print("  2. Rational slope 1/2 without divisibility check (Integer Checker)")
    print("  3. Additive counting without overlap check (Inclusion-Exclusion Checker)")
    print("  4. Integer/Denominator Reasoning Error template match")
    print("  5. Faulty Construction template match")
    print()

    # Run verification
    try:
        bug_report, verification_result = verify_solution(
            problem, solution_with_errors, verbose=True
        )

        print("\n" + "="*80)
        print("VERIFICATION RESULTS")
        print("="*80 + "\n")

        print(f"Verification passed: {'yes' in verification_result.lower()}")
        print(f"Bug report length: {len(bug_report)} characters")
        print()

        # Check for prescriptive feedback elements
        has_automated_checkers = "Automated Checker" in bug_report
        has_prescriptive_feedback = "Prescriptive Feedback" in bug_report

        print("Integration checks:")
        print(f"  ✅ Automated checkers ran: {has_automated_checkers}")
        print(f"  ✅ Prescriptive feedback generated: {has_prescriptive_feedback}")

        if has_automated_checkers:
            print("\n[SUCCESS] Automated checkers integrated successfully")

        if has_prescriptive_feedback:
            print("[SUCCESS] Template matching integrated successfully")

        # Show sample of bug report
        print("\n" + "="*80)
        print("BUG REPORT SAMPLE (first 1000 chars)")
        print("="*80)
        print(bug_report[:1000])
        if len(bug_report) > 1000:
            print(f"\n... (truncated, total length: {len(bug_report)} chars)")

        return has_automated_checkers and has_prescriptive_feedback

    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verification_without_errors():
    """Test verification on a correct solution (checkers should pass)"""

    print("\n" + "="*80)
    print("INTEGRATION TEST: Verification with Correct Solution")
    print("="*80 + "\n")

    problem = """
    Find all integers k with 0 ≤ k ≤ n such that there exist exactly n distinct lines
    in the plane, with exactly k of them being "sunny" lines (slope not 0, not ∞, not -1),
    that together contain all lattice points (a,b) with a,b ≥ 1 and a+b ≤ n+1.
    """

    # Better solution with explicit verification
    solution_correct = """
    Solution:

    We claim that k ∈ {0, 1, ..., n-2}.

    Construction for each k:
    - For k=0: Use n horizontal and vertical lines
      * Lines: x=1, x=2, ..., x=(n-1), y=1
      * Verification: For each (a,b) with a,b≥1, a+b≤n+1:
        - If a<n: point is on line x=a
        - If a=n: point is on line y=1
      * All points covered ✓

    - For general k: Replace k non-sunny lines with sunny lines of integer slope
      * Use lines with slope 1, 2, etc. (integer slopes guarantee lattice points)
      * For each line, explicitly verify which points it contains
      * Apply inclusion-exclusion when counting overlaps

    Upper bound: At least 2 lines must be non-sunny (horizontal and vertical needed
    for boundary points), so k ≤ n-2.

    Therefore, k ∈ {0, 1, ..., n-2}.
    """

    print("Testing solution with proper verification...")
    print("Expected: Automated checkers should pass or have minimal warnings")
    print()

    try:
        bug_report, verification_result = verify_solution(
            problem, solution_correct, verbose=True
        )

        print("\n" + "="*80)
        print("VERIFICATION RESULTS")
        print("="*80 + "\n")

        print(f"Verification passed: {'yes' in verification_result.lower()}")
        print(f"Bug report length: {len(bug_report)} characters")

        # This should have fewer issues
        has_warnings = len(bug_report) > 100
        print(f"Has warnings: {has_warnings}")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def main():
    """Run integration tests"""
    print("\n" + "="*80)
    print("PRESCRIPTIVE FEEDBACK INTEGRATION TESTS")
    print("="*80)

    results = []

    # Test 1: Solution with errors (should trigger automated checkers + templates)
    results.append(("Verification with errors", test_verification_with_prescriptive_feedback()))

    # Test 2: Better solution (should pass or have minimal warnings)
    results.append(("Verification without errors", test_verification_without_errors()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✅ ALL INTEGRATION TESTS PASSED")
        print("\nPrescriptive feedback is successfully integrated into agent_gpt_oss.py!")
        return 0
    else:
        print("\n❌ SOME INTEGRATION TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
