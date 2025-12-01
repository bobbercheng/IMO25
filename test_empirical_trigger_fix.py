#!/usr/bin/env python3
"""
Test suite for empirical verification trigger logic bugfix (commit 03104d3).

BUGFIX: Empirical verification should trigger on BROKEN/SUSPICIOUS verdicts
        to validate critic's attacks, NOT on ROBUST verdicts.

Tests:
1. Empirical triggers on BROKEN verdict
2. Empirical triggers on SUSPICIOUS verdict
3. Empirical does NOT trigger on ROBUST verdict
4. Empirical override: BROKEN → ROBUST when ground truth passes
5. Empirical confirmation: BROKEN → BROKEN when ground truth fails
"""

import sys
sys.path.insert(0, 'code')

from empirical_critic_wrapper import EmpiricalCriticWrapper
from adversarial_critic import AdversarialCritic
from unittest.mock import Mock, MagicMock, patch


def create_mock_critic(verdict):
    """Create a mock critic that returns a specific verdict."""
    mock_critic = Mock(spec=AdversarialCritic)
    mock_critic.attack_solution = Mock(return_value={
        'verdict': verdict,
        'score': -10 if verdict == 'BROKEN' else (0 if verdict == 'SUSPICIOUS' else 10),
        'counterexamples': ['Test counterexample'] if verdict in ['BROKEN', 'SUSPICIOUS'] else [],
    })
    return mock_critic


def test_trigger_on_broken():
    """Test that empirical verification triggers when critic says BROKEN."""
    print("\n" + "="*80)
    print("TEST 1: Empirical Triggers on BROKEN Verdict")
    print("="*80)

    # Setup
    base_critic = create_mock_critic('BROKEN')
    wrapper = EmpiricalCriticWrapper(base_critic, enable_empirical=True)

    # Mock the empirical verifier to return ROBUST (override case)
    with patch('empirical_critic_wrapper.empirical_verifier_dispatcher') as mock_verifier:
        mock_verifier.return_value = {
            'verdict': 'ROBUST',
            'score': 1.0,
            'errors': []
        }

        # Execute
        problem = "Test problem"
        solution = "Test solution with \\boxed{k \\in \\{0,1,n-1\\}}"
        result = wrapper.attack_solution(problem, solution, round_num=1)

        # Verify empirical was called
        assert mock_verifier.called, "❌ FAILED: Empirical verifier was not called on BROKEN verdict"
        print(f"  ✅ Empirical verifier called: {mock_verifier.call_count} time(s)")

        # Verify verdict was overridden
        assert result['verdict'] == 'ROBUST', f"❌ FAILED: Expected ROBUST, got {result['verdict']}"
        print(f"  ✅ Verdict overridden: BROKEN → ROBUST")

        # Verify override metadata
        assert result.get('empirical_override'), "❌ FAILED: Missing empirical_override flag"
        print(f"  ✅ Override flag set correctly")

    print("\n✅ TEST 1 PASSED")
    return True


def test_trigger_on_suspicious():
    """Test that empirical verification triggers when critic says SUSPICIOUS."""
    print("\n" + "="*80)
    print("TEST 2: Empirical Triggers on SUSPICIOUS Verdict")
    print("="*80)

    # Setup
    base_critic = create_mock_critic('SUSPICIOUS')
    wrapper = EmpiricalCriticWrapper(base_critic, enable_empirical=True)

    # Mock the empirical verifier to return BROKEN (confirmation case)
    with patch('empirical_critic_wrapper.empirical_verifier_dispatcher') as mock_verifier:
        mock_verifier.return_value = {
            'verdict': 'BROKEN',
            'score': 0.3,
            'errors': ['Test error 1', 'Test error 2']
        }

        # Execute
        problem = "Test problem"
        solution = "Test solution with \\boxed{k = 0 \\text{ or } k \\text{ odd}}"
        result = wrapper.attack_solution(problem, solution, round_num=1)

        # Verify empirical was called
        assert mock_verifier.called, "❌ FAILED: Empirical verifier was not called on SUSPICIOUS verdict"
        print(f"  ✅ Empirical verifier called: {mock_verifier.call_count} time(s)")

        # Verify verdict remains BROKEN/SUSPICIOUS
        assert result['verdict'] in ['BROKEN', 'SUSPICIOUS'], f"❌ FAILED: Unexpected verdict {result['verdict']}"
        print(f"  ✅ Verdict confirmed: SUSPICIOUS → {result['verdict']}")

        # Verify confirmation metadata
        assert result.get('empirical_confirmed') or result.get('empirical_warning'), \
            "❌ FAILED: Missing empirical confirmation/warning flag"
        print(f"  ✅ Confirmation flag set correctly")

    print("\n✅ TEST 2 PASSED")
    return True


def test_no_trigger_on_robust():
    """Test that empirical verification does NOT trigger when critic says ROBUST (old buggy behavior)."""
    print("\n" + "="*80)
    print("TEST 3: Empirical Does NOT Trigger on ROBUST Verdict")
    print("="*80)

    # Setup
    base_critic = create_mock_critic('ROBUST')
    wrapper = EmpiricalCriticWrapper(base_critic, enable_empirical=True)

    # Mock the empirical verifier (should not be called)
    with patch('empirical_critic_wrapper.empirical_verifier_dispatcher') as mock_verifier:
        mock_verifier.return_value = {
            'verdict': 'ROBUST',
            'score': 1.0,
            'errors': []
        }

        # Execute
        problem = "Test problem"
        solution = "Test solution with \\boxed{k \\in \\{1,2,\\ldots,n\\}}"
        result = wrapper.attack_solution(problem, solution, round_num=1)

        # Verify empirical was NOT called (correct behavior after fix)
        assert not mock_verifier.called, \
            "❌ FAILED: Empirical verifier was called on ROBUST verdict (old buggy behavior)"
        print(f"  ✅ Empirical verifier NOT called (correct)")

        # Verify verdict remains ROBUST
        assert result['verdict'] == 'ROBUST', f"❌ FAILED: Expected ROBUST, got {result['verdict']}"
        print(f"  ✅ Verdict unchanged: ROBUST")

    print("\n✅ TEST 3 PASSED")
    return True


def test_override_broken_to_robust():
    """Test empirical override: BROKEN → ROBUST when ground truth tests pass."""
    print("\n" + "="*80)
    print("TEST 4: Empirical Override (BROKEN → ROBUST)")
    print("="*80)

    # Setup
    base_critic = create_mock_critic('BROKEN')
    wrapper = EmpiricalCriticWrapper(base_critic, enable_empirical=True)

    # Mock empirical verifier to return ROBUST (ground truth passes)
    with patch('empirical_critic_wrapper.empirical_verifier_dispatcher') as mock_verifier:
        mock_verifier.return_value = {
            'verdict': 'ROBUST',
            'score': 1.0,  # 100% pass rate
            'errors': []
        }

        # Execute
        problem = "IMO Problem 1"
        solution = "Solution claiming \\boxed{k \\in \\{0,1,\\ldots,n-1\\}}"
        result = wrapper.attack_solution(problem, solution, round_num=1)

        # Verify override occurred
        assert result['verdict'] == 'ROBUST', \
            f"❌ FAILED: Expected override to ROBUST, got {result['verdict']}"
        print(f"  ✅ Verdict overridden: BROKEN → ROBUST")

        # Verify override reason
        assert result.get('empirical_override') == True, \
            "❌ FAILED: Missing empirical_override flag"
        assert 'override_reason' in result, \
            "❌ FAILED: Missing override_reason"
        print(f"  ✅ Override metadata: {result['override_reason'][:50]}...")

        # Verify score recorded
        assert result.get('empirical_score') == 1.0, \
            f"❌ FAILED: Expected score 1.0, got {result.get('empirical_score')}"
        print(f"  ✅ Empirical score: {result['empirical_score']:.1%}")

    print("\n✅ TEST 4 PASSED")
    return True


def test_confirmation_broken_remains():
    """Test empirical confirmation: BROKEN → BROKEN when ground truth tests fail."""
    print("\n" + "="*80)
    print("TEST 5: Empirical Confirmation (BROKEN → BROKEN)")
    print("="*80)

    # Setup
    base_critic = create_mock_critic('BROKEN')
    wrapper = EmpiricalCriticWrapper(base_critic, enable_empirical=True)

    # Mock empirical verifier to return BROKEN (ground truth fails)
    with patch('empirical_critic_wrapper.empirical_verifier_dispatcher') as mock_verifier:
        mock_verifier.return_value = {
            'verdict': 'BROKEN',
            'score': 0.35,  # 35% pass rate
            'errors': [
                'n=3, k=0: Expected construction to work, but fails',
                'n=4, k=3: Point (3,1) not covered'
            ]
        }

        # Execute
        problem = "IMO Problem 1"
        solution = "Solution with wrong answer \\boxed{k = 0 \\text{ or } k \\text{ odd}}"
        result = wrapper.attack_solution(problem, solution, round_num=1)

        # Verify verdict remains BROKEN
        assert result['verdict'] == 'BROKEN', \
            f"❌ FAILED: Expected BROKEN, got {result['verdict']}"
        print(f"  ✅ Verdict confirmed: BROKEN → BROKEN")

        # Verify confirmation metadata
        assert result.get('empirical_confirmed') == True, \
            "❌ FAILED: Missing empirical_confirmed flag"
        print(f"  ✅ Confirmation flag set")

        # Verify empirical errors added
        assert 'empirical_errors' in result, \
            "❌ FAILED: Missing empirical_errors"
        assert len(result['empirical_errors']) > 0, \
            "❌ FAILED: No empirical errors recorded"
        print(f"  ✅ Empirical errors: {len(result['empirical_errors'])} recorded")

        # Verify score recorded
        assert result.get('empirical_score') == 0.35, \
            f"❌ FAILED: Expected score 0.35, got {result.get('empirical_score')}"
        print(f"  ✅ Empirical score: {result['empirical_score']:.1%}")

    print("\n✅ TEST 5 PASSED")
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*80)
    print("EMPIRICAL VERIFICATION TRIGGER LOGIC TEST SUITE")
    print("Testing bugfix: Trigger on BROKEN/SUSPICIOUS, not ROBUST")
    print("="*80)

    tests = [
        ("Trigger on BROKEN", test_trigger_on_broken),
        ("Trigger on SUSPICIOUS", test_trigger_on_suspicious),
        ("No trigger on ROBUST", test_no_trigger_on_robust),
        ("Override BROKEN→ROBUST", test_override_broken_to_robust),
        ("Confirm BROKEN→BROKEN", test_confirmation_broken_remains),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ TEST FAILED: {name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {status}: {name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Empirical trigger fix verified!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Fix needs attention")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
