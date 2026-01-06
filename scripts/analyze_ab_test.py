#!/usr/bin/env python3
"""
Analyze A/B test results for prescriptive feedback impact.

Usage:
    python analyze_ab_test.py ab_test_results/
    python analyze_ab_test.py --control ab_test_results/control --treatment ab_test_results/treatment
    python analyze_ab_test.py ab_test_p1/ --output results.json
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import statistics

def extract_metrics_from_log(log_file: Path) -> Dict:
    """Extract key metrics from agent log file."""
    try:
        with open(log_file, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Warning: Could not read {log_file}: {e}")
        return {}

    metrics = {
        'log_file': str(log_file),
        'success': bool(re.search(r'Found a correct solution', content)),
        'iterations': len(re.findall(r'=== Iteration \d+', content)),
        'prescriptive_warnings': content.count('## Automated Checker Warnings'),
        'prescriptive_fixes': content.count('## Prescriptive Feedback'),
        'critical_errors': content.count('Critical Error'),
        'justification_gaps': content.count('Justification Gap'),
        'log_size_kb': log_file.stat().st_size / 1024,
    }

    # Extract final score if available
    score_match = re.search(r'\[SCORE\] Current score: ([-\d.]+)', content)
    if score_match:
        metrics['final_score'] = float(score_match.group(1))
    else:
        metrics['final_score'] = None

    # Extract iteration count from various formats
    iteration_matches = re.findall(r'Iteration (\d+):', content)
    if iteration_matches:
        metrics['max_iteration'] = max(int(i) for i in iteration_matches)
    else:
        metrics['max_iteration'] = metrics['iterations']

    # Extract total cost if available
    cost_match = re.search(r'Total cost: \$?([\d.]+)', content)
    if cost_match:
        metrics['total_cost'] = float(cost_match.group(1))

    return metrics

def analyze_group(group_dir: Path, group_name: str) -> Dict:
    """Analyze all runs in a group."""
    log_files = sorted(group_dir.glob('run_*.log'))

    if not log_files:
        raise ValueError(f"No log files found in {group_dir}")

    all_metrics = []
    for f in log_files:
        m = extract_metrics_from_log(f)
        if m:  # Only add if metrics were extracted
            all_metrics.append(m)

    if not all_metrics:
        raise ValueError(f"No valid metrics extracted from {group_dir}")

    # Aggregate statistics
    success_count = sum(m['success'] for m in all_metrics)
    success_rate = success_count / len(all_metrics)

    avg_iterations = statistics.mean(m.get('max_iteration', m['iterations']) for m in all_metrics)
    median_iterations = statistics.median(m.get('max_iteration', m['iterations']) for m in all_metrics)

    avg_critical_errors = statistics.mean(m['critical_errors'] for m in all_metrics)
    avg_warnings = statistics.mean(m['prescriptive_warnings'] for m in all_metrics)
    avg_fixes = statistics.mean(m['prescriptive_fixes'] for m in all_metrics)

    # Calculate standard deviations
    if len(all_metrics) > 1:
        stdev_iterations = statistics.stdev(m.get('max_iteration', m['iterations']) for m in all_metrics)
    else:
        stdev_iterations = 0

    return {
        'group_name': group_name,
        'n_runs': len(all_metrics),
        'success_rate': success_rate,
        'successes': success_count,
        'failures': len(all_metrics) - success_count,
        'avg_iterations': avg_iterations,
        'median_iterations': median_iterations,
        'stdev_iterations': stdev_iterations,
        'avg_critical_errors': avg_critical_errors,
        'avg_prescriptive_warnings': avg_warnings,
        'avg_prescriptive_fixes': avg_fixes,
        'all_metrics': all_metrics
    }

def compare_groups(control: Dict, treatment: Dict) -> Dict:
    """Statistical comparison between control and treatment."""

    # Calculate improvements
    if control['success_rate'] > 0:
        success_lift = ((treatment['success_rate'] - control['success_rate']) /
                        control['success_rate']) * 100
    else:
        success_lift = float('inf') if treatment['success_rate'] > 0 else 0

    if control['avg_iterations'] > 0:
        iteration_reduction = ((control['avg_iterations'] - treatment['avg_iterations']) /
                               control['avg_iterations']) * 100
    else:
        iteration_reduction = 0

    if control['avg_critical_errors'] > 0:
        error_reduction = ((control['avg_critical_errors'] - treatment['avg_critical_errors']) /
                           control['avg_critical_errors']) * 100
    else:
        error_reduction = 0

    return {
        'success_lift_pct': success_lift,
        'iteration_reduction_pct': iteration_reduction,
        'error_reduction_pct': error_reduction,
        'absolute_success_delta': treatment['success_rate'] - control['success_rate'],
        'absolute_iteration_delta': treatment['avg_iterations'] - control['avg_iterations'],
        'absolute_error_delta': treatment['avg_critical_errors'] - control['avg_critical_errors'],
    }

def print_report(control: Dict, treatment: Dict, comparison: Dict):
    """Print formatted A/B test report."""

    print("\n" + "="*80)
    print("A/B TEST RESULTS: Prescriptive Feedback Impact")
    print("="*80)

    print(f"\n📊 SAMPLE SIZE:")
    print(f"   Control:   {control['n_runs']} runs")
    print(f"   Treatment: {treatment['n_runs']} runs")

    print(f"\n✅ SUCCESS RATE:")
    print(f"   Control:   {control['success_rate']:.1%} ({control['successes']}/{control['n_runs']} successful)")
    print(f"   Treatment: {treatment['success_rate']:.1%} ({treatment['successes']}/{treatment['n_runs']} successful)")

    delta_color = "+" if comparison['absolute_success_delta'] > 0 else ""
    print(f"   Δ:         {delta_color}{comparison['absolute_success_delta']:.1%} ({comparison['success_lift_pct']:+.1f}% relative lift)")

    print(f"\n🔁 AVERAGE ITERATIONS TO SOLUTION:")
    print(f"   Control:   {control['avg_iterations']:.1f} ± {control['stdev_iterations']:.1f} (median: {control['median_iterations']:.1f})")
    print(f"   Treatment: {treatment['avg_iterations']:.1f} ± {treatment['stdev_iterations']:.1f} (median: {treatment['median_iterations']:.1f})")
    print(f"   Δ:         {comparison['absolute_iteration_delta']:+.1f} iterations ({comparison['iteration_reduction_pct']:+.1f}% reduction)")

    print(f"\n❌ AVERAGE CRITICAL ERRORS PER RUN:")
    print(f"   Control:   {control['avg_critical_errors']:.1f}")
    print(f"   Treatment: {treatment['avg_critical_errors']:.1f}")
    print(f"   Δ:         {comparison['absolute_error_delta']:+.1f} errors ({comparison['error_reduction_pct']:+.1f}% reduction)")

    if treatment['avg_prescriptive_warnings'] > 0 or treatment['avg_prescriptive_fixes'] > 0:
        print(f"\n🔍 PRESCRIPTIVE FEEDBACK USAGE (Treatment Group Only):")
        print(f"   Avg Checker Warnings: {treatment['avg_prescriptive_warnings']:.1f} per run")
        print(f"   Avg Template Fixes:   {treatment['avg_prescriptive_fixes']:.1f} per run")

    print(f"\n" + "="*80)
    print("CONCLUSION:")
    print("="*80)

    if comparison['success_lift_pct'] > 20:
        print(f"✅ Prescriptive feedback shows STRONG POSITIVE impact:")
        print(f"   - {comparison['success_lift_pct']:.1f}% improvement in success rate")
        print(f"   - {abs(comparison['iteration_reduction_pct']):.1f}% {'reduction' if comparison['iteration_reduction_pct'] > 0 else 'increase'} in iterations")
        print(f"   - {abs(comparison['error_reduction_pct']):.1f}% {'reduction' if comparison['error_reduction_pct'] > 0 else 'increase'} in critical errors")
        print(f"\n   ✅ RECOMMEND: Deploy prescriptive feedback to production")
    elif comparison['success_lift_pct'] > 10:
        print(f"✅ Prescriptive feedback shows MODERATE POSITIVE impact:")
        print(f"   - {comparison['success_lift_pct']:.1f}% improvement in success rate")
        print(f"   - Consider larger sample size for statistical confidence")
        print(f"\n   ✅ RECOMMEND: Run larger test (20+ runs per group)")
    elif comparison['success_lift_pct'] > 0:
        print(f"⚠️  Prescriptive feedback shows WEAK POSITIVE impact:")
        print(f"   - {comparison['success_lift_pct']:.1f}% improvement in success rate")
        print(f"   - Not statistically significant with current sample size")
        print(f"\n   ⚠️  RECOMMEND: Investigate and tune, or run larger test")
    else:
        print(f"❌ Prescriptive feedback shows NO SIGNIFICANT impact:")
        print(f"   - {comparison['success_lift_pct']:.1f}% change in success rate (negative)")
        print(f"   - May need tuning or different approach")
        print(f"\n   ❌ RECOMMEND: Investigate root cause before deployment")

    # Sample size recommendation
    print(f"\n" + "="*80)
    print("SAMPLE SIZE ASSESSMENT:")
    print("="*80)
    n = control['n_runs']
    if n < 10:
        print(f"⚠️  Sample size ({n}) is SMALL - results may not be reliable")
        print(f"   Recommend: Run at least 10-20 runs per group for 95% confidence")
    elif n < 20:
        print(f"✅ Sample size ({n}) is ADEQUATE for large effects (>25% lift)")
        print(f"   For small effects (<10% lift), recommend 20+ runs per group")
    else:
        print(f"✅ Sample size ({n}) is GOOD for statistical confidence")

    print("\n")

def main():
    parser = argparse.ArgumentParser(
        description='Analyze A/B test results for prescriptive feedback impact',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_ab_test.py ab_test_p1/
  python analyze_ab_test.py --control ab_test_p1/control --treatment ab_test_p1/treatment
  python analyze_ab_test.py ab_test_p1/ --output results.json
        """
    )
    parser.add_argument('test_dir', nargs='?', help='Directory containing control/ and treatment/ subdirectories')
    parser.add_argument('--control', help='Control group directory')
    parser.add_argument('--treatment', help='Treatment group directory')
    parser.add_argument('--output', '-o', help='Save results to JSON file')

    args = parser.parse_args()

    # Determine control and treatment directories
    if args.test_dir:
        control_dir = Path(args.test_dir) / 'control'
        treatment_dir = Path(args.test_dir) / 'treatment'
    elif args.control and args.treatment:
        control_dir = Path(args.control)
        treatment_dir = Path(args.treatment)
    else:
        parser.error("Either provide test_dir or both --control and --treatment")

    # Verify directories exist
    if not control_dir.exists():
        print(f"Error: Control directory not found: {control_dir}")
        return 1
    if not treatment_dir.exists():
        print(f"Error: Treatment directory not found: {treatment_dir}")
        return 1

    # Analyze both groups
    try:
        control = analyze_group(control_dir, 'Control (No Prescriptive Feedback)')
        treatment = analyze_group(treatment_dir, 'Treatment (With Prescriptive Feedback)')
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    # Compare
    comparison = compare_groups(control, treatment)

    # Print report
    print_report(control, treatment, comparison)

    # Save to JSON if requested
    if args.output:
        results = {
            'control': {k: v for k, v in control.items() if k != 'all_metrics'},
            'treatment': {k: v for k, v in treatment.items() if k != 'all_metrics'},
            'comparison': comparison,
            'recommendation': 'deploy' if comparison['success_lift_pct'] > 20 else
                             'larger_test' if comparison['success_lift_pct'] > 10 else
                             'investigate' if comparison['success_lift_pct'] > 0 else
                             'do_not_deploy'
        }

        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"✅ Results saved to {args.output}")

    return 0

if __name__ == '__main__':
    exit(main())
