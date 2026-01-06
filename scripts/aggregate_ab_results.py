#!/usr/bin/env python3
"""
Aggregate A/B test results across multiple problems.

Usage:
    python aggregate_ab_results.py ab_test_imo01/ ab_test_imo02/ ab_test_imo03/
    python aggregate_ab_results.py ab_test_imo*/ --output aggregate_results.json
"""

import argparse
import json
import statistics
from pathlib import Path
from typing import List, Dict
from analyze_ab_test import analyze_group, compare_groups

def aggregate_results(test_dirs: List[Path]) -> Dict:
    """Aggregate results across multiple test directories."""

    all_results = []

    for test_dir in test_dirs:
        problem_name = test_dir.name
        control_dir = test_dir / 'control'
        treatment_dir = test_dir / 'treatment'

        if not control_dir.exists() or not treatment_dir.exists():
            print(f"Warning: Skipping {test_dir} - missing control or treatment directory")
            continue

        try:
            control = analyze_group(control_dir, f'{problem_name} Control')
            treatment = analyze_group(treatment_dir, f'{problem_name} Treatment')
            comparison = compare_groups(control, treatment)

            all_results.append({
                'problem': problem_name,
                'control': control,
                'treatment': treatment,
                'comparison': comparison
            })
        except Exception as e:
            print(f"Warning: Error processing {test_dir}: {e}")
            continue

    if not all_results:
        raise ValueError("No valid test results found")

    # Aggregate statistics
    total_control_runs = sum(r['control']['n_runs'] for r in all_results)
    total_treatment_runs = sum(r['treatment']['n_runs'] for r in all_results)

    total_control_success = sum(r['control']['successes'] for r in all_results)
    total_treatment_success = sum(r['treatment']['successes'] for r in all_results)

    overall_control_rate = total_control_success / total_control_runs if total_control_runs > 0 else 0
    overall_treatment_rate = total_treatment_success / total_treatment_runs if total_treatment_runs > 0 else 0

    # Calculate average lift across problems
    avg_success_lift = statistics.mean(r['comparison']['success_lift_pct'] for r in all_results)
    avg_iteration_reduction = statistics.mean(r['comparison']['iteration_reduction_pct'] for r in all_results)
    avg_error_reduction = statistics.mean(r['comparison']['error_reduction_pct'] for r in all_results)

    # Calculate standard deviations
    if len(all_results) > 1:
        stdev_success_lift = statistics.stdev(r['comparison']['success_lift_pct'] for r in all_results)
        stdev_iteration_reduction = statistics.stdev(r['comparison']['iteration_reduction_pct'] for r in all_results)
    else:
        stdev_success_lift = 0
        stdev_iteration_reduction = 0

    return {
        'n_problems': len(all_results),
        'total_runs': total_control_runs + total_treatment_runs,
        'aggregate': {
            'control': {
                'total_runs': total_control_runs,
                'total_successes': total_control_success,
                'success_rate': overall_control_rate
            },
            'treatment': {
                'total_runs': total_treatment_runs,
                'total_successes': total_treatment_success,
                'success_rate': overall_treatment_rate
            },
            'comparison': {
                'overall_success_lift_pct': ((overall_treatment_rate - overall_control_rate) /
                                             max(overall_control_rate, 0.01)) * 100,
                'avg_success_lift_pct': avg_success_lift,
                'stdev_success_lift_pct': stdev_success_lift,
                'avg_iteration_reduction_pct': avg_iteration_reduction,
                'stdev_iteration_reduction_pct': stdev_iteration_reduction,
                'avg_error_reduction_pct': avg_error_reduction,
            }
        },
        'by_problem': all_results
    }

def print_aggregate_report(results: Dict):
    """Print formatted aggregate report."""

    print("\n" + "="*80)
    print("AGGREGATE A/B TEST RESULTS: Prescriptive Feedback Impact")
    print("="*80)

    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   Problems Tested: {results['n_problems']}")
    print(f"   Total Runs:      {results['total_runs']}")
    print(f"   Control Runs:    {results['aggregate']['control']['total_runs']}")
    print(f"   Treatment Runs:  {results['aggregate']['treatment']['total_runs']}")

    print(f"\n✅ AGGREGATED SUCCESS RATE:")
    ctrl = results['aggregate']['control']
    trt = results['aggregate']['treatment']
    cmp = results['aggregate']['comparison']

    print(f"   Control:   {ctrl['success_rate']:.1%} ({ctrl['total_successes']}/{ctrl['total_runs']})")
    print(f"   Treatment: {trt['success_rate']:.1%} ({trt['total_successes']}/{trt['total_runs']})")
    print(f"   Overall Δ: {cmp['overall_success_lift_pct']:+.1f}% lift")

    print(f"\n📈 AVERAGE IMPACT ACROSS PROBLEMS:")
    print(f"   Success Lift:        {cmp['avg_success_lift_pct']:+.1f}% ± {cmp['stdev_success_lift_pct']:.1f}%")
    print(f"   Iteration Reduction: {cmp['avg_iteration_reduction_pct']:+.1f}% ± {cmp['stdev_iteration_reduction_pct']:.1f}%")
    print(f"   Error Reduction:     {cmp['avg_error_reduction_pct']:+.1f}%")

    print(f"\n📋 RESULTS BY PROBLEM:")
    print(f"   {'Problem':<20} {'Control':<12} {'Treatment':<12} {'Lift':<10} {'Iter Δ':<10}")
    print(f"   {'-'*20} {'-'*12} {'-'*12} {'-'*10} {'-'*10}")

    for r in results['by_problem']:
        ctrl_rate = r['control']['success_rate']
        trt_rate = r['treatment']['success_rate']
        lift = r['comparison']['success_lift_pct']
        iter_delta = r['comparison']['iteration_reduction_pct']

        print(f"   {r['problem']:<20} {ctrl_rate:>6.1%} ({r['control']['successes']}/{r['control']['n_runs']:>2})  "
              f"{trt_rate:>6.1%} ({r['treatment']['successes']}/{r['treatment']['n_runs']:>2})  "
              f"{lift:>7.1f}%  {iter_delta:>7.1f}%")

    print(f"\n" + "="*80)
    print("CONCLUSION:")
    print("="*80)

    if cmp['overall_success_lift_pct'] > 15:
        print(f"✅ STRONG POSITIVE IMPACT across all problems:")
        print(f"   - {cmp['overall_success_lift_pct']:.1f}% overall improvement in success rate")
        print(f"   - {cmp['avg_success_lift_pct']:.1f}% average lift per problem")
        print(f"   - Consistent across {results['n_problems']} problems")
        print(f"\n   ✅ RECOMMEND: Deploy prescriptive feedback to production")
    elif cmp['overall_success_lift_pct'] > 5:
        print(f"✅ MODERATE POSITIVE IMPACT:")
        print(f"   - {cmp['overall_success_lift_pct']:.1f}% overall improvement")
        print(f"   - Results vary across problems (±{cmp['stdev_success_lift_pct']:.1f}%)")
        print(f"\n   ✅ RECOMMEND: Deploy with monitoring")
    elif cmp['overall_success_lift_pct'] > 0:
        print(f"⚠️  WEAK POSITIVE IMPACT:")
        print(f"   - {cmp['overall_success_lift_pct']:.1f}% overall improvement")
        print(f"   - High variance across problems")
        print(f"\n   ⚠️  RECOMMEND: Investigate variability, tune system")
    else:
        print(f"❌ NO POSITIVE IMPACT:")
        print(f"   - {cmp['overall_success_lift_pct']:.1f}% change (negative)")
        print(f"\n   ❌ RECOMMEND: Do not deploy, investigate issues")

    print("\n")

def main():
    parser = argparse.ArgumentParser(
        description='Aggregate A/B test results across multiple problems',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python aggregate_ab_results.py ab_test_imo01/ ab_test_imo02/ ab_test_imo03/
  python aggregate_ab_results.py ab_test_imo*/ --output aggregate.json
        """
    )
    parser.add_argument('test_dirs', nargs='+', type=Path,
                        help='Test directories (e.g., ab_test_imo01/ ab_test_imo02/)')
    parser.add_argument('--output', '-o', help='Save results to JSON file')

    args = parser.parse_args()

    # Aggregate results
    try:
        results = aggregate_results(args.test_dirs)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    # Print report
    print_aggregate_report(results)

    # Save to JSON if requested
    if args.output:
        # Remove detailed metrics to keep JSON clean
        clean_results = {
            'n_problems': results['n_problems'],
            'total_runs': results['total_runs'],
            'aggregate': results['aggregate'],
            'by_problem': [
                {
                    'problem': r['problem'],
                    'control': {k: v for k, v in r['control'].items() if k != 'all_metrics'},
                    'treatment': {k: v for k, v in r['treatment'].items() if k != 'all_metrics'},
                    'comparison': r['comparison']
                }
                for r in results['by_problem']
            ]
        }

        with open(args.output, 'w') as f:
            json.dump(clean_results, f, indent=2)
        print(f"✅ Results saved to {args.output}")

    return 0

if __name__ == '__main__':
    exit(main())
