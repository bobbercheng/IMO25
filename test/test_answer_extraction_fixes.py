#!/usr/bin/env python3
"""
Comprehensive unit tests for answer extraction fixes.

Tests verify:
1. Data leakage removed from STRUCTURED_OUTPUT_SUFFIX
2. Answer extraction uses JSON field (not regex)
3. Regex fallback removed (fail-fast on missing JSON)
4. Validation catches LaTeX fragments and variable assignments
"""

import sys
import re
sys.path.insert(0, 'code')

# Import functions under test
from agent_gpt_oss import (
    STRUCTURED_OUTPUT_SUFFIX,
    extract_answer_simple,
    extract_solution,
    parse_structured_solution,
    get_solution_text
)

def test_data_leakage_removed():
    """Test 1: Verify '2112' is NOT in STRUCTURED_OUTPUT_SUFFIX"""
    print("=" * 70)
    print("TEST 1: Data Leakage Removed")
    print("=" * 70)

    if '2112' in STRUCTURED_OUTPUT_SUFFIX:
        print("✗ FAIL: Data leak detected - '2112' found in STRUCTURED_OUTPUT_SUFFIX")
        print(f"   Content: {STRUCTURED_OUTPUT_SUFFIX}")
        return False

    print("✓ PASS: No '2112' in STRUCTURED_OUTPUT_SUFFIX")

    # Verify example is now generic
    if 'like 42' in STRUCTURED_OUTPUT_SUFFIX or 'like 7' in STRUCTURED_OUTPUT_SUFFIX:
        print("✓ PASS: Generic example used instead (42 or similar)")
    else:
        print("⚠ WARNING: No generic example found, verify prompt manually")

    return True


def test_extract_solution_preserves_dict():
    """Test 2: extract_solution() returns full dict, not just text"""
    print("\n" + "=" * 70)
    print("TEST 2: extract_solution() Preserves Full Dict")
    print("=" * 70)

    # Test case 1: Structured output
    structured_input = {
        "solution": "The answer is 2112 because n=2025...",
        "final_answer": "2112"
    }

    result = extract_solution(structured_input)

    if not isinstance(result, dict):
        print(f"✗ FAIL: Expected dict, got {type(result).__name__}")
        return False

    if 'final_answer' not in result:
        print("✗ FAIL: 'final_answer' field lost!")
        print(f"   Result keys: {result.keys()}")
        return False

    if result['final_answer'] != "2112":
        print(f"✗ FAIL: Wrong final_answer: {result['final_answer']}")
        return False

    print("✓ PASS: extract_solution() returns full dict with final_answer preserved")
    print(f"   Input: {list(structured_input.keys())}")
    print(f"   Output: {list(result.keys())}")
    print(f"   final_answer: {result['final_answer']}")

    return True


def test_extract_answer_uses_json_field():
    """Test 3: extract_answer_simple() uses JSON field, not regex"""
    print("\n" + "=" * 70)
    print("TEST 3: extract_answer_simple() Uses JSON Field")
    print("=" * 70)

    # Test case: Dict with final_answer
    solution_dict = {
        "solution": "Let n = 2025. The minimum is 2n - 2 = 4048.",
        "final_answer": "4048"
    }

    extracted = extract_answer_simple(solution_dict)

    if extracted != "4048":
        print(f"✗ FAIL: Expected '4048', got '{extracted}'")
        return False

    print("✓ PASS: Extracted clean answer from JSON field")
    print(f"   Solution text contains 'n = 2025' (trap)")
    print(f"   Extracted answer: '{extracted}' (correct, from final_answer field)")

    return True


def test_regex_fallback_removed():
    """Test 4: Regex fallback removed - fails on string input"""
    print("\n" + "=" * 70)
    print("TEST 4: Regex Fallback Removed (Fail-Fast)")
    print("=" * 70)

    # Test case: String input (should raise ValueError now)
    unstructured_solution = "Therefore n = 2025 and the answer is 4048."

    try:
        result = extract_answer_simple(unstructured_solution)
        print(f"✗ FAIL: Should have raised ValueError, but returned: {result}")
        return False
    except ValueError as e:
        if "Expected structured output" in str(e):
            print("✓ PASS: Correctly rejects string input with informative error")
            print(f"   Error message: {str(e)[:100]}...")
            return True
        else:
            print(f"✗ FAIL: Raised ValueError but wrong message: {e}")
            return False
    except Exception as e:
        print(f"✗ FAIL: Raised unexpected exception: {type(e).__name__}: {e}")
        return False


def test_validation_catches_latex_fragments():
    """Test 5: Validation catches LaTeX fragments"""
    print("\n" + "=" * 70)
    print("TEST 5: Validation Catches LaTeX Fragments")
    print("=" * 70)

    test_cases = [
        # (description, final_answer, should_fail)
        ("LaTeX backslash", "\\frac{4048}{2}", True),
        ("LaTeX dollar sign", "$4048$", True),
        ("Too long (100 chars)", "n = 2025$) binary matrix where a $1$ indicates a covered unit square and a $0$ indicates uncovered", True),
        ("Clean number", "4048", False),
        ("Clean expression", "2n-2", False),
    ]

    all_passed = True

    for desc, answer, should_fail in test_cases:
        solution_dict = {
            "solution": "...",
            "final_answer": answer
        }

        try:
            result = extract_answer_simple(solution_dict)
            if should_fail:
                print(f"✗ FAIL: {desc} - Should reject '{answer[:50]}...' but got: {result}")
                all_passed = False
            else:
                print(f"✓ PASS: {desc} - Correctly accepted '{answer}'")
        except ValueError as e:
            if should_fail:
                print(f"✓ PASS: {desc} - Correctly rejected '{answer[:30]}...'")
            else:
                print(f"✗ FAIL: {desc} - Should accept '{answer}' but got error: {e}")
                all_passed = False

    return all_passed


def test_validation_catches_variable_assignments():
    """Test 6: Validation catches variable assignments like 'n = 2025'"""
    print("\n" + "=" * 70)
    print("TEST 6: Validation Catches Variable Assignments")
    print("=" * 70)

    test_cases = [
        ("Variable assignment", "n = 2025", True),
        ("Set notation (corrupted)", "U = \\{(i", True),
        ("Clean number", "2112", False),
        ("Expression", "2n-2", False),
    ]

    all_passed = True

    for desc, answer, should_fail in test_cases:
        solution_dict = {
            "solution": "...",
            "final_answer": answer
        }

        try:
            result = extract_answer_simple(solution_dict)
            if should_fail:
                print(f"✗ FAIL: {desc} - Should reject '{answer}' but got: {result}")
                all_passed = False
            else:
                print(f"✓ PASS: {desc} - Correctly accepted '{answer}'")
        except ValueError as e:
            if should_fail:
                print(f"✓ PASS: {desc} - Correctly rejected '{answer}'")
                print(f"   Reason: {str(e)[:80]}...")
            else:
                print(f"✗ FAIL: {desc} - Should accept '{answer}' but got error: {e}")
                all_passed = False

    return all_passed


def test_get_solution_text_compatibility():
    """Test 7: get_solution_text() handles both dict and string"""
    print("\n" + "=" * 70)
    print("TEST 7: get_solution_text() Backward Compatibility")
    print("=" * 70)

    # Test dict input
    dict_input = {
        "solution": "This is the solution text.",
        "final_answer": "4048"
    }

    text = get_solution_text(dict_input)
    if text != "This is the solution text.":
        print(f"✗ FAIL: Dict input - Expected 'This is the solution text.', got '{text}'")
        return False

    print("✓ PASS: get_solution_text() extracts text from dict")

    # Test string input (backward compatibility)
    string_input = "This is legacy string format."
    text = get_solution_text(string_input)
    if text != "This is legacy string format.":
        print(f"✗ FAIL: String input - Expected 'This is legacy string format.', got '{text}'")
        return False

    print("✓ PASS: get_solution_text() handles legacy string format")

    return True


def test_end_to_end_extraction():
    """Test 8: End-to-end extraction from structured JSON"""
    print("\n" + "=" * 70)
    print("TEST 8: End-to-End Extraction (Realistic Scenario)")
    print("=" * 70)

    # Simulate full pipeline:
    # 1. LLM returns JSON string
    # 2. parse_structured_solution() parses it
    # 3. extract_solution() preserves full dict
    # 4. extract_answer_simple() gets clean answer

    # Step 1: LLM output (JSON string)
    llm_output = """{
  "solution": "Let n = 2025. Each row must have exactly 1 uncovered square...Therefore the minimum is 2n - 2 = 4048.",
  "final_answer": "4048"
}"""

    # Step 2: Parse JSON
    parsed = parse_structured_solution(llm_output)
    if not parsed:
        print("✗ FAIL: JSON parsing failed")
        return False
    print(f"✓ Step 1: Parsed JSON - keys: {list(parsed.keys())}")

    # Step 3: Extract solution (should preserve dict)
    solution = extract_solution(parsed)
    if not isinstance(solution, dict):
        print(f"✗ FAIL: extract_solution() returned {type(solution).__name__}, not dict")
        return False
    print(f"✓ Step 2: extract_solution() preserved dict")

    # Step 4: Extract answer
    answer = extract_answer_simple(solution)
    if answer != "4048":
        print(f"✗ FAIL: Expected '4048', got '{answer}'")
        return False
    print(f"✓ Step 3: extract_answer_simple() returned clean answer: '{answer}'")

    print("\n✅ PASS: End-to-end extraction works correctly!")
    print("   - No LaTeX fragments extracted")
    print("   - No variable assignments extracted")
    print("   - Clean numerical answer from JSON field")

    return True


def run_all_tests():
    """Run all unit tests and report results"""
    print("=" * 70)
    print("ANSWER EXTRACTION FIXES - COMPREHENSIVE UNIT TESTS")
    print("=" * 70)
    print()

    tests = [
        ("Data leakage removed", test_data_leakage_removed),
        ("extract_solution() preserves dict", test_extract_solution_preserves_dict),
        ("extract_answer_simple() uses JSON", test_extract_answer_uses_json_field),
        ("Regex fallback removed", test_regex_fallback_removed),
        ("LaTeX fragment validation", test_validation_catches_latex_fragments),
        ("Variable assignment validation", test_validation_catches_variable_assignments),
        ("get_solution_text() compatibility", test_get_solution_text_compatibility),
        ("End-to-end extraction", test_end_to_end_extraction),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ EXCEPTION in {name}: {type(e).__name__}: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    print()
    print(f"Total: {passed_count}/{total_count} tests passed ({100*passed_count/total_count:.1f}%)")

    if passed_count == total_count:
        print("\n🎉 All tests passed! Fixes verified successfully.")
        return 0
    else:
        print(f"\n❌ {total_count - passed_count} test(s) failed. Please review and fix.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
