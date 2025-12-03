#!/usr/bin/env python3
"""
Standalone TIER 2 Refinement Test

Tests the TIER 2 refinement loop with graduated verification using a
pre-existing RLAC solution (bypassing the need for API server).

This allows testing TIER 2 configuration changes in isolation.
"""

import json
import sys
from code.tier2_refinement import tier2_refinement_loop, extract_boxed_answer
from code.agent_gpt_oss import verify_solution_safe, generate_solution


def load_previous_rlac_result(memory_file):
    """Load RLAC solution from previous successful run."""
    with open(memory_file, 'r') as f:
        memory = json.load(f)

    # Extract the solution that achieved TIER 1
    if 'final_solution' in memory:
        return memory['final_solution']

    # Fallback: get last iteration solution
    if 'iterations' in memory and len(memory['iterations']) > 0:
        last_iter = memory['iterations'][-1]
        return last_iter.get('solution', '')

    raise ValueError("No solution found in memory file")


def mock_verify_solution(problem, solution, reasoning_effort):
    """Wrapper for verify_solution_safe with correct signature."""
    return verify_solution_safe(problem, solution, reasoning_effort=reasoning_effort)


def mock_generate_solution(prompt, reasoning_effort):
    """Wrapper for generate_solution with correct signature."""
    return generate_solution(prompt, reasoning_effort=reasoning_effort)


def main():
    print("=" * 80)
    print("STANDALONE TIER 2 REFINEMENT TEST")
    print("=" * 80)
    print()
    print("This test validates graduated verification using a previous RLAC solution")
    print("Configuration:")
    print("  - Max rounds: 8")
    print("  - Graduated verification: ENABLED")
    print("    - Rounds 1-3: low verification (accept proof outline)")
    print("    - Rounds 4-6: medium verification (IMO standard)")
    print("    - Rounds 7-8: high verification (publication-ready)")
    print("=" * 80)
    print()

    # Load problem statement
    with open('problems/imo02.txt', 'r') as f:
        problem_statement = f.read()

    # Load previous RLAC solution
    print("[SETUP] Loading previous RLAC solution...")
    try:
        rlac_solution = load_previous_rlac_result('test_rlac_log/tier2_test_p2.json')
        print(f"[SETUP] ✓ Loaded solution ({len(rlac_solution)} chars)")
    except Exception as e:
        print(f"[ERROR] Failed to load previous solution: {e}")
        return 1

    # Extract locked answer (will be None for proof problems)
    locked_answer = extract_boxed_answer(rlac_solution, problem_statement)
    print(f"[SETUP] Answer lock status: {'DISABLED (proof problem)' if locked_answer is None else f'ENABLED ({locked_answer[:50]}...)'}")
    print()

    # Run TIER 2 refinement with graduated verification
    print("[TIER 2] Starting refinement loop...")
    print()

    refined_solution, tier_status, refinement_history = tier2_refinement_loop(
        problem_statement=problem_statement,
        rlac_solution=rlac_solution,
        locked_answer=locked_answer,
        verify_solution_func=mock_verify_solution,
        generate_solution_func=mock_generate_solution,
        max_refinement_rounds=8,
        refinement_reasoning="high",
        verification_reasoning="medium",
        use_graduated_verification=True,
        verbose=True
    )

    # Report results
    print()
    print("=" * 80)
    print("TIER 2 REFINEMENT COMPLETE")
    print("=" * 80)
    print(f"Final Status: {tier_status}")
    print(f"Refinement Rounds: {len(refinement_history)}")
    print()

    if refinement_history:
        print("Round-by-round progression:")
        for round_info in refinement_history:
            print(f"  Round {round_info['round']}: {round_info['issues_count']} issues "
                  f"({round_info['critical']} critical, {round_info['gaps']} gaps)")

    # Save results
    output_file = 'test_rlac_log/tier2_standalone_results.json'
    results = {
        'tier_status': tier_status,
        'refinement_rounds': len(refinement_history),
        'refinement_history': refinement_history,
        'final_solution_length': len(refined_solution)
    }

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print()
    print(f"Results saved to: {output_file}")
    print("=" * 80)

    return 0 if tier_status == "TIER_2_VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())
