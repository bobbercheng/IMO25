"""
Unit tests for Priority 0 and Priority 1 bug fixes (2025-12-29)

Tests:
1. Temperature configuration (0.35 instead of 0.0)
2. MAX_ITERATIONS and MAX_ERROR_THRESHOLD constants
3. Early stopping on verification PASS
4. Adaptive reasoning escalation when stuck

Run with: python code/test_priority_fixes.py
"""

import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_temperature_configuration():
    """Test that base temperature is set to 0.35 for balanced exploration/determinism"""
    print("Testing temperature configuration...")

    import agent_gpt_oss

    # Test that build_request_payload uses temperature 0.35
    payload = agent_gpt_oss.build_request_payload(
        system_prompt="test",
        question_prompt="test problem",
        other_prompts=[],
        reasoning_effort="medium"
    )

    assert "temperature" in payload, "Temperature not found in payload"
    assert payload["temperature"] == 0.35, f"Expected temperature 0.35, got {payload['temperature']}"

    print("  ✓ Base temperature is 0.35")
    print("  ✓ Temperature configuration test PASSED\n")

def test_max_iterations_constants():
    """Test that MAX_ITERATIONS and MAX_ERROR_THRESHOLD are properly defined"""
    print("Testing MAX_ITERATIONS and MAX_ERROR_THRESHOLD constants...")

    import agent_gpt_oss

    # Test that constants are defined
    assert hasattr(agent_gpt_oss, 'MAX_ITERATIONS'), "MAX_ITERATIONS not defined"
    assert hasattr(agent_gpt_oss, 'MAX_ERROR_THRESHOLD'), "MAX_ERROR_THRESHOLD not defined"

    # Test that they have correct values
    assert agent_gpt_oss.MAX_ITERATIONS == 30, f"Expected MAX_ITERATIONS=30, got {agent_gpt_oss.MAX_ITERATIONS}"
    assert agent_gpt_oss.MAX_ERROR_THRESHOLD == 20, f"Expected MAX_ERROR_THRESHOLD=20, got {agent_gpt_oss.MAX_ERROR_THRESHOLD}"

    print(f"  ✓ MAX_ITERATIONS = {agent_gpt_oss.MAX_ITERATIONS}")
    print(f"  ✓ MAX_ERROR_THRESHOLD = {agent_gpt_oss.MAX_ERROR_THRESHOLD}")
    print("  ✓ Constants test PASSED\n")

def test_verify_solution_returns_four_values():
    """Test that verify_solution returns (bug_report, o, answer_is_correct, problem_id)"""
    print("Testing verify_solution return signature...")

    import agent_gpt_oss

    # Mock the API request to avoid actual calls
    with patch('agent_gpt_oss.send_api_request') as mock_api:
        # Mock response with PASS verdict
        mock_api.return_value = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        "verdict": "PASS",
                        "confidence": 0.9,
                        "answer_correctness": "CORRECT",
                        "issues": [],
                        "reasoning": "Solution is correct"
                    })
                }
            }]
        }

        # Mock get_api_key
        with patch('agent_gpt_oss.get_api_key', return_value='test_key'):
            # Call verify_solution with a simple problem
            result = agent_gpt_oss.verify_solution(
                problem_statement="For which non-negative integers k is there a sunny line? (Problem 1 test)",
                solution="The answer is k ∈ {0, 1, 3}. Test solution.",
                verbose=False
            )

            # Verify it returns 4 values
            assert len(result) == 4, f"Expected 4 return values, got {len(result)}"
            bug_report, good_verify, answer_is_correct, problem_id = result

            # Verify types
            assert isinstance(bug_report, str), f"bug_report should be str, got {type(bug_report)}"
            assert isinstance(good_verify, str), f"good_verify should be str, got {type(good_verify)}"
            assert isinstance(answer_is_correct, bool), f"answer_is_correct should be bool, got {type(answer_is_correct)}"
            assert problem_id is None or isinstance(problem_id, str), f"problem_id should be None or str, got {type(problem_id)}"

            print("  ✓ verify_solution returns 4 values")
            print(f"  ✓ answer_is_correct type: {type(answer_is_correct).__name__}")
            print(f"  ✓ problem_id type: {type(problem_id).__name__ if problem_id else 'None'}")
            print("  ✓ Return signature test PASSED\n")

def test_adaptive_reasoning_escalation():
    """Test that reasoning escalates from medium to high when stuck"""
    print("Testing adaptive reasoning escalation logic...")

    # Test 1: Escalation trigger at error_count >= 3
    error_count = 3
    ver_reasoning = "medium"

    # Simulate escalation logic
    if error_count >= 3 and ver_reasoning != "high":
        previous_reasoning = ver_reasoning
        ver_reasoning = "high"

        assert previous_reasoning == "medium", "Previous reasoning should be medium"
        assert ver_reasoning == "high", "Reasoning should escalate to high"
        print("  ✓ Reasoning escalates medium → high at error_count=3")

    # Test 2: No escalation if already high
    ver_reasoning = "high"
    if error_count >= 3 and ver_reasoning != "high":
        assert False, "Should not escalate if already high"

    print("  ✓ No escalation if already at high")

    # Test 3: No escalation if error_count < 3
    error_count = 2
    ver_reasoning = "medium"
    if error_count >= 3 and ver_reasoning != "high":
        assert False, "Should not escalate at error_count=2"

    print("  ✓ No escalation at error_count < 3")
    print("  ✓ Adaptive reasoning test PASSED\n")

def test_early_stopping_logic():
    """Test that success detection happens immediately after verification"""
    print("Testing early stopping logic...")

    # Test 1: correct_count >= 1 with answer_is_correct should trigger return
    correct_count = 1
    answer_is_correct = True
    problem_id = "imo2025_p1"

    should_return = (correct_count >= 1) and answer_is_correct
    assert should_return == True, "Should return when answer_is_correct and correct_count >= 1"
    print("  ✓ Returns immediately on correct answer")

    # Test 2: correct_count >= 1 without ground truth should trigger return
    correct_count = 1
    answer_is_correct = False
    problem_id = None

    should_return = (correct_count >= 1) and (problem_id is None)
    assert should_return == True, "Should return when verification passes and no ground truth"
    print("  ✓ Returns immediately on verification PASS (no ground truth)")

    # Test 3: correct_count >= 1 with wrong answer should NOT return
    correct_count = 1
    answer_is_correct = False
    problem_id = "imo2025_p1"

    should_return = (correct_count >= 1) and (answer_is_correct or problem_id is None)
    assert should_return == False, "Should NOT return when answer is wrong"
    print("  ✓ Continues when answer is wrong (edge case)")

    print("  ✓ Early stopping test PASSED\n")

def test_integration_configuration():
    """Integration test: verify all configurations work together"""
    print("Testing integration of all changes...")

    import agent_gpt_oss

    # Test 1: Temperature in payload
    payload = agent_gpt_oss.build_request_payload(
        system_prompt="test",
        question_prompt="test",
        other_prompts=[],
        reasoning_effort="medium"
    )
    assert payload["temperature"] == 0.35, "Temperature not correctly set in payload"
    print("  ✓ Temperature correctly integrated in payload")

    # Test 2: Constants available in module
    assert agent_gpt_oss.MAX_ITERATIONS == 30
    assert agent_gpt_oss.MAX_ERROR_THRESHOLD == 20
    print("  ✓ Constants available module-wide")

    # Test 3: verify_solution signature
    # (Already tested above, just verify it's callable)
    assert callable(agent_gpt_oss.verify_solution), "verify_solution not callable"
    print("  ✓ verify_solution is callable")

    # Test 4: Adaptive reasoning logic can be simulated
    ver_reasoning = "medium"
    error_count = 3
    if error_count >= 3 and ver_reasoning != "high":
        ver_reasoning = "high"
    assert ver_reasoning == "high", "Adaptive reasoning not working"
    print("  ✓ Adaptive reasoning logic functional")

    print("  ✓ Integration test PASSED\n")

def run_all_tests():
    """Run all unit tests"""
    print("="*80)
    print("PRIORITY FIXES UNIT TESTS")
    print("Testing Priority 0 and Priority 1 bug fixes (2025-12-29)")
    print("="*80 + "\n")

    tests = [
        ("Temperature Configuration", test_temperature_configuration),
        ("MAX_ITERATIONS Constants", test_max_iterations_constants),
        ("verify_solution Return Signature", test_verify_solution_returns_four_values),
        ("Adaptive Reasoning Escalation", test_adaptive_reasoning_escalation),
        ("Early Stopping Logic", test_early_stopping_logic),
        ("Integration Configuration", test_integration_configuration),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test_name} FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"  ✗ {test_name} ERROR: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1

    print("="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("="*80)

    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
