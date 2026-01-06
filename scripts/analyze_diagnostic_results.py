#!/usr/bin/env python3
"""
Analyze Diagnostic Test Results
Purpose: Extract metrics from diagnostic logs to identify root cause
"""

import os
import sys
import json
import re
from pathlib import Path
from collections import defaultdict

def analyze_log_file(log_path):
    """Extract key metrics from a single log file."""
    metrics = {
        'resume_count': 0,
        'iteration_count': 0,
        'log_lines': 0,
        'prescriptive_feedback_count': 0,
        'feedback_reference_count': 0,
        'critical_error_count': 0,
        'success': False
    }

    with open(log_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')

        metrics['log_lines'] = len(lines)

        # Count resumes
        metrics['resume_count'] = content.count('Resuming from memory')

        # Count iterations
        iteration_matches = re.findall(r'Iteration (\d+)', content)
        if iteration_matches:
            metrics['iteration_count'] = max(int(i) for i in iteration_matches)

        # Count prescriptive feedback instances
        metrics['prescriptive_feedback_count'] = content.count('[PRESCRIPTIVE FEEDBACK]')

        # Count feedback references (case-insensitive)
        feedback_keywords = ['prescriptive', 'fix the', 'repair', 'address the error']
        for keyword in feedback_keywords:
            metrics['feedback_reference_count'] += content.lower().count(keyword.lower())

        # Count critical errors
        metrics['critical_error_count'] = content.count('Critical Error')

        # Check for success
        metrics['success'] = 'Found a correct solution' in content

    return metrics

def analyze_json_file(json_path):
    """Extract additional metrics from JSON memory file."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            return {
                'total_iterations': data.get('iteration', 0),
                'current_iteration': data.get('current_iteration', 0),
                'final_verdict': data.get('final_verdict', 'UNKNOWN')
            }
    except Exception as e:
        print(f"Warning: Could not parse {json_path}: {e}")
        return {}

def compare_test_results(test_name, control_metrics, treatment_metrics):
    """Compare control vs treatment for a specific test."""
    print(f"\n{'='*60}")
    print(f"TEST RESULTS: {test_name}")
    print(f"{'='*60}\n")

    # Calculate averages
    control_avg = {
        'resume_count': sum(m['resume_count'] for m in control_metrics) / len(control_metrics),
        'iteration_count': sum(m['iteration_count'] for m in control_metrics) / len(control_metrics),
        'log_lines': sum(m['log_lines'] for m in control_metrics) / len(control_metrics),
    }

    treatment_avg = {
        'resume_count': sum(m['resume_count'] for m in treatment_metrics) / len(treatment_metrics),
        'iteration_count': sum(m['iteration_count'] for m in treatment_metrics) / len(treatment_metrics),
        'log_lines': sum(m['log_lines'] for m in treatment_metrics) / len(treatment_metrics),
    }

    # Print comparison table
    print(f"{'Metric':<25} {'Control':<15} {'Treatment':<15} {'Δ':<15}")
    print("-" * 70)

    for metric in ['resume_count', 'iteration_count', 'log_lines']:
        c_val = control_avg[metric]
        t_val = treatment_avg[metric]
        delta = t_val - c_val
        delta_pct = (delta / c_val * 100) if c_val > 0 else 0

        print(f"{metric:<25} {c_val:<15.1f} {t_val:<15.1f} {delta:+.1f} ({delta_pct:+.1f}%)")

    # Interpret results
    print(f"\n{'INTERPRETATION':}")
    print("-" * 70)

    if treatment_avg['resume_count'] < control_avg['resume_count'] * 0.5:
        print("❌ Treatment shows SIGNIFICANT reduction in resume count")
        print("   → Indicates early termination issue")
    elif treatment_avg['resume_count'] >= control_avg['resume_count'] * 0.8:
        print("✅ Treatment shows SIMILAR resume count to control")
        print("   → Early termination issue resolved or not present")
    else:
        print("⚠️  Treatment shows MODERATE reduction in resume count")
        print("   → Partial improvement, may need further fixes")

    if treatment_avg['log_lines'] < control_avg['log_lines'] * 0.6:
        print("❌ Treatment shows SIGNIFICANT reduction in log size")
        print("   → Indicates less work being done")

    return {
        'control_avg': control_avg,
        'treatment_avg': treatment_avg,
        'resume_delta': treatment_avg['resume_count'] - control_avg['resume_count'],
        'resume_delta_pct': (treatment_avg['resume_count'] - control_avg['resume_count']) / control_avg['resume_count'] * 100 if control_avg['resume_count'] > 0 else 0
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_diagnostic_results.py <diagnostic_results_dir>")
        sys.exit(1)

    results_dir = Path(sys.argv[1])

    if not results_dir.exists():
        print(f"Error: Directory {results_dir} does not exist")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"DIAGNOSTIC RESULTS ANALYSIS")
    print(f"{'='*60}")
    print(f"Directory: {results_dir}")
    print(f"Files found: {len(list(results_dir.glob('*.log')))}")

    # Group files by test
    test_files = defaultdict(lambda: {'control': [], 'treatment': []})

    for log_file in results_dir.glob('*.log'):
        # Parse filename: test1_control_full_feedback_run1_20251219.log
        parts = log_file.stem.split('_')
        if len(parts) >= 3:
            test_num = parts[0]  # test1, test2, test3
            variant = 'control' if 'control' in log_file.stem else 'treatment'

            metrics = analyze_log_file(log_file)
            test_files[test_num][variant].append(metrics)

    # Analyze each test
    test_results = {}

    for test_num in sorted(test_files.keys()):
        control = test_files[test_num]['control']
        treatment = test_files[test_num]['treatment']

        if control and treatment:
            test_results[test_num] = compare_test_results(test_num, control, treatment)
        else:
            print(f"\n⚠️  WARNING: {test_num} incomplete (control: {len(control)}, treatment: {len(treatment)})")

    # Overall decision
    print(f"\n{'='*60}")
    print(f"DIAGNOSTIC DECISION")
    print(f"{'='*60}\n")

    # Check Test 1 (content isolation)
    if 'test1' in test_results:
        t1 = test_results['test1']
        print("TEST 1: Feedback Content Impact")
        if abs(t1['resume_delta_pct']) < 20:
            print("✅ FINDING: Content doesn't matter (< 20% difference)")
            print("   → Feedback content is not the root cause")
        else:
            print("❌ FINDING: Content matters (> 20% difference)")
            print("   → Detailed prescriptive content may cause issues")

    # Check Test 2 (length isolation)
    if 'test2' in test_results:
        t2 = test_results['test2']
        print("\nTEST 2: Feedback Length Impact")
        if t2['resume_delta_pct'] > 50:
            print("✅ FINDING: Short feedback improves resume count by >50%")
            print("   → Implement Fix 2 (simplify format) FIRST")
        elif t2['resume_delta_pct'] > 20:
            print("⚠️  FINDING: Short feedback improves resume count moderately")
            print("   → Consider combining with Fix 1")
        else:
            print("❌ FINDING: Length doesn't help")
            print("   → Root cause is elsewhere")

    # Check Test 3 (utilization)
    if 'test3' in test_files:
        print("\nTEST 3: Feedback Utilization")
        # Check logs for [DIAGNOSTIC] markers
        utilization_logs = list(results_dir.glob('test3*.log'))
        if utilization_logs:
            feedback_refs = 0
            total_iterations = 0

            for log in utilization_logs:
                with open(log, 'r') as f:
                    content = f.read()
                    feedback_refs += content.count('[DIAGNOSTIC] Feedback referenced in next prompt: True')
                    total_iterations += content.count('[DIAGNOSTIC] Feedback received')

            ref_rate = feedback_refs / total_iterations * 100 if total_iterations > 0 else 0

            print(f"   Feedback reference rate: {ref_rate:.1f}%")

            if ref_rate < 10:
                print("❌ FINDING: Agent rarely references feedback (<10%)")
                print("   → Implement Fix 1 Option A (add instructions)")
            elif ref_rate < 30:
                print("⚠️  FINDING: Agent sometimes references feedback (10-30%)")
                print("   → May need Fix 1 Option B (separate delivery)")
            else:
                print("✅ FINDING: Agent frequently references feedback (>30%)")
                print("   → Utilization is not the primary issue")

    # Final recommendation
    print(f"\n{'='*60}")
    print(f"RECOMMENDED NEXT STEP")
    print(f"{'='*60}\n")

    if 'test2' in test_results and test_results['test2']['resume_delta_pct'] > 50:
        print("🎯 RECOMMENDATION: Implement Fix 2 Phase 0 (Simplify Feedback Format)")
        print("   Rationale: Short feedback shows >50% improvement")
        print("   Action: Remove placeholders, checklists, reduce to 15-20 lines")
        print("   Timeline: 4 hours implementation + 2 hours testing")
    elif 'test1' in test_results:
        print("🎯 RECOMMENDATION: Implement Fix 1 Option A (Add Instructions)")
        print("   Rationale: Feedback content/length not primary issue")
        print("   Action: Add short instruction about using prescriptive feedback")
        print("   Timeline: 1 hour implementation + 2 hours testing")
    else:
        print("⚠️  RECOMMENDATION: Gather more data")
        print("   Rationale: Diagnostic results inconclusive")
        print("   Action: Complete all 6 diagnostic runs, then re-analyze")

    print()

if __name__ == '__main__':
    main()
