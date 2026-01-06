#!/usr/bin/env python3
"""
Phase 2.2: Merge BFS + MCTS samples and re-categorize

This script:
1. Loads BFS errors (from stage1_results.json extraction)
2. Loads MCTS errors (from mcts_errors.json)
3. Creates stratified sample of 64 errors (balanced across sources and types)
4. Re-runs categorization LLM to check for new categories
5. Compares new taxonomy with original 7 categories
"""

import json
import random
import sys
import os

# Import categorization function from stage1_error_analysis
sys.path.insert(0, os.path.dirname(__file__))
from stage1_error_analysis import categorize_errors

def load_bfs_errors():
    """Load BFS errors from original Stage 1 extraction."""
    # Note: stage1_results.json doesn't store raw errors, only the analysis
    # We need to re-extract from the BFS log
    from stage1_error_analysis import extract_errors_from_log

    bfs_log = 'run_log_gpt_oss/bfs_revalidation_1.log'
    print(f"[LOAD] Extracting BFS errors from {bfs_log}")

    errors = extract_errors_from_log(bfs_log)
    total = sum(len(v) for v in errors.values())

    print(f"[LOAD] BFS errors: {total} total")
    print(f"  Critical: {len(errors['critical_errors'])}")
    print(f"  Justification Gaps: {len(errors['justification_gaps'])}")
    print(f"  Construction Failures: {len(errors['construction_failures'])}")
    print(f"  Other: {len(errors['other_errors'])}")

    return errors

def load_mcts_errors():
    """Load MCTS errors from Phase 2.1 extraction."""
    print(f"[LOAD] Loading MCTS errors from mcts_errors.json")

    with open('mcts_errors.json', 'r') as f:
        data = json.load(f)

    errors = data['errors']
    total = sum(len(v) for v in errors.values())

    print(f"[LOAD] MCTS errors: {total} total")
    print(f"  Critical: {len(errors['critical_errors'])}")
    print(f"  Justification Gaps: {len(errors['justification_gaps'])}")
    print(f"  Construction Failures: {len(errors['construction_failures'])}")
    print(f"  Other: {len(errors['other_errors'])}")

    return errors

def create_stratified_sample(bfs_errors, mcts_errors, samples_per_type=16):
    """
    Create a stratified sample with balanced representation from both sources.

    Args:
        bfs_errors: Dict of BFS errors by type
        mcts_errors: Dict of MCTS errors by type
        samples_per_type: Number of samples per error type (default: 16 for 64 total)

    Returns:
        Dict of sampled errors (same structure as input)
    """
    print(f"\n[SAMPLE] Creating stratified sample ({samples_per_type} per type)")

    sampled = {
        'critical_errors': [],
        'justification_gaps': [],
        'construction_failures': [],
        'other_errors': []
    }

    for error_type in sampled.keys():
        bfs_list = bfs_errors[error_type]
        mcts_list = mcts_errors[error_type]

        # Calculate how many from each source (aim for 50/50 split)
        total_available = len(bfs_list) + len(mcts_list)
        bfs_count = min(samples_per_type // 2, len(bfs_list))
        mcts_count = min(samples_per_type // 2, len(mcts_list))

        # If one source has fewer than half, take more from the other
        if bfs_count < samples_per_type // 2:
            mcts_count = min(samples_per_type - bfs_count, len(mcts_list))
        elif mcts_count < samples_per_type // 2:
            bfs_count = min(samples_per_type - mcts_count, len(bfs_list))

        # Sample from each source
        bfs_sample = random.sample(bfs_list, bfs_count) if bfs_count > 0 else []
        mcts_sample = random.sample(mcts_list, mcts_count) if mcts_count > 0 else []

        # Combine and truncate to 300 chars each (same as original Stage 1)
        combined_sample = bfs_sample + mcts_sample
        combined_sample = [err[:300] for err in combined_sample]

        sampled[error_type] = combined_sample

        print(f"  {error_type}: {len(combined_sample)} samples (BFS: {bfs_count}, MCTS: {mcts_count})")

    total_samples = sum(len(v) for v in sampled.values())
    print(f"  TOTAL: {total_samples} samples")

    return sampled

def compare_taxonomies(original_taxonomy, new_taxonomy):
    """Compare original and new taxonomies."""
    print("\n" + "="*80)
    print("TAXONOMY COMPARISON")
    print("="*80 + "\n")

    original_cats = set(cat['name'] for cat in original_taxonomy.get('categories', []))
    new_cats = set(cat['name'] for cat in new_taxonomy.get('categories', []))

    print(f"[ORIGINAL] {len(original_cats)} categories:")
    for cat in sorted(original_cats):
        print(f"  - {cat}")

    print(f"\n[NEW] {len(new_cats)} categories:")
    for cat in sorted(new_cats):
        print(f"  - {cat}")

    # Check for differences
    added = new_cats - original_cats
    removed = original_cats - new_cats
    same = original_cats & new_cats

    print(f"\n[COMPARISON]")
    print(f"  Same categories: {len(same)}")
    print(f"  Added categories: {len(added)}")
    print(f"  Removed categories: {len(removed)}")

    if added:
        print(f"\n  ⚠️  NEW CATEGORIES DETECTED:")
        for cat in added:
            print(f"    + {cat}")

    if removed:
        print(f"\n  ⚠️  CATEGORIES NO LONGER PRESENT:")
        for cat in removed:
            print(f"    - {cat}")

    if not added and not removed:
        print(f"\n  ✅ TAXONOMY IS STABLE (same categories in both)")

    return {
        'stable': len(added) == 0 and len(removed) == 0,
        'added': list(added),
        'removed': list(removed),
        'same': list(same)
    }

def main():
    print("\n" + "="*80)
    print("PHASE 2.2: MERGE BFS + MCTS AND RE-CATEGORIZE")
    print("="*80 + "\n")

    # Set random seed for reproducibility
    random.seed(42)

    # Step 1: Load errors from both sources
    bfs_errors = load_bfs_errors()
    mcts_errors = load_mcts_errors()

    # Step 2: Create stratified sample
    sampled_errors = create_stratified_sample(bfs_errors, mcts_errors, samples_per_type=16)

    # Step 3: Re-run categorization
    print("\n" + "="*80)
    print("RE-CATEGORIZING WITH MERGED SAMPLE")
    print("="*80 + "\n")

    new_taxonomy = categorize_errors(sampled_errors)

    if not new_taxonomy.get('categories'):
        print("[ERROR] Failed to create new taxonomy. Exiting.")
        return 1

    # Step 4: Load original taxonomy for comparison
    with open('stage1_results.json', 'r') as f:
        stage1 = json.load(f)
        original_taxonomy = stage1['taxonomy']

    # Step 5: Compare taxonomies
    comparison = compare_taxonomies(original_taxonomy, new_taxonomy)

    # Step 6: Save results
    results = {
        'phase': 'Phase 2.2',
        'date': '2025-12-18',
        'sample_strategy': 'stratified (balanced BFS/MCTS, 16 per type)',
        'sample_size': sum(len(v) for v in sampled_errors.values()),
        'sources': {
            'bfs': {
                'log': 'run_log_gpt_oss/bfs_revalidation_1.log',
                'errors': sum(len(v) for v in bfs_errors.values())
            },
            'mcts': {
                'log': 'run_log_gpt_oss/mcts_phase1_validation_p1.log',
                'errors': sum(len(v) for v in mcts_errors.values())
            }
        },
        'new_taxonomy': new_taxonomy,
        'comparison': comparison
    }

    with open('phase2_2_taxonomy_comparison.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to phase2_2_taxonomy_comparison.json")

    # Step 7: Generate summary
    if comparison['stable']:
        print("\n" + "="*80)
        print("✅ TAXONOMY IS STABLE")
        print("="*80)
        print("\nThe merged BFS+MCTS sample produces the same error categories as BFS-only.")
        print("This means:")
        print("  ✅ Original 7 templates generalize to MCTS data")
        print("  ✅ No new error patterns discovered in MCTS")
        print("  ✅ Ready to proceed to Phase 2.3 (saturation test)")
    else:
        print("\n" + "="*80)
        print("⚠️  TAXONOMY HAS CHANGED")
        print("="*80)
        print("\nNew categories detected or existing categories removed.")
        print("Action required:")
        print("  1. Review new categories")
        print("  2. Create templates for new categories (if applicable)")
        print("  3. Update Stage 1 templates list")
        print("  4. Re-run Phase 3 testing with updated templates")

    return 0

if __name__ == '__main__':
    sys.exit(main())
