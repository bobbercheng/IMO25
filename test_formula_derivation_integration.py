#!/usr/bin/env python3
"""
Test script for formula derivation integration with BFS agent.

This script tests:
1. Formula derivation module can be imported
2. Verified cases database can be loaded
3. The solve_with_formula_guidance wrapper works correctly

Usage:
    # Test with OpenRouter (recommended, faster)
    export GPT_OSS_API_URL=https://openrouter.ai/api/v1/chat/completions
    export GPT_OSS_MODEL_NAME=openrouter/openai/gpt-oss-120b
    export GPT_OSS_API_KEY=sk-or-...

    python test_formula_derivation_integration.py

Expected outcome:
    - Formula derivation should find n+2k-3
    - Answer should be 2112
    - Confidence should be >= 0.8
"""

import os
import sys

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

def test_imports():
    """Test that all required modules can be imported."""
    print("="*80)
    print("TEST 1: Module Imports")
    print("="*80)

    try:
        from small_case_validator import SmallCaseValidator
        print("✓ small_case_validator imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import small_case_validator: {e}")
        return False

    try:
        from verified_cases_db import get_verified_cases, should_use_formula_derivation
        print("✓ verified_cases_db imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import verified_cases_db: {e}")
        return False

    print("✓ All imports successful\n")
    return True


def test_verified_cases():
    """Test that verified cases can be loaded for IMO Problem 6."""
    print("="*80)
    print("TEST 2: Verified Cases Database")
    print("="*80)

    from verified_cases_db import get_verified_cases, should_use_formula_derivation

    # Read problem statement
    problem_path = os.path.join(os.path.dirname(__file__), 'problems', 'imo06.txt')
    with open(problem_path, 'r') as f:
        problem_statement = f.read()

    print(f"Problem: {problem_statement[:100]}...")
    print()

    # Test keyword matching
    if should_use_formula_derivation(problem_statement):
        print("✓ Problem identified as formula-based")
    else:
        print("✗ Problem NOT identified as formula-based")
        return False

    # Test verified cases lookup
    cases = get_verified_cases(problem_statement, "imo06")

    if cases:
        print(f"✓ Found {len(cases)} verified cases:")
        for case in cases:
            print(f"  - n={case['n']}, k={case['k']}, tiles={case['tiles']}, source={case['source']}")
    else:
        print("✗ No verified cases found")
        return False

    print("✓ Verified cases loaded successfully\n")
    return True


def test_formula_derivation():
    """Test formula derivation on IMO Problem 6."""
    print("="*80)
    print("TEST 3: Formula Derivation")
    print("="*80)

    # Check API key
    api_key = os.getenv("GPT_OSS_API_KEY", "")
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not api_key:
        print("✗ No API key found (set GPT_OSS_API_KEY or OPENROUTER_API_KEY)")
        print("  Skipping formula derivation test")
        return None  # Skip test, not a failure

    print(f"✓ API key found: {api_key[:10]}...")

    # Import modules
    from small_case_validator import SmallCaseValidator
    from verified_cases_db import get_verified_cases
    from agent_gpt_oss import LLMClient

    # Read problem
    problem_path = os.path.join(os.path.dirname(__file__), 'problems', 'imo06.txt')
    with open(problem_path, 'r') as f:
        problem_statement = f.read()

    # Get verified cases
    cases = get_verified_cases(problem_statement, "imo06")

    # Create validator
    llm_client = LLMClient(api_key)
    validator = SmallCaseValidator(llm_client)

    # Attempt derivation with low reasoning (fast test)
    print("Attempting formula derivation with low reasoning...")
    result = validator.derive_formula(problem_statement, cases, reasoning_effort="low")

    if result:
        print(f"✓ Formula derived: {result['formula']}")
        print(f"  Answer: {result['answer']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Pattern: {result['pattern_analysis'][:100]}...")

        # Verify correctness
        if result['answer'] == 2112:
            print("✓ Answer is correct (2112)")
        else:
            print(f"✗ Answer is wrong (expected 2112, got {result['answer']})")
            return False

        if result['confidence'] >= 0.8:
            print(f"✓ Confidence is high ({result['confidence']} >= 0.8)")
        else:
            print(f"⚠ Confidence is moderate ({result['confidence']} < 0.8)")

        print("✓ Formula derivation successful\n")
        return True
    else:
        print("✗ Formula derivation failed")
        return False


def test_integration():
    """Test the full integration with agent_gpt_oss.py."""
    print("="*80)
    print("TEST 4: BFS Integration")
    print("="*80)

    # Check if we can import the solve_with_formula_guidance function
    try:
        from agent_gpt_oss import solve_with_formula_guidance
        print("✓ solve_with_formula_guidance imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import solve_with_formula_guidance: {e}")
        return False

    print("✓ Integration code is available")
    print("  To test full integration, run:")
    print("  python code/agent_gpt_oss.py problems/imo06.txt --use-formula-derivation --log test_integration.log")
    print()
    return True


if __name__ == "__main__":
    print("\n")
    print("="*80)
    print("Formula Derivation Integration Test Suite")
    print("="*80)
    print()

    results = []

    # Run tests
    results.append(("Module Imports", test_imports()))
    results.append(("Verified Cases", test_verified_cases()))
    results.append(("Formula Derivation", test_formula_derivation()))
    results.append(("BFS Integration", test_integration()))

    # Print summary
    print("\n")
    print("="*80)
    print("Test Summary")
    print("="*80)

    for name, result in results:
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "○ SKIP"
        print(f"{status:8} {name}")

    # Overall result
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)

    print()
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")

    if failed == 0:
        print("\n✓ All tests passed! Integration is ready.")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed. Please fix before proceeding.")
        sys.exit(1)
