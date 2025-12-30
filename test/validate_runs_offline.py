#!/usr/bin/env python3
"""
Offline Answer Validation Script

Validates completed agent runs against ground truth WITHOUT providing feedback to LLM.
This script is run AFTER the agent completes, not during solving.

Usage:
    python validate_runs_offline.py <log_directory>
    python validate_runs_offline.py bfs_validation_test/

Output:
    - Success rate statistics
    - Detailed breakdown per run
    - CSV file for analysis
"""

import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Any
import json

# Import answer validator (for offline use only)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

try:
    from answer_validator import AnswerValidator, extract_final_answer
except ImportError as e:
    print(f"ERROR: Cannot import answer_validator module: {e}")
    print("Make sure code/answer_validator.py exists")
    sys.exit(1)


def extract_final_solution(log_file: Path) -> str:
    """Extract the final solution from log file."""
    with open(log_file, 'r') as f:
        content = f.read()

    # Find last corrected solution
    parts = content.split('>>>>>>> Corrected solution:')
    if len(parts) > 1:
        return parts[-1]

    return content


def check_success_marker(log_file: Path) -> bool:
    """Check if log has 'Correct solution found (first success)' marker."""
    with open(log_file, 'r') as f:
        content = f.read()

    return "Correct solution found (first success)" in content


def validate_run(log_file: Path, problem_id: str = "imo2025_p1") -> Dict[str, Any]:
    """
    Validate a single run offline (no feedback to LLM).

    Returns:
        {
            'run': run identifier,
            'had_success_marker': bool,
            'validator_verdict': str,
            'claimed_answer': set,
            'is_correct': bool,
            'iterations': int,
            'log_file': str
        }
    """
    # Extract solution and answer
    solution = extract_final_solution(log_file)
    claimed_answer_str = extract_final_answer(solution)

    # Check for success marker (agent's own judgment)
    had_success_marker = check_success_marker(log_file)

    # Count iterations
    with open(log_file, 'r') as f:
        content = f.read()
    iterations = content.count('>>>>>>> Corrected solution:')

    # Validate answer against ground truth
    validator = AnswerValidator(problem_id)

    result = {
        'log_file': log_file.name,
        'had_success_marker': had_success_marker,
        'iterations': iterations,
        'claimed_answer_str': claimed_answer_str[:100] if claimed_answer_str else "NOT_FOUND"
    }

    if claimed_answer_str:
        validation = validator.validate(claimed_answer_str, solution)
        result['validator_verdict'] = validation['verdict']
        result['confidence'] = validation.get('confidence', 0.0)

        # Extract claimed answer set
        details = validation.get('details', {})
        if 'claimed' in details:
            result['claimed_answer'] = details['claimed']
        else:
            result['claimed_answer'] = set()

        result['is_correct'] = (validation['verdict'] == 'CORRECT')
    else:
        result['validator_verdict'] = 'NO_ANSWER'
        result['claimed_answer'] = set()
        result['is_correct'] = False

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_runs_offline.py <log_directory>")
        print("Example: python validate_runs_offline.py bfs_validation_test/")
        sys.exit(1)

    log_dir = Path(sys.argv[1])

    if not log_dir.exists():
        print(f"ERROR: Directory not found: {log_dir}")
        sys.exit(1)

    # Find all log files
    log_files = sorted(log_dir.glob("*.log"))

    if not log_files:
        print(f"ERROR: No .log files found in {log_dir}")
        sys.exit(1)

    print("="*80)
    print("OFFLINE ANSWER VALIDATION")
    print("="*80)
    print(f"Directory: {log_dir}")
    print(f"Log files: {len(log_files)}")
    print()

    # Validate all runs
    results = []
    for log_file in log_files:
        try:
            result = validate_run(log_file)
            results.append(result)
        except Exception as e:
            print(f"ERROR validating {log_file.name}: {e}")
            continue

    # Compute statistics
    total = len(results)
    correct_count = sum(1 for r in results if r['is_correct'])
    success_marker_count = sum(1 for r in results if r['had_success_marker'])

    incomplete_count = sum(1 for r in results if r['validator_verdict'] == 'INCOMPLETE')
    wrong_count = sum(1 for r in results if r['validator_verdict'] == 'WRONG')

    print("="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print(f"Total runs: {total}")
    print(f"  ✅ CORRECT (validator): {correct_count}/{total} ({correct_count/total*100:.1f}%)")
    print(f"  ✅ Success marker (agent): {success_marker_count}/{total} ({success_marker_count/total*100:.1f}%)")
    print(f"  ❌ INCOMPLETE: {incomplete_count}/{total} ({incomplete_count/total*100:.1f}%)")
    print(f"  ❌ WRONG: {wrong_count}/{total} ({wrong_count/total*100:.1f}%)")
    print()

    # Discrepancy analysis
    discrepancy = success_marker_count - correct_count
    if discrepancy != 0:
        print(f"⚠️  DISCREPANCY: {abs(discrepancy)} runs have mismatch")
        print(f"   Agent thought success: {success_marker_count}")
        print(f"   Validator says correct: {correct_count}")
        print()

    print("="*80)
    print("DETAILED BREAKDOWN")
    print("="*80)
    print()

    # Sort by correctness then by file name
    results.sort(key=lambda r: (not r['is_correct'], r['log_file']))

    for r in results:
        marker_emoji = "🎯" if r['had_success_marker'] else "  "
        verdict_emoji = "✅" if r['is_correct'] else "❌"

        print(f"{verdict_emoji} {marker_emoji} {r['log_file']:40s} | "
              f"Verdict: {r['validator_verdict']:12s} | "
              f"Iters: {r['iterations']:2d} | "
              f"Claimed: {str(r['claimed_answer'])[:30]}")

    print()
    print("Legend:")
    print("  ✅ = Validator says CORRECT")
    print("  ❌ = Validator says INCOMPLETE/WRONG/NO_ANSWER")
    print("  🎯 = Agent marked 'Correct solution found (first success)'")
    print()

    # Save results to JSON
    output_file = log_dir / "validation_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            'summary': {
                'total': total,
                'correct': correct_count,
                'success_marker': success_marker_count,
                'incomplete': incomplete_count,
                'wrong': wrong_count,
                'success_rate': correct_count / total if total > 0 else 0
            },
            'results': results
        }, f, indent=2, default=str)

    print(f"Results saved to: {output_file}")
    print()

    # Return exit code based on success
    sys.exit(0 if correct_count > 0 else 1)


if __name__ == "__main__":
    main()
