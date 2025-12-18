#!/usr/bin/env python3
"""
Simplified error extraction: Use existing extraction function and select diverse, high-impact errors.
"""

import sys
import os
import json
import random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from stage1_error_analysis import extract_errors_from_log

def categorize_error(error_text):
    """Categorize error using keyword matching."""
    error_lower = error_text.lower()

    categories = {
        "Integer/Denominator Reasoning": ["integer", "lattice", "divisibility", "denominator", "gcd", "rational", "coprime"],
        "Faulty Construction": ["construction", "cover", "satisfy", "counterexample", "violate", "fail", "not all", "does not"],
        "Missing Justification": ["without proof", "unjustified", "claimed", "missing", "gap", "not shown", "not proven", "not rigorously"],
        "Quantitative Bounds": ["bound", "count", "inequality", "estimate", "maximum", "minimum", "at least", "at most", "incorrect"],
        "Logical Deduction": ["converse", "circular", "non sequitur", "implication", "assumes", "invalid", "does not follow", "false"],
        "Case Analysis": ["case", "incomplete", "missing", "overlapping", "boundary", "edge", "scenario"],
        "Coverage Counting": ["inclusion-exclusion", "overlap", "distinct", "double-count", "unique"]
    }

    for category, keywords in categories.items():
        if any(keyword in error_lower for keyword in keywords):
            return category

    return "Uncategorized"

def select_diverse_errors(all_errors, target_count=20):
    """Select diverse, representative errors for template application."""

    # Categorize all errors
    categorized = defaultdict(list)
    for error_type, error_list in all_errors.items():
        for error_text in error_list:
            category = categorize_error(error_text)
            categorized[category].append({
                'text': error_text,
                'source_type': error_type,
                'category': category
            })

    print(f"\n[CATEGORIZE] Error distribution:")
    for cat, errors in sorted(categorized.items()):
        print(f"  {cat}: {len(errors)}")

    # Select diverse sample (2-3 per category)
    selected = []
    random.seed(42)

    # Ensure each category is represented
    for category, errors in sorted(categorized.items()):
        if category == "Uncategorized":
            continue

        # Select 3 representative errors from this category
        count = min(3, len(errors))
        sample = random.sample(errors, count)
        selected.extend(sample)

    # Truncate to target count
    if len(selected) > target_count:
        selected = selected[:target_count]

    return selected

def main():
    print("\n" + "="*80)
    print("PRODUCTION PHASE 1: EXTRACT HIGH-IMPACT BFS ERRORS (SIMPLIFIED)")
    print("="*80 + "\n")

    # Try multiple BFS logs
    log_files = [
        'run_log_gpt_oss/bfs_medium_fresh_test.log',
        'run_log_gpt_oss/bfs_revalidation_1.log',
        'run_log_gpt_oss/bfs_medium_1.log'
    ]

    all_errors_combined = {
        'critical_errors': [],
        'justification_gaps': [],
        'construction_failures': [],
        'other_errors': []
    }

    for log_file in log_files:
        if not os.path.exists(log_file):
            continue

        print(f"[EXTRACT] Extracting from {log_file}...")
        errors = extract_errors_from_log(log_file)

        # Merge
        for key in all_errors_combined:
            all_errors_combined[key].extend(errors[key])

    # Deduplicate
    for key in all_errors_combined:
        all_errors_combined[key] = list(set(all_errors_combined[key]))

    total = sum(len(v) for v in all_errors_combined.values())
    print(f"\n[TOTAL] Extracted {total} unique errors from all BFS logs")

    # Select diverse sample
    selected = select_diverse_errors(all_errors_combined, target_count=20)

    print(f"\n[SELECT] Selected {len(selected)} diverse errors for template application")

    # Display selected errors
    print(f"\n{'='*80}")
    print("SELECTED ERRORS FOR TEMPLATE APPLICATION")
    print(f"{'='*80}\n")

    for i, error in enumerate(selected, 1):
        print(f"\n{'='*80}")
        print(f"ERROR #{i}")
        print(f"{'='*80}")
        print(f"Category: {error['category']}")
        print(f"Source Type: {error['source_type']}")
        print(f"\nError Text:")
        print(error['text'][:500])  # Show first 500 chars
        if len(error['text']) > 500:
            print(f"... (truncated, full length: {len(error['text'])} chars)")

    # Save results
    output = {
        'log_files': log_files,
        'total_unique_errors': total,
        'selected_count': len(selected),
        'errors': selected
    }

    with open('production_phase1_selected_errors.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Results saved to production_phase1_selected_errors.json")

    # Category distribution
    category_counts = defaultdict(int)
    for error in selected:
        category_counts[error['category']] += 1

    print(f"\n{'='*80}")
    print("CATEGORY DISTRIBUTION")
    print(f"{'='*80}\n")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")

    return 0

if __name__ == '__main__':
    sys.exit(main())
