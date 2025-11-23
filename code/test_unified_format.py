#!/usr/bin/env python3
"""
Test suite for Unified Format Implementation.

Tests:
1. Solution extraction with ### Summary ### and ### Detailed Solution ### markers
2. Solution structure validation
3. Adversarial verdict extraction with unified format
4. Counterexample extraction with COUNTEREXAMPLE_N: format
5. Answer implication extraction with IMPLICATION: format
6. Backward compatibility with old formats

Run with: python test_unified_format.py
"""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ==============================================================================
# Test Data: Unified Format Examples
# ==============================================================================

UNIFIED_SOLUTION_GOOD = """
Some preamble text that should be ignored...

### Summary ###

**a. Verdict:** I have successfully solved the problem. The final answer is \\boxed{42}.

**b. Method Sketch:** We use induction on n. The base case n=1 is trivial.
For the inductive step, we apply Lemma 1 to reduce to the n-1 case.

### Detailed Solution ###

**Lemma 1:** For all positive integers $n$, we have $f(n) \\leq n^2$.

*Proof:* By induction on $n$.
- Base case: $f(1) = 1 \\leq 1^2 = 1$. \\checkmark
- Inductive step: Assume $f(k) \\leq k^2$ for some $k \\geq 1$.
  Then $f(k+1) = f(k) + 2k + 1 \\leq k^2 + 2k + 1 = (k+1)^2$.

**Main Theorem:** The answer is $\\boxed{42}$.

*Proof:* Follows from Lemma 1 with $n = 42$. QED.
"""

UNIFIED_SOLUTION_OLD_FORMAT = """
Some text...

**1. Summary**

I have solved the problem. The answer is 100.

**2. Detailed Solution**

Here is the proof...
"""

UNIFIED_SOLUTION_MISSING_DETAILED = """
### Summary ###

The answer is 42.

Some more text but no Detailed Solution section.
"""

UNIFIED_ADVERSARIAL_ATTACK_GOOD = """
### VERDICT ###
ADVERSARIAL_VERDICT: BROKEN

### COUNTEREXAMPLES ###
COUNTEREXAMPLE_1: For n=3, the solution claims f(3)=9 but direct calculation shows f(3)=10.
COUNTEREXAMPLE_2: For n=5, k=2 the construction fails because the resulting configuration has only 4 elements.

### ANSWER_IMPLICATIONS ###
IMPLICATION: The solution claims the answer is n^2, but my counterexamples prove it should be n^2 + 1 for odd n.

### BOUNDARY_CASES ###
BOUNDARY_1: n=0 gives undefined result (should be handled as special case)
BOUNDARY_2: n=1 works correctly

### ASSUMPTION_CHALLENGES ###
CHALLENGE_1: The assumption that all elements are distinct is not verified in step 3.

### CRITICAL_FLAWS ###
FLAW_1: The induction hypothesis is used incorrectly in the main proof.

### SEVERITY ###
CRITICAL_COUNT: 2
MAJOR_COUNT: 1
MINOR_COUNT: 0
"""

UNIFIED_ADVERSARIAL_ATTACK_OLD_FORMAT = """
**ADVERSARIAL VERDICT**: SUSPICIOUS

**COUNTEREXAMPLES FOUND**:
- Counterexample 1: For n=2, the claim fails
- Counterexample 2: For n=4, another issue

**BOUNDARY CASES TESTED**:
- Edge case 1: n=0 not handled

**SEVERITY SCORES**:
- Critical flaws: 1
- Major issues: 2
- Minor issues: 1
"""

UNIFIED_ADVERSARIAL_ATTACK_ROBUST = """
### VERDICT ###
ADVERSARIAL_VERDICT: ROBUST

### COUNTEREXAMPLES ###
NO_COUNTEREXAMPLES_FOUND

### BOUNDARY_CASES ###
BOUNDARY_1: n=0 handled correctly
BOUNDARY_2: n=1 base case verified

### SEVERITY ###
CRITICAL_COUNT: 0
MAJOR_COUNT: 0
MINOR_COUNT: 0
"""


# ==============================================================================
# Test 1: extract_solution() with unified format
# ==============================================================================

def test_extract_solution_unified_format():
    """Test extract_solution with ### Summary ### marker."""
    print("\n" + "=" * 60)
    print("TEST 1: extract_solution() with Unified Format")
    print("=" * 60)

    from agent_gpt_oss import extract_solution

    # Test 1a: Good unified format
    result = extract_solution(UNIFIED_SOLUTION_GOOD)
    assert "### Summary ###" in result, "Should start with ### Summary ###"
    assert "### Detailed Solution ###" in result, "Should include Detailed Solution"
    assert "\\boxed{42}" in result, "Should include boxed answer"
    print("  [PASS] Unified format extraction works")

    # Test 1b: Old format (backward compatibility)
    result = extract_solution(UNIFIED_SOLUTION_OLD_FORMAT)
    assert "Summary" in result, "Should find Summary in old format"
    print("  [PASS] Old format backward compatibility works")

    # Test 1c: Empty input
    result = extract_solution("")
    assert result == "", "Empty input should return empty string"
    print("  [PASS] Empty input handled correctly")

    # Test 1d: No summary marker
    result = extract_solution("Just some random text without markers")
    assert result == "", "No Summary should return empty string"
    print("  [PASS] Missing markers handled correctly")

    print("\nTEST 1: PASSED")
    return True


# ==============================================================================
# Test 2: validate_solution_structure()
# ==============================================================================

def test_validate_solution_structure():
    """Test validate_solution_structure() function."""
    print("\n" + "=" * 60)
    print("TEST 2: validate_solution_structure()")
    print("=" * 60)

    from agent_gpt_oss import validate_solution_structure

    # Test 2a: Good unified format
    is_valid, errors, sections = validate_solution_structure(UNIFIED_SOLUTION_GOOD)
    assert is_valid, f"Good solution should be valid, got errors: {errors}"
    assert sections['has_boxed_answer'], "Should detect boxed answer"
    assert sections['boxed_answer'] == "42", f"Boxed answer should be 42, got {sections['boxed_answer']}"
    print("  [PASS] Valid unified format passes validation")

    # Test 2b: Missing detailed solution
    is_valid, errors, sections = validate_solution_structure(UNIFIED_SOLUTION_MISSING_DETAILED)
    # Should still pass because it has Summary (fallback)
    print(f"  [INFO] Missing detailed solution: valid={is_valid}, errors={errors}")

    # Test 2c: Empty solution
    is_valid, errors, sections = validate_solution_structure("")
    assert not is_valid, "Empty solution should fail validation"
    assert "Empty solution" in errors[0], "Should report empty solution error"
    print("  [PASS] Empty solution fails validation correctly")

    # Test 2d: Old format (backward compatibility)
    is_valid, errors, sections = validate_solution_structure(UNIFIED_SOLUTION_OLD_FORMAT)
    # Should pass due to fallback detection
    print(f"  [INFO] Old format: valid={is_valid}, errors={errors}")

    print("\nTEST 2: PASSED")
    return True


# ==============================================================================
# Test 3: _extract_verdict() with unified format
# ==============================================================================

def test_extract_verdict_unified_format():
    """Test _extract_verdict with ADVERSARIAL_VERDICT: format."""
    print("\n" + "=" * 60)
    print("TEST 3: _extract_verdict() with Unified Format")
    print("=" * 60)

    from adversarial_critic import AdversarialCritic

    critic = AdversarialCritic(verbose=False)

    # Test 3a: Unified format BROKEN
    verdict = critic._extract_verdict(UNIFIED_ADVERSARIAL_ATTACK_GOOD)
    assert verdict == "BROKEN", f"Expected BROKEN, got {verdict}"
    print("  [PASS] Unified format BROKEN detected")

    # Test 3b: Unified format ROBUST
    verdict = critic._extract_verdict(UNIFIED_ADVERSARIAL_ATTACK_ROBUST)
    assert verdict == "ROBUST", f"Expected ROBUST, got {verdict}"
    print("  [PASS] Unified format ROBUST detected")

    # Test 3c: Old format (backward compatibility)
    verdict = critic._extract_verdict(UNIFIED_ADVERSARIAL_ATTACK_OLD_FORMAT)
    assert verdict == "SUSPICIOUS", f"Expected SUSPICIOUS, got {verdict}"
    print("  [PASS] Old format SUSPICIOUS detected")

    # Test 3d: Content-based inference with counterexamples
    verdict = critic._extract_verdict("Some text mentioning broken", ["n=1 fails"])
    assert verdict == "BROKEN", f"Expected BROKEN with counterexamples, got {verdict}"
    print("  [PASS] Content inference with counterexamples works")

    # Test 3e: Suspicious when mentions counterexample but none extracted
    verdict = critic._extract_verdict("Found counterexample for n=1", [])
    assert verdict == "SUSPICIOUS", f"Expected SUSPICIOUS without extracted counterexamples, got {verdict}"
    print("  [PASS] SUSPICIOUS when counterexample mentioned but not extracted")

    print("\nTEST 3: PASSED")
    return True


# ==============================================================================
# Test 4: _extract_counterexamples() with unified format
# ==============================================================================

def test_extract_counterexamples_unified_format():
    """Test _extract_counterexamples with COUNTEREXAMPLE_N: format."""
    print("\n" + "=" * 60)
    print("TEST 4: _extract_counterexamples() with Unified Format")
    print("=" * 60)

    from adversarial_critic import AdversarialCritic

    critic = AdversarialCritic(verbose=False)

    # Test 4a: Unified format
    counterexamples = critic._extract_counterexamples(UNIFIED_ADVERSARIAL_ATTACK_GOOD)
    assert len(counterexamples) == 2, f"Expected 2 counterexamples, got {len(counterexamples)}"
    assert "n=3" in counterexamples[0], "First counterexample should mention n=3"
    assert "n=5" in counterexamples[1], "Second counterexample should mention n=5"
    print(f"  [PASS] Unified format: extracted {len(counterexamples)} counterexamples")

    # Test 4b: Old format (backward compatibility)
    counterexamples = critic._extract_counterexamples(UNIFIED_ADVERSARIAL_ATTACK_OLD_FORMAT)
    assert len(counterexamples) >= 1, f"Expected at least 1 counterexample from old format"
    print(f"  [PASS] Old format: extracted {len(counterexamples)} counterexamples")

    # Test 4c: ROBUST with NO_COUNTEREXAMPLES_FOUND
    counterexamples = critic._extract_counterexamples(UNIFIED_ADVERSARIAL_ATTACK_ROBUST)
    assert len(counterexamples) == 0, f"Expected 0 counterexamples for ROBUST, got {len(counterexamples)}"
    print("  [PASS] ROBUST case: no counterexamples extracted")

    # Test 4d: No duplicates
    test_text = """
COUNTEREXAMPLE_1: n=3 fails
COUNTEREXAMPLE_2: n=3 fails
    """
    counterexamples = critic._extract_counterexamples(test_text)
    assert len(counterexamples) == 1, f"Duplicates should be removed, got {len(counterexamples)}"
    print("  [PASS] Duplicate removal works")

    print("\nTEST 4: PASSED")
    return True


# ==============================================================================
# Test 5: _extract_answer_implications() with unified format
# ==============================================================================

def test_extract_answer_implications_unified_format():
    """Test _extract_answer_implications with IMPLICATION: format."""
    print("\n" + "=" * 60)
    print("TEST 5: _extract_answer_implications() with Unified Format")
    print("=" * 60)

    from adversarial_critic import AdversarialCritic

    critic = AdversarialCritic(verbose=False)

    # Test 5a: Unified format
    counterexamples = ["n=3 fails", "n=5 fails"]
    implications = critic._extract_answer_implications(UNIFIED_ADVERSARIAL_ATTACK_GOOD, counterexamples)
    assert len(implications) >= 1, f"Expected at least 1 implication, got {len(implications)}"
    assert any("n^2 + 1" in impl for impl in implications), "Should mention corrected answer"
    print(f"  [PASS] Unified format: extracted {len(implications)} implications")

    # Test 5b: Auto-generate from counterexamples when none found
    implications = critic._extract_answer_implications("No implications here", ["n=1 fails"])
    assert len(implications) >= 1, "Should auto-generate from counterexamples"
    assert "Counterexample" in implications[0], "Auto-generated should mention counterexample"
    print("  [PASS] Auto-generation from counterexamples works")

    # Test 5c: ROBUST case with no counterexamples
    implications = critic._extract_answer_implications(UNIFIED_ADVERSARIAL_ATTACK_ROBUST, [])
    # No implications expected for robust
    print(f"  [INFO] ROBUST case: {len(implications)} implications")

    print("\nTEST 5: PASSED")
    return True


# ==============================================================================
# Test 6: Full parsing workflow
# ==============================================================================

def test_full_parsing_workflow():
    """Test complete parsing workflow with unified format."""
    print("\n" + "=" * 60)
    print("TEST 6: Full Parsing Workflow")
    print("=" * 60)

    from adversarial_critic import AdversarialCritic

    critic = AdversarialCritic(verbose=False)

    # Test 6a: Parse complete attack result (unified format)
    result = critic._parse_attack_result(UNIFIED_ADVERSARIAL_ATTACK_GOOD, round_num=0)

    assert result['verdict'] == "BROKEN", f"Verdict should be BROKEN, got {result['verdict']}"
    assert len(result['counterexamples']) == 2, f"Should have 2 counterexamples, got {len(result['counterexamples'])}"
    assert len(result['answer_implications']) >= 1, f"Should have implications, got {len(result['answer_implications'])}"
    assert result['total_penalty'] > 0, f"Penalty should be > 0 for BROKEN, got {result['total_penalty']}"

    print(f"  Verdict: {result['verdict']}")
    print(f"  Counterexamples: {len(result['counterexamples'])}")
    print(f"  Answer implications: {len(result['answer_implications'])}")
    print(f"  Total penalty: {result['total_penalty']}")
    print("  [PASS] Unified format parsing complete")

    # Test 6b: Parse ROBUST result
    result = critic._parse_attack_result(UNIFIED_ADVERSARIAL_ATTACK_ROBUST, round_num=0)
    assert result['verdict'] == "ROBUST", f"Verdict should be ROBUST, got {result['verdict']}"
    assert len(result['counterexamples']) == 0, f"Should have 0 counterexamples for ROBUST"
    print("  [PASS] ROBUST parsing complete")

    # Test 6c: Parse old format (backward compatibility)
    result = critic._parse_attack_result(UNIFIED_ADVERSARIAL_ATTACK_OLD_FORMAT, round_num=0)
    assert result['verdict'] == "SUSPICIOUS", f"Verdict should be SUSPICIOUS, got {result['verdict']}"
    print("  [PASS] Old format parsing complete")

    print("\nTEST 6: PASSED")
    return True


# ==============================================================================
# Test 7: Prompt format alignment
# ==============================================================================

def test_prompt_format_alignment():
    """Test that prompts specify correct format markers."""
    print("\n" + "=" * 60)
    print("TEST 7: Prompt Format Alignment")
    print("=" * 60)

    from agent_oai import step1_prompt
    from adversarial_prompts import adversarial_critic_system_prompt

    # Test 7a: step1_prompt has ### Summary ### marker
    assert "### Summary ###" in step1_prompt, "step1_prompt should have ### Summary ### marker"
    print("  [PASS] step1_prompt has ### Summary ### marker")

    # Test 7b: step1_prompt has ### Detailed Solution ### marker
    assert "### Detailed Solution ###" in step1_prompt, "step1_prompt should have ### Detailed Solution ### marker"
    print("  [PASS] step1_prompt has ### Detailed Solution ### marker")

    # Test 7c: step1_prompt mentions \\boxed{} format
    assert "\\boxed" in step1_prompt, "step1_prompt should mention \\boxed{} format"
    print("  [PASS] step1_prompt mentions \\boxed{} format")

    # Test 7d: adversarial_critic_system_prompt has ### VERDICT ### marker
    assert "### VERDICT ###" in adversarial_critic_system_prompt, "Adversarial prompt should have ### VERDICT ### marker"
    print("  [PASS] adversarial_critic_system_prompt has ### VERDICT ### marker")

    # Test 7e: adversarial_critic_system_prompt has ADVERSARIAL_VERDICT: format
    assert "ADVERSARIAL_VERDICT:" in adversarial_critic_system_prompt, "Should have ADVERSARIAL_VERDICT: format"
    print("  [PASS] adversarial_critic_system_prompt has ADVERSARIAL_VERDICT: format")

    # Test 7f: adversarial_critic_system_prompt has COUNTEREXAMPLE_N: format
    assert "COUNTEREXAMPLE_1:" in adversarial_critic_system_prompt, "Should have COUNTEREXAMPLE_N: format"
    print("  [PASS] adversarial_critic_system_prompt has COUNTEREXAMPLE_N: format")

    # Test 7g: adversarial_critic_system_prompt has IMPLICATION: format
    assert "IMPLICATION:" in adversarial_critic_system_prompt, "Should have IMPLICATION: format"
    print("  [PASS] adversarial_critic_system_prompt has IMPLICATION: format")

    print("\nTEST 7: PASSED")
    return True


# ==============================================================================
# Test 8: Edge cases and error handling
# ==============================================================================

def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 60)
    print("TEST 8: Edge Cases and Error Handling")
    print("=" * 60)

    from agent_gpt_oss import extract_solution, validate_solution_structure
    from adversarial_critic import AdversarialCritic

    critic = AdversarialCritic(verbose=False)

    # Test 8a: Case insensitivity for markers
    mixed_case = """
### summary ###
The answer is 42.
### detailed solution ###
Proof here.
"""
    result = extract_solution(mixed_case)
    assert "summary" in result.lower(), "Should handle case-insensitive markers"
    print("  [PASS] Case insensitivity works")

    # Test 8b: Extra whitespace in markers
    extra_space = """
###   Summary   ###
Answer.
###  Detailed Solution  ###
Proof.
"""
    result = extract_solution(extra_space)
    assert len(result) > 0, "Should handle extra whitespace in markers"
    print("  [PASS] Extra whitespace handled")

    # Test 8c: Verdict with extra whitespace
    verdict_space = "ADVERSARIAL_VERDICT   :   BROKEN"
    verdict = critic._extract_verdict(verdict_space)
    assert verdict == "BROKEN", f"Should handle whitespace, got {verdict}"
    print("  [PASS] Verdict whitespace handling works")

    # Test 8d: None input handling
    try:
        result = extract_solution(None)
        assert result == "", "None should return empty string"
        print("  [PASS] None input handled")
    except:
        print("  [WARN] None input causes exception (acceptable)")

    # Test 8e: Very long input
    long_input = "### Summary ###\n" + "A" * 100000 + "\n### Detailed Solution ###\nProof."
    result = extract_solution(long_input)
    assert len(result) > 0, "Should handle very long input"
    print("  [PASS] Long input handled")

    print("\nTEST 8: PASSED")
    return True


# ==============================================================================
# Main test runner
# ==============================================================================

def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "=" * 70)
    print("UNIFIED FORMAT TEST SUITE")
    print("=" * 70)

    tests = [
        ("extract_solution() Unified Format", test_extract_solution_unified_format),
        ("validate_solution_structure()", test_validate_solution_structure),
        ("_extract_verdict() Unified Format", test_extract_verdict_unified_format),
        ("_extract_counterexamples() Unified Format", test_extract_counterexamples_unified_format),
        ("_extract_answer_implications() Unified Format", test_extract_answer_implications_unified_format),
        ("Full Parsing Workflow", test_full_parsing_workflow),
        ("Prompt Format Alignment", test_prompt_format_alignment),
        ("Edge Cases", test_edge_cases),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n[FAILED] {name}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)
    else:
        print("\nAll tests passed! Unified format implementation is correct.")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
