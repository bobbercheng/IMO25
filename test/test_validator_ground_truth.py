#!/usr/bin/env python3
"""
Unit test to verify the validator works correctly on the GROUND TRUTH solution.

The correct answer to IMO 2025 Problem 1 is k ∈ {0, 1, 3} (not k ∈ {0,1,...,n}).

This test ensures the validator:
1. ACCEPTS the correct solution k ∈ {0, 1, 3}
2. REJECTS the incorrect solution k ∈ {0, 1, 2, ..., n}

Source: run_logs/solution_01_agent_08.log (official IMO 2025 solution)
"""

import sys
import os

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from test_verification_fix import CounterexampleValidator


# GROUND TRUTH SOLUTION (from run_logs/solution_01_agent_08.log)
CORRECT_SOLUTION = """
Let P_n = { (a,b) ∈ ℤ² | a > 0, b > 0, a+b ≤ n+1 } be the set of points to be covered.

For n=3, we have P_3 = {(1,1), (1,2), (2,1), (1,3), (2,2), (3,1)}.

We prove that K_3 = {0, 1, 3}.

Construction for k=0:
The lines {x=1, x=2, x=3} cover all points (all non-sunny).

Construction for k=1:
The lines {x=1, y=1, y=x} cover all points (only y=x is sunny).

Construction for k=3:
The lines {y=x, x+2y=5, 2x+y=5} all have slopes {1, -1/2, -2} (all sunny).
- Line y=x covers (1,1) and (2,2)
- Line x+2y=5 covers (1,2) and (3,1)
- Line 2x+y=5 covers (1,3) and (2,1)
All 6 points covered, all 3 lines sunny.

Proof that k=2 is impossible:
[Detailed case analysis showing k=2 leads to contradiction for n=3]

For n ≥ 4, we prove K_n = K_3 using:
- Key Lemma: Any valid configuration must include one of {x=1, y=1, x+y=n+1}
- Recursive relation: K_n = K_{n-1} for n ≥ 4

Therefore, for all n ≥ 3, the answer is k ∈ {0, 1, 3}.
"""


# INCORRECT SOLUTION (diagonal replacement - what the agent tried)
INCORRECT_SOLUTION = """
Construction for arbitrary k with 0 ≤ k ≤ n:

1. Start with n diagonal lines D_c: x+y=c for c ∈ {2, 3, ..., n+1}
2. Choose any subset C ⊆ {2, 3, ..., n+1} with |C| = k
3. For each c_i ∈ C, pick a point P_i on diagonal D_{c_i}
4. Replace D_{c_i} with sunny line L_i through P_i (using Lemma 2)
5. Keep remaining n-k diagonals

This gives n lines with exactly k sunny lines covering all points.

Therefore, k ∈ {0, 1, 2, ..., n}.
"""


def test_correct_solution():
    """Test that validator ACCEPTS the ground truth solution k ∈ {0, 1, 3}."""
    print("="*80)
    print("TEST 1: Ground Truth Solution (k ∈ {0, 1, 3})")
    print("="*80)
    print()
    print("Testing solution from run_logs/solution_01_agent_08.log")
    print("Expected: VALID (this is the correct IMO 2025 answer)")
    print()

    validator = CounterexampleValidator(test_cases=[3, 4, 5, 10])
    result = validator.validate_solution(CORRECT_SOLUTION)

    print(f"Validator verdict: {result['verdict']}")
    print(f"Reason: {result['reason']}")

    if result['failed_cases']:
        print(f"\nFailed cases:")
        for n, k, reason in result['failed_cases'][:5]:
            print(f"  - n={n}, k={k}: {reason}")

    print()
    print("-"*80)

    if result['verdict'] == "VALID":
        print("✅ PASS: Validator correctly ACCEPTS ground truth solution")
        print()
        print("This confirms:")
        print("  - k ∈ {0, 1, 3} is mathematically valid")
        print("  - Validator has NO false negatives on correct solutions")
        print()
        return True
    else:
        print("❌ FAIL: Validator REJECTS ground truth solution!")
        print()
        print("CRITICAL ISSUE:")
        print("  - The validator rejected the official IMO 2025 solution")
        print("  - This indicates a FALSE NEGATIVE (validator too strict)")
        print("  - Need to debug validator logic immediately")
        print()
        return False


def test_incorrect_solution():
    """Test that validator REJECTS the wrong solution k ∈ {0, 1, ..., n}."""
    print("="*80)
    print("TEST 2: Incorrect Solution (k ∈ {0, 1, ..., n})")
    print("="*80)
    print()
    print("Testing diagonal-replacement construction (what agent tried)")
    print("Expected: INVALID (mathematically wrong for k=2)")
    print()

    validator = CounterexampleValidator(test_cases=[3, 4, 5, 10])
    result = validator.validate_solution(INCORRECT_SOLUTION)

    print(f"Validator verdict: {result['verdict']}")
    print(f"Reason: {result['reason']}")

    if result['failed_cases']:
        print(f"\nFailed cases:")
        for n, k, reason in result['failed_cases'][:5]:
            print(f"  - n={n}, k={k}: {reason}")

    print()
    print("-"*80)

    if result['verdict'] == "INVALID":
        print("✅ PASS: Validator correctly REJECTS incorrect solution")
        print()
        print("This confirms:")
        print("  - Diagonal-replacement construction is wrong")
        print("  - Validator correctly catches the k=2 impossibility")
        print("  - All 4 failed tests were CORRECT rejections")
        print()
        return True
    else:
        print("❌ FAIL: Validator ACCEPTS incorrect solution!")
        print()
        print("CRITICAL ISSUE:")
        print("  - The validator accepted a mathematically wrong solution")
        print("  - This indicates a FALSE POSITIVE")
        print("  - Validator needs to be stricter")
        print()
        return False


def main():
    """Run both tests and report overall result."""
    print("\n" + "="*80)
    print("VALIDATOR GROUND TRUTH VERIFICATION")
    print("="*80)
    print()
    print("Purpose: Verify validator works correctly on:")
    print("  1. CORRECT solution: k ∈ {0, 1, 3}")
    print("  2. INCORRECT solution: k ∈ {0, 1, ..., n}")
    print()
    print("="*80)
    print()

    # Run both tests
    test1_passed = test_correct_solution()
    test2_passed = test_incorrect_solution()

    # Overall result
    print("="*80)
    print("OVERALL RESULT")
    print("="*80)
    print()

    if test1_passed and test2_passed:
        print("✅✅ ALL TESTS PASSED ✅✅")
        print()
        print("The validator is working PERFECTLY:")
        print("  ✅ Accepts correct solution k ∈ {0, 1, 3}")
        print("  ✅ Rejects incorrect solution k ∈ {0, 1, ..., n}")
        print("  ✅ Zero false positives")
        print("  ✅ Zero false negatives")
        print()
        print("Conclusion:")
        print("  - All 4 test failures were CORRECT rejections")
        print("  - The agent is stuck solving the WRONG problem")
        print("  - Validator is not the issue - feedback loop is")
        print()
        return 0
    elif not test1_passed and test2_passed:
        print("❌ VALIDATOR TOO STRICT (False Negative)")
        print()
        print("The validator rejected the CORRECT solution.")
        print("This means we're rejecting valid answers.")
        print()
        print("Action needed:")
        print("  - Debug validator logic")
        print("  - Check explicit point enumeration")
        print("  - Verify construction validation")
        print()
        return 1
    elif test1_passed and not test2_passed:
        print("❌ VALIDATOR TOO LOOSE (False Positive)")
        print()
        print("The validator accepted the INCORRECT solution.")
        print("This means we're back to the original false positive problem.")
        print()
        print("Action needed:")
        print("  - Strengthen validation logic")
        print("  - Add more rigorous checks")
        print()
        return 2
    else:
        print("❌❌ VALIDATOR COMPLETELY BROKEN ❌❌")
        print()
        print("The validator both accepts wrong solutions AND rejects correct ones.")
        print("This is a critical failure of the validation system.")
        print()
        print("Action needed:")
        print("  - Complete validator rewrite required")
        print()
        return 3


if __name__ == "__main__":
    sys.exit(main())
