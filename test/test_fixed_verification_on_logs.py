#!/usr/bin/env python3
"""
Test fixed verification system on actual BFS and MCTS log files.

This script extracts the final solutions from the log files and runs them
through the fixed verification with counterexample validation to demonstrate:

1. BFS answer (k ∈ {0,...,n}) is ACCEPTED ✓ (CORRECTED: BFS is mathematically correct!)
2. MCTS answer (k ∈ {0,1}) is ACCEPTED ✓

Expected behavior:
- BFS: Verification should ACCEPT k ∈ {0,...,n} (proven correct by Google Scientist)
- MCTS: Verification should ACCEPT k ∈ {0,1} (subset of correct answer)

Note: Previous version incorrectly rejected BFS due to validator logical fallacy.
      This has been fixed to accept all k ∈ {0,...,n} as mathematically valid.
"""

import re
import sys
from test_verification_fix import CounterexampleValidator


def extract_solution_from_log(log_path):
    """Extract final solution from agent log file."""
    with open(log_path, 'r') as f:
        content = f.read()

    # Look for "Correct solution found" or "Found a correct solution"
    match = re.search(r'>>>>>>> Correct solution found\.\n"([^"]+)"', content, re.DOTALL)
    if not match:
        match = re.search(r'>>>>>>> Found a correct solution.*?\n"([^"]+)"', content, re.DOTALL)

    if match:
        # Clean up the solution text
        solution = match.group(1)
        # Unescape newlines and backslashes
        solution = solution.replace('\\n', '\n').replace('\\\\', '\\')
        return solution

    return None


def extract_verification_result_from_log(log_path):
    """Extract original verification result from log."""
    with open(log_path, 'r') as f:
        content = f.read()

    # Look for "Is verification good?"
    match = re.search(r'>>>>>>> Is verification good\?\n"([^"]+)"', content)
    if match:
        return match.group(1)

    return None


def test_bfs_log():
    """Test BFS log - should ACCEPT k ∈ {0,...,n} (CORRECTED: BFS is mathematically correct!)."""
    print("="*80)
    print("TEST 1: BFS Log (run_log_gpt_oss/agent_gpt_oss_bfs_output_1.log)")
    print("="*80)

    log_path = "run_log_gpt_oss/agent_gpt_oss_bfs_output_1.log"

    # Extract solution
    solution = extract_solution_from_log(log_path)
    if not solution:
        print("❌ FAILED: Could not extract solution from BFS log")
        return False

    print("\n[EXTRACTED SOLUTION]")
    # Show first 500 chars
    print(solution[:500] + "..." if len(solution) > 500 else solution)

    # Extract original verification result
    original_verdict = extract_verification_result_from_log(log_path)
    print(f"\n[ORIGINAL VERIFICATION]: {original_verdict}")

    # Run counterexample validation
    print("\n[COUNTEREXAMPLE VALIDATION]")
    validator = CounterexampleValidator(test_cases=[3, 4, 5])
    result = validator.validate_solution(solution)

    print(f"Verdict: {result['verdict']}")
    print(f"Reason: {result['reason']}")
    if result['failed_cases']:
        print("Failed cases:")
        for n, k, reason in result['failed_cases']:
            print(f"  - n={n}, k={k}: {reason}")

    # Check expectation (CORRECTED: BFS is mathematically correct!)
    if result['verdict'] == 'VALID':
        print("\n✅ PASS: BFS answer k ∈ {0,...,n} correctly ACCEPTED by counterexample validation")
        print(f"   Fixed validator now accepts all k ∈ {{0,...,n}} as mathematically valid")
        print(f"   (Previous validator had logical fallacy - now corrected!)")
        return True
    else:
        print("\n❌ FAIL: BFS answer was NOT accepted (expected VALID)")
        print(f"   BFS answer k ∈ {{0,...,n}} is mathematically correct (proven by Google Scientist)")
        return False


def test_mcts_log():
    """Test MCTS log - should ACCEPT k ∈ {0,1}."""
    print("\n" + "="*80)
    print("TEST 2: MCTS Log (run_log_gpt_oss/agent_gpt_oss_mcts_output_1.log)")
    print("="*80)

    log_path = "run_log_gpt_oss/agent_gpt_oss_mcts_output_1.log"

    # Extract solution
    solution = extract_solution_from_log(log_path)
    if not solution:
        print("❌ FAILED: Could not extract solution from MCTS log")
        return False

    print("\n[EXTRACTED SOLUTION]")
    # Show first 500 chars
    print(solution[:500] + "..." if len(solution) > 500 else solution)

    # Extract original verification result
    original_verdict = extract_verification_result_from_log(log_path)
    print(f"\n[ORIGINAL VERIFICATION]: {original_verdict}")

    # Run counterexample validation
    print("\n[COUNTEREXAMPLE VALIDATION]")
    validator = CounterexampleValidator(test_cases=[3, 4, 5])
    result = validator.validate_solution(solution)

    print(f"Verdict: {result['verdict']}")
    print(f"Reason: {result['reason']}")
    if result['failed_cases']:
        print("Failed cases:")
        for n, k, reason in result['failed_cases']:
            print(f"  - n={n}, k={k}: {reason}")

    # Check expectation
    if result['verdict'] == 'VALID':
        print("\n✅ PASS: MCTS correct answer correctly ACCEPTED by counterexample validation")
        print(f"   Original: '{original_verdict}' → Fixed: 'yes' (unchanged)")
        return True
    else:
        print("\n❌ FAIL: MCTS correct answer was NOT accepted (expected VALID)")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("FIXED VERIFICATION TEST: BFS vs MCTS")
    print("="*80)
    print("\nGoal: Demonstrate that FIXED counterexample validation correctly accepts both")
    print("      BFS and MCTS answers (both are mathematically correct!).")
    print("\nCORRECTION: Previous validator had logical fallacy that rejected k ∈ {0,...,n}.")
    print("           Google Scientist proved BFS answer k ∈ {0,...,n} is CORRECT.")
    print("           Fixed validator now accepts all valid constructions.")
    print()

    # Run tests
    bfs_pass = test_bfs_log()
    mcts_pass = test_mcts_log()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"BFS Test (accept correct answer):   {'✅ PASS' if bfs_pass else '❌ FAIL'}")
    print(f"MCTS Test (accept correct answer):  {'✅ PASS' if mcts_pass else '❌ FAIL'}")

    if bfs_pass and mcts_pass:
        print("\n🎉 SUCCESS: Fixed verification correctly accepts mathematically valid answers!")
        print("\nWhat changed:")
        print("  - BFS: k ∈ {0,...,n} → ACCEPTED (validator logical fallacy fixed)")
        print("  - MCTS: k ∈ {0,1} → ACCEPTED (subset of correct answer)")
        print("\nKey insight:")
        print("  - BFS and MCTS don't contradict each other!")
        print("  - BFS finds full answer: k ∈ {0,1,2,...,n}")
        print("  - MCTS finds partial answer: k ∈ {0,1} (valid but incomplete)")
        print("\nThis fixes the validator logical fallacy (diagonal lemma misinterpretation).")
        print("\nNext steps:")
        print("  1. Run new BFS/MCTS tests with corrected validator")
        print("  2. Both should succeed (no more false negatives)")
        print("  3. Scale up to MEDIUM/HIGH reasoning with correct validation")
        return 0
    else:
        print("\n❌ FAILURE: Some tests did not pass as expected")
        print("\nDebug:")
        if not bfs_pass:
            print("  - BFS test failed: Validator rejected mathematically correct answer k ∈ {0,...,n}")
            print("    This should NOT happen - BFS is proven correct by Google Scientist!")
        if not mcts_pass:
            print("  - MCTS test failed: Validator rejected correct answer k ∈ {0,1}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
