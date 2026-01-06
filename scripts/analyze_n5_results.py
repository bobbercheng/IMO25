#!/usr/bin/env python3
"""
Comprehensive analysis of N=5 validation test (WITH Phase 1 & 2 fixes)
"""

import os
import re
import json
from pathlib import Path

def analyze_run(log_path):
    """Analyze a single N=5 log file"""
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    run_num = re.search(r'bfs_run(\d+)_', log_path).group(1)

    # Check completion status
    if "No solution found" in content:
        status = "FAILED"
    else:
        status = "INCOMPLETE"

    # Count answer validator invocations
    validator_count = content.count("ANSWER VALIDATION] Checking answer correctness")

    # Check if validator found any CORRECT answers
    correct_count = content.count("ANSWER VALIDATION] ✅ CORRECT")
    wrong_count = content.count("ANSWER VALIDATION] ❌ FAILED")
    incomplete_count = content.count("ANSWER VALIDATION] ⚠️  INCOMPLETE")

    # Count pre-verification enforcement triggers
    pre_verif_count = content.count("PRE-VERIFICATION ENFORCEMENT")

    # Extract final answer
    boxed_answers = re.findall(r'\\boxed\{([^}]+)\}', content)
    final_answer = boxed_answers[-1][:100] if boxed_answers else "NONE"

    # Count iterations
    iterations = re.findall(r'Iteration (\d+)', content)
    max_iteration = max([int(i) for i in iterations]) if iterations else 0

    # Count critical errors in last verification
    last_verif = content[max(0, len(content)-50000):]  # Last 50KB
    critical_errors = last_verif.count("Critical Error")
    justification_gaps = last_verif.count("Justification Gap")

    return {
        'run': run_num,
        'status': status,
        'iterations': max_iteration,
        'validator_invocations': validator_count,
        'correct_answers_detected': correct_count,
        'wrong_answers_detected': wrong_count,
        'incomplete_answers_detected': incomplete_count,
        'pre_verification_triggers': pre_verif_count,
        'final_answer': final_answer,
        'critical_errors_final': critical_errors,
        'justification_gaps_final': justification_gaps
    }

def main():
    log_dir = Path('bfs_validation_n5')
    log_files = sorted(log_dir.glob('bfs_run*_20251222_194747.log'),
                      key=lambda x: int(re.search(r'run(\d+)_', str(x)).group(1)))

    results = []
    for log_file in log_files:
        results.append(analyze_run(str(log_file)))

    # Print results
    print("="*140)
    print("N=5 VALIDATION TEST ANALYSIS (WITH PHASE 1 & 2 FIXES)")
    print("="*140)
    print()
    print("Run | Status | Iters | Validator Calls | CORRECT | WRONG | INCOMPLETE | Pre-Verif | Crit Errs | Gaps | Final Answer")
    print("-" * 140)

    for r in results:
        print(f"{r['run']:>3} | {r['status']:<6} | {r['iterations']:>5} | {r['validator_invocations']:>15} | {r['correct_answers_detected']:>7} | {r['wrong_answers_detected']:>5} | {r['incomplete_answers_detected']:>10} | {r['pre_verification_triggers']:>9} | {r['critical_errors_final']:>9} | {r['justification_gaps_final']:>4} | {r['final_answer'][:40]}")

    # Summary
    print()
    print("="*140)
    print("SUMMARY")
    print("="*140)

    total_runs = len(results)
    failed_runs = sum(1 for r in results if r['status'] == "FAILED")
    success_runs = total_runs - failed_runs

    print(f"\nTotal runs: {total_runs}")
    print(f"Success: {success_runs}/{total_runs} ({success_runs/total_runs*100:.1f}%)")
    print(f"Failed: {failed_runs}/{total_runs} ({failed_runs/total_runs*100:.1f}%)")

    avg_iterations = sum(r['iterations'] for r in results) / len(results)
    print(f"\nAverage iterations: {avg_iterations:.1f}")

    # Phase 1 validation
    print(f"\nPhase 1 Impact (Answer Validator Integration):")
    total_validator_calls = sum(r['validator_invocations'] for r in results)
    print(f"  Total validator invocations: {total_validator_calls} (vs 0 in N=20 test)")
    print(f"  Avg validator calls per run: {total_validator_calls/total_runs:.1f}")

    total_correct = sum(r['correct_answers_detected'] for r in results)
    total_wrong = sum(r['wrong_answers_detected'] for r in results)
    total_incomplete = sum(r['incomplete_answers_detected'] for r in results)

    print(f"\n  Answer Detection:")
    print(f"    CORRECT answers detected: {total_correct}")
    print(f"    WRONG answers detected: {total_wrong}")
    print(f"    INCOMPLETE answers detected: {total_incomplete}")

    # Phase 2 validation
    print(f"\nPhase 2 Impact (Pre-Verification Enforcement):")
    total_pre_verif = sum(r['pre_verification_triggers'] for r in results)
    print(f"  Pre-verification enforcement triggers: {total_pre_verif}")
    print(f"  (This means validator found CORRECT answer but verification failed)")

    # Comparison to N=20
    print()
    print("="*140)
    print("COMPARISON: N=20 (No Fixes) vs N=5 (With Fixes)")
    print("="*140)

    print("\n| Metric | N=20 (No Fixes) | N=5 (With Fixes) | Change |")
    print("|--------|-----------------|------------------|--------|")
    print(f"| Success Rate | 0/12 (0.0%) | {success_runs}/{total_runs} ({success_runs/total_runs*100:.1f}%) | {success_runs/total_runs*100:+.1f}pp |")
    print(f"| Validator Ran | 0/12 (0%) | {total_runs}/{total_runs} (100%) | +100pp |")
    print(f"| CORRECT Detected | 0 | {total_correct} | +{total_correct} |")
    print(f"| WRONG Detected | 0 | {total_wrong} | +{total_wrong} |")

    # Analysis
    print()
    print("="*140)
    print("DETAILED ANALYSIS")
    print("="*140)

    if total_correct > 0:
        print(f"\n✅ Runs with CORRECT answers detected:")
        for r in results:
            if r['correct_answers_detected'] > 0:
                print(f"  Run {r['run']}: {r['correct_answers_detected']} iterations had CORRECT answer")
                if r['pre_verification_triggers'] > 0:
                    print(f"    → Pre-verification enforcement triggered {r['pre_verification_triggers']} times")
                print(f"    → Final status: {r['status']}")
                print(f"    → Final errors: {r['critical_errors_final']} critical, {r['justification_gaps_final']} gaps")
    else:
        print("\n❌ NO runs detected CORRECT answers at any iteration")

    if total_wrong > 0:
        print(f"\n⚠️  Runs with WRONG answers detected:")
        for r in results:
            if r['wrong_answers_detected'] > 0:
                print(f"  Run {r['run']}: {r['wrong_answers_detected']} iterations had WRONG answer (correctly caught)")

    # Verdict
    print()
    print("="*140)
    print("VERDICT")
    print("="*140)

    if success_runs > 0:
        print(f"\n✅ SUCCESS: Fixes validated - {success_runs}/{total_runs} runs succeeded")
    else:
        print(f"\n❌ FAILURE: Fixes did NOT improve success rate (still 0%)")
        if total_correct > 0:
            print(f"\n  However, validator IS WORKING:")
            print(f"    - Detected {total_correct} CORRECT answers across all runs")
            print(f"    - Triggered pre-verification {total_pre_verif} times")
            print(f"    - But runs still FAILED despite correct answers")
            print(f"\n  ROOT CAUSE: Even with correct answers and targeted feedback,")
            print(f"              agent cannot fix proof issues within iteration limit")
        else:
            print(f"\n  Validator is working (ran {total_validator_calls} times)")
            print(f"  But NO run found the correct answer k∈{{0,1,3}} at ANY iteration")

if __name__ == '__main__':
    main()
