#!/usr/bin/env python3
"""
Test the proof problem detection fix for TIER 2.

This test validates that answer locking is properly disabled for "prove that"
problems, preventing false rejections during refinement.
"""

import sys
sys.path.insert(0, 'code')

from tier2_refinement import is_proof_problem, extract_boxed_answer

print("="*80)
print("PROOF PROBLEM DETECTION - VALIDATION TEST")
print("="*80)

# Test cases
test_cases = [
    {
        "name": "Problem 2 (actual IMO prove-that problem)",
        "problem": """
Let Ω and Γ be circles with centers M and N, respectively, such that the
radius of Ω is less than the radius of Γ. Suppose circles Ω and Γ intersect
at two distinct points A and B. Let MN intersects Ω at C and Γ at D, such
that points C, M, N, and D lie on the line in that order. Let P be the
circumcenter of triangle ACD. Line AP intersects Ω again at E≠A. Line AP
intersects Γ again at F≠A. Let H be the orthocenter of triangle PMN.

Prove that the line through H parallel to AP is tangent to the circumcircle
of triangle BEF.
        """,
        "expected_is_proof": True
    },
    {
        "name": "Computational problem (find value)",
        "problem": "Find the value of x such that x^2 + 2x + 1 = 0.",
        "expected_is_proof": False
    },
    {
        "name": "Show that problem",
        "problem": "Show that √2 is irrational.",
        "expected_is_proof": True
    },
    {
        "name": "Demonstrate that problem",
        "problem": "Demonstrate that the sum of angles in a triangle is 180°.",
        "expected_is_proof": True
    },
    {
        "name": "Determine problem",
        "problem": "Determine all positive integers n such that n^2 - n - 1 is prime.",
        "expected_is_proof": False
    }
]

print("\n### Test 1: is_proof_problem() Detection ###\n")

all_passed = True
for test in test_cases:
    result = is_proof_problem(test["problem"])
    passed = result == test["expected_is_proof"]
    all_passed = all_passed and passed

    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status} - {test['name']}")
    print(f"       Expected: {test['expected_is_proof']}, Got: {result}")

print("\n" + "="*80)
print("\n### Test 2: Answer Lock Behavior ###\n")

# Test answer extraction with proof problem
proof_solution = r"""
Some proof content...

\boxed{A,B,E,F\text{ are concyclic}}

More proof steps...

\boxed{\text{The line is tangent to }(BEF).}

Therefore the tangency holds.
"""

problem2_statement = """Prove that the line through H parallel to AP is
tangent to the circumcircle of triangle BEF."""

# For proof problem: should return None (disables lock)
answer_proof = extract_boxed_answer(proof_solution, problem2_statement)
print(f"Proof problem (with problem_statement):")
print(f"  Extracted answer: {answer_proof}")
print(f"  Answer lock: {'DISABLED' if answer_proof is None else 'ENABLED'}")

# For computational problem: should extract answer
computational_solution = r"The value is \boxed{42}."
computational_problem = "Find the value of x."

answer_computational = extract_boxed_answer(computational_solution, computational_problem)
print(f"\nComputational problem:")
print(f"  Extracted answer: {answer_computational}")
print(f"  Answer lock: {'DISABLED' if answer_computational is None else 'ENABLED'}")

# Verify correctness
test2_passed = (answer_proof is None) and (answer_computational == "42")
all_passed = all_passed and test2_passed

print("\n" + "="*80)
print("\n### Test 3: Problem 2 Specific Case ###\n")

# Simulate the exact scenario from the error
problem2 = """Prove that the line through H parallel to AP is tangent
to the circumcircle of triangle BEF."""

rlac_solution = r"""
Coordinate geometry proof...
\boxed{P=\Bigl(X_{c},-\dfrac{X_{c}(r+x_{0})}{y_{0}}\Bigr)}
...
The line is tangent to the circumcircle.
"""

tier2_refinement = r"""
Lemma: First we show that points A, B, E, F are concyclic.
\boxed{A,B,E,F\text{ are concyclic}}

Using this, we prove the main result...
\boxed{\text{The line through }H\text{ parallel to }AP\text{ is tangent to }(BEF).}

Therefore the required tangency holds.
"""

rlac_answer = extract_boxed_answer(rlac_solution, problem2)
tier2_answer = extract_boxed_answer(tier2_refinement, problem2)

print(f"RLAC locked answer:     {rlac_answer}")
print(f"TIER 2 refined answer:  {tier2_answer}")
print(f"Comparison result:      {'MATCH' if rlac_answer == tier2_answer else 'MISMATCH'}")
print(f"Would refinement pass?  {'YES ✓' if rlac_answer == tier2_answer else 'NO ✗'}")

# With the fix, both should be None (answer lock disabled)
test3_passed = (rlac_answer is None) and (tier2_answer is None)
all_passed = all_passed and test3_passed

if test3_passed:
    print("\n✓✓ CORRECT: Answer locking is DISABLED for proof problems!")
    print("✓✓ Refinements can now proceed without false rejections!")
else:
    print("\n✗✗ FAILED: Answer locking is still causing issues")

print("\n" + "="*80)
if all_passed:
    print("✓✓✓ ALL TESTS PASSED!")
    print("✓✓✓ Proof problem fix is working correctly!")
    print("\nNext step: Re-run Problem 2 TIER 2 test")
else:
    print("✗✗✗ SOME TESTS FAILED!")
    print("✗✗✗ Check the implementation")
print("="*80)

sys.exit(0 if all_passed else 1)
