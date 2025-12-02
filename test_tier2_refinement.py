"""
Unit tests for TIER 2 refinement module

Tests core functionality without requiring API calls.
"""

import sys
import os

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from tier2_refinement import (
    parse_verification_feedback,
    build_refinement_prompt,
    extract_boxed_answer,
    detect_refinement_loop
)


def test_parse_verification_feedback():
    """Test parsing verification feedback into structured issues."""
    print("\n" + "="*80)
    print("TEST 1: Parse Verification Feedback")
    print("="*80)

    # Test case 1: Structured feedback with List of Findings
    feedback1 = """
**Final Verdict:** The solution is **invalid** because it contains multiple
**Justification Gaps** – essential claims are made without any rigorous argument
or proof.

**List of Findings:**
* Location: "k=0 – always possible (all vertical lines)."
  * Issue: Justification Gap – the solution does not demonstrate that a set of
    n distinct vertical lines indeed covers every point (a,b)...

* Location: "k=2 – impossible for any n≥3 (proved in §1)."
  * Issue: Justification Gap – the alleged proof is absent; the impossibility
    claim is unsupported.

* Location: "Step 7: PA·PQ = PM²-r²"
  * Issue: Critical Error – the power-of-a-point relation is mis-stated
"""

    issues = parse_verification_feedback(feedback1)

    print(f"Found {len(issues)} issues:")
    for i, issue in enumerate(issues, 1):
        print(f"\n{i}. Type: {issue['type']}")
        print(f"   Location: {issue['location']}")
        print(f"   Description: {issue['description'][:80]}...")

    assert len(issues) == 3, f"Expected 3 issues, got {len(issues)}"
    assert issues[0]['type'] == 'JUSTIFICATION_GAP', "First issue should be gap"
    assert issues[2]['type'] == 'CRITICAL_ERROR', "Third issue should be error"

    print("\n✓ Test 1 PASSED: parse_verification_feedback")


def test_extract_boxed_answer():
    """Test extracting boxed answers from solutions."""
    print("\n" + "="*80)
    print("TEST 2: Extract Boxed Answer")
    print("="*80)

    test_cases = [
        ("The answer is \\boxed{42}.", "42"),
        ("We prove \\boxed{0,1,3} is correct.", "0,1,3"),
        ("Therefore boxed{x+y=5} holds.", "x+y=5"),
        ("No answer here", None),
    ]

    for solution, expected in test_cases:
        result = extract_boxed_answer(solution)
        print(f"Input: {solution[:50]}...")
        print(f"Expected: {expected}, Got: {result}")
        assert result == expected, f"Failed for: {solution}"

    print("\n✓ Test 2 PASSED: extract_boxed_answer")


def test_build_refinement_prompt():
    """Test building refinement prompts."""
    print("\n" + "="*80)
    print("TEST 3: Build Refinement Prompt")
    print("="*80)

    problem = "Find all integers n such that n² = n + 6"
    solution = "The answer is n = 3 or n = -2. By algebra."
    locked_answer = "3, -2"

    critical_errors = [{
        'type': 'CRITICAL_ERROR',
        'location': 'Step 3',
        'description': 'Missing factorization step'
    }]

    justification_gaps = [{
        'type': 'JUSTIFICATION_GAP',
        'location': 'Final claim',
        'description': 'No verification of negative solution'
    }]

    prompt = build_refinement_prompt(
        problem_statement=problem,
        current_solution=solution,
        locked_answer=locked_answer,
        critical_errors=critical_errors,
        justification_gaps=justification_gaps,
        round_num=0
    )

    print("Generated prompt length:", len(prompt))
    print("\nPrompt contains:")
    assert "PROOF REFINEMENT TASK" in prompt
    assert locked_answer in prompt
    assert "Critical Errors (must fix)" in prompt
    assert "Justification Gaps (need more detail)" in prompt
    assert "Step 3" in prompt
    assert "DO NOT re-solve the problem" in prompt

    print("- PROOF REFINEMENT TASK ✓")
    print("- Locked answer ✓")
    print("- Critical errors section ✓")
    print("- Justification gaps section ✓")
    print("- Instructions ✓")

    print("\n✓ Test 3 PASSED: build_refinement_prompt")


def test_detect_refinement_loop():
    """Test refinement loop detection."""
    print("\n" + "="*80)
    print("TEST 4: Detect Refinement Loop")
    print("="*80)

    # Test case 1: No loop (decreasing issues)
    history1 = [
        {'issues_count': 5},
        {'issues_count': 3},
        {'issues_count': 2},
    ]
    current_issues1 = [{'type': 'GAP'}]  # 1 issue

    is_loop1 = detect_refinement_loop(history1, current_issues1, window=3)
    print(f"Test 1 (decreasing): {[h['issues_count'] for h in history1]} + 1 = {is_loop1}")
    assert not is_loop1, "Should not detect loop when decreasing"

    # Test case 2: Stuck (same count)
    history2 = [
        {'issues_count': 3},
        {'issues_count': 3},
    ]
    current_issues2 = [{'type': 'GAP'}] * 3  # 3 issues

    is_loop2 = detect_refinement_loop(history2, current_issues2, window=3)
    print(f"Test 2 (stuck): {[h['issues_count'] for h in history2]} + 3 = {is_loop2}")
    assert is_loop2, "Should detect loop when count stays same"

    # Test case 3: Not enough history
    history3 = [{'issues_count': 5}]
    current_issues3 = [{'type': 'GAP'}] * 3

    is_loop3 = detect_refinement_loop(history3, current_issues3, window=3)
    print(f"Test 3 (short history): len={len(history3)} = {is_loop3}")
    assert not is_loop3, "Should not detect loop with insufficient history"

    print("\n✓ Test 4 PASSED: detect_refinement_loop")


def test_tier2_integration():
    """Test TIER 2 integration with mock functions."""
    print("\n" + "="*80)
    print("TEST 5: TIER 2 Integration (Mock)")
    print("="*80)

    from tier2_refinement import tier2_refinement_loop

    problem = "Prove that 2 + 2 = 4"
    rlac_solution = "By arithmetic, 2 + 2 = 4. QED."
    locked_answer = "4"

    # Mock verification function (simulates passing on round 2)
    verification_calls = [0]

    def mock_verify(prob, sol, reasoning):
        verification_calls[0] += 1
        if verification_calls[0] == 1:
            # First call: fail with gap
            return ("Justification Gap: Need to show 2+2=4 rigorously", "no")
        else:
            # Second call: pass
            return ("All steps verified", "yes")

    # Mock generation function
    def mock_generate(prompt, reasoning):
        return "By Peano axioms, 2 + 2 = 4. Full derivation:\n1. 2 = S(S(0))\n2. 4 = S(S(S(S(0))))\n3. Therefore 2+2=4. \\boxed{4}"

    # Run TIER 2 refinement
    refined, status, history = tier2_refinement_loop(
        problem_statement=problem,
        rlac_solution=rlac_solution,
        locked_answer=locked_answer,
        verify_solution_func=mock_verify,
        generate_solution_func=mock_generate,
        max_refinement_rounds=3,
        refinement_reasoning="high",
        verification_reasoning="high",
        verbose=True
    )

    print(f"\nFinal status: {status}")
    print(f"Refinement rounds: {len(history)}")

    assert status == "TIER_2_VERIFIED", f"Expected TIER_2_VERIFIED, got {status}"
    assert len(history) == 1, f"Expected 1 refinement round, got {len(history)}"
    assert "Peano axioms" in refined, "Refined solution should contain new content"

    print("\n✓ Test 5 PASSED: tier2_integration")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("TIER 2 REFINEMENT MODULE - UNIT TESTS")
    print("="*80)

    tests = [
        test_parse_verification_feedback,
        test_extract_boxed_answer,
        test_build_refinement_prompt,
        test_detect_refinement_loop,
        test_tier2_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n✗ TEST FAILED: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗ TEST ERROR: {test.__name__}")
            print(f"  Exception: {e}")
            failed += 1

    print("\n" + "="*80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("="*80)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
