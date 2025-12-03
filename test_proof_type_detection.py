#!/usr/bin/env python3
"""
Test Proof-Type Detection

Validates the automatic proof-type detection system using existing RLAC solutions.
Tests coordinate geometry detection, synthetic geometry detection, and strategy selection.
"""

import json
import sys
import os

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from tier2_refinement import (
    uses_coordinate_geometry,
    uses_synthetic_geometry,
    select_tier2_strategy
)


def load_rlac_solution(memory_file):
    """Load RLAC solution from memory JSON file."""
    try:
        with open(memory_file, 'r') as f:
            memory = json.load(f)

        # Try different JSON structures
        if 'solution' in memory:
            return memory['solution']
        if 'final_solution' in memory:
            return memory['final_solution']
        if 'iterations' in memory and len(memory['iterations']) > 0:
            return memory['iterations'][-1].get('solution', '')

        return None
    except Exception as e:
        print(f"   ❌ Error loading {memory_file}: {e}")
        return None


def test_problem_2():
    """Test Problem 2 (known coordinate geometry proof)."""
    print("=" * 80)
    print("TEST 1: Problem 2 (Expected: Coordinate Geometry)")
    print("=" * 80)

    solution = load_rlac_solution('test_rlac_log/tier2_test_p2_optimized_rlac_solution.json')

    if not solution:
        print("   ⚠️  Could not load solution, skipping test")
        return False

    print(f"\nSolution length: {len(solution)} characters\n")

    # Test coordinate detection
    is_coordinate = uses_coordinate_geometry(solution)
    print(f"Coordinate geometry detected: {'✅ YES' if is_coordinate else '❌ NO'}")

    # Test synthetic detection
    is_synthetic = uses_synthetic_geometry(solution)
    print(f"Synthetic geometry detected: {'❌ YES (unexpected)' if is_synthetic else '✅ NO'}")

    # Test strategy selection
    strategy = select_tier2_strategy(solution, None)
    print(f"\nSelected strategy: {strategy['strategy_name']}")
    print(f"  - Verification reasoning: {strategy['verification_reasoning']}")
    print(f"  - Graduated verification: {strategy['use_graduated_verification']}")
    print(f"  - Max rounds: {strategy['max_rounds']}")
    print(f"  - Symbolic validation: {strategy['require_symbolic_validation']}")

    # Validate expectations
    expected_strategy = 'COORDINATE_STRICT'
    success = (
        is_coordinate and
        not is_synthetic and
        strategy['strategy_name'] == expected_strategy and
        strategy['verification_reasoning'] == 'high' and
        not strategy['use_graduated_verification'] and
        strategy['require_symbolic_validation']
    )

    if success:
        print(f"\n✅ TEST PASSED: Problem 2 correctly identified as {expected_strategy}")
    else:
        print(f"\n❌ TEST FAILED: Expected {expected_strategy}, got {strategy['strategy_name']}")

    return success


def test_sample_coordinate_proof():
    """Test with a sample coordinate geometry proof."""
    print("\n" + "=" * 80)
    print("TEST 2: Sample Coordinate Proof")
    print("=" * 80)

    sample_coordinate = """
    Let us place the origin at M = (0, 0) and N = (d, 0) on the x-axis.
    Circle Ω has center M = (0, 0) and radius r.
    Circle Γ has center N = (d, 0) and radius R.

    Point C is on MN with C = (-r, 0).
    Point D is on MN with D = (d + R, 0).

    Let A = (x_0, y_0) be one intersection point.
    Then |MA| = r gives x_0^2 + y_0^2 = r^2.
    And |NA| = R gives (x_0 - d)^2 + y_0^2 = R^2.

    The perpendicular bisector of AC passes through P.
    Using the slope formula: m = (y_0 - 0)/(x_0 - (-r)) = y_0/(x_0 + r).
    """

    is_coordinate = uses_coordinate_geometry(sample_coordinate)
    is_synthetic = uses_synthetic_geometry(sample_coordinate)
    strategy = select_tier2_strategy(sample_coordinate, None)

    print(f"\nCoordinate geometry detected: {'✅ YES' if is_coordinate else '❌ NO'}")
    print(f"Synthetic geometry detected: {'✅ NO' if not is_synthetic else '❌ YES (unexpected)'}")
    print(f"Selected strategy: {strategy['strategy_name']}")

    success = is_coordinate and not is_synthetic and strategy['strategy_name'] == 'COORDINATE_STRICT'

    if success:
        print(f"\n✅ TEST PASSED: Sample correctly identified as COORDINATE_STRICT")
    else:
        print(f"\n❌ TEST FAILED: Expected COORDINATE_STRICT, got {strategy['strategy_name']}")

    return success


def test_sample_synthetic_proof():
    """Test with a sample synthetic geometry proof."""
    print("\n" + "=" * 80)
    print("TEST 3: Sample Synthetic Proof")
    print("=" * 80)

    sample_synthetic = """
    Observe that \\angle BAC = \\angle BDC because they are inscribed angles
    subtending the same arc BC in the circle.

    By the power of a point theorem, PA \\cdot PB = PC \\cdot PD.

    Since triangles ABC and DEF are similar (by AA similarity),
    we have AB/DE = BC/EF = AC/DF.

    Note that points A, B, C, D are concyclic (lie on a circle).
    This follows from the inscribed angle theorem.

    By Ceva's theorem, the three cevians are concurrent.

    Consider the homothety centered at O with ratio k = AB/DE.
    This homothety maps triangle ABC to triangle DEF.
    """

    is_coordinate = uses_coordinate_geometry(sample_synthetic)
    is_synthetic = uses_synthetic_geometry(sample_synthetic)
    strategy = select_tier2_strategy(sample_synthetic, None)

    print(f"\nCoordinate geometry detected: {'✅ NO' if not is_coordinate else '❌ YES (unexpected)'}")
    print(f"Synthetic geometry detected: {'✅ YES' if is_synthetic else '❌ NO'}")
    print(f"Selected strategy: {strategy['strategy_name']}")

    success = not is_coordinate and is_synthetic and strategy['strategy_name'] == 'SYNTHETIC_GRADUATED'

    if success:
        print(f"\n✅ TEST PASSED: Sample correctly identified as SYNTHETIC_GRADUATED")
    else:
        print(f"\n❌ TEST FAILED: Expected SYNTHETIC_GRADUATED, got {strategy['strategy_name']}")

    return success


def test_mixed_proof():
    """Test with a mixed/ambiguous proof."""
    print("\n" + "=" * 80)
    print("TEST 4: Mixed/Unknown Proof")
    print("=" * 80)

    sample_mixed = """
    Consider the sequence a_n defined recursively.
    Let a_1 = 1 and a_{n+1} = 2a_n + 1 for n ≥ 1.

    By induction, we can prove that a_n = 2^n - 1 for all n ≥ 1.

    Base case: a_1 = 1 = 2^1 - 1. ✓

    Inductive step: Assume a_k = 2^k - 1.
    Then a_{k+1} = 2a_k + 1 = 2(2^k - 1) + 1 = 2^{k+1} - 2 + 1 = 2^{k+1} - 1. ✓

    Therefore, the formula holds for all n ≥ 1 by induction.
    """

    is_coordinate = uses_coordinate_geometry(sample_mixed)
    is_synthetic = uses_synthetic_geometry(sample_mixed)
    strategy = select_tier2_strategy(sample_mixed, None)

    print(f"\nCoordinate geometry detected: {'✅ NO' if not is_coordinate else '⚠️  YES (edge case)'}")
    print(f"Synthetic geometry detected: {'✅ NO' if not is_synthetic else '⚠️  YES (edge case)'}")
    print(f"Selected strategy: {strategy['strategy_name']}")

    success = strategy['strategy_name'] == 'BALANCED_FIXED'

    if success:
        print(f"\n✅ TEST PASSED: Mixed proof correctly identified as BALANCED_FIXED")
    else:
        print(f"\n❌ TEST FAILED: Expected BALANCED_FIXED, got {strategy['strategy_name']}")

    return success


def main():
    print("\n" + "=" * 80)
    print("PROOF-TYPE DETECTION TEST SUITE")
    print("=" * 80)
    print()
    print("This test validates the automatic proof-type detection system.")
    print("Expected outcomes:")
    print("  - Problem 2: COORDINATE_STRICT (high verification, no graduation)")
    print("  - Sample coordinate: COORDINATE_STRICT")
    print("  - Sample synthetic: SYNTHETIC_GRADUATED (medium verification, graduated)")
    print("  - Sample mixed: BALANCED_FIXED (medium verification, no graduation)")
    print()

    results = []

    # Run tests
    results.append(("Problem 2 (Real RLAC Solution)", test_problem_2()))
    results.append(("Sample Coordinate Proof", test_sample_coordinate_proof()))
    results.append(("Sample Synthetic Proof", test_sample_synthetic_proof()))
    results.append(("Mixed/Unknown Proof", test_mixed_proof()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")

    print()
    print(f"Overall: {passed}/{total} tests passed ({passed*100//total}%)")
    print("=" * 80)

    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
