#!/usr/bin/env python3
"""
Analyze 20-round validation test results for Option 1 (Verification Constraints).
"""

import json
import glob
from pathlib import Path
import statistics

def load_validation_results():
    """Load all 20 validation JSON files."""
    results = []
    for i in range(1, 21):
        path = f"week2_results/validation_r{i}.json"
        with open(path) as f:
            data = json.load(f)
            data['round'] = i
            results.append(data)
    return results

def extract_per_test_metrics(results):
    """Extract success rates for each test across all rounds."""
    test_results = {i: {'baseline': [], 'optimized': []} for i in range(1, 7)}

    for result in results:
        for test in result['full_results']:
            test_num = test['test_number']
            test_results[test_num]['baseline'].append(test['comparison']['baseline_correct'])
            test_results[test_num]['optimized'].append(test['comparison']['optimized_correct'])

    return test_results

def main():
    results = load_validation_results()

    # Extract aggregate metrics
    agreement_rates = [r['agreement']['rate_percent'] for r in results]
    baseline_accuracy = [r['baseline']['accuracy_percent'] for r in results]
    optimized_accuracy = [r['optimized']['accuracy_percent'] for r in results]
    baseline_fp = [r['baseline']['false_positives'] for r in results]
    baseline_fn = [r['baseline']['false_negatives'] for r in results]
    optimized_fp = [r['optimized']['false_positives'] for r in results]
    optimized_fn = [r['optimized']['false_negatives'] for r in results]
    baseline_latency = [r['baseline']['avg_latency_seconds'] for r in results]
    optimized_latency = [r['optimized']['avg_latency_seconds'] for r in results]

    print("=" * 80)
    print("20-ROUND VALIDATION SUMMARY - Option 1 (Verification Constraints)")
    print("=" * 80)
    print()

    # Round-by-round table
    print("ROUND-BY-ROUND METRICS")
    print("-" * 80)
    print(f"{'Round':<6} {'Agree%':<8} {'Base Acc%':<11} {'Opt Acc%':<11} {'Base FP/FN':<12} {'Opt FP/FN':<12}")
    print("-" * 80)

    for r in results:
        round_num = r['round']
        agree = r['agreement']['rate_percent']
        base_acc = r['baseline']['accuracy_percent']
        opt_acc = r['optimized']['accuracy_percent']
        base_fp_fn = f"{r['baseline']['false_positives']}/{r['baseline']['false_negatives']}"
        opt_fp_fn = f"{r['optimized']['false_positives']}/{r['optimized']['false_negatives']}"
        print(f"{round_num:<6} {agree:<8.2f} {base_acc:<11.2f} {opt_acc:<11.2f} {base_fp_fn:<12} {opt_fp_fn:<12}")

    print("-" * 80)
    print()

    # Summary statistics
    print("SUMMARY STATISTICS (across 20 rounds)")
    print("-" * 80)
    print(f"{'Metric':<30} {'Mean':<10} {'StdDev':<10} {'Min':<10} {'Max':<10}")
    print("-" * 80)

    stats = [
        ("Agreement Rate %", agreement_rates),
        ("Baseline Accuracy %", baseline_accuracy),
        ("Optimized Accuracy %", optimized_accuracy),
        ("Baseline FP Count", baseline_fp),
        ("Baseline FN Count", baseline_fn),
        ("Optimized FP Count", optimized_fp),
        ("Optimized FN Count", optimized_fn),
        ("Baseline Latency (s)", baseline_latency),
        ("Optimized Latency (s)", optimized_latency),
    ]

    for name, values in stats:
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0
        min_val = min(values)
        max_val = max(values)
        print(f"{name:<30} {mean:<10.2f} {stdev:<10.2f} {min_val:<10.2f} {max_val:<10.2f}")

    print("-" * 80)
    print()

    # Expected vs Actual
    print("EXPECTED vs ACTUAL PERFORMANCE")
    print("-" * 80)
    print(f"{'Metric':<30} {'Expected':<15} {'Actual':<15} {'Status':<10}")
    print("-" * 80)

    # Truncation rate (from JSON errors)
    truncation_count = sum(1 for r in results for test in r['full_results']
                          if test['baseline'].get('error') or test['optimized'].get('error'))
    total_tests = len(results) * 6
    truncation_rate = (truncation_count / total_tests) * 100

    # Accuracy
    mean_opt_acc = statistics.mean(optimized_accuracy)
    mean_base_acc = statistics.mean(baseline_accuracy)

    # False negatives
    mean_opt_fn = statistics.mean(optimized_fn)
    mean_base_fn = statistics.mean(baseline_fn)
    opt_fn_rate = (sum(optimized_fn) / (len(results) * 3)) * 100  # 3 expected PASS tests

    # Latency (P95)
    p95_opt_latency = sorted(optimized_latency)[int(0.95 * len(optimized_latency))]

    expected_actual = [
        ("Truncation Rate", "<2%", f"{truncation_rate:.2f}%", "✅ PASS" if truncation_rate < 2 else "❌ FAIL"),
        ("Optimized Accuracy", ">95%", f"{mean_opt_acc:.2f}%", "✅ PASS" if mean_opt_acc > 95 else "❌ FAIL"),
        ("Baseline Accuracy", ">95%", f"{mean_base_acc:.2f}%", "✅ PASS" if mean_base_acc > 95 else "❌ FAIL"),
        ("Optimized FN Rate", "<5%", f"{opt_fn_rate:.2f}%", "✅ PASS" if opt_fn_rate < 5 else "❌ FAIL"),
        ("P95 Latency (Opt)", "<100s", f"{p95_opt_latency:.2f}s", "✅ PASS" if p95_opt_latency < 100 else "❌ FAIL"),
    ]

    for metric, expected, actual, status in expected_actual:
        print(f"{metric:<30} {expected:<15} {actual:<15} {status:<10}")

    print("-" * 80)
    print()

    # Per-test breakdown
    print("PER-TEST SUCCESS RATES (across 20 rounds)")
    print("-" * 80)
    test_results = extract_per_test_metrics(results)
    test_names = [
        "Test 1: Complete Proof (PASS expected)",
        "Test 2: Alternative Proof (PASS expected)",
        "Test 3: Missing k=2 proof (FAIL expected)",
        "Test 4: Missing constructions (FAIL expected)",
        "Test 5: Wrong answer (FAIL expected)",
        "Test 6: Justification gap (PASS expected)",
    ]

    print(f"{'Test':<45} {'Base Success':<15} {'Opt Success':<15} {'Delta':<10}")
    print("-" * 80)

    for i, name in enumerate(test_names, 1):
        base_success = sum(test_results[i]['baseline']) / 20 * 100
        opt_success = sum(test_results[i]['optimized']) / 20 * 100
        delta = opt_success - base_success
        delta_str = f"{delta:+.1f}%"
        print(f"{name:<45} {base_success:>6.1f}% ({sum(test_results[i]['baseline'])}/20)    {opt_success:>6.1f}% ({sum(test_results[i]['optimized'])}/20)    {delta_str:<10}")

    print("-" * 80)
    print()

    # Truncation analysis
    print("TRUNCATION ANALYSIS")
    print("-" * 80)
    baseline_errors = sum(1 for r in results for test in r['full_results']
                         if test['baseline'].get('error'))
    optimized_errors = sum(1 for r in results for test in r['full_results']
                          if test['optimized'].get('error'))

    print(f"Baseline (HIGH) truncation errors:  {baseline_errors}/{total_tests} ({baseline_errors/total_tests*100:.1f}%)")
    print(f"Optimized (MEDIUM) truncation errors: {optimized_errors}/{total_tests} ({optimized_errors/total_tests*100:.1f}%)")
    print(f"Total truncation events: {truncation_count}/{total_tests} ({truncation_rate:.1f}%)")
    print()

    # Which tests caused truncation?
    print("Truncation by test:")
    for i in range(1, 7):
        base_trunc = sum(1 for r in results for test in r['full_results']
                        if test['test_number'] == i and test['baseline'].get('error'))
        opt_trunc = sum(1 for r in results for test in r['full_results']
                       if test['test_number'] == i and test['optimized'].get('error'))
        if base_trunc > 0 or opt_trunc > 0:
            print(f"  Test {i}: Baseline {base_trunc}/20, Optimized {opt_trunc}/20")

    print("-" * 80)
    print()

    # Key findings
    print("KEY FINDINGS")
    print("-" * 80)

    findings = []

    # Accuracy assessment
    if mean_opt_acc < 95:
        findings.append(f"❌ CRITICAL: Optimized accuracy ({mean_opt_acc:.1f}%) falls SHORT of 95% target by {95-mean_opt_acc:.1f}%")
    else:
        findings.append(f"✅ Optimized accuracy ({mean_opt_acc:.1f}%) MEETS >95% target")

    if mean_base_acc < 95:
        findings.append(f"❌ CRITICAL: Baseline accuracy ({mean_base_acc:.1f}%) falls SHORT of 95% target by {95-mean_base_acc:.1f}%")
    else:
        findings.append(f"✅ Baseline accuracy ({mean_base_acc:.1f}%) MEETS >95% target")

    # FN rate
    if opt_fn_rate >= 5:
        findings.append(f"❌ CRITICAL: Optimized FN rate ({opt_fn_rate:.1f}%) EXCEEDS 5% threshold")
    else:
        findings.append(f"✅ Optimized FN rate ({opt_fn_rate:.1f}%) meets <5% target")

    # Truncation
    if truncation_rate >= 2:
        findings.append(f"❌ Truncation rate ({truncation_rate:.1f}%) EXCEEDS 2% threshold")
    else:
        findings.append(f"✅ Truncation rate ({truncation_rate:.1f}%) meets <2% target")

    # Latency
    if p95_opt_latency >= 100:
        findings.append(f"❌ P95 latency ({p95_opt_latency:.1f}s) EXCEEDS 100s target")
    else:
        findings.append(f"✅ P95 latency ({p95_opt_latency:.1f}s) meets <100s target")

    # Disagreement analysis
    mean_agree = statistics.mean(agreement_rates)
    findings.append(f"⚠️  Average agreement rate: {mean_agree:.1f}% (only {mean_agree/100*6:.1f}/6 tests agree)")

    # Which tests are most problematic?
    problematic_tests = []
    for i in range(1, 7):
        opt_success = sum(test_results[i]['optimized']) / 20 * 100
        if opt_success < 80:  # Less than 80% success
            problematic_tests.append((i, opt_success))

    if problematic_tests:
        findings.append(f"⚠️  Problematic tests (< 80% success): " +
                       ", ".join([f"Test {i} ({s:.0f}%)" for i, s in problematic_tests]))

    for finding in findings:
        print(finding)

    print("-" * 80)
    print()

    # Recommendations
    print("RECOMMENDATIONS")
    print("-" * 80)

    recommendations = []

    # Overall verdict
    passing_criteria = sum([
        truncation_rate < 2,
        mean_opt_acc > 95,
        opt_fn_rate < 5,
        p95_opt_latency < 100
    ])

    if passing_criteria == 4:
        recommendations.append("✅ VERDICT: Option 1 PASSES all criteria. Ready for deployment.")
    else:
        recommendations.append(f"❌ VERDICT: Option 1 FAILS {4-passing_criteria}/4 criteria. NOT READY for deployment.")

    # Specific recommendations based on failures
    if mean_opt_acc < 95:
        recommendations.append("• Accuracy Issue: Consider increasing reasoning effort or adding more verification steps")

    if opt_fn_rate >= 5:
        recommendations.append("• False Negative Issue: Too lenient - tighten verification constraints")

    if truncation_rate >= 2:
        recommendations.append("• Truncation Issue: Increase max_tokens limits or reduce solution complexity requirements")

    if mean_agree < 80:
        recommendations.append("• Agreement Issue: High disagreement between HIGH/MEDIUM suggests instability - investigate variance")

    # Test-specific recommendations
    if any(sum(test_results[i]['optimized']) < 16 for i in [1, 2, 6]):  # PASS tests
        recommendations.append("• Test 1/2/6 (PASS expected): Increase tolerance for complete/alternative proofs")

    if any(sum(test_results[i]['optimized']) < 16 for i in [3, 4, 5]):  # FAIL tests
        recommendations.append("• Test 3/4/5 (FAIL expected): Strengthen detection of missing proofs/constructions")

    for rec in recommendations:
        print(rec)

    print("-" * 80)

if __name__ == "__main__":
    main()
