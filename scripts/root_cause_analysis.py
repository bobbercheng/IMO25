#!/usr/bin/env python3
"""
Root Cause Analysis: RLAC Test Variance
Analyzing 12 runs of identical code (commit 42015fb)
"""

import csv
import re
import json
from pathlib import Path
from collections import defaultdict
import statistics

# Read test results CSV
csv_file = Path("/home/user/IMO25/test_results_tracking_42015fb.csv")
results = []
with open(csv_file) as f:
    reader = csv.DictReader(f)
    for row in reader:
        results.append(row)

print("="*80)
print("ROOT CAUSE ANALYSIS: RLAC Test Non-Determinism")
print("="*80)
print()

# Statistical Summary
accuracies = [float(row['Accuracy'].replace('%', '')) for row in results]
print("STATISTICAL SUMMARY:")
print(f"  Mean Accuracy: {statistics.mean(accuracies):.1f}%")
print(f"  Std Dev: {statistics.stdev(accuracies):.1f}%")
print(f"  Min: {min(accuracies):.1f}%")
print(f"  Max: {max(accuracies):.1f}%")
print(f"  Range: {max(accuracies) - min(accuracies):.1f}% (5x variation!)")
print()

# Per-test pass rates
test_names = ['Test1', 'Test2', 'Test3', 'Test4', 'Test5', 'Test6']
test_descriptions = [
    'Complete proof bfs_run2 (SHOULD ALWAYS PASS)',
    'Complete proof bfs_run8 (SHOULD ALWAYS PASS)',
    'Incomplete k=2 (expected to fail)',
    'Missing constructions',
    'Wrong answer',
    'Justification gap'
]

print("PER-TEST PASS RATES (out of 12 runs):")
for i, (test, desc) in enumerate(zip(test_names, test_descriptions), 1):
    col_name = f"{test}_Pass"
    passes = sum(1 for row in results if row[col_name] == 'PASS')
    pass_rate = passes / len(results) * 100
    print(f"  Test {i} ({desc}): {passes}/12 ({pass_rate:.1f}%)")
    if i <= 2 and passes < 12:
        print(f"    ⚠️  CRITICAL: Should be 100%, not {pass_rate:.1f}%!")
print()

# Correlation Analysis
print("CORRELATION ANALYSIS:")
print("  Test 1 vs Test 2 correlation:")
test1_test2_both_pass = 0
test1_test2_both_fail = 0
test1_pass_test2_fail = 0
test1_fail_test2_pass = 0

for row in results:
    t1 = row['Test1_Pass'] == 'PASS'
    t2 = row['Test2_Pass'] == 'PASS'
    if t1 and t2:
        test1_test2_both_pass += 1
    elif not t1 and not t2:
        test1_test2_both_fail += 1
    elif t1 and not t2:
        test1_pass_test2_fail += 1
    else:
        test1_fail_test2_pass += 1

print(f"    Both PASS: {test1_test2_both_pass}/12 ({test1_test2_both_pass/12*100:.1f}%)")
print(f"    Both FAIL: {test1_test2_both_fail}/12 ({test1_test2_both_fail/12*100:.1f}%)")
print(f"    Test1 PASS, Test2 FAIL: {test1_pass_test2_fail}/12 ({test1_pass_test2_fail/12*100:.1f}%)")
print(f"    Test1 FAIL, Test2 PASS: {test1_fail_test2_pass}/12 ({test1_fail_test2_pass/12*100:.1f}%)")

# Calculate correlation coefficient (phi coefficient for binary data)
n = len(results)
n11 = test1_test2_both_pass  # both pass
n10 = test1_pass_test2_fail  # t1 pass, t2 fail
n01 = test1_fail_test2_pass  # t1 fail, t2 pass
n00 = test1_test2_both_fail  # both fail

phi = (n11*n00 - n10*n01) / ((n11+n10)*(n01+n00)*(n11+n01)*(n10+n00))**0.5
print(f"    Phi correlation coefficient: {phi:.3f}")
print(f"    Interpretation: {'STRONG' if abs(phi) > 0.7 else 'MODERATE' if abs(phi) > 0.4 else 'WEAK'} correlation")
print()

# Hypothesis Testing
print("HYPOTHESIS TESTING:")
print("  H0: System is deterministic (variance = 0)")
print("  H1: System has high variance (observed std dev = 25.9%)")
print()

# Chi-square test for uniformity
# If deterministic, all runs should have same accuracy
# Expected: all runs at mean accuracy
expected_freq = len(results)
observed_freqs = {}
for acc in accuracies:
    observed_freqs[acc] = observed_freqs.get(acc, 0) + 1

chi_square = sum((obs - expected_freq/len(observed_freqs))**2 / (expected_freq/len(observed_freqs))
                 for obs in observed_freqs.values())

print(f"  Chi-square statistic: {chi_square:.2f}")
print(f"  Degrees of freedom: {len(observed_freqs) - 1}")
print(f"  Critical value (α=0.05): ~{(len(observed_freqs)-1) * 3.84:.1f}")
print(f"  Result: {'REJECT H0' if chi_square > (len(observed_freqs)-1)*3.84 else 'FAIL TO REJECT H0'}")
print()

# Distribution analysis
print("ACCURACY DISTRIBUTION:")
accuracy_counts = defaultdict(int)
for acc in accuracies:
    accuracy_counts[acc] += 1

for acc in sorted(accuracy_counts.keys()):
    count = accuracy_counts[acc]
    pct = count / len(results) * 100
    bar = '█' * int(pct / 5)
    print(f"  {acc:5.1f}%: {count:2d} runs ({pct:5.1f}%) {bar}")
print()

# Identify worst and best runs for detailed analysis
worst_runs = [i+1 for i, row in enumerate(results) if float(row['Accuracy'].replace('%', '')) == min(accuracies)]
best_runs = [i+1 for i, row in enumerate(results) if float(row['Accuracy'].replace('%', '')) == max(accuracies)]

print(f"WORST RUNS (16.7%): {worst_runs}")
print(f"BEST RUNS (83.3%): {best_runs}")
print()

# Empty response analysis
print("EMPTY LLM RESPONSE ANALYSIS:")
log_files = sorted(Path("/home/user/IMO25").glob("test_option_b_full_solution_validation_high_42015fb*.log"))

empty_response_counts = {}
for log_file in log_files:
    # Extract run number from filename
    match = re.search(r'_(\d+)\.log$', str(log_file))
    if match:
        run_num = int(match.group(1))
    elif log_file.name.endswith("42015fb.log"):
        run_num = 1
    else:
        continue

    # Count empty responses
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        empty_count = content.count('"content": ""')

    empty_response_counts[run_num] = empty_count

print("  Run | Empty Responses | Accuracy | Test1 | Test2")
print("  " + "-"*55)
for i, row in enumerate(results, 1):
    empty_cnt = empty_response_counts.get(i, 0)
    acc = row['Accuracy']
    t1 = row['Test1_Pass']
    t2 = row['Test2_Pass']
    print(f"  {i:3d} | {empty_cnt:15d} | {acc:>7s} | {t1:>5s} | {t2:>5s}")

print()

# Correlation between empty responses and test passes
empty_counts_list = [empty_response_counts.get(i, 0) for i in range(1, 13)]
test1_passes = [1 if row['Test1_Pass'] == 'PASS' else 0 for row in results]

# Calculate Pearson correlation
mean_empty = statistics.mean(empty_counts_list)
mean_test1 = statistics.mean(test1_passes)
cov = sum((e - mean_empty) * (t - mean_test1) for e, t in zip(empty_counts_list, test1_passes)) / len(empty_counts_list)
std_empty = statistics.stdev(empty_counts_list)
std_test1 = statistics.stdev(test1_passes)
correlation = cov / (std_empty * std_test1) if std_empty > 0 and std_test1 > 0 else 0

print(f"CORRELATION: Empty Responses vs Test1 Pass: {correlation:.3f}")
print()

print("="*80)
print("CONCLUSIONS:")
print("="*80)
print()
print("1. ROOT CAUSE: LLM Non-Determinism at API Level")
print("   - Same input (seed=42, temp=0.0) produces different outputs")
print("   - Sometimes returns EMPTY response → test passes")
print("   - Sometimes returns detailed analysis → finds 'Justification Gap' → test fails")
print()
print("2. SEVERITY: CATASTROPHIC")
print(f"   - Complete proofs fail 58% of the time (should be 0%)")
print(f"   - 5x variation in overall accuracy (16.7% to 83.3%)")
print(f"   - Strong correlation between Test1 and Test2 failures (phi={phi:.3f})")
print()
print("3. HYPOTHESIS:")
print("   - OpenRouter API does NOT respect seed/temperature settings")
print("   - OR: Model has inherent non-determinism despite temperature=0")
print("   - Empty responses may indicate API timeout/failure mode")
print()
print("4. RECOMMENDATION:")
print("   - DO NOT trust single-run results")
print("   - Average accuracy ~41.7% is the TRUE baseline")
print("   - Need ensemble of 10+ runs for reliable measurement")
print("   - Investigate why LLM sometimes returns empty content")
print()
