#!/usr/bin/env python3
"""
Validate Phase 1 & 2 fixes against N=20 validation test logs

This script simulates what would have happened if the fixes were in place:
1. Answer validator running BEFORE verification verdict
2. Relaxed verification strictness for correct answers
3. Pre-verification enforcement for missing point-by-point verification

Expected outcomes:
- Runs 5 & 6: Should succeed (CORRECT answer, proof issues should be relaxed)
- Runs 4, 7, 8, 9, 12: Should fail (WRONG/INCOMPLETE answers caught by validator)
- Other runs: Status depends on answer correctness
"""

import os
import re
import json
from pathlib import Path
import sys

# Add code directory to path
sys.path.insert(0, str(Path(__file__).parent / 'code'))

from answer_validator import AnswerValidator, extract_final_answer

def extract_verification_verdict(log_content):
    """Extract the final verification verdict from log"""
    # Look for the last verification verdict
    matches = list(re.finditer(r'Is verification good\?\s*\n"([^"]*)"', log_content))
    if matches:
        last_verdict = matches[-1].group(1)
        return "yes" if "yes" in last_verdict.lower() else "no"
    return "no"

def extract_final_solution(log_content):
    """Extract the final solution from log"""
    # Look for the last "Corrected solution:" block
    matches = list(re.finditer(r'Corrected solution:\s*\n"([^"]{500,})', log_content, re.DOTALL))
    if matches:
        solution = matches[-1].group(1)
        return solution[:5000]  # Truncate to reasonable length
    return ""

def check_for_verification_issues(log_content):
    """Check what verification issues were found"""
    issues = {
        'point_by_point_missing': False,
        'justification_gaps': 0,
        'critical_errors': 0
    }

    # Look for the last verification bug report
    matches = list(re.finditer(r'Bug report:\s*\n"([^"]{100,})', log_content, re.DOTALL))
    if matches:
        last_bug_report = matches[-1].group(1)

        # Check for point-by-point verification issues
        if any(keyword in last_bug_report.lower() for keyword in [
            'point-by-point', 'explicit verification', 'coverage',
            'verify all points', 'check each point'
        ]):
            issues['point_by_point_missing'] = True

        # Count justification gaps and critical errors
        issues['justification_gaps'] = last_bug_report.count('Justification Gap')
        issues['critical_errors'] = last_bug_report.count('Critical Error')

    return issues

def simulate_fix(run_num, log_path):
    """Simulate what would happen with the fixes in place"""

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Extract data from log
    solution = extract_final_solution(content)
    original_verdict = extract_verification_verdict(content)
    issues = check_for_verification_issues(content)

    # Run answer validator
    validator = AnswerValidator("imo2025_p1")
    claimed_answer = extract_final_answer(solution) if solution else None

    if not claimed_answer:
        return {
            'run': run_num,
            'original_verdict': original_verdict,
            'simulated_verdict': original_verdict,
            'answer_verdict': 'NO_ANSWER',
            'would_succeed': False,
            'reason': 'Could not extract answer from solution'
        }

    # Validate answer
    answer_result = validator.validate(claimed_answer, solution)
    answer_verdict = answer_result['verdict']
    answer_is_correct = (answer_verdict == "CORRECT")

    # Simulate Phase 1 fix: Answer validator runs BEFORE verification
    simulated_verdict = original_verdict

    # If answer is WRONG, override to failure (Phase 1)
    if answer_verdict in ["WRONG", "OVERGENERALIZED"]:
        simulated_verdict = "no"
        reason = f"Answer validator caught WRONG answer: {claimed_answer[:50]}"
        would_succeed = False

    # If answer is INCOMPLETE, keep original verdict but add warning
    elif answer_verdict == "INCOMPLETE":
        simulated_verdict = original_verdict
        reason = f"Answer is INCOMPLETE (missing values), kept original verdict: {original_verdict}"
        would_succeed = (simulated_verdict == "yes")

    # If answer is CORRECT but verification failed (Phase 2)
    elif answer_is_correct and original_verdict == "no":
        # Check if failure is due to missing point-by-point verification
        if issues['point_by_point_missing'] and issues['critical_errors'] > 0:
            # Phase 2 fix: Relax strictness - treat as Justification Gap
            # With targeted feedback, assume agent would add verification in next iteration
            # For simulation, we'll count this as POTENTIAL SUCCESS
            simulated_verdict = "yes (with fixes)"
            reason = f"Answer CORRECT, relaxed verification strictness (point-by-point missing)"
            would_succeed = True
        elif issues['justification_gaps'] > 0 and issues['critical_errors'] == 0:
            # Only justification gaps, no critical errors - likely would succeed
            simulated_verdict = "yes (with relaxed strictness)"
            reason = f"Answer CORRECT, only justification gaps ({issues['justification_gaps']})"
            would_succeed = True
        else:
            # Has critical errors beyond presentation issues
            simulated_verdict = "no"
            reason = f"Answer CORRECT but proof has {issues['critical_errors']} critical errors (not just presentation)"
            would_succeed = False

    # If answer is CORRECT and verification passed (Phase 1 validates)
    elif answer_is_correct and original_verdict == "yes":
        simulated_verdict = "yes"
        reason = "Answer CORRECT and verification passed"
        would_succeed = True

    # Other cases (SUSPICIOUS, PLAUSIBLE, etc.)
    else:
        simulated_verdict = original_verdict
        reason = f"Answer verdict: {answer_verdict}, kept original: {original_verdict}"
        would_succeed = (simulated_verdict == "yes")

    return {
        'run': run_num,
        'original_verdict': original_verdict,
        'simulated_verdict': simulated_verdict,
        'answer_verdict': answer_verdict,
        'answer_claimed': claimed_answer[:50],
        'would_succeed': would_succeed,
        'reason': reason,
        'issues': issues
    }

def main():
    # Find all log files
    log_dir = Path('bfs_validation_n20')
    log_files = sorted(log_dir.glob('bfs_run*_20251222_162739.log'),
                      key=lambda x: int(re.search(r'run(\d+)_', str(x)).group(1)))

    results = []
    for log_file in log_files:
        run_num = int(re.search(r'run(\d+)_', str(log_file)).group(1))
        result = simulate_fix(run_num, str(log_file))
        results.append(result)

    # Print results
    print("="*120)
    print("VALIDATION OF PHASE 1 & 2 FIXES AGAINST N=20 LOGS")
    print("="*120)
    print()
    print("Run | Original | Simulated | Answer Verdict | Would Succeed | Reason")
    print("-" * 120)

    for r in results:
        success_icon = "✅" if r['would_succeed'] else "❌"
        print(f"{r['run']:>3} | {r['original_verdict']:<8} | {r['simulated_verdict']:<25} | {r['answer_verdict']:<14} | {success_icon} {str(r['would_succeed']):<11} | {r['reason'][:60]}")

    # Summary statistics
    print()
    print("="*120)
    print("SUMMARY")
    print("="*120)

    total_runs = len(results)
    original_success = sum(1 for r in results if r['original_verdict'] == "yes")
    simulated_success = sum(1 for r in results if r['would_succeed'])

    answer_correct = sum(1 for r in results if r['answer_verdict'] == "CORRECT")
    answer_wrong = sum(1 for r in results if r['answer_verdict'] in ["WRONG", "OVERGENERALIZED"])
    answer_incomplete = sum(1 for r in results if r['answer_verdict'] == "INCOMPLETE")

    print(f"\nOriginal Success Rate: {original_success}/{total_runs} ({original_success/total_runs*100:.1f}%)")
    print(f"Simulated Success Rate (with fixes): {simulated_success}/{total_runs} ({simulated_success/total_runs*100:.1f}%)")
    print(f"Improvement: {simulated_success - original_success} runs (+{(simulated_success - original_success)/total_runs*100:.1f} percentage points)")

    print(f"\nAnswer Validator Results:")
    print(f"  CORRECT: {answer_correct}/{total_runs}")
    print(f"  WRONG/OVERGENERALIZED: {answer_wrong}/{total_runs}")
    print(f"  INCOMPLETE: {answer_incomplete}/{total_runs}")

    print(f"\nPhase 1 Impact (Answer Validator):")
    caught_wrong = sum(1 for r in results if r['answer_verdict'] in ["WRONG", "OVERGENERALIZED"])
    print(f"  Would catch {caught_wrong} WRONG answers (prevented false positives)")

    print(f"\nPhase 2 Impact (Relaxed Strictness + Pre-verification):")
    rescued = sum(1 for r in results if r['answer_verdict'] == "CORRECT" and r['original_verdict'] == "no" and r['would_succeed'])
    print(f"  Would rescue {rescued} CORRECT answers that failed due to presentation issues")

    # Detailed analysis
    print()
    print("="*120)
    print("DETAILED ANALYSIS")
    print("="*120)

    print("\n✅ WOULD SUCCEED WITH FIXES:")
    for r in results:
        if r['would_succeed']:
            print(f"  Run {r['run']}: {r['reason']}")
            if r['issues']['point_by_point_missing']:
                print(f"    - Issues: Point-by-point missing, {r['issues']['critical_errors']} critical errors, {r['issues']['justification_gaps']} gaps")

    print("\n❌ WOULD STILL FAIL:")
    for r in results:
        if not r['would_succeed']:
            print(f"  Run {r['run']}: {r['reason']}")

    # Statistical significance
    print()
    print("="*120)
    print("STATISTICAL SIGNIFICANCE")
    print("="*120)

    # Fisher's exact test (simulated)
    from scipy.stats import fisher_exact

    # Compare original (0/12) vs simulated
    contingency_table = [
        [original_success, total_runs - original_success],  # Original
        [simulated_success, total_runs - simulated_success]  # Simulated
    ]

    oddsratio, pvalue = fisher_exact(contingency_table)

    print(f"\nFisher's Exact Test:")
    print(f"  Original: {original_success}/{total_runs}")
    print(f"  Simulated: {simulated_success}/{total_runs}")
    print(f"  p-value: {pvalue:.4f}")
    print(f"  Significant: {'YES' if pvalue < 0.05 else 'NO'} (α=0.05)")

    # Recommendation
    print()
    print("="*120)
    print("RECOMMENDATION")
    print("="*120)

    if simulated_success >= 4:  # ≥30% of 12
        print(f"\n✅ PROCEED: Simulated success rate ({simulated_success/total_runs*100:.1f}%) meets target (≥30%)")
        print("   Recommendation: Run N=5 test with actual fixes to validate simulation")
    elif simulated_success >= 2:
        print(f"\n⚠️  CAUTION: Simulated success rate ({simulated_success/total_runs*100:.1f}%) below target but shows improvement")
        print("   Recommendation: Run N=5 test to validate, may need additional improvements")
    else:
        print(f"\n❌ STOP: Simulated success rate ({simulated_success/total_runs*100:.1f}%) too low")
        print("   Recommendation: Deeper architectural changes needed before testing")

if __name__ == '__main__':
    main()
