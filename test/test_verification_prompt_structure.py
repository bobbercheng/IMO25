#!/usr/bin/env python3
"""
Unit tests for Enhanced Verification Prompt Structure (Option A)

Tests that verification_system_prompt contains required construction checking rules
WITHOUT making expensive API calls.

This validates the prompt STRUCTURE, not the LLM's actual behavior.
For full end-to-end tests, use test_verification_construction_requirements.py with live API.
"""

import sys
import os

# Import prompts
sys.path.insert(0, os.path.dirname(__file__))
from agent_oai import verification_system_prompt


def test_prompt_contains_find_determine_requirements():
    """Test that prompt includes FIND/DETERMINE problem requirements."""

    required_sections = {
        "Section 4: FIND/DETERMINE Problems": [
            "FIND ALL",
            "DETERMINE ALL",
            "Small-Case Explicit Testing",
            "Impossibility Proofs",
            "Answer Completeness",
        ],
        "Section 5: Construction Verification": [
            "Construction Verification Requirements",
            "Point-by-Point Verification",
            "Impossibility Proof Rigor",
            "Construction Feasibility",
        ],
        "Completeness Checks": [
            "Critical Error if:",
            "Justification Gap if:",
            "complete answer",
            "INCOMPLETE",
        ],
        "Construction Checks": [
            "construction",
            "explicit",
            "verify",
            "algebraic substitution",
        ],
    }

    print("="*80)
    print("UNIT TEST: Verification Prompt Structure")
    print("="*80)

    all_passed = True

    for section_name, keywords in required_sections.items():
        print(f"\n{section_name}:")
        section_passed = True

        for keyword in keywords:
            if keyword.lower() in verification_system_prompt.lower():
                print(f"  ✓ Contains: '{keyword}'")
            else:
                print(f"  ✗ MISSING: '{keyword}'")
                section_passed = False
                all_passed = False

        if section_passed:
            print(f"  → {section_name}: PASS")
        else:
            print(f"  → {section_name}: FAIL")

    print("\n" + "="*80)

    if all_passed:
        print("✅ ALL TESTS PASSED - Prompt structure is correct")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Prompt is missing required sections")
        return 1


def test_prompt_has_examples():
    """Test that prompt includes concrete examples."""

    print("\n" + "="*80)
    print("UNIT TEST: Verification Prompt Examples")
    print("="*80)

    required_examples = {
        "Completeness Example": "Problem: \"Determine all k for n≥3\"",
        "Construction Example": "Solution claims: \"For n=3, k=3, use lines",
        "Critical Error Example": "Critical Error",
        "Justification Gap Example": "Justification Gap",
    }

    all_passed = True

    for example_name, example_text in required_examples.items():
        if example_text in verification_system_prompt:
            print(f"  ✓ Contains example: {example_name}")
        else:
            print(f"  ✗ MISSING example: {example_name}")
            all_passed = False

    print()

    if all_passed:
        print("✅ ALL EXAMPLES PRESENT")
        return 0
    else:
        print("❌ MISSING SOME EXAMPLES")
        return 1


def test_prompt_relaxation_notes():
    """Test that prompt includes 2025-12-23 relaxation notes."""

    print("\n" + "="*80)
    print("UNIT TEST: Verification Prompt Relaxation (2025-12-23)")
    print("="*80)

    # Check for relaxation notes
    relaxation_keywords = [
        "2025-12-23 RELAXED",
        "presentation issue",
        "not necessarily a mathematical error",
        "allow if answer is correct",
    ]

    all_passed = True

    for keyword in relaxation_keywords:
        if keyword in verification_system_prompt:
            print(f"  ✓ Contains relaxation note: '{keyword}'")
        else:
            print(f"  ✗ MISSING relaxation note: '{keyword}'")
            all_passed = False

    print()

    if all_passed:
        print("✅ RELAXATION NOTES PRESENT (prevents correct answers from failing)")
        return 0
    else:
        print("❌ MISSING RELAXATION NOTES")
        return 1


def test_prompt_length_and_quality():
    """Test basic prompt quality metrics."""

    print("\n" + "="*80)
    print("UNIT TEST: Verification Prompt Quality Metrics")
    print("="*80)

    prompt_length = len(verification_system_prompt)
    line_count = verification_system_prompt.count('\n')

    # Quality checks
    checks = {
        "Length ≥ 5000 chars": prompt_length >= 5000,
        "Line count ≥ 100": line_count >= 100,
        "Contains markdown formatting": '**' in verification_system_prompt,
        "Contains bullet points": '*' in verification_system_prompt,
        "No obvious typos (teh, recieve)": 'teh' not in verification_system_prompt and 'recieve' not in verification_system_prompt,
    }

    all_passed = True

    for check_name, result in checks.items():
        if result:
            print(f"  ✓ {check_name}")
        else:
            print(f"  ✗ {check_name}")
            all_passed = False

    print(f"\n  Prompt stats:")
    print(f"    - Length: {prompt_length} characters")
    print(f"    - Lines: {line_count}")

    print()

    if all_passed:
        print("✅ PROMPT QUALITY CHECKS PASSED")
        return 0
    else:
        print("❌ PROMPT QUALITY ISSUES FOUND")
        return 1


def main():
    """Run all structure tests."""

    print("\n" + "="*80)
    print("ENHANCED VERIFICATION PROMPT STRUCTURE TESTS")
    print("Option A: Construction Requirements for FIND Problems")
    print("="*80)
    print("\nNOTE: These tests validate prompt STRUCTURE only.")
    print("For end-to-end LLM behavior tests, use test_verification_construction_requirements.py")
    print()

    results = []

    # Run all tests
    results.append(test_prompt_contains_find_determine_requirements())
    results.append(test_prompt_has_examples())
    results.append(test_prompt_relaxation_notes())
    results.append(test_prompt_length_and_quality())

    # Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)

    passed = sum(1 for r in results if r == 0)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if all(r == 0 for r in results):
        print("\n✅ ALL STRUCTURE TESTS PASSED")
        print("\nThe verification_system_prompt contains all required sections for Option A:")
        print("  • Section 4: Completeness Requirements for FIND/DETERMINE Problems")
        print("  • Section 5: Construction Verification Requirements")
        print("  • Concrete examples for graders")
        print("  • 2025-12-23 relaxations to prevent false negatives")
        print("\nThis prompt should correctly validate IMO Problem 1 by checking:")
        print("  ✓ Constructions for k=0, k=1, k=3")
        print("  ✓ Impossibility proof for k=2")
        print("  ✓ Completeness of answer set")
        print("\nFor live LLM testing, configure API and run:")
        print("  python code/test_verification_construction_requirements.py")
        return 0
    else:
        print("\n❌ SOME STRUCTURE TESTS FAILED")
        print("Review verification_system_prompt in code/agent_oai.py")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
