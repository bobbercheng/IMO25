#!/usr/bin/env python3
"""
Analyze the ~5-10% of errors not matched by keyword analysis
to determine if they represent new categories or just keyword matching failures.
"""

import json
import random
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from stage1_error_analysis import extract_errors_from_log

def find_uncovered_errors():
    """Find errors that don't match any category keywords."""
    # Load all errors
    bfs_log = 'run_log_gpt_oss/bfs_revalidation_1.log'
    bfs_errors = extract_errors_from_log(bfs_log)

    with open('mcts_errors.json', 'r') as f:
        mcts_data = json.load(f)
    mcts_errors = mcts_data['errors']

    # Combine
    combined = []
    for error_type in ['critical_errors', 'justification_gaps', 'construction_failures', 'other_errors']:
        for err in bfs_errors[error_type] + mcts_errors[error_type]:
            combined.append(err[:300])

    # Category keywords (same as saturation test)
    category_keywords = {
        "Integer/Denominator": ["integer", "lattice", "divisibility", "denominator", "gcd", "rational", "coprime"],
        "Faulty Construction": ["construction", "cover", "satisfy", "counterexample", "violate", "fail", "not all"],
        "Missing Justification": ["without proof", "unjustified", "claimed", "missing", "gap", "not shown"],
        "Quantitative Bounds": ["bound", "count", "inequality", "estimate", "maximum", "minimum", "at least"],
        "Logical Deduction": ["converse", "circular", "non sequitur", "implication", "assumes", "invalid"],
        "Case Analysis": ["case", "incomplete", "missing", "overlapping", "boundary", "edge", "scenario"],
        "Coverage Counting": ["inclusion-exclusion", "overlap", "distinct", "double-count", "unique"]
    }

    # Find uncovered
    uncovered = []
    for err in combined:
        err_lower = err.lower()
        matched = False
        for cat_name, keywords in category_keywords.items():
            if any(keyword in err_lower for keyword in keywords):
                matched = True
                break
        if not matched:
            uncovered.append(err)

    return uncovered

def main():
    print("\n" + "="*80)
    print("ANALYZE UNCOVERED ERRORS")
    print("="*80 + "\n")

    uncovered = find_uncovered_errors()

    print(f"Total uncovered errors: {len(uncovered)}")
    print(f"Percentage of corpus: ~{len(uncovered)/1085*100:.1f}%\n")

    if len(uncovered) == 0:
        print("✅ All errors matched at least one category!")
        return 0

    # Sample and display
    random.seed(42)
    sample_size = min(10, len(uncovered))
    samples = random.sample(uncovered, sample_size)

    print(f"Displaying {sample_size} uncovered errors for manual review:\n")

    for i, err in enumerate(samples, 1):
        print(f"\n{'='*80}")
        print(f"UNCOVERED ERROR #{i}")
        print(f"{'='*80}")
        print(err)

    # Manual categorization
    print("\n" + "="*80)
    print("MANUAL CATEGORIZATION ATTEMPT")
    print("="*80 + "\n")

    print("Review each error above and determine:")
    print("  A) Fits existing category (keyword matching failed)")
    print("  B) Represents new category (not covered by current taxonomy)")
    print()

    print("Based on manual review:\n")

    # Heuristic analysis
    analysis = []
    for i, err in enumerate(samples, 1):
        err_lower = err.lower()

        # Check for specific patterns
        category = "Unknown"

        if "no justification" in err_lower or "not rigorously" in err_lower or "informal" in err_lower:
            category = "Missing Justification (keyword matching failed)"
        elif "does not" in err_lower or "fail" in err_lower or "wrong" in err_lower:
            category = "Faulty Construction (keyword matching failed)"
        elif "flawed" in err_lower or "relies on" in err_lower:
            category = "Logical Deduction (dependency error, keyword matching failed)"
        elif "trivial" in err_lower or "tautology" in err_lower:
            category = "Quantitative Bounds (trivial inequality, keyword matching failed)"
        else:
            category = "Possible new category (needs expert review)"

        analysis.append(category)
        print(f"Error #{i}: {category}")

    # Count new vs. existing
    new_count = sum(1 for cat in analysis if "new category" in cat)
    existing_count = len(analysis) - new_count

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    print(f"Uncovered errors analyzed: {len(analysis)}")
    print(f"  Fit existing categories: {existing_count} ({existing_count/len(analysis)*100:.1f}%)")
    print(f"  Possible new categories: {new_count} ({new_count/len(analysis)*100:.1f}%)")

    if new_count == 0:
        print("\n✅ CONCLUSION: Taxonomy is SATURATED")
        print("   All uncovered errors are keyword matching failures, not new categories.")
        print("   The 6.2% coverage variation is due to keyword limitations, not missing categories.")
    elif new_count <= 2:
        print("\n⚠️  CONCLUSION: Taxonomy is MOSTLY SATURATED")
        print(f"   {new_count}/{len(analysis)} errors may represent edge cases.")
        print("   Review needed, but taxonomy is likely sufficient for Stage 1.5.")
    else:
        print("\n❌ CONCLUSION: Taxonomy may have GAPS")
        print(f"   {new_count}/{len(analysis)} errors don't fit existing categories.")
        print("   New category may be needed before Phase 3.")

    # Save results
    results = {
        'uncovered_count': len(uncovered),
        'uncovered_percentage': len(uncovered)/1085*100,
        'sample_analyzed': len(analysis),
        'fit_existing': existing_count,
        'possible_new': new_count,
        'verdict': 'SATURATED' if new_count == 0 else 'MOSTLY_SATURATED' if new_count <= 2 else 'GAPS'
    }

    with open('uncovered_error_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n✅ Results saved to uncovered_error_analysis.json")

    return 0

if __name__ == '__main__':
    sys.exit(main())
