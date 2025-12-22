#!/usr/bin/env python3
"""
Comprehensive analysis of N=20 validation test results
"""

import os
import re
import json
from pathlib import Path

def analyze_log(log_path):
    """Analyze a single log file"""
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    run_num = re.search(r'bfs_run(\d+)_', log_path).group(1)

    # Check completion status
    if "No solution found" in content:
        status = "FAILED"
    elif content.strip().endswith(">>>>>>>") or "Streaming Response:" in content[-500:]:
        status = "INCOMPLETE"
    else:
        status = "UNKNOWN"

    # Extract final answer
    boxed_answers = re.findall(r'\\boxed\{([^}]+)\}', content)
    final_answer = boxed_answers[-1] if boxed_answers else "NONE"

    # Count iterations
    iterations = re.findall(r'Iteration (\d+)', content)
    max_iteration = max([int(i) for i in iterations]) if iterations else 0

    # Count validator invocations
    validator_count = content.count("ANSWER VALIDATION")

    # Count critical errors in final iteration
    last_iteration_match = re.search(r'Iteration ' + str(max_iteration) + r'.*?(?=Iteration \d+|$)', content, re.DOTALL)
    if last_iteration_match:
        last_iter_text = last_iteration_match.group(0)[-10000:]  # Last 10KB
        critical_errors_final = last_iter_text.count("Critical Error")
    else:
        critical_errors_final = 0

    # Check if answer validator was triggered
    answer_wrong = "ANSWER VALIDATION FAILED" in content or "verdict\": \"WRONG" in content
    answer_incomplete = "verdict\": \"INCOMPLETE" in content
    answer_correct = "verdict\": \"CORRECT" in content

    return {
        'run': run_num,
        'status': status,
        'iterations': max_iteration,
        'final_answer': final_answer[:50],  # Truncate long answers
        'validator_invocations': validator_count,
        'critical_errors_final': critical_errors_final,
        'answer_wrong': answer_wrong,
        'answer_incomplete': answer_incomplete,
        'answer_correct': answer_correct
    }

def main():
    # Find all log files
    log_dir = Path('bfs_validation_n20')
    log_files = sorted(log_dir.glob('bfs_run*_20251222_162739.log'),
                      key=lambda x: int(re.search(r'run(\d+)_', str(x)).group(1)))

    results = []
    for log_file in log_files:
        results.append(analyze_log(str(log_file)))

    # Print results
    print("Run | Status | Iters | Val Calls | Crit Errs | Answer Status | Final Answer")
    print("-" * 100)
    for r in results:
        answer_status = "CORRECT" if r['answer_correct'] else ("WRONG" if r['answer_wrong'] else ("INCOMPLETE" if r['answer_incomplete'] else "N/A"))
        print(f"{r['run']:>3} | {r['status']:<10} | {r['iterations']:>5} | {r['validator_invocations']:>9} | {r['critical_errors_final']:>9} | {answer_status:<13} | {r['final_answer']}")

    # Summary statistics
    print("\n" + "=" * 100)
    print("SUMMARY STATISTICS")
    print("=" * 100)

    total_runs = len(results)
    failed_runs = sum(1 for r in results if r['status'] == "FAILED")
    incomplete_runs = sum(1 for r in results if r['status'] == "INCOMPLETE")
    success_runs = total_runs - failed_runs - incomplete_runs

    print(f"Total runs: {total_runs}")
    print(f"Failed: {failed_runs} ({failed_runs/total_runs*100:.1f}%)")
    print(f"Incomplete: {incomplete_runs} ({incomplete_runs/total_runs*100:.1f}%)")
    print(f"Success: {success_runs} ({success_runs/total_runs*100:.1f}%)")

    avg_iterations = sum(r['iterations'] for r in results) / len(results)
    print(f"\nAverage iterations: {avg_iterations:.1f}")

    avg_validator_calls = sum(r['validator_invocations'] for r in results) / len(results)
    print(f"Average validator invocations: {avg_validator_calls:.1f}")

    # Answer validator impact
    wrong_caught = sum(1 for r in results if r['answer_wrong'])
    incomplete_caught = sum(1 for r in results if r['answer_incomplete'])
    correct_validated = sum(1 for r in results if r['answer_correct'])

    print(f"\nAnswer Validator Results:")
    print(f"  Wrong answers caught: {wrong_caught}")
    print(f"  Incomplete answers caught: {incomplete_caught}")
    print(f"  Correct answers validated: {correct_validated}")

if __name__ == '__main__':
    main()
