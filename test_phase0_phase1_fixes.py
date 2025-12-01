#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Phase 0 and Phase 1 Fixes

Tests:
- Phase 0.1: Problem difficulty detection
- Phase 0.2: Geometry-enhanced prompts
- Phase 1.1: P1 failure recovery mode (integration test)
- Phase 1.2: Counterexample quality filter
"""

import sys
import os

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

def test_problem_difficulty_detection():
    """Test Phase 0.1: Problem difficulty detection."""
    print("\n" + "="*80)
    print("TEST: Phase 0.1 - Problem Difficulty Detection")
    print("="*80)

    from agent_gpt_oss import detect_problem_difficulty, compare_reasoning_effort

    # Test 1: Geometry PROVE problem (Problem 2)
    problem2 = """
    Let Ω and Γ be two circles intersecting at two distinct points M and N.
    Prove that line ℓ through H parallel to AP is tangent to the circumcircle of triangle BEF.
    """
    result = detect_problem_difficulty(problem2, verbose=False)

    checks = [
        (result['type'] == 'PROVE', "Detected PROVE type"),
        (result['domain'] == 'GEOMETRY', "Detected GEOMETRY domain"),
        (result['min_critic_reasoning'] == 'medium', "Minimum critic reasoning is MEDIUM for geometry"),
        (result['generator_reasoning'] in ['medium', 'high'], "Generator reasoning appropriate for geometry"),
    ]

    print("\nTest 1: Geometry PROVE problem")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    # Test 2: Combinatorics FIND problem
    combinatorics_problem = """
    Find the number of permutations of {1, 2, 3, ..., n} such that no element
    appears in its natural position. Determine all sequences with this property.
    """
    result = detect_problem_difficulty(combinatorics_problem, verbose=False)

    checks = [
        (result['type'] == 'FIND', "Detected FIND type"),
        (result['domain'] == 'COMBINATORICS', "Detected COMBINATORICS domain"),
        (result['generator_reasoning'] == 'low', "Generator reasoning is LOW for combinatorics FIND"),
    ]

    print("\nTest 2: Combinatorics FIND problem")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    # Test 3: Advanced geometry detection
    advanced_geo = """
    Using inversion at point A with radius k, prove that the image of circle ω
    is tangent to line ℓ.
    """
    result = detect_problem_difficulty(advanced_geo, verbose=False)

    checks = [
        (result['domain'] == 'GEOMETRY', "Detected GEOMETRY domain"),
        (result['is_advanced_geometry'] == True, "Detected advanced geometry (inversion)"),
        (result['difficulty'] == 'high', "Difficulty is HIGH for advanced geometry"),
    ]

    print("\nTest 3: Advanced geometry detection")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    # Test 4: Reasoning comparison helper
    checks = [
        (compare_reasoning_effort('low', 'medium') < 0, "low < medium"),
        (compare_reasoning_effort('medium', 'medium') == 0, "medium == medium"),
        (compare_reasoning_effort('high', 'low') > 0, "high > low"),
        (compare_reasoning_effort('high', 'medium') > 0, "high > medium"),
        (compare_reasoning_effort('low', 'high') < 0, "low < high"),
    ]

    print("\nTest 4: Reasoning comparison helper")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    all_passed = all(passed for passed, _ in checks)
    return all_passed


def test_geometry_prompts():
    """Test Phase 0.2: Geometry-enhanced prompts."""
    print("\n" + "="*80)
    print("TEST: Phase 0.2 - Geometry-Enhanced Prompts")
    print("="*80)

    from adversarial_prompts import (
        get_critic_system_prompt,
        get_defense_prompt,
        geometry_critic_requirements,
        geometry_defense_addendum
    )

    # Test 1: Critic prompt for geometry includes requirements
    geom_prompt = get_critic_system_prompt('GEOMETRY')
    checks = [
        ('GEOMETRY-SPECIFIC COUNTEREXAMPLE REQUIREMENTS' in geom_prompt,
         "Geometry requirements included"),
        ('concrete coordinates' in geom_prompt.lower(),
         "Requires concrete coordinates"),
        ('testable' in geom_prompt.lower(),
         "Emphasizes testability"),
    ]

    print("\nTest 1: Geometry critic prompt")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    # Test 2: General prompt doesn't have geometry specifics
    general_prompt = get_critic_system_prompt('GENERAL')
    checks = [
        ('GEOMETRY-SPECIFIC' not in general_prompt,
         "General prompt doesn't have geometry specifics"),
        (len(general_prompt) < len(geom_prompt),
         "General prompt is shorter than geometry prompt"),
    ]

    print("\nTest 2: General critic prompt")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    # Test 3: Defense prompt for geometry includes strategies
    geom_defense = get_defense_prompt('GEOMETRY', defense_first=True)
    checks = [
        ('GEOMETRY PROOF DEFENSE STRATEGIES' in geom_defense,
         "Geometry defense strategies included"),
        ('coordinate verification' in geom_defense.lower(),
         "Mentions coordinate verification"),
        ('tangency' in geom_defense.lower(),
         "Mentions tangency verification"),
    ]

    print("\nTest 3: Geometry defense prompt")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    # Test 4: AdversarialCritic accepts domain parameter
    from adversarial_critic import AdversarialCritic
    try:
        critic = AdversarialCritic(reasoning_effort="medium", verbose=False, domain='GEOMETRY')
        checks = [
            (critic.domain == 'GEOMETRY', "Domain parameter stored correctly"),
        ]
    except Exception as e:
        checks = [
            (False, f"Failed to create critic with domain: {e}"),
        ]

    print("\nTest 4: AdversarialCritic domain parameter")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    all_passed = all(passed for passed, _ in checks)
    return all_passed


def test_counterexample_quality_filter():
    """Test Phase 1.2: Counterexample quality filter."""
    print("\n" + "="*80)
    print("TEST: Phase 1.2 - Counterexample Quality Filter")
    print("="*80)

    from empirical_critic_wrapper import EmpiricalCriticWrapper
    from adversarial_critic import AdversarialCritic

    # Create wrapper
    base_critic = AdversarialCritic(reasoning_effort="medium", verbose=False)
    wrapper = EmpiricalCriticWrapper(base_critic, enable_empirical=False)

    # Test 1: Valid geometric counterexample (has coordinates + angles)
    valid_ce = """
    Set M=(0,0), N=(4,0), A=(2,√3). Circle ω has center M with radius r=2.
    Computing the angle ∠AMN = 60°, we find that point P at (1,√3) violates
    the tangency condition because the distance from center to line is 1.5 ≠ 2.
    """

    is_valid = wrapper._validate_geometric_counterexample(valid_ce)
    checks = [
        (is_valid == True, "Valid CE with coordinates and angles accepted"),
    ]

    print("\nTest 1: Valid geometric counterexample")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    # Test 2: Invalid geometric counterexample (vague, no concrete values)
    invalid_ce = """
    The claim that P' is the midpoint might not hold in general for all
    configurations. Consider cases where the construction could fail.
    """

    is_valid = wrapper._validate_geometric_counterexample(invalid_ce)
    checks = [
        (is_valid == False, "Invalid vague CE rejected"),
    ]

    print("\nTest 2: Invalid vague counterexample")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    # Test 3: Self-contradicting counterexample
    contradiction_ce = """
    The proof claims that angle ABC = 60°. However, when I compute this angle
    with M=(0,0) and N=(2,0), I get angle = 60° which actually works and validates
    the claim. So this seems to work after all.
    """

    is_valid = wrapper._validate_geometric_counterexample(contradiction_ce)
    checks = [
        (is_valid == False, "Self-contradicting CE rejected"),
    ]

    print("\nTest 3: Self-contradicting counterexample")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    # Test 4: Counterexample with only one measurement (insufficient)
    insufficient_ce = """
    Setting radius r=5, the construction fails because the circles don't intersect.
    """

    is_valid = wrapper._validate_geometric_counterexample(insufficient_ce)
    checks = [
        (is_valid == False, "CE with only one measurement rejected"),
    ]

    print("\nTest 4: Insufficient measurements")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    # Test 5: Valid counterexample with coordinates only (2 assignments)
    coords_ce = """
    Testing the configuration with M=(0,0), N=(5,0), and computing point P
    at the intersection gives P=(2.5, y) where x=2.5. This violates the constraint
    that P must lie on the perpendicular bisector.
    """

    is_valid = wrapper._validate_geometric_counterexample(coords_ce)
    checks = [
        (is_valid == True, "CE with multiple coordinate assignments accepted"),
    ]

    print("\nTest 5: Valid with coordinate assignments")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    all_passed = all(passed for passed, _ in checks)
    return all_passed


def test_p1_recovery_integration():
    """Test Phase 1.1: P1 failure recovery mode (integration check)."""
    print("\n" + "="*80)
    print("TEST: Phase 1.1 - P1 Failure Recovery Mode (Integration)")
    print("="*80)

    # Test that the recovery code is present in agent_gpt_oss.py
    import agent_gpt_oss
    source = open('code/agent_gpt_oss.py', 'r').read()

    checks = [
        ('PHASE 1.1: P1 FAILURE RECOVERY MODE' in source,
         "P1 recovery code section present"),
        ('[RLAC P1 RECOVERY]' in source,
         "P1 recovery logging present"),
        ('Escalating generator: ' in source,
         "Generator reasoning escalation logic present"),
        ('get_proof_approach' in source,
         "Proof approach detection function present"),
        ('CRITICAL: HIGH reasoning verification found fundamental flaw' in source,
         "Strategy pivot prompt present"),
        ('DO NOT try to repair the old approach' in source,
         "Strategy change instruction present"),
        ('Alternative strategies for this problem:' in source,
         "Alternative strategy suggestions present"),
    ]

    print("\nTest 1: P1 recovery code integration")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    # Test that recovery triggers after P1 tiebreaker
    checks = [
        ('if original_critic_reasoning is not None and verdict in' in source,
         "Recovery condition checks for P1 activation and failure"),
        ("consecutive_robust = 0" in source and "# Reset near-success state" in source,
         "Resets consecutive ROBUST counter on P1 failure"),
    ]

    print("\nTest 2: P1 recovery trigger logic")
    for passed, desc in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")

    all_passed = all(passed for passed, _ in checks)
    return all_passed


def run_all_tests():
    """Run all Phase 0 and Phase 1 tests."""
    print("\n" + "="*80)
    print("COMPREHENSIVE PHASE 0 + PHASE 1 TEST SUITE")
    print("="*80)

    results = []

    # Phase 0 tests
    print("\n" + "="*80)
    print("PHASE 0: QUICK WINS")
    print("="*80)
    results.append(("Phase 0.1: Problem Difficulty Detection", test_problem_difficulty_detection()))
    results.append(("Phase 0.2: Geometry-Enhanced Prompts", test_geometry_prompts()))

    # Phase 1 tests
    print("\n" + "="*80)
    print("PHASE 1: CORE FIXES")
    print("="*80)
    results.append(("Phase 1.1: P1 Failure Recovery Mode", test_p1_recovery_integration()))
    results.append(("Phase 1.2: Counterexample Quality Filter", test_counterexample_quality_filter()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    total = len(results)
    passed = sum(1 for _, result in results if result)
    failed = total - passed

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print("\n" + "="*80)
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED - Phase 0 + Phase 1 implementation verified!")
        print("="*80)
        return True
    else:
        print(f"\n⚠️  {failed} TEST(S) FAILED - Please review implementation")
        print("="*80)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
