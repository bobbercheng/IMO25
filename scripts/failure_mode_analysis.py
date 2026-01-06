#!/usr/bin/env python3
"""
Failure Mode Analysis - What breaks in production?
Dr. Alex Rivera - Nvidia AI
"""

import json
from collections import defaultdict, Counter

def load_results():
    results = []
    for i in range(1, 12):
        path = f"/home/user/IMO25/week2_results_{i}.json"
        with open(path) as f:
            data = json.load(f)
            data['round'] = i
            results.append(data)
    return results

def analyze_disagreement_patterns(results):
    """What types of disagreements occur?"""
    disagreement_types = defaultdict(list)

    for r in results:
        for test in r['full_results']:
            test_num = test['test_number']
            test_name = test['test_name']
            expected = test['expected_verdict']
            baseline_verdict = test['baseline']['verdict']
            optimized_verdict = test['optimized']['verdict']

            if baseline_verdict != optimized_verdict:
                pattern = f"Test{test_num}: {expected} | Base={baseline_verdict} → Opt={optimized_verdict}"
                disagreement_types[pattern].append(r['round'])

    return disagreement_types

def analyze_critical_failures(results):
    """Identify production-breaking scenarios"""
    critical_failures = {
        'fp_on_wrong_proof': [],  # Accepts incorrect proofs
        'fn_on_complete_proof': [],  # Rejects correct proofs
        'baseline_truncation_recovery': [],  # Baseline truncates, MEDIUM doesn't
        'medium_worse_than_baseline': []  # MEDIUM makes worse decision
    }

    for r in results:
        for test in r['full_results']:
            test_num = test['test_number']
            expected = test['expected_verdict']
            baseline_correct = test['comparison']['baseline_correct']
            optimized_correct = test['comparison']['optimized_correct']
            baseline_verdict = test['baseline']['verdict']
            optimized_verdict = test['optimized']['verdict']

            # FP on wrong proof (Test 4, 5 should be FAIL)
            if test_num in [4, 5]:
                if optimized_verdict == 'yes':
                    critical_failures['fp_on_wrong_proof'].append({
                        'round': r['round'],
                        'test': test_num,
                        'name': test['test_name']
                    })

            # FN on complete proof (Test 1, 2, 6 should be PASS)
            if test_num in [1, 2, 6]:
                if optimized_verdict == 'no':
                    critical_failures['fn_on_complete_proof'].append({
                        'round': r['round'],
                        'test': test_num,
                        'name': test['test_name']
                    })

            # Baseline truncation recovery
            if baseline_verdict == 'error' and optimized_verdict != 'error':
                critical_failures['baseline_truncation_recovery'].append({
                    'round': r['round'],
                    'test': test_num,
                    'baseline_verdict': baseline_verdict,
                    'optimized_verdict': optimized_verdict,
                    'optimized_correct': optimized_correct
                })

            # MEDIUM worse than baseline
            if baseline_correct and not optimized_correct:
                critical_failures['medium_worse_than_baseline'].append({
                    'round': r['round'],
                    'test': test_num,
                    'name': test['test_name']
                })

    return critical_failures

def analyze_worst_rounds(results):
    """Identify the worst performing rounds"""
    worst_rounds = []

    for r in results:
        worst_rounds.append({
            'round': r['round'],
            'agreement': r['agreement']['rate_percent'],
            'fp_rate': r['optimized']['fp_rate_percent'],
            'fn_rate': r['optimized']['fn_rate_percent'],
            'accuracy': r['optimized']['accuracy_percent']
        })

    # Sort by agreement
    worst_rounds.sort(key=lambda x: x['agreement'])
    return worst_rounds

def print_failure_analysis():
    results = load_results()

    print("="*80)
    print("FAILURE MODE ANALYSIS - PRODUCTION RISK ASSESSMENT")
    print("="*80)
    print()

    # Disagreement patterns
    patterns = analyze_disagreement_patterns(results)
    print("## 1. DISAGREEMENT PATTERNS (Frequency)")
    print()
    for pattern, rounds in sorted(patterns.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"   {pattern}")
        print(f"      Occurred in {len(rounds)}/11 rounds: {rounds}")
        print()

    # Critical failures
    failures = analyze_critical_failures(results)
    print()
    print("="*80)
    print("## 2. CRITICAL FAILURE MODES")
    print("="*80)
    print()

    print("### 2.1 FALSE POSITIVES (Accepting Wrong Proofs)")
    print(f"   Total incidents: {len(failures['fp_on_wrong_proof'])}")
    if failures['fp_on_wrong_proof']:
        for f in failures['fp_on_wrong_proof']:
            print(f"      Round {f['round']}, Test {f['test']}: {f['name'][:60]}")
    print()

    print("### 2.2 FALSE NEGATIVES (Rejecting Correct Proofs)")
    print(f"   Total incidents: {len(failures['fn_on_complete_proof'])}")
    if failures['fn_on_complete_proof']:
        for f in failures['fn_on_complete_proof']:
            print(f"      Round {f['round']}, Test {f['test']}: {f['name'][:60]}")
    print()

    print("### 2.3 BASELINE TRUNCATION RECOVERY")
    print(f"   Total incidents: {len(failures['baseline_truncation_recovery'])}")
    print("   (MEDIUM succeeds where HIGH truncated - good or bad?)")
    if failures['baseline_truncation_recovery']:
        for f in failures['baseline_truncation_recovery']:
            correct = "✅ CORRECT" if f['optimized_correct'] else "❌ WRONG"
            print(f"      Round {f['round']}, Test {f['test']}: {f['optimized_verdict']} {correct}")
    print()

    print("### 2.4 MEDIUM WORSE THAN BASELINE")
    print(f"   Total incidents: {len(failures['medium_worse_than_baseline'])}")
    print("   (Cases where MEDIUM makes WORSE decision than HIGH)")
    if failures['medium_worse_than_baseline']:
        for f in failures['medium_worse_than_baseline']:
            print(f"      Round {f['round']}, Test {f['test']}: {f['name'][:60]}")
    print()

    # Worst rounds
    print()
    print("="*80)
    print("## 3. WORST PERFORMING ROUNDS (Production Risk)")
    print("="*80)
    print()
    worst = analyze_worst_rounds(results)

    print("   Top 5 Worst Rounds by Agreement:")
    for i, r in enumerate(worst[:5], 1):
        print(f"   {i}. Round {r['round']:2d}: Agreement={r['agreement']:5.1f}%, "
              f"FP={r['fp_rate']:5.1f}%, FN={r['fn_rate']:5.1f}%, "
              f"Accuracy={r['accuracy']:5.1f}%")
    print()

    # Production risk summary
    print()
    print("="*80)
    print("## 4. PRODUCTION RISK SUMMARY")
    print("="*80)
    print()

    total_tests = 11 * 6  # 11 rounds * 6 tests
    fp_count = len(failures['fp_on_wrong_proof'])
    fn_count = len(failures['fn_on_complete_proof'])

    print(f"   Total tests executed: {total_tests}")
    print(f"   False Positives:      {fp_count} ({fp_count/total_tests*100:.1f}%)")
    print(f"   False Negatives:      {fn_count} ({fn_count/total_tests*100:.1f}%)")
    print(f"   MEDIUM worse than HIGH: {len(failures['medium_worse_than_baseline'])} cases")
    print()

    print("   RISK ASSESSMENT:")
    if fp_count / total_tests > 0.05:
        print("   ❌ CRITICAL: >5% FP rate - accepting wrong proofs in production")
    if fn_count / total_tests > 0.02:
        print("   ⚠️  WARNING: >2% FN rate - rejecting correct proofs")
    if len(failures['medium_worse_than_baseline']) > 5:
        print("   ❌ CRITICAL: MEDIUM degrades quality vs HIGH in >5 cases")

    print()

if __name__ == "__main__":
    print_failure_analysis()
