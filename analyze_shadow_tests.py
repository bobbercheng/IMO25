#!/usr/bin/env python3
"""
Shadow Test Analysis - Engineering Perspective
Dr. Alex Rivera - Nvidia AI
"""

import json
import glob
from pathlib import Path
from typing import Dict, List, Any
import statistics

def load_results() -> List[Dict]:
    """Load all 11 shadow test results"""
    results = []
    for i in range(1, 12):
        path = f"/home/user/IMO25/week2_results_{i}.json"
        with open(path) as f:
            data = json.load(f)
            data['round'] = i
            results.append(data)
    return results

def analyze_agreement(results: List[Dict]) -> Dict:
    """Analyze agreement rates across all rounds"""
    agreements = [r['agreement']['rate_percent'] for r in results]
    return {
        'mean': statistics.mean(agreements),
        'median': statistics.median(agreements),
        'min': min(agreements),
        'max': max(agreements),
        'stdev': statistics.stdev(agreements) if len(agreements) > 1 else 0,
        'rounds_below_95': sum(1 for a in agreements if a < 95),
        'rounds_below_92': sum(1 for a in agreements if a < 92),
        'per_round': agreements
    }

def analyze_false_positives(results: List[Dict]) -> Dict:
    """Analyze FP rates for optimized system"""
    fp_rates = [r['optimized']['fp_rate_percent'] for r in results]
    fp_counts = [r['optimized']['false_positives'] for r in results]
    return {
        'mean_rate': statistics.mean(fp_rates),
        'median_rate': statistics.median(fp_rates),
        'max_rate': max(fp_rates),
        'stdev': statistics.stdev(fp_rates) if len(fp_rates) > 1 else 0,
        'rounds_above_5pct': sum(1 for r in fp_rates if r > 5),
        'rounds_above_3pct': sum(1 for r in fp_rates if r > 3),
        'total_fp_count': sum(fp_counts),
        'per_round': fp_rates
    }

def analyze_false_negatives(results: List[Dict]) -> Dict:
    """Analyze FN rates for optimized system"""
    fn_rates = [r['optimized']['fn_rate_percent'] for r in results]
    fn_counts = [r['optimized']['false_negatives'] for r in results]
    return {
        'mean_rate': statistics.mean(fn_rates),
        'median_rate': statistics.median(fn_rates),
        'max_rate': max(fn_rates),
        'stdev': statistics.stdev(fn_rates) if len(fn_rates) > 1 else 0,
        'rounds_above_2pct': sum(1 for r in fn_rates if r > 2),
        'total_fn_count': sum(fn_counts),
        'per_round': fn_rates
    }

def analyze_latency(results: List[Dict]) -> Dict:
    """Analyze latency performance"""
    baseline_latencies = [r['baseline']['avg_latency_seconds'] for r in results]
    optimized_latencies = [r['optimized']['avg_latency_seconds'] for r in results]
    improvements = [r['performance']['latency_improvement_percent'] for r in results]

    return {
        'baseline': {
            'mean': statistics.mean(baseline_latencies),
            'median': statistics.median(baseline_latencies),
            'min': min(baseline_latencies),
            'max': max(baseline_latencies),
            'stdev': statistics.stdev(baseline_latencies)
        },
        'optimized': {
            'mean': statistics.mean(optimized_latencies),
            'median': statistics.median(optimized_latencies),
            'min': min(optimized_latencies),
            'max': max(optimized_latencies),
            'stdev': statistics.stdev(optimized_latencies)
        },
        'improvement_percent': {
            'mean': statistics.mean(improvements),
            'median': statistics.median(improvements),
            'min': min(improvements),
            'max': max(improvements)
        }
    }

def analyze_per_test_variance(results: List[Dict]) -> Dict:
    """Analyze variance across test cases"""
    test_variance = {}

    for test_num in range(1, 7):
        test_name = None
        baseline_verdicts = []
        optimized_verdicts = []

        for r in results:
            for test in r['full_results']:
                if test['test_number'] == test_num:
                    if test_name is None:
                        test_name = test['test_name']
                    baseline_verdicts.append(test['baseline']['verdict'])
                    optimized_verdicts.append(test['optimized']['verdict'])

        # Count verdict consistency
        baseline_unique = len(set(baseline_verdicts))
        optimized_unique = len(set(optimized_verdicts))

        test_variance[f"test_{test_num}"] = {
            'name': test_name,
            'baseline_unique_verdicts': baseline_unique,
            'optimized_unique_verdicts': optimized_unique,
            'baseline_verdicts': baseline_verdicts,
            'optimized_verdicts': optimized_verdicts,
            'is_stable': optimized_unique <= 2  # yes/no variance acceptable
        }

    return test_variance

def calculate_go_decision(agreement: Dict, fp: Dict, fn: Dict) -> str:
    """Apply GO/NO-GO criteria"""
    mean_agreement = agreement['mean']
    mean_fp = fp['mean_rate']
    mean_fn = fn['mean_rate']

    # NO-GO conditions
    if mean_agreement < 92:
        return "NO-GO: Agreement < 92%"
    if mean_fp > 5:
        return "NO-GO: FP rate > 5%"

    # GO conditions
    if mean_agreement > 95 and mean_fp < 3 and mean_fn < 2:
        return "GO: All criteria met"

    # CONDITIONAL GO
    if 92 <= mean_agreement <= 95 and mean_fp <= 5:
        return "CONDITIONAL GO: Agreement 92-95%, requires monitoring"

    return "CONDITIONAL GO: Borderline performance"

def print_report(results: List[Dict]):
    """Print comprehensive engineering report"""

    print("="*80)
    print("SHADOW TEST ANALYSIS - ENGINEERING REPORT")
    print("Dr. Alex Rivera - Nvidia AI")
    print("="*80)
    print()

    # Agreement analysis
    agreement = analyze_agreement(results)
    print("## 1. AGREEMENT ANALYSIS (11 Rounds)")
    print(f"   Mean:    {agreement['mean']:.2f}%")
    print(f"   Median:  {agreement['median']:.2f}%")
    print(f"   Range:   {agreement['min']:.2f}% - {agreement['max']:.2f}%")
    print(f"   StdDev:  {agreement['stdev']:.2f}%")
    print(f"   Rounds < 95%: {agreement['rounds_below_95']}/11")
    print(f"   Rounds < 92%: {agreement['rounds_below_92']}/11")
    print(f"   Per-round: {[f'{x:.1f}' for x in agreement['per_round']]}")
    print()

    # False Positive analysis
    fp = analyze_false_positives(results)
    print("## 2. FALSE POSITIVE ANALYSIS (Optimized MEDIUM)")
    print(f"   Mean Rate:     {fp['mean_rate']:.2f}%")
    print(f"   Median Rate:   {fp['median_rate']:.2f}%")
    print(f"   Max Rate:      {fp['max_rate']:.2f}%")
    print(f"   StdDev:        {fp['stdev']:.2f}%")
    print(f"   Rounds > 5%:   {fp['rounds_above_5pct']}/11  ❌ CRITICAL")
    print(f"   Rounds > 3%:   {fp['rounds_above_3pct']}/11  ⚠️  WARNING")
    print(f"   Total FP count: {fp['total_fp_count']} across all rounds")
    print(f"   Per-round: {[f'{x:.1f}' for x in fp['per_round']]}")
    print()

    # False Negative analysis
    fn = analyze_false_negatives(results)
    print("## 3. FALSE NEGATIVE ANALYSIS (Optimized MEDIUM)")
    print(f"   Mean Rate:     {fn['mean_rate']:.2f}%")
    print(f"   Median Rate:   {fn['median_rate']:.2f}%")
    print(f"   Max Rate:      {fn['max_rate']:.2f}%")
    print(f"   StdDev:        {fn['stdev']:.2f}%")
    print(f"   Rounds > 2%:   {fn['rounds_above_2pct']}/11")
    print(f"   Total FN count: {fn['total_fn_count']} across all rounds")
    print(f"   Per-round: {[f'{x:.1f}' for x in fn['per_round']]}")
    print()

    # Latency analysis
    latency = analyze_latency(results)
    print("## 4. LATENCY PERFORMANCE")
    print("   Baseline (HIGH reasoning):")
    print(f"      Mean:   {latency['baseline']['mean']:.2f}s  ({latency['baseline']['mean']/60:.1f} min)")
    print(f"      Median: {latency['baseline']['median']:.2f}s")
    print(f"      Range:  {latency['baseline']['min']:.2f}s - {latency['baseline']['max']:.2f}s")
    print(f"      StdDev: {latency['baseline']['stdev']:.2f}s")
    print()
    print("   Optimized (MEDIUM reasoning):")
    print(f"      Mean:   {latency['optimized']['mean']:.2f}s")
    print(f"      Median: {latency['optimized']['median']:.2f}s")
    print(f"      Range:  {latency['optimized']['min']:.2f}s - {latency['optimized']['max']:.2f}s")
    print(f"      StdDev: {latency['optimized']['stdev']:.2f}s")
    print()
    print(f"   Improvement: {latency['improvement_percent']['mean']:.2f}% (mean)")
    print(f"   Speedup:     {latency['baseline']['mean'] / latency['optimized']['mean']:.1f}x faster")
    print()

    # Per-test variance
    test_variance = analyze_per_test_variance(results)
    print("## 5. PER-TEST STABILITY (Verdict Consistency)")
    for test_id, test_data in test_variance.items():
        stable = "✅ STABLE" if test_data['is_stable'] else "❌ UNSTABLE"
        print(f"   {test_data['name'][:50]}")
        print(f"      Baseline unique verdicts:  {test_data['baseline_unique_verdicts']}")
        print(f"      Optimized unique verdicts: {test_data['optimized_unique_verdicts']} {stable}")
        # Count verdict distribution
        opt_verdicts = test_data['optimized_verdicts']
        yes_count = opt_verdicts.count('yes')
        no_count = opt_verdicts.count('no')
        error_count = opt_verdicts.count('error')
        print(f"      Distribution: yes={yes_count}, no={no_count}, error={error_count}")
        print()

    # GO/NO-GO decision
    print("="*80)
    decision = calculate_go_decision(agreement, fp, fn)
    print(f"## GO/NO-GO DECISION: {decision}")
    print("="*80)
    print()

    # Detailed breakdown
    print("## DETAILED BREAKDOWN BY CRITERION")
    print(f"   ✅ Agreement > 95%:     {'PASS' if agreement['mean'] > 95 else 'FAIL'} ({agreement['mean']:.1f}%)")
    print(f"   ✅ Agreement > 92%:     {'PASS' if agreement['mean'] > 92 else 'FAIL'} ({agreement['mean']:.1f}%)")
    print(f"   ✅ FP rate < 3%:        {'PASS' if fp['mean_rate'] < 3 else 'FAIL'} ({fp['mean_rate']:.1f}%)")
    print(f"   ✅ FP rate < 5%:        {'PASS' if fp['mean_rate'] < 5 else 'FAIL'} ({fp['mean_rate']:.1f}%)")
    print(f"   ✅ FN rate < 2%:        {'PASS' if fn['mean_rate'] < 2 else 'FAIL'} ({fn['mean_rate']:.1f}%)")
    print()

    # Engineering concerns
    print("="*80)
    print("## ENGINEERING CONCERNS")
    print("="*80)

    # High variance
    if agreement['stdev'] > 15:
        print("   ⚠️  HIGH VARIANCE: Agreement StdDev > 15%")
        print(f"       → StdDev = {agreement['stdev']:.2f}%")
        print("       → RISK: Unpredictable production behavior")

    # FP rate violations
    if fp['rounds_above_5pct'] > 0:
        print(f"   ❌ CRITICAL: {fp['rounds_above_5pct']} rounds exceeded 5% FP rate")
        print("       → Violates NO-GO threshold")

    if fp['rounds_above_3pct'] > 3:
        print(f"   ⚠️  WARNING: {fp['rounds_above_3pct']} rounds exceeded 3% FP rate")
        print("       → Frequent quality degradation")

    # Low agreement rounds
    if agreement['rounds_below_92'] > 0:
        print(f"   ❌ CRITICAL: {agreement['rounds_below_92']} rounds below 92% agreement")
        print("       → Violates NO-GO threshold")

    if agreement['rounds_below_95'] > 5:
        print(f"   ⚠️  WARNING: {agreement['rounds_below_95']} rounds below 95% agreement")

    # Unstable tests
    unstable_tests = [t for t in test_variance.values() if not t['is_stable']]
    if unstable_tests:
        print(f"   ⚠️  UNSTABLE TESTS: {len(unstable_tests)} tests show high verdict variance")
        for t in unstable_tests:
            print(f"       → {t['name'][:60]}")

    print()

if __name__ == "__main__":
    results = load_results()
    print_report(results)
