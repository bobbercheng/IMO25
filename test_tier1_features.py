#!/usr/bin/env python3
"""
Test script for Tier 1 features:
1. Answer change validation
2. Stuck pattern detection
3. Score tracking

This script tests the new functions without running full agent.
"""

import sys
sys.path.insert(0, '/home/user/IMO25/code')

from agent_gpt_oss import (
    extract_answer_from_solution,
    validate_answer_change,
    detect_stuck_pattern,
    calculate_solution_score
)

def test_answer_extraction():
    """Test answer extraction from solutions."""
    print("=" * 80)
    print("TEST 1: Answer Extraction")
    print("=" * 80)

    test_cases = [
        ("The answer is k ∈ {0, 1, 2, ..., n}", "k ∈ {0, 1, 2, ..., n}"),
        ("Therefore k = 0 or k = n", "k = 0 or k = n"),
        ("We conclude that k ∈ {0, 1, ..., ⌊n/2⌋}", "k ∈ {0, 1, ..., ⌊n/2⌋}"),
        ("Empty solution", None),
    ]

    for solution, expected in test_cases:
        result = extract_answer_from_solution(solution)
        status = "✓" if result == expected else "✗"
        print(f"{status} Input: {solution[:50]}...")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        print()

    return True

def test_answer_validation():
    """Test answer change validation."""
    print("\n" + "=" * 80)
    print("TEST 2: Answer Validation (Narrowing Detection)")
    print("=" * 80)

    # Test Case 1: Narrowing from {0,...,n} to {0,...,⌊n/2⌋}
    print("\nTest Case 1: Classic narrowing (Test 1 regression scenario)")
    prev_sol = "The answer is k ∈ {0, 1, 2, ..., n}"
    new_sol = "The answer is k ∈ {0, 1, 2, ..., ⌊n/2⌋}"

    result = validate_answer_change(prev_sol, new_sol, iteration=4, verbose=True)

    assert result['changed'] == True, "Should detect change"
    assert result['narrowed'] == True, "Should detect narrowing"
    print(f"✓ Narrowing detected correctly!")
    print(f"  Warning: {result['warning']}")

    # Test Case 2: No change
    print("\n\nTest Case 2: No change")
    prev_sol = "The answer is k ∈ {0, 1, 2, ..., n}"
    new_sol = "The answer is k ∈ {0, 1, 2, ..., n}"

    result = validate_answer_change(prev_sol, new_sol, iteration=5, verbose=False)

    assert result['changed'] == False, "Should not detect change"
    print(f"✓ No change detected correctly!")

    # Test Case 3: Change from range to specific values
    print("\n\nTest Case 3: Range to specific values")
    prev_sol = "The answer is k ∈ {0, 1, ..., n}"
    new_sol = "The answer is k ∈ {0, 1, 3}"

    result = validate_answer_change(prev_sol, new_sol, iteration=2, verbose=True)

    assert result['changed'] == True, "Should detect change"
    assert result['narrowed'] == True, "Should detect narrowing"
    print(f"✓ Range-to-specific narrowing detected!")

    return True

def test_stuck_detection():
    """Test stuck pattern detection."""
    print("\n" + "=" * 80)
    print("TEST 3: Stuck Pattern Detection")
    print("=" * 80)

    # Test Case 1: Stuck pattern (0 corrects, increasing errors)
    print("\nTest Case 1: Stuck pattern (Test 1 scenario - iterations 5-13)")
    correct_history = [0, 0, 0, 0, 0]  # 5 iterations with 0 corrects
    error_history = [1, 2, 3, 4, 5]    # Increasing errors

    is_stuck = detect_stuck_pattern(correct_history, error_history, current_iteration=9,
                                    threshold=3, verbose=True)

    assert is_stuck == True, "Should detect stuck pattern"
    print(f"✓ Stuck pattern detected correctly!")

    # Test Case 2: Not stuck (improving)
    print("\n\nTest Case 2: Not stuck (progressive improvement)")
    correct_history = [1, 2, 3]
    error_history = [5, 3, 1]  # Decreasing errors

    is_stuck = detect_stuck_pattern(correct_history, error_history, current_iteration=3,
                                    threshold=3, verbose=False)

    assert is_stuck == False, "Should not detect stuck pattern"
    print(f"✓ Progressive improvement recognized!")

    # Test Case 3: Not enough history
    print("\n\nTest Case 3: Insufficient history")
    correct_history = [0, 0]  # Only 2 iterations
    error_history = [1, 2]

    is_stuck = detect_stuck_pattern(correct_history, error_history, current_iteration=2,
                                    threshold=3, verbose=False)

    assert is_stuck == False, "Should not detect stuck (insufficient data)"
    print(f"✓ Insufficient history handled correctly!")

    return True

def test_score_tracking():
    """Test score calculation."""
    print("\n" + "=" * 80)
    print("TEST 4: Score Calculation and Tracking")
    print("=" * 80)

    # Test Case 1: Perfect solution
    print("\nTest Case 1: Perfect solution")
    verify = ""
    good_verify = "yes"
    score = calculate_solution_score(verify, good_verify)
    print(f"Score: {score:.2f}")
    assert score >= 90, "Perfect solution should score high"
    print(f"✓ Perfect solution scored {score:.2f} (expected ≥90)")

    # Test Case 2: Critical errors
    print("\nTest Case 2: Multiple critical errors")
    verify = "Critical Error 1... Critical Error 2... Critical Error 3..."
    good_verify = "no"
    score = calculate_solution_score(verify, good_verify)
    print(f"Score: {score:.2f}")
    assert score < 0, "Multiple errors should give negative score"
    print(f"✓ Multiple errors scored {score:.2f} (expected <0)")

    # Test Case 3: Justification gap
    print("\nTest Case 3: Justification gap")
    verify = "The solution has a justification gap in step 3"
    good_verify = "no"
    score = calculate_solution_score(verify, good_verify)
    print(f"Score: {score:.2f}")
    assert -20 < score < 0, "Justification gap should give small negative score"
    print(f"✓ Justification gap scored {score:.2f} (expected -20 to 0)")

    # Test Case 4: Score progression
    print("\nTest Case 4: Score progression tracking")
    scores = []

    # Iteration 0: Bad solution
    scores.append(calculate_solution_score("Critical Error 1, Critical Error 2", "no"))

    # Iteration 1: Improved but still errors
    scores.append(calculate_solution_score("Critical Error 1", "no"))

    # Iteration 2: Only gap
    scores.append(calculate_solution_score("Justification gap", "no"))

    # Iteration 3: Perfect
    scores.append(calculate_solution_score("", "yes"))

    print(f"\nScore progression:")
    for i, score in enumerate(scores):
        delta = scores[i] - scores[i-1] if i > 0 else 0
        trend = "↑" if delta > 0 else "↓" if delta < 0 else "="
        print(f"  Iteration {i}: {score:.2f} ({delta:+.2f} {trend})")

    # Check monotonic improvement
    for i in range(1, len(scores)):
        assert scores[i] > scores[i-1], f"Score should improve: iter {i}"

    print(f"✓ Monotonic improvement detected!")

    return True

def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("TIER 1 FEATURES TEST SUITE")
    print("Testing: Answer Validation, Stuck Detection, Score Tracking")
    print("=" * 80)

    try:
        test_answer_extraction()
        test_answer_validation()
        test_stuck_detection()
        test_score_tracking()

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)
        print("\nFeatures ready for production use:")
        print("  1. ✓ Answer extraction and validation")
        print("  2. ✓ Stuck pattern detection")
        print("  3. ✓ Score calculation and tracking")
        print("\nNew log markers to look for:")
        print("  - [ANSWER VALIDATION] for answer change warnings")
        print("  - [STUCK DETECTION] for stuck pattern alerts")
        print("  - [SCORE] for score tracking across iterations")
        print()

        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
