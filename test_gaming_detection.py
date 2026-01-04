#!/usr/bin/env python3
"""
Test gaming detection validation function.

Tests the validate_blacklist_consistency function to ensure it correctly
detects when a solution derives a blacklisted value in the text but returns
a different value in the final_answer field.
"""

import sys
sys.path.insert(0, 'code')

from agent_gpt_oss import validate_blacklist_consistency

def test_gaming_detected():
    """Test that gaming is detected when solution says 4048 but final_answer is 4047"""
    solution = {
        "solution": "The minimum number of tiles is 2n-2 = 2×2025-2 = 4048. Hence the answer is $4048$.",
        "final_answer": 4047
    }
    blacklist = [2025, 4048, 4050]

    is_valid, error_msg = validate_blacklist_consistency(solution, blacklist, verbose=True)

    print(f"\n{'='*80}")
    print(f"TEST: Gaming Detection (solution says 4048, final_answer is 4047)")
    print(f"{'='*80}")
    print(f"Result: {'PASS' if not is_valid else 'FAIL'}")
    print(f"Expected: Gaming should be DETECTED (is_valid=False)")
    print(f"Actual: is_valid={is_valid}")
    if error_msg:
        print(f"Error message: {error_msg[:200]}...")
    print(f"{'='*80}\n")

    assert not is_valid, "Gaming should be detected"
    assert "GAMING DETECTED" in error_msg, "Error message should mention gaming"
    assert "4048" in error_msg, "Error message should mention the blacklisted value"
    assert "4047" in error_msg, "Error message should mention the final_answer"

    return True

def test_consistent_solution():
    """Test that consistent solution passes validation"""
    solution = {
        "solution": "Using Dilworth's theorem with block decomposition, the answer is $2112$.",
        "final_answer": 2112
    }
    blacklist = [2025, 4048, 4050]

    is_valid, error_msg = validate_blacklist_consistency(solution, blacklist, verbose=True)

    print(f"\n{'='*80}")
    print(f"TEST: Consistent Solution (no blacklisted values)")
    print(f"{'='*80}")
    print(f"Result: {'PASS' if is_valid else 'FAIL'}")
    print(f"Expected: Should be VALID (is_valid=True)")
    print(f"Actual: is_valid={is_valid}")
    if error_msg:
        print(f"Error message: {error_msg}")
    print(f"{'='*80}\n")

    assert is_valid, "Consistent solution should be valid"
    assert error_msg is None, "No error message should be present"

    return True

def test_blacklisted_value_in_both():
    """Test that solution deriving blacklisted value in both text and field is caught"""
    solution = {
        "solution": "The answer is $4048$ by the 2n-2 formula.",
        "final_answer": 4048
    }
    blacklist = [2025, 4048, 4050]

    is_valid, error_msg = validate_blacklist_consistency(solution, blacklist, verbose=True)

    print(f"\n{'='*80}")
    print(f"TEST: Blacklisted Value in Both Fields")
    print(f"{'='*80}")
    print(f"Result: {'PASS' if not is_valid else 'FAIL'}")
    print(f"Expected: Should be INVALID (constraint violation)")
    print(f"Actual: is_valid={is_valid}")
    if error_msg:
        print(f"Error message: {error_msg[:200]}...")
    print(f"{'='*80}\n")

    assert not is_valid, "Blacklisted value in both fields should be invalid"
    assert "CONSTRAINT VIOLATION" in error_msg or "GAMING DETECTED" in error_msg

    return True

def test_edge_case_no_explicit_number():
    """Test solution that doesn't explicitly state the final number"""
    solution = {
        "solution": "By applying the construction method, we obtain the minimum value.",
        "final_answer": 2112
    }
    blacklist = [2025, 4048, 4050]

    is_valid, error_msg = validate_blacklist_consistency(solution, blacklist, verbose=True)

    print(f"\n{'='*80}")
    print(f"TEST: No Explicit Number in Solution Text")
    print(f"{'='*80}")
    print(f"Result: {'PASS' if is_valid else 'FAIL'}")
    print(f"Expected: Should be VALID (acceptable pattern)")
    print(f"Actual: is_valid={is_valid}")
    if error_msg:
        print(f"Error message: {error_msg}")
    print(f"{'='*80}\n")

    assert is_valid, "Solution without explicit number should be valid"

    return True

if __name__ == "__main__":
    print("\n" + "="*80)
    print("GAMING DETECTION VALIDATION TESTS")
    print("="*80 + "\n")

    tests = [
        ("Gaming Detection", test_gaming_detected),
        ("Consistent Solution", test_consistent_solution),
        ("Blacklisted in Both", test_blacklisted_value_in_both),
        ("No Explicit Number", test_edge_case_no_explicit_number),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name}: PASSED\n")
            passed += 1
        except AssertionError as e:
            print(f"❌ {name}: FAILED - {e}\n")
            failed += 1
        except Exception as e:
            print(f"💥 {name}: ERROR - {e}\n")
            failed += 1

    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*80 + "\n")

    sys.exit(0 if failed == 0 else 1)
