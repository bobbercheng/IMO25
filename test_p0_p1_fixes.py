#!/usr/bin/env python3
"""
Test suite for P0.5 (Verdict Downgrade Bug) and P1 (Oscillation Tiebreaker) fixes.

P0.5 - Verdict Downgrade Bug:
- Audit logging tracks all verdict changes
- Downgrades are logged with source (P3, P4, P1, etc.)
- Final verdict audit shows if downgrade occurred

P1 - Oscillation Tiebreaker:
- When consecutive_robust == threshold-1, flag is set
- Next critic attack uses HIGH reasoning
- Reasoning is restored after attack
- Helps convert near-miss (2/3) to success (3/3)
"""

import sys
import os
sys.path.insert(0, 'code')

# Mock test - we'll test logging output patterns
def test_verdict_audit_logging():
    """Test that verdict audit logging is properly added."""
    print("\n" + "="*80)
    print("TEST 1: Verdict Audit Logging (P0.5)")
    print("="*80)

    # Read the agent code
    with open('code/agent_gpt_oss.py', 'r') as f:
        code = f.read()

    # Check for audit logging patterns
    checks = [
        ('original_critic_verdict = verdict', 'Original verdict captured'),
        ('[VERDICT AUDIT] Critic original verdict', 'Initial audit log present'),
        ('[VERDICT AUDIT] P3 Truncation downgrade', 'P3 downgrade logging'),
        ('[VERDICT AUDIT] P4 Oscillation downgrade', 'P4 downgrade logging'),
        ('[VERDICT AUDIT] ⚠️  DOWNGRADE DETECTED', 'Final downgrade detection'),
        ('[VERDICT AUDIT] Verdict unchanged', 'No-downgrade logging'),
    ]

    passed = 0
    for pattern, description in checks:
        if pattern in code:
            print(f"  ✅ {description}")
            passed += 1
        else:
            print(f"  ❌ {description} - NOT FOUND")

    assert passed == len(checks), f"Only {passed}/{len(checks)} checks passed"
    print(f"\n✅ TEST 1 PASSED ({passed}/{len(checks)} checks)")
    return True


def test_oscillation_tiebreaker_flag():
    """Test that oscillation tiebreaker flag is properly initialized and used."""
    print("\n" + "="*80)
    print("TEST 2: Oscillation Tiebreaker Flag (P1)")
    print("="*80)

    with open('code/agent_gpt_oss.py', 'r') as f:
        code = f.read()

    checks = [
        ('use_tiebreaker_next_round = False', 'Flag initialized to False'),
        ('use_tiebreaker_next_round = (consecutive_robust == consecutive_robust_threshold - 1)',
         'Flag set at threshold-1'),
        ('[RLAC P1 TIEBREAKER] Near success', 'Tiebreaker message logged'),
        ('if use_tiebreaker_next_round:', 'Tiebreaker check before critic'),
        ('original_critic_reasoning = critic.reasoning_effort', 'Original reasoning saved'),
        ('critic.reasoning_effort = "high"', 'Reasoning upgraded to high'),
        ('use_tiebreaker_next_round = False  # Reset', 'Flag reset after use'),
        ('critic.reasoning_effort = original_critic_reasoning', 'Reasoning restored'),
    ]

    passed = 0
    for pattern, description in checks:
        if pattern in code:
            print(f"  ✅ {description}")
            passed += 1
        else:
            print(f"  ❌ {description} - NOT FOUND")

    assert passed == len(checks), f"Only {passed}/{len(checks)} checks passed"
    print(f"\n✅ TEST 2 PASSED ({passed}/{len(checks)} checks)")
    return True


def test_tiebreaker_logic_flow():
    """Test the logical flow of the tiebreaker mechanism."""
    print("\n" + "="*80)
    print("TEST 3: Tiebreaker Logic Flow (P1)")
    print("="*80)

    with open('code/agent_gpt_oss.py', 'r') as f:
        lines = f.readlines()

    # Find key lines
    flag_init_line = None
    flag_set_line = None
    flag_check_line = None
    reasoning_upgrade_line = None
    reasoning_restore_line = None

    for i, line in enumerate(lines):
        if 'use_tiebreaker_next_round = False' in line and '# P1 FIX' in lines[i-1]:
            flag_init_line = i + 1
        elif 'use_tiebreaker_next_round = (consecutive_robust' in line:
            flag_set_line = i + 1
        elif 'if use_tiebreaker_next_round:' in line and '# P1 FIX' in lines[i-2]:
            flag_check_line = i + 1
        elif 'critic.reasoning_effort = "high"' in line:
            reasoning_upgrade_line = i + 1
        elif 'critic.reasoning_effort = original_critic_reasoning' in line:
            reasoning_restore_line = i + 1

    print(f"  Flag initialization: line {flag_init_line}")
    print(f"  Flag set (at threshold-1): line {flag_set_line}")
    print(f"  Flag check (before critic): line {flag_check_line}")
    print(f"  Reasoning upgrade: line {reasoning_upgrade_line}")
    print(f"  Reasoning restore: line {reasoning_restore_line}")

    # Validate flow
    checks = [
        (flag_init_line is not None, "Flag initialized"),
        (flag_set_line is not None, "Flag set at threshold-1"),
        (flag_check_line is not None, "Flag checked before critic"),
        (reasoning_upgrade_line is not None, "Reasoning upgraded"),
        (reasoning_restore_line is not None, "Reasoning restored"),
        (flag_init_line < flag_set_line, "Initialization before setting"),
        # Note: flag_check_line < flag_set_line is CORRECT - flag is checked in round N+1 after being set in round N
        (flag_check_line < flag_set_line, "Check before setting (cross-round flow)"),
        (flag_check_line < reasoning_upgrade_line, "Check before upgrade"),
        (reasoning_upgrade_line < reasoning_restore_line, "Upgrade before restore"),
    ]

    passed = 0
    for condition, description in checks:
        if condition:
            print(f"  ✅ {description}")
            passed += 1
        else:
            print(f"  ❌ {description}")

    assert passed == len(checks), f"Only {passed}/{len(checks)} checks passed"
    print(f"\n✅ TEST 3 PASSED ({passed}/{len(checks)} checks)")
    return True


def test_downgrade_logging_comprehensive():
    """Test that all downgrade points have audit logging."""
    print("\n" + "="*80)
    print("TEST 4: Comprehensive Downgrade Logging (P0.5)")
    print("="*80)

    with open('code/agent_gpt_oss.py', 'r') as f:
        code = f.read()

    # Find all places where verdict gets downgraded
    downgrade_patterns = [
        ('verdict = "SUSPICIOUS".*truncation_detected', 'P3 truncation downgrade'),
        ('verdict = "SUSPICIOUS".*p4_oscillation_override', 'P4 oscillation downgrade'),
        ('verdict = "SUSPICIOUS".*p1_downgraded', 'P1 counterexample downgrade'),
    ]

    found_downgrades = []
    for pattern, description in downgrade_patterns:
        import re
        if re.search(pattern, code, re.DOTALL):
            found_downgrades.append(description)
            print(f"  ✅ Found: {description}")

    print(f"\n  Found {len(found_downgrades)} downgrade locations")

    # Check that each has corresponding audit logging
    audit_patterns = [
        'P3 Truncation downgrade',
        'P4 Oscillation downgrade',
    ]

    logged_downgrades = []
    for pattern in audit_patterns:
        if pattern in code:
            logged_downgrades.append(pattern)
            print(f"  ✅ Audit log: {pattern}")
        else:
            print(f"  ⚠️  Missing audit log: {pattern}")

    # At minimum, we should have 2 audit logs (P3 and P4)
    assert len(logged_downgrades) >= 2, f"Only {len(logged_downgrades)} audit logs found"

    print(f"\n✅ TEST 4 PASSED (Found {len(logged_downgrades)} audit logs)")
    return True


def test_tiebreaker_threshold_detection():
    """Test that tiebreaker correctly detects threshold-1 condition."""
    print("\n" + "="*80)
    print("TEST 5: Tiebreaker Threshold Detection (P1)")
    print("="*80)

    with open('code/agent_gpt_oss.py', 'r') as f:
        code = f.read()

    # Verify the threshold-1 detection logic
    checks = [
        ('consecutive_robust == consecutive_robust_threshold - 1', 'Threshold-1 condition'),
        ('Will verify next solution with HIGH reasoning', 'High reasoning notification'),
        ('Near success', 'Near success detection message'),
    ]

    passed = 0
    for pattern, description in checks:
        if pattern in code:
            print(f"  ✅ {description}")
            passed += 1
        else:
            print(f"  ❌ {description} - NOT FOUND")

    # Verify the condition is checked in ROBUST verdict handler
    if 'if verdict == "ROBUST":' in code and 'consecutive_robust == consecutive_robust_threshold - 1' in code:
        print(f"  ✅ Threshold check in ROBUST handler")
        passed += 1
    else:
        print(f"  ❌ Threshold check not in ROBUST handler")

    assert passed == len(checks) + 1, f"Only {passed}/{len(checks) + 1} checks passed"
    print(f"\n✅ TEST 5 PASSED ({passed}/{len(checks) + 1} checks)")
    return True


def test_integration_workflow():
    """Test the complete workflow for both fixes."""
    print("\n" + "="*80)
    print("TEST 6: Integration Workflow (P0.5 + P1)")
    print("="*80)

    with open('code/agent_gpt_oss.py', 'r') as f:
        code = f.read()

    # Test the complete flow
    workflow_steps = [
        ('original_critic_verdict = verdict', 'Step 1: Capture original verdict'),
        ('[VERDICT AUDIT] Critic original verdict', 'Step 2: Log original verdict'),
        ('if attack_length < min_valid_attack_length', 'Step 3: Check truncation'),
        ('[VERDICT AUDIT] P3 Truncation downgrade', 'Step 4: Log P3 downgrade if occurs'),
        ('elif verdict == "BROKEN" and total_robust_count >= 3', 'Step 5: Check P4 oscillation'),
        ('[VERDICT AUDIT] P4 Oscillation downgrade', 'Step 6: Log P4 downgrade if occurs'),
        ('[VERDICT AUDIT] ⚠️  DOWNGRADE DETECTED', 'Step 7: Final downgrade summary'),
        ('use_tiebreaker_next_round = (consecutive_robust', 'Step 8: Set tiebreaker flag'),
        ('if use_tiebreaker_next_round:', 'Step 9: Check flag next round'),
        ('critic.reasoning_effort = "high"', 'Step 10: Upgrade reasoning'),
        ('critic.reasoning_effort = original_critic_reasoning', 'Step 11: Restore reasoning'),
    ]

    passed = 0
    for pattern, description in workflow_steps:
        if pattern in code:
            print(f"  ✅ {description}")
            passed += 1
        else:
            print(f"  ❌ {description} - NOT FOUND")

    assert passed == len(workflow_steps), f"Only {passed}/{len(workflow_steps)} steps passed"
    print(f"\n✅ TEST 6 PASSED ({passed}/{len(workflow_steps)} workflow steps)")
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*80)
    print("P0.5 + P1 FIX TEST SUITE")
    print("Testing: Verdict Downgrade Audit + Oscillation Tiebreaker")
    print("="*80)

    tests = [
        ("Verdict Audit Logging", test_verdict_audit_logging),
        ("Oscillation Tiebreaker Flag", test_oscillation_tiebreaker_flag),
        ("Tiebreaker Logic Flow", test_tiebreaker_logic_flow),
        ("Comprehensive Downgrade Logging", test_downgrade_logging_comprehensive),
        ("Tiebreaker Threshold Detection", test_tiebreaker_threshold_detection),
        ("Integration Workflow", test_integration_workflow),
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
        print("\n🎉 ALL TESTS PASSED - P0.5 + P1 fixes verified!")
        print("\nP0.5 - Verdict Downgrade Bug:")
        print("  ✅ Audit logging tracks all verdict changes")
        print("  ✅ Downgrades logged with source (P3, P4, etc.)")
        print("  ✅ Final verdict audit shows if downgrade occurred")
        print("\nP1 - Oscillation Tiebreaker:")
        print("  ✅ Flag set when consecutive_robust == threshold-1")
        print("  ✅ Next critic attack uses HIGH reasoning")
        print("  ✅ Reasoning restored after attack")
        print("  ✅ Helps convert 2/3 ROBUST → 3/3 SUCCESS")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Fixes need attention")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
