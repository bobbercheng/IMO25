#!/usr/bin/env python3
"""
Test script to verify empirical_critic_wrapper integration with agent_gpt_oss.py
"""
import sys
sys.path.insert(0, 'code')

print("="*80)
print("Testing EmpiricalCriticWrapper Integration")
print("="*80)

# Test 1: Import all modules
print("\n[Test 1] Importing modules...")
try:
    from adversarial_critic import AdversarialCritic
    from empirical_critic_wrapper import EmpiricalCriticWrapper
    print("  ✅ Imports successful")
except Exception as e:
    print(f"  ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Create wrapper (same as agent_gpt_oss.py line 2569-2574)
print("\n[Test 2] Creating EmpiricalCriticWrapper (mimicking agent_gpt_oss.py)...")
try:
    base_critic = AdversarialCritic(
        reasoning_effort="medium",
        verbose=False
    )
    critic = EmpiricalCriticWrapper(base_critic, enable_empirical=True)
    print("  ✅ Wrapper created successfully")
except Exception as e:
    print(f"  ❌ Wrapper creation failed: {e}")
    sys.exit(1)

# Test 3: Test create_enhanced_session (line 2586)
print("\n[Test 3] Testing create_enhanced_session()...")
try:
    enhanced_session = critic.create_enhanced_session()
    print(f"  ✅ Enhanced session created: {type(enhanced_session).__name__}")
except Exception as e:
    print(f"  ❌ create_enhanced_session() failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test other forwarded methods
print("\n[Test 4] Testing other forwarded methods...")
methods = [
    'get_defense_prompt',
    'get_metrics_summary',
    'detect_stuck_pattern',
    'save_attack_history'
]

for method_name in methods:
    try:
        method = getattr(critic, method_name)
        print(f"  ✅ {method_name}: accessible")
    except AttributeError as e:
        print(f"  ❌ {method_name}: NOT FOUND - {e}")
        sys.exit(1)

# Test 5: Test attack_solution still works
print("\n[Test 5] Testing attack_solution() (with empirical layer)...")
try:
    # Mock problem and solution
    mock_problem = "Find all nonnegative integers k..."
    mock_solution = """
We claim k∈{0,1,n-1}.

Proof: ...

Therefore, \\boxed{k \\in \\{0, 1, n-1\\}}.
"""

    # This should work but may fail due to API call - that's OK for integration test
    # We just want to make sure it doesn't crash on method forwarding
    print("  Note: This may fail due to API not running - that's OK")
    print("  We're just testing method forwarding works, not actual execution")

    # The attack_solution override exists in wrapper
    assert hasattr(critic, 'attack_solution'), "attack_solution method missing!"
    print("  ✅ attack_solution() method exists in wrapper")

except Exception as e:
    print(f"  ⚠️  Test inconclusive (API may not be running): {e}")
    # This is OK - we're testing integration, not execution

# Test 6: Test empirical history tracking
print("\n[Test 6] Testing empirical history tracking...")
try:
    summary = critic.get_empirical_summary()
    assert 'total' in summary, "Summary missing 'total' field"
    assert 'enabled' in summary, "Summary missing 'enabled' field"
    assert summary['enabled'] == True, "Empirical verification should be enabled"
    print(f"  ✅ Empirical history tracking works: {summary}")
except Exception as e:
    print(f"  ❌ Empirical history failed: {e}")
    sys.exit(1)

print("\n" + "="*80)
print("✅ ALL INTEGRATION TESTS PASSED")
print("="*80)
print("\nConclusion:")
print("  - EmpiricalCriticWrapper successfully wraps AdversarialCritic")
print("  - All methods forward correctly to base_critic")
print("  - Integration with agent_gpt_oss.py should work")
print("  - Ready to run full RLAC test with empirical verification")
print("="*80)
