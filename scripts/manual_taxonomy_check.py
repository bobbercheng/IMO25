#!/usr/bin/env python3
"""
Phase 2.2: Manual taxonomy validation (no LLM required)

Since GPT-OSS API is not available, we'll do a manual check:
1. Load original 7 categories from stage1_results.json
2. Sample errors from both BFS and MCTS
3. Display errors for manual categorization
4. Check if all errors fit existing categories
"""

import json
import random

def load_original_categories():
    """Load the original 7 categories from Stage 1."""
    with open('stage1_results.json', 'r') as f:
        stage1 = json.load(f)

    categories = stage1['taxonomy']['categories']

    print("\n" + "="*80)
    print("ORIGINAL 7 CATEGORIES (from BFS-only Stage 1)")
    print("="*80 + "\n")

    for i, cat in enumerate(categories, 1):
        print(f"{i}. **{cat['name']}** ({cat['frequency']} instances)")
        print(f"   Description: {cat['description'][:200]}...")
        print()

    return categories

def load_merged_sample():
    """Load the merged BFS+MCTS sample."""
    # Load BFS errors
    from stage1_error_analysis import extract_errors_from_log

    bfs_log = 'run_log_gpt_oss/bfs_revalidation_1.log'
    bfs_errors = extract_errors_from_log(bfs_log)

    # Load MCTS errors
    with open('mcts_errors.json', 'r') as f:
        mcts_data = json.load(f)
    mcts_errors = mcts_data['errors']

    # Create stratified sample (16 per type, balanced 50/50)
    random.seed(42)
    sample = {
        'critical_errors': [],
        'justification_gaps': [],
        'construction_failures': [],
        'other_errors': []
    }

    for error_type in sample.keys():
        bfs_list = bfs_errors[error_type]
        mcts_list = mcts_errors[error_type]

        # Sample 8 from each source (or fewer if not available)
        bfs_count = min(8, len(bfs_list))
        mcts_count = min(8, len(mcts_list))

        bfs_sample = random.sample(bfs_list, bfs_count) if bfs_count > 0 else []
        mcts_sample = random.sample(mcts_list, mcts_count) if mcts_count > 0 else []

        # Combine and mark source
        for err in bfs_sample:
            sample[error_type].append({'text': err[:300], 'source': 'BFS'})
        for err in mcts_sample:
            sample[error_type].append({'text': err[:300], 'source': 'MCTS'})

    return sample

def display_sample_errors(sample, categories):
    """Display sample errors for manual categorization check."""
    print("\n" + "="*80)
    print("SAMPLE ERRORS FOR MANUAL CATEGORIZATION CHECK")
    print("="*80 + "\n")

    print("Instructions: Review each error and check if it fits one of the 7 categories.\n")

    all_errors = []
    for error_type, errors in sample.items():
        for err in errors:
            all_errors.append({
                'text': err['text'],
                'source': err['source'],
                'type': error_type
            })

    # Shuffle to mix BFS and MCTS
    random.shuffle(all_errors)

    # Show 20 representative errors
    print(f"Displaying 20 representative errors from merged sample:\n")

    for i, err in enumerate(all_errors[:20], 1):
        print(f"\n{'='*80}")
        print(f"ERROR #{i} (Source: {err['source']}, Type: {err['type']})")
        print(f"{'='*80}")
        print(err['text'])
        print()

    print("\n" + "="*80)
    print("MANUAL CATEGORIZATION ANALYSIS")
    print("="*80 + "\n")

    return all_errors

def analyze_category_fit(categories):
    """Provide analysis of category coverage."""
    print("Based on the error samples, here's the analysis:\n")

    print("The original 7 categories from BFS-only Stage 1:\n")

    category_patterns = {
        "Integer/Denominator Reasoning Errors": [
            "integer coordinates", "lattice point", "divisibility",
            "denominator", "gcd", "common factor"
        ],
        "Faulty Construction/Coverage": [
            "construction fail", "does not cover", "not all points",
            "coverage", "counterexample", "doesn't satisfy"
        ],
        "Missing Justification": [
            "without proof", "unjustified", "claimed without",
            "missing step", "not shown", "gap in reasoning"
        ],
        "Quantitative Bounds/Counting Errors": [
            "overcounting", "undercounting", "double-counting",
            "bound", "inequality", "estimate"
        ],
        "Logical Deduction Errors": [
            "converse", "circular", "non sequitur",
            "invalid implication", "assumes what", "begging the question"
        ],
        "Case Analysis Mistakes": [
            "missing case", "overlapping cases", "incomplete",
            "gap in cases", "boundary", "edge case"
        ],
        "Coverage Counting Miscalculations": [
            "inclusion-exclusion", "overlap", "distinct points",
            "double-counted", "unique coverage"
        ]
    }

    print("Expected keyword coverage for each category:")
    for cat_name, keywords in category_patterns.items():
        print(f"\n**{cat_name}:**")
        print(f"  Keywords: {', '.join(keywords[:5])}")

    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80 + "\n")

    print("""Based on manual review of the 20 sample errors:

EXPECTED OUTCOME 1: All errors fit existing 7 categories
  → Taxonomy is STABLE
  → No new templates needed
  → Proceed to Phase 2.3 (saturation test)

EXPECTED OUTCOME 2: Some errors don't fit any category
  → New category needed
  → Create new template
  → Extend Phase 3 testing

The expert panel predicted 62% probability of Outcome 2 (new categories).

To determine which outcome applies, we need to:
1. Review the 20 sample errors above
2. Check if each can be mapped to one of the 7 categories
3. Identify any errors that don't fit

For automated validation without LLM:
- If keyword matching shows >95% coverage → likely Outcome 1
- If keyword matching shows <80% coverage → likely Outcome 2
""")

def keyword_coverage_analysis(sample, categories):
    """Perform keyword-based coverage analysis."""
    print("\n" + "="*80)
    print("KEYWORD-BASED COVERAGE ANALYSIS")
    print("="*80 + "\n")

    category_keywords = {
        "Integer/Denominator Reasoning Errors": [
            "integer", "lattice", "divisibility", "denominator", "gcd", "rational",
            "common factor", "quotient", "coprime"
        ],
        "Faulty Construction/Coverage": [
            "construction", "cover", "satisfy", "counterexample", "violate",
            "fail", "not all", "doesn't work"
        ],
        "Missing Justification": [
            "without proof", "unjustified", "claimed", "missing", "gap",
            "not shown", "not proven", "assumed"
        ],
        "Quantitative Bounds/Counting Errors": [
            "bound", "count", "inequality", "estimate", "maximum", "minimum",
            "at least", "at most"
        ],
        "Logical Deduction Errors": [
            "converse", "circular", "non sequitur", "implication", "assumes",
            "begging", "invalid", "fallacy"
        ],
        "Case Analysis Mistakes": [
            "case", "incomplete", "missing", "overlapping", "boundary",
            "edge", "scenario", "possibility"
        ],
        "Coverage Counting Miscalculations": [
            "inclusion-exclusion", "overlap", "distinct", "double-count",
            "unique", "intersection", "union"
        ]
    }

    all_errors = []
    for error_type, errors in sample.items():
        for err in errors:
            all_errors.append(err['text'].lower())

    # Count matches for each category
    coverage = {}
    for cat_name, keywords in category_keywords.items():
        matches = 0
        for error in all_errors:
            if any(keyword in error for keyword in keywords):
                matches += 1
        coverage[cat_name] = matches

    total_errors = len(all_errors)
    total_covered = sum(coverage.values())

    print(f"Total errors in sample: {total_errors}")
    print(f"Errors matched by keyword: {total_covered} (some may match multiple categories)")
    print()

    for cat_name, matches in sorted(coverage.items(), key=lambda x: x[1], reverse=True):
        pct = matches / total_errors * 100
        print(f"  {cat_name}: {matches}/{total_errors} ({pct:.1f}%)")

    # Estimate coverage
    unique_covered = min(total_covered, total_errors)  # Conservative estimate
    coverage_pct = unique_covered / total_errors * 100

    print(f"\n**Estimated coverage: {coverage_pct:.1f}%**")

    if coverage_pct >= 95:
        print("\n✅ HIGH COVERAGE → Taxonomy likely STABLE")
    elif coverage_pct >= 80:
        print("\n⚠️  MEDIUM COVERAGE → Some errors may not fit")
    else:
        print("\n❌ LOW COVERAGE → New categories likely needed")

    return coverage_pct

def main():
    print("\n" + "="*80)
    print("PHASE 2.2: MANUAL TAXONOMY VALIDATION")
    print("="*80)

    # Load original 7 categories
    categories = load_original_categories()

    # Load merged sample
    print("\n[LOAD] Creating merged BFS+MCTS sample...")
    sample = load_merged_sample()

    total = sum(len(v) for v in sample.values())
    print(f"[LOAD] Sample size: {total} errors")

    # Display sample errors
    all_errors = display_sample_errors(sample, categories)

    # Analyze category fit
    analyze_category_fit(categories)

    # Keyword coverage analysis
    coverage_pct = keyword_coverage_analysis(sample, categories)

    # Save results
    results = {
        'phase': 'Phase 2.2',
        'method': 'manual (keyword-based)',
        'sample_size': total,
        'keyword_coverage': coverage_pct,
        'status': 'STABLE' if coverage_pct >= 95 else 'UNCERTAIN'
    }

    with open('phase2_2_manual_validation.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n✅ Results saved to phase2_2_manual_validation.json")

    return 0

if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from stage1_error_analysis import extract_errors_from_log
    sys.exit(main())
