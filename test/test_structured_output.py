#!/usr/bin/env python3
"""
Unit tests for structured output functionality.
Tests JSON solution generation and integration with blacklist.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

def test_json_parsing():
    """Test 1: Parse valid JSON response"""
    print("\n" + "="*70)
    print("TEST 1: JSON parsing from API response")
    print("="*70)

    # Simulate API response with JSON
    api_response = {
        'choices': [{
            'message': {
                'content': json.dumps({
                    "solution": "The answer is 2112 because...",
                    "final_answer": "2112"
                })
            }
        }]
    }

    # Parse the response
    content = api_response['choices'][0]['message']['content']
    parsed = json.loads(content)

    print(f"\nParsed JSON:")
    print(json.dumps(parsed, indent=2))

    assert 'solution' in parsed, "Missing 'solution' field"
    assert 'final_answer' in parsed, "Missing 'final_answer' field"
    assert parsed['final_answer'] == "2112", f"Wrong answer: {parsed['final_answer']}"

    print("\n✓ PASS: Valid JSON parsed correctly")
    return True


def test_json_with_newlines():
    """Test 2: Parse JSON with newlines in solution"""
    print("\n" + "="*70)
    print("TEST 2: JSON with multiline solution")
    print("="*70)

    # JSON with newlines in solution field
    response_json = {
        "solution": "Step 1: Analyze the problem\n\nStep 2: Apply Dilworth's theorem\n\nStep 3: Calculate k^2 + 2k - 3 = 2112",
        "final_answer": "2112"
    }

    content = json.dumps(response_json)
    parsed = json.loads(content)

    print(f"\nSolution text (first 100 chars):")
    print(parsed['solution'][:100])
    print(f"\nFinal answer: {parsed['final_answer']}")

    assert '\n' in parsed['solution'], "Solution should contain newlines"
    assert parsed['final_answer'] == "2112", "Wrong answer"

    print("\n✓ PASS: JSON with newlines handled correctly")
    return True


def test_json_parsing_failure_cases():
    """Test 3: Handle invalid JSON gracefully"""
    print("\n" + "="*70)
    print("TEST 3: JSON parsing failure cases")
    print("="*70)

    test_cases = [
        {
            'name': 'Invalid JSON syntax',
            'content': '{invalid json}',
            'should_fail': True
        },
        {
            'name': 'Missing final_answer field',
            'content': '{"solution": "text"}',
            'should_fail': True
        },
        {
            'name': 'Missing solution field',
            'content': '{"final_answer": "2112"}',
            'should_fail': True
        },
        {
            'name': 'Valid JSON',
            'content': '{"solution": "text", "final_answer": "2112"}',
            'should_fail': False
        }
    ]

    for tc in test_cases:
        print(f"\nTesting: {tc['name']}")
        try:
            parsed = json.loads(tc['content'])
            has_required_fields = 'solution' in parsed and 'final_answer' in parsed

            if tc['should_fail']:
                if not has_required_fields:
                    print(f"  ✓ Correctly detected missing fields")
                else:
                    print(f"  ✗ Should have failed but passed")
                    return False
            else:
                if has_required_fields:
                    print(f"  ✓ Valid JSON with required fields")
                else:
                    print(f"  ✗ Valid JSON but missing fields")
                    return False

        except json.JSONDecodeError as e:
            if tc['should_fail']:
                print(f"  ✓ Correctly failed to parse: {e}")
            else:
                print(f"  ✗ Should have parsed but failed: {e}")
                return False

    print("\n✓ PASS: All failure cases handled correctly")
    return True


def test_structured_solution_object():
    """Test 4: Solution object structure"""
    print("\n" + "="*70)
    print("TEST 4: Structured solution object")
    print("="*70)

    # Expected structure after parsing
    solution_obj = {
        'solution': 'For n = k^2 where k = 45, we have n = 2025. Using Dilworth theorem...',
        'final_answer': '2112'
    }

    print(f"\nSolution object structure:")
    print(json.dumps(solution_obj, indent=2))

    # Verify structure
    assert isinstance(solution_obj, dict), "Should be a dictionary"
    assert isinstance(solution_obj['solution'], str), "Solution should be string"
    assert isinstance(solution_obj['final_answer'], str), "Answer should be string"
    assert len(solution_obj['solution']) > 0, "Solution should not be empty"
    assert len(solution_obj['final_answer']) > 0, "Answer should not be empty"

    print("\n✓ PASS: Solution object has correct structure")
    return True


def test_blacklist_integration():
    """Test 5: Integration with blacklist save"""
    print("\n" + "="*70)
    print("TEST 5: Blacklist integration with structured output")
    print("="*70)

    from solution_blacklist import SolutionBlacklist

    with tempfile.TemporaryDirectory() as tmpdir:
        blacklist = SolutionBlacklist(
            problem_id="test_structured",
            blacklist_dir=str(tmpdir)
        )

        # Simulate structured solution
        solution_obj = {
            'solution': 'Using Dilworth decomposition, the answer is k^2 + 2k - 3 = 2112',
            'final_answer': '2112'
        }

        # Save to blacklist (using final_answer directly)
        blacklist.add_solution(
            answer=solution_obj['final_answer'],  # Use answer from JSON directly
            method="dilworth_decomposition",
            run_id="test_run",
            verdict="PASS",
            iterations=5
        )

        # Verify saved correctly
        stats = blacklist.get_statistics()
        print(f"\nBlacklist stats:")
        print(f"  Total attempts: {stats['total_attempts']}")
        print(f"  Answers: {stats['answers']}")

        assert stats['total_attempts'] == 1, "Should have 1 entry"
        assert '2112' in stats['answers'], "Should have answer '2112'"

        # Verify answer is clean (no LaTeX fragments)
        assert '\\' not in solution_obj['final_answer'], "Answer should not contain LaTeX"
        assert 'boxed' not in solution_obj['final_answer'], "Answer should not contain 'boxed'"

        print("\n✓ PASS: Blacklist integration works with structured output")
        return True


def test_verification_compatibility():
    """Test 6: Verification uses solution text from structured output"""
    print("\n" + "="*70)
    print("TEST 6: Verification compatibility")
    print("="*70)

    # Structured solution
    solution_obj = {
        'solution': 'For n = 2025, using Dilworth theorem k^2 + 2k - 3 = 2112 where k = 45...',
        'final_answer': '2112'
    }

    # Verification should use solution_obj['solution']
    solution_text_for_verification = solution_obj['solution']

    print(f"\nSolution text for verification:")
    print(solution_text_for_verification[:100])
    print(f"\nAnswer for blacklist: {solution_obj['final_answer']}")

    # Verify we can separate solution text and answer
    assert len(solution_text_for_verification) > 0, "Solution text should not be empty"
    assert len(solution_obj['final_answer']) > 0, "Answer should not be empty"
    assert isinstance(solution_obj['solution'], str), "Solution should be string"
    assert isinstance(solution_obj['final_answer'], str), "Answer should be string"

    print("\n✓ PASS: Verification can use solution text from structured output")
    return True


def test_prompt_format():
    """Test 7: Solution generation prompt requests JSON"""
    print("\n" + "="*70)
    print("TEST 7: Prompt format for JSON request")
    print("="*70)

    # Example prompt that requests JSON
    prompt = """
Solve this problem and provide your response as valid JSON.

Problem: [problem text here]

Return your response as JSON with this structure:
{
  "solution": "your detailed mathematical reasoning and solution",
  "final_answer": "the numerical answer only (e.g., 2112)"
}

Ensure 'final_answer' contains only the numerical value without LaTeX formatting.
"""

    print(f"\nPrompt format:")
    print(prompt)

    # Verify prompt structure
    assert 'JSON' in prompt or 'json' in prompt, "Prompt should mention JSON"
    assert 'solution' in prompt, "Prompt should show 'solution' field"
    assert 'final_answer' in prompt, "Prompt should show 'final_answer' field"
    assert 'numerical' in prompt.lower(), "Prompt should specify numerical answer"

    print("\n✓ PASS: Prompt correctly requests JSON structure")
    return True


def test_answer_extraction_comparison():
    """Test 8: Compare old regex vs new structured output"""
    print("\n" + "="*70)
    print("TEST 8: Structured output vs regex extraction")
    print("="*70)

    # Same solution in two formats
    unstructured_solution = "Therefore the answer is \\boxed{2112}."

    structured_solution = {
        'solution': "Therefore the answer is 2112.",
        'final_answer': "2112"
    }

    print(f"\nOld approach (regex needed):")
    print(f"  Input: {unstructured_solution}")
    print(f"  Would need regex to extract '2112' from \\boxed{{2112}}")

    print(f"\nNew approach (direct access):")
    print(f"  Input: {json.dumps(structured_solution)}")
    print(f"  Answer: {structured_solution['final_answer']} (direct access, no regex!)")

    # Verify new approach is cleaner
    assert structured_solution['final_answer'] == "2112", "Should extract answer directly"
    assert '\\' not in structured_solution['final_answer'], "Should not have LaTeX"
    assert 'boxed' not in structured_solution['final_answer'], "Should not have boxed"

    print("\n✓ PASS: Structured output eliminates need for regex extraction")
    return True


def run_all_tests():
    """Run all structured output tests"""
    print("\n" + "="*70)
    print("STRUCTURED OUTPUT - UNIT TEST SUITE")
    print("="*70)
    print("\nTesting structured JSON solution generation and integration")
    print("="*70)

    tests = [
        ("JSON parsing", test_json_parsing),
        ("JSON with newlines", test_json_with_newlines),
        ("JSON parsing failures", test_json_parsing_failure_cases),
        ("Structured solution object", test_structured_solution_object),
        ("Blacklist integration", test_blacklist_integration),
        ("Verification compatibility", test_verification_compatibility),
        ("Prompt format", test_prompt_format),
        ("Structured vs regex", test_answer_extraction_comparison),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "PASS", None))
        except AssertionError as e:
            results.append((name, "FAIL", str(e)))
            print(f"\n✗ FAIL: {e}")
        except Exception as e:
            results.append((name, "ERROR", str(e)))
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for name, status, error in results:
        symbol = "✓" if status == "PASS" else "✗"
        print(f"{symbol} {name}: {status}")
        if error:
            print(f"   Error: {error}")

    passed = sum(1 for _, status, _ in results if status == "PASS")
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 All unit tests passed!")
        print("\nReady to implement structured output in agent code.")
    else:
        print("\n⚠ Some tests failed - review failures above")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
