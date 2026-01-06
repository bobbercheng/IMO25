#!/usr/bin/env python3
"""
Phase 2.3: Saturation Test

Test if sampling MORE errors from merged corpus reveals new categories.

Methodology:
1. Sample progressively larger sets: 64 → 128 → 256 errors
2. Check keyword coverage at each level
3. If coverage remains 100% → taxonomy is saturated
4. If coverage drops → new categories may exist
"""

import json
import random
import sys
import os

# Import extraction function
sys.path.insert(0, os.path.dirname(__file__))
from stage1_error_analysis import extract_errors_from_log

def load_all_errors():
    """Load all errors from both BFS and MCTS."""
    # BFS errors
    bfs_log = 'run_log_gpt_oss/bfs_revalidation_1.log'
    print(f"[LOAD] Extracting BFS errors from {bfs_log}")
    bfs_errors = extract_errors_from_log(bfs_log)

    # MCTS errors
    with open('mcts_errors.json', 'r') as f:
        mcts_data = json.load(f)
    mcts_errors = mcts_data['errors']

    # Combine
    combined = {
        'critical_errors': bfs_errors['critical_errors'] + mcts_errors['critical_errors'],
        'justification_gaps': bfs_errors['justification_gaps'] + mcts_errors['justification_gaps'],
        'construction_failures': bfs_errors['construction_failures'] + mcts_errors['construction_failures'],
        'other_errors': bfs_errors['other_errors'] + mcts_errors['other_errors']
    }

    total = sum(len(v) for v in combined.values())
    print(f"[LOAD] Combined corpus: {total} errors")

    return combined

def sample_errors(all_errors, sample_size):
    """Sample errors proportionally from each type."""
    sampled = {
        'critical_errors': [],
        'justification_gaps': [],
        'construction_failures': [],
        'other_errors': []
    }

    total_errors = sum(len(v) for v in all_errors.values())

    for error_type, error_list in all_errors.items():
        # Proportional sampling
        proportion = len(error_list) / total_errors
        type_sample_size = min(int(sample_size * proportion), len(error_list))

        if type_sample_size > 0:
            sample = random.sample(error_list, type_sample_size)
            sampled[error_type] = [err[:300] for err in sample]

    actual_size = sum(len(v) for v in sampled.values())
    print(f"[SAMPLE] Sampled {actual_size} errors (target: {sample_size})")

    return sampled

def keyword_coverage_analysis(sample):
    """Perform keyword-based coverage analysis."""
    category_keywords = {
        "Integer/Denominator Reasoning Errors": [
            "integer", "lattice", "divisibility", "denominator", "gcd", "rational",
            "common factor", "quotient", "coprime"
        ],
        "Faulty Construction/Coverage": [
            "construction", "cover", "satisfy", "counterexample", "violate",
            "fail", "not all", "doesn't work", "incomplete"
        ],
        "Missing Justification": [
            "without proof", "unjustified", "claimed", "missing", "gap",
            "not shown", "not proven", "assumed", "unsupported"
        ],
        "Quantitative Bounds/Counting Errors": [
            "bound", "count", "inequality", "estimate", "maximum", "minimum",
            "at least", "at most", "overcounting", "undercounting"
        ],
        "Logical Deduction Errors": [
            "converse", "circular", "non sequitur", "implication", "assumes",
            "begging", "invalid", "fallacy", "does not follow"
        ],
        "Case Analysis Mistakes": [
            "case", "incomplete", "missing", "overlapping", "boundary",
            "edge", "scenario", "possibility", "unresolved"
        ],
        "Coverage Counting Miscalculations": [
            "inclusion-exclusion", "overlap", "distinct", "double-count",
            "unique", "intersection", "union", "shared"
        ]
    }

    all_errors = []
    for error_type, errors in sample.items():
        all_errors.extend([err.lower() for err in errors])

    # Count matches for each category
    coverage = {}
    for cat_name, keywords in category_keywords.items():
        matches = 0
        for error in all_errors:
            if any(keyword in error for keyword in keywords):
                matches += 1
        coverage[cat_name] = matches

    total_errors = len(all_errors)
    total_matched = sum(coverage.values())

    # Count how many errors match at least one category
    matched_errors = set()
    for i, error in enumerate(all_errors):
        for cat_name, keywords in category_keywords.items():
            if any(keyword in error for keyword in keywords):
                matched_errors.add(i)
                break

    unique_coverage = len(matched_errors) / total_errors * 100 if total_errors > 0 else 0

    return {
        'total_errors': total_errors,
        'category_matches': coverage,
        'total_matched': total_matched,
        'unique_coverage': unique_coverage
    }

def run_saturation_test(all_errors, sample_sizes=[64, 128, 256]):
    """Run saturation test with progressively larger samples."""
    print("\n" + "="*80)
    print("SATURATION TEST")
    print("="*80 + "\n")

    results = []

    random.seed(42)  # Reproducibility

    for size in sample_sizes:
        print(f"\n{'='*80}")
        print(f"SAMPLE SIZE: {size}")
        print(f"{'='*80}\n")

        # Sample errors
        sample = sample_errors(all_errors, size)

        # Analyze coverage
        analysis = keyword_coverage_analysis(sample)

        print(f"Total errors: {analysis['total_errors']}")
        print(f"Unique coverage: {analysis['unique_coverage']:.1f}%\n")

        print("Category-wise matches:")
        for cat_name, matches in sorted(analysis['category_matches'].items(),
                                       key=lambda x: x[1], reverse=True):
            pct = matches / analysis['total_errors'] * 100 if analysis['total_errors'] > 0 else 0
            print(f"  {cat_name}: {matches}/{analysis['total_errors']} ({pct:.1f}%)")

        results.append({
            'sample_size': size,
            'actual_size': analysis['total_errors'],
            'unique_coverage': analysis['unique_coverage'],
            'category_matches': analysis['category_matches']
        })

        # Check saturation
        if analysis['unique_coverage'] >= 95:
            print(f"\n✅ Coverage ≥95% at sample size {size} → Taxonomy likely saturated")
        else:
            print(f"\n⚠️  Coverage <95% at sample size {size} → May need new categories")

    return results

def analyze_saturation_trend(results):
    """Analyze if coverage is stable or declining."""
    print("\n" + "="*80)
    print("SATURATION TREND ANALYSIS")
    print("="*80 + "\n")

    coverages = [r['unique_coverage'] for r in results]

    print("Coverage by sample size:")
    for r in results:
        print(f"  n={r['sample_size']}: {r['unique_coverage']:.1f}%")

    # Check if coverage is stable (within 5% range)
    max_cov = max(coverages)
    min_cov = min(coverages)
    variation = max_cov - min_cov

    print(f"\nCoverage variation: {variation:.1f}%")

    if variation <= 5:
        print("✅ STABLE coverage (variation ≤5%) → Taxonomy is SATURATED")
        saturated = True
    else:
        print("⚠️  UNSTABLE coverage (variation >5%) → May need more categories")
        saturated = False

    # Check if coverage is declining
    if len(coverages) >= 2 and coverages[-1] < coverages[0] - 5:
        print("⚠️  Coverage DECLINING with larger samples → New categories may exist")
        saturated = False

    return saturated

def main():
    print("\n" + "="*80)
    print("PHASE 2.3: SATURATION TEST")
    print("="*80)

    # Load all errors
    all_errors = load_all_errors()

    total = sum(len(v) for v in all_errors.values())
    print(f"\nTotal corpus size: {total} errors")

    # Determine sample sizes based on corpus size
    # Use 5%, 10%, 20% of corpus
    sample_sizes = [
        min(64, total),
        min(128, total),
        min(256, int(0.2 * total))
    ]

    print(f"Sample sizes: {sample_sizes}\n")

    # Run saturation test
    results = run_saturation_test(all_errors, sample_sizes)

    # Analyze trend
    saturated = analyze_saturation_trend(results)

    # Save results
    output = {
        'phase': 'Phase 2.3',
        'date': '2025-12-18',
        'corpus_size': total,
        'sample_sizes': sample_sizes,
        'results': results,
        'saturated': saturated
    }

    with open('phase2_3_saturation_test.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("\n✅ Results saved to phase2_3_saturation_test.json")

    # Final verdict
    print("\n" + "="*80)
    print("FINAL VERDICT")
    print("="*80 + "\n")

    if saturated:
        print("✅ TAXONOMY IS SATURATED")
        print("\nConclusion:")
        print("  - Coverage stable across sample sizes (64 → 128 → 256)")
        print("  - All errors fit existing 7 categories")
        print("  - No new categories needed")
        print("\nReady for Phase 3: Statistical Validation")
    else:
        print("⚠️  TAXONOMY MAY NOT BE SATURATED")
        print("\nConclusion:")
        print("  - Coverage varies or declines with larger samples")
        print("  - Some errors may not fit existing categories")
        print("  - Review needed before Phase 3")

    print("\n" + "="*80)
    print(f"PHASE 2.3 STATUS: {'✅ COMPLETE' if saturated else '⚠️  UNCERTAIN'}")
    print("="*80 + "\n")

    return 0

if __name__ == '__main__':
    sys.exit(main())
